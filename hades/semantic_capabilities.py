"""Semantic capability resolution for provider-agnostic graph planning."""

from __future__ import annotations

from hades.capabilities import CapabilityRegistry


def _normalize_capability(capability: str) -> str:
    return " ".join(capability.lower().strip().split())


class SemanticCapabilityIndex:
    """Maps semantic capabilities like 'monitor' or 'analyse' to allowed actions."""

    ASYNC_FIRST = {"monitor", "watch", "track", "research"}
    SYNC_FIRST = {"analyse", "analyze", "summarise", "summarize", "classify", "reason", "notify", "alert", "deliver"}

    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    def resolve(self, capability: str) -> list[str]:
        normalized = _normalize_capability(capability)
        matches: list[str] = []
        for action_name in self.registry.allowed_actions():
            try:
                action = self.registry.get_action(action_name)
            except KeyError:
                continue
            if normalized in {_normalize_capability(item) for item in action.capabilities}:
                matches.append(action_name)
        return matches

    def resolve_best(self, capability: str) -> str | None:
        matches = self.resolve(capability)
        if not matches:
            return None

        normalized = _normalize_capability(capability)
        ranked = sorted(matches, key=lambda name: self._rank(name, normalized))
        return ranked[0] if ranked else None

    def _rank(self, action_name: str, capability: str) -> tuple[int, int, str]:
        action = self.registry.get_action(action_name)
        if capability in self.ASYNC_FIRST:
            async_penalty = 0 if action.async_supported else 1
        elif capability in self.SYNC_FIRST:
            async_penalty = 0 if not action.async_supported else 1
        else:
            async_penalty = 0
        provider_penalty = 0 if action.providers else 1
        return (async_penalty, provider_penalty, action_name)
