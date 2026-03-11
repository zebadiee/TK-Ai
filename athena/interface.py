"""ATHENA interface for intent intake."""

from __future__ import annotations

from typing import Any


class AthenaInterface:
    """Provides the next intent for the kernel loop."""

    def get_next_intent(self) -> dict[str, Any]:
        # Deterministic default; replace with real intake when integrating.
        return {"intent": "noop", "payload": {}}
