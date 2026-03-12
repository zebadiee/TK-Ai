"""Token-aware model policy for HADES Assist."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from hades.model_router import ModelRouter
from tools.load_cluster_env import get_default_model

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "vault" / "runtime" / "hades_assist_model_metrics.json"

LOW_RISK_SKILLS = {
    "filesystem_inventory",
    "filesystem-inventory",
    "markdown_wiki",
    "fact_lookup",
    "snapshot_state",
    "snapshot-state",
    "time_travel_reader",
    "sync_tkai_knowledge_to_obsidian",
    "sync_entities_to_obsidian",
    "hades_assist_launcher",
}
SOCIAL_MOODS = {"curious", "excited", "pissed", "drunk", "tired", "anxious"}
COMPLEX_KEYWORDS = {
    "architect",
    "reason",
    "analysis",
    "analyze",
    "design",
    "multi-step",
    "plan",
    "strategy",
    "nuanced",
    "promotion",
}

FREE_MODEL_POOLS: dict[str, list[str]] = {
    "code": [
        "qwen/qwen3-coder:free",
        "stepfun/step-3.5-flash:free",
        "openrouter/free",
    ],
    "analysis": [
        "nvidia/nemotron-3-super-120b-a12b:free",
        "stepfun/step-3.5-flash:free",
        "openrouter/free",
    ],
    "chat": [
        "openrouter/free",
        "stepfun/step-3.5-flash:free",
    ],
}


@dataclass(frozen=True)
class HadesAssistRoute:
    backend: str
    model: str
    tier: str
    reason: str
    task_class: str
    max_tokens: int
    max_latency_ms: int
    fallback_chain: list[str]
    provider_order: list[str]
    used_rotation: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_state() -> dict[str, Any]:
    metrics: dict[str, dict[str, float]] = {}
    for model in {candidate for values in FREE_MODEL_POOLS.values() for candidate in values}:
        metrics[model] = {
            "quota_remaining": 1.0,
            "recent_error_rate": 0.0,
            "recent_latency_ms": 800.0,
        }
    return {
        "free_models": metrics,
        "paid_model": "paid-premium",
        "paid_backend": "paid",
    }


def load_policy_state(path: Path = STATE_PATH) -> dict[str, Any]:
    if not path.exists():
        return default_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default_state()
    if not isinstance(data, dict):
        return default_state()
    state = default_state()
    free_models = data.get("free_models")
    if isinstance(free_models, dict):
        for model, metrics in free_models.items():
            if model not in state["free_models"] or not isinstance(metrics, dict):
                continue
            for key in ("quota_remaining", "recent_error_rate", "recent_latency_ms"):
                try:
                    state["free_models"][model][key] = float(metrics.get(key, state["free_models"][model][key]))
                except (TypeError, ValueError):
                    continue
    for key in ("paid_model", "paid_backend"):
        if key in data and isinstance(data[key], str):
            state[key] = data[key]
    return state


def write_policy_state(state: dict[str, Any], path: Path = STATE_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    return path


def classify_task(intent: str, *, skill_name: str | None = None) -> str:
    lowered = intent.lower()
    normalized_skill = (skill_name or "").strip()
    if normalized_skill in LOW_RISK_SKILLS:
        return "low_risk"
    if any(token in lowered for token in ("code", "script", "tool", "skill", "test", "python")):
        return "code"
    if any(token in lowered for token in ("wiki", "fact", "snapshot", "inventory", "obsidian")):
        return "low_risk"
    if any(token in lowered for token in COMPLEX_KEYWORDS):
        return "analysis"
    return "chat"


def requires_paid(
    intent: str,
    *,
    user_mood: str = "focused",
    high_stakes: bool = False,
    production: bool = False,
    task_class: str,
) -> bool:
    lowered = intent.lower()
    if high_stakes or production:
        return True
    if user_mood in SOCIAL_MOODS and task_class not in {"low_risk"}:
        return True
    return any(token in lowered for token in ("multi-step", "deep reasoning", "nuanced", "architecture review"))


def rank_free_models(task_class: str, state: dict[str, Any]) -> list[str]:
    pool_key = "analysis" if task_class == "analysis" else "code" if task_class == "code" else "chat"
    candidates = FREE_MODEL_POOLS[pool_key]

    def score(model: str) -> tuple[float, float, float, str]:
        metrics = state["free_models"].get(model, {})
        quota = float(metrics.get("quota_remaining", 0.0))
        error_rate = float(metrics.get("recent_error_rate", 1.0))
        latency = float(metrics.get("recent_latency_ms", 10_000.0))
        return (-quota, error_rate, latency, model)

    return sorted(candidates, key=score)


def choose_route(
    intent: str,
    *,
    skill_name: str | None = None,
    user_mood: str = "focused",
    high_stakes: bool = False,
    production: bool = False,
    long_running: bool = False,
    high_volume: bool = False,
    state: dict[str, Any] | None = None,
) -> HadesAssistRoute:
    policy_state = state or load_policy_state()
    task_class = classify_task(intent, skill_name=skill_name)

    if task_class == "low_risk" and not high_stakes and not production:
        local_model = get_default_model()
        free_rotation = rank_free_models(task_class, policy_state)
        reason = "low_risk_local_first"
        if long_running or high_volume:
            reason = "low_risk_cost_sensitive"
        return HadesAssistRoute(
            backend="ollama",
            model=local_model,
            tier="local_free",
            reason=reason,
            task_class=task_class,
            max_tokens=512,
            max_latency_ms=2000,
            fallback_chain=free_rotation,
            provider_order=["ollama", "openrouter_free"],
            used_rotation=bool(free_rotation),
        )

    if requires_paid(
        intent,
        user_mood=user_mood,
        high_stakes=high_stakes,
        production=production,
        task_class=task_class,
    ):
        base_route = ModelRouter().resolve(intent, {"requires_paid": True, "payload": {"long_running": long_running}})
        return HadesAssistRoute(
            backend=policy_state["paid_backend"],
            model=policy_state["paid_model"],
            tier="paid",
            reason="high_stakes_or_complex_reasoning",
            task_class=task_class,
            max_tokens=base_route.max_tokens,
            max_latency_ms=base_route.max_latency_ms,
            fallback_chain=rank_free_models(task_class, policy_state),
            provider_order=[policy_state["paid_backend"], "openrouter_free", "ollama"],
            used_rotation=True,
        )

    base_route = ModelRouter().resolve(intent, {"payload": {"long_running": long_running}})
    free_rotation = rank_free_models(task_class, policy_state)
    backend = "openrouter_free" if base_route.backend == "free" else "ollama"
    model = free_rotation[0] if backend == "openrouter_free" else get_default_model()
    return HadesAssistRoute(
        backend=backend,
        model=model,
        tier="free",
        reason="tokenomics_balanced_default",
        task_class=task_class,
        max_tokens=base_route.max_tokens,
        max_latency_ms=base_route.max_latency_ms,
        fallback_chain=free_rotation[1:] if backend == "openrouter_free" else free_rotation,
        provider_order=["ollama", "openrouter_free", "paid"],
        used_rotation=backend == "openrouter_free",
    )


def render_policy_summary(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "free_model_pools": FREE_MODEL_POOLS,
        "paid_backend": state["paid_backend"],
        "paid_model": state["paid_model"],
        "free_model_metrics": state["free_models"],
        "low_risk_skills": sorted(LOW_RISK_SKILLS),
    }
