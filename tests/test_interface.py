from athena.interface import AthenaInterface

def test_interface_returns_default_intent():
    interface = AthenaInterface()
    message = interface.get_next_intent()
    assert message == {'intent': 'noop', 'payload': {}}
