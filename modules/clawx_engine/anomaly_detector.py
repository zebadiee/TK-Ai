"""Simple anomaly detectors for the ClawX research layer."""

from __future__ import annotations

from typing import Any


class FundingAnomalyDetector:
    """Detects high funding-rate observations from evidence events."""

    def __init__(self, threshold: float = 0.2) -> None:
        self.threshold = threshold

    def detect(self, evidence: Any) -> bool:
        content = getattr(evidence, "content", {})
        if not isinstance(content, dict):
            return False

        rate = content.get("funding_rate")
        if isinstance(rate, (int, float)):
            return float(rate) > self.threshold
        return False
