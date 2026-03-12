import json
from pathlib import Path

from tools import clawx_scheduler, mission_runner


class StubResult:
    def __init__(self, stdout: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.returncode = returncode


def test_process_signals_supports_mission_actions() -> None:
    calls: list[list[str]] = []

    def runner(command, **kwargs):
        calls.append(command)
        return StubResult(stdout="", returncode=0)

    original = clawx_scheduler.RULES.copy()
    clawx_scheduler.RULES["mission_signal"] = [{"mission": "control_plane_health"}]
    try:
        invoked = clawx_scheduler.process_signals([{"type": "mission_signal"}], runner=runner)
    finally:
        clawx_scheduler.RULES.clear()
        clawx_scheduler.RULES.update(original)

    assert invoked == [("mission_signal", "control_plane_health")]
    assert calls[0][-1] == "control_plane_health"


def test_run_mission_skips_step_when_service_is_active(tmp_path: Path) -> None:
    mission_path = tmp_path / "missions.json"
    mission_path.write_text(
        json.dumps(
            {
                "guarded_mission": {
                    "steps": [
                        {
                            "agent": "investigation_agent",
                            "args": ["--once"],
                            "skip_if_service_active": "tkai-investigation.service",
                        },
                        {
                            "agent": "cluster_doctor",
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    def runner(command, **kwargs):
        calls.append(command)
        if command[:3] == ["systemctl", "--user", "is-active"]:
            return StubResult(stdout="active\n")
        return StubResult(stdout="", returncode=0)

    results = mission_runner.run_mission("guarded_mission", missions_path=mission_path, runner=runner)

    assert results == [
        {
            "agent": "investigation_agent",
            "args": ["--once"],
            "returncode": 0,
            "skipped": True,
            "skip_if_service_active": "tkai-investigation.service",
        },
        {
            "agent": "cluster_doctor",
            "args": [],
            "returncode": 0,
        },
    ]
    assert calls[-1][-1] == "cluster_doctor"
