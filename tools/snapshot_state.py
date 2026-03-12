#!/usr/bin/env python3
"""
Capture a versioned snapshot of TK-Ai-Maxx system state.

Creates a frozen universe with skills, scripts, and governance at a specific point in time.
Snapshots can be time-traveled to for consistent historical queries.
"""

import json
import os
import shutil
import tarfile
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

class SnapshotState:
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or os.path.expanduser("~/TK-Ai-Maxx"))
        self.snapshot_root = self.base_path / "vault" / "snapshots"
        self.snapshot_root.mkdir(parents=True, exist_ok=True)

    def generate_timestamp(self) -> str:
        """Generate ISO 8601 timestamp for snapshot."""
        return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    def create_snapshot(self, label: Optional[str] = None) -> dict:
        """
        Create a frozen snapshot of system state.
        
        Args:
            label: Optional human-readable label (e.g., "pre-clawX", "tkai-ready-alpha")
        
        Returns:
            Snapshot metadata dict
        """
        timestamp = self.generate_timestamp()
        snapshot_dir = self.snapshot_root / timestamp
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Track what gets snapshotted
        snapshot_meta = {
            "timestamp": timestamp,
            "label": label or f"snapshot-{timestamp}",
            "components": {},
            "files_count": 0,
            "created_at": datetime.utcnow().isoformat()
        }

        # 1. Snapshot skills
        skills_src = self.base_path / "ct" / "skills"
        if skills_src.exists():
            skills_dst = snapshot_dir / "skills"
            shutil.copytree(skills_src, skills_dst, dirs_exist_ok=True)
            skill_files = sum(1 for _ in skills_dst.rglob("*") if _.is_file())
            snapshot_meta["components"]["skills"] = {
                "source": str(skills_src),
                "files": skill_files
            }
            snapshot_meta["files_count"] += skill_files

        # 2. Snapshot tools
        tools_src = self.base_path / "tools"
        if tools_src.exists():
            tools_dst = snapshot_dir / "tools"
            shutil.copytree(tools_src, tools_dst, dirs_exist_ok=True)
            tool_files = sum(1 for _ in tools_dst.rglob("*.py") if _.is_file())
            snapshot_meta["components"]["tools"] = {
                "source": str(tools_src),
                "files": tool_files
            }
            snapshot_meta["files_count"] += tool_files

        # 3. Snapshot governance / rules if they exist
        governance_src = self.base_path / "ct" / "rules"
        if governance_src.exists():
            governance_dst = snapshot_dir / "governance"
            shutil.copytree(governance_src, governance_dst, dirs_exist_ok=True)
            gov_files = sum(1 for _ in governance_dst.rglob("*") if _.is_file())
            snapshot_meta["components"]["governance"] = {
                "source": str(governance_src),
                "files": gov_files
            }
            snapshot_meta["files_count"] += gov_files

        # 4. Snapshot vault indexes (wiki, patterns, etc)
        vault_src = self.base_path / "vault"
        vault_dst = snapshot_dir / "vault_index"
        vault_dst.mkdir(exist_ok=True)

        for index_file in ["graph_index.json", "pattern_index.json", "signals.json", "triggers.json"]:
            src = vault_src / index_file
            if src.exists():
                dst = vault_dst / index_file
                shutil.copy2(src, dst)
                snapshot_meta["files_count"] += 1

        # 5. Write snapshot manifest
        manifest_path = snapshot_dir / "MANIFEST.json"
        with open(manifest_path, "w") as f:
            json.dump(snapshot_meta, f, indent=2)

        # 6. Write index file listing all snapshots
        self._update_snapshot_index(timestamp, label, snapshot_meta)

        return snapshot_meta

    def _update_snapshot_index(self, timestamp: str, label: str, meta: dict):
        """Update central snapshot index."""
        index_path = self.snapshot_root / ".snapshot_index.json"
        
        if index_path.exists():
            with open(index_path, "r") as f:
                index = json.load(f)
        else:
            index = {"snapshots": [], "versions": []}

        index["snapshots"].append({
            "timestamp": timestamp,
            "label": label,
            "files": meta["files_count"]
        })

        with open(index_path, "w") as f:
            json.dump(index, f, indent=2)

    def list_snapshots(self) -> list:
        """List all available snapshots."""
        index_path = self.snapshot_root / ".snapshot_index.json"
        
        if not index_path.exists():
            return []

        with open(index_path, "r") as f:
            index = json.load(f)

        return index.get("snapshots", [])

    def get_snapshot_path(self, timestamp: str) -> Path:
        """Get path to a specific snapshot by timestamp."""
        snapshot_dir = self.snapshot_root / timestamp
        if not snapshot_dir.exists():
            raise FileNotFoundError(f"Snapshot {timestamp} not found")
        return snapshot_dir


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Create system state snapshots")
    parser.add_argument("--label", type=str, help="Human-readable snapshot label")
    parser.add_argument("--list", action="store_true", help="List existing snapshots")
    parser.add_argument("--path", type=str, default=None, help="Base TK-Ai-Maxx path")
    
    args = parser.parse_args()

    snapshot = SnapshotState(args.path)

    if args.list:
        snapshots = snapshot.list_snapshots()
        if snapshots:
            print("Available snapshots:")
            for s in snapshots:
                print(f"  {s['timestamp']} ({s['label']}) - {s['files']} files")
        else:
            print("No snapshots found")
        return

    meta = snapshot.create_snapshot(label=args.label)
    print(f"✓ Snapshot created: {meta['timestamp']}")
    print(f"  Label: {meta['label']}")
    print(f"  Files captured: {meta['files_count']}")
    for component, info in meta["components"].items():
        print(f"    - {component}: {info['files']} files")


if __name__ == "__main__":
    main()
