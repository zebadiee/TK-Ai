"""Read recent signals and persist LLM evidence artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from tools.load_cluster_env import get_ollama_url

from .ollama_analyser import analyse_signal

SIGNALS = Path("vault/runtime/signals.jsonl")
EVIDENCE = Path("vault/evidence/evidence.jsonl")
PROCESSED = Path("vault/runtime/processed_signals.json")
SEVERITY_ORDER = {
    "high": 3,
    "medium": 2,
    "low": 1,
}


def read_signals(path: Path = SIGNALS, limit: int = 5) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        if isinstance(data, dict):
            records.append(data)
    return records


def write_evidence(record: dict[str, Any], path: Path = EVIDENCE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def load_processed(path: Path = PROCESSED) -> set[str]:
    if not path.exists():
        return set()

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return set()
    return {str(item) for item in data}


def save_processed(ids: set[str], path: Path = PROCESSED) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(ids)), encoding="utf-8")


def prioritize_signals(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        signals,
        key=lambda signal: SEVERITY_ORDER.get(str(signal.get("severity", "medium")).lower(), 2),
        reverse=True,
    )


def resolve_node(node: str | None, endpoint: str | None) -> str:
    atlas_url = get_ollama_url()
    atlas_host = urlparse(atlas_url).hostname
    endpoint_host = urlparse(endpoint).hostname if endpoint else None

    if node == "atlas" or node == atlas_host or endpoint == atlas_url or endpoint_host == atlas_host:
        return "atlas"
    return node or "unknown"


def resolve_source(node: str | None, endpoint: str | None) -> str:
    return "atlas_ollama" if resolve_node(node, endpoint) == "atlas" else "router"


def current_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_investigation(
    signal_path: Path = SIGNALS,
    evidence_path: Path = EVIDENCE,
    processed_path: Path = PROCESSED,
) -> None:
    processed = load_processed(path=processed_path)

    for signal in prioritize_signals(read_signals(path=signal_path)):
        signal_id = signal.get("signal_id")
        processed_id = None if signal_id is None else str(signal_id)
        if processed_id is not None and processed_id in processed:
            continue

        try:
            result = analyse_signal(signal)
        except Exception as exc:
            print(f"Investigation error for signal {signal_id}: {exc}", flush=True)
            continue

        endpoint = result.get("endpoint")
        node = resolve_node(result.get("node"), endpoint)
        analysis = result.get("analysis", {})

        record = {
            "type": "llm_analysis",
            "signal_id": signal_id,
            "root_cause": analysis.get("root_cause", ""),
            "severity": analysis.get("severity", "unknown"),
            "confidence": analysis.get("confidence", 0.0),
            "recommended_action": analysis.get("recommended_action", ""),
            "agent": "investigation_agent",
            "model": result.get("model"),
            "node": node,
            "timestamp": current_timestamp(),
            "source": resolve_source(node, endpoint),
        }
        write_evidence(record, path=evidence_path)
        if processed_id is not None:
            processed.add(processed_id)
            save_processed(processed, path=processed_path)

    if not processed_path.exists():
        save_processed(processed, path=processed_path)
