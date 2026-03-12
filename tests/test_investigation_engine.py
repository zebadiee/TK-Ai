import json
import json as json_lib
from pathlib import Path

from modules.investigation_engine import investigation_loop
from modules.investigation_engine.ollama_analyser import analyse_signal


class StubResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self.payload


def test_read_signals_returns_last_five_records(tmp_path: Path) -> None:
    signal_file = tmp_path / "signals.jsonl"
    lines = [
        json.dumps({"signal_id": index, "type": "test", "payload": {"n": index}})
        for index in range(7)
    ]
    signal_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    records = investigation_loop.read_signals(path=signal_file)

    assert [record["signal_id"] for record in records] == [2, 3, 4, 5, 6]


def test_write_evidence_appends_jsonl(tmp_path: Path) -> None:
    evidence_file = tmp_path / "evidence" / "evidence.jsonl"

    investigation_loop.write_evidence(
        {"type": "llm_analysis", "signal_id": "abc"},
        path=evidence_file,
    )

    lines = evidence_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["signal_id"] == "abc"


def test_load_processed_returns_empty_set_when_file_missing(tmp_path: Path) -> None:
    assert investigation_loop.load_processed(tmp_path / "processed_signals.json") == set()


def test_prioritize_signals_orders_high_before_low() -> None:
    ordered = investigation_loop.prioritize_signals(
        [
            {"signal_id": "sig-low", "severity": "low"},
            {"signal_id": "sig-high", "severity": "high"},
            {"signal_id": "sig-medium", "severity": "medium"},
        ]
    )

    assert [signal["signal_id"] for signal in ordered] == ["sig-high", "sig-medium", "sig-low"]


def test_resolve_source_marks_fallback_nodes(monkeypatch) -> None:
    monkeypatch.setattr(investigation_loop, "get_ollama_url", lambda: "http://192.168.1.17:11434")

    assert investigation_loop.resolve_node("atlas", "http://192.168.1.17:11434") == "atlas"
    assert investigation_loop.resolve_node("192.168.1.17", "http://192.168.1.17:11434") == "atlas"
    assert investigation_loop.resolve_source("atlas", "http://192.168.1.17:11434") == "atlas_ollama"
    assert investigation_loop.resolve_source("hermes", "http://hermes:11434") == "router"


def test_run_investigation_uses_ollama_analysis_once_per_signal(monkeypatch, tmp_path: Path) -> None:
    signal_file = tmp_path / "signals.jsonl"
    evidence_file = tmp_path / "evidence.jsonl"
    processed_file = tmp_path / "processed_signals.json"
    signal_file.write_text(
        json.dumps(
            {
                "signal_id": "sig-1",
                "type": "funding_rate_anomaly",
                "payload": {"rate": 0.2},
                "severity": "high",
                "timestamp": 123,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        investigation_loop,
        "analyse_signal",
        lambda signal: {
            "analysis": {
                "root_cause": f"root cause for {signal['signal_id']}",
                "severity": "critical",
                "confidence": 0.83,
                "recommended_action": "inspect concurrent inference jobs",
            },
            "model": "mistral",
            "node": "atlas",
            "endpoint": "http://192.168.1.17:11434",
        },
    )
    monkeypatch.setattr(investigation_loop, "get_ollama_url", lambda: "http://192.168.1.17:11434")
    monkeypatch.setattr(investigation_loop, "current_timestamp", lambda: "2026-03-11T16:30:12Z")

    investigation_loop.run_investigation(
        signal_path=signal_file,
        evidence_path=evidence_file,
        processed_path=processed_file,
    )
    investigation_loop.run_investigation(
        signal_path=signal_file,
        evidence_path=evidence_file,
        processed_path=processed_file,
    )

    records = [json.loads(line) for line in evidence_file.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["type"] == "llm_analysis"
    assert records[0]["signal_id"] == "sig-1"
    assert records[0]["root_cause"] == "root cause for sig-1"
    assert records[0]["severity"] == "critical"
    assert records[0]["confidence"] == 0.83
    assert records[0]["recommended_action"] == "inspect concurrent inference jobs"
    assert records[0]["agent"] == "investigation_agent"
    assert records[0]["model"] == "mistral"
    assert records[0]["node"] == "atlas"
    assert records[0]["timestamp"] == "2026-03-11T16:30:12Z"
    assert records[0]["source"] == "atlas_ollama"
    assert json.loads(processed_file.read_text(encoding="utf-8")) == ["sig-1"]


def test_run_investigation_saves_processed_when_later_signal_fails(monkeypatch, tmp_path: Path) -> None:
    signal_file = tmp_path / "signals.jsonl"
    evidence_file = tmp_path / "evidence.jsonl"
    processed_file = tmp_path / "processed_signals.json"
    signal_file.write_text(
        "\n".join(
            [
                json.dumps({"signal_id": "sig-1", "type": "funding_rate_anomaly", "payload": {"rate": 0.2}}),
                json.dumps({"signal_id": "sig-2", "type": "funding_rate_anomaly", "payload": {"rate": 0.4}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    def fake_analyse(signal: dict[str, object]) -> dict[str, object]:
        if signal["signal_id"] == "sig-2":
            raise TimeoutError("ollama read timed out")
        return {
            "analysis": {
                "root_cause": "market volatility",
                "severity": "medium",
                "confidence": 0.7,
                "recommended_action": "monitor market",
            },
            "model": "mistral",
            "node": "atlas",
            "endpoint": "http://192.168.1.17:11434",
        }

    monkeypatch.setattr(investigation_loop, "analyse_signal", fake_analyse)
    monkeypatch.setattr(investigation_loop, "get_ollama_url", lambda: "http://192.168.1.17:11434")
    monkeypatch.setattr(investigation_loop, "current_timestamp", lambda: "2026-03-11T16:30:12Z")

    investigation_loop.run_investigation(
        signal_path=signal_file,
        evidence_path=evidence_file,
        processed_path=processed_file,
    )

    records = [json.loads(line) for line in evidence_file.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["signal_id"] == "sig-1"
    assert json.loads(processed_file.read_text(encoding="utf-8")) == ["sig-1"]


def test_analyse_signal_calls_cluster_ollama(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_router(payload: dict[str, object]) -> tuple[dict[str, object], str, str, str]:
        captured["payload"] = payload
        return (
            {
                "response": json_lib.dumps(
                    {
                        "root_cause": "network congestion",
                        "severity": "low",
                        "confidence": 0.4,
                        "recommended_action": "observe",
                    }
                )
            },
            "http://192.168.1.17:11434",
            "atlas",
            "mistral",
        )

    monkeypatch.setattr("modules.investigation_engine.ollama_analyser.get_default_model", lambda: "mistral")
    monkeypatch.setattr("modules.investigation_engine.ollama_analyser.call_model_router", fake_router)

    result = analyse_signal({"type": "volatility_spike", "payload": {"symbol": "BTC"}})

    assert result == {
        "analysis": {
            "root_cause": "network congestion",
            "severity": "low",
            "confidence": 0.4,
            "recommended_action": "observe",
        },
        "model": "mistral",
        "node": "atlas",
        "endpoint": "http://192.168.1.17:11434",
    }
    assert captured["payload"] == {
        "model": "mistral",
        "prompt": """
You are an infrastructure analysis AI.

Signal:
type: volatility_spike
payload: {'symbol': 'BTC'}

Return JSON:

{
 "root_cause": "string",
 "severity": "low|medium|high|critical",
 "confidence": 0.0,
 "recommended_action": "string"
}
""",
        "stream": False,
    }


def test_analyse_signal_normalizes_legacy_response_shape(monkeypatch) -> None:
    def fake_router(payload: dict[str, object]) -> tuple[dict[str, object], str, str, str]:
        return (
            {
                "response": json_lib.dumps(
                    {
                        "severity": "medium",
                        "likely_causes": ["gpu queue saturation"],
                        "recommended_actions": ["inspect concurrent model jobs"],
                    }
                )
            },
            "http://192.168.1.17:11434",
            "atlas",
            "mistral",
        )

    monkeypatch.setattr("modules.investigation_engine.ollama_analyser.get_default_model", lambda: "mistral")
    monkeypatch.setattr("modules.investigation_engine.ollama_analyser.call_model_router", fake_router)

    result = analyse_signal({"type": "latency_spike", "payload": {"node": "atlas"}})

    assert result["analysis"] == {
        "root_cause": "gpu queue saturation",
        "severity": "medium",
        "confidence": 0.0,
        "recommended_action": "inspect concurrent model jobs",
    }


def test_analyse_signal_parses_fenced_json_response(monkeypatch) -> None:
    def fake_router(payload: dict[str, object]) -> tuple[dict[str, object], str, str, str]:
        return (
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
            },
            "http://192.168.1.17:11434",
            "atlas",
            "mistral",
        )

    monkeypatch.setattr("modules.investigation_engine.ollama_analyser.get_default_model", lambda: "mistral")
    monkeypatch.setattr("modules.investigation_engine.ollama_analyser.call_model_router", fake_router)

    result = analyse_signal({"type": "latency_spike", "payload": {"node": "atlas"}})

    assert result["analysis"] == {
        "root_cause": "scheduler warmup",
        "severity": "low",
        "confidence": 0.6,
        "recommended_action": "observe",
    }


def test_analyse_signal_retries_before_raising(monkeypatch) -> None:
    calls: list[int] = []
    sleeps: list[int] = []

    def fake_router(payload: dict[str, object]) -> tuple[dict[str, object], str, str]:
        calls.append(1)
        raise RuntimeError("router unavailable")

    monkeypatch.setattr("modules.investigation_engine.ollama_analyser.get_default_model", lambda: "mistral")
    monkeypatch.setattr("modules.investigation_engine.ollama_analyser.call_model_router", fake_router)
    monkeypatch.setattr("modules.investigation_engine.ollama_analyser.time.sleep", lambda seconds: sleeps.append(seconds))

    try:
        analyse_signal({"type": "volatility_spike", "payload": {"symbol": "BTC"}})
    except RuntimeError as exc:
        assert str(exc) == "router unavailable"
    else:
        raise AssertionError("analyse_signal should raise after exhausting retries")

    assert len(calls) == 3
    assert sleeps == [1, 2]
