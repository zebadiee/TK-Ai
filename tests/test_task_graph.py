from atlas.executor import AtlasExecutor
from hades.task_graph import TaskGraph, TaskGraphRunner, TaskNode


class RecordingExecutor:
    def __init__(self) -> None:
        self.calls = []

    def execute(self, action, payload):
        self.calls.append(action)
        if action == "fail":
            return {"status": "failed", "action": action}
        if action == "async":
            return {"status": "accepted", "action": action, "job_id": "job-1"}
        return {"status": "ok", "action": action}


def test_task_graph_runner_executes_nodes_in_order():
    executor = RecordingExecutor()
    runner = TaskGraphRunner(executor)
    graph = TaskGraph(
        graph_id="g1",
        nodes=[
            TaskNode(node_id="one", action="first"),
            TaskNode(node_id="two", action="second"),
        ],
    )

    state = runner.run(graph, trace_id="trace-1")

    assert executor.calls == ["first", "second"]
    assert state.completed is True
    assert state.node_status == {"one": "ok", "two": "ok"}


def test_task_graph_runner_stops_on_failure():
    executor = RecordingExecutor()
    runner = TaskGraphRunner(executor)
    graph = TaskGraph(
        graph_id="g1",
        nodes=[
            TaskNode(node_id="one", action="first"),
            TaskNode(node_id="two", action="fail"),
            TaskNode(node_id="three", action="never"),
        ],
    )

    state = runner.run(graph, trace_id="trace-1")

    assert executor.calls == ["first", "fail"]
    assert state.completed is False
    assert "three" not in state.node_status


def test_task_graph_runner_can_use_notify_placeholder():
    runner = TaskGraphRunner(AtlasExecutor())
    graph = TaskGraph(
        graph_id="g1",
        nodes=[TaskNode(node_id="notify", action="notify", payload={"channel": "telegram", "message": "hi"})],
    )

    state = runner.run(graph, trace_id="trace-1")

    assert state.completed is True
    assert state.node_results["notify"]["channel"] == "telegram"


def test_task_graph_runner_pauses_on_async_node():
    executor = RecordingExecutor()
    runner = TaskGraphRunner(executor)
    graph = TaskGraph(
        graph_id="g1",
        nodes=[
            TaskNode(node_id="monitor", action="async"),
            TaskNode(node_id="notify", action="notify"),
        ],
    )

    state = runner.run(graph, trace_id="trace-1")

    assert state.completed is False
    assert state.node_status["monitor"] == "pending"
    assert state.pending_jobs["job-1"] == "monitor"
    assert "notify" not in state.node_status
