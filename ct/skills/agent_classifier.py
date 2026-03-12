"""Derive candidate agents from the cluster cartography map."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MAP = Path("~/TK-Ai-Maxx/vault/runtime/cluster_map.json").expanduser()
OUT = Path("~/TK-Ai-Maxx/vault/runtime/agent_candidates.json").expanduser()

ENTRYPOINT_HINTS = ("daemon", "doctor", "console", "launch", "mission_control", "investigation_loop")


def classify(map_path: Path = MAP) -> list[dict[str, Any]]:
    if not map_path.exists():
        return []

    loaded = json.loads(map_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        return []

    agents: list[dict[str, Any]] = []
    for item in loaded:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", ""))
        name = Path(path).stem
        if not path.endswith(".py"):
            continue
        if not any(hint in name for hint in ENTRYPOINT_HINTS):
            continue
        agents.append(
            {
                "name": name,
                "node": item.get("node"),
                "entrypoint": path,
                "type": "python_agent",
            }
        )
    return agents


def write(agents: list[dict[str, Any]], out_path: Path = OUT) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(agents, indent=2), encoding="utf-8")


if __name__ == "__main__":
    write(classify())
