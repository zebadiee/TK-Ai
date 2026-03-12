"""Obsidian beacon writer for Pi.

Mirrors skill catalogues, changelogs, and session summaries into the
Obsidian TK-Ai vault so they're visible in the knowledge graph.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OBSIDIAN_ROOT = Path("~/Obsidian/TK-Ai").expanduser()
SKILLS_DIR = OBSIDIAN_ROOT / "Skills"
SYSTEM_DIR = OBSIDIAN_ROOT / "System" / "PiSessions"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_skill_index(skills: dict[str, Any]) -> Path:
    """Rewrite Skills/Index.md from the resolved registry."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    path = SKILLS_DIR / "Index.md"
    lines = [
        "# Skills Index",
        "",
        f"Tracked skills: {len(skills)}",
        "",
        "| Skill | Status | Last Updated | Visibility |",
        "| --- | --- | --- | --- |",
    ]
    prod_candidates: list[str] = []
    for name, entry in sorted(skills.items()):
        nodes_str = ", ".join(entry.nodes) if hasattr(entry, "nodes") else ""
        lines.append(
            f"| [[Skills/{name}|{name}]] | {entry.status} | {_ts()} | {nodes_str} |"
        )
        if entry.status == "production":
            prod_candidates.append(name)

    lines.append("")
    lines.append("## Production-Ready Candidates")
    if prod_candidates:
        for c in prod_candidates:
            lines.append(f"- {c}")
    else:
        lines.append("- none")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def append_changelog(message: str) -> Path:
    """Append a timestamped entry to Skills/Changelog.md."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    path = SKILLS_DIR / "Changelog.md"
    entry = f"- {_ts()}: {message}\n"
    if path.exists():
        content = path.read_text(encoding="utf-8")
        if not content.endswith("\n"):
            content += "\n"
    else:
        content = "# Skills Changelog\n\n"
    content += entry
    path.write_text(content, encoding="utf-8")
    return path


def write_session_summary(
    session_id: str,
    mood: str,
    entries: list[dict[str, Any]],
) -> Path | None:
    """Write a high-level session summary to System/PiSessions/<id>.md."""
    SYSTEM_DIR.mkdir(parents=True, exist_ok=True)
    path = SYSTEM_DIR / f"{session_id}.md"
    lines = [
        f"# Pi Session: {session_id}",
        "",
        f"- mood: {mood}",
        f"- entries: {len(entries)}",
        f"- written: {_ts()}",
        "",
        "## Entries",
        "",
    ]
    for i, e in enumerate(entries, 1):
        status = "ok" if e.get("success") else "fail"
        skills = ", ".join(e.get("skills", []))
        lines.append(f"{i}. [{status}] skills={skills} — {e.get('summary', '')[:120]}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
