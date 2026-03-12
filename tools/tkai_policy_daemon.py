#!/usr/bin/env python3
"""Apply scheduler policy artifacts to the local TK-Ai runtime."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

POLICY_FILE = Path("vault/policy/scheduler_policy.json")
START_CMD = ["/home/zebadiee/bin/tkai-start"]
STOP_CMD = ["/home/zebadiee/bin/tkai-stop"]
STATUS_CMD = ["systemctl", "--user", "is-active", "tkai-scheduler.service"]
CHECK_INTERVAL = 300


def scheduler_running(
    status_cmd: list[str] | None = None,
    runner=subprocess.run,
) -> bool:
    command = status_cmd or STATUS_CMD
    result = runner(command, capture_output=True, text=True, check=False)
    return result.stdout.strip() == "active"


def start_scheduler(runner=subprocess.run) -> int:
    result = runner(START_CMD, check=False)
    return int(result.returncode)


def stop_scheduler(runner=subprocess.run) -> int:
    result = runner(STOP_CMD, check=False)
    return int(result.returncode)


def load_policy(path: Path = POLICY_FILE) -> dict[str, object] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    return data


def apply_policy(
    path: Path = POLICY_FILE,
    *,
    status_cmd: list[str] | None = None,
    runner=subprocess.run,
) -> str:
    policy = load_policy(path)
    if policy is None:
        return "no_policy"

    desired = str(policy.get("desired_state") or policy.get("state") or "").strip().lower()
    if desired not in {"running", "stopped"}:
        return "invalid_policy"

    running = scheduler_running(status_cmd=status_cmd, runner=runner)
    if desired == "running" and not running:
        start_scheduler(runner=runner)
        return "started"
    if desired == "stopped" and running:
        stop_scheduler(runner=runner)
        return "stopped"
    return "noop"


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply TK-Ai scheduler policy continuously")
    parser.add_argument("--once", action="store_true", help="Apply policy a single time and exit")
    parser.add_argument("--interval", type=int, default=CHECK_INTERVAL, help="Seconds between policy checks")
    args = parser.parse_args()

    if args.once:
        print(apply_policy())
        return 0

    while True:
        outcome = apply_policy()
        if outcome in {"started", "stopped"}:
            print(f"Policy daemon applied change: {outcome}", flush=True)
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
