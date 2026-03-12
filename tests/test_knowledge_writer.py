from __future__ import annotations

from pathlib import Path

from memory.obsidian_bridge.knowledge_writer import (
    discover_tool_records,
    render_growth_focus,
    render_snapshot_index,
    render_tools_index,
    sync_tkai_knowledge,
)


def test_discover_tool_records_reads_docstrings(tmp_path: Path) -> None:
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "cluster_doctor.py").write_text(
        '"""Inspect the cluster health."""\n\nprint("ok")\n',
        encoding="utf-8",
    )

    records = discover_tool_records(tools_dir)

    assert records == [
        {
            "name": "cluster_doctor",
            "filename": "cluster_doctor.py",
            "summary": "Inspect the cluster health.",
            "command": "python tools/cluster_doctor.py",
            "source_path": str(tools_dir / "cluster_doctor.py"),
        }
    ]


def test_sync_tkai_knowledge_writes_hub_and_indexes(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    vault_root = tmp_path / "vault"
    (repo_root / "tools").mkdir(parents=True)
    (repo_root / "docs").mkdir()
    (repo_root / "snapshots" / "2026-03-12T20-34-31Z--baseline").mkdir(parents=True)
    (repo_root / "var" / "inventory" / "canonical-projects").mkdir(parents=True)

    (repo_root / "tools" / "cluster_doctor.py").write_text(
        '"""Inspect the cluster health."""\n',
        encoding="utf-8",
    )
    (repo_root / "docs" / "TKAI_CLUSTER_ARCHITECTURE.md").write_text("# Cluster Architecture\n", encoding="utf-8")
    (repo_root / "docs" / "ACME_TKAI_INTERFACE.md").write_text("# ACME Interface\n", encoding="utf-8")
    (repo_root / "docs" / "TKAI_SNAPSHOT_TIME_TRAVEL.md").write_text("# Snapshot Time Travel\n", encoding="utf-8")
    (repo_root / "var" / "inventory" / "canonical-projects" / "INDEX.md").write_text("# Canonical Inventory\n", encoding="utf-8")
    (repo_root / "snapshots" / "2026-03-12T20-34-31Z--baseline" / "manifest.json").write_text(
        '{"label": "baseline", "generated_at": "2026-03-12T20:34:31+00:00"}\n',
        encoding="utf-8",
    )

    written = sync_tkai_knowledge(repo_root, vault_root)

    assert written
    assert (vault_root / "INDEX.md").exists()
    assert (vault_root / "Architecture" / "TKAI_CLUSTER_ARCHITECTURE.md").exists()
    assert (vault_root / "Operations" / "TOOLS_INDEX.md").exists()
    assert (vault_root / "Tools" / "cluster_doctor.md").exists()
    assert (vault_root / "Knowledge" / "SNAPSHOTS.md").exists()
    assert "cluster_doctor" in (vault_root / "Operations" / "TOOLS_INDEX.md").read_text(encoding="utf-8")
    assert "baseline" in (vault_root / "Knowledge" / "SNAPSHOTS.md").read_text(encoding="utf-8")


def test_render_indexes_include_growth_and_snapshot_state(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "docs").mkdir(parents=True)
    (repo_root / "docs" / "TKAI_CLUSTER_ARCHITECTURE.md").write_text("# Cluster\n", encoding="utf-8")
    (repo_root / "docs" / "ACME_TKAI_INTERFACE.md").write_text("# ACME\n", encoding="utf-8")
    (repo_root / "docs" / "TKAI_SNAPSHOT_TIME_TRAVEL.md").write_text("# Snapshot\n", encoding="utf-8")

    tool_index = render_tools_index(
        [{"name": "cluster_doctor", "summary": "Inspect the cluster health.", "command": "python tools/cluster_doctor.py", "filename": "cluster_doctor.py", "source_path": "/tmp/cluster_doctor.py"}]
    )
    snapshot_index = render_snapshot_index([{"name": "2026-03-12T20-34-31Z--baseline", "label": "baseline", "generated_at": "2026-03-12T20:34:31+00:00"}])
    growth = render_growth_focus(
        repo_root,
        [{"name": "cluster_doctor", "summary": "Inspect the cluster health.", "command": "python tools/cluster_doctor.py", "filename": "cluster_doctor.py", "source_path": "/tmp/cluster_doctor.py"}],
        [{"name": "2026-03-12T20-34-31Z--baseline", "label": "baseline", "generated_at": "2026-03-12T20:34:31+00:00"}],
    )

    assert "[[Tools/cluster_doctor|cluster_doctor]]" in tool_index
    assert "baseline" in snapshot_index
    assert "TK-Ai is the kernel focus." in growth
