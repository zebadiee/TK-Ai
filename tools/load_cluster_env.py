"""Load stable cluster environment values from the canonical config."""

from pathlib import Path

from tools.cluster_registry import load_cluster_config

CONFIG_PATH = Path("cluster/cluster_config.json")


def load_config():
    return load_cluster_config(CONFIG_PATH)


def get_ollama_url():
    return load_config()["cluster"]["atlas"]["ollama_url"]


def get_default_model():
    return load_config()["ollama"]["model_default"]


def get_ollama_timeout():
    return int(load_config()["ollama"]["timeout"])
