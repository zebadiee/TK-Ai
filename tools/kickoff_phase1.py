#!/usr/bin/env python3
"""Run the current Phase 1 startup sequence for TK-Ai."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run_step(label: str, script: str, *, long_running: bool = False) -> int:
    path = REPO_ROOT / script
    print(f"\n== {label} ==", flush=True)
    print(f"$ {PYTHON} {script}", flush=True)

    if long_running:
        completed = subprocess.run([PYTHON, str(path)], cwd=REPO_ROOT)
    else:
        completed = subprocess.run([PYTHON, str(path)], cwd=REPO_ROOT, check=False)

    if completed.returncode != 0:
        print(f"\nStep failed: {label} (exit {completed.returncode})", file=sys.stderr)
        return completed.returncode
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Kick off the current TK-Ai Phase 1 flow")
    parser.add_argument(
        "--scheduler",
        action="store_true",
        help="Start the ACME example scheduler after the staged checks pass",
    )
    args = parser.parse_args()

    steps = [
        ("ClawX Sandbox Stream", "sandbox/clawx_lab/simulate_evidence_stream.py"),
        ("ACME Example Workflow", "examples/basic_run.py"),
        ("Entity Registry Sync", "tools/sync_entities_to_obsidian.py"),
        ("TK-Ai Knowledge Sync", "tools/sync_tkai_knowledge_to_obsidian.py"),
    ]

    for label, script in steps:
        result = run_step(label, script)
        if result != 0:
            return result

    if not args.scheduler:
        print("\nPhase 1 kickoff checks completed.")
        print("Run with --scheduler to hand off into the long-running ACME example loop.")
        return 0

    print("\nPhase 1 kickoff checks completed. Starting scheduler.")
    return run_step(
        "ACME Scheduler",
        "examples/acme_ai/run_scheduler.py",
        long_running=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
