import json
from pathlib import Path

from tools import generate_topology, mission_runner


class StubResult:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode


def test_generate_topology_groups_agents_by_node(tmp_path: Path) -> None:
    registry_path = tmp_path / "agent_registry.json"
    cluster_config_path = tmp_path / "cluster_config.json"
    registry_path.write_text(
        json.dumps(
            {
                "cluster_doctor": {"node": "hades", "entrypoint": "/tmp/cluster_doctor.py"},
                "atlas_inference": {"node": "atlas", "entrypoint": "/tmp/atlas.py"},
                "custom": {"node": "custom-node", "entrypoint": "/tmp/custom.py"},
            }
        ),
        encoding="utf-8",
    )
    cluster_config_path.write_text(
        json.dumps(
            {
                "cluster": {
                    "hades": {"role": "control"},
                    "atlas": {"role": "gpu_worker", "ip": "192.168.1.17"},
                    "hermes": {"role": "gateway"},
                }
            }
        ),
        encoding="utf-8",
    )

    original = generate_topology.CLUSTER_CONFIG
    generate_topology.CLUSTER_CONFIG = cluster_config_path
    try:
        topology = generate_topology.generate_topology(registry_path=registry_path)
    finally:
        generate_topology.CLUSTER_CONFIG = original

    assert topology["nodes"]["hades"]["role"] == "control_plane"
    assert topology["nodes"]["atlas"]["role"] == "gpu_inference"
    assert topology["nodes"]["hermes"]["role"] == "infrastructure_backbone"
    assert topology["nodes"]["atlas"]["host"] == "atlas"
    assert topology["nodes"]["atlas"]["ssh_target"] == "192.168.1.17"
    assert topology["nodes"]["hermes"]["agents"] == []
    assert topology["nodes"]["custom-node"]["role"] == "worker"
    assert topology["nodes"]["custom-node"]["host"] == "custom-node"
    assert topology["nodes"]["hades"]["agents"] == ["cluster_doctor"]


def test_mission_runner_invokes_each_step(tmp_path: Path) -> None:
    missions_path = tmp_path / "missions.json"
    missions_path.write_text(
        json.dumps(
            {
                "control_plane_health": {
                    "steps": [
                        {"agent": "cluster_doctor"},
                        {"agent": "acme_governance", "args": ["status"]},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    def runner(command, **kwargs):
        calls.append(command)
        return StubResult(0)

    results = mission_runner.run_mission("control_plane_health", missions_path=missions_path, runner=runner)

    assert results == [
        {"agent": "cluster_doctor", "args": [], "returncode": 0},
        {"agent": "acme_governance", "args": ["status"], "returncode": 0},
    ]
    assert calls[0][-1] == "cluster_doctor"
    assert calls[1][-2:] == ["acme_governance", "status"]


def test_mission_runner_main_errors_for_unknown_mission(monkeypatch, capsys) -> None:
    monkeypatch.setattr(mission_runner.sys, "argv", ["mission_runner.py", "missing"])
    monkeypatch.setattr(
        mission_runner,
        "run_mission",
        lambda name, missions_path=mission_runner.MISSIONS, runner=mission_runner.subprocess.run: (_ for _ in ()).throw(KeyError("unknown mission: missing")),
    )

    result = mission_runner.main()
    stderr = capsys.readouterr().err

    assert result == 1
    assert "unknown mission: missing" in stderr
