#!/usr/bin/env python3
"""Write cluster runtime status artifacts for Mission Control and Apollo."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from tools.cluster_registry import detect_local_node, load_cluster_nodes

RUNTIME_STATUS = Path("vault/runtime/cluster_status.json")
CLUSTER_CONFIG = Path("cluster/cluster_config.json")
NODE_ROLES = Path("cluster/node_roles.json")
CHECK_INTERVAL = 60
SERVICES = {
    "scheduler": "tkai-scheduler.service",
    "policy_daemon": "tkai-policy.service",
}


def service_state(service: str) -> str:
    result = subprocess.run(
        ["systemctl", "--user", "is-active", service],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() or "unknown"


def build_status() -> dict[str, object]:
    nodes = load_cluster_nodes(CLUSTER_CONFIG, NODE_ROLES)
    node_name = detect_local_node()
    node = nodes.get(node_name)
    services = {name: service_state(unit) for name, unit in SERVICES.items()}
    payload: dict[str, object] = {
        "node": node_name,
        "timestamp": int(time.time()),
        "services": services,
    }
    if node is not None:
        payload["role"] = node.cluster_role
        payload["host"] = node.host
        payload["ssh_target"] = node.transport_target
        if node.ip:
            payload["ip"] = node.ip
        if node.services:
            payload["declared_services"] = list(node.services)
    else:
        payload["role"] = "control"
    return payload


def write_status(path: Path = RUNTIME_STATUS) -> dict[str, object]:
    payload = build_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Write TK-Ai runtime status artifacts")
    parser.add_argument("--once", action="store_true", help="Write one status snapshot and exit")
    parser.add_argument("--interval", type=int, default=CHECK_INTERVAL, help="Seconds between snapshots")
    args = parser.parse_args()

    if args.once:
        write_status()
        return 0

    while True:
        write_status()
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
