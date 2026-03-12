#!/usr/bin/env python3
"""Operator-facing ClawX console over artifact streams."""

from __future__ import annotations

import json
import socket
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.load_topology import load_topology

CLAWX_LOG = ROOT / "vault" / "runtime" / "clawx_log.jsonl"
SIGNALS = ROOT / "vault" / "runtime" / "signals.jsonl"
EVIDENCE = ROOT / "vault" / "evidence" / "evidence.jsonl"
CLUSTER_STATUS = ROOT / "vault" / "runtime" / "cluster_status.json"
POLICY = ROOT / "vault" / "policy" / "scheduler_policy.json"
NODE_ROLES = ROOT / "cluster" / "node_roles.json"


def tail_log(path: Path, count: int = 10) -> list[str]:
    if not path.exists():
        return []
    return [line for line in path.read_text(encoding="utf-8").splitlines()[-count:] if line.strip()]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
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


def repo_summary(root: Path = ROOT) -> list[str]:
    interesting = [
        "adapters",
        "athena",
        "atlas",
        "cluster",
        "docs",
        "examples",
        "gateway",
        "hades",
        "kernel",
        "memory",
        "modules",
        "providers",
        "sandbox",
        "tests",
        "tools",
        "vault",
    ]
    present = [name for name in interesting if (root / name).exists()]
    lines = ["Repo Summary", "------------", f"root: {root}", "paths:"]
    lines.extend(f"- {name}" for name in present)
    return lines


def module_summary(root: Path = ROOT) -> list[str]:
    module_root = root / "modules"
    lines = ["Modules", "-------"]
    if not module_root.exists():
        return lines + ["No modules directory"]
    for path in sorted(module_root.iterdir()):
        if path.is_dir():
            files = sorted(item.name for item in path.iterdir() if item.is_file() and item.suffix == ".py")
            lines.append(f"{path.name}: {', '.join(files) if files else 'no python files'}")
    return lines


def health_summary(root: Path = ROOT) -> list[str]:
    cluster = load_json(root / "vault" / "runtime" / "cluster_status.json")
    roles = load_json(root / "cluster" / "node_roles.json")
    policy = load_json(root / "vault" / "policy" / "scheduler_policy.json")
    lines = ["Cluster Health", "--------------"]
    if cluster:
        lines.append(f"node: {cluster.get('node', 'unknown')}")
        lines.append(f"role: {cluster.get('role', 'unknown')}")
        services = cluster.get("services", {})
        if isinstance(services, dict):
            for name, state in services.items():
                lines.append(f"{name}: {state}")
    else:
        lines.append("cluster_status: unavailable")

    if policy:
        lines.append(f"policy_state: {policy.get('desired_state', policy.get('state', 'unknown'))}")
        lines.append(f"policy_reason: {policy.get('reason', '')}")
    else:
        lines.append("policy_state: unavailable")

    if roles:
        lines.append("known_nodes:")
        lines.extend(f"- {name}: {meta.get('role', 'unknown')}" for name, meta in sorted(roles.items()) if isinstance(meta, dict))
    return lines


def proposal_summary(root: Path = ROOT) -> list[str]:
    policy = load_json(root / "vault" / "policy" / "scheduler_policy.json")
    signal_count = len(tail_log(root / "vault" / "runtime" / "signals.jsonl", count=20))
    reasoning_count = len(tail_log(root / "vault" / "runtime" / "clawx_log.jsonl", count=20))

    lines = ["ClawX Proposal", "--------------"]
    if signal_count == 0:
        lines.append("No recent signals. Run tkai-try to seed the observability loop.")
        return lines

    if policy.get("updated_by") == "operator":
        lines.append("City is under manual override. Observe signal flow before changing policy.")
    else:
        lines.append("Policy is artifact-driven. Let ClawX recommendations settle before overriding.")

    lines.append(f"recent_signals: {signal_count}")
    lines.append(f"recent_reasoning_events: {reasoning_count}")
    lines.append("Next read-only step: compare 'signals' with 'status' to confirm reasoning-to-signal alignment.")
    return lines


def node_summary(root: Path = ROOT, hostname: str | None = None) -> list[str]:
    topology = load_topology(root / "vault" / "runtime" / "cluster_topology.json")
    nodes = topology.get("nodes", {}) if isinstance(topology, dict) else {}
    current = hostname or socket.gethostname()
    payload = nodes.get(current, {}) if isinstance(nodes, dict) else {}
    agents = payload.get("agents", []) if isinstance(payload, dict) else []
    lines = ["Current Node", "------------"]
    lines.append(f"node: {current}")
    lines.append(f"role: {payload.get('role', 'unknown') if isinstance(payload, dict) else 'unknown'}")
    lines.append(f"agents: {', '.join(str(agent) for agent in agents) if agents else 'none'}")
    return lines


def show_nodes(root: Path = ROOT) -> list[str]:
    topology = load_topology(root / "vault" / "runtime" / "cluster_topology.json")
    nodes = topology.get("nodes", {}) if isinstance(topology, dict) else {}
    lines = ["Nodes", "-----"]
    for node, payload in sorted(nodes.items()):
        if not isinstance(payload, dict):
            continue
        lines.append(f"{node}: {payload.get('role', 'unknown')}")
    if len(lines) == 2:
        lines.append("No nodes in topology")
    return lines


def show_agents(root: Path = ROOT, node: str | None = None) -> list[str]:
    topology = load_topology(root / "vault" / "runtime" / "cluster_topology.json")
    nodes = topology.get("nodes", {}) if isinstance(topology, dict) else {}
    lines = ["Agents", "------"]
    if node:
        payload = nodes.get(node, {}) if isinstance(nodes, dict) else {}
        agents = payload.get("agents", []) if isinstance(payload, dict) else []
        lines.append(f"{node}:")
        lines.extend(f"- {agent}" for agent in agents)
        if not agents:
            lines.append("No agents")
        return lines

    for name, payload in sorted(nodes.items()):
        if not isinstance(payload, dict):
            continue
        agents = payload.get("agents", [])
        lines.append(f"{name}: {', '.join(str(agent) for agent in agents) if agents else 'none'}")
    if len(lines) == 2:
        lines.append("No agents in topology")
    return lines


def evidence_for_signal(signal_id: str, root: Path = ROOT) -> list[str]:
    lines = [json.dumps(record, sort_keys=True) for record in load_jsonl(root / "vault" / "evidence" / "evidence.jsonl") if str(record.get("signal_id")) == signal_id]
    return lines or [f"No evidence found for signal {signal_id}"]


def signals_for_agent(agent: str, root: Path = ROOT) -> list[str]:
    evidence = load_jsonl(root / "vault" / "evidence" / "evidence.jsonl")
    signal_ids = {str(record.get("signal_id")) for record in evidence if str(record.get("agent")) == agent}
    signals = [json.dumps(record, sort_keys=True) for record in load_jsonl(root / "vault" / "runtime" / "signals.jsonl") if str(record.get("signal_id")) in signal_ids]
    return signals or [f"No signals found for agent {agent}"]


def print_recent() -> None:
    print("\nRecent reasoning:\n")
    lines = tail_log(CLAWX_LOG)
    if not lines:
        print("No ClawX reasoning yet")
        return
    for line in lines:
        print(line)


def main() -> int:
    print("")
    print("=================================")
    print("ClawX Operator Console")
    print("=================================")
    print("\n".join(node_summary()))
    print_recent()
    print("\nType 'exit' to leave\n")

    while True:
        try:
            command = input("clawx> ").strip()
        except EOFError:
            print()
            return 0

        if command == "exit":
            return 0
        if command == "status":
            print_recent()
            continue
        if command == "signals":
            lines = tail_log(SIGNALS)
            if not lines:
                print("No signals yet")
                continue
            for line in lines:
                print(line)
            continue
        if command == "repo":
            print("\n".join(repo_summary()))
            continue
        if command == "modules":
            print("\n".join(module_summary()))
            continue
        if command == "health":
            print("\n".join(health_summary()))
            continue
        if command == "propose":
            print("\n".join(proposal_summary()))
            continue
        if command == "help":
            print("Commands: status, signals, repo, modules, health, propose, where, show nodes, show agents [node], evidence <signal_id>, signals-for-agent <name>, help, exit")
            continue
        if command == "where":
            print("\n".join(node_summary()))
            continue
        if command == "show nodes":
            print("\n".join(show_nodes()))
            continue
        if command.startswith("show agents"):
            parts = command.split(maxsplit=2)
            node = parts[2] if len(parts) == 3 else None
            print("\n".join(show_agents(node=node)))
            continue
        if command.startswith("evidence "):
            _, signal_id = command.split(maxsplit=1)
            print("\n".join(evidence_for_signal(signal_id)))
            continue
        if command.startswith("signals-for-agent "):
            _, agent = command.split(maxsplit=1)
            print("\n".join(signals_for_agent(agent)))
            continue
        if command:
            print("Commands: status, signals, repo, modules, health, propose, where, show nodes, show agents [node], evidence <signal_id>, signals-for-agent <name>, help, exit")


if __name__ == "__main__":
    raise SystemExit(main())
