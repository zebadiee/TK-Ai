import json
from pathlib import Path

from tools import clawx_burnin


class DummyResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self) -> dict:
        return self._payload


def test_read_obsidian_context_limits_notes_and_text(tmp_path: Path) -> None:
    vault = tmp_path / "Obsidian"
    vault.mkdir()
    (vault / "a.md").write_text("a" * 20, encoding="utf-8")
    (vault / "b.md").write_text("b" * 20, encoding="utf-8")
    (vault / "c.md").write_text("c" * 20, encoding="utf-8")

    context = clawx_burnin.read_obsidian_context(vault, max_notes=2, max_note_chars=5)

    assert "# a.md" in context
    assert "# b.md" in context
    assert "# c.md" not in context
    assert "aaaaa" in context
    assert "bbbbb" in context


def test_training_cycle_writes_evidence_and_result_signal(tmp_path: Path) -> None:
    obsidian = tmp_path / "Obsidian"
    obsidian.mkdir()
    (obsidian / "note.md").write_text("cluster note", encoding="utf-8")
    signals = tmp_path / "signals.jsonl"
    evidence = tmp_path / "evidence.jsonl"

    def requester(url, json, timeout):
        assert url.endswith("/api/generate")
        assert json["model"] == "mistral"
        return DummyResponse(
            {
                "response": {
                    "root_cause": "Queue saturation",
                    "severity": "medium",
                    "confidence": 0.8,
                    "recommended_action": "Inspect concurrent jobs",
                }
            }
        )

    results = clawx_burnin.training_cycle(
        models=["mistral"],
        obsidian_root=obsidian,
        signal_path=signals,
        evidence_path=evidence,
        requester=requester,
    )

    assert len(results) == 1
    evidence_rows = [json.loads(line) for line in evidence.read_text(encoding="utf-8").splitlines()]
    signal_rows = [json.loads(line) for line in signals.read_text(encoding="utf-8").splitlines()]

    assert evidence_rows == [
        {
            "agent": "clawx_burnin",
            "confidence": 0.8,
            "model": "mistral",
            "node": "atlas",
            "recommended_action": "Inspect concurrent jobs",
            "root_cause": "Queue saturation",
            "severity": "medium",
            "signal_id": signal_rows[0]["signal_id"],
            "source": "atlas_ollama",
            "timestamp": evidence_rows[0]["timestamp"],
            "type": "llm_analysis",
        }
    ]
    assert signal_rows[0]["type"] == "clawx_burnin_cycle"
    assert signal_rows[1]["type"] == "clawx_training_result"
    assert signal_rows[1]["payload"]["evidence_signal_id"] == signal_rows[0]["signal_id"]


def test_training_cycle_writes_failure_signal_on_error(tmp_path: Path) -> None:
    obsidian = tmp_path / "Obsidian"
    obsidian.mkdir()
    (obsidian / "note.md").write_text("cluster note", encoding="utf-8")
    signals = tmp_path / "signals.jsonl"
    evidence = tmp_path / "evidence.jsonl"

    def requester(url, json, timeout):
        raise RuntimeError("atlas unavailable")

    results = clawx_burnin.training_cycle(
        models=["mistral"],
        obsidian_root=obsidian,
        signal_path=signals,
        evidence_path=evidence,
        requester=requester,
    )

    assert len(results) == 1
    assert not evidence.exists()
    signal_rows = [json.loads(line) for line in signals.read_text(encoding="utf-8").splitlines()]
    assert signal_rows[0]["type"] == "clawx_burnin_cycle"
    assert signal_rows[1]["type"] == "clawx_training_failure"
    assert signal_rows[1]["payload"]["error"] == "atlas unavailable"


def test_query_model_extracts_fenced_json_response(monkeypatch) -> None:
    monkeypatch.setattr(clawx_burnin, "get_ollama_url", lambda: "http://atlas:11434")
    monkeypatch.setattr(clawx_burnin, "get_ollama_timeout", lambda: 30)

    def requester(url, json, timeout):
        return DummyResponse(
            {
                "response": """Here is the result:

```json
{
  "root_cause": "scheduler warmup",
  "severity": "low",
  "confidence": 0.6,
  "recommended_action": "observe"
}
```"""
            }
        )

    result = clawx_burnin.query_model("mistral", "prompt", requester=requester)

    assert result["analysis"] == {
        "root_cause": "scheduler warmup",
        "severity": "low",
        "confidence": 0.6,
        "recommended_action": "observe",
    }


def test_query_model_falls_back_when_response_stays_unstructured(monkeypatch) -> None:
    monkeypatch.setattr(clawx_burnin, "get_ollama_url", lambda: "http://atlas:11434")
    monkeypatch.setattr(clawx_burnin, "get_ollama_timeout", lambda: 30)

    def requester(url, json, timeout):
        return DummyResponse({"response": "This looks healthy overall. Retry later if needed."})

    result = clawx_burnin.query_model("mistral", "prompt", requester=requester)

    assert result["analysis"] == {
        "root_cause": "model_output_unstructured",
        "severity": "low",
        "confidence": 0.3,
        "recommended_action": "retry",
    }
