"""Hypothesis generation from repeated evidence events."""

from __future__ import annotations

from typing import Any


class HypothesisBuilder:
    """Builds coarse hypotheses once enough evidence has accumulated."""

    def __init__(self, minimum_events: int = 3) -> None:
        self.minimum_events = minimum_events

    def build(self, evidence_events: list[Any]) -> dict[str, Any] | None:
        if len(evidence_events) < self.minimum_events:
            return None

        return {
            "type": "funding_pattern_detected",
            "confidence": 0.7,
            "event_count": len(evidence_events),
        }
