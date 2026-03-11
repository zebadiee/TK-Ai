"""Deterministic model routing policy for memory misses."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ModelRoute:
    backend: str
    model: str
    max_tokens: int
    max_latency_ms: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ModelRouter:
    """Selects an allowed model tier for genuine memory misses."""

    def resolve(self, intent: str, context: dict[str, Any] | None = None) -> ModelRoute:
        route_context = context if isinstance(context, dict) else {}
        payload = route_context.get("payload", {})
        if isinstance(payload, dict) and payload.get("long_running"):
            return ModelRoute(
                backend="clawx",
                model="clawx-research",
                max_tokens=768,
                max_latency_ms=5000,
                reason="research_daemon",
            )
        problem_size = self._classify_problem(intent, route_context)

        if problem_size == "small":
            return ModelRoute(
                backend="local",
                model="local-small",
                max_tokens=256,
                max_latency_ms=1000,
                reason="small_problem",
            )

        if problem_size == "medium":
            return ModelRoute(
                backend="free",
                model="free-standard",
                max_tokens=512,
                max_latency_ms=3000,
                reason="medium_problem",
            )

        return ModelRoute(
            backend="paid",
            model="paid-premium",
            max_tokens=1024,
            max_latency_ms=6000,
            reason="large_problem",
        )

    def _classify_problem(self, intent: str, context: dict[str, Any]) -> str:
        explicit_size = context.get("problem_size")
        if explicit_size in {"small", "medium", "large"}:
            return str(explicit_size)

        if context.get("requires_paid"):
            return "large"

        token_count = len(intent.split())
        payload = context.get("payload", {})
        payload_size = len(payload) if isinstance(payload, dict) else 0

        if token_count <= 3 and payload_size <= 2:
            return "small"
        if token_count <= 8 and payload_size <= 5:
            return "medium"
        return "large"
