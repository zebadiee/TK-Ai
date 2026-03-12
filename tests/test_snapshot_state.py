from __future__ import annotations

import json
from pathlib import Path

from tools.snapshot_state import SnapshotState


def test_create_snapshot_produces_metadata(tmp_path: Path) -> None:
    base = tmp_path / "TK-Ai-Maxx"
    (base / "vault" / "runtime").mkdir(parents=True)
    (base / "vault" / "runtime" / "signals.jsonl").write_text(
        '{"signal_id":"s1"}\n', encoding="utf-8"
    )
    (base / "ct" / "skills").mkdir(parents=True)
    (base / "ct" / "skills" / "reader.py").write_text("# reader\n", encoding="utf-8")

    state = SnapshotState(base_path=str(base))
    meta = state.create_snapshot(label="test-alpha")

    assert meta["label"] == "test-alpha"
    assert isinstance(meta["timestamp"], str)
    assert meta["files_count"] >= 0


def test_list_snapshots_returns_created_snapshot(tmp_path: Path) -> None:
    base = tmp_path / "TK-Ai-Maxx"
    (base / "vault" / "runtime").mkdir(parents=True)
    (base / "vault" / "runtime" / "signals.jsonl").write_text("{}\n", encoding="utf-8")

    state = SnapshotState(base_path=str(base))
    state.create_snapshot(label="alpha")
    snapshots = state.list_snapshots()

    assert len(snapshots) >= 1
