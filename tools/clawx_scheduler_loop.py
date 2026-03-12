#!/usr/bin/env python3
"""Compatibility wrapper for the ClawX scheduler loop entrypoint."""

from __future__ import annotations

from tools.clawx_scheduler import main


if __name__ == "__main__":
    raise SystemExit(main())
