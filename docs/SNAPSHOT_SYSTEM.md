# TK-Ai-Maxx Snapshot System

## Overview

The snapshot system enables **time-travel for consistent information** across the TK-Ai-Maxx cluster. Instead of querying against "now + whatever model knows," agents mount a frozen snapshot at a specific timestamp and answer **only from that snapshot**.

**Mathematical principle:**

$$\text{Answer} = \text{Query}(F \mid S_t)$$

where $S_t$ is the snapshot at time $t$, not `Query(F | current + model memory)`.

---

## Features

### 1. **Frozen Snapshots**
Every snapshot captures a complete, consistent state:
- Skills library (`ct/skills/`)
- Tool scripts (`tools/`)
- Governance rules and policies
- Vault indexes (patterns, signals, triggers, graphs)
- Full manifest with metadata

### 2. **Time-Travel Reader**
Mount any past snapshot and query facts exactly as they were:
```bash
python3 tools/time_travel_reader.py --mount "20260312T211215Z" --query "total_files"
```

### 3. **Investigation Checkpoints**
Freeze system state at critical points (e.g., before/after investigation):
```python
from tools.snapshot_integration import SnapshotIntegration

integration = SnapshotIntegration()
checkpoint = integration.create_investigation_checkpoint()
```

### 4. **Evidence-Snapshot Linking**
Evidence records automatically embed snapshot metadata:
```json
{
  "signal_id": "sig-abc123",
  "analysis": { ... },
  "snapshot": {
    "timestamp": "20260312T211215Z",
    "allows_time_travel": true
  }
}
```

---

## Usage

### Create a Snapshot

```bash
# Create snapshot with label
python3 ~/TK-Ai-Maxx/tools/snapshot_state.py --label "pre-clawX"

# Output:
# ✓ Snapshot created: 20260312T211215Z
#   Label: pre-clawX
#   Files captured: 57
#     - skills: 12 files
#     - tools: 18 files
#     - vault_index: 4 files
```

### List Snapshots

```bash
python3 ~/TK-Ai-Maxx/tools/time_travel_reader.py --list

# Output:
# Available snapshots:
#   20260312T211215Z (investigation-checkpoint-2026-03-12T21:12:15) - 57 files
#   20260312T205000Z (pre-clawX) - 57 files
```

### Mount and Query

```bash
# Mount a snapshot
python3 ~/TK-Ai-Maxx/tools/time_travel_reader.py --mount "pre-clawX"

# Query facts from it
python3 ~/TK-Ai-Maxx/tools/time_travel_reader.py --mount "pre-clawX" --query "total_files"

# List skills in that snapshot
python3 ~/TK-Ai-Maxx/tools/time_travel_reader.py --mount "pre-clawX" --skills

# List governance rules
python3 ~/TK-Ai-Maxx/tools/time_travel_reader.py --mount "pre-clawX" --rules
```

### From Python Code

```python
from tools.snapshot_integration import SnapshotIntegration

integration = SnapshotIntegration()

# Create checkpoint
checkpoint = integration.create_investigation_checkpoint()
print(checkpoint["checkpoint_id"])  # 20260312T211215Z

# Look up a fact from a specific snapshot
fact = integration.time_travel_fact_lookup("pre-clawX", "total_files")

# Read a skill from the past
skill_code = integration.read_skill_from_snapshot("pre-clawX", "cluster_cartographer")

# Read governance rules as they were then
rule = integration.read_governance_from_snapshot("pre-clawX", "safety_rule_v2")

# Embed snapshot in evidence
evidence = {"signal_id": "sig-xyz"}
evidence = integration.embed_snapshot_in_evidence(evidence)
# evidence now includes: {"snapshot": {"timestamp": "20260312T211215Z", ...}}
```

---

## Architecture

```
~/ TK-Ai-Maxx/
├── vault/
│   ├── snapshots/                    ← Frozen state archives
│   │   ├── 20260312T211215Z/         ← Immutable snapshot
│   │   │   ├── skills/               ← Skills at this moment
│   │   │   ├── tools/                ← Tools at this moment
│   │   │   ├── governance/           ← Rules at this moment
│   │   │   ├── vault_index/          ← Patterns, signals, etc
│   │   │   └── MANIFEST.json         ← Metadata
│   │   └── .snapshot_index.json      ← Index of all snapshots
│   ├── evidence/
│   └── runtime/
├── tools/
│   ├── snapshot_state.py             ← Create snapshots
│   ├── time_travel_reader.py         ← Query snapshots
│   └── snapshot_integration.py       ← Integration bridge
└── ct/
    ├── skills/
    └── rules/
```

---

## Snapshot Structure

### MANIFEST.json

```json
{
  "timestamp": "20260312T211215Z",
  "label": "pre-clawX",
  "created_at": "2026-03-12T21:12:15.783096",
  "files_count": 57,
  "components": {
    "skills": {
      "source": "/home/zebadiee/TK-Ai-Maxx/ct/skills",
      "files": 12
    },
    "tools": {
      "source": "/home/zebadiee/TK-Ai-Maxx/tools",
      "files": 18
    }
  }
}
```

### .snapshot_index.json

```json
{
  "snapshots": [
    {
      "timestamp": "20260312T211215Z",
      "label": "investigation-checkpoint-2026-03-12T21:12:15",
      "files": 57
    },
    {
      "timestamp": "20260312T205000Z",
      "label": "pre-clawX",
      "files": 57
    }
  ]
}
```

---

## Why This Matters

### Problem
Without snapshots:
- "What was true about the system when this signal occurred?" → Unclear
- Agent queries current facts + model knowledge = inconsistent
- Debugging: "Which version of the skill was active?" → Lost to time

### Solution
With snapshots:
- **Reproducibility**: Same snapshot + same query → same answer, always
- **Auditability**: Evidence records exactly which snapshot they reference
- **Debugging**: "Mount Feb 1 snapshot, query the facts" → exact historical state
- **Consistency**: Investigation engine reads governance, skills, patterns from frozen moment

---

## Integration Points

### 1. Investigation Engine
```python
from tools.snapshot_integration import SnapshotIntegration

# At start of investigation
integration = SnapshotIntegration()
checkpoint = integration.create_investigation_checkpoint()

# During investigation, embed in evidence
evidence = {
  "signal_id": "sig-abc",
  "analysis": model_output
}
evidence = integration.embed_snapshot_in_evidence(evidence)
```

### 2. ClawX Policy Engine
```python
# Query governance rules from when signal occurred
rule = integration.read_governance_from_snapshot(
  checkpoint_id="20260312T211215Z",
  rule_name="safety_rule_v2"
)
```

### 3. Evidence Ledger
Evidence records automatically track:
- Which snapshot they reference
- When the snapshot was created
- What was frozen in it

---

## Operational Flow

```
Signal Arrives
    ↓
Create Investigation Checkpoint (Snapshot S_t)
    ↓
Investigation Engine
    ├─ Query facts from S_t
    ├─ Read skills from S_t
    ├─ Apply governance from S_t
    ↓
Write Evidence
    ├─ Embed snapshot metadata (S_t reference)
    ├─ Link back to checkpoint
    ↓
ClawX Reasoning
    ├─ Can time-travel to S_t
    ├─ Verify facts as they were
    ├─ Justify decisions
    ↓
Policy Daemon
    └─ Acts on evidence + snapshot context
```

---

## Best Practices

### 1. Create Snapshots at Milestones
```bash
# Before major changes
python3 tools/snapshot_state.py --label "before-policy-update"

# After system initialization
python3 tools/snapshot_state.py --label "initialized"

# Before each investigation run (automated)
```

### 2. Reference Snapshots in Evidence
Always embed checkpoint ID in investigation output:
```python
evidence["snapshot_id"] = checkpoint["checkpoint_id"]
```

### 3. Use Time-Travel for Debugging
When something unexpected happens:
```bash
# Mount the snapshot from when it occurred
python3 tools/time_travel_reader.py --mount "20260312T151500Z" --skills
# Compare to current skills
ls ~/TK-Ai-Maxx/ct/skills/
```

### 4. Automated Checkpoint Creation
Modify investigation daemon to auto-create checkpoint:
```python
integration = SnapshotIntegration()
checkpoint = integration.create_investigation_checkpoint()
# Investigation runs with this checkpoint
```

---

## Commands Reference

### Snapshot State (Create)
```bash
python3 tools/snapshot_state.py --label "my-label"    # Create snapshot
python3 tools/snapshot_state.py --list                 # List all
```

### Time Travel Reader (Query)
```bash
python3 tools/time_travel_reader.py --list                          # List snapshots
python3 tools/time_travel_reader.py --mount "label" --skills        # List skills
python3 tools/time_travel_reader.py --mount "label" --rules         # List rules
python3 tools/time_travel_reader.py --mount "label" --query "total" # Query fact
```

### Integration (Python)
```python
from tools.snapshot_integration import SnapshotIntegration

integration = SnapshotIntegration()
cp = integration.create_investigation_checkpoint()
fact = integration.time_travel_fact_lookup(cp["checkpoint_id"], "total_files")
skill = integration.read_skill_from_snapshot(cp["checkpoint_id"], "skill_name")
integration.list_snapshots()
```

---

## Current Status (2026-03-12)

✅ **Snapshot System Operational**
- Snapshot state capture: Working
- Time-travel reader: Working
- Integration module: Working
- First checkpoint created: `20260312T211215Z` (57 files)

**Next Steps:**
1. Wire snapshot checkpoints into investigation daemon
2. Embed snapshots in all evidence records
3. Build snapshot comparison tool (detect what changed between snapshots)
4. Create snapshot rotation policy (auto-cleanup old snapshots)

