"""Shared evidence ledger helpers for ACME-facing reasoning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EVIDENCE = Path("~/TK-Ai-Maxx/vault/evidence/evidence.jsonl").expanduser()


def read_recent_evidence(n: int = 10, path: Path = EVIDENCE) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines()[-n:]:
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        if isinstance(data, dict):
            records.append(data)
    return records


def derive_follow_up_signals(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    follow_ups: list[dict[str, Any]] = []
    for evidence in records:
        severity = str(evidence.get("severity", "")).lower()
        if severity == "critical":
            follow_ups.append({"type": "cluster_emergency", "evidence": evidence})
        elif severity == "high":
            follow_ups.append({"type": "investigate_deeper", "evidence": evidence})
    return follow_ups
