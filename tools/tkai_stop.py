#!/usr/bin/env python3
"""Stop the ACME example scheduler if it is running."""

from __future__ import annotations

import subprocess

PATTERN = "/home/zebadiee/TK-Ai-Maxx/examples/acme_ai/run_scheduler.py"


def main() -> int:
    status = subprocess.run(
        ["pgrep", "-af", PATTERN],
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [line.strip() for line in status.stdout.splitlines() if line.strip()]
    if not lines:
        print("TK-Ai scheduler: not running")
        return 0

    stop = subprocess.run(["pkill", "-f", PATTERN], check=False)
    if stop.returncode != 0:
        print("TK-Ai scheduler: stop failed")
        return stop.returncode

    print("TK-Ai scheduler: stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
