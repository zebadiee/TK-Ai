"""Derive candidate skills from the cluster cartography map."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MAP = Path("~/TK-Ai-Maxx/vault/runtime/cluster_map.json").expanduser()
OUT = Path("~/TK-Ai-Maxx/vault/runtime/skill_candidates.json").expanduser()


def classify(map_path: Path = MAP) -> list[dict[str, Any]]:
    if not map_path.exists():
        return []

    loaded = json.loads(map_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        return []

    skills: list[dict[str, Any]] = []
    for item in loaded:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", ""))
        if not path.endswith(".py"):
            continue
        skills.append(
            {
                "node": item.get("node"),
                "path": path,
                "type": "python_skill",
            }
        )
    return skills


def write(skills: list[dict[str, Any]], out_path: Path = OUT) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(skills, indent=2), encoding="utf-8")


if __name__ == "__main__":
    write(classify())
