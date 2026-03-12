#!/usr/bin/env python3
"""Run ClawX burn-in cycles against ATLAS using Obsidian context."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.investigation_engine.ollama_analyser import parse_analysis_response
from tools.load_cluster_env import get_ollama_timeout, get_ollama_url

VAULT = ROOT / "vault"
SIGNALS = VAULT / "runtime" / "signals.jsonl"
EVIDENCE = VAULT / "evidence" / "evidence.jsonl"
DEFAULT_OBSIDIAN = Path("~/Obsidian").expanduser()
DEFAULT_MODELS = ["mistral", "qwen2.5:3b", "gemma:2b"]
DEFAULT_DELAY = 30
DEFAULT_MAX_NOTES = 3
DEFAULT_MAX_NOTE_CHARS = 800
DEFAULT_MAX_CONTEXT_CHARS = 1800


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def run_agent(agent: str, args: Iterable[str] | None = None, runner=subprocess.run) -> int:
    command = ["python3", str(ROOT / "tools" / "invoke_agent.py"), agent, *(list(args or []))]
    result = runner(command, cwd=ROOT, check=False)
    return int(getattr(result, "returncode", 0))


def read_obsidian_context(
    obsidian_root: Path = DEFAULT_OBSIDIAN,
    max_notes: int = DEFAULT_MAX_NOTES,
    max_note_chars: int = DEFAULT_MAX_NOTE_CHARS,
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> str:
    notes: list[str] = []
    used_chars = 0
    if not obsidian_root.exists():
        return ""

    for note in sorted(obsidian_root.rglob("*.md")):
        try:
            text = note.read_text(encoding="utf-8")[:max_note_chars].strip()
        except OSError:
            continue
        if not text:
            continue
        rendered = f"# {note.name}\n{text}"
        remaining = max_context_chars - used_chars
        if remaining <= 0:
            break
        if len(rendered) > remaining:
            rendered = rendered[:remaining].rstrip()
        if not rendered:
            break
        notes.append(rendered)
        used_chars += len(rendered) + 2
        if len(notes) >= max_notes:
            break

    return "\n\n".join(notes)


def build_prompt(context: str) -> str:
    rendered_context = context or "No Obsidian notes were available."
    return f"""
You are ClawX burn-in training.

Analyse this cluster context and propose ONE operational improvement.
Respond with STRICT JSON only. Do not add markdown, prose, or code fences.

Context:
{rendered_context}

Return STRICT JSON:

{{
  "root_cause": "...",
  "severity": "low|medium|high|critical",
  "confidence": 0.0,
  "recommended_action": "..."
}}
"""


def extract_json_object(text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return None
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()

    start = stripped.find("{")
    if start == -1:
        return None

    depth = 0
    for index in range(start, len(stripped)):
        char = stripped[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return stripped[start : index + 1].strip()
    return None


def fallback_analysis() -> dict[str, Any]:
    return {
        "root_cause": "model_output_unstructured",
        "severity": "low",
        "confidence": 0.3,
        "recommended_action": "retry",
    }


def normalize_training_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    response = payload.get("response")
    candidate = extract_json_object(response) if isinstance(response, str) else None
    normalized_payload = dict(payload)
    if candidate:
        normalized_payload["response"] = candidate

    analysis = parse_analysis_response(normalized_payload)
    if analysis.get("severity") == "unknown" or not str(analysis.get("root_cause", "")).strip():
        return fallback_analysis()
    return analysis


def query_model(model: str, prompt: str, requester=requests.post) -> dict[str, Any]:
    response = requester(
        f"{get_ollama_url()}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=get_ollama_timeout(),
    )
    response.raise_for_status()
    payload = response.json()
    return {
        "analysis": normalize_training_analysis(payload),
        "model": model,
        "node": "atlas",
        "source": "atlas_ollama",
    }


def make_cycle_signal(model: str, timestamp: str) -> dict[str, Any]:
    signal_id = f"burnin-{model.replace(':', '-')}-{uuid.uuid4().hex[:12]}"
    return {
        "signal_id": signal_id,
        "type": "clawx_burnin_cycle",
        "severity": "low",
        "payload": {
            "model": model,
            "context_source": "obsidian_vault",
        },
        "timestamp": timestamp,
    }


def make_result_signal(
    signal_id: str,
    model: str,
    analysis: dict[str, Any],
    timestamp: str,
) -> dict[str, Any]:
    return {
        "signal_id": f"{signal_id}-result",
        "type": "clawx_training_result",
        "severity": str(analysis.get("severity", "unknown")),
        "payload": {
            "model": model,
            "evidence_signal_id": signal_id,
            "recommended_action": str(analysis.get("recommended_action", "")),
        },
        "timestamp": timestamp,
    }


def make_failure_signal(signal_id: str, model: str, error: str, timestamp: str) -> dict[str, Any]:
    return {
        "signal_id": f"{signal_id}-failure",
        "type": "clawx_training_failure",
        "severity": "medium",
        "payload": {
            "model": model,
            "evidence_signal_id": signal_id,
            "error": error,
        },
        "timestamp": timestamp,
    }


def make_evidence_record(
    signal_id: str,
    analysis: dict[str, Any],
    model: str,
    timestamp: str,
) -> dict[str, Any]:
    return {
        "type": "llm_analysis",
        "signal_id": signal_id,
        "root_cause": str(analysis.get("root_cause", "")),
        "severity": str(analysis.get("severity", "unknown")),
        "confidence": float(analysis.get("confidence", 0.0)),
        "recommended_action": str(analysis.get("recommended_action", "")),
        "agent": "clawx_burnin",
        "node": "atlas",
        "model": model,
        "timestamp": timestamp,
        "source": "atlas_ollama",
    }


def training_cycle(
    models: Iterable[str] = DEFAULT_MODELS,
    obsidian_root: Path = DEFAULT_OBSIDIAN,
    signal_path: Path = SIGNALS,
    evidence_path: Path = EVIDENCE,
    requester=requests.post,
) -> list[dict[str, Any]]:
    context = read_obsidian_context(obsidian_root=obsidian_root)
    results: list[dict[str, Any]] = []

    for model in models:
        timestamp = utc_now()
        signal = make_cycle_signal(model, timestamp)
        append_jsonl(signal_path, signal)

        try:
            outcome = query_model(model, build_prompt(context), requester=requester)
            evidence = make_evidence_record(signal["signal_id"], outcome["analysis"], outcome["model"], timestamp)
            append_jsonl(evidence_path, evidence)
            result_signal = make_result_signal(signal["signal_id"], outcome["model"], outcome["analysis"], timestamp)
            append_jsonl(signal_path, result_signal)
            results.append({"signal": signal, "evidence": evidence, "result_signal": result_signal})
        except Exception as exc:
            failure_signal = make_failure_signal(signal["signal_id"], model, str(exc), timestamp)
            append_jsonl(signal_path, failure_signal)
            results.append({"signal": signal, "failure_signal": failure_signal})

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ClawX burn-in training cycles")
    parser.add_argument("--once", action="store_true", help="Run a single burn-in cycle and exit")
    parser.add_argument("--delay", type=int, default=DEFAULT_DELAY, help="Seconds between cycles")
    parser.add_argument("--obsidian-root", type=Path, default=DEFAULT_OBSIDIAN, help="Path to the Obsidian vault root")
    parser.add_argument("--model", dest="models", action="append", help="Model to query on ATLAS; may be passed multiple times")
    parser.add_argument("--skip-doctor", action="store_true", help="Skip running cluster_doctor before each cycle")
    args = parser.parse_args()

    models = args.models or list(DEFAULT_MODELS)

    while True:
        if not args.skip_doctor:
            run_agent("cluster_doctor")

        training_cycle(models=models, obsidian_root=args.obsidian_root)
        if args.once:
            return 0
        time.sleep(max(args.delay, 1))


if __name__ == "__main__":
    raise SystemExit(main())
