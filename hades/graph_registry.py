"""Versioned graph registry for trusted and experimental workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hades.task_graph import TaskGraph, TaskNode


def _graph_from_dict(graph_id: str, data: dict[str, Any]) -> TaskGraph | None:
    if not isinstance(data, dict):
        return None

    raw_nodes = data.get("nodes", [])
    if not isinstance(raw_nodes, list):
        return None

    nodes = []
    for raw_node in raw_nodes:
        if not isinstance(raw_node, dict):
            continue
        node_id = str(raw_node.get("node_id", "")).strip()
        action = str(raw_node.get("action", "")).strip()
        payload = raw_node.get("payload", {})
        if not node_id or not action:
            continue
        if not isinstance(payload, dict):
            payload = {}
        nodes.append(TaskNode(node_id=node_id, action=action, payload=payload))

    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    if not nodes:
        return None
    return TaskGraph(graph_id=graph_id, nodes=nodes, metadata=metadata)


def _graph_to_dict(graph: TaskGraph) -> dict[str, Any]:
    return {
        "metadata": graph.metadata,
        "nodes": [
            {"node_id": node.node_id, "action": node.action, "payload": node.payload}
            for node in graph.nodes
        ],
    }


class GraphRegistry:
    """Loads active graph versions and manages promotion and rollback."""

    def __init__(
        self,
        index: dict[str, Any] | None,
        graph_dir: str | Path,
        index_path: str | Path | None = None,
    ) -> None:
        self.index = index if isinstance(index, dict) else {}
        self.graph_dir = Path(graph_dir)
        self.index_path = Path(index_path) if index_path is not None else None

    @classmethod
    def from_paths(cls, index_path: str | Path, graph_dir: str | Path) -> "GraphRegistry":
        path = Path(index_path)
        if not path.exists():
            return cls({}, graph_dir, path)

        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        if not isinstance(data, dict):
            data = {}
        return cls(data, graph_dir, path)

    def save(self, index_path: str | Path | None = None) -> None:
        path = Path(index_path) if index_path is not None else self.index_path
        if path is None:
            raise ValueError("Graph registry save path is not configured")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(self.index, handle, indent=2, sort_keys=True)

    def load_active(self, graph_name: str) -> TaskGraph | None:
        record = self.index.get(graph_name, {})
        if not isinstance(record, dict):
            return None

        version_id = str(record.get("active", "")).strip()
        if not version_id:
            return None
        return self.load_version(version_id)

    def load_version(self, version_id: str) -> TaskGraph | None:
        path = self.graph_dir / f"{version_id}.json"
        if not path.exists():
            return None

        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return _graph_from_dict(version_id, data)

    def resolve(self, graph_id: str) -> TaskGraph | None:
        graph = self.load_active(graph_id)
        if graph is not None:
            return graph
        return self.load_version(graph_id)

    def graph_name_for_version(self, version_id: str) -> str | None:
        for graph_name, record in self.index.items():
            if not isinstance(record, dict):
                continue
            versions = record.get("versions", [])
            if isinstance(versions, list) and version_id in versions:
                return str(graph_name)
        return None

    def register_version(
        self,
        graph_name: str,
        graph: TaskGraph,
        version_id: str,
        experimental: bool = True,
    ) -> None:
        self.graph_dir.mkdir(parents=True, exist_ok=True)
        path = self.graph_dir / f"{version_id}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(_graph_to_dict(graph), handle, indent=2, sort_keys=True)

        record = self.index.setdefault(
            graph_name,
            {
                "active": "",
                "versions": [],
                "experimental": [],
                "history": [],
                "failure_count": 0,
            },
        )
        versions = record.setdefault("versions", [])
        if version_id not in versions:
            versions.append(version_id)

        experimental_versions = record.setdefault("experimental", [])
        if experimental and version_id not in experimental_versions:
            experimental_versions.append(version_id)

        if not record.get("active"):
            record["active"] = version_id
            record.setdefault("history", []).append(version_id)

    def promote_version(self, graph_name: str, version_id: str) -> None:
        record = self.index.setdefault(graph_name, {"active": "", "versions": []})
        versions = record.setdefault("versions", [])
        if version_id not in versions:
            raise ValueError(f"Unknown version {version_id!r} for graph family {graph_name!r}")

        record["active"] = version_id
        record["failure_count"] = 0
        history = record.setdefault("history", [])
        if version_id not in history:
            history.append(version_id)

        experimental_versions = record.setdefault("experimental", [])
        if version_id in experimental_versions:
            experimental_versions.remove(version_id)

    def rollback(self, graph_name: str) -> str | None:
        record = self.index.get(graph_name, {})
        if not isinstance(record, dict):
            return None

        versions = record.get("versions", [])
        active = record.get("active")
        if not isinstance(versions, list) or active not in versions:
            return None

        active_index = versions.index(active)
        if active_index <= 0:
            return None

        previous = versions[active_index - 1]
        record["active"] = previous
        record["failure_count"] = 0
        return previous

    def record_failure(self, graph_name: str, threshold: int = 3) -> str | None:
        record = self.index.get(graph_name, {})
        if not isinstance(record, dict):
            return None

        record["failure_count"] = int(record.get("failure_count", 0)) + 1
        if int(record["failure_count"]) >= threshold:
            return self.rollback(graph_name)
        return None
