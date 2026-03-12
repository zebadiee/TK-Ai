from tools import tkai_ui


class StubResult:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode


def test_parse_shell_command_handles_slash_commands_and_aliases() -> None:
    assert tkai_ui.parse_shell_command("/nav nodes") == ["nav", "nodes"]
    assert tkai_ui.parse_shell_command("/cross-talk") == ["autonomy", "--once", "--cooldown", "0"]
    assert tkai_ui.parse_shell_command("/learn") == ["burnin", "--once"]


def test_launch_builds_surface_command() -> None:
    calls: list[list[str]] = []

    def runner(command, cwd=None, check=False):
        calls.append(command)
        return StubResult(0)

    result = tkai_ui.launch("nav", ["nodes"], runner=runner)

    assert result == 0
    assert calls == [[tkai_ui.sys.executable, str(tkai_ui.SURFACES["nav"]), "nodes"]]


def test_shell_exits_cleanly_on_keyboard_interrupt(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda prompt="": (_ for _ in ()).throw(KeyboardInterrupt()))

    assert tkai_ui.shell() == 0


def test_surfaces_lines_include_core_interfaces() -> None:
    lines = tkai_ui.surfaces_lines()

    assert any("mc: TK-AI Mission Control TUI" in line for line in lines)
    assert any("clawx: ClawX operator console" in line for line in lines)
    assert any("acme-status: ACME and TK-Ai integration health" in line for line in lines)
    assert any("acme-sync: Export TK-Ai snapshot into ACME runtime" in line for line in lines)


def test_status_lines_include_signal_and_service_summary(monkeypatch, tmp_path) -> None:
    signals = tmp_path / "signals.jsonl"
    evidence = tmp_path / "evidence.jsonl"
    signals.write_text('{"type":"gpu_inference_exploration"}\n', encoding="utf-8")
    evidence.write_text('{"signal_id":"sig-1","severity":"low"}\n', encoding="utf-8")
    monkeypatch.setattr(tkai_ui, "SIGNALS", signals)
    monkeypatch.setattr(tkai_ui, "EVIDENCE", evidence)
    monkeypatch.setattr(tkai_ui, "service_status", lambda name: "active" if "investigation" in name else "activating")

    lines = tkai_ui.status_lines()

    assert "investigation: active" in lines
    assert "scheduler: activating" in lines
    assert "last_signal: gpu_inference_exploration" in lines
    assert "last_evidence_signal: sig-1" in lines


def test_main_reports_nonzero_child_exit(monkeypatch, capsys) -> None:
    monkeypatch.setattr(tkai_ui, "launch", lambda surface, args, runner=tkai_ui.subprocess.run: 3)
    monkeypatch.setattr(tkai_ui.sys, "argv", ["tkai_ui.py", "nav", "nodes"])

    result = tkai_ui.main()
    stderr = capsys.readouterr().err

    assert result == 3
    assert "[tkai-ui] nav exited with code 3" in stderr
