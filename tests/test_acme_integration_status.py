from __future__ import annotations

import json
from pathlib import Path

from tools import acme_integration_status


def test_build_status_reports_file_and_endpoint_health(tmp_path: Path, monkeypatch) -> None:
    acme_root = tmp_path / "ACME-AI"
    adapter = acme_root / "acme_ai" / "intelligence" / "tkai_adapter.py"
    signal_exports = acme_root / ".acme-ai" / "signal_exports"
    tkai_root = tmp_path / "TK-Ai-Maxx"
    signals = tkai_root / "vault" / "runtime" / "signals.jsonl"
    evidence = tkai_root / "vault" / "evidence" / "evidence.jsonl"
    topology = tkai_root / "vault" / "runtime" / "cluster_topology.json"
    registry = tkai_root / "vault" / "runtime" / "agent_registry.json"
    bridge_state = tkai_root / "vault" / "runtime" / "acme_signal_bridge_state.json"
    runtime_snapshot = acme_root / ".acme-ai" / "runtime" / "tkai_status.json"

    adapter.parent.mkdir(parents=True, exist_ok=True)
    adapter.write_text("# adapter\n", encoding="utf-8")
    signal_exports.mkdir(parents=True, exist_ok=True)
    (signal_exports / "sig-1.json").write_text(json.dumps({"signal_id": "sig-1"}), encoding="utf-8")
    signals.parent.mkdir(parents=True, exist_ok=True)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    signals.write_text('{"signal_id":"sig-1"}\n', encoding="utf-8")
    evidence.write_text('{"signal_id":"sig-1"}\n', encoding="utf-8")
    topology.write_text(json.dumps({"nodes": {}}), encoding="utf-8")
    registry.write_text(json.dumps({"cluster_doctor": {"node": "hades"}}), encoding="utf-8")
    bridge_state.write_text(json.dumps({"processed_files": ["a.json", "b.json"]}), encoding="utf-8")
    runtime_snapshot.parent.mkdir(parents=True, exist_ok=True)
    runtime_snapshot.write_text(json.dumps({"node": "hades"}), encoding="utf-8")

    monkeypatch.setattr(acme_integration_status, "ACME_ROOT", acme_root)
    monkeypatch.setattr(acme_integration_status, "ACME_ADAPTER", adapter)
    monkeypatch.setattr(acme_integration_status, "ACME_SIGNAL_EXPORTS", signal_exports)
    monkeypatch.setattr(acme_integration_status, "ACME_RUNTIME_SNAPSHOT", runtime_snapshot)
    monkeypatch.setattr(acme_integration_status, "TKAI_SIGNALS", signals)
    monkeypatch.setattr(acme_integration_status, "TKAI_EVIDENCE", evidence)
    monkeypatch.setattr(acme_integration_status, "TKAI_TOPOLOGY", topology)
    monkeypatch.setattr(acme_integration_status, "TKAI_REGISTRY", registry)
    monkeypatch.setattr(acme_integration_status, "BRIDGE_STATE", bridge_state)
    exporter = acme_root / "acme_ai" / "intelligence" / "signal_exporter.py"
    exporter.parent.mkdir(parents=True, exist_ok=True)
    exporter.write_text("# exporter\n", encoding="utf-8")
    # Rename the export file so the acme_signals_* glob picks it up
    (signal_exports / "sig-1.json").rename(signal_exports / "acme_signals_1.json")

    monkeypatch.setattr(acme_integration_status, "ACME_MESH_HEALTH", "http://mesh/health")
    monkeypatch.setattr(acme_integration_status, "ACME_SIGNAL_EXPORTER", exporter)
    monkeypatch.setattr(
        acme_integration_status,
        "test_http",
        lambda url, timeout=2.0: 200 if "mesh" in url else None,
    )

    status = acme_integration_status.build_status()

    assert status["acme_root_exists"] is True
    assert status["acme_adapter_exists"] is True
    assert status["acme_runtime_snapshot_exists"] is True
    assert status["acme_signal_exporter_exists"] is True
    assert status["acme_signal_export_files"] == 1
    assert status["bridge_processed_files"] == 2
    assert status["mesh_health_status"] == 200


def test_format_status_lines_is_operator_readable() -> None:
    lines = acme_integration_status.format_status_lines(
        {
            "acme_root_exists": True,
            "acme_adapter_exists": True,
            "acme_runtime_snapshot_exists": True,
            "tkai_signals_exists": True,
            "tkai_evidence_exists": True,
            "tkai_topology_exists": True,
            "tkai_registry_exists": True,
            "acme_signal_export_dir_exists": True,
            "acme_signal_export_files": 3,
            "acme_signal_exporter_exists": True,
            "bridge_processed_files": 5,
            "bridge_state_exists": True,
            "mesh_health_url": "http://127.0.0.1:8088/health",
            "mesh_health_status": 200,
        }
    )

    assert "ACME root: OK" in lines
    assert "ACME runtime snapshot: OK" in lines
    assert "ACME signal exporter: OK" in lines
    assert "ACME signal exports: OK (3 files)" in lines
    assert "ACME mesh health on 127.0.0.1:8088: OK" in lines
