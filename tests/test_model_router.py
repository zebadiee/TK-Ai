from hades.model_router import ModelRouter


def test_model_router_routes_small_problem_to_local():
    router = ModelRouter()

    route = router.resolve("ping user", {"payload": {"trace_id": "1"}})

    assert route.backend == "local"
    assert route.model == "local-small"
    assert route.reason == "small_problem"


def test_model_router_routes_medium_problem_to_free():
    router = ModelRouter()

    route = router.resolve(
        "summarize market headlines today",
        {"payload": {"trace_id": "1", "topic": "markets", "window": "1d"}},
    )

    assert route.backend == "free"
    assert route.model == "free-standard"
    assert route.reason == "medium_problem"


def test_model_router_routes_large_problem_to_paid():
    router = ModelRouter()

    route = router.resolve(
        "build a comprehensive multi-source research brief with comparisons and risk notes",
        {"payload": {"trace_id": "1", "topic": "energy", "window": "30d", "region": "global"}},
    )

    assert route.backend == "paid"
    assert route.model == "paid-premium"
    assert route.reason == "large_problem"


def test_model_router_routes_long_running_work_to_clawx():
    router = ModelRouter()

    route = router.resolve(
        "monitor sec filings",
        {"payload": {"long_running": True}},
    )

    assert route.backend == "clawx"
    assert route.model == "clawx-research"
    assert route.reason == "research_daemon"
