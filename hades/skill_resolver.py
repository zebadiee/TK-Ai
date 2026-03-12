"""Skill registry resolver for Pi.

Loads the assistant manifest, indexes Obsidian skill notes, and resolves
skill names to executable paths and metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "hades" / "assistant_manifest.md"
OBSIDIAN_SKILLS = Path("~/Obsidian/TK-Ai/Skills").expanduser()


@dataclass(frozen=True)
class SkillEntry:
    name: str
    status: str                       # experimental | beta | production
    mutating: bool
    nodes: list[str] = field(default_factory=list)
    repo: str = ""                    # repo path (filled from Obsidian note)
    execution: list[str] = field(default_factory=list)  # CLI commands


_TABLE_RE = re.compile(
    r"^\|\s*(?P<skill>[^|]+?)\s*\|\s*(?P<status>experimental|beta|production)\s*"
    r"\|\s*(?P<mut>yes|no)\s*\|\s*(?P<nodes>[^|]+?)\s*\|$",
    re.IGNORECASE,
)


def load_manifest(path: Path = MANIFEST) -> list[SkillEntry]:
    """Parse the Allowed Skills table from the assistant manifest."""
    if not path.exists():
        return []
    entries: list[SkillEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _TABLE_RE.match(line.strip())
        if not m:
            continue
        entries.append(
            SkillEntry(
                name=m.group("skill").strip(),
                status=m.group("status").strip().lower(),
                mutating=m.group("mut").strip().lower() == "yes",
                nodes=[n.strip() for n in m.group("nodes").split(",") if n.strip()],
            )
        )
    return entries


def _read_obsidian_note(skill_name: str) -> dict[str, Any]:
    """Extract repo path and execution lines from an Obsidian skill note."""
    note = OBSIDIAN_SKILLS / f"{skill_name}.md"
    if not note.exists():
        return {}
    text = note.read_text(encoding="utf-8")

    repo = ""
    execution: list[str] = []
    in_execution = False
    in_code = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- repo path:"):
            repo = stripped.split(":", 1)[1].strip().strip("`")
        if stripped == "## Execution":
            in_execution = True
            continue
        if in_execution and stripped.startswith("## "):
            in_execution = False
        if in_execution and stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_execution and not in_code and stripped.startswith("- `"):
            execution.append(stripped.lstrip("- ").strip("`"))
    return {"repo": repo, "execution": execution}


def resolve_skills(path: Path = MANIFEST) -> dict[str, SkillEntry]:
    """Return a mapping of skill name -> enriched SkillEntry."""
    registry: dict[str, SkillEntry] = {}
    for entry in load_manifest(path):
        extra = _read_obsidian_note(entry.name)
        enriched = SkillEntry(
            name=entry.name,
            status=entry.status,
            mutating=entry.mutating,
            nodes=entry.nodes,
            repo=extra.get("repo", ""),
            execution=extra.get("execution", []),
        )
        registry[entry.name] = enriched
    return registry


def skill_allowed(entry: SkillEntry, *, live: bool) -> bool:
    """Check whether a skill may execute.  *live* means it touches real data."""
    if live and entry.status == "experimental":
        return False
    return True


HOME_REPOS = {"TK-Ai-Maxx", "ACME-AI"}


def prefer_home(candidates: list[SkillEntry]) -> list[SkillEntry]:
    """Sort candidates so home-repo skills at beta+ come first."""
    def _key(e: SkillEntry) -> tuple[int, int, str]:
        home = 0 if any(h in e.repo for h in HOME_REPOS) else 1
        status_rank = {"production": 0, "beta": 1, "experimental": 2}.get(e.status, 3)
        return (home, status_rank, e.name)
    return sorted(candidates, key=_key)
