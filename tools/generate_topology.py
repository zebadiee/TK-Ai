#!/usr/bin/env python3
"""Generate cluster topology from the authoritative agent registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.cluster_registry import load_cluster_nodes, normalize_node_name

REGISTRY = Path("~/TK-Ai-Maxx/vault/runtime/agent_registry.json").expanduser()
TOPOLOGY = Path("~/TK-Ai-Maxx/vault/runtime/cluster_topology.json").expanduser()
CLUSTER_CONFIG = Path("~/TK-Ai-Maxx/cluster/cluster_config.json").expanduser()


def generate_topology(registry_path: Path = REGISTRY) -> dict[str, Any]:
    registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else {}
    if not isinstance(registry, dict):
        raise ValueError("agent registry must be a JSON object")

    nodes = {name: payload.to_topology_dict() for name, payload in load_cluster_nodes(CLUSTER_CONFIG).items()}

    for agent, data in sorted(registry.items()):
        if not isinstance(data, dict):
            continue
        node = normalize_node_name(str(data.get("node", "hades")).strip() or "hades")
        nodes.setdefault(
            node,
            {
                "role": "worker",
                "agents": [],
                "host": node,
                "ssh_target": node,
            },
        )
        nodes[node]["agents"].append(str(agent))

    for payload in nodes.values():
        payload["agents"] = sorted(payload["agents"])

    return {"nodes": nodes}


def write_topology(topology: dict[str, Any], path: Path = TOPOLOGY) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(topology, indent=2), encoding="utf-8")


def main() -> int:
    topology = generate_topology()
    write_topology(topology)
    print(f"Topology generated: {len(topology.get('nodes', {}))} nodes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
