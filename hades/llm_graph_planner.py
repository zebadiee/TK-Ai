"""Constrained LLM-style graph planner with semantic validation."""

from __future__ import annotations

import json
from typing import Any, Callable

from hades.capabilities import CapabilityRegistry
from hades.graph_planner import GraphPlanner, _normalize_intent
from hades.task_graph import TaskGraph, TaskNode

ProposalSource = Callable[[str, dict[str, Any]], dict[str, Any] | list[str] | str | None]


class LLMGraphPlanner(GraphPlanner):
    """Plans graphs from model-like proposals while staying inside registry constraints."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        proposer: ProposalSource | None = None,
        fallback_planner: GraphPlanner | None = None,
        fallback_on_invalid: bool = True,
    ) -> None:
        super().__init__(registry)
        self.proposer = proposer
        self.fallback_planner = fallback_planner or GraphPlanner(registry)
        self.fallback_on_invalid = fallback_on_invalid

    def plan_graph(self, intent: str, payload: dict[str, Any] | None = None) -> TaskGraph:
        base_payload = payload if isinstance(payload, dict) else {}
        try:
            proposal = self._propose(intent, base_payload)
            semantic_steps, graph_id = self._extract_steps(proposal, intent)
            self._validate_semantic_steps(semantic_steps)

            actions = self._resolve_steps(semantic_steps)
            self._validate_actions(actions)
            if len(actions) != len(semantic_steps):
                raise ValueError("LLM proposal could not be resolved to a complete safe action list")

            nodes = [
                TaskNode(
                    node_id=f"n{index + 1}",
                    action=action,
                    payload=self._node_payload(action, intent, base_payload),
                )
                for index, action in enumerate(actions)
            ]
            return TaskGraph(
                graph_id=graph_id,
                nodes=nodes,
                metadata={
                    "planner": "llm_constrained",
                    "intent": intent,
                    "semantic_steps": semantic_steps,
                },
            )
        except ValueError:
            if not self.fallback_on_invalid:
                raise
            return self.fallback_planner.plan_graph(intent, base_payload)

    def _propose(self, intent: str, payload: dict[str, Any]) -> dict[str, Any] | list[str] | str | None:
        if self.proposer is None:
            return None
        return self.proposer(intent, payload)

    def _extract_steps(
        self,
        proposal: dict[str, Any] | list[str] | str | None,
        intent: str,
    ) -> tuple[list[str], str]:
        default_graph_id = f"llm-{_normalize_intent(intent).replace(' ', '-') or 'noop'}"
        if proposal is None:
            raise ValueError("No LLM proposal available")

        if isinstance(proposal, str):
            stripped = proposal.strip()
            if not stripped:
                raise ValueError("Empty LLM proposal")
            if stripped.startswith("{") or stripped.startswith("["):
                try:
                    proposal = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError("Invalid JSON LLM proposal") from exc
            else:
                proposal = [part.strip() for part in stripped.split("->") if part.strip()]

        if isinstance(proposal, list):
            steps = [self._normalize_step(item) for item in proposal]
            return steps, default_graph_id

        if isinstance(proposal, dict):
            raw_steps = proposal.get("steps", [])
            if not isinstance(raw_steps, list):
                raise ValueError("LLM proposal steps must be a list")
            graph_id = _normalize_intent(str(proposal.get("graph_id", default_graph_id))).replace(" ", "-")
            return [self._normalize_step(item) for item in raw_steps], graph_id or default_graph_id

        raise ValueError("Unsupported LLM proposal type")

    def _validate_semantic_steps(self, steps: list[str]) -> None:
        if not steps:
            raise ValueError("LLM proposal did not include any steps")

        max_nodes = self.registry.limit("max_nodes_per_graph", default=5)
        if max_nodes > 0 and len(steps) > max_nodes:
            raise ValueError(f"LLM proposal exceeds node limit: {len(steps)} > {max_nodes}")

        allowed_actions = set(self.registry.allowed_actions())
        unknown = [
            step
            for step in steps
            if step not in allowed_actions and self.semantic_index.resolve_best(step) is None
        ]
        if unknown:
            raise ValueError(f"Unsupported semantic steps in proposal: {unknown}")

    def _normalize_step(self, step: Any) -> str:
        return _normalize_intent(str(step))
