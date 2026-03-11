"""Graph fitness scoring and rolling metrics persistence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class GraphMetrics:
    success: bool
    latency_ms: float
    cost: float = 0.0
    token_usage: int = 0


@dataclass
class GraphFitnessSummary:
    runs: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    avg_cost: float = 0.0
    avg_tokens: float = 0.0
    avg_score: float = 0.0
    last_score: float = 0.0

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


class GraphFitnessStore:
    """Persists rolling graph metrics by versioned graph id."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.data = self._load()

    def _load(self) -> dict[str, dict[str, float | int]]:
        if not self.path.exists():
            return {}

        with self.path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        return data if isinstance(data, dict) else {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(self.data, handle, indent=2, sort_keys=True)

    def get(self, graph_id: str) -> GraphFitnessSummary:
        raw = self.data.get(graph_id, {})
        if not isinstance(raw, dict):
            raw = {}
        return GraphFitnessSummary(
            runs=int(raw.get("runs", 0)),
            success_rate=float(raw.get("success_rate", 0.0)),
            avg_latency_ms=float(raw.get("avg_latency_ms", 0.0)),
            avg_cost=float(raw.get("avg_cost", 0.0)),
            avg_tokens=float(raw.get("avg_tokens", 0.0)),
            avg_score=float(raw.get("avg_score", 0.0)),
            last_score=float(raw.get("last_score", 0.0)),
        )

    def record(self, graph_id: str, metrics: GraphMetrics, score: float) -> GraphFitnessSummary:
        current = self.get(graph_id)
        runs = current.runs + 1
        successes = round(current.success_rate * current.runs) + (1 if metrics.success else 0)

        summary = GraphFitnessSummary(
            runs=runs,
            success_rate=successes / runs,
            avg_latency_ms=((current.avg_latency_ms * current.runs) + metrics.latency_ms) / runs,
            avg_cost=((current.avg_cost * current.runs) + metrics.cost) / runs,
            avg_tokens=((current.avg_tokens * current.runs) + metrics.token_usage) / runs,
            avg_score=((current.avg_score * current.runs) + score) / runs,
            last_score=score,
        )
        self.data[graph_id] = summary.to_dict()
        self.save()
        return summary


class GraphFitnessScorer:
    """Scores graph runs and decides promotion or rollback pressure."""

    def __init__(
        self,
        promotion_threshold: float = 0.8,
        failure_threshold: float = 0.3,
        min_runs_for_promotion: int = 2,
        failure_streak_threshold: int = 3,
    ) -> None:
        self.promotion_threshold = promotion_threshold
        self.failure_threshold = failure_threshold
        self.min_runs_for_promotion = min_runs_for_promotion
        self.failure_streak_threshold = failure_streak_threshold

    def score(self, metrics: GraphMetrics) -> float:
        success_score = 1.0 if metrics.success else 0.0
        latency_score = max(0.0, 1.0 - (metrics.latency_ms / 5000.0))
        cost_score = max(0.0, 1.0 - metrics.cost)
        return (success_score * 0.6) + (latency_score * 0.2) + (cost_score * 0.2)

    def should_promote(self, summary: GraphFitnessSummary, experimental: bool) -> bool:
        return (
            experimental
            and summary.runs >= self.min_runs_for_promotion
            and summary.avg_score >= self.promotion_threshold
        )

    def should_record_failure(self, summary: GraphFitnessSummary) -> bool:
        return summary.last_score <= self.failure_threshold
