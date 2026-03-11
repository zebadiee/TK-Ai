"""Deterministic graph planning under capability constraints."""

from __future__ import annotations

from typing import Any

from hades.capabilities import CapabilityRegistry
from hades.semantic_capabilities import SemanticCapabilityIndex
from hades.task_graph import TaskGraph, TaskNode


def _normalize_intent(intent: str) -> str:
    return " ".join(intent.lower().strip().split())


class GraphPlanner:
    """Builds safe task graphs from intents using registry-constrained templates."""

    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry
        self.semantic_index = SemanticCapabilityIndex(registry)

    def _plan_actions(self, intent: str) -> list[str]:
        normalized = _normalize_intent(intent)

        if self._is_monitoring_intent(normalized):
            template = self.registry.node_template("monitor_flow")
            if template:
                return self._resolve_steps(template)
            return self._resolve_steps(["monitor", "analyse", "notify"])

        template = self.registry.node_template("analysis_flow")
        if template:
            return self._resolve_steps(template)

        return self._resolve_steps(["analyse"]) or self._resolve_steps(["noop"])

    def _validate_actions(self, actions: list[str]) -> None:
        allowed = set(self.registry.allowed_actions())
        invalid = [action for action in actions if action not in allowed]
        if invalid:
            raise ValueError(f"Unsupported actions in plan: {invalid}")

        max_nodes = self.registry.limit("max_nodes_per_graph", default=5)
        if max_nodes > 0 and len(actions) > max_nodes:
            raise ValueError(f"Planned graph exceeds node limit: {len(actions)} > {max_nodes}")

    def plan_graph(self, intent: str, payload: dict[str, Any] | None = None) -> TaskGraph:
        base_payload = payload if isinstance(payload, dict) else {}
        actions = self._plan_actions(intent)
        self._validate_actions(actions)
        if not actions:
            raise ValueError("Planner could not produce a safe action list")

        nodes = [
            TaskNode(node_id=f"n{index + 1}", action=action, payload=self._node_payload(action, intent, base_payload))
            for index, action in enumerate(actions)
        ]
        graph_id = f"planned-{_normalize_intent(intent).replace(' ', '-') or 'noop'}"
        return TaskGraph(
            graph_id=graph_id,
            nodes=nodes,
            metadata={"planner": "deterministic", "intent": intent},
        )

    def _node_payload(self, action: str, intent: str, payload: dict[str, Any]) -> dict[str, Any]:
        if action == "model_infer":
            capability = self.registry.get_action("model_infer")
            provider = capability.providers[0] if capability.providers else "ollama"
            tier = capability.tiers[0] if capability.tiers else "local"
            model = self.registry.allowed_models(provider)
            return {
                "prompt": intent,
                "provider": provider,
                "model_route": {
                    "backend": self._tier_backend(tier),
                    "model": model[0] if model else "local-small",
                    "max_tokens": 256 if tier == "local" else 512,
                    "max_latency_ms": 1000 if tier == "local" else 3000,
                    "reason": "planned_graph",
                },
            }

        if action == "notify":
            return {
                "channel": "console",
                "message": f"Planned graph completed for: {intent}",
            }

        if action == "clawx_monitor":
            task_type = "monitor" if self._is_monitoring_intent(_normalize_intent(intent)) else "once"
            return {
                "task_type": task_type,
                "objective": intent,
                "sources": payload.get("sources", ["auto"]),
                "schedule": payload.get("schedule", {"every": "15m"} if task_type == "monitor" else {}),
                "delivery": payload.get("delivery", {"channels": ["console"], "format": "summary"}),
            }

        return {}

    def _resolve_steps(self, steps: list[str]) -> list[str]:
        allowed = set(self.registry.allowed_actions())
        resolved: list[str] = []
        for step in steps:
            normalized = _normalize_intent(str(step))
            if normalized in allowed:
                resolved.append(normalized)
                continue

            action = self.semantic_index.resolve_best(normalized)
            if action is not None:
                resolved.append(action)
        return resolved

    def _is_monitoring_intent(self, normalized_intent: str) -> bool:
        keywords = {"monitor", "watch", "track", "alert", "notify", "every", "daily", "cron"}
        return any(keyword in normalized_intent.split() for keyword in keywords)

    def _tier_backend(self, tier: str) -> str:
        if tier in {"local", "free", "paid", "clawx"}:
            return tier
        return "local"
