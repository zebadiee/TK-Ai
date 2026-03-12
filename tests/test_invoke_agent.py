import json
from pathlib import Path

from tools import invoke_agent


class StubResult:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode


def test_build_command_runs_local_entrypoint(monkeypatch) -> None:
    monkeypatch.setattr(invoke_agent, "local_node", lambda: "hades")

    command = invoke_agent.build_command(
        "cluster_doctor",
        ["--once"],
        {
            "cluster_doctor": {
                "node": "hades",
                "entrypoint": "tools/cluster_doctor.py",
            }
        },
    )

    assert command[0] == invoke_agent.sys.executable
    assert command[1].endswith("/tools/cluster_doctor.py")
    assert command[2:] == ["--once"]


def test_build_command_wraps_remote_entrypoint_in_ssh(monkeypatch) -> None:
    monkeypatch.setattr(invoke_agent, "local_node", lambda: "hades")

    command = invoke_agent.build_command(
        "cluster_doctor",
        ["--tail"],
        {
            "cluster_doctor": {
                "node": "atlas",
                "entrypoint": "/tmp/cluster_doctor.py",
            }
        },
    )

    assert command[0:2] == ["ssh", "192.168.1.17"]
    assert "/bin/bash -lc" in command[2]
    assert "/tmp/cluster_doctor.py --tail" in command[2]


def test_build_command_treats_fqdn_as_local_node(monkeypatch) -> None:
    monkeypatch.setattr(invoke_agent, "local_node", lambda: "hades")

    command = invoke_agent.build_command(
        "cluster_doctor",
        [],
        {
            "cluster_doctor": {
                "node": "hades.example.net",
                "entrypoint": "tools/cluster_doctor.py",
            }
        },
    )

    assert command[0] == invoke_agent.sys.executable
    assert command[1].endswith("/tools/cluster_doctor.py")


def test_build_command_rejects_endpoint_only_agent(monkeypatch) -> None:
    monkeypatch.setattr(invoke_agent, "local_node", lambda: "hades")

    try:
        invoke_agent.build_command(
            "atlas_inference",
            [],
            {
                "atlas_inference": {
                    "node": "atlas",
                    "endpoint": "http://atlas:11434",
                }
            },
        )
    except ValueError as exc:
        assert str(exc) == "agent atlas_inference is endpoint-only: http://atlas:11434"
    else:
        raise AssertionError("endpoint-only agents should not be executable")


def test_run_executes_subprocess(monkeypatch, tmp_path: Path) -> None:
    registry_path = tmp_path / "agent_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "cluster_doctor": {
                    "node": "hades",
                    "entrypoint": "tools/cluster_doctor.py",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(invoke_agent, "local_node", lambda: "hades")
    captured: list[list[str]] = []
    monkeypatch.setattr(
        "tools.invoke_agent.subprocess.run",
        lambda command, check=False: captured.append(command) or StubResult(0),
    )

    result = invoke_agent.run("cluster_doctor", ["--flag"], registry_path=registry_path)

    assert result == 0
    assert captured
    assert captured[0][1].endswith("/tools/cluster_doctor.py")


def test_main_returns_error_for_unknown_agent(monkeypatch, capsys) -> None:
    monkeypatch.setattr(invoke_agent, "run", lambda agent, argv=None, registry_path=invoke_agent.REGISTRY: (_ for _ in ()).throw(KeyError("unknown agent: missing")))
    monkeypatch.setattr(invoke_agent.sys, "argv", ["invoke_agent.py", "missing"])

    result = invoke_agent.main()
    stderr = capsys.readouterr().err

    assert result == 1
    assert "unknown agent: missing" in stderr
