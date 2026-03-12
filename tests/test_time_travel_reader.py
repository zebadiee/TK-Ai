from __future__ import annotations

import json
from pathlib import Path

from tools.time_travel_reader import TimeTravelReader


def _make_base(tmp_path: Path) -> Path:
    """Create a minimal TK-Ai-Maxx base with a snapshot index."""
    base = tmp_path / "TK-Ai-Maxx"
    snap_root = base / "vault" / "snapshots"
    snap_root.mkdir(parents=True)
    return base


def _write_snapshot(base: Path, ts: str, *, label: str | None = None) -> Path:
    snap_root = base / "vault" / "snapshots"
    snap_dir = snap_root / ts
    (snap_dir / "skills").mkdir(parents=True)
    (snap_dir / "skills" / "guide.md").write_text("Frozen\n", encoding="utf-8")
    # Update index
    index_path = snap_root / ".snapshot_index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
    else:
        index = {"snapshots": []}
    index["snapshots"].append({"timestamp": ts, "label": label or ts})
    index_path.write_text(json.dumps(index), encoding="utf-8")
    return snap_dir


def test_list_available_snapshots(tmp_path: Path) -> None:
    base = _make_base(tmp_path)
    _write_snapshot(base, "20260311T201500Z", label="alpha")
    _write_snapshot(base, "20260312T201500Z", label="beta")

    reader = TimeTravelReader(base_path=str(base))
    snaps = reader.list_available_snapshots()
    assert len(snaps) == 2
    assert snaps[0]["label"] == "alpha"


def test_mount_snapshot_by_label(tmp_path: Path) -> None:
    base = _make_base(tmp_path)
    _write_snapshot(base, "20260312T201500Z", label="beta")

    reader = TimeTravelReader(base_path=str(base))
    assert reader.mount_snapshot("beta") is True
    assert reader.current_snapshot["label"] == "beta"


def test_read_file_from_mounted_snapshot(tmp_path: Path) -> None:
    base = _make_base(tmp_path)
    _write_snapshot(base, "20260312T201500Z", label="gamma")

    reader = TimeTravelReader(base_path=str(base))
    reader.mount_snapshot("gamma")
    content = reader.read_file_from_snapshot("skills/guide.md")
    assert content is not None
    assert "Frozen" in content
