from __future__ import annotations

from pathlib import Path

from tools import tool_creation_checker


def test_check_skill_validates_frontmatter_and_agents_yaml(tmp_path: Path) -> None:
    skill_dir = tmp_path / "snapshot-state"
    (skill_dir / "agents").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: snapshot-state\ndescription: Capture snapshots.\n---\n\n# Snapshot State\n",
        encoding="utf-8",
    )
    (skill_dir / "agents" / "openai.yaml").write_text("interface:\n  display_name: Snapshot State\n", encoding="utf-8")

    result = tool_creation_checker.check_skill(skill_dir)

    assert result["valid"] is True
    assert result["errors"] == []


def test_check_skill_rejects_missing_frontmatter(tmp_path: Path) -> None:
    skill_dir = tmp_path / "broken-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# broken\n", encoding="utf-8")

    result = tool_creation_checker.check_skill(skill_dir)

    assert result["valid"] is False
    assert "missing frontmatter name" in result["errors"]
