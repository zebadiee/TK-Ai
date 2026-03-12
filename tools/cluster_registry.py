#!/usr/bin/env python3
"""Canonical cluster node registry and transport helpers."""

from __future__ import annotations

import json
import shlex
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "cluster" / "cluster_config.json"
NODE_ROLES_PATH = ROOT / "cluster" / "node_roles.json"

TOPOLOGY_ROLE_BY_CLUSTER_ROLE = {
    "control": "control_plane",
    "gpu_worker": "gpu_inference",
    "gateway": "infrastructure_backbone",
}


@dataclass(frozen=True)
class ClusterNode:
    """Resolved node metadata from cluster configuration."""

    name: str
    cluster_role: str
    topology_role: str
    host: str
    ip: str | None = None
    ssh_target: str | None = None
    ssh_user: str | None = None
    ssh_port: int = 22
    ollama_url: str | None = None
    services: tuple[str, ...] = ()

    def to_topology_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "role": self.topology_role,
            "agents": [],
            "host": self.host,
            "ssh_target": self.transport_target,
        }
        if self.ip:
            payload["ip"] = self.ip
        if self.ollama_url:
            payload["ollama_url"] = self.ollama_url
        if self.services:
            payload["services"] = list(self.services)
        return payload

    @property
    def transport_target(self) -> str:
        target = self.ssh_target or self.ip or self.host or self.name
        if self.ssh_user and "@" not in target:
            return f"{self.ssh_user}@{target}"
        return target


def normalize_node_name(value: str) -> str:
    token = value.strip()
    if not token:
        return ""
    if "://" in token:
        parsed = urlparse(token)
        token = parsed.hostname or token
    if "@" in token:
        token = token.rsplit("@", 1)[-1]
    if ":" in token and token.count(":") == 1:
        token = token.split(":", 1)[0]
    if "." in token:
        segments = token.split(".")
        if not all(segment.isdigit() for segment in segments):
            token = segments[0]
    return token.lower()


def detect_local_node() -> str:
    return normalize_node_name(socket.gethostname())


def load_cluster_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("cluster config must be a JSON object")
    return data


def load_node_roles(path: Path = NODE_ROLES_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("node roles must be a JSON object")
    payload: dict[str, dict[str, Any]] = {}
    for name, value in data.items():
        if not isinstance(value, dict):
            continue
        payload[normalize_node_name(str(name))] = value
    return payload


def load_cluster_nodes(
    config_path: Path = CONFIG_PATH,
    node_roles_path: Path = NODE_ROLES_PATH,
) -> dict[str, ClusterNode]:
    config = load_cluster_config(config_path)
    cluster = config.get("cluster", {}) if isinstance(config, dict) else {}
    if not isinstance(cluster, dict):
        raise ValueError("cluster config must define a cluster object")

    role_overrides = load_node_roles(node_roles_path)
    nodes: dict[str, ClusterNode] = {}

    names = {normalize_node_name(str(name)) for name in cluster}
    names.update(role_overrides.keys())

    for name in sorted(names):
        raw = cluster.get(name, {})
        if not isinstance(raw, dict):
            raw = {}
        override = role_overrides.get(name, {})

        cluster_role = str(raw.get("role") or override.get("role") or "worker").strip() or "worker"
        host = str(raw.get("host") or name).strip() or name
        ip = str(raw.get("ip", "")).strip() or None
        ssh_target = str(raw.get("ssh_target", "")).strip() or None
        ssh_user = str(raw.get("ssh_user", "")).strip() or None
        ollama_url = str(raw.get("ollama_url", "")).strip() or None
        ssh_port = int(raw.get("ssh_port", 22) or 22)
        services = tuple(
            sorted(
                {
                    str(service).strip()
                    for service in override.get("services", [])
                    if str(service).strip()
                }
            )
        )

        nodes[name] = ClusterNode(
            name=name,
            cluster_role=cluster_role,
            topology_role=TOPOLOGY_ROLE_BY_CLUSTER_ROLE.get(cluster_role, cluster_role),
            host=host,
            ip=ip,
            ssh_target=ssh_target,
            ssh_user=ssh_user,
            ssh_port=ssh_port,
            ollama_url=ollama_url,
            services=services,
        )

    return nodes


def resolve_node(name: str, nodes: dict[str, ClusterNode] | None = None) -> ClusterNode:
    cluster_nodes = nodes or load_cluster_nodes()
    lookup = normalize_node_name(name)
    if lookup in cluster_nodes:
        return cluster_nodes[lookup]

    for node in cluster_nodes.values():
        candidates = {
            normalize_node_name(node.name),
            normalize_node_name(node.host),
        }
        if node.ip:
            candidates.add(normalize_node_name(node.ip))
        if node.ssh_target:
            candidates.add(normalize_node_name(node.ssh_target))
        if lookup in candidates:
            return node

    raise KeyError(f"unknown cluster node: {name}")


def build_transport_command(
    node_name: str,
    argv: list[str],
    *,
    nodes: dict[str, ClusterNode] | None = None,
    local_node: str | None = None,
) -> list[str]:
    if not argv:
        raise ValueError("transport argv must not be empty")

    current = normalize_node_name(local_node or detect_local_node())
    ssh_port = 22
    try:
        node = resolve_node(node_name, nodes=nodes)
        target = node.transport_target
        remote_name = node.name
        ssh_port = node.ssh_port
    except KeyError:
        target = node_name
        remote_name = normalize_node_name(node_name)

    if remote_name == current:
        return list(argv)

    remote = shlex.join(argv)
    command = ["ssh"]
    if "@" in target:
        target_host = target.split("@", 1)[1]
    else:
        target_host = target
    if ":" not in target_host and ssh_port != 22:
        command.extend(["-p", str(ssh_port)])
    command.extend([target, f"/bin/bash -lc {shlex.quote(remote)}"])
    return command
