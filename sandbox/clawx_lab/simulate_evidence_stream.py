#!/usr/bin/env python3
"""Sandbox driver for the standalone ClawX evidence stream module."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.clawx_engine.clawx_engine import ClawXEngine
from modules.clawx_engine.clawx_subscriber import ClawXSubscriber
from modules.clawx_engine.scheduler_policy_writer import SchedulerPolicyWriter
from modules.clawx_engine.signal_adapter import SignalAdapter


class FakeSignalEngine:
    def receive(self, signal):
        print("Signal emitted:", signal)


def main() -> int:
    adapter = SignalAdapter(FakeSignalEngine())
    writer = SchedulerPolicyWriter(REPO_ROOT / "vault" / "policy" / "scheduler_policy.json")
    engine = ClawXEngine(signal_adapter=adapter, scheduler_policy_writer=writer)
    subscriber = ClawXSubscriber(engine)

    event = SimpleNamespace(
        type="observation",
        content={"exchange": "binance", "funding_rate": 0.23},
        trace_id="sandbox-trace",
    )
    subscriber.on_event(event)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
