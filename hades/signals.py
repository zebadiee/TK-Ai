"""Signal aggregation for higher-confidence graph launches."""

from __future__ import annotations

import copy
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SignalEvent:
    signal_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    observed_at: float | None = None


@dataclass
class SignalRule:
    rule_id: str
    signal_types: list[str]
    min_score: float
    within_seconds: int
    graph_id: str


@dataclass
class AggregatedTrigger:
    graph_id: str
    rule_id: str
    score: float
    matched_signals: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def load_signal_rules(path: str | Path) -> list[SignalRule]:
    signal_path = Path(path)
    if not signal_path.exists():
        return []

    with signal_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        return []

    raw_rules = data.get("rules", [])
    if not isinstance(raw_rules, list):
        return []

    rules = []
    for raw_rule in raw_rules:
        if not isinstance(raw_rule, dict):
            continue
        rule_id = str(raw_rule.get("rule_id", "")).strip()
        graph_id = str(raw_rule.get("graph_id", "")).strip()
        signal_types = raw_rule.get("signal_types", [])
        if not isinstance(signal_types, list):
            signal_types = []
        if not rule_id or not graph_id or not signal_types:
            continue
        rules.append(
            SignalRule(
                rule_id=rule_id,
                signal_types=[str(item) for item in signal_types],
                min_score=float(raw_rule.get("min_score", len(signal_types))),
                within_seconds=int(raw_rule.get("within_seconds", 300)),
                graph_id=graph_id,
            )
        )
    return rules


class SignalAggregator:
    """Collects short-lived signals and emits aggregated triggers."""

    def __init__(
        self,
        rules: list[SignalRule] | None = None,
        max_events: int = 50,
    ) -> None:
        self.rules = rules or []
        self.max_events = max_events
        self.events: list[SignalEvent] = []

    def ingest(self, event: SignalEvent) -> AggregatedTrigger | None:
        timestamp = event.observed_at if event.observed_at is not None else time.time()
        normalized = SignalEvent(
            signal_type=event.signal_type,
            payload=copy.deepcopy(event.payload),
            observed_at=timestamp,
        )
        self.events.append(normalized)
        self.events = self.events[-self.max_events :]

        for rule in self.rules:
            aggregate = self._match_rule(rule, timestamp)
            if aggregate is not None:
                return aggregate
        return None

    def _match_rule(self, rule: SignalRule, now: float) -> AggregatedTrigger | None:
        window_start = now - rule.within_seconds
        matching_events = [event for event in self.events if event.observed_at is not None and event.observed_at >= window_start]

        matched_payloads: dict[str, dict[str, Any]] = {}
        score = 0.0
        for signal_type in rule.signal_types:
            for event in reversed(matching_events):
                if event.signal_type != signal_type:
                    continue
                matched_payloads[signal_type] = copy.deepcopy(event.payload)
                score += float(event.payload.get("score", 1.0))
                break

        if len(matched_payloads) != len(rule.signal_types):
            return None
        if score < rule.min_score:
            return None

        return AggregatedTrigger(
            graph_id=rule.graph_id,
            rule_id=rule.rule_id,
            score=score,
            matched_signals=sorted(matched_payloads.keys()),
            metadata={"signals": matched_payloads, "within_seconds": rule.within_seconds},
        )
