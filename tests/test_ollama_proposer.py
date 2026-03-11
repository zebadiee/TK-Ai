import requests

from atlas.proposers.ollama_proposer import build_ollama_proposer


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_ollama_proposer_parses_json_response(monkeypatch):
    def fake_post(url, json, timeout):
        return _FakeResponse(
            {"response": '{"graph_id":"btc-plan","steps":["monitor","analyse","notify"]}'}
        )

    monkeypatch.setattr("atlas.proposers.ollama_proposer.requests.post", fake_post)
    proposer = build_ollama_proposer(
        model="qwen2.5",
        capabilities=["monitor", "analyse", "notify"],
    )

    proposal = proposer("monitor btc funding", {"trace_id": "123"})

    assert proposal["graph_id"] == "btc-plan"
    assert proposal["steps"] == ["monitor", "analyse", "notify"]


def test_ollama_proposer_returns_none_on_request_error(monkeypatch):
    def fake_post(url, json, timeout):
        raise requests.RequestException("offline")

    monkeypatch.setattr("atlas.proposers.ollama_proposer.requests.post", fake_post)
    proposer = build_ollama_proposer(
        model="qwen2.5",
        capabilities=["monitor", "analyse", "notify"],
    )

    proposal = proposer("monitor btc funding", {"trace_id": "123"})

    assert proposal is None
