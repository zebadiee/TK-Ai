import json
from pathlib import Path
from types import SimpleNamespace

from modules.clawx_engine.clawx_engine import ClawXEngine
from modules.clawx_engine.scheduler_policy_rules import SchedulerPolicyRules
from modules.clawx_engine.scheduler_policy_writer import SchedulerPolicyWriter
from modules.clawx_engine.signal_adapter import SignalAdapter


class RecordingWriter:
    def __init__(self) -> None:
        self.calls = []

    def recommend_running(self, reason: str, duration: int):
        payload = {"state": "running", "reason": reason, "duration_hours": duration}
        self.calls.append(payload)
        return payload

    def recommend_stop(self, reason: str):
        payload = {"state": "stopped", "reason": reason, "duration_hours": 0}
        self.calls.append(payload)
        return payload


class RecordingSignalEngine:
    def __init__(self) -> None:
        self.signals = []

    def receive(self, signal):
        self.signals.append(signal)


def test_scheduler_policy_rules_recommend_running_on_recent_anomalies() -> None:
    now = 1_700_000_000
    writer = RecordingWriter()
    rules = SchedulerPolicyRules(
        [
            {"type": "funding_rate_anomaly", "severity": "high", "timestamp": now - 60},
            {"type": "funding_rate_anomaly", "severity": "high", "timestamp": now - 120},
            {"type": "funding_rate_anomaly", "severity": "high", "timestamp": now - 180},
        ],
        [],
        writer,
        now_fn=lambda: now,
    )

    result = rules.evaluate()

    assert result == writer.calls[-1]
    assert result["state"] == "running"
    assert result["duration_hours"] == 6


def test_scheduler_policy_rules_recommend_running_on_active_investigations() -> None:
    now = 1_700_000_000
    writer = RecordingWriter()
    evidence = [{"timestamp": now - 120, "content": {}} for _ in range(10)]
    rules = SchedulerPolicyRules([], evidence, writer, now_fn=lambda: now)

    result = rules.evaluate()

    assert result == writer.calls[-1]
    assert result["state"] == "running"
    assert result["duration_hours"] == 3


def test_scheduler_policy_rules_recommend_stop_on_quiet_period() -> None:
    now = 1_700_000_000
    writer = RecordingWriter()
    rules = SchedulerPolicyRules([], [], writer, now_fn=lambda: now)

    result = rules.evaluate()

    assert result == writer.calls[-1]
    assert result["state"] == "stopped"


def test_scheduler_policy_writer_persists_json_policy(tmp_path: Path) -> None:
    writer = SchedulerPolicyWriter(tmp_path / "scheduler_policy.json")

    writer.recommend_running("Recent anomaly signals detected", duration=6)
    data = json.loads((tmp_path / "scheduler_policy.json").read_text(encoding="utf-8"))

    assert data["state"] == "running"
    assert data["duration_hours"] == 6
    assert data["source"] == "clawx"


def test_clawx_engine_updates_policy_via_rules() -> None:
    signal_engine = RecordingSignalEngine()
    writer = RecordingWriter()
    signal_history: list[dict] = []
    evidence_history: list[dict] = []
    rules = SchedulerPolicyRules(signal_history, evidence_history, writer, now_fn=lambda: 1_700_000_000)
    engine = ClawXEngine(
        signal_adapter=SignalAdapter(signal_engine),
        scheduler_policy_rules=rules,
    )
    engine._signal_history = signal_history
    engine._evidence_history = evidence_history

    for trace_id in ("one", "two", "three"):
        engine.process_event(
            SimpleNamespace(
                type="observation",
                content={"exchange": "binance", "funding_rate": 0.23},
                trace_id=trace_id,
                timestamp=1_699_999_900,
            )
        )

    assert any(signal["type"] == "funding_rate_anomaly" for signal in signal_engine.signals)
    assert writer.calls[-1]["state"] == "running"
    assert writer.calls[-1]["duration_hours"] == 6
