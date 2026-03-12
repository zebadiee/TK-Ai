#!/usr/bin/env python3
"""
Time-travel reader for TK-Ai-Maxx snapshots.

Mounts a frozen snapshot and allows querying facts, skills, and governance
exactly as they were at that point in time.

Mathematics: Answer = Query(F | S_t) where S_t is snapshot at time t.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


class TimeTravelReader:
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or os.path.expanduser("~/TK-Ai-Maxx"))
        self.snapshot_root = self.base_path / "vault" / "snapshots"
        self.current_snapshot = None
        self.snapshot_path = None

    def list_available_snapshots(self) -> list:
        """List all available snapshots with metadata."""
        index_path = self.snapshot_root / ".snapshot_index.json"
        
        if not index_path.exists():
            return []

        with open(index_path, "r") as f:
            index = json.load(f)

        return index.get("snapshots", [])

    def mount_snapshot(self, timestamp_or_label: str) -> bool:
        """
        Mount a snapshot by timestamp or label.
        
        Args:
            timestamp_or_label: ISO timestamp (e.g., "20260312T154300Z") or label (e.g., "pre-clawX")
        
        Returns:
            True if mounted successfully
        """
        snapshots = self.list_available_snapshots()
        
        # Try exact timestamp match first
        for snap in snapshots:
            if snap["timestamp"] == timestamp_or_label:
                self.snapshot_path = self.snapshot_root / timestamp_or_label
                self.current_snapshot = snap
                return True
        
        # Try label match
        for snap in snapshots:
            if snap["label"] == timestamp_or_label:
                self.snapshot_path = self.snapshot_root / snap["timestamp"]
                self.current_snapshot = snap
                return True
        
        return False

    def read_file_from_snapshot(self, rel_path: str) -> Optional[str]:
        """
        Read a file from the mounted snapshot.
        
        Args:
            rel_path: Relative path within snapshot (e.g., "tools/clawx_scheduler.py")
        
        Returns:
            File contents or None if not found
        """
        if not self.snapshot_path:
            raise RuntimeError("No snapshot mounted. Call mount_snapshot() first.")

        full_path = self.snapshot_path / rel_path
        
        if not full_path.exists():
            return None

        with open(full_path, "r") as f:
            return f.read()

    def list_skills(self) -> list:
        """List all skills in mounted snapshot."""
        if not self.snapshot_path:
            raise RuntimeError("No snapshot mounted.")

        skills_dir = self.snapshot_path / "skills"
        if not skills_dir.exists():
            return []

        skills = []
        for skill_file in skills_dir.rglob("*.md"):
            skills.append({
                "name": skill_file.stem,
                "path": str(skill_file.relative_to(self.snapshot_path))
            })

        return skills

    def read_skill(self, skill_name: str) -> Optional[str]:
        """Read a specific skill from snapshot."""
        if not self.snapshot_path:
            raise RuntimeError("No snapshot mounted.")

        skill_path = self.snapshot_path / "skills" / f"{skill_name}.md"
        
        if not skill_path.exists():
            return None

        with open(skill_path, "r") as f:
            return f.read()

    def list_governance(self) -> list:
        """List all governance rules in snapshot."""
        if not self.snapshot_path:
            raise RuntimeError("No snapshot mounted.")

        gov_dir = self.snapshot_path / "governance"
        if not gov_dir.exists():
            return []

        rules = []
        for rule_file in gov_dir.rglob("*.md"):
            rules.append({
                "name": rule_file.stem,
                "path": str(rule_file.relative_to(self.snapshot_path))
            })

        return rules

    def read_governance_rule(self, rule_name: str) -> Optional[str]:
        """Read a specific governance rule from snapshot."""
        if not self.snapshot_path:
            raise RuntimeError("No snapshot mounted.")

        rule_path = self.snapshot_path / "governance" / f"{rule_name}.md"
        
        if not rule_path.exists():
            return None

        with open(rule_path, "r") as f:
            return f.read()

    def get_vault_index(self, index_type: str = "pattern") -> Optional[dict]:
        """
        Get a vault index from snapshot (patterns, signals, etc).
        
        Args:
            index_type: Type of index (pattern, signal, trigger, graph)
        
        Returns:
            Index dict or None if not found
        """
        if not self.snapshot_path:
            raise RuntimeError("No snapshot mounted.")

        index_file = self.snapshot_path / "vault_index" / f"{index_type}_index.json"
        
        if not index_file.exists():
            return None

        with open(index_file, "r") as f:
            return json.load(f)

    def get_snapshot_metadata(self) -> Optional[dict]:
        """Get metadata for currently mounted snapshot."""
        if not self.current_snapshot:
            return None

        manifest_path = self.snapshot_path / "MANIFEST.json"
        
        if not manifest_path.exists():
            return None

        with open(manifest_path, "r") as f:
            return json.load(f)

    def query_fact(self, fact_key: str) -> Optional[Any]:
        """
        Query facts about the system as it existed in this snapshot.
        
        This is the core time-travel query function.
        
        Facts are sourced from:
        - Vault indexes (patterns, signals, triggers)
        - Manifest metadata
        - Skill definitions
        
        Args:
            fact_key: Fact to query (e.g., "total_patterns", "active_signals")
        
        Returns:
            Fact value or None
        """
        if not self.snapshot_path:
            raise RuntimeError("No snapshot mounted.")

        # Try manifest
        manifest = self.get_snapshot_metadata()
        if manifest:
            if fact_key == "timestamp":
                return manifest.get("timestamp")
            if fact_key == "label":
                return manifest.get("label")
            if fact_key == "created_at":
                return manifest.get("created_at")
            if fact_key == "total_files":
                return manifest.get("files_count")

        # Try pattern index
        pattern_idx = self.get_vault_index("pattern")
        if pattern_idx and fact_key == "total_patterns":
            return len(pattern_idx.get("patterns", []))

        # Try signal index
        signal_idx = self.get_vault_index("signal")
        if signal_idx and fact_key == "active_signals":
            return len(signal_idx.get("signals", []))

        return None

    def compare_with_current(self, fact_key: str) -> dict:
        """
        Compare a fact in the snapshot to the current system.
        
        Returns dict with snapshot value and current value (if readable).
        """
        snapshot_value = self.query_fact(fact_key)
        
        return {
            "snapshot_timestamp": self.current_snapshot["timestamp"],
            "snapshot_value": snapshot_value,
            "query": fact_key
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Time-travel reader for TK-Ai snapshots")
    parser.add_argument("--list", action="store_true", help="List available snapshots")
    parser.add_argument("--mount", type=str, help="Mount snapshot by timestamp or label")
    parser.add_argument("--query", type=str, help="Query a fact from mounted snapshot")
    parser.add_argument("--read", type=str, help="Read skill/file from snapshot")
    parser.add_argument("--skills", action="store_true", help="List skills in snapshot")
    parser.add_argument("--rules", action="store_true", help="List governance in snapshot")
    parser.add_argument("--path", type=str, default=None, help="Base TK-Ai-Maxx path")
    
    args = parser.parse_args()

    reader = TimeTravelReader(args.path)

    if args.list:
        snapshots = reader.list_available_snapshots()
        if snapshots:
            print("Available snapshots:")
            for s in snapshots:
                print(f"  {s['timestamp']} ({s['label']}) - {s['files']} files")
        else:
            print("No snapshots found")
        return

    if args.mount:
        if reader.mount_snapshot(args.mount):
            meta = reader.get_snapshot_metadata()
            print(f"✓ Mounted snapshot: {args.mount}")
            print(f"  Label: {meta['label']}")
            print(f"  Created: {meta['created_at']}")
            print(f"  Files: {meta['files_count']}")
        else:
            print(f"✗ Snapshot not found: {args.mount}")
            return

    if args.skills and reader.current_snapshot:
        skills = reader.list_skills()
        print(f"Skills in {reader.current_snapshot['label']}:")
        for skill in skills:
            print(f"  - {skill['name']}")

    if args.rules and reader.current_snapshot:
        rules = reader.list_governance()
        print(f"Governance rules in {reader.current_snapshot['label']}:")
        for rule in rules:
            print(f"  - {rule['name']}")

    if args.query and reader.current_snapshot:
        value = reader.query_fact(args.query)
        print(f"Query: {args.query}")
        print(f"Value: {value}")
        print(f"From snapshot: {reader.current_snapshot['timestamp']}")


if __name__ == "__main__":
    main()
