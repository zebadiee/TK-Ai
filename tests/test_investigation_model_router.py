from __future__ import annotations

import os

import requests

from modules.router.model_router import call_model_router, endpoint_to_node, get_route_chain, payload_for_endpoint


class StubResponse:
    def __init__(self, status_code: int, payload: dict[str, object]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload


def test_call_model_router_uses_first_successful_endpoint(monkeypatch) -> None:
    calls: list[str] = []

    def fake_post(url: str, json: dict[str, object], timeout: int) -> StubResponse:
        calls.append(url)
        if url.startswith("http://192.168.1.17:11434"):
            raise requests.ConnectionError("atlas down")
        if url.startswith("http://hermes:11434"):
            return StubResponse(200, {"response": "{\"severity\":\"low\"}"})
        return StubResponse(500, {})

    monkeypatch.setattr("modules.router.model_router.requests.post", fake_post)

    data, endpoint, node, model = call_model_router({"model": "mistral", "prompt": "hello", "stream": False})

    assert endpoint == "http://hermes:11434"
    assert node == "hermes"
    assert model == "qwen2.5:7b-instruct-q4_0"
    assert data == {"response": "{\"severity\":\"low\"}"}
    assert calls[:2] == [
        "http://192.168.1.17:11434/api/generate",
        "http://hermes:11434/api/generate",
    ]


def test_endpoint_to_node_extracts_hostname() -> None:
    assert endpoint_to_node("http://192.168.1.17:11434") == "192.168.1.17"
    assert endpoint_to_node("http://hermes:11434") == "hermes"


def test_get_route_chain_uses_env_override(monkeypatch) -> None:
    monkeypatch.setenv("TKAI_ROUTER_CHAIN", "http://127.0.0.1:1, http://localhost:11434")

    assert get_route_chain() == ["http://127.0.0.1:1", "http://localhost:11434"]


def test_payload_for_endpoint_applies_model_override() -> None:
    payload = payload_for_endpoint("http://localhost:11434", {"model": "mistral", "prompt": "hello", "stream": False})

    assert payload["model"] == "gemma:2b"
    assert payload["prompt"] == "hello"
