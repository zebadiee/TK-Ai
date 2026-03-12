from __future__ import annotations

from hades import hades_assist_model_policy


def test_low_risk_skill_prefers_local_with_free_fallback(monkeypatch) -> None:
    monkeypatch.setattr(hades_assist_model_policy, "get_default_model", lambda: "mistral")

    route = hades_assist_model_policy.choose_route(
        "sync the obsidian knowledge index",
        skill_name="snapshot-state",
    )

    assert route.backend == "ollama"
    assert route.model == "mistral"
    assert route.reason == "low_risk_local_first"
    assert route.fallback_chain


def test_complex_reasoning_or_production_escalates_to_paid(monkeypatch) -> None:
    monkeypatch.setattr(hades_assist_model_policy, "get_default_model", lambda: "mistral")

    route = hades_assist_model_policy.choose_route(
        "perform a nuanced multi-step architecture review",
        user_mood="excited",
        production=True,
    )

    assert route.tier == "paid"
    assert route.backend == "paid"
    assert route.reason == "high_stakes_or_complex_reasoning"


def test_free_rotation_prefers_best_quota_low_error_model(monkeypatch) -> None:
    monkeypatch.setattr(hades_assist_model_policy, "get_default_model", lambda: "mistral")
    state = hades_assist_model_policy.default_state()
    state["free_models"]["openrouter/free"]["quota_remaining"] = 0.2
    state["free_models"]["stepfun/step-3.5-flash:free"]["quota_remaining"] = 0.8
    state["free_models"]["stepfun/step-3.5-flash:free"]["recent_error_rate"] = 0.01
    state["free_models"]["nvidia/nemotron-3-super-120b-a12b:free"]["quota_remaining"] = 0.9
    state["free_models"]["nvidia/nemotron-3-super-120b-a12b:free"]["recent_error_rate"] = 0.0

    route = hades_assist_model_policy.choose_route(
        "analyze the cluster governance surface",
        state=state,
    )

    assert route.backend == "openrouter_free"
    assert route.model == "nvidia/nemotron-3-super-120b-a12b:free"
    assert route.used_rotation is True
