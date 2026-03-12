#!/usr/bin/env python3
"""Execute a command on one or more cluster nodes over the canonical transport."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cluster_registry import build_transport_command, load_cluster_nodes

CLUSTER_CONFIG = ROOT / "cluster" / "cluster_config.json"
NODE_ROLES = ROOT / "cluster" / "node_roles.json"
Runner = Callable[..., subprocess.CompletedProcess[str]]


def default_handshake_command() -> list[str]:
    return [
        sys.executable,
        "-c",
        (
            "import json, socket, time; "
            "print(json.dumps({"
            "'hostname': socket.gethostname(), "
            "'timestamp': int(time.time())"
            "}, sort_keys=True))"
        ),
    ]


def run_on_node(
    node_name: str,
    command: Sequence[str] | None = None,
    *,
    timeout: float = 10.0,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    nodes = load_cluster_nodes(CLUSTER_CONFIG, NODE_ROLES)
    argv = list(command) if command else default_handshake_command()
    transport = build_transport_command(node_name, argv, nodes=nodes)
    started = time.time()
    try:
        result = runner(transport, capture_output=True, text=True, check=False, timeout=timeout)
        ok = result.returncode == 0
        returncode = result.returncode
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
    except subprocess.TimeoutExpired as exc:
        ok = False
        returncode = 124
        stdout = (exc.stdout or "").strip()
        stderr = f"timeout after {timeout:.1f}s"
    duration_ms = int((time.time() - started) * 1000)
    return {
        "node": node_name,
        "command": transport,
        "ok": ok,
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "duration_ms": duration_ms,
    }


def run_many(
    node_names: Sequence[str],
    command: Sequence[str] | None = None,
    *,
    timeout: float = 10.0,
    runner: Runner = subprocess.run,
) -> list[dict[str, Any]]:
    return [run_on_node(node_name, command, timeout=timeout, runner=runner) for node_name in node_names]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute a command on TK-Ai cluster nodes")
    parser.add_argument("nodes", nargs="*", help="Node names to target")
    parser.add_argument("--all", action="store_true", help="Target every configured node")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-node execution timeout in seconds")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run after --")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    nodes = load_cluster_nodes(CLUSTER_CONFIG, NODE_ROLES)

    targets = list(nodes.keys()) if args.all else list(args.nodes)
    if not targets:
        print("No target nodes supplied", file=sys.stderr)
        return 1

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]

    results = run_many(targets, command if command else None, timeout=args.timeout)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for result in results:
            status = "OK" if result["ok"] else "FAILED"
            print(f"{result['node']}: {status} ({result['duration_ms']} ms)")
            if result["stdout"]:
                print(result["stdout"])
            if result["stderr"]:
                print(result["stderr"], file=sys.stderr)

    return 0 if all(result["ok"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
