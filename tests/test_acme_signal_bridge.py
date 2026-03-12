import json
from pathlib import Path

from tools import acme_signal_bridge


def test_bridge_signals_imports_json_files_once(tmp_path: Path) -> None:
    source = tmp_path / "signals"
    bus = tmp_path / "signals.jsonl"
    state = tmp_path / "bridge_state.json"
    source.mkdir()
    (source / "sig-1.json").write_text(json.dumps({"signal_id": "sig-1", "type": "acme_test"}), encoding="utf-8")

    imported_first = acme_signal_bridge.bridge_signals(source=source, bus=bus, state_path=state)
    imported_second = acme_signal_bridge.bridge_signals(source=source, bus=bus, state_path=state)

    rows = [json.loads(line) for line in bus.read_text(encoding="utf-8").splitlines()]
    assert imported_first == 1
    assert imported_second == 0
    assert [row["signal_id"] for row in rows] == ["sig-1"]
    assert rows[0]["source"] == "acme_ai"
    assert rows[0]["imported_by"] == "acme_signal_bridge"
    assert rows[0]["trace_id"] == "acme-bridge-sig-1"
    assert isinstance(rows[0]["ingested_at"], int)


def test_bridge_signals_supports_json_arrays(tmp_path: Path) -> None:
    source = tmp_path / "signals"
    bus = tmp_path / "signals.jsonl"
    state = tmp_path / "bridge_state.json"
    source.mkdir()
    (source / "batch.json").write_text(
        json.dumps(
            [
                {"signal_id": "sig-1", "type": "acme_test"},
                {"signal_id": "sig-2", "type": "acme_test"},
            ]
        ),
        encoding="utf-8",
    )

    imported = acme_signal_bridge.bridge_signals(source=source, bus=bus, state_path=state)

    lines = bus.read_text(encoding="utf-8").splitlines()
    assert imported == 2
    assert [json.loads(line)["signal_id"] for line in lines] == ["sig-1", "sig-2"]


def test_bridge_signals_generates_signal_id_when_missing(tmp_path: Path) -> None:
    source = tmp_path / "signals"
    bus = tmp_path / "signals.jsonl"
    state = tmp_path / "bridge_state.json"
    source.mkdir()
    (source / "batch.json").write_text(json.dumps({"type": "acme_test"}), encoding="utf-8")

    imported = acme_signal_bridge.bridge_signals(source=source, bus=bus, state_path=state)

    rows = [json.loads(line) for line in bus.read_text(encoding="utf-8").splitlines()]
    assert imported == 1
    assert rows[0]["signal_id"] == "acme-batch-1"
