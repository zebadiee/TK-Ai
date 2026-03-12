import subprocess
import sys
from pathlib import Path

from hades.graph_registry import GraphRegistry
from hades.task_graph import load_solution_graphs
from hades.triggers import load_trigger_rules

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_basic_run_script_executes_end_to_end() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "examples" / "basic_run.py")],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0
    assert "trigger_result:" in result.stdout
    assert '"status": "accepted"' in result.stdout
    assert "resume_result:" in result.stdout
    assert '"status": "ok"' in result.stdout
    assert "acme_btc_funding_watch_v1" in result.stdout


def test_acme_ai_pack_loads_with_registry_and_triggers() -> None:
    pack_root = REPO_ROOT / "examples" / "acme_ai"
    graphs = load_solution_graphs(pack_root / "solution_graph.json")
    registry = GraphRegistry.from_paths(pack_root / "graph_index.json", pack_root / "solution_graphs")
    triggers = load_trigger_rules(pack_root / "triggers.json")

    assert "acme_btc_funding_watch" in graphs
    assert registry.resolve("acme_btc_funding_watch").graph_id == "acme_btc_funding_watch_v1"
    assert triggers[0].graph_id == "acme_btc_funding_watch"
