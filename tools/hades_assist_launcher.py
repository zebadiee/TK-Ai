#!/usr/bin/env python3
"""Governed HADES entrypoint for skill registration, promotion, and Obsidian sync."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hades.hades_assist_model_policy import (
    STATE_PATH as MODEL_POLICY_STATE_PATH,
    choose_route,
    load_policy_state,
    render_policy_summary,
    write_policy_state,
)
from memory.obsidian_bridge.knowledge_writer import sync_tkai_knowledge
from memory.obsidian_bridge.skill_catalog_writer import sync_skill_catalog
from tools.cluster_registry import load_cluster_nodes
from tools.tool_creation_checker import check_skill, parse_frontmatter

DEFAULT_SKILLS_ROOT = Path.home() / ".codex" / "skills"
DEFAULT_OBSIDIAN_ROOT = Path.home() / "Obsidian" / "TK-Ai"
SNAPSHOT_ROOT = ROOT / "snapshots"
STATE_PATH = ROOT / "vault" / "runtime" / "hades_assist_skill_state.json"
EVENT_LOG_PATH = ROOT / "vault" / "runtime" / "hades_assist_events.jsonl"
REGISTRY_PATH = ROOT / "vault" / "runtime" / "hades_assist_skill_registry.json"
NODE_REGISTRY_TEMPLATE = ROOT / "vault" / "runtime" / "{node}_skill_registry.json"
MODEL_POLICY_PATH = ROOT / "vault" / "runtime" / "hades_assist_model_policy.json"
MODEL_SELECTION_PATH = ROOT / "vault" / "runtime" / "hades_assist_model_selection.json"
ALLOWED_STATUSES = {"experimental", "beta", "production"}


def current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_execution_paths(skill_text: str) -> list[str]:
    commands: list[str] = []
    for line in skill_text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("python ", "python3 ", "bash ", "./")):
            commands.append(stripped)
    return list(dict.fromkeys(commands))


def infer_generator(skill_dir: Path) -> str:
    if (skill_dir / "agents" / "openai.yaml").exists():
        return "skill-creator"
    return "manual"


def skill_last_updated(skill_dir: Path) -> str:
    latest = 0.0
    for path in skill_dir.rglob("*"):
        try:
            latest = max(latest, path.stat().st_mtime)
        except FileNotFoundError:
            continue
    if latest == 0.0:
        latest = skill_dir.stat().st_mtime
    return datetime.fromtimestamp(latest, tz=timezone.utc).isoformat()


def discover_governed_skills(skills_root: Path) -> list[dict[str, Any]]:
    skills: list[dict[str, Any]] = []
    if not skills_root.exists():
        return skills

    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        report = check_skill(skill_dir)
        if not report["valid"]:
            continue
        skill_path = skill_dir / "SKILL.md"
        text = skill_path.read_text(encoding="utf-8")
        metadata = parse_frontmatter(text)
        skills.append(
            {
                "slug": skill_dir.name,
                "name": metadata.get("name", skill_dir.name),
                "source_path": str(skill_dir),
                "spec_path": str(skill_path),
                "execution_paths": extract_execution_paths(text),
                "generator": infer_generator(skill_dir),
                "checker": "tool_creation_checker",
                "checker_result": "pass",
                "last_updated": skill_last_updated(skill_dir),
            }
        )
    return skills


def load_state(path: Path = STATE_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"skills": {}, "events": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {"skills": {}, "events": []}


def parse_promotions(values: list[str]) -> dict[str, str]:
    promotions: dict[str, str] = {}
    for value in values:
        name, sep, status = value.partition("=")
        if not sep or not name.strip() or status.strip() not in ALLOWED_STATUSES:
            raise ValueError(f"invalid promotion: {value!r}")
        promotions[name.strip()] = status.strip()
    return promotions


def append_event(events: list[dict[str, Any]], *, skill: str, summary: str, timestamp: str) -> None:
    events.append({"timestamp": timestamp, "skill": skill, "summary": summary})


def reconcile_skill_state(
    discovered: list[dict[str, Any]],
    existing_state: dict[str, Any],
    *,
    promotions: dict[str, str] | None = None,
    snapshot_name: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    timestamp = current_timestamp()
    promotions = promotions or {}
    prior_skills = existing_state.get("skills", {}) if isinstance(existing_state, dict) else {}
    prior_events = existing_state.get("events", []) if isinstance(existing_state, dict) else []
    events = list(prior_events) if isinstance(prior_events, list) else []
    state_skills: dict[str, Any] = {}
    reconciled: list[dict[str, Any]] = []

    nodes = load_cluster_nodes()
    visibility = {
        "hades": "hades" in nodes,
        "hermes": "hermes" in nodes,
        "atlas": "atlas" in nodes,
    }

    for skill in discovered:
        slug = skill["slug"]
        prior = prior_skills.get(slug, {}) if isinstance(prior_skills, dict) else {}
        history = list(prior.get("promotion_history", [])) if isinstance(prior, dict) else []
        status = str(prior.get("status", "experimental"))

        if slug not in prior_skills:
            summary = "discovered and catalogued as experimental"
            if snapshot_name:
                summary += f" from snapshot {snapshot_name}"
            history.append({"timestamp": timestamp, "summary": summary})
            append_event(events, skill=slug, summary=summary, timestamp=timestamp)

        if skill["last_updated"] != prior.get("source_mtime") and slug in prior_skills:
            summary = "skill specification updated"
            history.append({"timestamp": timestamp, "summary": summary})
            append_event(events, skill=slug, summary=summary, timestamp=timestamp)

        if slug in promotions and promotions[slug] != status:
            target = promotions[slug]
            summary = f"promoted from {status} to {target}"
            status = target
            history.append({"timestamp": timestamp, "summary": summary})
            append_event(events, skill=slug, summary=summary, timestamp=timestamp)

        skill_payload = {
            **skill,
            "status": status,
            "cluster_visibility": visibility,
            "promotion_history": history,
            "snapshot": snapshot_name,
        }
        reconciled.append(skill_payload)
        state_skills[slug] = {
            "status": status,
            "source_mtime": skill["last_updated"],
            "promotion_history": history,
        }

    state = {"skills": state_skills, "events": events}
    return reconciled, events, state


def write_runtime_artifacts(skills: list[dict[str, Any]], events: list[dict[str, Any]], *, snapshot_name: str | None = None) -> list[Path]:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": current_timestamp(),
        "snapshot": snapshot_name,
        "skills": skills,
    }
    REGISTRY_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    written = [REGISTRY_PATH]
    for node in ("atlas", "hermes"):
        node_payload = {
            "node": node,
            "generated_at": payload["generated_at"],
            "snapshot": snapshot_name,
            "skills": skills,
        }
        node_path = Path(str(NODE_REGISTRY_TEMPLATE).format(node=node))
        node_path.write_text(json.dumps(node_payload, indent=2, sort_keys=True), encoding="utf-8")
        written.append(node_path)

    EVENT_LOG_PATH.write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
        encoding="utf-8",
    )
    written.append(EVENT_LOG_PATH)
    return written


def write_state(state: dict[str, Any], path: Path = STATE_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    return path


def write_model_artifacts(
    *,
    intent: str | None,
    route_payload: dict[str, Any] | None,
    state: dict[str, Any],
    path: Path = MODEL_POLICY_PATH,
    selection_path: Path = MODEL_SELECTION_PATH,
) -> list[Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    policy = {
        "generated_at": current_timestamp(),
        "policy": render_policy_summary(state),
    }
    path.write_text(json.dumps(policy, indent=2, sort_keys=True), encoding="utf-8")
    written = [path]

    if intent and route_payload:
        selection = {
            "generated_at": current_timestamp(),
            "intent": intent,
            "route": route_payload,
        }
        selection_path.write_text(json.dumps(selection, indent=2, sort_keys=True), encoding="utf-8")
        written.append(selection_path)
    return written


def resolve_skills_root(snapshot_label: str | None, skills_root: Path) -> tuple[Path, str | None]:
    if not snapshot_label:
        return skills_root, None
    snapshot = resolve_snapshot_dir(snapshot_label)
    return snapshot / "skills", snapshot.name


def resolve_snapshot_dir(identifier: str, snapshot_root: Path = SNAPSHOT_ROOT) -> Path:
    snapshots = sorted(
        (path for path in snapshot_root.iterdir() if path.is_dir()),
        key=lambda path: path.name,
        reverse=True,
    )
    if not snapshots:
        raise FileNotFoundError(f"no snapshots found under {snapshot_root}")
    exact = [path for path in snapshots if path.name == identifier]
    if exact:
        return exact[0]
    suffix = [path for path in snapshots if path.name.endswith(f"--{identifier}")]
    if len(suffix) == 1:
        return suffix[0]
    if len(suffix) > 1:
        raise ValueError(f"snapshot label is ambiguous: {identifier}")
    raise FileNotFoundError(f"snapshot not found: {identifier}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Launch HADES Assist governance sync")
    parser.add_argument("--skills-root", type=Path, default=DEFAULT_SKILLS_ROOT, help="Path to the installed skills root")
    parser.add_argument("--vault-root", type=Path, default=DEFAULT_OBSIDIAN_ROOT, help="Obsidian output root")
    parser.add_argument("--snapshot", help="Optional snapshot label or name")
    parser.add_argument("--intent", help="Optional operator request used for model policy selection")
    parser.add_argument("--skill", help="Optional governed skill name for routing classification")
    parser.add_argument("--user-mood", default="focused", help="Operator mood for social-mode-aware routing")
    parser.add_argument("--high-stakes", action="store_true", help="Force paid-capable routing for high-stakes requests")
    parser.add_argument("--production", action="store_true", help="Force paid-capable routing for production requests")
    parser.add_argument("--long-running", action="store_true", help="Mark the request as long-running")
    parser.add_argument("--high-volume", action="store_true", help="Mark the request as high-volume and cost-sensitive")
    parser.add_argument(
        "--promote",
        action="append",
        default=[],
        help="Promotion mapping in skill=status form where status is experimental, beta, or production",
    )
    args = parser.parse_args(argv)

    promotions = parse_promotions(args.promote)
    skills_root, snapshot_name = resolve_skills_root(args.snapshot, args.skills_root.expanduser())
    skills = discover_governed_skills(skills_root)
    existing_state = load_state()
    reconciled, events, state = reconcile_skill_state(
        skills,
        existing_state,
        promotions=promotions,
        snapshot_name=snapshot_name,
    )

    write_state(state)
    write_runtime_artifacts(reconciled, events, snapshot_name=snapshot_name)
    model_state = load_policy_state(MODEL_POLICY_STATE_PATH)
    write_policy_state(model_state, MODEL_POLICY_STATE_PATH)
    route = None
    if args.intent:
        route = choose_route(
            args.intent,
            skill_name=args.skill,
            user_mood=args.user_mood,
            high_stakes=args.high_stakes,
            production=args.production,
            long_running=args.long_running,
            high_volume=args.high_volume,
            state=model_state,
        )
    write_model_artifacts(
        intent=args.intent,
        route_payload=route.to_dict() if route else None,
        state=model_state,
    )
    sync_tkai_knowledge(ROOT, args.vault_root.expanduser())
    sync_skill_catalog(reconciled, events, args.vault_root.expanduser())

    print(f"HADES Assist synced {len(reconciled)} governed skills")
    if route:
        print(json.dumps({"intent": args.intent, "route": route.to_dict()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
