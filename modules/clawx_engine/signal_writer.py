"""Append-only runtime signal stream for ClawX."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

SIGNALS = Path("vault/runtime/signals.jsonl")


def emit_signal(
    signal_type: str,
    payload: dict[str, Any],
    *,
    path: Path | None = None,
    **fields: Any,
) -> None:
    event = {
        "type": signal_type,
        "payload": payload,
        "timestamp": int(time.time()),
    }
    event.update(fields)

    target = path or SIGNALS
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    except Exception:
        pass
