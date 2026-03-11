from atlas.providers import ClawXProvider, ProviderRequest, StaticProvider


def test_static_provider_returns_provider_response():
    provider = StaticProvider("local")
    request = ProviderRequest(
        prompt="ping user",
        model="local-small",
        max_tokens=128,
        trace_id="123",
    )

    response = provider.infer(request)

    assert response.provider == "local"
    assert response.model == "local-small"
    assert response.output == "local:local-small:ping user"
    assert response.usage["total_tokens"] >= response.usage["prompt_tokens"]


def test_clawx_provider_mock_returns_provider_response():
    provider = ClawXProvider(bridge="mock")
    request = ProviderRequest(
        prompt="collect filings",
        model="clawx-research",
        max_tokens=256,
        trace_id="123",
    )

    response = provider.infer(request)

    assert response.provider == "clawx"
    assert response.model == "clawx-research"
    assert response.metadata["bridge"] == "mock"
