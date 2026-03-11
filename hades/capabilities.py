"""Capability registry for graph planning and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ActionCapability:
    name: str
    providers: list[str]
    tiers: list[str]
    async_supported: bool
    capabilities: list[str]


class CapabilityRegistry:
    """Loads and validates the actions, models, and limits available to planners."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config if isinstance(config, dict) else {}

    @classmethod
    def from_path(cls, path: str | Path) -> "CapabilityRegistry":
        config_path = Path(path)
        if not config_path.exists():
            return cls({})

        with config_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        if not isinstance(data, dict):
            return cls({})
        return cls(data)

    def allowed_actions(self) -> list[str]:
        actions = self.config.get("actions", {})
        if not isinstance(actions, dict):
            return []
        return list(actions.keys())

    def get_action(self, name: str) -> ActionCapability:
        actions = self.config.get("actions", {})
        if not isinstance(actions, dict) or name not in actions:
            raise KeyError(name)

        record = actions[name]
        if not isinstance(record, dict):
            raise KeyError(name)

        providers = record.get("providers", [])
        tiers = record.get("tiers", [])
        capabilities = record.get("capabilities", [])
        return ActionCapability(
            name=name,
            providers=[str(item) for item in providers] if isinstance(providers, list) else [],
            tiers=[str(item) for item in tiers] if isinstance(tiers, list) else [],
            async_supported=bool(record.get("async", False)),
            capabilities=[str(item) for item in capabilities] if isinstance(capabilities, list) else [],
        )

    def allowed_capabilities(self) -> list[str]:
        actions = self.config.get("actions", {})
        if not isinstance(actions, dict):
            return []

        seen: set[str] = set()
        ordered: list[str] = []
        for action_name in actions:
            try:
                record = self.get_action(str(action_name))
            except KeyError:
                continue
            for capability in record.capabilities:
                normalized = capability.strip().lower()
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    ordered.append(normalized)
        return ordered

    def allowed_models(self, provider: str) -> list[str]:
        models = self.config.get("models", {})
        if not isinstance(models, dict):
            return []
        allowed = models.get(provider, [])
        if not isinstance(allowed, list):
            return []
        return [str(item) for item in allowed]

    def limit(self, name: str, default: int = 0) -> int:
        limits = self.config.get("limits", {})
        if not isinstance(limits, dict):
            return default
        value = limits.get(name, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def node_template(self, name: str) -> list[str]:
        templates = self.config.get("node_templates", {})
        if not isinstance(templates, dict):
            return []
        template = templates.get(name, [])
        if not isinstance(template, list):
            return []
        return [str(item) for item in template]
