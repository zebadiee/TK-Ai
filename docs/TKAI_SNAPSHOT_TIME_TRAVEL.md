# TK-Ai Snapshot Time Travel

TK-Ai uses versioned snapshots to answer historical questions from a frozen state instead of the current workspace.

## Canonical Rule

When an operator asks for time travel, choose one snapshot and stay inside it.

- Capture state with `python tools/snapshot_state.py --label tkai-ready-alpha`
- Query markdown only with `python tools/time_travel_reader.py wiki "cluster doctor" --snapshot tkai-ready-alpha`
- Query structured facts only with `python tools/time_travel_reader.py fact "signal_id" --snapshot tkai-ready-alpha`
- Read one frozen file with `python tools/time_travel_reader.py cat var/wiki/wiki_index.json --snapshot tkai-ready-alpha`

Do not mix snapshot output with current-head files, live runtime state, or free model recall.

## Snapshot Contents

The default snapshot root is [snapshots](/home/zebadiee/TK-Ai-Maxx/snapshots). Each snapshot directory contains a frozen copy of the TK-Ai control surface:

- `skills/`
- `scripts/`
- `governance/`
- `cluster/`
- `var/wiki/`
- `var/inventory/`
- `manifest.json`

The manifest records the snapshot name, human label, generation time, and which sources were actually copied.

## Operator Flow

1. Capture a snapshot before a risky change, rollout, or architecture phase transition.
2. Resolve the snapshot by exact name or human label.
3. Run `wiki`, `fact`, or `cat` against that snapshot only.
4. Treat the answer as true only for that frozen snapshot.

## Notes

- `wiki` searches markdown files only.
- `fact` searches structured files only: `json`, `jsonl`, `yaml`, `yml`, and `toml`.
- `cat` rejects paths that escape the chosen snapshot root.
