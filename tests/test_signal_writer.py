import json
from pathlib import Path

from modules.clawx_engine.signal_writer import emit_signal


def test_signal_writer_appends_jsonl(tmp_path: Path) -> None:
    signal_file = tmp_path / "signals.jsonl"

    emit_signal(
        "funding_rate_anomaly",
        {"exchange": "binance", "rate": 0.23},
        path=signal_file,
        source="clawx",
    )

    assert signal_file.exists()
    lines = signal_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    record = json.loads(lines[0])
    assert record["type"] == "funding_rate_anomaly"
    assert record["payload"]["exchange"] == "binance"
