"""Read-only Hermes API over vault artifacts, plus Pi assistant endpoint."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

BASE = Path("vault")
POLICY = BASE / "policy" / "scheduler_policy.json"
EVIDENCE = BASE / "evidence" / "evidence.jsonl"
CLAIMS = BASE / "evidence" / "claims.jsonl"
SIGNALS = BASE / "runtime" / "signals.jsonl"
CLAWX_LOG = BASE / "runtime" / "clawx_log.jsonl"


def tail_jsonl(path: Path, n: int = 10) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    items: list[dict[str, Any]] = []
    for line in lines[-n:]:
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        if isinstance(data, dict):
            items.append(data)
    return items


def scheduler_state() -> str:
    result = subprocess.run(
        ["systemctl", "--user", "is-active", "tkai-scheduler.service"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() or "unknown"


@app.get("/status")
def status() -> dict[str, Any]:
    policy = json.loads(POLICY.read_text(encoding="utf-8")) if POLICY.exists() else {}
    if not isinstance(policy, dict):
        policy = {}
    return {
        "scheduler": scheduler_state(),
        "policy": policy,
    }


@app.get("/signals")
def signals() -> list[dict[str, Any]]:
    return tail_jsonl(SIGNALS)


@app.get("/evidence")
def evidence() -> list[dict[str, Any]]:
    return tail_jsonl(EVIDENCE)


@app.get("/claims")
def claims() -> list[dict[str, Any]]:
    return tail_jsonl(CLAIMS)


@app.get("/clawx/insights")
def clawx_insights() -> list[dict[str, Any]]:
    return tail_jsonl(CLAWX_LOG, n=40)


# ---------------------------------------------------------------------------
# Pi assistant endpoint
# ---------------------------------------------------------------------------

class PiPayload(BaseModel):
    user_text: str
    user_mood: Optional[str] = "focused"
    snapshot_label: Optional[str] = ""
    session_id: Optional[str] = ""


_pi_engine = None


def _get_pi():
    global _pi_engine
    if _pi_engine is None:
        from hades.pi_engine import PiEngine
        _pi_engine = PiEngine()
    return _pi_engine


@app.post("/pi")
def pi_endpoint(payload: PiPayload) -> dict[str, Any]:
    from hades.pi_engine import PiRequest
    engine = _get_pi()
    resp = engine.handle(
        PiRequest(
            user_text=payload.user_text,
            user_mood=payload.user_mood or "focused",
            snapshot_label=payload.snapshot_label or "",
            session_id=payload.session_id or "",
        )
    )
    return {
        "text": resp.text,
        "skills_used": resp.skills_used,
        "nodes": resp.nodes,
        "model_tier": resp.model_tier,
        "success": resp.success,
        "session_id": resp.session_id,
    }


@app.post("/pi/close")
def pi_close(session_id: str) -> dict[str, str]:
    engine = _get_pi()
    engine.close_session(session_id)
    return {"status": "closed", "session_id": session_id}


@app.post("/pi/reload")
def pi_reload() -> dict[str, Any]:
    engine = _get_pi()
    count = engine.reload_skills()
    return {"status": "reloaded", "skills": count}
