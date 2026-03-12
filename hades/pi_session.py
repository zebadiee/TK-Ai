"""Pi session management and social-mode selection."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SESSION_DIR = Path("~/TK-Ai-Maxx/vault/runtime/pi_sessions").expanduser()

MOOD_TO_MODE: dict[str, str] = {
    "calm": "serious",
    "focused": "serious",
    "anxious": "soother",
    "curious": "witty",
    "excited": "witty",
    "pissed": "roaster",
    "drunk": "roaster",
    "tired": "soother",
}

MODE_PREAMBLE: dict[str, str] = {
    "serious": (
        "You are Pi, a precise and terse assistant.  "
        "Answer directly, no fluff, no follow-up suggestions."
    ),
    "witty": (
        "You are Pi, a playful and sharp assistant.  "
        "Be informative with a light touch of humour.  "
        "No follow-up trails."
    ),
    "roaster": (
        "You are Pi, a blunt assistant with dry humour.  "
        "Keep it respectful but pull no punches.  "
        "One answer, no breadcrumbs."
    ),
    "soother": (
        "You are Pi, a calm and reassuring assistant.  "
        "Speak gently, keep it minimal, no extra suggestions."
    ),
}


def resolve_mode(mood: str | None) -> str:
    return MOOD_TO_MODE.get((mood or "focused").lower(), "serious")


def preamble_for(mood: str | None) -> str:
    return MODE_PREAMBLE[resolve_mode(mood)]


@dataclass
class PiSession:
    session_id: str = ""
    user_mood: str = "focused"
    snapshot_label: str = ""
    mode: str = "serious"
    started_at: float = 0.0
    entries: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = f"pi-{uuid.uuid4().hex[:12]}"
        if not self.started_at:
            self.started_at = time.time()
        self.mode = resolve_mode(self.user_mood)

    def log_entry(
        self,
        *,
        user_text: str,
        skills_used: list[str],
        nodes: list[str],
        model_tier: str,
        success: bool,
        summary: str,
    ) -> None:
        self.entries.append(
            {
                "ts": time.time(),
                "user_text": user_text[:200],
                "skills": skills_used,
                "nodes": nodes,
                "model_tier": model_tier,
                "success": success,
                "summary": summary[:500],
            }
        )

    def persist(self) -> Path:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        path = SESSION_DIR / f"{self.session_id}.json"
        path.write_text(
            json.dumps(asdict(self), indent=2, default=str),
            encoding="utf-8",
        )
        return path
