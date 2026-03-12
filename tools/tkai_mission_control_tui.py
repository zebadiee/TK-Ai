#!/usr/bin/env python3
"""Continuously refresh the Mission Control artifact view."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MISSION_CONTROL = ROOT / "tools" / "tkai_mission_control.py"


def clear_screen() -> None:
    print("\033[2J\033[H", end="", flush=True)


def run_once(runner=subprocess.run) -> int:
    result = runner([sys.executable, str(MISSION_CONTROL)], cwd=ROOT, check=False)
    return int(getattr(result, "returncode", 0))


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh TK-AI Mission Control in a simple terminal loop")
    parser.add_argument("--once", action="store_true", help="Render Mission Control once and exit")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between refreshes")
    args = parser.parse_args()

    try:
        while True:
            clear_screen()
            run_once()
            if args.once:
                return 0
            time.sleep(max(args.interval, 0.1))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
