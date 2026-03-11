from hades.signals import SignalAggregator, SignalEvent, SignalRule


def test_signal_aggregator_emits_when_threshold_met():
    aggregator = SignalAggregator(
        [
            SignalRule(
                rule_id="fusion",
                signal_types=["market_move", "filing_detected"],
                min_score=2.0,
                within_seconds=300,
                graph_id="market_alert_graph",
            )
        ]
    )

    assert aggregator.ingest(SignalEvent("market_move", {"score": 1.0}, observed_at=100.0)) is None

    aggregate = aggregator.ingest(
        SignalEvent("filing_detected", {"score": 1.0}, observed_at=120.0)
    )

    assert aggregate is not None
    assert aggregate.graph_id == "market_alert_graph"
    assert aggregate.rule_id == "fusion"
    assert aggregate.score == 2.0


def test_signal_aggregator_ignores_incomplete_signal_set():
    aggregator = SignalAggregator(
        [
            SignalRule(
                rule_id="fusion",
                signal_types=["market_move", "filing_detected"],
                min_score=2.0,
                within_seconds=300,
                graph_id="market_alert_graph",
            )
        ]
    )

    aggregate = aggregator.ingest(SignalEvent("market_move", {"score": 1.0}, observed_at=100.0))

    assert aggregate is None
