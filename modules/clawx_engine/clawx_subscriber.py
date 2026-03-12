"""Subscriber bridge from evidence streams into the ClawX engine."""

from __future__ import annotations

from typing import Any


class ClawXSubscriber:
    """Consumes evidence events and forwards them into the engine safely."""

    def __init__(self, engine: Any) -> None:
        self.engine = engine

    def on_event(self, event: Any) -> None:
        """Receive an evidence or claim event without breaking the caller."""
        try:
            self.engine.process_event(event)
        except Exception as exc:  # pragma: no cover - exercised via sandbox usage
            print(f"[ClawX] subscriber error: {exc}")
