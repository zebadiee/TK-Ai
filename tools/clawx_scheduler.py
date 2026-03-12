#!/usr/bin/env python3
"""Minimal signal-driven scheduler for invoking missions and agents."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SIGNALS = ROOT / "vault" / "runtime" / "signals.jsonl"
STATE = ROOT / "vault" / "runtime" / "scheduler_state.json"
INVOKE_AGENT = ROOT / "tools" / "invoke_agent.py"
MISSION_RUNNER = ROOT / "tools" / "mission_runner.py"
INVESTIGATION_SERVICE = "tkai-investigation.service"
CHECK_INTERVAL = 10

RULES: dict[str, list[dict[str, Any]]] = {
    "latency_spike": [{"mission": "atlas_latency_investigation"}],
    "funding_rate_anomaly": [{"mission": "funding_signal_triage"}],
    "funding_pattern_detected": [{"mission": "control_plane_health"}],
    "router_test": [{"mission": "control_plane_health"}],
    "control_plane_exploration": [{"mission": "control_plane_exploration"}],
    "gpu_inference_exploration": [{"mission": "inference_node_exploration"}],
    "infrastructure_exploration": [{"mission": "gateway_node_exploration"}],
    "cluster_exploration": [{"mission": "control_plane_health"}],
}


def load_state(path: Path = STATE) -> dict[str, int]:
    if not path.exists():
        return {"last_offset": 0}

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"last_offset": 0}
    try:
        offset = int(data.get("last_offset", 0))
    except (TypeError, ValueError):
        offset = 0
    return {"last_offset": max(offset, 0)}


def save_state(state: dict[str, int], path: Path = STATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def read_new_signals(offset: int, path: Path = SIGNALS) -> tuple[list[dict[str, Any]], int]:
    if not path.exists():
        return [], offset

    lines = path.read_text(encoding="utf-8").splitlines()
    new_lines = lines[offset:]
    signals: list[dict[str, Any]] = []
    for line in new_lines:
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        if isinstance(data, dict):
            signals.append(data)
    return signals, len(lines)


def service_is_active(service: str, runner=subprocess.run) -> bool:
    result = runner(
        ["systemctl", "--user", "is-active", service],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == "active"


def invoke(agent: str, args: list[str] | None = None, runner=subprocess.run) -> int:
    command = [sys.executable, str(INVOKE_AGENT), agent, *(args or [])]
    print(f"[scheduler] invoking {agent}", flush=True)
    result = runner(command, cwd=ROOT, check=False)
    return int(getattr(result, "returncode", 0))


def invoke_mission(name: str, runner=subprocess.run) -> int:
    command = [sys.executable, str(MISSION_RUNNER), name]
    print(f"[scheduler] invoking mission {name}", flush=True)
    result = runner(command, cwd=ROOT, check=False)
    return int(getattr(result, "returncode", 0))


def process_signals(signals: list[dict[str, Any]], runner=subprocess.run) -> list[tuple[str, str]]:
    invoked: list[tuple[str, str]] = []
    service_cache: dict[str, bool] = {}

    for signal in signals:
        signal_type = str(signal.get("type", ""))
        for action in RULES.get(signal_type, []):
            if "mission" in action:
                mission = str(action["mission"])
                invoke_mission(mission, runner=runner)
                invoked.append((signal_type, mission))
                continue

            agent = str(action["agent"])
            service = action.get("skip_if_service_active")
            if isinstance(service, str):
                if service not in service_cache:
                    service_cache[service] = service_is_active(service, runner=runner)
                if service_cache[service]:
                    print(f"[scheduler] skipping {agent}; {service} is active", flush=True)
                    continue

            invoke(agent, list(action.get("args", [])), runner=runner)
            invoked.append((signal_type, agent))

    return invoked


def run_once(
    state_path: Path = STATE,
    signal_path: Path = SIGNALS,
    runner=subprocess.run,
) -> list[tuple[str, str]]:
    state = load_state(path=state_path)
    signals, new_offset = read_new_signals(state["last_offset"], path=signal_path)
    invoked = process_signals(signals, runner=runner)
    state["last_offset"] = new_offset
    save_state(state, path=state_path)
    return invoked


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch signals and invoke registered agents by rule")
    parser.add_argument("--once", action="store_true", help="Process the current unread signals once and exit")
    parser.add_argument("--interval", type=int, default=CHECK_INTERVAL, help="Seconds between signal polls")
    args = parser.parse_args()

    if args.once:
        run_once()
        return 0

    while True:
        run_once()
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
