"""TK-Ai Graph Visualiser.

Renders TaskGraph definitions as Mermaid, ASCII, or DOT diagrams.

Usage:
    python tools/graphviz_render.py vault/solution_graph.json
    python tools/graphviz_render.py vault/solution_graph.json --format mermaid
    python tools/graphviz_render.py vault/solution_graph.json --format ascii
    python tools/graphviz_render.py vault/solution_graph.json --format dot
    python tools/graphviz_render.py vault/solution_graph.json --output docs/graphs.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_graphs(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "graphs" in data:
        return data["graphs"]
    if "nodes" in data:
        graph_id = Path(path).stem
        return {graph_id: data}
    return {}


def render_ascii(graph_id: str, nodes: list[dict[str, Any]]) -> str:
    lines = [f"=== {graph_id} ===", ""]
    max_width = max((len(n.get("node_id", "?")) for n in nodes), default=4)
    
    for i, node in enumerate(nodes):
        node_id = node.get("node_id", "?")
        action = node.get("action", "?")
        label = f"  [{node_id}] → {action}"
        lines.append(label)
        if i < len(nodes) - 1:
            lines.append("      ↓")
    
    lines.append("")
    return "\n".join(lines)


def render_mermaid(graph_id: str, nodes: list[dict[str, Any]]) -> str:
    lines = [
        "flowchart TD",
        f"    subgraph {graph_id}[{graph_id}]",
    ]

    for node in nodes:
        node_id = node.get("node_id", "?")
        action = node.get("action", "?")
        lines.append(f'        {node_id}["{node_id}<br/>{action}"]')

    lines.append("    end")

    for i in range(len(nodes) - 1):
        src = nodes[i].get("node_id", "?")
        dst = nodes[i + 1].get("node_id", "?")
        lines.append(f"    {src} --> {dst}")

    return "\n".join(lines)


def render_dot(graph_id: str, nodes: list[dict[str, Any]]) -> str:
    lines = [
        f"digraph {graph_id} {{",
        "    rankdir=TB;",
        "    node [shape=box, style=rounded, fontname=\"Helvetica\"];",
        "",
    ]
    
    for node in nodes:
        nid = node.get("node_id", "?")
        action = node.get("action", "?")
        lines.append(f"    {nid} [label=\"{nid}\\n({action})\"];")
    
    for i in range(len(nodes) - 1):
        src = nodes[i].get("node_id", "?")
        dst = nodes[i + 1].get("node_id", "?")
        lines.append(f"    {src} -> {dst};")
    
    lines.append("}")
    return "\n".join(lines)


RENDERERS = {
    "ascii": render_ascii,
    "mermaid": render_mermaid,
    "dot": render_dot,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="TK-Ai Graph Visualiser")
    parser.add_argument("input", help="Path to solution graph JSON file")
    parser.add_argument("--format", choices=RENDERERS.keys(), default="ascii",
                        help="Output format (default: ascii)")
    parser.add_argument("--output", help="Write output to file instead of stdout")
    parser.add_argument("--graph", help="Render only this graph ID")
    
    args = parser.parse_args()
    graphs = load_graphs(args.input)
    
    if not graphs:
        print("No graphs found.", file=sys.stderr)
        sys.exit(1)
    
    renderer = RENDERERS[args.format]
    output_parts = []
    
    for graph_id, graph_data in graphs.items():
        if args.graph and graph_id != args.graph:
            continue
        nodes = graph_data.get("nodes", [])
        if not nodes:
            continue
        output_parts.append(renderer(graph_id, nodes))
    
    result = "\n".join(output_parts)
    
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(result, encoding="utf-8")
        print(f"Written to {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()
