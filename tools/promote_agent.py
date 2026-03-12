#!/usr/bin/env python3
"""Promote one discovered agent candidate into the authoritative registry."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REGISTRY = Path("~/TK-Ai-Maxx/vault/runtime/agent_registry.json").expanduser()
DISCOVERED = Path("~/TK-Ai-Maxx/vault/runtime/discovered_agents.json").expanduser()


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def save(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def promote(name: str, registry_path: Path = REGISTRY, discovered_path: Path = DISCOVERED) -> bool:
    registry = load(registry_path)
    discovered = load(discovered_path)

    if name not in discovered:
        print(f"Agent not found in discovery list: {name}")
        return False

    registry[name] = discovered[name]
    save(registry_path, registry)
    print(f"Promoted agent: {name}")
    return True


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if len(args) < 1:
        print("Usage: promote_agent.py <agent_name>")
        return 1
    return 0 if promote(args[0]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
