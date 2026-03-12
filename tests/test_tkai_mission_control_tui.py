from pathlib import Path

from tools import tkai_mission_control_tui


class StubResult:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode


def test_run_once_invokes_mission_control_script() -> None:
    calls: list[tuple[list[str], Path]] = []

    def runner(command, cwd=None, check=False):
        calls.append((command, cwd))
        return StubResult(0)

    result = tkai_mission_control_tui.run_once(runner=runner)

    assert result == 0
    assert calls == [
        (
            [tkai_mission_control_tui.sys.executable, str(tkai_mission_control_tui.MISSION_CONTROL)],
            tkai_mission_control_tui.ROOT,
        )
    ]
