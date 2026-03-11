from __future__ import annotations

from pathlib import Path

from hades.graph_fitness import GraphFitnessScorer, GraphFitnessStore, GraphMetrics


def test_graph_fitness_score_success() -> None:
    scorer = GraphFitnessScorer()

    score = scorer.score(GraphMetrics(success=True, latency_ms=250.0, cost=0.01, token_usage=120))

    assert 0.8 < score <= 1.0


def test_graph_fitness_store_tracks_rolling_averages(tmp_path: Path) -> None:
    store = GraphFitnessStore(tmp_path / "graph_metrics.json")
    scorer = GraphFitnessScorer()

    first_score = scorer.score(GraphMetrics(success=True, latency_ms=100.0, cost=0.0, token_usage=50))
    second_score = scorer.score(GraphMetrics(success=False, latency_ms=1000.0, cost=0.2, token_usage=10))
    summary = store.record("graph_v1", GraphMetrics(success=True, latency_ms=100.0, cost=0.0, token_usage=50), first_score)
    summary = store.record("graph_v1", GraphMetrics(success=False, latency_ms=1000.0, cost=0.2, token_usage=10), second_score)

    assert summary.runs == 2
    assert 0.0 < summary.success_rate < 1.0
    assert summary.avg_latency_ms == 550.0
    assert summary.avg_tokens == 30.0


def test_graph_fitness_failure_threshold_flags_low_score(tmp_path: Path) -> None:
    scorer = GraphFitnessScorer(failure_threshold=0.5)
    score = scorer.score(GraphMetrics(success=False, latency_ms=50.0, cost=0.0, token_usage=0))
    store = GraphFitnessStore(tmp_path / "graph_metrics.json")
    summary = store.record("graph_v1", GraphMetrics(success=False, latency_ms=50.0, cost=0.0, token_usage=0), score)

    assert score < 0.5
    assert scorer.should_record_failure(summary) is True
