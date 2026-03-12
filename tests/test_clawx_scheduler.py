import json
from pathlib import Path

from tools import clawx_scheduler


class StubResult:
    def __init__(self, stdout: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.returncode = returncode


def test_read_new_signals_returns_unread_records(tmp_path: Path) -> None:
    signal_path = tmp_path / "signals.jsonl"
    signal_path.write_text(
        "\n".join(
            [
                json.dumps({"signal_id": "sig-1", "type": "funding_rate_anomaly"}),
                json.dumps({"signal_id": "sig-2", "type": "latency_spike"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    signals, offset = clawx_scheduler.read_new_signals(1, path=signal_path)

    assert signals == [{"signal_id": "sig-2", "type": "latency_spike"}]
    assert offset == 2


def test_run_once_invokes_cluster_doctor_when_investigation_service_is_active(monkeypatch, tmp_path: Path) -> None:
    signal_path = tmp_path / "signals.jsonl"
    state_path = tmp_path / "scheduler_state.json"
    signal_path.write_text(json.dumps({"signal_id": "sig-1", "type": "latency_spike"}) + "\n", encoding="utf-8")
    calls: list[list[str]] = []

    def runner(command, **kwargs):
        calls.append(command)
        if command[:3] == ["systemctl", "--user", "is-active"]:
            return StubResult(stdout="active\n")
        return StubResult(stdout="", returncode=0)

    invoked = clawx_scheduler.run_once(state_path=state_path, signal_path=signal_path, runner=runner)

    assert invoked == [("latency_spike", "atlas_latency_investigation")]
    assert calls[-1][-1] == "atlas_latency_investigation"
    assert json.loads(state_path.read_text(encoding="utf-8")) == {"last_offset": 1}


def test_run_once_invokes_investigation_when_service_is_inactive(monkeypatch, tmp_path: Path) -> None:
    signal_path = tmp_path / "signals.jsonl"
    state_path = tmp_path / "scheduler_state.json"
    signal_path.write_text(json.dumps({"signal_id": "sig-1", "type": "funding_rate_anomaly"}) + "\n", encoding="utf-8")
    calls: list[list[str]] = []

    def runner(command, **kwargs):
        calls.append(command)
        if command[:3] == ["systemctl", "--user", "is-active"]:
            return StubResult(stdout="inactive\n")
        return StubResult(stdout="", returncode=0)

    invoked = clawx_scheduler.run_once(state_path=state_path, signal_path=signal_path, runner=runner)

    assert invoked == [("funding_rate_anomaly", "funding_signal_triage")]
    assert calls[-1][-1] == "funding_signal_triage"


def test_run_once_advances_offset_without_reinvoking_processed_lines(tmp_path: Path) -> None:
    signal_path = tmp_path / "signals.jsonl"
    state_path = tmp_path / "scheduler_state.json"
    signal_path.write_text(json.dumps({"signal_id": "sig-1", "type": "router_test"}) + "\n", encoding="utf-8")
    state_path.write_text(json.dumps({"last_offset": 1}), encoding="utf-8")
    calls: list[list[str]] = []

    def runner(command, **kwargs):
        calls.append(command)
        return StubResult(stdout="", returncode=0)

    invoked = clawx_scheduler.run_once(state_path=state_path, signal_path=signal_path, runner=runner)

    assert invoked == []
    assert calls == []
