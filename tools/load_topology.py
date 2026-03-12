#!/usr/bin/env python3
"""Load the cluster topology artifact."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TOPOLOGY = Path("~/TK-Ai-Maxx/vault/runtime/cluster_topology.json").expanduser()


def load_topology(path: Path = TOPOLOGY) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("cluster topology must be a JSON object")
    return data
