from types import SimpleNamespace

from modules.clawx_engine.clawx_engine import ClawXEngine
from modules.clawx_engine.clawx_subscriber import ClawXSubscriber
from modules.clawx_engine.signal_adapter import SignalAdapter


class RecordingSignalEngine:
    def __init__(self) -> None:
        self.signals = []

    def receive(self, signal):
        self.signals.append(signal)


def test_clawx_engine_emits_anomaly_signal_for_high_funding_rate() -> None:
    signal_engine = RecordingSignalEngine()
    engine = ClawXEngine(signal_adapter=SignalAdapter(signal_engine))

    engine.process_event(
        SimpleNamespace(
            type="observation",
            content={"exchange": "binance", "funding_rate": 0.23},
            trace_id="trace-1",
        )
    )

    assert len(signal_engine.signals) == 1
    assert signal_engine.signals[0]["type"] == "funding_rate_anomaly"
    assert signal_engine.signals[0]["trace_id"] == "trace-1"


def test_clawx_engine_emits_low_confidence_claim_signal() -> None:
    signal_engine = RecordingSignalEngine()
    engine = ClawXEngine(signal_adapter=SignalAdapter(signal_engine))

    engine.process_event(
        SimpleNamespace(
            type="claim",
            claim_id="claim-1",
            confidence=0.2,
            trace_id="trace-2",
        )
    )

    assert len(signal_engine.signals) == 1
    assert signal_engine.signals[0]["type"] == "low_confidence_claim"
    assert signal_engine.signals[0]["payload"]["claim_id"] == "claim-1"


def test_clawx_subscriber_swallows_engine_errors(capsys) -> None:
    class FailingEngine:
        def process_event(self, event) -> None:
            raise RuntimeError("boom")

    subscriber = ClawXSubscriber(FailingEngine())
    subscriber.on_event(SimpleNamespace(type="observation", content={}))

    assert "subscriber error" in capsys.readouterr().out


def test_clawx_engine_emits_pattern_signal_after_three_observations() -> None:
    signal_engine = RecordingSignalEngine()
    engine = ClawXEngine(signal_adapter=SignalAdapter(signal_engine))

    for rate in (0.1, 0.15, 0.18):
        engine.process_event(
            SimpleNamespace(
                type="observation",
                content={"exchange": "binance", "funding_rate": rate},
                trace_id="trace-3",
            )
        )

    assert signal_engine.signals[-1]["type"] == "funding_pattern_detected"
