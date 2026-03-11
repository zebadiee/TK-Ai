"""HADES kernel runtime loop with indexed memory layer."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from atlas.executor import AtlasExecutor
from atlas.proposers import build_ollama_proposer
from athena.interface import AthenaInterface
from hades.budget import BudgetLedger
from hades.capabilities import CapabilityRegistry
from hades.graph_fitness import GraphFitnessScorer, GraphFitnessStore, GraphMetrics
from hades.graph_planner import GraphPlanner
from hades.graph_registry import GraphRegistry
from hades.llm_graph_planner import LLMGraphPlanner
from hades.model_router import ModelRoute, ModelRouter
from hades.patterns import PatternIndex, load_patterns
from hades.router import Router
from hades.signals import AggregatedTrigger, SignalAggregator, SignalEvent, load_signal_rules
from hades.task_graph import GraphRunState, TaskGraph, TaskGraphRunner, load_solution_graphs
from hades.triggers import TriggerEngine, TriggerEvent, load_trigger_rules


class HadesKernel:
    """Coordinates ATHENA intake, routing, execution, and memory reinforcement."""

    def __init__(
        self,
        athena: AthenaInterface,
        router: Router,
        executor: AtlasExecutor,
        state_path: str | Path,
        index_path: str | Path,
        memory_threshold: float = 0.5,
        model_router: ModelRouter | None = None,
        budget_ledger: BudgetLedger | None = None,
        graph_path: str | Path | None = None,
        graph_registry: GraphRegistry | None = None,
        fitness_scorer: GraphFitnessScorer | None = None,
        fitness_store: GraphFitnessStore | None = None,
        trigger_engine: TriggerEngine | None = None,
        signal_aggregator: SignalAggregator | None = None,
        graph_planner: GraphPlanner | None = None,
    ) -> None:
        self.athena = athena
        self.router = router
        self.executor = executor
        self.state_path = Path(state_path)
        self.index = PatternIndex(index_path)
        self.memory_threshold = memory_threshold
        self.model_router = model_router or ModelRouter()
        self.budget_ledger = budget_ledger or BudgetLedger()
        self.graphs = load_solution_graphs(graph_path) if graph_path is not None else {}
        self.graph_registry = graph_registry
        self.fitness_scorer = fitness_scorer or GraphFitnessScorer()
        self.fitness_store = fitness_store
        self.trigger_engine = trigger_engine or TriggerEngine()
        self.signal_aggregator = signal_aggregator or SignalAggregator()
        self.graph_planner = graph_planner
        self.graph_runner = TaskGraphRunner(executor)
        self.state = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {
                "ticks": 0,
                "events": [],
                "graph_runs": {},
                "memory_version": self.index.data.get("version", 1),
            }
        with self.state_path.open("r", encoding="utf-8") as handle:
            state = json.load(handle)
        if not isinstance(state, dict):
            raise ValueError(f"Invalid state at {self.state_path}")
        state.setdefault("ticks", 0)
        state.setdefault("events", [])
        state.setdefault("graph_runs", {})
        state["memory_version"] = self.index.data.get("version", 1)
        return state

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with self.state_path.open("w", encoding="utf-8") as handle:
            json.dump(self.state, handle, indent=2, sort_keys=True)

    def _coerce_model_route(self, route_data: Any) -> ModelRoute | None:
        if not isinstance(route_data, dict):
            return None

        backend = str(route_data.get("backend", "")).strip()
        model = str(route_data.get("model", "")).strip()
        if not backend or not model:
            return None

        return ModelRoute(
            backend=backend,
            model=model,
            max_tokens=int(route_data.get("max_tokens", 256)),
            max_latency_ms=int(route_data.get("max_latency_ms", 1000)),
            reason=str(route_data.get("reason", "memory_route")),
        )

    def tick(self) -> dict[str, Any]:
        start_ts = time.perf_counter()

        message = self.athena.get_next_intent()
        intent = str(message.get("intent", "noop"))
        payload = message.get("payload", {})
        if not isinstance(payload, dict):
            payload = {"raw": payload}

        trace_id = str(payload.get("trace_id", uuid.uuid4()))
        payload["trace_id"] = trace_id
        payload.setdefault("intent_text", intent)

        pattern_match = self.index.lookup_best(intent, threshold=self.memory_threshold)
        matched_record: dict[str, Any] | None = None
        if pattern_match is not None:
            action = pattern_match.action
            matched_record = self.index.lookup(intent, threshold=self.memory_threshold)
            if isinstance(matched_record, dict) and action == "model_infer":
                metadata = matched_record.get("metadata", {})
                if isinstance(metadata, dict):
                    model_route = metadata.get("model_route")
                    if isinstance(model_route, dict):
                        payload["model_route"] = model_route
                    saved_budget = metadata.get("budget_decision")
                    if isinstance(saved_budget, dict):
                        payload["budget_decision"] = saved_budget
            resolution_source = f"memory_{pattern_match.reason}"
        else:
            action = self.router.resolve(intent)
            if action == "noop":
                proposed_route = self.model_router.resolve(
                    intent,
                    {"payload": payload, "trace_id": trace_id},
                )
                payload["model_route"] = proposed_route.to_dict()
                action = "model_infer"
                resolution_source = "model_router"
            else:
                resolution_source = "static_router"

        if action == "model_infer":
            proposed_route = self._coerce_model_route(payload.get("model_route", {}))
            if proposed_route is None:
                proposed_route = self.model_router.resolve(
                    intent,
                    {"payload": payload, "trace_id": trace_id},
                )

            effective_route, budget_decision = self.budget_ledger.enforce(
                proposed_route,
                {"payload": payload, "trace_id": trace_id},
            )
            payload["budget_decision"] = budget_decision.to_dict()
            if effective_route is None:
                action = "noop"
                resolution_source = "budget_blocked"
                payload.pop("model_route", None)
            else:
                payload["model_route"] = effective_route.to_dict()

        result = self.executor.execute(action, payload)
        success = result.get("status") in ("ok", "dispatched", "ignored")
        pattern_update = None

        if success and resolution_source in {"static_router", "model_router"} and action != "noop":
            reinforce_metadata = {"source": resolution_source}
            if action == "model_infer":
                reinforce_metadata["model_route"] = payload.get("model_route", {})
                reinforce_metadata["budget_decision"] = payload.get("budget_decision", {})
            self.index.reinforce(
                intent,
                action,
                success=True,
                metadata=reinforce_metadata,
            )
            pattern_update = action

        latency_ms = round((time.perf_counter() - start_ts) * 1000, 2)

        event = {
            "event_id": str(uuid.uuid4()),
            "trace_id": trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "intent": intent,
            "action": action,
            "status": result.get("status", "unknown"),
            "latency_ms": latency_ms,
            "resolution_source": resolution_source,
            "pattern_selected": pattern_match is not None,
            "pattern_confidence": pattern_match.confidence if pattern_match else None,
            "pattern_update": pattern_update,
        }

        budget_data = payload.get("budget_decision")
        if isinstance(budget_data, dict):
            event["budget_allowed"] = budget_data.get("allow")
            event["budget_tier"] = budget_data.get("tier")
            event["budget_reason"] = budget_data.get("reason")
            event["budget_max_tokens"] = budget_data.get("max_tokens")

        model_route_data = payload.get("model_route")
        if isinstance(model_route_data, dict):
            event["model_backend"] = model_route_data.get("backend")
            event["model_name"] = model_route_data.get("model")

        if "error" in result:
            event["error"] = result["error"]

        self.state["ticks"] += 1
        self.state["events"].append(event)

        if len(self.state["events"]) > 100:
            self.state["events"] = self.state["events"][-100:]

        self._save_state()
        return result

    def _record_graph_event(
        self,
        graph_state: GraphRunState,
        trace_id: str,
        entry_mode: str,
        entry_metadata: dict[str, Any],
        fitness_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if graph_state.pending_jobs:
            status = "accepted"
        elif graph_state.completed:
            status = "ok"
        else:
            status = "failed"
        event = {
            "event_id": str(uuid.uuid4()),
            "trace_id": trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "task_graph",
            "graph_id": graph_state.graph_id,
            "status": status,
            "entry_mode": entry_mode,
            "node_status": graph_state.node_status,
            "pending_jobs": graph_state.pending_jobs,
            "entry_metadata": entry_metadata,
        }
        if isinstance(fitness_data, dict):
            event.update(fitness_data)
        self.state["ticks"] += 1
        self.state["events"].append(event)
        if len(self.state["events"]) > 100:
            self.state["events"] = self.state["events"][-100:]
        self._save_state()
        return event

    def _estimate_graph_tokens(self, graph_state: GraphRunState) -> int:
        total_tokens = 0
        for result in graph_state.results.values():
            if not isinstance(result, dict):
                continue
            usage = result.get("usage", {})
            if not isinstance(usage, dict):
                continue
            try:
                total_tokens += int(usage.get("total_tokens", 0))
            except (TypeError, ValueError):
                continue
        return total_tokens

    def _estimate_graph_cost(self, graph_state: GraphRunState) -> float:
        total_cost = 0.0
        for result in graph_state.results.values():
            if not isinstance(result, dict):
                continue

            provider_metadata = result.get("provider_metadata", {})
            if isinstance(provider_metadata, dict):
                explicit_cost = provider_metadata.get("estimated_cost", provider_metadata.get("cost"))
                if isinstance(explicit_cost, (int, float)):
                    total_cost += float(explicit_cost)
                    continue

            usage = result.get("usage", {})
            if isinstance(usage, dict):
                try:
                    total_cost += float(usage.get("total_tokens", 0)) / 100000.0
                except (TypeError, ValueError):
                    continue
        return round(total_cost, 6)

    def _score_graph_run(self, graph_state: GraphRunState, runtime_ms: float) -> dict[str, Any]:
        if self.fitness_store is None:
            return {}

        metrics = GraphMetrics(
            success=graph_state.completed,
            latency_ms=runtime_ms,
            cost=self._estimate_graph_cost(graph_state),
            token_usage=self._estimate_graph_tokens(graph_state),
        )
        score = self.fitness_scorer.score(metrics)
        summary = self.fitness_store.record(graph_state.graph_id, metrics, score)

        fitness_data: dict[str, Any] = {
            "graph_fitness_score": round(score, 4),
            "graph_avg_fitness_score": round(summary.avg_score, 4),
            "graph_runs": summary.runs,
            "graph_success_rate": round(summary.success_rate, 4),
            "graph_avg_latency_ms": round(summary.avg_latency_ms, 2),
            "graph_avg_cost": round(summary.avg_cost, 6),
            "graph_avg_tokens": round(summary.avg_tokens, 2),
        }

        if self.graph_registry is None:
            return fitness_data

        graph_name = self.graph_registry.graph_name_for_version(graph_state.graph_id)
        if graph_name is None:
            return fitness_data

        fitness_data["graph_family"] = graph_name
        record = self.graph_registry.index.get(graph_name, {})
        experimental_versions = record.get("experimental", []) if isinstance(record, dict) else []
        experimental = isinstance(experimental_versions, list) and graph_state.graph_id in experimental_versions

        registry_changed = False
        if self.fitness_scorer.should_promote(summary, experimental):
            self.graph_registry.promote_version(graph_name, graph_state.graph_id)
            fitness_data["graph_promoted"] = graph_state.graph_id
            registry_changed = True
        elif self.fitness_scorer.should_record_failure(summary):
            rollback_to = self.graph_registry.record_failure(
                graph_name,
                threshold=self.fitness_scorer.failure_streak_threshold,
            )
            fitness_data["graph_failure_recorded"] = True
            if rollback_to is not None:
                fitness_data["graph_rolled_back_to"] = rollback_to
            registry_changed = True

        if registry_changed:
            self.graph_registry.save()

        return fitness_data

    def _run_graph(
        self,
        graph_id: str,
        trace_id: str,
        entry_mode: str,
        entry_metadata: dict[str, Any],
        base_payload: dict[str, Any] | None = None,
        reinforce_intent: str | None = None,
        reinforce_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        graph = self.graphs.get(graph_id)
        if graph is None and self.graph_registry is not None:
            graph = self.graph_registry.resolve(graph_id)
        if graph is None:
            return {"status": "error", "error": f"Unknown task graph: {graph_id}", "graph_id": graph_id}

        return self._run_task_graph(
            graph=graph,
            trace_id=trace_id,
            entry_mode=entry_mode,
            entry_metadata=entry_metadata,
            base_payload=base_payload,
            reinforce_intent=reinforce_intent,
            reinforce_metadata=reinforce_metadata,
        )

    def _run_task_graph(
        self,
        graph: TaskGraph,
        trace_id: str,
        entry_mode: str,
        entry_metadata: dict[str, Any],
        base_payload: dict[str, Any] | None = None,
        reinforce_intent: str | None = None,
        reinforce_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.graphs[graph.graph_id] = graph

        started_at = time.time()
        graph_state = self.graph_runner.run(graph, trace_id=trace_id, base_payload=base_payload)
        self._persist_graph_run(
            trace_id=trace_id,
            graph_state=graph_state,
            entry_mode=entry_mode,
            entry_metadata=entry_metadata,
            reinforce_intent=reinforce_intent,
            reinforce_metadata=reinforce_metadata,
            started_at=started_at,
        )

        fitness_data = {}
        if not graph_state.pending_jobs:
            fitness_data = self._score_graph_run(
                graph_state=graph_state,
                runtime_ms=max(0.0, (time.time() - started_at) * 1000.0),
            )

        if reinforce_intent is not None and not graph_state.pending_jobs:
            metadata = reinforce_metadata if isinstance(reinforce_metadata, dict) else {}
            self.index.reinforce(
                intent=reinforce_intent,
                action="task_graph",
                success=graph_state.completed,
                metadata={**metadata, "graph_id": graph.graph_id, "entry_mode": entry_mode},
            )

        event = self._record_graph_event(
            graph_state=graph_state,
            trace_id=trace_id,
            entry_mode=entry_mode,
            entry_metadata=entry_metadata,
            fitness_data=fitness_data,
        )
        return {
            "status": "accepted" if graph_state.pending_jobs else ("ok" if graph_state.completed else "failed"),
            "graph_id": graph.graph_id,
            "trace_id": trace_id,
            "node_status": graph_state.node_status,
            "pending_jobs": graph_state.pending_jobs,
            "event_id": event["event_id"],
            **fitness_data,
        }

    def handle_intent(self, message: dict[str, Any]) -> dict[str, Any]:
        if self.graph_planner is None:
            return {"status": "ignored", "reason": "no_graph_planner"}

        intent = str(message.get("intent", "noop"))
        payload = message.get("payload", {})
        if not isinstance(payload, dict):
            payload = {"raw": payload}
        trace_id = str(payload.get("trace_id", uuid.uuid4()))
        payload["trace_id"] = trace_id

        graph = self.graph_planner.plan_graph(intent, payload)
        return self._run_task_graph(
            graph=graph,
            trace_id=trace_id,
            entry_mode="planner",
            entry_metadata={"intent": intent, "planner": graph.metadata.get("planner", "unknown")},
            base_payload=payload,
            reinforce_intent=intent,
            reinforce_metadata={"planner_graph_id": graph.graph_id},
        )

    def _persist_graph_run(
        self,
        trace_id: str,
        graph_state: GraphRunState,
        entry_mode: str,
        entry_metadata: dict[str, Any],
        reinforce_intent: str | None,
        reinforce_metadata: dict[str, Any] | None,
        started_at: float,
    ) -> None:
        graph_runs = self.state.setdefault("graph_runs", {})
        if graph_state.pending_jobs:
            graph_runs[trace_id] = {
                "graph_state": graph_state.to_dict(),
                "entry_mode": entry_mode,
                "entry_metadata": entry_metadata,
                "reinforce_intent": reinforce_intent,
                "reinforce_metadata": reinforce_metadata if isinstance(reinforce_metadata, dict) else {},
                "started_at": started_at,
            }
        else:
            graph_runs.pop(trace_id, None)

    def handle_job_finished(self, event: dict[str, Any]) -> dict[str, Any]:
        trace_id = str(event.get("trace_id", "")).strip()
        job_id = str(event.get("job_id", "")).strip()
        result_payload = event.get("result", {})
        if not trace_id or not job_id:
            return {"status": "ignored", "reason": "missing_job_identity"}

        graph_runs = self.state.setdefault("graph_runs", {})
        run_record = graph_runs.get(trace_id)
        if not isinstance(run_record, dict):
            return {"status": "ignored", "reason": "unknown_graph_run", "trace_id": trace_id}
        started_at = float(run_record.get("started_at", time.time()))

        graph_state = GraphRunState.from_dict(run_record.get("graph_state", {}))
        node_id = graph_state.pending_jobs.pop(job_id, None)
        if node_id is None:
            return {"status": "ignored", "reason": "unknown_job_id", "trace_id": trace_id, "job_id": job_id}

        graph = self.graphs.get(graph_state.graph_id)
        if graph is None and self.graph_registry is not None:
            graph = self.graph_registry.resolve(graph_state.graph_id)
        if graph is None:
            return {"status": "error", "error": f"Unknown task graph: {graph_state.graph_id}", "graph_id": graph_state.graph_id}

        graph_state.node_status[node_id] = "ok"
        if not isinstance(result_payload, dict):
            result_payload = {"result": result_payload}
        graph_state.results[node_id] = dict(result_payload)
        graph_state.current_node_id = self.graph_runner._next_node_id(graph, node_id)

        resumed_state = self.graph_runner.run_once(
            graph,
            graph_state,
            base_payload={**result_payload, "trace_id": trace_id},
        )

        reinforce_intent = run_record.get("reinforce_intent")
        reinforce_metadata = run_record.get("reinforce_metadata", {})
        entry_mode = str(run_record.get("entry_mode", "job_resume"))
        entry_metadata = run_record.get("entry_metadata", {})

        self._persist_graph_run(
            trace_id=trace_id,
            graph_state=resumed_state,
            entry_mode=entry_mode,
            entry_metadata=entry_metadata,
            reinforce_intent=reinforce_intent if isinstance(reinforce_intent, str) else None,
            reinforce_metadata=reinforce_metadata if isinstance(reinforce_metadata, dict) else {},
            started_at=started_at,
        )

        fitness_data = {}
        if not resumed_state.pending_jobs:
            fitness_data = self._score_graph_run(
                graph_state=resumed_state,
                runtime_ms=max(0.0, (time.time() - started_at) * 1000.0),
            )

        if isinstance(reinforce_intent, str) and not resumed_state.pending_jobs:
            self.index.reinforce(
                intent=reinforce_intent,
                action="task_graph",
                success=resumed_state.completed,
                metadata={
                    **(reinforce_metadata if isinstance(reinforce_metadata, dict) else {}),
                    "graph_id": resumed_state.graph_id,
                    "entry_mode": entry_mode,
                },
            )

        graph_event = self._record_graph_event(
            graph_state=resumed_state,
            trace_id=trace_id,
            entry_mode="job_finished",
            entry_metadata={"job_id": job_id, "result": result_payload},
            fitness_data=fitness_data,
        )

        return {
            "status": "accepted" if resumed_state.pending_jobs else ("ok" if resumed_state.completed else "failed"),
            "graph_id": resumed_state.graph_id,
            "trace_id": trace_id,
            "node_status": resumed_state.node_status,
            "event_id": graph_event["event_id"],
            **fitness_data,
        }

    def handle_event(self, event: TriggerEvent) -> dict[str, Any]:
        match = self.trigger_engine.match(event)
        if match is None:
            return {"status": "ignored", "reason": "no_trigger_match"}

        trace_id = str(event.payload.get("trace_id", uuid.uuid4()))
        return self._run_graph(
            graph_id=match.graph_id,
            trace_id=trace_id,
            entry_mode="trigger",
            entry_metadata=match.metadata,
            base_payload=dict(event.payload),
            reinforce_intent=f"trigger:{event.event_type}",
            reinforce_metadata={"trigger_event_type": event.event_type},
        )

    def handle_signal(self, signal: SignalEvent) -> dict[str, Any]:
        aggregate = self.signal_aggregator.ingest(signal)
        if aggregate is None:
            return {"status": "ignored", "reason": "no_signal_match"}

        trace_id = str(aggregate.metadata.get("trace_id", uuid.uuid4()))
        return self._run_graph(
            graph_id=aggregate.graph_id,
            trace_id=trace_id,
            entry_mode="signal",
            entry_metadata={
                "signal_rule_id": aggregate.rule_id,
                "score": aggregate.score,
                "matched_signals": aggregate.matched_signals,
                **aggregate.metadata,
            },
            base_payload={"signal_context": aggregate.metadata, "trace_id": trace_id},
            reinforce_intent=f"signal:{aggregate.rule_id}",
            reinforce_metadata={"score": aggregate.score, "matched_signals": aggregate.matched_signals},
        )

    def run(self, max_ticks: int = 1) -> list[dict[str, Any]]:
        results = []
        for _ in range(max_ticks):
            results.append(self.tick())
        return results


def build_default_kernel(repo_root: Path) -> HadesKernel:
    patterns = load_patterns(repo_root / "vault" / "patterns.json")
    router = Router(routes=patterns.get("routes", {}))

    executor_config: dict[str, Any] = {}
    capabilities = patterns.get("capabilities", {})

    if isinstance(capabilities, dict):
        clawx_capability = capabilities.get("clawx", {})
        if isinstance(clawx_capability, dict):
            bridge = clawx_capability.get("bridge")
            if isinstance(bridge, str) and bridge.strip():
                executor_config["clawx_bridge"] = bridge

    trigger_engine = TriggerEngine(load_trigger_rules(repo_root / "vault" / "triggers.json"))
    signal_aggregator = SignalAggregator(load_signal_rules(repo_root / "vault" / "signals.json"))
    capability_registry = CapabilityRegistry.from_path(repo_root / "vault" / "capabilities.json")
    graph_registry = GraphRegistry.from_paths(
        repo_root / "vault" / "graph_index.json",
        repo_root / "vault" / "solution_graphs",
    )
    fitness_store = GraphFitnessStore(repo_root / "vault" / "graph_metrics.json")
    planner_config = capability_registry.config.get("planner", {})
    if not isinstance(planner_config, dict):
        planner_config = {}
    ollama_models = capability_registry.allowed_models("ollama")
    proposer = build_ollama_proposer(
        model=str(planner_config.get("model", ollama_models[0] if ollama_models else "qwen2.5")),
        url=str(planner_config.get("url", "http://localhost:11434/api/generate")),
        timeout=float(planner_config.get("timeout", 30.0)),
        capabilities=capability_registry.allowed_capabilities(),
    )
    graph_planner = LLMGraphPlanner(
        capability_registry,
        proposer=proposer,
        fallback_planner=GraphPlanner(capability_registry),
        fallback_on_invalid=True,
    )

    return HadesKernel(
        athena=AthenaInterface(),
        router=router,
        executor=AtlasExecutor(config=executor_config),
        state_path=repo_root / "vault" / "state.json",
        index_path=repo_root / "vault" / "pattern_index.json",
        graph_path=repo_root / "vault" / "solution_graph.json",
        graph_registry=graph_registry,
        fitness_store=fitness_store,
        trigger_engine=trigger_engine,
        signal_aggregator=signal_aggregator,
        graph_planner=graph_planner,
    )


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    kernel = build_default_kernel(root)
    kernel.run(max_ticks=1)
