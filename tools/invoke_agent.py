#!/usr/bin/env python3
"""Invoke a registered agent locally or over SSH."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from tools.cluster_registry import build_transport_command, detect_local_node, normalize_node_name

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "vault" / "runtime" / "agent_registry.json"


def load_registry(path: Path = REGISTRY) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("agent registry must be a JSON object")
    return data


def local_node() -> str:
    return detect_local_node()


def resolve_entrypoint(entrypoint: str) -> str:
    path = Path(entrypoint)
    if path.is_absolute():
        return str(path)
    return str((ROOT / path).resolve())


def build_command(agent: str, argv: list[str], registry: dict[str, Any]) -> list[str]:
    if agent not in registry:
        raise KeyError(f"unknown agent: {agent}")

    record = registry[agent]
    if not isinstance(record, dict):
        raise ValueError(f"invalid registry entry for {agent}")

    node = str(record.get("node", "")).strip()
    entrypoint = str(record.get("entrypoint", "")).strip()
    endpoint = str(record.get("endpoint", "")).strip()

    if not entrypoint:
        if endpoint:
            raise ValueError(f"agent {agent} is endpoint-only: {endpoint}")
        raise ValueError(f"agent {agent} has no entrypoint")

    command = [sys.executable, resolve_entrypoint(entrypoint), *argv]
    if node and normalize_node_name(node) != local_node():
        return build_transport_command(node, command, local_node=local_node())
    return command


def run(agent: str, argv: list[str] | None = None, registry_path: Path = REGISTRY) -> int:
    command = build_command(agent, argv or [], load_registry(registry_path))
    result = subprocess.run(command, check=False)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Invoke a registered cluster agent")
    parser.add_argument("agent", help="Registry key for the agent to invoke")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed through to the agent")
    parsed = parser.parse_args()

    try:
        return run(parsed.agent, parsed.args)
    except (KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
