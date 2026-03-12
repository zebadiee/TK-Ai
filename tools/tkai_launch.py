#!/usr/bin/env python3
"""Canonical operator entrypoint for the TK-Ai cluster."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_step(label: str, command: list[str], *, allow_failure: bool = False) -> int:
    print()
    print(label)
    print("-" * len(label))
    print("$", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode != 0 and not allow_failure:
        print(f"Step failed with exit code {result.returncode}", file=sys.stderr)
        return result.returncode
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Canonical TK-Ai cluster launcher")
    parser.add_argument("--tail-only", action="store_true", help="Tail runtime artifacts and exit")
    parser.add_argument(
        "--probe-clawx",
        action="store_true",
        help="Run the ClawX sandbox probe before showing artifacts so the signal stream is populated",
    )
    args = parser.parse_args()

    print("====================================")
    print("TK-AI CLUSTER LAUNCH")
    print("====================================")

    if args.tail_only:
        _tail_artifacts()
        return 0

    steps = [
        ("Step 0: Syncing HADES Assist governance surfaces", [sys.executable, str(ROOT / "tools" / "hades_assist_launcher.py")], True),
        ("Step 1: Starting core runtime", ["/home/zebadiee/bin/tkai-start"]),
        ("Step 2: Starting policy daemon", ["/home/zebadiee/bin/tkai-policy-start"]),
        ("Step 3: Starting status writer", ["systemctl", "--user", "start", "tkai-status.service"]),
        ("Step 4: Checking runtime health", ["/home/zebadiee/bin/tkai-status"], True),
        ("Step 4a: Checking policy daemon", ["/home/zebadiee/bin/tkai-policy-status"], True),
    ]

    if args.probe_clawx:
        steps.append(
            ("Step 5: Probing ClawX signal loop", [sys.executable, str(ROOT / "sandbox" / "clawx_lab" / "simulate_evidence_stream.py")], True)
        )

    steps.extend(
        [
            ("Step 6: Verifying artifact streams", [sys.executable, str(ROOT / "tools" / "tkai_launch.py"), "--tail-only"], True),
            ("Step 7: Launching Mission Control", [sys.executable, str(ROOT / "tools" / "tkai_mission_control.py")], True),
            ("Step 8: Opening ClawX operator console", [sys.executable, str(ROOT / "modules" / "clawx_engine" / "clawx_console.py")]),
        ]
    )

    for step in steps:
        label, command, *rest = step
        allow_failure = bool(rest[0]) if rest else False
        result = run_step(label, command, allow_failure=allow_failure)
        if result != 0:
            return result
    return 0


def _tail_artifacts() -> None:
    for path in (
        ROOT / "vault" / "runtime" / "signals.jsonl",
        ROOT / "vault" / "runtime" / "clawx_log.jsonl",
    ):
        if not path.exists():
            print(f"{path.name}: no entries yet")
            continue
        print(path.name)
        lines = path.read_text(encoding="utf-8").splitlines()
        for line in lines[-3:]:
            print(line)


if __name__ == "__main__":
    raise SystemExit(main())
