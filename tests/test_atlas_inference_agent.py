import json

from tools import atlas_inference_agent


class StubResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self.payload


def test_run_posts_prompt_to_local_ollama(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(url: str, json: dict[str, object], timeout: int) -> StubResponse:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return StubResponse({"response": "ok"})

    monkeypatch.setattr("tools.atlas_inference_agent.requests.post", fake_post)

    result = atlas_inference_agent.run("test prompt")

    assert result == {"response": "ok"}
    assert captured == {
        "url": "http://localhost:11434/api/generate",
        "json": {
            "model": "mistral",
            "prompt": "test prompt",
            "stream": False,
        },
        "timeout": 30,
    }


def test_main_defaults_to_health_check(monkeypatch, capsys) -> None:
    monkeypatch.setattr(atlas_inference_agent, "run", lambda prompt, **kwargs: {"response": prompt})
    monkeypatch.setattr(atlas_inference_agent, "MODEL", "mistral")
    monkeypatch.setattr(atlas_inference_agent, "URL", "http://localhost:11434/api/generate")
    monkeypatch.setattr("tools.atlas_inference_agent.argparse.ArgumentParser.parse_args", lambda self: type("Args", (), {"prompt": []})())

    result = atlas_inference_agent.main()
    output = capsys.readouterr().out

    assert result == 0
    assert json.loads(output)["response"] == "health check"
