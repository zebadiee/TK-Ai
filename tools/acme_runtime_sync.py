#!/usr/bin/env python3
"""Export a consolidated TK-Ai snapshot into the ACME runtime area."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.acme_integration_status import build_status as build_acme_integration_status
from tools.cluster_registry import detect_local_node

ACME_RUNTIME_SNAPSHOT = Path("~/ACME-AI/.acme-ai/runtime/tkai_status.json").expanduser()
CLUSTER_STATUS = ROOT / "vault" / "runtime" / "cluster_status.json"
TOPOLOGY = ROOT / "vault" / "runtime" / "cluster_topology.json"
REGISTRY = ROOT / "vault" / "runtime" / "agent_registry.json"
SIGNALS = ROOT / "vault" / "runtime" / "signals.jsonl"
EVIDENCE = ROOT / "vault" / "evidence" / "evidence.jsonl"


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default
    return payload


def read_jsonl_tail(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def build_snapshot(signals_limit: int = 20, evidence_limit: int = 20) -> dict[str, Any]:
    return {
        "generated_at": int(time.time()),
        "node": detect_local_node(),
        "cluster_status": read_json(CLUSTER_STATUS, {}),
        "topology": read_json(TOPOLOGY, {"nodes": {}}),
        "agent_registry": read_json(REGISTRY, {}),
        "recent_signals": read_jsonl_tail(SIGNALS, signals_limit),
        "recent_evidence": read_jsonl_tail(EVIDENCE, evidence_limit),
        "integration": build_acme_integration_status(),
    }


def write_snapshot(
    path: Path = ACME_RUNTIME_SNAPSHOT,
    *,
    signals_limit: int = 20,
    evidence_limit: int = 20,
) -> dict[str, Any]:
    payload = build_snapshot(signals_limit=signals_limit, evidence_limit=evidence_limit)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Export TK-Ai runtime snapshot into ACME")
    parser.add_argument("--path", type=Path, default=ACME_RUNTIME_SNAPSHOT, help="Output snapshot path")
    parser.add_argument("--signals-limit", type=int, default=20, help="Number of recent signals to include")
    parser.add_argument("--evidence-limit", type=int, default=20, help="Number of recent evidence rows to include")
    args = parser.parse_args()

    payload = write_snapshot(
        path=args.path.expanduser(),
        signals_limit=args.signals_limit,
        evidence_limit=args.evidence_limit,
    )
    print(
        f"Wrote ACME runtime snapshot: {args.path.expanduser()} "
        f"(signals={len(payload['recent_signals'])}, evidence={len(payload['recent_evidence'])})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
