"""Pi — the governed personal assistant engine for HADES.

This module is the single entry-point for every Pi request.  It:
  1. Loads the assistant manifest and skill registry.
  2. Resolves social mode from user_mood.
  3. Routes the request through the model policy.
  4. Executes only declared skills via the HADES tool bridge.
  5. Logs the session and optionally mirrors to Obsidian.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hades.hades_assist_model_policy import choose_route, classify_task
from hades.obsidian_beacon import append_changelog, write_session_summary
from hades.pi_session import PiSession, preamble_for
from hades.skill_resolver import (
    SkillEntry,
    prefer_home,
    resolve_skills,
    skill_allowed,
)


MANIFEST = ROOT / "hades" / "assistant_manifest.md"

# Skills that map to a Python tool invocation
_SKILL_TOOL_MAP: dict[str, str] = {
    "acme-integration-status": "tools/acme_integration_status.py",
    "acme-runtime-sync": "tools/acme_runtime_sync.py",
    "acme-signal-bridge": "tools/acme_signal_bridge.py",
    "cluster-doctor": "tools/cluster_doctor.py",
    "tkai-status": "tools/tkai_status_writer.py",
    "obsidian-sync": "tools/sync_tkai_knowledge_to_obsidian.py",
    "filesystem-inventory": "tools/snapshot_state.py",
    "snapshot-state": "tools/snapshot_state.py",
    "time-travel-reader": "tools/time_travel_reader.py",
}


@dataclass
class PiRequest:
    user_text: str
    user_mood: str = "focused"
    snapshot_label: str = ""
    session_id: str = ""


@dataclass
class PiResponse:
    text: str
    skills_used: list[str]
    nodes: list[str]
    model_tier: str
    success: bool
    session_id: str = ""


class PiEngine:
    """Core engine behind the /pi endpoint."""

    def __init__(self) -> None:
        self.skills = resolve_skills(MANIFEST)
        self.sessions: dict[str, PiSession] = {}

    def reload_skills(self) -> int:
        self.skills = resolve_skills(MANIFEST)
        return len(self.skills)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle(self, req: PiRequest) -> PiResponse:
        session = self._get_or_create_session(req)

        # 1. Route model tier
        route = choose_route(
            req.user_text,
            user_mood=req.user_mood,
            skill_name=self._guess_skill(req.user_text),
        )

        # 2. Resolve which skills are needed
        matched = self._match_skills(req.user_text)
        if not matched:
            resp = PiResponse(
                text=self._styled(
                    "No matching skill in the manifest for this request.",
                    session.mode,
                ),
                skills_used=[],
                nodes=[],
                model_tier=route.tier,
                success=False,
                session_id=session.session_id,
            )
            session.log_entry(
                user_text=req.user_text,
                skills_used=[],
                nodes=[],
                model_tier=route.tier,
                success=False,
                summary="no_matching_skill",
            )
            session.persist()
            return resp

        # 3. Prefer home-repo skills
        ordered = prefer_home(matched)
        chosen = ordered[0]

        # 4. Gate check
        live = chosen.mutating
        if not skill_allowed(chosen, live=live):
            resp = PiResponse(
                text=self._styled(
                    f"Skill '{chosen.name}' is {chosen.status} and cannot mutate live data.",
                    session.mode,
                ),
                skills_used=[chosen.name],
                nodes=chosen.nodes,
                model_tier=route.tier,
                success=False,
                session_id=session.session_id,
            )
            session.log_entry(
                user_text=req.user_text,
                skills_used=[chosen.name],
                nodes=chosen.nodes,
                model_tier=route.tier,
                success=False,
                summary=f"blocked: {chosen.name} is {chosen.status}",
            )
            session.persist()
            return resp

        # 5. Execute via tool bridge
        output, ok = self._execute_skill(chosen, req)
        summary = output[:300] if ok else f"error: {output[:200]}"

        resp = PiResponse(
            text=self._styled(output, session.mode),
            skills_used=[chosen.name],
            nodes=chosen.nodes,
            model_tier=route.tier,
            success=ok,
            session_id=session.session_id,
        )
        session.log_entry(
            user_text=req.user_text,
            skills_used=[chosen.name],
            nodes=chosen.nodes,
            model_tier=route.tier,
            success=ok,
            summary=summary,
        )
        session.persist()
        return resp

    # ------------------------------------------------------------------
    # Skill matching
    # ------------------------------------------------------------------

    def _guess_skill(self, text: str) -> str | None:
        lowered = text.lower()
        for name in self.skills:
            if name.replace("-", " ") in lowered or name in lowered:
                return name
        return None

    def _match_skills(self, text: str) -> list[SkillEntry]:
        lowered = text.lower()
        hits: list[SkillEntry] = []
        for name, entry in self.skills.items():
            tokens = name.replace("-", " ").split()
            if any(t in lowered for t in tokens):
                hits.append(entry)
        # Also match broad intents
        intent_map: dict[str, list[str]] = {
            "status": ["acme-integration-status", "tkai-status", "cluster-doctor"],
            "sync": ["acme-runtime-sync", "obsidian-sync"],
            "signal": ["acme-signal-bridge"],
            "snapshot": ["snapshot-state"],
            "time travel": ["time-travel-reader"],
            "inventory": ["filesystem-inventory"],
            "doctor": ["cluster-doctor"],
            "obsidian": ["obsidian-sync"],
            "health": ["cluster-doctor", "acme-integration-status"],
        }
        for keyword, skill_names in intent_map.items():
            if keyword in lowered:
                for sn in skill_names:
                    if sn in self.skills and self.skills[sn] not in hits:
                        hits.append(self.skills[sn])
        return hits

    # ------------------------------------------------------------------
    # Tool bridge execution
    # ------------------------------------------------------------------

    def _execute_skill(self, entry: SkillEntry, req: PiRequest) -> tuple[str, bool]:
        tool_path = _SKILL_TOOL_MAP.get(entry.name)
        if not tool_path:
            return f"No tool mapping for skill '{entry.name}'.", False

        cmd = [sys.executable, str(ROOT / tool_path)]
        # Append snapshot label if relevant
        if req.snapshot_label and entry.name in {"time-travel-reader", "snapshot-state"}:
            cmd.extend(["--snapshot", req.snapshot_label])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(ROOT),
            )
        except subprocess.TimeoutExpired:
            return "Skill execution timed out (30s).", False
        except Exception as exc:
            return f"Execution error: {exc}", False

        output = (result.stdout or "").strip()
        if result.returncode != 0:
            err = (result.stderr or "").strip()
            return output + ("\n" + err if err else ""), False
        return output, True

    # ------------------------------------------------------------------
    # Social styling
    # ------------------------------------------------------------------

    def _styled(self, text: str, mode: str) -> str:
        """Apply minimal personality framing — no breadcrumbs."""
        if mode == "roaster":
            return text.rstrip(".") + "."
        if mode == "soother":
            return text
        if mode == "witty" and len(text) < 300:
            return text
        return text

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def _get_or_create_session(self, req: PiRequest) -> PiSession:
        sid = req.session_id
        if sid and sid in self.sessions:
            return self.sessions[sid]
        session = PiSession(
            session_id=sid,
            user_mood=req.user_mood,
            snapshot_label=req.snapshot_label,
        )
        self.sessions[session.session_id] = session
        return session

    def close_session(self, session_id: str) -> None:
        session = self.sessions.pop(session_id, None)
        if session and session.entries:
            write_session_summary(
                session.session_id,
                session.user_mood,
                session.entries,
            )
            append_changelog(
                f"Session {session.session_id} closed "
                f"({len(session.entries)} entries, mood={session.user_mood})"
            )
