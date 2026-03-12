#!/usr/bin/env python3
"""Show the current TK-Ai scheduler and policy state."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gateway.hermes_api import tail_jsonl

POLICY_FILE = Path("vault/policy/scheduler_policy.json")
CLAWX_LOG = Path("vault/runtime/clawx_log.jsonl")
CLUSTER_STATUS = Path("vault/runtime/cluster_status.json")


def scheduler_state() -> str:
    result = subprocess.run(
        ["systemctl", "--user", "is-active", "tkai-scheduler.service"],
        capture_output=True,
        text=True,
        check=False,
    )
    state = result.stdout.strip()
    return state or "unknown"


def load_policy() -> dict[str, object] | None:
    if not POLICY_FILE.exists():
        return None
    data = json.loads(POLICY_FILE.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def load_cluster_status() -> dict[str, object] | None:
    if not CLUSTER_STATUS.exists():
        return None
    data = json.loads(CLUSTER_STATUS.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def main() -> int:
    cluster_status = load_cluster_status()
    if cluster_status is not None:
        print("Cluster Status")
        print("--------------")
        print(f"node: {cluster_status.get('node', 'unknown')}")
        services = cluster_status.get("services", {})
        if isinstance(services, dict):
            for name, state in services.items():
                print(f"{name}: {state}")
        print()

    print("Scheduler Runtime")
    print("-----------------")
    print(f"service: {scheduler_state()}")
    print()
    print("Scheduler Policy")
    print("----------------")
    policy = load_policy()
    if policy is None:
        print("state: none")
        print("reason: no policy artifact")
        print("duration: 0h")
        print("updated_by: unknown")
        return 0

    desired = policy.get("desired_state", policy.get("state", "unknown"))
    duration = policy.get("duration_hours", 0)
    reason = policy.get("reason", "")
    updated_by = policy.get("updated_by", policy.get("source", "unknown"))
    print(f"state: {desired}")
    print(f"reason: {reason}")
    print(f"duration: {duration}h")
    print(f"updated_by: {updated_by}")
    print()
    print("ClawX Thinking")
    print("--------------")
    insights = tail_jsonl(CLAWX_LOG, n=5)
    if not insights:
        print("no reasoning events")
        return 0

    for item in insights:
        event = item.get("event", "unknown")
        detail = item.get("signal") or item.get("hypothesis") or item.get("pattern") or ""
        if detail:
            print(f"{event} {detail}")
        else:
            print(str(event))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
