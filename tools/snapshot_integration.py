#!/usr/bin/env python3
"""
Integrate time-travel snapshots into the TK-Ai-Maxx investigation engine.

This module:
1. Automatically creates snapshots at critical points
2. Embeds snapshot metadata in evidence records
3. Allows investigation engine to reference facts from specific points in time
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Import snapshot tools (need to be in same tools directory)
sys.path.insert(0, os.path.expanduser("~/TK-Ai-Maxx/tools"))

try:
    from snapshot_state import SnapshotState
    from time_travel_reader import TimeTravelReader
except ImportError as e:
    print(f"Warning: Could not import snapshot tools: {e}")
    SnapshotState = None
    TimeTravelReader = None


class SnapshotIntegration:
    """
    Bridges snapshot system with investigation engine.
    """
    
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or os.path.expanduser("~/TK-Ai-Maxx"))
        self.snapshot_state = SnapshotState(str(self.base_path)) if SnapshotState else None
        self.time_travel = TimeTravelReader(str(self.base_path)) if TimeTravelReader else None
        self.current_snapshot_id = None

    def create_checkpoint_snapshot(self, label: str) -> Optional[Dict[str, Any]]:
        """
        Create a named checkpoint snapshot (e.g., "pre-investigation", "post-policy").
        
        Args:
            label: Human-readable checkpoint name
        
        Returns:
            Snapshot metadata or None if snapshot system unavailable
        """
        if not self.snapshot_state:
            return None

        meta = self.snapshot_state.create_snapshot(label=label)
        self.current_snapshot_id = meta["timestamp"]
        return meta

    def embed_snapshot_in_evidence(self, evidence_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add current snapshot reference to an evidence record.
        
        Args:
            evidence_record: Investigation evidence dict
        
        Returns:
            Enhanced evidence record with snapshot metadata
        """
        if not self.current_snapshot_id:
            return evidence_record

        evidence_record["snapshot"] = {
            "timestamp": self.current_snapshot_id,
            "embedded_at": datetime.utcnow().isoformat(),
            "allows_time_travel": True
        }

        return evidence_record

    def time_travel_fact_lookup(self, snapshot_id: str, fact_key: str) -> Optional[Any]:
        """
        Query a fact from a specific snapshot.
        
        This is the core time-travel operation.
        
        Args:
            snapshot_id: Snapshot timestamp or label to query
            fact_key: Fact to retrieve (e.g., "total_patterns", "active_signals")
        
        Returns:
            Fact value or None
        """
        if not self.time_travel:
            return None

        if not self.time_travel.mount_snapshot(snapshot_id):
            return None

        return self.time_travel.query_fact(fact_key)

    def read_skill_from_snapshot(self, snapshot_id: str, skill_name: str) -> Optional[str]:
        """
        Retrieve a skill definition from a past snapshot.
        
        Allows reproducible skill-based reasoning from a specific point in time.
        
        Args:
            snapshot_id: Snapshot to read from
            skill_name: Skill to retrieve
        
        Returns:
            Skill content or None
        """
        if not self.time_travel:
            return None

        if not self.time_travel.mount_snapshot(snapshot_id):
            return None

        return self.time_travel.read_skill(skill_name)

    def read_governance_from_snapshot(self, snapshot_id: str, rule_name: str) -> Optional[str]:
        """
        Retrieve a governance rule from a past snapshot.
        
        Allows investigation engine to reference the exact rules that were active
        when a signal occurred.
        
        Args:
            snapshot_id: Snapshot to read from
            rule_name: Governance rule to retrieve
        
        Returns:
            Rule content or None
        """
        if not self.time_travel:
            return None

        if not self.time_travel.mount_snapshot(snapshot_id):
            return None

        return self.time_travel.read_governance_rule(rule_name)

    def create_investigation_checkpoint(self) -> Dict[str, Any]:
        """
        Create a checkpoint snapshot at the start of an investigation.
        
        This freezes the state of skills, governance, and patterns so that
        the investigation can reference exactly what was defined at this moment.
        
        Returns:
            Checkpoint metadata with timestamp and label
        """
        timestamp = datetime.utcnow().isoformat()
        label = f"investigation-checkpoint-{timestamp}"

        meta = self.create_checkpoint_snapshot(label)

        return {
            "checkpoint_id": self.current_snapshot_id,
            "label": label,
            "created_at": timestamp,
            "metadata": meta
        }

    def list_snapshots(self) -> list:
        """List all available snapshots."""
        if not self.snapshot_state:
            return []

        return self.snapshot_state.list_snapshots()


def integrate_snapshots_into_investigation(investigation_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Utility function to add snapshot context to an investigation.
    
    Args:
        investigation_record: Investigation engine output
    
    Returns:
        Investigation record enhanced with snapshot metadata
    """
    integration = SnapshotIntegration()
    
    # Add snapshot info to investigation
    investigation_record["snapshots_available"] = len(integration.list_snapshots())
    
    if integration.current_snapshot_id:
        investigation_record["active_snapshot"] = integration.current_snapshot_id

    return investigation_record


if __name__ == "__main__":
    # Demo: Create a checkpoint and list snapshots
    integration = SnapshotIntegration()

    # Create checkpoint
    checkpoint = integration.create_investigation_checkpoint()
    print(f"✓ Investigation checkpoint created")
    print(f"  ID: {checkpoint['checkpoint_id']}")
    print(f"  Label: {checkpoint['label']}")

    # List all snapshots available
    snapshots = integration.list_snapshots()
    print(f"\nAvailable snapshots: {len(snapshots)}")
    for snap in snapshots:
        print(f"  - {snap['timestamp']} ({snap['label']})")

