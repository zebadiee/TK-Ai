import json
from pathlib import Path

from modules.clawx_engine.clawx_logger import log_event


def test_clawx_log_append(tmp_path: Path) -> None:
    log_file = tmp_path / "clawx_log.jsonl"

    log_event("test_event", path=log_file, entity="BTC")

    assert log_file.exists()
    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    record = json.loads(lines[-1])
    assert record["event"] == "test_event"
    assert record["entity"] == "BTC"
