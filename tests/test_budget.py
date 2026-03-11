from hades.budget import BudgetLedger
from hades.model_router import ModelRoute


def test_budget_ledger_downgrades_paid_route_when_paid_disabled():
    ledger = BudgetLedger({"allow_paid": False})
    route = ModelRoute(
        backend="paid",
        model="paid-premium",
        max_tokens=1024,
        max_latency_ms=6000,
        reason="large_problem",
    )

    adjusted, decision = ledger.enforce(route)

    assert adjusted is not None
    assert adjusted.backend == "free"
    assert adjusted.model == "free-standard"
    assert adjusted.max_tokens == 512
    assert decision.reason == "paid_downgraded"


def test_budget_ledger_can_block_all_models():
    ledger = BudgetLedger({"models_enabled": False})
    route = ModelRoute(
        backend="local",
        model="local-small",
        max_tokens=256,
        max_latency_ms=1000,
        reason="small_problem",
    )

    adjusted, decision = ledger.enforce(route)

    assert adjusted is None
    assert decision.allow is False
    assert decision.reason == "models_disabled"


def test_budget_ledger_can_block_clawx_provider():
    ledger = BudgetLedger({"allow_clawx": False})
    route = ModelRoute(
        backend="clawx",
        model="clawx-research",
        max_tokens=768,
        max_latency_ms=5000,
        reason="research_daemon",
    )

    adjusted, decision = ledger.enforce(route)

    assert adjusted is None
    assert decision.reason == "clawx_disabled"
