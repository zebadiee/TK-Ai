#!/usr/bin/env python3
"""Cluster diagnostics for TK-Ai nodes."""

from __future__ import annotations

import socket
import subprocess
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.router.model_router import get_route_chain
from tools.acme_integration_status import format_status_lines as format_acme_status_lines
from tools.cluster_registry import detect_local_node, load_cluster_config, load_cluster_nodes

CONFIG_PATH = ROOT / "cluster" / "cluster_config.json"
NODE_ROLES_PATH = ROOT / "cluster" / "node_roles.json"
SIGNALS_PATH = ROOT / "vault" / "runtime" / "signals.jsonl"
EVIDENCE_PATH = ROOT / "vault" / "evidence" / "evidence.jsonl"


def load_config() -> dict[str, object]:
    return load_cluster_config(CONFIG_PATH)


def detect_node() -> str:
    return detect_local_node()


def test_tcp(host: str, port: int, timeout: int = 3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def test_http(url: str, timeout: int = 5) -> int | None:
    try:
        response = requests.get(url, timeout=timeout)
    except requests.RequestException:
        return None
    return response.status_code


def get_local_ip() -> str:
    hostname = socket.gethostname()
    try:
        return socket.gethostbyname(hostname)
    except OSError:
        return "unavailable"


def get_service_status(name: str = "tkai-investigation.service") -> str:
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", name],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError:
        return "unavailable"

    status = result.stdout.strip() or result.stderr.strip()
    return status or "unknown"


def main() -> int:
    nodes = load_cluster_nodes(CONFIG_PATH, NODE_ROLES_PATH)
    node = detect_node()

    print()
    print("=== TK-AI CLUSTER DOCTOR ===")
    print()
    print(f"Node: {node}")

    print()
    print("Cluster nodes:")
    for name, payload in nodes.items():
        print(f" - {name} ({payload.cluster_role})")

    atlas = nodes.get("atlas")
    atlas_host = atlas.ip or atlas.host if atlas else None
    ollama_url = atlas.ollama_url if atlas else None

    print()
    print("--- NETWORK CHECK ---")
    if atlas_host:
        tcp_ok = test_tcp(atlas_host, 11434)
        print(f"ATLAS TCP 11434: {'OK' if tcp_ok else 'FAILED'}")
    else:
        print("ATLAS TCP 11434: SKIPPED")

    print()
    print("--- OLLAMA CHECK ---")
    if ollama_url:
        status = test_http(f"{ollama_url}/api/tags")
        print("Ollama API: OK" if status == 200 else "Ollama API: FAILED")
    else:
        print("Ollama API: SKIPPED")

    print()
    print("--- PIPELINE ---")
    print(f"Signals file: {'OK' if SIGNALS_PATH.exists() else 'MISSING'}")
    print(f"Evidence file: {'OK' if EVIDENCE_PATH.exists() else 'MISSING'}")
    print(f"Investigation daemon: {get_service_status()}")

    print()
    print("--- ROUTER STATUS ---")
    print(f"Router chain: {' -> '.join(get_route_chain())}")

    print()
    print("--- ACME INTEGRATION ---")
    for line in format_acme_status_lines():
        print(line)

    print()
    print("--- LOCAL HOST ---")
    print(f"Hostname: {socket.gethostname()}")
    print(f"IP: {get_local_ip()}")
    if node in nodes:
        print(f"Role: {nodes[node].cluster_role}")
        print(f"SSH target: {nodes[node].transport_target}")

    print()
    print("=== END REPORT ===")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
