#!/usr/bin/env python3
"""Continuously analyse recent signals with the investigation engine."""

from __future__ import annotations

import argparse
import time

from modules.investigation_engine.investigation_loop import run_investigation

CHECK_INTERVAL = 30


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the TK-Ai investigation loop continuously")
    parser.add_argument("--once", action="store_true", help="Run one investigation pass and exit")
    parser.add_argument("--interval", type=int, default=CHECK_INTERVAL, help="Seconds between runs")
    args = parser.parse_args()

    if args.once:
        run_investigation()
        return 0

    while True:
        try:
            run_investigation()
        except Exception as exc:
            print(f"Investigation error: {exc}", flush=True)
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())

