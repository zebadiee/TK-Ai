from __future__ import annotations

import uuid
from pathlib import Path

from atlas.executor import AtlasExecutor
from hades.budget import BudgetLedger
from hades.capabilities import CapabilityRegistry
from hades.graph_fitness import GraphFitnessScorer, GraphFitnessStore
from hades.graph_planner import GraphPlanner
from hades.graph_registry import GraphRegistry
from hades.kernel import HadesKernel, build_default_kernel
from hades.llm_graph_planner import LLMGraphPlanner
from hades.model_router import ModelRouter
from hades.router import Router
from hades.signals import SignalAggregator, SignalEvent, SignalRule
from hades.triggers import TriggerEngine, TriggerEvent, TriggerRule


class StubAthena:
    def __init__(self, intents=None):
        self.intents = intents or [{"intent": "ping", "payload": {}}]
        self.count = 0

    def get_next_intent(self) -> dict[str, object]:
        intent = self.intents[self.count % len(self.intents)]
        self.count += 1
        return intent


def test_kernel_tick_persists_structured_state(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    index_path = tmp_path / "index.json"
    kernel = HadesKernel(
        athena=StubAthena([{"intent": "ping", "payload": {"trace_id": "fixed-id"}}]),
        router=Router(routes={"ping": "echo"}),
        executor=AtlasExecutor(),
        state_path=state_path,
        index_path=index_path,
    )
    result = kernel.tick()

    assert result["status"] == "ok"
    assert kernel.state["ticks"] == 1

    event = kernel.state["events"][0]
    assert event["trace_id"] == "fixed-id"
    assert "event_id" in event
    assert "latency_ms" in event
    assert event["intent"] == "ping"
    assert event["action"] == "echo"
    assert event["resolution_source"] == "static_router"
    assert event["pattern_selected"] is False
    assert event["pattern_confidence"] is None
    assert event["pattern_update"] == "echo"


def test_kernel_learning_behavior(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    index_path = tmp_path / "index.json"

    kernel = HadesKernel(
        athena=StubAthena([{"intent": "new_intent"}]),
        router=Router(routes={"new_intent": "special_action"}),
        executor=AtlasExecutor(),
        state_path=state_path,
        index_path=index_path,
    )
    kernel.tick()
    assert kernel.state["events"][0]["resolution_source"] == "static_router"
    assert kernel.state["events"][0]["pattern_update"] == "special_action"

    kernel.tick()
    assert kernel.state["events"][1]["resolution_source"] == "memory_exact"
    assert kernel.state["events"][1]["action"] == "special_action"
    assert kernel.state["events"][1]["pattern_selected"] is True
    assert kernel.state["events"][1]["pattern_confidence"] == 1.0
    assert kernel.state["events"][1]["pattern_update"] is None


def test_kernel_does_not_learn_failures(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    index_path = tmp_path / "index.json"

    class FailingExecutor(AtlasExecutor):
        def execute(self, action, payload):
            return {"status": "error", "error": "failed"}

    kernel = HadesKernel(
        athena=StubAthena([{"intent": "bad_intent"}]),
        router=Router(routes={"bad_intent": "broken"}),
        executor=FailingExecutor(),
        state_path=state_path,
        index_path=index_path,
    )

    kernel.tick()
    assert kernel.state["events"][0]["resolution_source"] == "static_router"
    assert "bad_intent" not in kernel.index.data.get("patterns", {})
    assert not index_path.exists()


def test_kernel_exact_match_beats_router(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    index_path = tmp_path / "index.json"
    kernel = HadesKernel(
        athena=StubAthena([{"intent": "ping"}]),
        router=Router(routes={"ping": "router_action"}),
        executor=AtlasExecutor(),
        state_path=state_path,
        index_path=index_path,
    )
    kernel.index.reinforce("ping", "memory_action", metadata={"source": "seed"})

    result = kernel.tick()

    assert result["action"] == "memory_action"
    assert kernel.state["events"][0]["resolution_source"] == "memory_exact"


def test_kernel_below_threshold_match_falls_back_to_router(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    index_path = tmp_path / "index.json"
    kernel = HadesKernel(
        athena=StubAthena([{"intent": "monitor filings"}]),
        router=Router(routes={"monitor filings": "router_action"}),
        executor=AtlasExecutor(),
        state_path=state_path,
        index_path=index_path,
        memory_threshold=0.9,
    )
    kernel.index.reinforce("monitor sec filings", "memory_action", metadata={"source": "seed"})

    result = kernel.tick()

    assert result["action"] == "router_action"
    assert kernel.state["events"][0]["resolution_source"] == "static_router"
    assert kernel.state["events"][0]["pattern_selected"] is False


def test_kernel_uses_model_router_only_on_true_miss(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    index_path = tmp_path / "index.json"
    kernel = HadesKernel(
        athena=StubAthena([{"intent": "draft summary"}]),
        router=Router(),
        executor=AtlasExecutor(),
        state_path=state_path,
        index_path=index_path,
        model_router=ModelRouter(),
    )

    result = kernel.tick()

    assert result["action"] == "model_infer"
    assert result["backend"] == "Model"
    assert kernel.state["events"][0]["resolution_source"] == "model_router"
    assert kernel.state["events"][0]["pattern_update"] == "model_infer"
    assert kernel.state["events"][0]["model_backend"] == "local"
    assert kernel.state["events"][0]["budget_allowed"] is True
    assert kernel.state["events"][0]["budget_tier"] == "local"


def test_kernel_memory_hit_skips_model_router(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    index_path = tmp_path / "index.json"
    kernel = HadesKernel(
        athena=StubAthena([{"intent": "draft summary"}]),
        router=Router(),
        executor=AtlasExecutor(),
        state_path=state_path,
        index_path=index_path,
        model_router=ModelRouter(),
    )
    kernel.index.reinforce(
        "draft summary",
        "model_infer",
        metadata={
            "source": "model_router",
            "model_route": {
                "backend": "free",
                "model": "free-standard",
                "max_tokens": 512,
                "max_latency_ms": 3000,
                "reason": "medium_problem",
            },
        },
    )

    result = kernel.tick()

    assert result["action"] == "model_infer"
    assert result["model_backend"] == "free"
    assert kernel.state["events"][0]["resolution_source"] == "memory_exact"
    assert kernel.state["events"][0]["pattern_selected"] is True


def test_kernel_budget_block_can_skip_model_call(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    index_path = tmp_path / "index.json"
    kernel = HadesKernel(
        athena=StubAthena([{"intent": "draft summary"}]),
        router=Router(),
        executor=AtlasExecutor(),
        state_path=state_path,
        index_path=index_path,
        model_router=ModelRouter(),
        budget_ledger=BudgetLedger({"models_enabled": False}),
    )

    result = kernel.tick()

    assert result["action"] == "noop"
    assert kernel.state["events"][0]["resolution_source"] == "budget_blocked"
    assert kernel.state["events"][0]["budget_allowed"] is False
    assert kernel.state["events"][0]["pattern_update"] is None


def test_kernel_long_running_miss_can_route_to_clawx_provider(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    index_path = tmp_path / "index.json"
    kernel = HadesKernel(
        athena=StubAthena([{"intent": "monitor sec filings", "payload": {"long_running": True}}]),
        router=Router(),
        executor=AtlasExecutor(config={"clawx_bridge": "mock"}),
        state_path=state_path,
        index_path=index_path,
        model_router=ModelRouter(),
        budget_ledger=BudgetLedger(),
    )

    result = kernel.tick()

    assert result["action"] == "model_infer"
    assert result["model_backend"] == "clawx"
    assert kernel.state["events"][0]["model_backend"] == "clawx"
    assert kernel.state["events"][0]["budget_tier"] == "clawx"


def test_kernel_generates_missing_trace_id(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    index_path = tmp_path / "index.json"
    kernel = HadesKernel(
        athena=StubAthena([{"intent": "ping", "payload": {}}]),
        router=Router(),
        executor=AtlasExecutor(),
        state_path=state_path,
        index_path=index_path,
    )
    kernel.tick()
    event = kernel.state["events"][0]
    uuid.UUID(event["trace_id"])


def test_kernel_history_limit(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    index_path = tmp_path / "index.json"
    kernel = HadesKernel(
        athena=StubAthena([{"intent": "ping"}]),
        router=Router(),
        executor=AtlasExecutor(),
        state_path=state_path,
        index_path=index_path,
    )
    for _ in range(110):
        kernel.tick()

    assert len(kernel.state["events"]) == 100
    assert kernel.state["ticks"] == 110


def test_kernel_handle_event_launches_graph_and_reinforces(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    index_path = tmp_path / "index.json"
    graph_path = tmp_path / "graphs.json"
    graph_path.write_text(
        """
{
  "graphs": {
    "g1": {
      "nodes": [
        {"node_id": "notify", "action": "notify", "payload": {"channel": "telegram", "message": "hello"}}
      ]
    }
  }
}
""".strip()
    )
    kernel = HadesKernel(
        athena=StubAthena(),
        router=Router(),
        executor=AtlasExecutor(),
        state_path=state_path,
        index_path=index_path,
        graph_path=graph_path,
        trigger_engine=TriggerEngine(
            [TriggerRule(event_type="market_move", condition={"change_pct_gt": 3}, graph_id="g1")]
        ),
    )

    result = kernel.handle_event(TriggerEvent(event_type="market_move", payload={"change_pct": 5}))

    assert result["status"] == "ok"
    assert result["graph_id"] == "g1"
    assert kernel.state["events"][0]["entry_mode"] == "trigger"
    assert kernel.index.lookup("trigger:market_move") is not None


def test_kernel_handle_event_resolves_graph_from_registry(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    index_path = tmp_path / "index.json"
    graph_dir = tmp_path / "solution_graphs"
    graph_dir.mkdir()
    (graph_dir / "g1_v1.json").write_text(
        """
{
  "metadata": {"purpose": "registry graph"},
  "nodes": [
    {"node_id": "notify", "action": "notify", "payload": {"channel": "telegram", "message": "registry"}}
  ]
}
""".strip(),
        encoding="utf-8",
    )
    graph_index_path = tmp_path / "graph_index.json"
    graph_index_path.write_text(
        """
{
  "g1": {
    "active": "g1_v1",
    "versions": ["g1_v1"],
    "experimental": [],
    "history": ["g1_v1"],
    "failure_count": 0
  }
}
""".strip(),
        encoding="utf-8",
    )
    kernel = HadesKernel(
        athena=StubAthena(),
        router=Router(),
        executor=AtlasExecutor(),
        state_path=state_path,
        index_path=index_path,
        trigger_engine=TriggerEngine(
            [TriggerRule(event_type="market_move", condition={"change_pct_gt": 3}, graph_id="g1")]
        ),
        graph_registry=GraphRegistry.from_paths(graph_index_path, graph_dir),
    )

    result = kernel.handle_event(TriggerEvent(event_type="market_move", payload={"change_pct": 5}))

    assert result["status"] == "ok"
    assert result["graph_id"] == "g1_v1"
    assert kernel.state["events"][0]["graph_id"] == "g1_v1"


def test_kernel_promotes_experimental_graph_on_high_fitness(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    index_path = tmp_path / "index.json"
    graph_dir = tmp_path / "solution_graphs"
    graph_dir.mkdir()
    (graph_dir / "g1_v1.json").write_text(
        """
{
  "metadata": {"purpose": "stable"},
  "nodes": [
    {"node_id": "notify", "action": "notify", "payload": {"channel": "telegram", "message": "v1"}}
  ]
}
""".strip(),
        encoding="utf-8",
    )
    (graph_dir / "g1_v2.json").write_text(
        """
{
  "metadata": {"purpose": "candidate"},
  "nodes": [
    {"node_id": "notify", "action": "notify", "payload": {"channel": "telegram", "message": "v2"}}
  ]
}
""".strip(),
        encoding="utf-8",
    )
    graph_index_path = tmp_path / "graph_index.json"
    graph_index_path.write_text(
        """
{
  "g1": {
    "active": "g1_v1",
    "versions": ["g1_v1", "g1_v2"],
    "experimental": ["g1_v2"],
    "history": ["g1_v1"],
    "failure_count": 0
  }
}
""".strip(),
        encoding="utf-8",
    )
    metrics_path = tmp_path / "graph_metrics.json"
    kernel = HadesKernel(
        athena=StubAthena(),
        router=Router(),
        executor=AtlasExecutor(),
        state_path=state_path,
        index_path=index_path,
        trigger_engine=TriggerEngine(
            [TriggerRule(event_type="market_move", condition={"change_pct_gt": 3}, graph_id="g1_v2")]
        ),
        graph_registry=GraphRegistry.from_paths(graph_index_path, graph_dir),
        fitness_store=GraphFitnessStore(metrics_path),
        fitness_scorer=GraphFitnessScorer(min_runs_for_promotion=2),
    )

    first = kernel.handle_event(TriggerEvent(event_type="market_move", payload={"change_pct": 5, "trace_id": "one"}))
    second = kernel.handle_event(TriggerEvent(event_type="market_move", payload={"change_pct": 6, "trace_id": "two"}))

    assert first["status"] == "ok"
    assert second["status"] == "ok"
    assert kernel.graph_registry.index["g1"]["active"] == "g1_v2"
    assert second["graph_promoted"] == "g1_v2"
    assert kernel.state["events"][-1]["graph_avg_fitness_score"] >= 0.8
    assert GraphFitnessStore(metrics_path).get("g1_v2").runs == 2


def test_kernel_records_failure_and_rolls_back_low_fitness_graph(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    index_path = tmp_path / "index.json"
    graph_dir = tmp_path / "solution_graphs"
    graph_dir.mkdir()
    (graph_dir / "g1_v1.json").write_text(
        """
{
  "metadata": {"purpose": "stable"},
  "nodes": [
    {"node_id": "notify", "action": "notify", "payload": {"channel": "telegram", "message": "v1"}}
  ]
}
""".strip(),
        encoding="utf-8",
    )
    (graph_dir / "g1_v2.json").write_text(
        """
{
  "metadata": {"purpose": "unstable"},
  "nodes": [
    {"node_id": "notify", "action": "notify", "payload": {"channel": "telegram", "message": "v2"}}
  ]
}
""".strip(),
        encoding="utf-8",
    )
    graph_index_path = tmp_path / "graph_index.json"
    graph_index_path.write_text(
        """
{
  "g1": {
    "active": "g1_v2",
    "versions": ["g1_v1", "g1_v2"],
    "experimental": [],
    "history": ["g1_v1", "g1_v2"],
    "failure_count": 0
  }
}
""".strip(),
        encoding="utf-8",
    )
    metrics_path = tmp_path / "graph_metrics.json"

    class FailingNotifyExecutor(AtlasExecutor):
        def execute(self, action, payload):
            if action == "notify":
                return {"status": "failed", "action": action, "payload": payload}
            return super().execute(action, payload)

    kernel = HadesKernel(
        athena=StubAthena(),
        router=Router(),
        executor=FailingNotifyExecutor(),
        state_path=state_path,
        index_path=index_path,
        trigger_engine=TriggerEngine(
            [TriggerRule(event_type="market_move", condition={"change_pct_gt": 3}, graph_id="g1")]
        ),
        graph_registry=GraphRegistry.from_paths(graph_index_path, graph_dir),
        fitness_store=GraphFitnessStore(metrics_path),
        fitness_scorer=GraphFitnessScorer(failure_threshold=0.5, failure_streak_threshold=2),
    )

    first = kernel.handle_event(TriggerEvent(event_type="market_move", payload={"change_pct": 5, "trace_id": "one"}))
    second = kernel.handle_event(TriggerEvent(event_type="market_move", payload={"change_pct": 6, "trace_id": "two"}))

    assert first["status"] == "failed"
    assert second["status"] == "failed"
    assert kernel.graph_registry.index["g1"]["active"] == "g1_v1"
    assert second["graph_failure_recorded"] is True
    assert second["graph_rolled_back_to"] == "g1_v1"


def test_kernel_handle_event_ignores_unmatched_event(tmp_path: Path) -> None:
    kernel = HadesKernel(
        athena=StubAthena(),
        router=Router(),
        executor=AtlasExecutor(),
        state_path=tmp_path / "state.json",
        index_path=tmp_path / "index.json",
        trigger_engine=TriggerEngine([]),
    )

    result = kernel.handle_event(TriggerEvent(event_type="market_move", payload={"change_pct": 1}))

    assert result["status"] == "ignored"


def test_kernel_handle_signal_launches_graph_after_aggregation(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    index_path = tmp_path / "index.json"
    graph_path = tmp_path / "graphs.json"
    graph_path.write_text(
        """
{
  "graphs": {
    "g1": {
      "nodes": [
        {"node_id": "notify", "action": "notify", "payload": {"channel": "telegram", "message": "signal fired"}}
      ]
    }
  }
}
""".strip()
    )
    aggregator = SignalAggregator(
        [
            SignalRule(
                rule_id="fusion",
                signal_types=["market_move", "filing_detected"],
                min_score=2.0,
                within_seconds=300,
                graph_id="g1",
            )
        ]
    )
    kernel = HadesKernel(
        athena=StubAthena(),
        router=Router(),
        executor=AtlasExecutor(),
        state_path=state_path,
        index_path=index_path,
        graph_path=graph_path,
        signal_aggregator=aggregator,
    )

    first = kernel.handle_signal(SignalEvent("market_move", {"score": 1.0}, observed_at=100.0))
    second = kernel.handle_signal(SignalEvent("filing_detected", {"score": 1.0}, observed_at=120.0))

    assert first["status"] == "ignored"
    assert second["status"] == "ok"
    assert second["graph_id"] == "g1"
    assert kernel.state["events"][0]["entry_mode"] == "signal"
    assert kernel.index.lookup("signal:fusion") is not None


def test_kernel_async_graph_run_persists_and_resumes(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    index_path = tmp_path / "index.json"
    graph_path = tmp_path / "graphs.json"
    graph_path.write_text(
        """
{
  "graphs": {
    "g1": {
      "nodes": [
        {
          "node_id": "monitor",
          "action": "clawx_monitor",
          "payload": {
            "task_type": "monitor",
            "objective": "monitor sec filings",
            "schedule": {"every": "15m"}
          }
        },
        {
          "node_id": "notify",
          "action": "notify",
          "payload": {"channel": "telegram", "message": "done"}
        }
      ]
    }
  }
}
""".strip()
    )
    kernel = HadesKernel(
        athena=StubAthena(),
        router=Router(),
        executor=AtlasExecutor(config={"clawx_bridge": "mock"}),
        state_path=state_path,
        index_path=index_path,
        graph_path=graph_path,
        trigger_engine=TriggerEngine(
            [TriggerRule(event_type="market_move", condition={"change_pct_gt": 3}, graph_id="g1")]
        ),
    )

    launch = kernel.handle_event(TriggerEvent(event_type="market_move", payload={"change_pct": 5, "trace_id": "trace-1"}))

    assert launch["status"] == "accepted"
    assert kernel.state["graph_runs"]["trace-1"]["graph_state"]["pending_jobs"] == {"clawx-trace-1-monitor": "monitor"}
    assert kernel.index.lookup("trigger:market_move") is None

    resume = kernel.handle_job_finished(
        {
            "job_id": "clawx-trace-1-monitor",
            "trace_id": "trace-1",
            "result": {"summary": "BTC funding spikes"},
        }
    )

    assert resume["status"] == "ok"
    assert "trace-1" not in kernel.state["graph_runs"]
    assert kernel.index.lookup("trigger:market_move") is not None
    assert kernel.state["events"][-1]["entry_mode"] == "job_finished"
    assert kernel.state["events"][-1]["node_status"]["notify"] == "ok"


def test_planner_graph_executes(tmp_path: Path) -> None:
    registry = CapabilityRegistry(
        {
            "actions": {
                "model_infer": {"providers": ["ollama"], "tiers": ["local"], "async": False},
                "notify": {"providers": ["internal"], "tiers": ["system"], "async": False},
            },
            "models": {"ollama": ["qwen2.5"]},
            "limits": {"max_nodes_per_graph": 5},
            "node_templates": {"analysis_flow": ["model_infer", "notify"]},
        }
    )
    kernel = HadesKernel(
        athena=StubAthena(),
        router=Router(),
        executor=AtlasExecutor(),
        state_path=tmp_path / "state.json",
        index_path=tmp_path / "index.json",
        graph_planner=GraphPlanner(registry),
    )

    result = kernel.handle_intent({"intent": "analyze btc funding"})

    assert result["status"] in ["ok", "accepted"]


def test_llm_planner_graph_executes_with_kernel(tmp_path: Path) -> None:
    registry = CapabilityRegistry(
        {
            "actions": {
                "clawx_monitor": {
                    "capabilities": ["monitor"],
                    "providers": ["clawx"],
                    "tiers": ["clawx"],
                    "async": True,
                },
                "model_infer": {
                    "capabilities": ["analyse", "summarise"],
                    "providers": ["ollama"],
                    "tiers": ["local"],
                    "async": False,
                },
                "notify": {
                    "capabilities": ["notify"],
                    "providers": ["internal"],
                    "tiers": ["system"],
                    "async": False,
                },
            },
            "models": {"ollama": ["qwen2.5"], "clawx": ["clawx-research"]},
            "limits": {"max_nodes_per_graph": 5},
            "node_templates": {"monitor_flow": ["monitor", "analyse", "notify"]},
        }
    )
    planner = LLMGraphPlanner(
        registry,
        proposer=lambda intent, payload: {"graph_id": "llm-monitor-flow", "steps": ["monitor", "analyse", "notify"]},
    )
    kernel = HadesKernel(
        athena=StubAthena(),
        router=Router(),
        executor=AtlasExecutor(config={"clawx_bridge": "mock"}),
        state_path=tmp_path / "state.json",
        index_path=tmp_path / "index.json",
        graph_planner=planner,
    )

    result = kernel.handle_intent({"intent": "monitor btc funding", "payload": {"trace_id": "llm-1"}})

    assert result["status"] == "accepted"
    assert result["graph_id"] == "llm-monitor-flow"
    assert kernel.state["events"][0]["entry_metadata"]["planner"] == "llm_constrained"


def test_build_default_kernel_uses_ollama_proposer(tmp_path: Path, monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"response": '{"graph_id":"ollama-monitor-flow","steps":["monitor","analyse","notify"]}'}

    def fake_post(url, json, timeout):
        return FakeResponse()

    monkeypatch.setattr("atlas.proposers.ollama_proposer.requests.post", fake_post)
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "patterns.json").write_text(
        '{"routes": {}, "capabilities": {}}',
        encoding="utf-8",
    )
    (vault / "capabilities.json").write_text(
        """
{
  "actions": {
    "clawx_monitor": {
      "capabilities": ["monitor"],
      "providers": ["clawx"],
      "tiers": ["clawx"],
      "async": true
    },
    "model_infer": {
      "capabilities": ["analyse", "summarise"],
      "providers": ["ollama"],
      "tiers": ["local"],
      "async": false
    },
    "notify": {
      "capabilities": ["notify"],
      "providers": ["internal"],
      "tiers": ["system"],
      "async": false
    }
  },
  "models": {
    "ollama": ["qwen2.5"],
    "clawx": ["clawx-research"]
  },
  "limits": {
    "max_nodes_per_graph": 5
  },
  "planner": {
    "model": "qwen2.5",
    "timeout": 30,
    "url": "http://localhost:11434/api/generate"
  },
  "node_templates": {
    "monitor_flow": ["monitor", "analyse", "notify"]
  }
}
""".strip(),
        encoding="utf-8",
    )
    (vault / "triggers.json").write_text('{"rules": []}', encoding="utf-8")
    (vault / "signals.json").write_text('{"rules": []}', encoding="utf-8")

    kernel = build_default_kernel(tmp_path)

    result = kernel.handle_intent({"intent": "monitor btc funding", "payload": {"trace_id": "ollama-1"}})

    assert isinstance(kernel.graph_planner, LLMGraphPlanner)
    assert result["status"] == "accepted"
    assert result["graph_id"] == "ollama-monitor-flow"
    assert kernel.state["events"][0]["entry_metadata"]["planner"] == "llm_constrained"
