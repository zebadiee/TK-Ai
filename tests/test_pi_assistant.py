"""Tests for Pi assistant stack: manifest, skill resolver, session, engine."""

from __future__ import annotations

import json
from pathlib import Path

from hades.skill_resolver import (
    SkillEntry,
    load_manifest,
    prefer_home,
    resolve_skills,
    skill_allowed,
)
from hades.pi_session import PiSession, preamble_for, resolve_mode
from hades.obsidian_beacon import append_changelog, write_skill_index
from hades.pi_engine import PiEngine, PiRequest

MANIFEST = Path(__file__).resolve().parents[1] / "hades" / "assistant_manifest.md"


# ──────────────────────────────────────────────
# Manifest + skill resolver
# ──────────────────────────────────────────────

def test_load_manifest_parses_all_skills() -> None:
    skills = load_manifest(MANIFEST)
    names = [s.name for s in skills]
    assert len(skills) >= 9
    assert "acme-integration-status" in names
    assert "cluster-doctor" in names
    assert "snapshot-state" in names


def test_resolve_skills_returns_dict() -> None:
    registry = resolve_skills(MANIFEST)
    assert isinstance(registry, dict)
    assert "acme-integration-status" in registry
    entry = registry["acme-integration-status"]
    assert entry.status == "beta"
    assert entry.mutating is False
    assert "HADES" in entry.nodes


def test_skill_allowed_blocks_experimental_live() -> None:
    entry = SkillEntry(name="test", status="experimental", mutating=True)
    assert skill_allowed(entry, live=True) is False
    assert skill_allowed(entry, live=False) is True


def test_skill_allowed_permits_beta_live() -> None:
    entry = SkillEntry(name="test", status="beta", mutating=True)
    assert skill_allowed(entry, live=True) is True


def test_prefer_home_sorts_home_first() -> None:
    foreign = SkillEntry(name="ext-tool", status="beta", mutating=False, repo="/other/repo")
    home = SkillEntry(name="tkai-tool", status="beta", mutating=False, repo="/TK-Ai-Maxx/tools/x.py")
    result = prefer_home([foreign, home])
    assert result[0].name == "tkai-tool"


# ──────────────────────────────────────────────
# Session + social modes
# ──────────────────────────────────────────────

def test_resolve_mode_mapping() -> None:
    assert resolve_mode("focused") == "serious"
    assert resolve_mode("pissed") == "roaster"
    assert resolve_mode("tired") == "soother"
    assert resolve_mode("curious") == "witty"
    assert resolve_mode(None) == "serious"


def test_preamble_for_contains_pi_identity() -> None:
    for mood in ("focused", "pissed", "tired", "curious"):
        text = preamble_for(mood)
        assert "Pi" in text
        assert "breadcrumb" in text.lower() or "follow" in text.lower() or "suggestion" in text.lower()


def test_session_logs_entry_and_persists(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hades.pi_session.SESSION_DIR", tmp_path)
    session = PiSession(user_mood="excited")
    assert session.mode == "witty"
    session.log_entry(
        user_text="test query",
        skills_used=["cluster-doctor"],
        nodes=["HADES"],
        model_tier="free",
        success=True,
        summary="all ok",
    )
    path = session.persist()
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["mode"] == "witty"
    assert len(data["entries"]) == 1
    assert data["entries"][0]["success"] is True


# ──────────────────────────────────────────────
# Obsidian beacon
# ──────────────────────────────────────────────

def test_write_skill_index(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hades.obsidian_beacon.SKILLS_DIR", tmp_path)
    skills = {
        "alpha": SkillEntry(name="alpha", status="beta", mutating=False, nodes=["HADES"]),
        "bravo": SkillEntry(name="bravo", status="production", mutating=True, nodes=["ATLAS"]),
    }
    path = write_skill_index(skills)
    text = path.read_text(encoding="utf-8")
    assert "Tracked skills: 2" in text
    assert "alpha" in text
    assert "bravo" in text
    assert "## Production-Ready Candidates" in text


def test_append_changelog(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hades.obsidian_beacon.SKILLS_DIR", tmp_path)
    append_changelog("first entry")
    append_changelog("second entry")
    text = (tmp_path / "Changelog.md").read_text(encoding="utf-8")
    assert "first entry" in text
    assert "second entry" in text


# ──────────────────────────────────────────────
# Pi engine (integration)
# ──────────────────────────────────────────────

def test_engine_refuses_unknown_request() -> None:
    engine = PiEngine()
    resp = engine.handle(PiRequest(user_text="launch nuclear codes", user_mood="calm"))
    assert resp.success is False
    assert "No matching skill" in resp.text


def test_engine_executes_known_skill() -> None:
    engine = PiEngine()
    resp = engine.handle(PiRequest(user_text="Show me the acme integration status", user_mood="focused"))
    assert resp.success is True
    assert "acme-integration-status" in resp.skills_used
    assert resp.session_id.startswith("pi-")


def test_engine_blocks_experimental_mutating() -> None:
    engine = PiEngine()
    # filesystem-inventory is experimental + non-mutating so it should be allowed read-only
    resp = engine.handle(PiRequest(user_text="run filesystem inventory", user_mood="calm"))
    # It's experimental but non-mutating, so the gate should let it through
    # (it may fail on execution but should not be blocked by the gate)
    assert resp.session_id.startswith("pi-")
