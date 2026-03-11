import json
from pathlib import Path

import pytest

from hades.patterns import DEFAULT_PATTERNS, PatternIndex, load_patterns, save_patterns


def test_load_patterns_returns_deepcopy_default_if_missing(tmp_path):
    path = tmp_path / "missing.json"
    patterns = load_patterns(path)
    assert patterns["routes"] == {}

    patterns["routes"]["mutated"] = True
    assert DEFAULT_PATTERNS["routes"] == {}


def test_load_patterns_reads_json_correctly(tmp_path):
    path = tmp_path / "patterns.json"
    data = {"routes": {"a": "b"}, "capabilities": {"c": "d"}}
    path.write_text(json.dumps(data))
    patterns = load_patterns(path)
    assert patterns["routes"] == data["routes"]
    assert patterns["capabilities"] == data["capabilities"]


def test_save_patterns_validation():
    with pytest.raises(ValueError, match="dictionary"):
        save_patterns("foo.json", [1, 2, 3])


def test_pattern_index_lookup_and_reinforce(tmp_path):
    index_path = tmp_path / "index.json"
    index = PatternIndex(index_path)

    assert index.lookup("test_intent") is None

    index.reinforce("test_intent", "test_action")
    assert index_path.exists()

    record = index.lookup("test_intent")
    assert record is not None
    assert record["action"] == "test_action"
    assert record["usage_count"] == 1
    assert record["confidence"] == 1.0

    match = index.lookup_best("test_intent")
    assert match is not None
    assert match.action == "test_action"
    assert match.reason == "exact"


def test_pattern_index_confidence_gating(tmp_path):
    index_path = tmp_path / "index.json"
    index = PatternIndex(index_path)

    index.data["patterns"] = {"low_conf": {"action": "noop", "confidence": 0.1}}
    assert index.lookup("low_conf", threshold=0.5) is None
    assert index.lookup_best("low_conf", threshold=0.5) is None


def test_pattern_index_lookup_best_uses_token_overlap(tmp_path):
    index_path = tmp_path / "index.json"
    index = PatternIndex(index_path)
    index.reinforce("monitor sec filings", "clawx_monitor")

    match = index.lookup_best("monitor filings", threshold=0.5)

    assert match is not None
    assert match.action == "clawx_monitor"
    assert match.reason == "token_overlap"
    assert match.source_intent == "monitor sec filings"


def test_pattern_index_reinforce_merges_metadata(tmp_path):
    index_path = tmp_path / "index.json"
    index = PatternIndex(index_path)

    index.reinforce("ping user", "echo", metadata={"source": "router"})
    index.reinforce("ping user", "echo", metadata={"channel": "cli"})

    record = index.lookup("ping user")
    assert record is not None
    assert record["metadata"]["source"] == "router"
    assert record["metadata"]["channel"] == "cli"


def test_pattern_index_migrates_legacy_list_shape(tmp_path):
    index_path = tmp_path / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "patterns": [
                    {
                        "intent": "legacy_intent",
                        "action": "legacy_action",
                        "confidence": 0.7,
                        "usage_count": 3,
                    }
                ]
            }
        )
    )

    index = PatternIndex(index_path)
    record = index.lookup("legacy_intent", threshold=0.5)

    assert record is not None
    assert record["action"] == "legacy_action"
    assert record["usage_count"] == 3
