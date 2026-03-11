"""Budget policy for model routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hades.model_router import ModelRoute


@dataclass
class BudgetDecision:
    allow: bool
    tier: str
    reason: str
    max_tokens: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "allow": self.allow,
            "tier": self.tier,
            "reason": self.reason,
            "max_tokens": self.max_tokens,
        }


class BudgetLedger:
    """Applies token and tier policy before any model execution."""

    DEFAULT_MODELS = {
        "local": "local-small",
        "free": "free-standard",
        "paid": "paid-premium",
        "clawx": "clawx-research",
    }

    def __init__(self, policy: dict[str, Any] | None = None) -> None:
        config = policy if isinstance(policy, dict) else {}
        self.models_enabled = bool(config.get("models_enabled", True))
        self.allow_paid = bool(config.get("allow_paid", False))
        self.allow_clawx = bool(config.get("allow_clawx", True))
        self.max_model_tokens = int(config.get("max_model_tokens", 768))
        self.free_max_tokens = int(config.get("free_max_tokens", 512))
        self.local_max_tokens = int(config.get("local_max_tokens", 256))
        self.clawx_max_tokens = int(config.get("clawx_max_tokens", 768))

    def decide(
        self,
        route: ModelRoute,
        context: dict[str, Any] | None = None,
    ) -> BudgetDecision:
        route_context = context if isinstance(context, dict) else {}
        if not self.models_enabled or route_context.get("skip_models"):
            return BudgetDecision(
                allow=False,
                tier="blocked",
                reason="models_disabled",
                max_tokens=0,
            )

        if route.backend == "paid" and not self.allow_paid:
            capped_tokens = min(route.max_tokens, self.free_max_tokens, self.max_model_tokens)
            return BudgetDecision(
                allow=True,
                tier="free",
                reason="paid_downgraded",
                max_tokens=capped_tokens,
            )

        if route.backend == "clawx" and not self.allow_clawx:
            return BudgetDecision(
                allow=False,
                tier="blocked",
                reason="clawx_disabled",
                max_tokens=0,
            )

        tier_caps = {
            "local": self.local_max_tokens,
            "free": self.free_max_tokens,
            "paid": self.max_model_tokens,
            "clawx": self.clawx_max_tokens,
        }
        max_tokens = min(route.max_tokens, tier_caps.get(route.backend, self.max_model_tokens))
        return BudgetDecision(
            allow=True,
            tier=route.backend,
            reason="within_budget",
            max_tokens=max_tokens,
        )

    def enforce(
        self,
        route: ModelRoute,
        context: dict[str, Any] | None = None,
    ) -> tuple[ModelRoute | None, BudgetDecision]:
        decision = self.decide(route, context)
        if not decision.allow:
            return None, decision

        model = self.DEFAULT_MODELS.get(decision.tier, route.model)
        adjusted_route = ModelRoute(
            backend=decision.tier,
            model=model,
            max_tokens=decision.max_tokens,
            max_latency_ms=route.max_latency_ms,
            reason=route.reason,
        )
        return adjusted_route, decision
