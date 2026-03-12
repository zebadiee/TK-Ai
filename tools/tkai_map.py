#!/usr/bin/env python3
"""Print a compact cluster map from the generated topology artifact."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.load_topology import load_topology


def render_map() -> list[str]:
    topology = load_topology()
    nodes = topology.get("nodes", {}) if isinstance(topology, dict) else {}
    lines = ["TK-AI Cluster Map", "-----------------"]
    for node, payload in sorted(nodes.items()):
        if not isinstance(payload, dict):
            continue
        agents = payload.get("agents", [])
        preview = ", ".join(str(agent) for agent in agents[:3]) if agents else "-"
        lines.append(f"{node} [{payload.get('role', 'unknown')}] -> {preview}")
    if len(lines) == 2:
        lines.append("No topology available")
    return lines


def main() -> int:
    print("\n".join(render_map()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
