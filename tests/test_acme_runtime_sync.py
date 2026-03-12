from __future__ import annotations

import json
from pathlib import Path

from tools import acme_runtime_sync


def test_write_snapshot_exports_cluster_artifacts(tmp_path: Path, monkeypatch) -> None:
    tkai_root = tmp_path / "TK-Ai-Maxx"
    cluster_status = tkai_root / "vault" / "runtime" / "cluster_status.json"
    topology = tkai_root / "vault" / "runtime" / "cluster_topology.json"
    registry = tkai_root / "vault" / "runtime" / "agent_registry.json"
    signals = tkai_root / "vault" / "runtime" / "signals.jsonl"
    evidence = tkai_root / "vault" / "evidence" / "evidence.jsonl"
    snapshot = tmp_path / "ACME-AI" / ".acme-ai" / "runtime" / "tkai_status.json"

    cluster_status.parent.mkdir(parents=True, exist_ok=True)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    cluster_status.write_text(json.dumps({"node": "hades"}), encoding="utf-8")
    topology.write_text(json.dumps({"nodes": {"hades": {"role": "control_plane"}}}), encoding="utf-8")
    registry.write_text(json.dumps({"cluster_doctor": {"node": "hades"}}), encoding="utf-8")
    signals.write_text('{"signal_id":"sig-1"}\n', encoding="utf-8")
    evidence.write_text('{"signal_id":"sig-1"}\n', encoding="utf-8")

    monkeypatch.setattr(acme_runtime_sync, "CLUSTER_STATUS", cluster_status)
    monkeypatch.setattr(acme_runtime_sync, "TOPOLOGY", topology)
    monkeypatch.setattr(acme_runtime_sync, "REGISTRY", registry)
    monkeypatch.setattr(acme_runtime_sync, "SIGNALS", signals)
    monkeypatch.setattr(acme_runtime_sync, "EVIDENCE", evidence)
    monkeypatch.setattr(acme_runtime_sync, "detect_local_node", lambda: "hades")
    monkeypatch.setattr(acme_runtime_sync, "build_acme_integration_status", lambda: {"acme_root_exists": True})

    payload = acme_runtime_sync.write_snapshot(path=snapshot, signals_limit=5, evidence_limit=5)
    data = json.loads(snapshot.read_text(encoding="utf-8"))

    assert payload["node"] == "hades"
    assert data["cluster_status"]["node"] == "hades"
    assert data["recent_signals"][0]["signal_id"] == "sig-1"
    assert data["recent_evidence"][0]["signal_id"] == "sig-1"
    assert data["integration"]["acme_root_exists"] is True
