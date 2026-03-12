#!/usr/bin/env python3
"""Bridge ACME-exported JSON signals into the shared TK-AI signal bus."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

DEFAULT_SOURCE = Path("~/ACME-AI/.acme-ai/signal_exports").expanduser()
BUS = Path("~/TK-Ai-Maxx/vault/runtime/signals.jsonl").expanduser()
STATE = Path("~/TK-Ai-Maxx/vault/runtime/acme_signal_bridge_state.json").expanduser()


def load_state(path: Path = STATE) -> dict[str, list[str]]:
    if not path.exists():
        return {"processed_files": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"processed_files": []}
    processed = data.get("processed_files", [])
    if not isinstance(processed, list):
        processed = []
    return {"processed_files": [str(item) for item in processed]}


def save_state(state: dict[str, list[str]], path: Path = STATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def read_signal_file(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def normalize_record(record: dict[str, Any], *, source_file: Path, ordinal: int) -> dict[str, Any]:
    payload = dict(record)
    payload.setdefault("signal_id", f"acme-{source_file.stem}-{ordinal}")
    payload.setdefault("source", "acme_ai")
    payload.setdefault("source_system", "acme_ai")
    payload.setdefault("imported_by", "acme_signal_bridge")
    payload.setdefault("trace_id", f"acme-bridge-{source_file.stem}")
    payload.setdefault("ingested_at", int(time.time()))
    return payload


def bridge_signals(source: Path = DEFAULT_SOURCE, bus: Path = BUS, state_path: Path = STATE) -> int:
    state = load_state(path=state_path)
    processed = set(state["processed_files"])
    imported = 0
    bus.parent.mkdir(parents=True, exist_ok=True)

    with bus.open("a", encoding="utf-8") as handle:
        for file in sorted(source.glob("*.json")) if source.exists() else []:
            resolved = str(file.resolve())
            if resolved in processed:
                continue
            for ordinal, record in enumerate(read_signal_file(file), start=1):
                handle.write(json.dumps(normalize_record(record, source_file=file, ordinal=ordinal), sort_keys=True) + "\n")
                imported += 1
            processed.add(resolved)

    save_state({"processed_files": sorted(processed)}, path=state_path)
    return imported


def main() -> int:
    parser = argparse.ArgumentParser(description="Import ACME-exported JSON signals into the TK-AI bus")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Directory containing ACME JSON signal exports")
    args = parser.parse_args()

    imported = bridge_signals(source=args.source.expanduser())
    print(f"Imported {imported} ACME signals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
