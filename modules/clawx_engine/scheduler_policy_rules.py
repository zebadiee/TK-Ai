"""Deterministic rules for ClawX scheduler policy recommendations."""

from __future__ import annotations

import time
from typing import Any, Callable


class SchedulerPolicyRules:
    """Converts recent signal and evidence history into scheduler policy."""

    def __init__(
        self,
        signal_history: list[dict[str, Any]],
        evidence_history: list[dict[str, Any]],
        writer: Any,
        *,
        now_fn: Callable[[], float] | None = None,
        anomaly_threshold: int = 3,
        anomaly_window_seconds: int = 1800,
        evidence_threshold: int = 10,
        evidence_window_seconds: int = 3600,
        quiet_window_seconds: int = 14400,
    ) -> None:
        self.signals = signal_history
        self.evidence = evidence_history
        self.writer = writer
        self.now_fn = now_fn or time.time
        self.anomaly_threshold = anomaly_threshold
        self.anomaly_window_seconds = anomaly_window_seconds
        self.evidence_threshold = evidence_threshold
        self.evidence_window_seconds = evidence_window_seconds
        self.quiet_window_seconds = quiet_window_seconds

    def evaluate(self) -> dict[str, Any] | None:
        if self._recent_anomaly():
            return self.writer.recommend_running(
                "Recent anomaly signals detected",
                duration=6,
            )

        if self._investigations_active():
            return self.writer.recommend_running(
                "Investigations still generating evidence",
                duration=3,
            )

        if self._quiet_period():
            return self.writer.recommend_stop("No anomalies detected recently")

        return None

    def _recent_anomaly(self) -> bool:
        now = self.now_fn()
        recent = [
            signal
            for signal in self.signals
            if self._within_window(signal, now, self.anomaly_window_seconds) and self._is_anomaly_signal(signal)
        ]
        return len(recent) >= self.anomaly_threshold

    def _investigations_active(self) -> bool:
        now = self.now_fn()
        recent = [
            event
            for event in self.evidence
            if self._within_window(event, now, self.evidence_window_seconds)
        ]
        return len(recent) >= self.evidence_threshold

    def _quiet_period(self) -> bool:
        now = self.now_fn()
        recent_anomalies = [
            signal
            for signal in self.signals
            if self._within_window(signal, now, self.quiet_window_seconds) and self._is_anomaly_signal(signal)
        ]
        return len(recent_anomalies) == 0

    def _within_window(self, event: dict[str, Any], now: float, window_seconds: int) -> bool:
        try:
            timestamp = float(event.get("timestamp", 0))
        except (TypeError, ValueError):
            return False
        return now - timestamp < window_seconds

    def _is_anomaly_signal(self, signal: dict[str, Any]) -> bool:
        signal_type = str(signal.get("type", "")).strip().lower()
        severity = str(signal.get("severity", "")).strip().lower()
        return "anomaly" in signal_type or severity == "high"
