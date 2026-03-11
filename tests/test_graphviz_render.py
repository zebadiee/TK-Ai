"""Tests for the graph visualiser tool."""
import json
import subprocess
import sys
from pathlib import Path

TOOL_PATH = Path(__file__).resolve().parents[1] / "tools" / "graphviz_render.py"


def _make_graph_file(tmp_path: Path) -> Path:
    graph_file = tmp_path / "test_graph.json"
    graph_file.write_text(json.dumps({
        "graphs": {
            "demo": {
                "metadata": {"purpose": "test"},
                "nodes": [
                    {"node_id": "step_a", "action": "clawx_monitor", "payload": {}},
                    {"node_id": "step_b", "action": "model_infer", "payload": {}},
                    {"node_id": "step_c", "action": "notify", "payload": {}}
                ]
            }
        }
    }))
    return graph_file


def test_ascii_output(tmp_path: Path) -> None:
    graph_file = _make_graph_file(tmp_path)
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), str(graph_file), "--format", "ascii"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "step_a" in result.stdout
    assert "step_b" in result.stdout
    assert "step_c" in result.stdout


def test_mermaid_output(tmp_path: Path) -> None:
    graph_file = _make_graph_file(tmp_path)
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), str(graph_file), "--format", "mermaid"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "flowchart TD" in result.stdout
    assert "step_a --> step_b" in result.stdout
    assert "step_b --> step_c" in result.stdout


def test_dot_output(tmp_path: Path) -> None:
    graph_file = _make_graph_file(tmp_path)
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), str(graph_file), "--format", "dot"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "digraph demo" in result.stdout
    assert "step_a -> step_b" in result.stdout


def test_output_to_file(tmp_path: Path) -> None:
    graph_file = _make_graph_file(tmp_path)
    out_file = tmp_path / "output.md"
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), str(graph_file), "--format", "mermaid", "--output", str(out_file)],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert out_file.exists()
    content = out_file.read_text()
    assert "flowchart TD" in content
