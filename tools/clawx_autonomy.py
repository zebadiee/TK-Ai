#!/usr/bin/env python3
"""Emit low-risk topology-driven exploration signals for ClawX autonomy."""

from __future__ import annotations

import argparse
import json
import socket
import sys
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.clawx_engine.clawx_logger import log_event
from modules.clawx_engine.signal_writer import emit_signal
from tools.load_topology import load_topology

STATE = ROOT / "vault" / "runtime" / "clawx_autonomy_state.json"
DEFAULT_COOLDOWN = 900
ROLE_TO_SIGNAL = {
    "control_plane": "control_plane_exploration",
    "gpu_inference": "gpu_inference_exploration",
    "infrastructure_backbone": "infrastructure_exploration",
}


def load_state(path: Path = STATE) -> dict[str, Any]:
    if not path.exists():
        return {"last_emit_by_node": {}, "cycles": 0}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {"last_emit_by_node": {}, "cycles": 0}


def save_state(state: dict[str, Any], path: Path = STATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def should_explore(node: str, state: dict[str, Any], now: int, cooldown: int) -> bool:
    last_emit = state.get("last_emit_by_node", {}).get(node)
    try:
        last_emit_int = int(last_emit)
    except (TypeError, ValueError):
        return True
    return now - last_emit_int >= cooldown


def build_signal(node: str, payload: dict[str, Any], now: int) -> dict[str, Any]:
    role = str(payload.get("role", "worker"))
    signal_type = ROLE_TO_SIGNAL.get(role, "cluster_exploration")
    agents = payload.get("agents", []) if isinstance(payload.get("agents"), list) else []
    return {
        "signal_id": f"autonomy-{node}-{uuid.uuid4().hex[:12]}",
        "type": signal_type,
        "severity": "low",
        "source": "clawx",
        "payload": {
            "node": node,
            "role": role,
            "agents": agents[:5],
            "agent_count": len(agents),
            "mode": "city_exploration",
        },
        "timestamp": now,
        "trace_id": f"autonomy-{node}",
    }


def emit_exploration_cycle(
    topology: dict[str, Any] | None = None,
    *,
    cooldown: int = DEFAULT_COOLDOWN,
    state_path: Path = STATE,
    signal_path: Path | None = None,
    log_path: Path | None = None,
    now: int | None = None,
) -> list[dict[str, Any]]:
    state = load_state(path=state_path)
    current_time = int(time.time()) if now is None else int(now)
    cluster = topology or load_topology()
    nodes = cluster.get("nodes", {}) if isinstance(cluster, dict) else {}
    emitted: list[dict[str, Any]] = []

    log_event(
        "autonomy_cycle_started",
        path=log_path,
        node=socket.gethostname(),
        known_nodes=len(nodes),
        cooldown=cooldown,
    )

    for node, payload in sorted(nodes.items()):
        if not isinstance(payload, dict):
            continue
        if not should_explore(node, state, current_time, cooldown):
            continue
        signal = build_signal(node, payload, current_time)
        emit_signal(
            signal["type"],
            signal["payload"],
            path=signal_path,
            signal_id=signal["signal_id"],
            severity=signal["severity"],
            source=signal["source"],
            timestamp=signal["timestamp"],
            trace_id=signal["trace_id"],
        )
        log_event(
            "autonomy_signal_emitted",
            path=log_path,
            signal=signal["type"],
            signal_id=signal["signal_id"],
            target_node=node,
            role=signal["payload"]["role"],
        )
        emitted.append(signal)
        state.setdefault("last_emit_by_node", {})[node] = current_time

    state["cycles"] = int(state.get("cycles", 0)) + 1
    state["last_cycle"] = current_time
    save_state(state, path=state_path)
    return emitted


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit low-risk ClawX autonomy exploration signals")
    parser.add_argument("--once", action="store_true", help="Run one exploration cycle and exit")
    parser.add_argument("--cooldown", type=int, default=DEFAULT_COOLDOWN, help="Seconds before re-exploring the same node")
    parser.add_argument("--interval", type=int, default=300, help="Seconds between exploration cycles")
    args = parser.parse_args()

    if args.once:
        emit_exploration_cycle(cooldown=args.cooldown)
        return 0

    while True:
        emit_exploration_cycle(cooldown=args.cooldown)
        time.sleep(max(args.interval, 1))


if __name__ == "__main__":
    raise SystemExit(main())
