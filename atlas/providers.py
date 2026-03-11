"""Provider interfaces for model inference."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any

import requests


@dataclass
class ProviderRequest:
    prompt: str
    model: str
    max_tokens: int
    trace_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderResponse:
    output: str
    provider: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaseProvider(ABC):
    """Abstract provider interface for model inference."""

    @abstractmethod
    def infer(self, request: ProviderRequest) -> ProviderResponse:
        raise NotImplementedError


class StaticProvider(BaseProvider):
    """Deterministic provider used for local policy simulation."""

    def __init__(self, name: str) -> None:
        self.name = name

    def infer(self, request: ProviderRequest) -> ProviderResponse:
        prompt_tokens = len(request.prompt.split())
        completion_tokens = min(64, request.max_tokens)
        return ProviderResponse(
            output=f"{self.name}:{request.model}:{request.prompt}",
            provider=self.name,
            model=request.model,
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            metadata={"mode": "deterministic"},
        )


class ClawXProvider(BaseProvider):
    """ClawX-backed provider with mock-safe fallback."""

    def __init__(self, bridge: str = "mock", timeout: float = 10.0) -> None:
        self.bridge = bridge
        self.timeout = timeout

    def infer(self, request: ProviderRequest) -> ProviderResponse:
        if not self.bridge.strip() or self.bridge == "mock":
            prompt_tokens = len(request.prompt.split())
            completion_tokens = min(96, request.max_tokens)
            return ProviderResponse(
                output=f"clawx:{request.model}:{request.prompt}",
                provider="clawx",
                model=request.model,
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                },
                metadata={"bridge": "mock"},
            )

        response = requests.post(
            f"{self.bridge.rstrip('/')}/v1/infer",
            json=request.to_dict(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        output = str(data.get("output", ""))
        usage = data.get("usage", {})
        metadata = data.get("metadata", {})
        if not isinstance(usage, dict):
            usage = {}
        if not isinstance(metadata, dict):
            metadata = {}
        return ProviderResponse(
            output=output,
            provider="clawx",
            model=str(data.get("model", request.model)),
            usage={
                "prompt_tokens": int(usage.get("prompt_tokens", 0)),
                "completion_tokens": int(usage.get("completion_tokens", 0)),
                "total_tokens": int(usage.get("total_tokens", 0)),
            },
            metadata=metadata,
        )


def build_default_providers(config: dict[str, Any] | None = None) -> dict[str, BaseProvider]:
    provider_config = config if isinstance(config, dict) else {}
    timeout = float(provider_config.get("timeout", 10.0))
    bridge = str(provider_config.get("clawx_bridge", "mock"))
    return {
        "local": StaticProvider("local"),
        "free": StaticProvider("free"),
        "paid": StaticProvider("paid"),
        "clawx": ClawXProvider(bridge=bridge, timeout=timeout),
    }
