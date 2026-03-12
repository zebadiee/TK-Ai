import json
from pathlib import Path

from tools import clawx_autonomy, clawx_scheduler


def test_emit_exploration_cycle_emits_signals_for_each_node(tmp_path: Path) -> None:
    state_path = tmp_path / "autonomy_state.json"
    signal_path = tmp_path / "signals.jsonl"
    log_path = tmp_path / "clawx_log.jsonl"
    topology = {
        "nodes": {
            "hades": {"role": "control_plane", "agents": ["cluster_doctor"]},
            "atlas": {"role": "gpu_inference", "agents": ["atlas_inference"]},
            "hermes": {"role": "infrastructure_backbone", "agents": []},
        }
    }

    emitted = clawx_autonomy.emit_exploration_cycle(
        topology,
        cooldown=900,
        state_path=state_path,
        signal_path=signal_path,
        log_path=log_path,
        now=1234,
    )

    assert [signal["type"] for signal in emitted] == [
        "gpu_inference_exploration",
        "control_plane_exploration",
        "infrastructure_exploration",
    ]
    rows = [json.loads(line) for line in signal_path.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["payload"]["node"] == "atlas"
    assert rows[1]["payload"]["node"] == "hades"
    assert rows[2]["payload"]["node"] == "hermes"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["cycles"] == 1
    assert state["last_emit_by_node"] == {"atlas": 1234, "hades": 1234, "hermes": 1234}


def test_emit_exploration_cycle_respects_cooldown(tmp_path: Path) -> None:
    state_path = tmp_path / "autonomy_state.json"
    signal_path = tmp_path / "signals.jsonl"
    topology = {"nodes": {"hades": {"role": "control_plane", "agents": []}}}

    first = clawx_autonomy.emit_exploration_cycle(
        topology,
        cooldown=900,
        state_path=state_path,
        signal_path=signal_path,
        now=100,
    )
    second = clawx_autonomy.emit_exploration_cycle(
        topology,
        cooldown=900,
        state_path=state_path,
        signal_path=signal_path,
        now=200,
    )

    assert len(first) == 1
    assert second == []


def test_scheduler_routes_exploration_signals_to_missions() -> None:
    calls: list[list[str]] = []

    class StubResult:
        def __init__(self, returncode: int = 0, stdout: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout

    def runner(command, **kwargs):
        calls.append(command)
        return StubResult()

    invoked = clawx_scheduler.process_signals(
        [
            {"type": "control_plane_exploration"},
            {"type": "gpu_inference_exploration"},
            {"type": "infrastructure_exploration"},
        ],
        runner=runner,
    )

    assert invoked == [
        ("control_plane_exploration", "control_plane_exploration"),
        ("gpu_inference_exploration", "inference_node_exploration"),
        ("infrastructure_exploration", "gateway_node_exploration"),
    ]
    assert calls[0][-1] == "control_plane_exploration"
    assert calls[1][-1] == "inference_node_exploration"
    assert calls[2][-1] == "gateway_node_exploration"
