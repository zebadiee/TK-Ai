import requests
import pytest
from atlas.executor import AtlasExecutor

def test_executor_noop_status():
    executor = AtlasExecutor()
    result = executor.execute('noop', {'data': 1})
    assert result['status'] == 'ignored'
    assert result['action'] == 'noop'

def test_executor_ok_status_for_other_actions():
    executor = AtlasExecutor()
    result = executor.execute('any_action', {'data': 1})
    assert result['status'] == 'ok'
    assert result['action'] == 'any_action'

def test_executor_forbids_unknown_clawx_action():
    executor = AtlasExecutor()
    result = executor.execute('clawx_hacker_access', {})
    assert result['status'] == 'error'
    assert 'Forbidden' in result['error']

def test_executor_bridge_fallback():
    # Test fallback to mock when config is missing
    executor = AtlasExecutor(config={})
    result = executor.execute('clawx_monitor', {})
    assert result['context']['bridge'] == 'mock'
    
    # Test explicit mock bridge
    executor_mock = AtlasExecutor(config={'clawx_bridge': 'mock'})
    result_mock = executor_mock.execute('clawx_monitor', {})
    assert result_mock['context']['bridge'] == 'mock'

def test_executor_http_bridge_failure():
    # Use a non-existent local port to trigger connection error
    executor = AtlasExecutor(config={'clawx_bridge': 'http://localhost:59999'})
    result = executor.execute('clawx_monitor', {'trace_id': '123'})
    
    assert result['status'] == 'failed'
    assert 'Bridge unreachable' in result['error']
    assert result['backend'] == 'ClawX'


def test_executor_model_route_returns_backend_details():
    executor = AtlasExecutor()
    result = executor.execute(
        'model_infer',
        {
            'trace_id': '123',
            'model_route': {
                'backend': 'free',
                'model': 'free-standard',
                'max_tokens': 512,
                'max_latency_ms': 3000,
            },
        },
    )

    assert result['status'] == 'ok'
    assert result['backend'] == 'Model'
    assert result['model_backend'] == 'free'
    assert result['model'] == 'free-standard'
    assert result['output'] == 'free:free-standard:123'


def test_executor_model_route_uses_clawx_provider():
    executor = AtlasExecutor(config={'clawx_bridge': 'mock'})
    result = executor.execute(
        'model_infer',
        {
            'trace_id': '123',
            'prompt': 'collect filings',
            'model_route': {
                'backend': 'clawx',
                'model': 'clawx-research',
                'max_tokens': 256,
                'max_latency_ms': 5000,
            },
        },
    )

    assert result['status'] == 'ok'
    assert result['backend'] == 'Model'
    assert result['model_backend'] == 'clawx'
    assert result['provider_metadata']['bridge'] == 'mock'


def test_executor_clawx_monitor_accepts_async_job_payload():
    executor = AtlasExecutor(config={'clawx_bridge': 'mock'})
    result = executor.execute(
        'clawx_monitor',
        {
            'trace_id': '123',
            'graph_node_id': 'monitor',
            'task_type': 'monitor',
            'objective': 'monitor sec filings',
            'schedule': {'every': '15m'},
        },
    )

    assert result['status'] == 'accepted'
    assert result['action'] == 'clawx_monitor'
    assert result['job_id'] == 'clawx-123-monitor'


def test_executor_notify_placeholder():
    executor = AtlasExecutor()
    result = executor.execute(
        'notify',
        {'channel': 'telegram', 'message': 'alert ready', 'trace_id': '123'},
    )

    assert result['status'] == 'ok'
    assert result['backend'] == 'Notify'
    assert result['channel'] == 'telegram'
