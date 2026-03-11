import pytest

from hades.capabilities import CapabilityRegistry
from hades.llm_graph_planner import LLMGraphPlanner


def _registry() -> CapabilityRegistry:
    return CapabilityRegistry(
        {
            "actions": {
                "clawx_monitor": {
                    "capabilities": ["monitor", "watch"],
                    "providers": ["clawx"],
                    "tiers": ["clawx"],
                    "async": True,
                },
                "model_infer": {
                    "capabilities": ["analyse", "summarise", "reason"],
                    "providers": ["ollama"],
                    "tiers": ["local"],
                    "async": False,
                },
                "notify": {
                    "capabilities": ["notify", "alert", "deliver"],
                    "providers": ["internal"],
                    "tiers": ["system"],
                    "async": False,
                },
                "noop": {
                    "capabilities": ["noop"],
                    "providers": ["internal"],
                    "tiers": ["system"],
                    "async": False,
                },
            },
            "models": {"ollama": ["qwen2.5"], "clawx": ["clawx-research"]},
            "limits": {"max_nodes_per_graph": 5},
            "node_templates": {
                "analysis_flow": ["analyse", "notify"],
                "monitor_flow": ["monitor", "analyse", "notify"],
            },
        }
    )


def test_llm_planner_builds_graph_from_semantic_steps():
    planner = LLMGraphPlanner(
        _registry(),
        proposer=lambda intent, payload: {"graph_id": "btc-plan", "steps": ["monitor", "analyse", "notify"]},
    )

    graph = planner.plan_graph("monitor btc funding")

    assert graph.graph_id == "btc-plan"
    assert [node.action for node in graph.nodes] == ["clawx_monitor", "model_infer", "notify"]
    assert graph.metadata["planner"] == "llm_constrained"


def test_llm_planner_falls_back_on_invalid_capability():
    planner = LLMGraphPlanner(
        _registry(),
        proposer=lambda intent, payload: {"steps": ["invent", "notify"]},
        fallback_on_invalid=True,
    )

    graph = planner.plan_graph("analyse btc")

    assert graph.metadata["planner"] == "deterministic"
    assert [node.action for node in graph.nodes] == ["model_infer", "notify"]


def test_llm_planner_rejects_oversized_plan_without_fallback():
    planner = LLMGraphPlanner(
        CapabilityRegistry(
            {
                "actions": {
                    "noop": {
                        "capabilities": ["noop"],
                        "providers": ["internal"],
                        "tiers": ["system"],
                        "async": False,
                    }
                },
                "limits": {"max_nodes_per_graph": 2},
            }
        ),
        proposer=lambda intent, payload: {"steps": ["noop", "noop", "noop"]},
        fallback_on_invalid=False,
    )

    with pytest.raises(ValueError):
        planner.plan_graph("noop plan")
