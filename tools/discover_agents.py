#!/usr/bin/env python3
"""Discover executable agent candidates without mutating the registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOTS = [
    Path("~/ACME-AI").expanduser(),
    Path("~/declanos").expanduser(),
    Path("~/dexai").expanduser(),
    Path("~/hades").expanduser(),
]
REGISTRY = Path("~/TK-Ai-Maxx/vault/runtime/agent_registry.json").expanduser()
CANDIDATES = Path("~/TK-Ai-Maxx/vault/runtime/discovered_agents.json").expanduser()
IGNORE_PARTS = {".git", "__pycache__", ".venv", "venv", "env", ".pytest_cache", "node_modules"}


def load_registry(path: Path = REGISTRY) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def is_executable_python(file: Path) -> bool:
    if file.suffix != ".py":
        return False
    if any(part in IGNORE_PARTS for part in file.parts):
        return False

    try:
        head = file.read_text(encoding="utf-8")[:400]
    except (OSError, UnicodeDecodeError):
        return False

    return "if __name__" in head or "argparse" in head


def scan(roots: list[Path] = ROOTS, registry_path: Path = REGISTRY) -> dict[str, dict[str, str]]:
    registry = load_registry(path=registry_path)
    found: dict[str, dict[str, str]] = {}

    for root in roots:
        if not root.exists():
            continue

        for file in root.rglob("*.py"):
            if not is_executable_python(file):
                continue

            name = file.stem
            if name in registry or name in found:
                continue

            found[name] = {
                "node": "hades",
                "entrypoint": str(file),
            }

    return dict(sorted(found.items()))


def write_candidates(candidates: dict[str, dict[str, str]], path: Path = CANDIDATES) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(candidates, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover executable agent candidates without updating the registry")
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        help="Additional root to scan. May be provided multiple times.",
    )
    args = parser.parse_args()

    roots = ROOTS + [Path(value).expanduser() for value in args.root]
    discovered = scan(roots=roots)
    write_candidates(discovered)

    print(f"Discovered agents: {len(discovered)}")
    for name in discovered:
        print(f" - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
