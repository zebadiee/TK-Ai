"""Event trigger matching for task graph launches."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TriggerEvent:
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class TriggerRule:
    event_type: str
    condition: dict[str, Any]
    graph_id: str


@dataclass
class TriggerMatch:
    graph_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


def load_trigger_rules(path: str | Path) -> list[TriggerRule]:
    trigger_path = Path(path)
    if not trigger_path.exists():
        return []

    with trigger_path.open("r", encoding="utf-8") as handle:
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
        event_type = str(raw_rule.get("event_type", "")).strip()
        graph_id = str(raw_rule.get("graph_id", "")).strip()
        condition = raw_rule.get("condition", {})
        if not event_type or not graph_id:
            continue
        if not isinstance(condition, dict):
            condition = {}
        rules.append(TriggerRule(event_type=event_type, condition=condition, graph_id=graph_id))
    return rules


class TriggerEngine:
    """Matches incoming events to task graphs using deterministic rules."""

    def __init__(self, rules: list[TriggerRule] | None = None) -> None:
        self.rules = rules or []

    def match(self, event: TriggerEvent) -> TriggerMatch | None:
        for rule in self.rules:
            if rule.event_type != event.event_type:
                continue
            if not self._check_condition(rule.condition, event.payload):
                continue
            return TriggerMatch(
                graph_id=rule.graph_id,
                metadata={
                    "event_type": event.event_type,
                    "payload": copy.deepcopy(event.payload),
                    "condition": copy.deepcopy(rule.condition),
                },
            )
        return None

    def _check_condition(self, condition: dict[str, Any], payload: dict[str, Any]) -> bool:
        if "change_pct_gt" in condition and payload.get("change_pct", 0) <= condition["change_pct_gt"]:
            return False

        if "hour" in condition and payload.get("hour") != condition["hour"]:
            return False

        for key, value in condition.items():
            if key in {"change_pct_gt", "hour"}:
                continue
            if payload.get(key) != value:
                return False

        return True
