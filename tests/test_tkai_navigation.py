import json
from pathlib import Path

from tools import tkai_map, tkai_navigate


def test_list_nodes_and_agents_from_topology() -> None:
    topology = {
        "nodes": {
            "atlas": {"role": "gpu_inference", "agents": ["atlas_inference"]},
            "hades": {"role": "control_plane", "agents": ["cluster_doctor", "investigation_agent"]},
        }
    }
    registry = {
        "cluster_doctor": {"node": "hades", "entrypoint": "/tmp/cluster_doctor.py"},
        "atlas_inference": {"node": "atlas", "entrypoint": "/tmp/atlas.py"},
    }

    node_lines = tkai_navigate.list_nodes(topology)
    agent_lines = tkai_navigate.list_agents(topology, registry)
    describe_lines = tkai_navigate.describe_agent("cluster_doctor", registry)

    assert any("hades: role=control_plane agents=2" in line for line in node_lines)
    assert any("atlas_inference: node=atlas" in line for line in agent_lines)
    assert "agent: cluster_doctor" in describe_lines
    assert any("python3 tools/invoke_agent.py cluster_doctor" in line for line in describe_lines)


def test_evidence_and_signal_navigation_helpers(tmp_path: Path) -> None:
    signals = tmp_path / "signals.jsonl"
    evidence = tmp_path / "evidence.jsonl"
    signals.write_text(
        "\n".join(
            [
                json.dumps({"signal_id": "sig-1", "type": "latency_spike"}),
                json.dumps({"signal_id": "sig-2", "type": "router_test"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    evidence.write_text(
        "\n".join(
            [
                json.dumps({"signal_id": "sig-1", "agent": "investigation_agent", "node": "atlas"}),
                json.dumps({"signal_id": "sig-2", "agent": "cluster_doctor", "node": "hades"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    evidence_lines = tkai_navigate.evidence_for_signal("sig-1", evidence_path=evidence)
    signal_lines = tkai_navigate.signals_for_agent("cluster_doctor", signals_path=signals, evidence_path=evidence)

    assert any('"signal_id": "sig-1"' in line for line in evidence_lines)
    assert any('"signal_id": "sig-2"' in line for line in signal_lines)


def test_render_map_prints_compact_cluster_view(monkeypatch) -> None:
    monkeypatch.setattr(
        tkai_map,
        "load_topology",
        lambda: {
            "nodes": {
                "hades": {"role": "control_plane", "agents": ["cluster_doctor", "investigation_agent"]},
                "atlas": {"role": "gpu_inference", "agents": ["atlas_inference"]},
            }
        },
    )

    lines = tkai_map.render_map()

    assert lines[0] == "TK-AI Cluster Map"
    assert any("hades [control_plane]" in line for line in lines)
    assert any("atlas [gpu_inference]" in line for line in lines)
