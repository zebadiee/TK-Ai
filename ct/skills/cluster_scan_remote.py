"""Run the cartography scan on remote nodes and merge results locally."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ct.skills.cluster_cartographer import write_map

NODES = ["atlas", "hermes"]
SCRIPT = "~/TK-Ai-Maxx/ct/skills/cluster_cartographer.py"
OUTPUT = Path("~/TK-Ai-Maxx/vault/runtime/cluster_map.json").expanduser()


def fetch_remote_scan(node: str, script: str = SCRIPT) -> list[dict[str, Any]]:
    result = subprocess.run(
        ["ssh", node, f"/bin/bash -lc 'python3 {script} --stdout'"],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    if not isinstance(data, list):
        raise ValueError(f"Remote scan for {node} did not return a JSON array")
    return [item for item in data if isinstance(item, dict)]


def scan(nodes: list[str] = NODES, output: Path = OUTPUT) -> list[dict[str, Any]]:
    discovered: list[dict[str, Any]] = []

    for node in nodes:
        try:
            print(f"Scanning {node}...")
            records = fetch_remote_scan(node)
            write_map(records, output=output)
            discovered.extend(records)
            print(f"{node} ✓")
        except subprocess.CalledProcessError as exc:
            message = exc.stderr.strip() or str(exc)
            print(f"{node} failed: {message}")
        except Exception as exc:
            print(f"{node} failed: {exc}")

    return discovered


if __name__ == "__main__":
    scan()
