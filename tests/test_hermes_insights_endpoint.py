from pathlib import Path

from fastapi.testclient import TestClient

from gateway.hermes_api import app, CLAWX_LOG

client = TestClient(app)


def test_clawx_insights_endpoint(tmp_path: Path, monkeypatch) -> None:
    log_file = tmp_path / "clawx_log.jsonl"
    log_file.write_text(
        '{"event":"pattern_detected","pattern":"funding_rate_spike"}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("gateway.hermes_api.CLAWX_LOG", log_file)

    response = client.get("/clawx/insights")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["event"] == "pattern_detected"
