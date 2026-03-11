from pathlib import Path

from hades.capabilities import CapabilityRegistry


def test_registry_loads_from_json(tmp_path: Path):
    path = tmp_path / "capabilities.json"
    path.write_text(
        """
{
  "actions": {
    "model_infer": {"providers": ["ollama"], "tiers": ["local"], "async": false}
  },
  "models": {"ollama": ["qwen2.5"]},
  "limits": {"max_nodes_per_graph": 5}
}
""".strip()
    )

    registry = CapabilityRegistry.from_path(path)

    assert "model_infer" in registry.allowed_actions()


def test_get_action_capability():
    registry = CapabilityRegistry(
        {
            "actions": {
                "notify": {
                    "capabilities": ["notify", "alert"],
                    "providers": ["internal"],
                    "tiers": ["system"],
                    "async": False,
                }
            },
            "models": {},
            "limits": {},
        }
    )

    action = registry.get_action("notify")

    assert action.name == "notify"
    assert action.async_supported is False
    assert "notify" in action.capabilities


def test_allowed_models():
    registry = CapabilityRegistry(
        {
            "actions": {},
            "models": {"ollama": ["qwen2.5"]},
            "limits": {},
        }
    )

    models = registry.allowed_models("ollama")

    assert "qwen2.5" in models


def test_allowed_capabilities():
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
            },
            "models": {},
            "limits": {},
        }
    )

    capabilities = registry.allowed_capabilities()

    assert "monitor" in capabilities
    assert "alert" in capabilities
