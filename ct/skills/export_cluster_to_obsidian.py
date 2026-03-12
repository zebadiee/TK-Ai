"""Export the cluster map into an Obsidian-friendly markdown view."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

MAP = Path("vault/runtime/cluster_map.json")
OUT = Path("~/Obsidian/DeclanOS/ClusterMap.md").expanduser()


def render_cluster_map(entries: list[dict[str, Any]]) -> str:
    by_node: dict[str, list[str]] = defaultdict(list)
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        node = str(entry.get("node", "unknown"))
        path = str(entry.get("path", ""))
        if not path:
            continue
        by_node[node].append(path)

    lines = ["# ClawX Cluster Map", ""]
    for node in sorted(by_node):
        lines.append(f"## {node}")
        for path in sorted(by_node[node]):
            lines.append(f"- `{path}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export_cluster_map(map_path: Path = MAP, out_path: Path = OUT) -> Path:
    entries = json.loads(map_path.read_text(encoding="utf-8")) if map_path.exists() else []
    if not isinstance(entries, list):
        raise ValueError("cluster_map.json must contain a JSON array")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_cluster_map(entries), encoding="utf-8")
    return out_path


if __name__ == "__main__":
    export_cluster_map()
