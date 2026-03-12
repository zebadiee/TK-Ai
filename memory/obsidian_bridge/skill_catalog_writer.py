"""Mirror governed TK-Ai skills into Obsidian markdown notes."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class SkillCatalogWriter:
    """Write skill catalogue notes into an Obsidian vault."""

    def __init__(self, vault_root: str | Path = "~/Obsidian/TK-Ai") -> None:
        self.base = Path(vault_root).expanduser()
        self.skills_dir = self.base / "Skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def write(self, relative_path: str | Path, content: str) -> Path:
        path = self.base / Path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.rstrip() + "\n", encoding="utf-8")
        return path


def render_skill_note(skill: dict[str, Any]) -> str:
    commands = skill.get("execution_paths", [])
    command_lines = "\n".join(f"- `{command}`" for command in commands) if commands else "- none recorded"

    history_lines = []
    for event in skill.get("promotion_history", []):
        if not isinstance(event, dict):
            continue
        summary = str(event.get("summary", "")).strip()
        timestamp = str(event.get("timestamp", "-"))
        if summary:
            history_lines.append(f"- {timestamp}: {summary}")
    if not history_lines:
        history_lines.append("- no promotions recorded")

    visibility = skill.get("cluster_visibility", {})
    return "\n".join(
        [
            f"# {skill['slug']}",
            "",
            f"Name: {skill['name']}",
            f"Status: {skill['status']}",
            f"Last Updated: {skill['last_updated']}",
            "",
            "## Source",
            f"- repo path: `{skill['source_path']}`",
            f"- spec: `{skill['spec_path']}`",
            "",
            "## Execution",
            command_lines,
            "",
            "## Provenance",
            f"- generator: `{skill['generator']}`",
            f"- checker: `{skill['checker']}`",
            f"- checker result: `{skill['checker_result']}`",
            "",
            "## Cluster Visibility",
            f"- HADES: {'yes' if visibility.get('hades') else 'no'}",
            f"- HERMES: {'yes' if visibility.get('hermes') else 'no'}",
            f"- ATLAS: {'yes' if visibility.get('atlas') else 'no'}",
            "",
            "## Promotion History",
            *history_lines,
        ]
    )


def render_index(skills: list[dict[str, Any]]) -> str:
    lines = [
        "# Skills Index",
        "",
        f"Tracked skills: {len(skills)}",
        "",
        "| Skill | Status | Last Updated | Visibility |",
        "| --- | --- | --- | --- |",
    ]
    for skill in skills:
        visibility = skill.get("cluster_visibility", {})
        nodes = ",".join(node.upper() for node, enabled in visibility.items() if enabled) or "-"
        lines.append(
            f"| [[Skills/{skill['slug']}|{skill['slug']}]] | {skill['status']} | {skill['last_updated']} | {nodes} |"
        )

    candidates = [skill["slug"] for skill in skills if skill.get("status") == "beta"]
    lines.extend(["", "## Production-Ready Candidates"])
    if not candidates:
        lines.append("- none")
    else:
        lines.extend(f"- [[Skills/{candidate}|{candidate}]]" for candidate in candidates)
    return "\n".join(lines)


def render_changelog(events: list[dict[str, Any]]) -> str:
    lines = ["# Skills Changelog", ""]
    if not events:
        lines.append("- no skill events recorded")
        return "\n".join(lines)

    for event in events:
        if not isinstance(event, dict):
            continue
        timestamp = str(event.get("timestamp", "-"))
        skill = str(event.get("skill", "-"))
        summary = str(event.get("summary", "")).strip() or "change recorded"
        lines.append(f"- {timestamp} - `{skill}` - {summary}")
    return "\n".join(lines)


def sync_skill_catalog(skills: list[dict[str, Any]], events: list[dict[str, Any]], vault_root: str | Path) -> list[Path]:
    writer = SkillCatalogWriter(vault_root)
    written: list[Path] = []

    for skill in skills:
        written.append(writer.write(f"Skills/{skill['slug']}.md", render_skill_note(skill)))

    written.append(writer.write("Skills/Index.md", render_index(skills)))
    written.append(writer.write("Skills/Changelog.md", render_changelog(events)))
    return written
