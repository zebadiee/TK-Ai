#!/usr/bin/env python3
"""Unified terminal interface for TK-AI, ClawX, and ACME surfaces."""

from __future__ import annotations

import argparse
import json
import shlex
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACME_ROOT = Path.home() / "ACME-AI"
SIGNALS = ROOT / "vault" / "runtime" / "signals.jsonl"
EVIDENCE = ROOT / "vault" / "evidence" / "evidence.jsonl"

SURFACES = {
    "mc": ROOT / "tools" / "tkai_mission_control_tui.py",
    "mission-control": ROOT / "tools" / "tkai_mission_control_tui.py",
    "clawx": ROOT / "modules" / "clawx_engine" / "clawx_console.py",
    "console": ROOT / "modules" / "clawx_engine" / "clawx_console.py",
    "acme": ACME_ROOT / "mission_control_tui.py",
    "cockpit": ACME_ROOT / "mission_control_tui.py",
    "acme-status": ROOT / "tools" / "acme_integration_status.py",
    "acme-sync": ROOT / "tools" / "acme_runtime_sync.py",
    "map": ROOT / "tools" / "tkai_map.py",
    "nav": ROOT / "tools" / "tkai_navigate.py",
    "navigate": ROOT / "tools" / "tkai_navigate.py",
    "autonomy": ROOT / "tools" / "clawx_autonomy.py",
    "burnin": ROOT / "tools" / "clawx_burnin.py",
    "mission": ROOT / "tools" / "mission_runner.py",
    "agent": ROOT / "tools" / "invoke_agent.py",
}
SURFACE_LABELS = {
    "mc": "TK-AI Mission Control TUI",
    "clawx": "ClawX operator console",
    "acme": "ACME Mission Control cockpit",
    "acme-status": "ACME and TK-Ai integration health",
    "acme-sync": "Export TK-Ai snapshot into ACME runtime",
    "map": "Compact cluster map",
    "nav": "Topology/evidence navigation",
    "mission": "Named mission runner",
    "agent": "Registered agent invocation",
    "autonomy": "ClawX autonomy loop",
    "burnin": "ClawX burn-in loop",
}
ALIASES = {
    "learn": ["burnin", "--once"],
    "train": ["burnin"],
    "cross-talk": ["autonomy", "--once", "--cooldown", "0"],
    "crosstalk": ["autonomy", "--once", "--cooldown", "0"],
}


def help_lines() -> list[str]:
    return [
        "TK-AI Unified Interface",
        "-----------------------",
        "Surfaces:",
        "/mc                TK-AI Mission Control TUI",
        "/clawx             ClawX operator console",
        "/acme              ACME Mission Control cockpit",
        "/acme-status       ACME and TK-Ai integration health",
        "/acme-sync         Export TK-Ai snapshot into ACME runtime",
        "/map               Compact cluster map",
        "/nav ...           Topology/evidence navigation",
        "/mission ...       Run a named mission",
        "/agent ...         Invoke a registered agent",
        "/autonomy ...      Run the ClawX autonomy loop",
        "/burnin ...        Run the ClawX burn-in loop",
        "",
        "Built-ins:",
        "/status            Compact control-plane status",
        "/surfaces          List available surfaces",
        "/clear             Clear the terminal",
        "",
        "Convenience:",
        "/cross-talk        Emit one exploration cycle now",
        "/learn             Run one burn-in cycle now",
        "/train             Start the continuous burn-in loop",
        "/help              Show this help",
        "/exit              Leave the shell",
    ]


def parse_shell_command(command: str) -> list[str]:
    stripped = command.strip()
    if stripped.startswith("/"):
        stripped = stripped[1:]
    if not stripped:
        return []
    parts = shlex.split(stripped)
    if not parts:
        return []
    if parts[0] in ALIASES:
        return ALIASES[parts[0]] + parts[1:]
    return parts


def read_jsonl_tail(path: Path, limit: int = 1) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def service_status(name: str) -> str:
    result = subprocess.run(
        ["systemctl", "--user", "is-active", name],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() or result.stderr.strip() or "unknown"


def surfaces_lines() -> list[str]:
    return [
        "Available Surfaces",
        "------------------",
        *[f"{name}: {label}" for name, label in SURFACE_LABELS.items()],
    ]


def status_lines() -> list[str]:
    last_signal = read_jsonl_tail(SIGNALS, limit=1)
    last_evidence = read_jsonl_tail(EVIDENCE, limit=1)
    signal_type = str(last_signal[-1].get("type", "none")) if last_signal else "none"
    evidence_signal = str(last_evidence[-1].get("signal_id", "none")) if last_evidence else "none"
    evidence_severity = str(last_evidence[-1].get("severity", "none")) if last_evidence else "none"
    return [
        "TK-AI Status",
        "------------",
        f"node: {socket.gethostname().split('.')[0]}",
        f"investigation: {service_status('tkai-investigation.service')}",
        f"scheduler: {service_status('tkai-scheduler.service')}",
        f"last_signal: {signal_type}",
        f"last_evidence_signal: {evidence_signal}",
        f"last_evidence_severity: {evidence_severity}",
    ]


def build_command(surface: str, args: list[str]) -> list[str]:
    if surface not in SURFACES:
        raise KeyError(f"unknown surface: {surface}")
    return [sys.executable, str(SURFACES[surface]), *args]


def launch(surface: str, args: list[str], runner=subprocess.run) -> int:
    command = build_command(surface, args)
    result = runner(command, cwd=ROOT, check=False)
    return int(getattr(result, "returncode", 0))


def shell() -> int:
    print("\n".join(help_lines()))
    while True:
        try:
            raw = input("tkai-ui> ")
        except KeyboardInterrupt:
            print()
            return 0
        except EOFError:
            print()
            return 0

        parts = parse_shell_command(raw)
        if not parts:
            continue
        if parts[0] in {"exit", "quit"}:
            return 0
        if parts[0] == "help":
            print("\n".join(help_lines()))
            continue
        if parts[0] == "surfaces":
            print("\n".join(surfaces_lines()))
            continue
        if parts[0] == "status":
            print("\n".join(status_lines()))
            continue
        if parts[0] == "clear":
            print("\033[2J\033[H", end="", flush=True)
            continue

        try:
            returncode = launch(parts[0], parts[1:])
            if returncode != 0:
                print(f"[tkai-ui] {parts[0]} exited with code {returncode}")
        except KeyError as exc:
            print(str(exc))
        except KeyboardInterrupt:
            print()
            continue


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("surface", nargs="?")
    parser.add_argument("args", nargs=argparse.REMAINDER)
    parsed = parser.parse_args()

    if not parsed.surface:
        return shell()
    if parsed.surface in {"help", "-h", "--help"}:
        print("\n".join(help_lines()))
        return 0
    if parsed.surface == "surfaces":
        print("\n".join(surfaces_lines()))
        return 0
    if parsed.surface == "status":
        print("\n".join(status_lines()))
        return 0
    try:
        returncode = launch(parsed.surface, parsed.args)
        if returncode != 0:
            print(f"[tkai-ui] {parsed.surface} exited with code {returncode}", file=sys.stderr)
        return returncode
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
