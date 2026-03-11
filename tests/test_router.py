from hades.router import Router

def test_router_resolves_known_intent():
    router = Router(routes={'ping': 'pong'})
    assert router.resolve('ping') == 'pong'

def test_router_returns_noop_for_unknown_intent():
    router = Router(routes={'ping': 'pong'})
    assert router.resolve('missing') == 'noop'

def test_router_default_routes_is_empty():
    router = Router()
    assert router.resolve('any') == 'noop'
