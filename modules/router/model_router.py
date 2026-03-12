"""Route model inference requests across available Ollama endpoints."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import requests

DEFAULT_ROUTE_CHAIN = [
    "http://192.168.1.17:11434",
    "http://hermes:11434",
    "http://localhost:11434",
]
MODEL_OVERRIDES = {
    "http://hermes:11434": "qwen2.5:7b-instruct-q4_0",
    "http://localhost:11434": "gemma:2b",
}


def get_route_chain() -> list[str]:
    override = os.environ.get("TKAI_ROUTER_CHAIN", "").strip()
    if not override:
        return list(DEFAULT_ROUTE_CHAIN)
    return [endpoint.strip() for endpoint in override.split(",") if endpoint.strip()]


ROUTE_CHAIN = get_route_chain()


def endpoint_to_node(endpoint: str) -> str:
    hostname = urlparse(endpoint).hostname
    return hostname or endpoint


def payload_for_endpoint(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    resolved = dict(payload)
    resolved["model"] = MODEL_OVERRIDES.get(endpoint, str(payload.get("model", "")))
    return resolved


def call_model_router(payload: dict[str, Any]) -> tuple[dict[str, Any], str, str, str]:
    for endpoint in get_route_chain():
        endpoint_payload = payload_for_endpoint(endpoint, payload)
        try:
            response = requests.post(
                f"{endpoint}/api/generate",
                json=endpoint_payload,
                timeout=30,
            )
        except requests.RequestException:
            continue

        if response.status_code != 200:
            continue

        data = response.json()
        if isinstance(data, dict):
            return data, endpoint, endpoint_to_node(endpoint), str(endpoint_payload["model"])

    raise RuntimeError("No inference node available")
