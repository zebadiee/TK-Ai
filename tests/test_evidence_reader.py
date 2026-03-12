import json
from pathlib import Path

from gateway.evidence_reader import derive_follow_up_signals, read_recent_evidence


def test_read_recent_evidence_returns_last_records(tmp_path: Path) -> None:
    evidence_file = tmp_path / "evidence.jsonl"
    evidence_file.write_text(
        "\n".join(
            [
                json.dumps({"signal_id": "sig-1", "severity": "low"}),
                json.dumps({"signal_id": "sig-2", "severity": "high"}),
                json.dumps({"signal_id": "sig-3", "severity": "critical"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    records = read_recent_evidence(2, path=evidence_file)

    assert [record["signal_id"] for record in records] == ["sig-2", "sig-3"]


def test_derive_follow_up_signals_emits_high_and_critical() -> None:
    follow_ups = derive_follow_up_signals(
        [
            {"signal_id": "sig-1", "severity": "low"},
            {"signal_id": "sig-2", "severity": "high"},
            {"signal_id": "sig-3", "severity": "critical"},
        ]
    )

    assert follow_ups == [
        {"type": "investigate_deeper", "evidence": {"signal_id": "sig-2", "severity": "high"}},
        {"type": "cluster_emergency", "evidence": {"signal_id": "sig-3", "severity": "critical"}},
    ]
