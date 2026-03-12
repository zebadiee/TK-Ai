#!/usr/bin/env python3
"""Sync TK-Ai architecture, tools, growth knowledge, and governed skills into Obsidian."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from memory.obsidian_bridge.knowledge_writer import sync_tkai_knowledge
from memory.obsidian_bridge.skill_catalog_writer import sync_skill_catalog
from tools.hades_assist_launcher import load_state, reconcile_skill_state, resolve_skills_root, discover_governed_skills


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync TK-Ai architecture, tools, and governed skill knowledge into Obsidian")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Path to the TK-Ai repository root",
    )
    parser.add_argument(
        "--vault-root",
        type=Path,
        default=Path("~/Obsidian/TK-Ai").expanduser(),
        help="Path to the Obsidian destination root",
    )
    parser.add_argument("--skills-root", type=Path, default=Path.home() / ".codex" / "skills", help="Path to installed skills")
    parser.add_argument("--snapshot", help="Optional snapshot label or name for skill discovery")
    args = parser.parse_args()

    repo_root = args.repo_root.expanduser().resolve()
    vault_root = args.vault_root.expanduser()
    written = sync_tkai_knowledge(repo_root, vault_root)
    skills_root, snapshot_name = resolve_skills_root(args.snapshot, args.skills_root.expanduser())
    skills = discover_governed_skills(skills_root)
    state = load_state()
    reconciled, events, _ = reconcile_skill_state(skills, state, snapshot_name=snapshot_name)
    written.extend(sync_skill_catalog(reconciled, events, vault_root))
    print(f"TK-Ai knowledge synced to Obsidian ({len(written)} notes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
