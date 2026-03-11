"""Minimal Ollama provider for model-backed inference."""

from __future__ import annotations

from typing import Any

import requests

from providers.base import BaseProvider, ProviderRequest, ProviderResponse

DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"


class OllamaProvider(BaseProvider):
    """Small provider wrapper around the Ollama generate API."""

    def __init__(self, model: str = "qwen2.5", url: str = DEFAULT_OLLAMA_URL, timeout: float = 30.0) -> None:
        self.model = model
        self.url = url
        self.timeout = timeout

    def infer(self, request: ProviderRequest) -> ProviderResponse:
        response = requests.post(
            self.url,
            json={
                "model": request.model or self.model,
                "prompt": request.prompt,
                "stream": False,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            data = {}

        usage = self._usage_from_response(data)
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        return ProviderResponse(
            output=str(data.get("response", "")),
            provider="ollama",
            model=str(data.get("model", request.model or self.model)),
            usage=usage,
            metadata=metadata,
        )

    def _usage_from_response(self, data: dict[str, Any]) -> dict[str, int]:
        prompt_tokens = self._int_value(data, "prompt_eval_count")
        completion_tokens = self._int_value(data, "eval_count")
        total_tokens = prompt_tokens + completion_tokens
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

    def _int_value(self, data: dict[str, Any], key: str) -> int:
        value = data.get(key, 0)
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0


__all__ = ["DEFAULT_OLLAMA_URL", "OllamaProvider"]
