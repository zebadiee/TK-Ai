import json
from pathlib import Path

from tools import load_topology, promote_agent


def test_promote_adds_discovered_agent_to_registry(tmp_path: Path, capsys) -> None:
    registry_path = tmp_path / "agent_registry.json"
    discovered_path = tmp_path / "discovered_agents.json"
    registry_path.write_text(json.dumps({"existing": {"node": "hades", "entrypoint": "/tmp/existing.py"}}), encoding="utf-8")
    discovered_path.write_text(
        json.dumps({"arch_scan": {"node": "hades", "entrypoint": "/tmp/arch_scan.py"}}),
        encoding="utf-8",
    )

    result = promote_agent.promote("arch_scan", registry_path=registry_path, discovered_path=discovered_path)
    output = capsys.readouterr().out
    registry = json.loads(registry_path.read_text(encoding="utf-8"))

    assert result is True
    assert "Promoted agent: arch_scan" in output
    assert registry["arch_scan"]["entrypoint"] == "/tmp/arch_scan.py"
    assert registry["existing"]["entrypoint"] == "/tmp/existing.py"


def test_promote_returns_false_for_unknown_candidate(tmp_path: Path, capsys) -> None:
    registry_path = tmp_path / "agent_registry.json"
    discovered_path = tmp_path / "discovered_agents.json"
    registry_path.write_text("{}", encoding="utf-8")
    discovered_path.write_text("{}", encoding="utf-8")

    result = promote_agent.promote("missing", registry_path=registry_path, discovered_path=discovered_path)
    output = capsys.readouterr().out

    assert result is False
    assert "Agent not found in discovery list: missing" in output


def test_load_topology_reads_nodes(tmp_path: Path) -> None:
    topology_path = tmp_path / "cluster_topology.json"
    topology_path.write_text(
        json.dumps({"nodes": {"atlas": {"role": "gpu_inference", "agents": ["atlas_inference"]}}}),
        encoding="utf-8",
    )

    topology = load_topology.load_topology(path=topology_path)

    assert topology["nodes"]["atlas"]["agents"] == ["atlas_inference"]
