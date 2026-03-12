#!/usr/bin/env python3
"""Report whether the ACME example scheduler is currently running."""

from __future__ import annotations

import subprocess
import sys

PATTERN = "/home/zebadiee/TK-Ai-Maxx/examples/acme_ai/run_scheduler.py"


def main() -> int:
    result = subprocess.run(
        ["pgrep", "-af", PATTERN],
        capture_output=True,
        text=True,
        check=False,
    )

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        print("TK-Ai scheduler: not running")
        return 1

    print("TK-Ai scheduler: running")
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
