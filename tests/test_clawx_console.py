import json
from pathlib import Path

from modules.clawx_engine import clawx_console


def test_repo_summary_lists_expected_paths(tmp_path: Path) -> None:
    for name in ("modules", "tools", "vault"):
        (tmp_path / name).mkdir()

    lines = clawx_console.repo_summary(tmp_path)

    assert any("modules" in line for line in lines)
    assert any("tools" in line for line in lines)
    assert any("vault" in line for line in lines)


def test_module_summary_lists_python_modules(tmp_path: Path) -> None:
    module_dir = tmp_path / "modules" / "clawx_engine"
    module_dir.mkdir(parents=True)
    (module_dir / "clawx_engine.py").write_text("", encoding="utf-8")
    (module_dir / "signal_adapter.py").write_text("", encoding="utf-8")

    lines = clawx_console.module_summary(tmp_path)

    assert any("clawx_engine:" in line for line in lines)
    assert any("signal_adapter.py" in line for line in lines)


def test_health_summary_reads_cluster_and_policy_artifacts(tmp_path: Path) -> None:
    runtime = tmp_path / "vault" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "cluster_status.json").write_text(
        json.dumps(
            {
                "node": "hades",
                "role": "control",
                "services": {"scheduler": "active", "policy_daemon": "active"},
            }
        ),
        encoding="utf-8",
    )
    policy_dir = tmp_path / "vault" / "policy"
    policy_dir.mkdir(parents=True)
    (policy_dir / "scheduler_policy.json").write_text(
        json.dumps({"desired_state": "running", "reason": "manual override"}),
        encoding="utf-8",
    )
    cluster_dir = tmp_path / "cluster"
    cluster_dir.mkdir()
    (cluster_dir / "node_roles.json").write_text(
        json.dumps({"hades": {"role": "control"}, "atlas": {"role": "gpu_worker"}}),
        encoding="utf-8",
    )

    lines = clawx_console.health_summary(tmp_path)

    assert "node: hades" in lines
    assert "scheduler: active" in lines
    assert "policy_state: running" in lines
    assert any("atlas" in line for line in lines)


def test_proposal_summary_reflects_manual_override(tmp_path: Path) -> None:
    signals = tmp_path / "vault" / "runtime"
    signals.mkdir(parents=True)
    (signals / "signals.jsonl").write_text('{"type":"funding_rate_anomaly"}\n', encoding="utf-8")
    (signals / "clawx_log.jsonl").write_text('{"event":"signal_emitted"}\n', encoding="utf-8")
    policy_dir = tmp_path / "vault" / "policy"
    policy_dir.mkdir(parents=True)
    (policy_dir / "scheduler_policy.json").write_text(
        json.dumps({"updated_by": "operator", "desired_state": "running"}),
        encoding="utf-8",
    )

    lines = clawx_console.proposal_summary(tmp_path)

    assert any("manual override" in line for line in lines)
    assert any("recent_signals: 1" in line for line in lines)


def test_node_and_agent_views_read_cluster_topology(tmp_path: Path) -> None:
    runtime = tmp_path / "vault" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "cluster_topology.json").write_text(
        json.dumps(
            {
                "nodes": {
                    "hades": {"role": "control_plane", "agents": ["cluster_doctor", "investigation_agent"]},
                    "atlas": {"role": "gpu_inference", "agents": ["atlas_inference"]},
                }
            }
        ),
        encoding="utf-8",
    )

    node_lines = clawx_console.node_summary(tmp_path, hostname="hades")
    all_agent_lines = clawx_console.show_agents(tmp_path)
    atlas_agent_lines = clawx_console.show_agents(tmp_path, node="atlas")

    assert "node: hades" in node_lines
    assert "role: control_plane" in node_lines
    assert any("cluster_doctor" in line for line in node_lines)
    assert any("hades: cluster_doctor, investigation_agent" in line for line in all_agent_lines)
    assert atlas_agent_lines == ["Agents", "------", "atlas:", "- atlas_inference"]


def test_signal_and_evidence_cross_reference_helpers(tmp_path: Path) -> None:
    runtime = tmp_path / "vault" / "runtime"
    evidence_dir = tmp_path / "vault" / "evidence"
    runtime.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)
    (runtime / "signals.jsonl").write_text(
        json.dumps({"signal_id": "sig-1", "type": "latency_spike"}) + "\n",
        encoding="utf-8",
    )
    (evidence_dir / "evidence.jsonl").write_text(
        json.dumps({"signal_id": "sig-1", "agent": "investigation_agent", "root_cause": "queue"}) + "\n",
        encoding="utf-8",
    )

    evidence_lines = clawx_console.evidence_for_signal("sig-1", tmp_path)
    signal_lines = clawx_console.signals_for_agent("investigation_agent", tmp_path)

    assert any('"signal_id": "sig-1"' in line for line in evidence_lines)
    assert any('"type": "latency_spike"' in line for line in signal_lines)
