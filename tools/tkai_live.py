#!/usr/bin/env python3
"""Repeatedly render Mission Control for a live terminal view."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MISSION_CONTROL = REPO_ROOT / "tools" / "tkai_mission_control.py"


def main() -> int:
    parser = argparse.ArgumentParser(description="Live TK-Ai Mission Control dashboard")
    parser.add_argument("--interval", type=int, default=5, help="Refresh interval in seconds")
    args = parser.parse_args()

    while True:
        print("\033[2J\033[H", end="")
        subprocess.run([sys.executable, str(MISSION_CONTROL)], cwd=REPO_ROOT, check=False)
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
