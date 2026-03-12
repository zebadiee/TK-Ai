from __future__ import annotations

import json
from pathlib import Path

from tools import cluster_doctor


def test_load_config_reads_cluster_config(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "cluster_config.json"
    config_path.write_text(json.dumps({"cluster": {"atlas": {"role": "gpu_worker"}}}), encoding="utf-8")
    monkeypatch.setattr(cluster_doctor, "CONFIG_PATH", config_path)

    config = cluster_doctor.load_config()

    assert config["cluster"]["atlas"]["role"] == "gpu_worker"


def test_detect_node_uses_short_hostname(monkeypatch) -> None:
    monkeypatch.setattr("tools.cluster_doctor.socket.gethostname", lambda: "atlas.example.net")

    assert cluster_doctor.detect_node() == "atlas"


def test_main_reports_cluster_health(monkeypatch, capsys, tmp_path: Path) -> None:
    config_path = tmp_path / "cluster_config.json"
    node_roles_path = tmp_path / "node_roles.json"
    signals_path = tmp_path / "signals.jsonl"
    evidence_path = tmp_path / "evidence.jsonl"
    config_path.write_text(
        json.dumps(
            {
                "cluster": {
                    "hades": {"role": "control", "host": "hades"},
                    "atlas": {
                        "role": "gpu_worker",
                        "host": "atlas",
                        "ip": "192.168.1.17",
                        "ollama_url": "http://192.168.1.17:11434",
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    node_roles_path.write_text(
        json.dumps(
            {
                "hades": {"role": "control", "services": ["scheduler", "policy_daemon"]},
                "atlas": {"role": "gpu_worker", "services": ["inference"]},
            }
        ),
        encoding="utf-8",
    )
    signals_path.write_text("", encoding="utf-8")
    evidence_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(cluster_doctor, "CONFIG_PATH", config_path)
    monkeypatch.setattr(cluster_doctor, "NODE_ROLES_PATH", node_roles_path)
    monkeypatch.setattr(cluster_doctor, "detect_node", lambda: "hades")
    monkeypatch.setattr(cluster_doctor, "test_tcp", lambda host, port: True)
    monkeypatch.setattr(cluster_doctor, "test_http", lambda url: 200)
    monkeypatch.setattr(cluster_doctor, "get_local_ip", lambda: "192.168.1.12")
    monkeypatch.setattr(cluster_doctor, "get_service_status", lambda: "active")
    monkeypatch.setattr(cluster_doctor, "format_acme_status_lines", lambda: ["ACME root: OK", "ACME mesh health: OK [http://127.0.0.1:8088/health]"])
    monkeypatch.setattr("tools.cluster_doctor.socket.gethostname", lambda: "hades")
    monkeypatch.setattr(cluster_doctor, "SIGNALS_PATH", signals_path)
    monkeypatch.setattr(cluster_doctor, "EVIDENCE_PATH", evidence_path)

    result = cluster_doctor.main()
    output = capsys.readouterr().out

    assert result == 0
    assert "Node: hades" in output
    assert "ATLAS TCP 11434: OK" in output
    assert "Ollama API: OK" in output
    assert "Signals file: OK" in output
    assert "Evidence file: OK" in output
    assert "Investigation daemon: active" in output
    assert "ACME root: OK" in output
    assert "IP: 192.168.1.12" in output
    assert "Role: control" in output
    assert "SSH target: hades" in output
