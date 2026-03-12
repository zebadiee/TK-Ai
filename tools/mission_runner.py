#!/usr/bin/env python3
"""Run named missions through the existing agent control plane."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MISSIONS = ROOT / "vault" / "runtime" / "missions.json"
INVOKE_AGENT = ROOT / "tools" / "invoke_agent.py"
INVESTIGATION_SERVICE = "tkai-investigation.service"


def load_missions(path: Path = MISSIONS) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("missions.json must be a JSON object")
    return data


def run_agent(agent: str, args: list[str] | None = None, runner=subprocess.run) -> int:
    command = [sys.executable, str(INVOKE_AGENT), agent, *(args or [])]
    result = runner(command, cwd=ROOT, check=False)
    return int(getattr(result, "returncode", 0))


def service_is_active(service: str, runner=subprocess.run) -> bool:
    result = runner(
        ["systemctl", "--user", "is-active", service],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == "active"


def run_mission(name: str, missions_path: Path = MISSIONS, runner=subprocess.run) -> list[dict[str, Any]]:
    missions = load_missions(path=missions_path)
    if name not in missions:
        raise KeyError(f"unknown mission: {name}")

    mission = missions[name]
    if not isinstance(mission, dict):
        raise ValueError(f"mission {name} must be a JSON object")

    steps = mission.get("steps", [])
    if not isinstance(steps, list):
        raise ValueError(f"mission {name} steps must be a list")

    print(f"Running mission: {name}")
    results: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        agent = str(step.get("agent", "")).strip()
        args = step.get("args")
        argv = [str(value) for value in args] if isinstance(args, list) else []
        service = step.get("skip_if_service_active")
        if not agent:
            continue
        if isinstance(service, str) and service_is_active(service, runner=runner):
            results.append(
                {
                    "agent": agent,
                    "args": argv,
                    "returncode": 0,
                    "skipped": True,
                    "skip_if_service_active": service,
                }
            )
            continue
        returncode = run_agent(agent, argv, runner=runner)
        results.append({"agent": agent, "args": argv, "returncode": returncode})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a named mission through the agent control plane")
    parser.add_argument("mission", help="Mission key in vault/runtime/missions.json")
    args = parser.parse_args()

    try:
        run_mission(args.mission)
    except (KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
