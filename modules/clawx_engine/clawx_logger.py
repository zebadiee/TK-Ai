"""Append-only reasoning log for ClawX observability."""

from __future__ import annotations

import json
import socket
import time
from pathlib import Path
from typing import Any

LOG_PATH = Path("vault/runtime/clawx_log.jsonl")
NODE = socket.gethostname()


def log_event(event: str, *, path: Path | None = None, **fields: Any) -> None:
    """Append a structured reasoning event without breaking ClawX execution."""
    entry = {
        "timestamp": int(time.time()),
        "node": NODE,
        "event": event,
    }
    entry.update(fields)

    log_path = path or LOG_PATH
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
    except Exception as exc:  # pragma: no cover - exercised by failure injection
        print(f"[ClawXLogger] write failed: {exc}")
