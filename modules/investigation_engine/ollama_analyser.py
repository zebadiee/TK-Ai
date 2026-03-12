"""Analyse signals by forwarding prompts to the cluster Ollama node."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from modules.router.model_router import call_model_router
from tools.load_cluster_env import get_default_model

MAX_RETRIES = 3
ALLOWED_SEVERITIES = {"low", "medium", "high", "critical", "unknown"}


def _build_prompt(signal: dict[str, Any]) -> str:
    return f"""
You are an infrastructure analysis AI.

Signal:
type: {signal.get("type")}
payload: {signal.get("payload")}

Return JSON:

{{
 "root_cause": "string",
 "severity": "low|medium|high|critical",
 "confidence": 0.0,
 "recommended_action": "string"
}}
"""


def _normalize_analysis(data: dict[str, Any]) -> dict[str, Any]:
    root_cause = data.get("root_cause")
    if not isinstance(root_cause, str) or not root_cause.strip():
        likely_causes = data.get("likely_causes")
        if isinstance(likely_causes, list) and likely_causes and isinstance(likely_causes[0], str):
            root_cause = likely_causes[0]
        elif isinstance(data.get("raw_response"), str):
            root_cause = data["raw_response"]
        else:
            root_cause = ""

    recommended_action = data.get("recommended_action")
    if not isinstance(recommended_action, str) or not recommended_action.strip():
        recommended_actions = data.get("recommended_actions")
        if isinstance(recommended_actions, list) and recommended_actions and isinstance(recommended_actions[0], str):
            recommended_action = recommended_actions[0]
        else:
            recommended_action = ""

    severity = str(data.get("severity", "unknown")).strip().lower()
    if severity not in ALLOWED_SEVERITIES:
        severity = "unknown"

    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(confidence, 1.0))

    return {
        "root_cause": root_cause,
        "severity": severity,
        "confidence": confidence,
        "recommended_action": recommended_action,
    }


def _extract_json_object(text: str) -> str | None:
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


def parse_analysis_response(data: dict[str, Any]) -> dict[str, Any]:
    response = data.get("response")
    if isinstance(response, dict):
        return _normalize_analysis(response)
    if isinstance(response, str):
        candidate = _extract_json_object(response)
        try:
            parsed = json.loads(candidate or response)
        except json.JSONDecodeError:
            return _normalize_analysis({"raw_response": response})
        if isinstance(parsed, dict):
            return _normalize_analysis(parsed)
    return _normalize_analysis({})


def call_model(prompt: str) -> tuple[dict[str, Any], str, str, str]:
    model = get_default_model()
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    for attempt in range(MAX_RETRIES):
        try:
            data, endpoint, node, model_used = call_model_router(payload)
            return parse_analysis_response(data), endpoint, node, model_used
        except Exception:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(2**attempt)

    raise RuntimeError("Unreachable retry state")


def analyse_signal(signal: dict[str, Any]) -> dict[str, Any]:
    analysis, endpoint, node, model = call_model(_build_prompt(signal))
    return {
        "analysis": analysis,
        "endpoint": endpoint,
        "node": node,
        "model": model,
    }
