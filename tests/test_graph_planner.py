import pytest

from hades.capabilities import CapabilityRegistry
from hades.graph_planner import GraphPlanner


def test_planner_actions_are_allowed():
    registry = CapabilityRegistry(
        {
            "actions": {
                "model_infer": {
                    "capabilities": ["analyse", "summarise"],
                    "providers": ["ollama"],
                    "tiers": ["local"],
                    "async": False,
                },
                "notify": {
                    "capabilities": ["notify", "alert"],
                    "providers": ["internal"],
                    "tiers": ["system"],
                    "async": False,
                },
            },
            "models": {"ollama": ["qwen2.5"]},
            "limits": {"max_nodes_per_graph": 5},
            "node_templates": {"analysis_flow": ["analyse", "notify"]},
        }
    )

    planner = GraphPlanner(registry)
    actions = planner._plan_actions("analyze btc")

    assert all(action in registry.allowed_actions() for action in actions)


def test_planner_rejects_invalid_action():
    registry = CapabilityRegistry(
        {
            "actions": {
                "notify": {"providers": ["internal"], "tiers": ["system"], "async": False}
            },
            "models": {},
            "limits": {"max_nodes_per_graph": 5},
        }
    )

    planner = GraphPlanner(registry)

    with pytest.raises(ValueError):
        planner._validate_actions(["model_infer"])


def test_planner_respects_max_nodes():
    registry = CapabilityRegistry(
        {
            "actions": {
                "noop": {"providers": ["internal"], "tiers": ["system"], "async": False}
            },
            "models": {},
            "limits": {"max_nodes_per_graph": 2},
        }
    )

    planner = GraphPlanner(registry)

    with pytest.raises(ValueError):
        planner._validate_actions(["noop", "noop", "noop"])


def test_planner_resolves_semantic_monitor_flow():
    registry = CapabilityRegistry(
        {
            "actions": {
                "clawx_monitor": {
                    "capabilities": ["monitor", "watch"],
                    "providers": ["clawx"],
                    "tiers": ["clawx"],
                    "async": True,
                },
                "model_infer": {
                    "capabilities": ["analyse", "summarise"],
                    "providers": ["ollama"],
                    "tiers": ["local"],
                    "async": False,
                },
                "notify": {
                    "capabilities": ["notify", "alert"],
                    "providers": ["internal"],
                    "tiers": ["system"],
                    "async": False,
                },
            },
            "models": {"ollama": ["qwen2.5"], "clawx": ["clawx-research"]},
            "limits": {"max_nodes_per_graph": 5},
            "node_templates": {"monitor_flow": ["monitor", "analyse", "notify"]},
        }
    )

    planner = GraphPlanner(registry)
    actions = planner._plan_actions("monitor btc funding")

    assert actions == ["clawx_monitor", "model_infer", "notify"]
