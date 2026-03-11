"""Serial task graph loading and execution for HADES."""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TaskNode:
    node_id: str
    action: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskGraph:
    graph_id: str
    nodes: list[TaskNode]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphRunState:
    graph_id: str
    current_node_id: str | None = None
    node_status: dict[str, str] = field(default_factory=dict)
    results: dict[str, dict[str, Any]] = field(default_factory=dict)
    pending_jobs: dict[str, str] = field(default_factory=dict)
    trace_id: str | None = None
    completed: bool = False

    @property
    def node_results(self) -> dict[str, dict[str, Any]]:
        return self.results

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphRunState:
        return cls(
            graph_id=str(data.get("graph_id", "")),
            current_node_id=data.get("current_node_id"),
            node_status=dict(data.get("node_status", {})),
            results=dict(data.get("results", data.get("node_results", {}))),
            pending_jobs=dict(data.get("pending_jobs", {})),
            trace_id=data.get("trace_id"),
            completed=bool(data.get("completed", False)),
        )


def load_solution_graphs(path: str | Path) -> dict[str, TaskGraph]:
    graph_path = Path(path)
    if not graph_path.exists():
        return {}

    with graph_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        return {}

    raw_graphs = data.get("graphs", {})
    if not isinstance(raw_graphs, dict):
        return {}

    graphs: dict[str, TaskGraph] = {}
    for graph_id, record in raw_graphs.items():
        if not isinstance(record, dict):
            continue

        raw_nodes = record.get("nodes", [])
        if not isinstance(raw_nodes, list):
            continue

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

        metadata = record.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        if nodes:
            graphs[str(graph_id)] = TaskGraph(
                graph_id=str(graph_id),
                nodes=nodes,
                metadata=metadata,
            )

    return graphs


class TaskGraphRunner:
    """Runs a task graph serially and stops on the first failure."""

    SUCCESS_STATUSES = {"ok", "dispatched", "ignored"}
    ASYNC_STATUSES = {"accepted"}

    def __init__(self, executor: Any) -> None:
        self.executor = executor

    def _node_index(self, graph: TaskGraph, node_id: str) -> int:
        for index, node in enumerate(graph.nodes):
            if node.node_id == node_id:
                return index
        raise ValueError(f"Unknown node_id {node_id!r} in graph {graph.graph_id}")

    def _next_node_id(self, graph: TaskGraph, node_id: str) -> str | None:
        index = self._node_index(graph, node_id)
        if index + 1 >= len(graph.nodes):
            return None
        return graph.nodes[index + 1].node_id

    def run_once(
        self,
        graph: TaskGraph,
        state: GraphRunState,
        base_payload: dict[str, Any] | None = None,
    ) -> GraphRunState:
        shared_payload = copy.deepcopy(base_payload) if isinstance(base_payload, dict) else {}
        if state.trace_id is None:
            state.trace_id = str(shared_payload.get("trace_id", ""))

        if state.current_node_id is None:
            start_index = 0
        else:
            start_index = self._node_index(graph, state.current_node_id)

        for node in graph.nodes[start_index:]:
            state.current_node_id = node.node_id
            payload = copy.deepcopy(shared_payload)
            payload.update(copy.deepcopy(node.payload))
            payload.setdefault("trace_id", state.trace_id)
            payload.setdefault("graph_node_id", node.node_id)
            result = self.executor.execute(node.action, payload)

            state.results[node.node_id] = result
            status = str(result.get("status", "unknown"))

            if status in self.ASYNC_STATUSES:
                job_id = str(result.get("job_id", "")).strip()
                if job_id:
                    state.pending_jobs[job_id] = node.node_id
                state.node_status[node.node_id] = "pending"
                state.completed = False
                return state

            state.node_status[node.node_id] = status
            if status not in self.SUCCESS_STATUSES:
                state.completed = False
                return state

        state.current_node_id = None
        state.completed = True
        return state

    def run(
        self,
        graph: TaskGraph,
        trace_id: str,
        base_payload: dict[str, Any] | None = None,
    ) -> GraphRunState:
        shared_payload = copy.deepcopy(base_payload) if isinstance(base_payload, dict) else {}
        shared_payload.setdefault("trace_id", trace_id)
        state = GraphRunState(graph_id=graph.graph_id, trace_id=trace_id)
        return self.run_once(graph, state, shared_payload)
