"""Ollama-backed workflow proposal source for constrained graph planning."""

from __future__ import annotations

import json
from typing import Any, Callable

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MODEL = "qwen2.5"


def build_ollama_proposer(
    model: str = DEFAULT_MODEL,
    url: str = OLLAMA_URL,
    timeout: float = DEFAULT_TIMEOUT,
    capabilities: list[str] | None = None,
) -> Callable[[str, dict[str, Any]], dict[str, Any] | list[str] | str | None]:
    allowed_capabilities = [cap.strip() for cap in (capabilities or []) if cap and cap.strip()]

    def proposer(intent: str, payload: dict[str, Any]) -> dict[str, Any] | list[str] | str | None:
        prompt = _build_prompt(intent, payload, allowed_capabilities)
        try:
            response = requests.post(
                url,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return None

        if not isinstance(data, dict):
            return None
        raw_response = data.get("response", "")
        if not isinstance(raw_response, str) or not raw_response.strip():
            return None

        return _parse_response(raw_response)

    return proposer


def _build_prompt(intent: str, payload: dict[str, Any], capabilities: list[str]) -> str:
    allowed = "\n".join(f"- {cap}" for cap in capabilities) if capabilities else "- analyse\n- notify"
    payload_context = json.dumps(payload, sort_keys=True) if payload else "{}"
    return (
        "You are designing safe workflow steps for an AI orchestration kernel.\n"
        "Return valid JSON only.\n"
        "Use this schema: {\"graph_id\": \"short-name\", \"steps\": [\"capability\", ...]}.\n"
        "Only use capabilities from this allowlist:\n"
        f"{allowed}\n"
        "Do not invent actions, providers, or extra fields.\n"
        f"Intent: {intent}\n"
        f"Payload: {payload_context}\n"
    )


def _parse_response(raw_response: str) -> dict[str, Any] | list[str] | str | None:
    stripped = raw_response.strip()
    if not stripped:
        return None

    if stripped.startswith("{") or stripped.startswith("["):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return None
    return stripped
