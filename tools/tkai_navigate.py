#!/usr/bin/env python3
"""Topology-aware navigation helpers for nodes, agents, and evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.load_topology import load_topology

REGISTRY = ROOT / "vault" / "runtime" / "agent_registry.json"
SIGNALS = ROOT / "vault" / "runtime" / "signals.jsonl"
EVIDENCE = ROOT / "vault" / "evidence" / "evidence.jsonl"


def load_registry(path: Path = REGISTRY) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def list_nodes(topology: dict[str, Any]) -> list[str]:
    nodes = topology.get("nodes", {}) if isinstance(topology, dict) else {}
    lines = ["Nodes", "-----"]
    for node, payload in sorted(nodes.items()):
        if not isinstance(payload, dict):
            continue
        agents = payload.get("agents", [])
        lines.append(f"{node}: role={payload.get('role', 'unknown')} agents={len(agents)}")
        if agents:
            lines.append(f"  {', '.join(str(agent) for agent in agents)}")
    if len(lines) == 2:
        lines.append("No nodes in topology")
    return lines


def list_agents(topology: dict[str, Any], registry: dict[str, Any], node: str | None = None) -> list[str]:
    lines = ["Agents", "------"]
    nodes = topology.get("nodes", {}) if isinstance(topology, dict) else {}

    if node:
        payload = nodes.get(node, {})
        agents = payload.get("agents", []) if isinstance(payload, dict) else []
        lines.append(f"{node}:")
        lines.extend(f"- {agent}" for agent in agents)
        if not agents:
            lines.append("No agents")
        return lines

    for agent, payload in sorted(registry.items()):
        if not isinstance(payload, dict):
            continue
        lines.append(f"{agent}: node={payload.get('node', 'unknown')}")
    if len(lines) == 2:
        lines.append("No agents in registry")
    return lines


def describe_agent(name: str, registry: dict[str, Any]) -> list[str]:
    payload = registry.get(name)
    if not isinstance(payload, dict):
        return [f"Unknown agent: {name}"]

    node = str(payload.get("node", "unknown"))
    entrypoint = payload.get("entrypoint")
    lines = [
        f"agent: {name}",
        f"node: {node}",
    ]
    if entrypoint:
        lines.append(f"entrypoint: {entrypoint}")
        lines.append(f"invoke: python3 tools/invoke_agent.py{name and ' ' + name or ''}")
    else:
        lines.append(f"endpoint: {payload.get('endpoint', 'unavailable')}")
        lines.append("invoke: not executable via invoke_agent (no entrypoint)")
    return lines


def evidence_for_signal(signal_id: str, evidence_path: Path = EVIDENCE) -> list[str]:
    matches = [record for record in read_jsonl(evidence_path) if str(record.get("signal_id")) == signal_id]
    lines = [f"Evidence for signal {signal_id}", "------------------------------"]
    if not matches:
        return lines + ["No evidence found"]
    lines.extend(json.dumps(record, sort_keys=True) for record in matches)
    return lines


def signals_for_agent(agent: str, signals_path: Path = SIGNALS, evidence_path: Path = EVIDENCE) -> list[str]:
    evidence = read_jsonl(evidence_path)
    signal_ids = {str(record.get("signal_id")) for record in evidence if str(record.get("agent")) == agent}
    signals = [record for record in read_jsonl(signals_path) if str(record.get("signal_id")) in signal_ids]

    lines = [f"Signals associated with agent {agent}", "---------------------------------"]
    if not signals:
        return lines + ["No signals found"]
    lines.extend(json.dumps(record, sort_keys=True) for record in signals)
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Navigate the TK-AI topology and evidence graph")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("nodes", help="List nodes, roles, and agents")

    agents_parser = subparsers.add_parser("agents", help="List agents for all nodes or a specific node")
    agents_parser.add_argument("node", nargs="?", help="Optional node name")

    agent_parser = subparsers.add_parser("agent", help="Show one agent's location and invocation")
    agent_parser.add_argument("name", help="Agent name")

    evidence_parser = subparsers.add_parser("evidence", help="Show evidence for a signal")
    evidence_parser.add_argument("signal_id", help="Signal ID")

    signals_parser = subparsers.add_parser("signals-for-agent", help="Show signals associated with an agent")
    signals_parser.add_argument("name", help="Agent name")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    topology = load_topology()
    registry = load_registry()

    if args.command == "nodes":
        print("\n".join(list_nodes(topology)))
        return 0
    if args.command == "agents":
        print("\n".join(list_agents(topology, registry, node=args.node)))
        return 0
    if args.command == "agent":
        print("\n".join(describe_agent(args.name, registry)))
        return 0
    if args.command == "evidence":
        print("\n".join(evidence_for_signal(args.signal_id)))
        return 0
    if args.command == "signals-for-agent":
        print("\n".join(signals_for_agent(args.name)))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
