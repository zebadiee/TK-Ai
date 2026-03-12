from __future__ import annotations

import json
from pathlib import Path

from tools import hades_assist_launcher


def _create_skill(skills_root: Path, slug: str, description: str = "desc") -> Path:
    skill_dir = skills_root / slug
    (skill_dir / "agents").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {slug}\ndescription: {description}\n---\n\npython tools/{slug.replace('-', '_')}.py\n",
        encoding="utf-8",
    )
    (skill_dir / "agents" / "openai.yaml").write_text("interface:\n  display_name: test\n", encoding="utf-8")
    return skill_dir


def test_discover_governed_skills_filters_invalid_and_system_dirs(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills"
    skills_root.mkdir()
    _create_skill(skills_root, "snapshot-state")
    (skills_root / ".system").mkdir()
    (skills_root / "broken").mkdir()

    discovered = hades_assist_launcher.discover_governed_skills(skills_root)

    assert [skill["slug"] for skill in discovered] == ["snapshot-state"]
    assert discovered[0]["checker_result"] == "pass"


def test_reconcile_skill_state_records_discovery_and_promotion(monkeypatch) -> None:
    monkeypatch.setattr(
        hades_assist_launcher,
        "load_cluster_nodes",
        lambda: {"hades": object(), "hermes": object(), "atlas": object()},
    )
    monkeypatch.setattr(hades_assist_launcher, "current_timestamp", lambda: "2026-03-12T20:00:00+00:00")

    reconciled, events, state = hades_assist_launcher.reconcile_skill_state(
        [
            {
                "slug": "snapshot-state",
                "name": "snapshot-state",
                "source_path": "/skills/snapshot-state",
                "spec_path": "/skills/snapshot-state/SKILL.md",
                "execution_paths": ["python tools/snapshot_state.py"],
                "generator": "skill-creator",
                "checker": "tool_creation_checker",
                "checker_result": "pass",
                "last_updated": "2026-03-12T19:00:00+00:00",
            }
        ],
        {"skills": {}, "events": []},
        promotions={"snapshot-state": "beta"},
    )

    assert reconciled[0]["status"] == "beta"
    assert any("discovered and catalogued as experimental" in event["summary"] for event in events)
    assert any("promoted from experimental to beta" in event["summary"] for event in events)
    assert state["skills"]["snapshot-state"]["status"] == "beta"


def test_write_runtime_artifacts_writes_cluster_registries(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(hades_assist_launcher, "REGISTRY_PATH", tmp_path / "hades_assist_skill_registry.json")
    monkeypatch.setattr(hades_assist_launcher, "EVENT_LOG_PATH", tmp_path / "hades_assist_events.jsonl")
    monkeypatch.setattr(hades_assist_launcher, "NODE_REGISTRY_TEMPLATE", tmp_path / "{node}_skill_registry.json")
    monkeypatch.setattr(hades_assist_launcher, "current_timestamp", lambda: "2026-03-12T20:00:00+00:00")

    hades_assist_launcher.write_runtime_artifacts(
        [{"slug": "snapshot-state", "status": "beta"}],
        [{"timestamp": "2026-03-12T20:00:00+00:00", "skill": "snapshot-state", "summary": "promoted"}],
    )

    registry = json.loads((tmp_path / "hades_assist_skill_registry.json").read_text(encoding="utf-8"))
    atlas = json.loads((tmp_path / "atlas_skill_registry.json").read_text(encoding="utf-8"))
    hermes = json.loads((tmp_path / "hermes_skill_registry.json").read_text(encoding="utf-8"))

    assert registry["skills"][0]["slug"] == "snapshot-state"
    assert atlas["node"] == "atlas"
    assert hermes["node"] == "hermes"


def test_write_model_artifacts_writes_policy_and_selection(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(hades_assist_launcher, "current_timestamp", lambda: "2026-03-12T20:00:00+00:00")

    written = hades_assist_launcher.write_model_artifacts(
        intent="sync the obsidian knowledge index",
        route_payload={"backend": "ollama", "model": "mistral"},
        state={"free_models": {}, "paid_backend": "paid", "paid_model": "paid-premium"},
        path=tmp_path / "policy.json",
        selection_path=tmp_path / "selection.json",
    )

    assert tmp_path / "policy.json" in written
    assert tmp_path / "selection.json" in written
    selection = json.loads((tmp_path / "selection.json").read_text(encoding="utf-8"))
    assert selection["route"]["backend"] == "ollama"
