from __future__ import annotations
from pathlib import Path
from atlas.executor import AtlasExecutor
from hades.kernel import HadesKernel
from hades.router import Router

class MockAthena:
    def __init__(self, intents):
        self.intents = intents
        self.current = 0
    def get_next_intent(self):
        val = self.intents[self.current % len(self.intents)]
        self.current += 1
        return val

def test_clawx_rich_contract_routing(tmp_path: Path):
    # Setup kernel with ClawX routes and MOCK bridge
    state_path = tmp_path / "state.json"
    index_path = tmp_path / "index.json"
    athena = MockAthena([
        {"intent": "monitor_sec_filings", "payload": {"symbol": "AAPL", "interval": "15m"}},
        {"intent": "push_bulletin", "payload": {"channel": "telegram", "text": "Alert"}}
    ])
    
    router = Router(routes={
        "monitor_sec_filings": "clawx_monitor",
        "push_bulletin": "clawx_push"
    })
    
    executor = AtlasExecutor(config={"clawx_bridge": "mock"})
    kernel = HadesKernel(athena, router, executor, state_path, index_path)
    
    # Tick 1: Monitor
    result1 = kernel.tick()
    assert result1["status"] == "dispatched"
    
    # Verify structured state
    assert "trace_id" in kernel.state["events"][0]
    assert "latency_ms" in kernel.state["events"][0]
