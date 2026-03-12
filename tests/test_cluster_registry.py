import json
from pathlib import Path

from tools import cluster_registry


def test_load_cluster_nodes_merges_cluster_config_and_role_metadata(tmp_path: Path) -> None:
    config_path = tmp_path / "cluster_config.json"
    roles_path = tmp_path / "node_roles.json"
    config_path.write_text(
        json.dumps(
            {
                "cluster": {
                    "hades": {"role": "control", "host": "hades", "ssh_user": "zebadiee"},
                    "atlas": {
                        "role": "gpu_worker",
                        "host": "atlas.local",
                        "ip": "192.168.1.17",
                        "ollama_url": "http://192.168.1.17:11434",
                        "ssh_port": 2222,
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    roles_path.write_text(
        json.dumps(
            {
                "hades": {"role": "control", "services": ["scheduler", "policy_daemon"]},
                "atlas": {"role": "gpu_worker", "services": ["inference"]},
            }
        ),
        encoding="utf-8",
    )

    nodes = cluster_registry.load_cluster_nodes(config_path, roles_path)

    assert nodes["hades"].transport_target == "zebadiee@hades"
    assert nodes["hades"].services == ("policy_daemon", "scheduler")
    assert nodes["atlas"].topology_role == "gpu_inference"
    assert nodes["atlas"].ssh_port == 2222
    assert nodes["atlas"].ollama_url == "http://192.168.1.17:11434"


def test_resolve_node_accepts_aliases(tmp_path: Path) -> None:
    config_path = tmp_path / "cluster_config.json"
    roles_path = tmp_path / "node_roles.json"
    config_path.write_text(
        json.dumps(
            {
                "cluster": {
                    "atlas": {
                        "role": "gpu_worker",
                        "host": "atlas.example.net",
                        "ip": "192.168.1.17",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    roles_path.write_text(json.dumps({}), encoding="utf-8")

    nodes = cluster_registry.load_cluster_nodes(config_path, roles_path)

    assert cluster_registry.resolve_node("atlas.example.net", nodes).name == "atlas"
    assert cluster_registry.resolve_node("192.168.1.17", nodes).name == "atlas"
    assert cluster_registry.resolve_node("http://atlas.example.net:11434", nodes).name == "atlas"


def test_build_transport_command_uses_ssh_for_remote_nodes(tmp_path: Path) -> None:
    config_path = tmp_path / "cluster_config.json"
    roles_path = tmp_path / "node_roles.json"
    config_path.write_text(
        json.dumps(
            {
                "cluster": {
                    "atlas": {
                        "role": "gpu_worker",
                        "host": "atlas",
                        "ssh_user": "zebadiee",
                        "ssh_port": 2222,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    roles_path.write_text(json.dumps({}), encoding="utf-8")
    nodes = cluster_registry.load_cluster_nodes(config_path, roles_path)

    command = cluster_registry.build_transport_command(
        "atlas",
        ["python3", "/tmp/ping.py"],
        nodes=nodes,
        local_node="hades",
    )

    assert command[:4] == ["ssh", "-p", "2222", "zebadiee@atlas"]
    assert "/bin/bash -lc" in command[4]


def test_build_transport_command_short_circuits_for_local_node() -> None:
    command = cluster_registry.build_transport_command(
        "hades",
        ["python3", "/tmp/local.py"],
        local_node="hades",
    )

    assert command == ["python3", "/tmp/local.py"]
