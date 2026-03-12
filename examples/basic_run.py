#!/usr/bin/env python3
"""Run the ACME-AI example workload in an isolated workspace."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hades.triggers import TriggerEvent
from kernel.kernel import build_default_kernel

BASE_VAULT_FILES = ("patterns.json", "capabilities.json")
PACK_VAULT_FILES = ("graph_index.json", "signals.json", "triggers.json")
PACK_NAME = "acme_ai"
TRACE_ID = "example-acme-btc-funding"


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _prepare_workspace(workspace_root: Path) -> None:
    repo_vault = REPO_ROOT / "vault"
    workspace_vault = workspace_root / "vault"
    pack_root = REPO_ROOT / "examples" / PACK_NAME

    for name in BASE_VAULT_FILES:
        _copy_file(repo_vault / name, workspace_vault / name)

    for name in PACK_VAULT_FILES:
        _copy_file(pack_root / name, workspace_vault / name)

    shutil.copytree(pack_root / "solution_graphs", workspace_vault / "solution_graphs", dirs_exist_ok=True)


def _emit(label: str, payload: dict[str, object]) -> None:
    print(f"{label}:")
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> int:
    with TemporaryDirectory(prefix="tk-ai-example-") as tmpdir:
        workspace_root = Path(tmpdir)
        _prepare_workspace(workspace_root)

        kernel = build_default_kernel(workspace_root)
        initial = kernel.handle_event(
            TriggerEvent(
                event_type="schedule_tick",
                payload={
                    "hour": 9,
                    "asset": "BTC",
                    "exchange": "ACME-AI",
                    "trace_id": TRACE_ID,
                },
            )
        )
        _emit("trigger_result", initial)

        if initial.get("status") != "accepted":
            return 1

        pending_jobs = initial.get("pending_jobs", {})
        if not isinstance(pending_jobs, dict) or not pending_jobs:
            return 1

        job_id = next(iter(pending_jobs))
        resumed = kernel.handle_job_finished(
            {
                "trace_id": TRACE_ID,
                "job_id": job_id,
                "result": {
                    "status": "ok",
                    "summary": "BTC funding deviated above the ACME watch threshold.",
                },
            }
        )
        _emit("resume_result", resumed)

        final_event = kernel.state["events"][-1]
        _emit(
            "final_event",
            {
                "entry_mode": final_event.get("entry_mode"),
                "graph_id": final_event.get("graph_id"),
                "node_status": final_event.get("node_status"),
                "status": final_event.get("status"),
            },
        )
        return 0 if resumed.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
