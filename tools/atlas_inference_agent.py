#!/usr/bin/env python3
"""Thin agent wrapper for direct ATLAS Ollama inference."""

from __future__ import annotations

import argparse
import json

import requests

URL = "http://localhost:11434/api/generate"
MODEL = "mistral"
TIMEOUT = 30


def run(prompt: str, *, url: str = URL, model: str = MODEL, timeout: int = TIMEOUT) -> dict[str, object]:
    response = requests.post(
        url,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("atlas inference agent expected a JSON object response")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a direct inference request against the local Ollama service")
    parser.add_argument("prompt", nargs="*", help="Prompt to send to the local Ollama service")
    args = parser.parse_args()

    prompt = " ".join(args.prompt).strip() or "health check"
    result = run(prompt)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
