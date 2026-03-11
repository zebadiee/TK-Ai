from hades.capabilities import CapabilityRegistry
from hades.semantic_capabilities import SemanticCapabilityIndex


def test_semantic_capability_resolves_matching_actions():
    registry = CapabilityRegistry(
        {
            "actions": {
                "clawx_monitor": {
                    "capabilities": ["monitor", "watch"],
                    "providers": ["clawx"],
                    "tiers": ["clawx"],
                    "async": True,
                },
                "notify": {
                    "capabilities": ["notify", "alert"],
                    "providers": ["internal"],
                    "tiers": ["system"],
                    "async": False,
                },
            }
        }
    )

    index = SemanticCapabilityIndex(registry)

    assert index.resolve("monitor") == ["clawx_monitor"]


def test_semantic_capability_prefers_async_monitor_action():
    registry = CapabilityRegistry(
        {
            "actions": {
                "clawx_monitor": {
                    "capabilities": ["monitor"],
                    "providers": ["clawx"],
                    "tiers": ["clawx"],
                    "async": True,
                },
                "model_infer": {
                    "capabilities": ["monitor", "analyse"],
                    "providers": ["ollama"],
                    "tiers": ["local"],
                    "async": False,
                },
            }
        }
    )

    index = SemanticCapabilityIndex(registry)

    assert index.resolve_best("monitor") == "clawx_monitor"
