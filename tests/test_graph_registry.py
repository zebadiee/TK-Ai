from __future__ import annotations

import json
from pathlib import Path

from hades.graph_registry import GraphRegistry
from hades.task_graph import TaskGraph, TaskNode


def _write_graph(path: Path, purpose: str) -> None:
    path.write_text(
        json.dumps(
            {
                "metadata": {"purpose": purpose},
                "nodes": [
                    {
                        "node_id": "notify",
                        "action": "notify",
                        "payload": {"channel": "telegram", "message": purpose},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_graph_registry_loads_active_version(tmp_path: Path) -> None:
    graph_dir = tmp_path / "solution_graphs"
    graph_dir.mkdir()
    _write_graph(graph_dir / "btc_monitor_v1.json", "v1")
    index_path = tmp_path / "graph_index.json"
    index_path.write_text(
        json.dumps(
            {
                "btc_monitor": {
                    "active": "btc_monitor_v1",
                    "versions": ["btc_monitor_v1"],
                    "experimental": [],
                    "history": ["btc_monitor_v1"],
                    "failure_count": 0,
                }
            }
        ),
        encoding="utf-8",
    )

    registry = GraphRegistry.from_paths(index_path, graph_dir)
    graph = registry.load_active("btc_monitor")

    assert graph is not None
    assert graph.graph_id == "btc_monitor_v1"
    assert graph.metadata["purpose"] == "v1"


def test_graph_registry_promotes_new_version(tmp_path: Path) -> None:
    graph_dir = tmp_path / "solution_graphs"
    registry = GraphRegistry({}, graph_dir)
    base_graph = TaskGraph(
        graph_id="btc_monitor",
        metadata={"purpose": "baseline"},
        nodes=[TaskNode(node_id="notify", action="notify", payload={"message": "v1"})],
    )
    candidate_graph = TaskGraph(
        graph_id="btc_monitor",
        metadata={"purpose": "candidate"},
        nodes=[TaskNode(node_id="notify", action="notify", payload={"message": "v2"})],
    )

    registry.register_version("btc_monitor", base_graph, "btc_monitor_v1", experimental=False)
    registry.register_version("btc_monitor", candidate_graph, "btc_monitor_v2", experimental=True)
    registry.promote_version("btc_monitor", "btc_monitor_v2")

    assert registry.index["btc_monitor"]["active"] == "btc_monitor_v2"
    assert "btc_monitor_v2" not in registry.index["btc_monitor"]["experimental"]
    assert registry.load_active("btc_monitor").metadata["purpose"] == "candidate"


def test_graph_registry_rolls_back_on_failure(tmp_path: Path) -> None:
    graph_dir = tmp_path / "solution_graphs"
    registry = GraphRegistry({}, graph_dir)
    v1_graph = TaskGraph(
        graph_id="btc_monitor",
        metadata={"purpose": "stable"},
        nodes=[TaskNode(node_id="notify", action="notify", payload={"message": "v1"})],
    )
    v2_graph = TaskGraph(
        graph_id="btc_monitor",
        metadata={"purpose": "experimental"},
        nodes=[TaskNode(node_id="notify", action="notify", payload={"message": "v2"})],
    )

    registry.register_version("btc_monitor", v1_graph, "btc_monitor_v1", experimental=False)
    registry.register_version("btc_monitor", v2_graph, "btc_monitor_v2", experimental=True)
    registry.promote_version("btc_monitor", "btc_monitor_v2")

    rolled_back = registry.record_failure("btc_monitor", threshold=1)

    assert rolled_back == "btc_monitor_v1"
    assert registry.index["btc_monitor"]["active"] == "btc_monitor_v1"
    assert registry.index["btc_monitor"]["failure_count"] == 0
