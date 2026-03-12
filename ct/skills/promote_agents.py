"""Promote discovered agent candidates into the registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CANDIDATES = Path("vault/runtime/agent_candidates.json")
REGISTRY = Path("vault/runtime/agent_registry.json")


def load_json(path: Path, *, default: Any) -> Any:
    if not path.exists():
        return default
    data = json.loads(path.read_text(encoding="utf-8"))
    return data


def promote_agents(candidates_path: Path = CANDIDATES, registry_path: Path = REGISTRY) -> dict[str, Any]:
    candidates = load_json(candidates_path, default=[])
    if not isinstance(candidates, list):
        candidates = []

    registry = load_json(registry_path, default={})
    if not isinstance(registry, dict):
        registry = {}

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        name = str(candidate.get("name", "")).strip()
        entrypoint = str(candidate.get("entrypoint", "")).strip()
        if not name or not entrypoint:
            continue
        registry[name] = {
            "node": candidate.get("node"),
            "entrypoint": entrypoint,
        }

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    return registry


if __name__ == "__main__":
    promote_agents()
