"""Intent router for HADES."""

from __future__ import annotations


class Router:
    """Maps incoming intents to executable actions."""

    def __init__(self, routes: dict[str, str] | None = None) -> None:
        self.routes = routes or {}

    def resolve(self, intent: str) -> str:
        return self.routes.get(intent, "noop")
