#!/usr/bin/env python3
"""Sync the canonical entity registry into Obsidian markdown pages."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from memory.obsidian_bridge.entity_writer import EntityWriter

REGISTRY = Path("vault/entities/entities.json")


def main() -> int:
    if not REGISTRY.exists():
        raise FileNotFoundError(f"Missing entity registry: {REGISTRY}")

    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Entity registry must be a JSON object")

    writer = EntityWriter()
    for entity, meta in data.items():
        if not isinstance(meta, dict):
            continue
        writer.write_entity(str(entity), meta)

    print("Entities synced to Obsidian")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
