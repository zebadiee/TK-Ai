import json
from pathlib import Path

from modules.clawx_engine.scheduler_policy_writer import SchedulerPolicyWriter
from tools import tkai_policy_daemon


class StubResult:
    def __init__(self, stdout: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.returncode = returncode


def test_policy_writer_persists_desired_state(tmp_path: Path) -> None:
    writer = SchedulerPolicyWriter(tmp_path / "scheduler_policy.json")

    writer.recommend_running("Recent anomaly signals detected", duration=6)
    data = json.loads((tmp_path / "scheduler_policy.json").read_text(encoding="utf-8"))

    assert data["desired_state"] == "running"
    assert data["updated_by"] == "clawx"


def test_apply_policy_starts_scheduler_when_policy_requests_running(tmp_path: Path) -> None:
    policy_file = tmp_path / "scheduler_policy.json"
    policy_file.write_text(json.dumps({"desired_state": "running"}), encoding="utf-8")
    calls: list[list[str]] = []

    def runner(command, **kwargs):
        calls.append(command)
        if command == tkai_policy_daemon.STATUS_CMD:
            return StubResult(stdout="inactive\n")
        return StubResult(stdout="")

    result = tkai_policy_daemon.apply_policy(path=policy_file, runner=runner)

    assert result == "started"
    assert tkai_policy_daemon.START_CMD in calls


def test_apply_policy_stops_scheduler_when_policy_requests_stop(tmp_path: Path) -> None:
    policy_file = tmp_path / "scheduler_policy.json"
    policy_file.write_text(json.dumps({"desired_state": "stopped"}), encoding="utf-8")
    calls: list[list[str]] = []

    def runner(command, **kwargs):
        calls.append(command)
        if command == tkai_policy_daemon.STATUS_CMD:
            return StubResult(stdout="active\n")
        return StubResult(stdout="")

    result = tkai_policy_daemon.apply_policy(path=policy_file, runner=runner)

    assert result == "stopped"
    assert tkai_policy_daemon.STOP_CMD in calls


def test_apply_policy_noops_when_state_already_matches(tmp_path: Path) -> None:
    policy_file = tmp_path / "scheduler_policy.json"
    policy_file.write_text(json.dumps({"desired_state": "running"}), encoding="utf-8")

    def runner(command, **kwargs):
        if command == tkai_policy_daemon.STATUS_CMD:
            return StubResult(stdout="active\n")
        return StubResult(stdout="")

    assert tkai_policy_daemon.apply_policy(path=policy_file, runner=runner) == "noop"
