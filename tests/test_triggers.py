from hades.triggers import TriggerEngine, TriggerEvent, TriggerRule


def test_trigger_rule_matches():
    engine = TriggerEngine(
        [
            TriggerRule(
                event_type="market_move",
                condition={"change_pct_gt": 3},
                graph_id="g1",
            )
        ]
    )

    match = engine.match(TriggerEvent(event_type="market_move", payload={"change_pct": 4}))

    assert match is not None
    assert match.graph_id == "g1"
    assert match.metadata["payload"]["change_pct"] == 4


def test_trigger_no_match():
    engine = TriggerEngine([])

    match = engine.match(TriggerEvent(event_type="market_move", payload={"change_pct": 1}))

    assert match is None
