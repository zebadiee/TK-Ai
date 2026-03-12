"""Inventory local files for the ClawX cluster cartography mission."""

from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path
from typing import Any

NODE = socket.gethostname().split(".")[0]
SCAN_ROOTS = [
    Path.home() / "TK-Ai-Maxx",
    Path.home() / "projects",
    Path.home() / "scripts",
    Path.home() / "tools",
]
OUTPUT = Path("~/TK-Ai-Maxx/vault/runtime/cluster_map.json").expanduser()
IGNORED_PARTS = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "env", "node_modules"}


def scan(scan_roots: list[Path] = SCAN_ROOTS, node: str = NODE) -> list[dict[str, Any]]:
    discovered: list[dict[str, Any]] = []

    for root in scan_roots:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in IGNORED_PARTS for part in path.parts):
                continue

            discovered.append(
                {
                    "node": node,
                    "path": str(path),
                    "type": path.suffix,
                    "size": path.stat().st_size,
                }
            )

    return discovered


def _is_ignored_path(path: str) -> bool:
    return any(part in IGNORED_PARTS for part in Path(path).parts)


def write_map(data: list[dict[str, Any]], output: Path = OUTPUT) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, Any]] = []
    if output.exists():
        loaded = json.loads(output.read_text(encoding="utf-8"))
        if isinstance(loaded, list):
            existing = [item for item in loaded if isinstance(item, dict)]

    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for item in existing + data:
        if _is_ignored_path(str(item.get("path", ""))):
            continue
        key = (str(item.get("node", "")), str(item.get("path", "")))
        merged[key] = item

    output.write_text(
        json.dumps(sorted(merged.values(), key=lambda item: (item["node"], item["path"])), indent=2),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory local files for cluster cartography")
    parser.add_argument("--stdout", action="store_true", help="Print discovered files as JSON to stdout")
    parser.add_argument("--write", action="store_true", help="Write discovered files into the local cluster map")
    args = parser.parse_args()

    records = scan()
    if args.stdout:
        print(json.dumps(records))
        return 0

    write_map(records)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
