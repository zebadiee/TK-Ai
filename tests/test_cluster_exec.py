from __future__ import annotations

import json
from pathlib import Path

from tools import cluster_exec


class StubResult:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_run_on_node_uses_transport_and_returns_result(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "cluster_config.json"
    node_roles_path = tmp_path / "node_roles.json"
    config_path.write_text(
        json.dumps(
            {
                "cluster": {
                    "atlas": {"role": "gpu_worker", "host": "atlas"},
                }
            }
        ),
        encoding="utf-8",
    )
    node_roles_path.write_text(json.dumps({}), encoding="utf-8")
    monkeypatch.setattr(cluster_exec, "CLUSTER_CONFIG", config_path)
    monkeypatch.setattr(cluster_exec, "NODE_ROLES", node_roles_path)
    monkeypatch.setattr("tools.cluster_exec.time.time", lambda: 100.0)

    captured: list[list[str]] = []

    def runner(command, **kwargs):
        captured.append(command)
        return StubResult(stdout="atlas")

    result = cluster_exec.run_on_node("atlas", ["hostname"], runner=runner)

    assert captured[0][0] == "ssh"
    assert result["ok"] is True
    assert result["stdout"] == "atlas"


def test_main_requires_target_node(capsys) -> None:
    result = cluster_exec.main([])
    stderr = capsys.readouterr().err

    assert result == 1
    assert "No target nodes supplied" in stderr


def test_run_on_node_returns_timeout_result(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "cluster_config.json"
    node_roles_path = tmp_path / "node_roles.json"
    config_path.write_text(
        json.dumps(
            {
                "cluster": {
                    "atlas": {"role": "gpu_worker", "host": "atlas"},
                }
            }
        ),
        encoding="utf-8",
    )
    node_roles_path.write_text(json.dumps({}), encoding="utf-8")
    monkeypatch.setattr(cluster_exec, "CLUSTER_CONFIG", config_path)
    monkeypatch.setattr(cluster_exec, "NODE_ROLES", node_roles_path)

    def runner(command, **kwargs):
        raise cluster_exec.subprocess.TimeoutExpired(command, kwargs["timeout"])

    result = cluster_exec.run_on_node("atlas", ["hostname"], timeout=2.5, runner=runner)

    assert result["ok"] is False
    assert result["returncode"] == 124
    assert result["stderr"] == "timeout after 2.5s"
