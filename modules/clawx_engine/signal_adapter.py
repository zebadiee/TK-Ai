"""Adapter that emits normalized signals into a signal engine."""

from __future__ import annotations

import time
import uuid
from typing import Any


class SignalAdapter:
    """Translates ClawX findings into signal-engine input events."""

    def __init__(self, signal_engine: Any, source: str = "clawx") -> None:
        self.signal_engine = signal_engine
        self.source = source

    def emit(
        self,
        signal_type: str,
        payload: dict[str, Any],
        *,
        severity: str = "medium",
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        signal = {
            "signal_id": f"sig-{uuid.uuid4()}",
            "type": signal_type,
            "source": self.source,
            "severity": severity,
            "payload": payload,
            "timestamp": int(time.time()),
            "trace_id": trace_id,
        }
        self.signal_engine.receive(signal)
        return signal
