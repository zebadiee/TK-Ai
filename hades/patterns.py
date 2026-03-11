"""Pattern storage and indexed memory for HADES."""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_PATTERNS: dict[str, Any] = {"routes": {}, "capabilities": {}}


@dataclass
class PatternRecord:
    intent: str
    action: str
    confidence: float = 1.0
    usage_count: int = 0
    last_used: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PatternMatch:
    action: str
    confidence: float
    reason: str
    source_intent: str


def normalize_intent(intent: str) -> str:
    return " ".join(intent.lower().strip().split())


def _tokenize_intent(intent: str) -> set[str]:
    normalized = normalize_intent(intent)
    if not normalized:
        return set()
    return set(normalized.split(" "))


class PatternIndex:
    """Indexed memory for persistent pattern reinforcement."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "patterns": {}}

        with self.path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        if not isinstance(data, dict):
            return {"version": 1, "patterns": {}}

        patterns = data.get("patterns", {})
        if isinstance(patterns, dict):
            normalized_patterns: dict[str, Any] = {}
            for key, record in patterns.items():
                normalized = self._normalize_record(record, fallback_intent=str(key))
                if normalized is not None:
                    normalized_patterns[normalized["intent"]] = normalized
            return {"version": data.get("version", 1), "patterns": normalized_patterns}

        migrated_patterns: dict[str, Any] = {}
        if isinstance(patterns, list):
            for record in patterns:
                normalized = self._normalize_record(record)
                if normalized is not None:
                    migrated_patterns[normalized["intent"]] = normalized

        return {"version": 1, "patterns": migrated_patterns}

    def _normalize_record(
        self,
        record: Any,
        fallback_intent: str = "",
    ) -> dict[str, Any] | None:
        if not isinstance(record, dict):
            return None

        intent = normalize_intent(str(record.get("intent", fallback_intent)))
        action = str(record.get("action", "")).strip()
        if not intent or not action:
            return None

        confidence = record.get("confidence", 1.0)
        if not isinstance(confidence, (int, float)):
            confidence = 1.0

        usage_count = record.get("usage_count", 0)
        if not isinstance(usage_count, int):
            usage_count = 0

        metadata = record.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        return {
            "intent": intent,
            "action": action,
            "confidence": max(0.0, min(1.0, float(confidence))),
            "usage_count": max(0, usage_count),
            "last_used": record.get("last_used"),
            "metadata": metadata,
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(self.data, handle, indent=2, sort_keys=True)

    def lookup(self, intent: str, threshold: float = 0.5) -> dict[str, Any] | None:
        match = self.lookup_best(intent, threshold=threshold)
        if match is None:
            return None
        patterns = self.data.get("patterns", {})
        if not isinstance(patterns, dict):
            return None
        return patterns.get(match.source_intent)

    def lookup_best(self, intent: str, threshold: float = 0.5) -> PatternMatch | None:
        normalized_intent = normalize_intent(intent)
        if not normalized_intent:
            return None

        patterns = self.data.get("patterns", {})
        if not isinstance(patterns, dict):
            return None

        record = patterns.get(normalized_intent)
        if record and float(record.get("confidence", 0.0)) >= threshold:
            return PatternMatch(
                action=str(record["action"]),
                confidence=float(record["confidence"]),
                reason="exact",
                source_intent=normalized_intent,
            )

        query_tokens = _tokenize_intent(normalized_intent)
        best_match: PatternMatch | None = None
        best_score = 0.0
        for source_intent, candidate in patterns.items():
            if not isinstance(candidate, dict):
                continue

            candidate_tokens = _tokenize_intent(source_intent)
            if not candidate_tokens or not query_tokens:
                continue

            overlap = len(query_tokens & candidate_tokens)
            union = len(query_tokens | candidate_tokens)
            if overlap == 0 or union == 0:
                continue

            similarity = overlap / union
            confidence = float(candidate.get("confidence", 0.0))
            score = round(similarity * confidence, 4)
            if score < threshold or score <= best_score:
                continue

            best_score = score
            best_match = PatternMatch(
                action=str(candidate.get("action", "")),
                confidence=score,
                reason="token_overlap",
                source_intent=source_intent,
            )

        return best_match

    def reinforce(
        self,
        intent: str,
        action: str,
        success: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not success:
            return

        intent = normalize_intent(intent)
        patterns = self.data.setdefault("patterns", {})
        metadata = metadata if isinstance(metadata, dict) else {}

        if intent in patterns:
            patterns[intent]["usage_count"] += 1
            patterns[intent]["last_used"] = datetime.now(timezone.utc).isoformat()
            patterns[intent]["confidence"] = min(1.0, patterns[intent]["confidence"] + 0.05)
            existing_metadata = patterns[intent].get("metadata", {})
            if not isinstance(existing_metadata, dict):
                existing_metadata = {}
            patterns[intent]["metadata"] = {**existing_metadata, **metadata}
        else:
            record = PatternRecord(
                intent=intent,
                action=action,
                usage_count=1,
                last_used=datetime.now(timezone.utc).isoformat(),
                metadata=metadata,
            )
            patterns[intent] = record.to_dict()

        self.save()


def load_patterns(path: str | Path) -> dict[str, Any]:
    pattern_path = Path(path)
    if not pattern_path.exists():
        return copy.deepcopy(DEFAULT_PATTERNS)

    with pattern_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        return copy.deepcopy(DEFAULT_PATTERNS)

    return {
        "routes": data.get("routes", {}),
        "capabilities": data.get("capabilities", {}),
    }


def save_patterns(path: str | Path, patterns: dict[str, Any]) -> None:
    if not isinstance(patterns, dict):
        raise ValueError("Patterns must be a dictionary")

    pattern_path = Path(path)
    pattern_path.parent.mkdir(parents=True, exist_ok=True)
    with pattern_path.open("w", encoding="utf-8") as handle:
        json.dump(patterns, handle, indent=2, sort_keys=True)
