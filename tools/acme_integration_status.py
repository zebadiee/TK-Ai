#!/usr/bin/env python3
"""Report the operational seam between TK-Ai and ACME-AI."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
ACME_ROOT = Path("~/ACME-AI").expanduser()
ACME_ADAPTER = ACME_ROOT / "acme_ai" / "intelligence" / "tkai_adapter.py"
ACME_SIGNAL_EXPORTS = ACME_ROOT / ".acme-ai" / "signal_exports"
ACME_RUNTIME_SNAPSHOT = ACME_ROOT / ".acme-ai" / "runtime" / "tkai_status.json"
ACME_MESH_HEALTH = os.getenv("ACME_HADES_MESH_URL", "http://127.0.0.1:8088/health")
ACME_SIGNAL_EXPORTER = ACME_ROOT / "acme_ai" / "intelligence" / "signal_exporter.py"

TKAI_SIGNALS = ROOT / "vault" / "runtime" / "signals.jsonl"
TKAI_EVIDENCE = ROOT / "vault" / "evidence" / "evidence.jsonl"
TKAI_TOPOLOGY = ROOT / "vault" / "runtime" / "cluster_topology.json"
TKAI_REGISTRY = ROOT / "vault" / "runtime" / "agent_registry.json"
BRIDGE_STATE = ROOT / "vault" / "runtime" / "acme_signal_bridge_state.json"


def test_http(url: str, timeout: float = 2.0) -> int | None:
    try:
        response = requests.get(url, timeout=timeout)
    except requests.RequestException:
        return None
    return response.status_code


def read_bridge_state(path: Path | None = None) -> dict[str, Any]:
    path = path or BRIDGE_STATE
    if not path.exists():
        return {"processed_files": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"processed_files": []}
    if not isinstance(payload, dict):
        return {"processed_files": []}
    processed = payload.get("processed_files", [])
    if not isinstance(processed, list):
        processed = []
    return {"processed_files": [str(item) for item in processed]}


def build_status() -> dict[str, Any]:
    bridge_state = read_bridge_state(BRIDGE_STATE)
    exported_signal_files = (
        [f for f in ACME_SIGNAL_EXPORTS.glob("acme_signals_*.json")]
        if ACME_SIGNAL_EXPORTS.exists()
        else []
    )
    return {
        "acme_root_exists": ACME_ROOT.exists(),
        "acme_adapter_exists": ACME_ADAPTER.exists(),
        "tkai_signals_exists": TKAI_SIGNALS.exists(),
        "tkai_evidence_exists": TKAI_EVIDENCE.exists(),
        "tkai_topology_exists": TKAI_TOPOLOGY.exists(),
        "tkai_registry_exists": TKAI_REGISTRY.exists(),
        "acme_signal_export_dir_exists": ACME_SIGNAL_EXPORTS.exists(),
        "acme_signal_export_files": len(exported_signal_files),
        "acme_signal_exporter_exists": ACME_SIGNAL_EXPORTER.exists(),
        "acme_runtime_snapshot_exists": ACME_RUNTIME_SNAPSHOT.exists(),
        "bridge_processed_files": len(bridge_state["processed_files"]),
        "bridge_state_exists": BRIDGE_STATE.exists(),
        "mesh_health_url": ACME_MESH_HEALTH,
        "mesh_health_status": test_http(ACME_MESH_HEALTH),
    }


def format_status_lines(status: dict[str, Any] | None = None) -> list[str]:
    payload = status or build_status()

    def mark(value: bool) -> str:
        return "OK" if value else "MISSING"

    def health_mark(code: int | None) -> str:
        if code == 200:
            return "OK"
        if code is None:
            return "DOWN"
        return str(code)

    return [
        f"ACME root: {mark(bool(payload['acme_root_exists']))}",
        f"ACME TK-Ai adapter: {mark(bool(payload['acme_adapter_exists']))}",
        f"ACME runtime snapshot: {mark(bool(payload['acme_runtime_snapshot_exists']))}",
        f"TK-Ai signals bus: {mark(bool(payload['tkai_signals_exists']))}",
        f"TK-Ai evidence ledger: {mark(bool(payload['tkai_evidence_exists']))}",
        f"TK-Ai topology: {mark(bool(payload['tkai_topology_exists']))}",
        f"TK-Ai agent registry: {mark(bool(payload['tkai_registry_exists']))}",
        f"ACME signal exporter: {mark(bool(payload['acme_signal_exporter_exists']))}",
        f"ACME signal exports: {mark(bool(payload['acme_signal_export_dir_exists']))} ({payload['acme_signal_export_files']} files)",
        f"Bridge state: {mark(bool(payload['bridge_state_exists']))} ({payload['bridge_processed_files']} processed)",
        f"ACME mesh health on 127.0.0.1:8088: {health_mark(payload['mesh_health_status'])}",
    ]


def is_healthy(status: dict[str, Any] | None = None) -> bool:
    payload = status or build_status()
    required = (
        payload["acme_root_exists"],
        payload["acme_adapter_exists"],
        payload["acme_runtime_snapshot_exists"],
        payload["acme_signal_exporter_exists"],
        payload["tkai_signals_exists"],
        payload["tkai_evidence_exists"],
        payload["tkai_topology_exists"],
        payload["tkai_registry_exists"],
        payload["mesh_health_status"] == 200,
    )
    return all(required)


def main() -> int:
    parser = argparse.ArgumentParser(description="Report TK-Ai and ACME-AI integration status")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    status = build_status()
    if args.json:
        print(json.dumps(status, indent=2, sort_keys=True))
    else:
        print("\n".join(format_status_lines(status)))

    return 0 if is_healthy(status) else 1


if __name__ == "__main__":
    raise SystemExit(main())
