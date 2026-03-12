"""Persistence for ClawX scheduler policy recommendations."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class SchedulerPolicyWriter:
    """Writes the current scheduler recommendation as runtime policy state."""

    def __init__(self, path: str | Path = "vault/policy/scheduler_policy.json") -> None:
        self.path = Path(path)

    def recommend_running(self, reason: str, duration: int) -> dict[str, Any]:
        payload = {
            "state": "running",
            "desired_state": "running",
            "reason": reason,
            "duration_hours": int(duration),
            "recommended_at": int(time.time()),
            "updated_by": "clawx",
            "source": "clawx",
        }
        self._write(payload)
        return payload

    def recommend_stop(self, reason: str) -> dict[str, Any]:
        payload = {
            "state": "stopped",
            "desired_state": "stopped",
            "reason": reason,
            "duration_hours": 0,
            "recommended_at": int(time.time()),
            "updated_by": "clawx",
            "source": "clawx",
        }
        self._write(payload)
        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
