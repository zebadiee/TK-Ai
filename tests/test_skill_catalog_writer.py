from __future__ import annotations

from pathlib import Path

from memory.obsidian_bridge.skill_catalog_writer import render_changelog, render_index, render_skill_note, sync_skill_catalog


def test_render_skill_note_contains_provenance_and_visibility() -> None:
    content = render_skill_note(
        {
            "slug": "snapshot-state",
            "name": "snapshot-state",
            "status": "beta",
            "last_updated": "2026-03-12T20:00:00+00:00",
            "source_path": "/skills/snapshot-state",
            "spec_path": "/skills/snapshot-state/SKILL.md",
            "execution_paths": ["python tools/snapshot_state.py --label alpha"],
            "generator": "skill-creator",
            "checker": "tool_creation_checker",
            "checker_result": "pass",
            "cluster_visibility": {"hades": True, "hermes": True, "atlas": True},
            "promotion_history": [{"timestamp": "2026-03-12T20:00:00+00:00", "summary": "promoted from experimental to beta"}],
        }
    )

    assert "Status: beta" in content
    assert "- checker: `tool_creation_checker`" in content
    assert "- HERMES: yes" in content


def test_sync_skill_catalog_writes_index_and_changelog(tmp_path: Path) -> None:
    skills = [
        {
            "slug": "snapshot-state",
            "name": "snapshot-state",
            "status": "beta",
            "last_updated": "2026-03-12T20:00:00+00:00",
            "source_path": "/skills/snapshot-state",
            "spec_path": "/skills/snapshot-state/SKILL.md",
            "execution_paths": ["python tools/snapshot_state.py --label alpha"],
            "generator": "skill-creator",
            "checker": "tool_creation_checker",
            "checker_result": "pass",
            "cluster_visibility": {"hades": True, "hermes": True, "atlas": True},
            "promotion_history": [],
        }
    ]
    events = [{"timestamp": "2026-03-12T20:00:00+00:00", "skill": "snapshot-state", "summary": "promoted from experimental to beta"}]

    sync_skill_catalog(skills, events, tmp_path)

    assert (tmp_path / "Skills" / "snapshot-state.md").exists()
    index = (tmp_path / "Skills" / "Index.md").read_text(encoding="utf-8")
    changelog = (tmp_path / "Skills" / "Changelog.md").read_text(encoding="utf-8")
    assert "[[Skills/snapshot-state|snapshot-state]]" in index
    assert "Production-Ready Candidates" in index
    assert "promoted from experimental to beta" in changelog


def test_render_index_and_changelog_handle_empty_lists() -> None:
    assert "Tracked skills: 0" in render_index([])
    assert "no skill events recorded" in render_changelog([])
