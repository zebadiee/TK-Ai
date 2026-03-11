"""ATLAS executor for deterministic action execution and ClawX integration."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import requests
from atlas.providers import ProviderRequest, build_default_providers, BaseProvider

CLAWX_ALLOWLIST = {"clawx_monitor", "clawx_scrape", "clawx_push"}

class AtlasExecutor:
    """Executes actions selected by the router, including external bridges."""

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        providers: dict[str, BaseProvider] | None = None,
    ) -> None:
        self.config = config or {}
        self.logger = logging.getLogger("atlas")
        self.timeout = self.config.get("timeout", 10.0)
        self.providers = providers or build_default_providers(self.config)

    def execute(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        if action == "noop":
            return {"status": "ignored", "action": action, "payload": payload}

        if action == "notify":
            return self._handle_notify(action, payload)

        if action == "model_infer":
            return self._handle_model(action, payload)

        if action.startswith("clawx_"):
            return self._handle_clawx(action, payload)

        return {"status": "ok", "action": action, "payload": payload}

    def _handle_model(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        model_route = payload.get("model_route", {})
        if not isinstance(model_route, dict):
            model_route = {}

        backend = str(model_route.get("backend", "local"))
        model = str(model_route.get("model", "local-small"))
        budget = {
            "max_tokens": int(model_route.get("max_tokens", 256)),
            "max_latency_ms": int(model_route.get("max_latency_ms", 1000)),
        }
        provider = self.providers.get(backend)
        if provider is None:
            return {
                "status": "failed",
                "error": f"Unknown model provider backend: {backend}",
                "backend": "Model",
                "action": action,
            }

        prompt = str(payload.get("prompt") or payload.get("intent_text") or payload.get("trace_id", ""))
        request = ProviderRequest(
            prompt=prompt,
            model=model,
            max_tokens=budget["max_tokens"],
            trace_id=str(payload.get("trace_id", "")),
            metadata={"payload": payload},
        )

        self.logger.info("Routing to model backend: %s via %s", model, backend)
        try:
            response = provider.infer(request)
        except Exception as exc:
            self.logger.error("Model provider failure: %s", str(exc))
            return {
                "status": "failed",
                "error": f"Model provider failure: {str(exc)}",
                "backend": "Model",
                "action": action,
                "model_backend": backend,
                "model": model,
            }

        return {
            "status": "ok",
            "backend": "Model",
            "action": action,
            "model_backend": backend,
            "model": response.model,
            "budget": budget,
            "output": response.output,
            "usage": response.usage,
            "provider_metadata": response.metadata,
            "payload": payload,
        }

    def _handle_notify(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "ok",
            "backend": "Notify",
            "action": action,
            "channel": payload.get("channel", "console"),
            "message": payload.get("message", ""),
            "trace_id": payload.get("trace_id"),
            "payload": payload,
        }

    def _handle_clawx(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Bridge to ClawX runtime via HTTP.
        """
        if action not in CLAWX_ALLOWLIST:
            return {
                "status": "error",
                "error": f"Forbidden or unknown ClawX action: {action}",
                "action": action
            }

        if action == "clawx_monitor" and (
            "task_type" in payload or "objective" in payload or "schedule" in payload
        ):
            trace_id = str(payload.get("trace_id", uuid.uuid4()))
            node_id = str(payload.get("graph_node_id", "job")).strip() or "job"
            return {
                "status": "accepted",
                "backend": "ClawX",
                "provider": "clawx",
                "action": action,
                "job_id": f"clawx-{trace_id}-{node_id}",
                "payload": payload,
            }

        bridge = self.config.get("clawx_bridge")
        if not isinstance(bridge, str) or not bridge.strip() or bridge == "mock":
            self.logger.info(f"Routing to ClawX (MOCK): {action}")
            return {
                "status": "dispatched",
                "backend": "ClawX",
                "action": action,
                "payload": payload,
                "context": {"bridge": "mock"}
            }

        # Live HTTP Bridge
        try:
            self.logger.info(f"Posting to ClawX Bridge: {bridge}/{action}")
            response = requests.post(
                f"{bridge.rstrip('/')}/v1/tasks",
                json={
                    "action": action,
                    "payload": payload,
                    "trace_id": payload.get("trace_id")
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "status": "dispatched",
                "backend": "ClawX",
                "action": action,
                "external_id": data.get("id"),
                "context": {"bridge": bridge}
            }
        except Exception as e:
            self.logger.error(f"ClawX Bridge failure: {str(e)}")
            return {
                "status": "failed",
                "error": f"Bridge unreachable: {str(e)}",
                "action": action,
                "backend": "ClawX"
            }
