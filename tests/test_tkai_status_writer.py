import json
from pathlib import Path

from tools import tkai_status_writer


class StubResult:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout


def test_write_status_persists_cluster_status(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "cluster_config.json"
    node_roles_path = tmp_path / "node_roles.json"
    config_path.write_text(
        json.dumps(
            {
                "cluster": {
                    "hades": {
                        "role": "control",
                        "host": "hades",
                        "ip": "192.168.1.12",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    node_roles_path.write_text(
        json.dumps(
            {
                "hades": {"role": "control", "services": ["scheduler", "policy_daemon", "signals"]}
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "tools.tkai_status_writer.subprocess.run",
        lambda *args, **kwargs: StubResult("active\n"),
    )
    monkeypatch.setattr(tkai_status_writer, "CLUSTER_CONFIG", config_path)
    monkeypatch.setattr(tkai_status_writer, "NODE_ROLES", node_roles_path)
    monkeypatch.setattr("tools.tkai_status_writer.detect_local_node", lambda: "hades")

    path = tmp_path / "cluster_status.json"
    payload = tkai_status_writer.write_status(path)
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["services"]["scheduler"] == "active"
    assert data["services"]["policy_daemon"] == "active"
    assert data["node"] == payload["node"]
    assert data["role"] == "control"
    assert data["host"] == "hades"
    assert data["declared_services"] == ["policy_daemon", "scheduler", "signals"]
