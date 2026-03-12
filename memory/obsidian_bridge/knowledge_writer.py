"""Mirror TK-Ai architecture and tool knowledge into Obsidian markdown notes."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any


class KnowledgeWriter:
    """Write a structured TK-Ai knowledge surface into an Obsidian vault."""

    def __init__(self, vault_root: str | Path = "~/Obsidian/TK-Ai") -> None:
        self.base = Path(vault_root).expanduser()
        self.base.mkdir(parents=True, exist_ok=True)

    def write_note(self, relative_path: str | Path, content: str) -> Path:
        path = self.base / Path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        normalized = content.rstrip() + "\n"
        path.write_text(normalized, encoding="utf-8")
        return path

    def mirror_markdown(self, source_path: Path, relative_path: str | Path) -> Path | None:
        if not source_path.exists() or not source_path.is_file():
            return None
        content = source_path.read_text(encoding="utf-8", errors="ignore")
        return self.write_note(relative_path, content)


def module_summary(path: Path) -> str:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return "No module summary available."
    docstring = ast.get_docstring(tree)
    if not docstring:
        return "No module summary available."
    first_line = next((line.strip() for line in docstring.splitlines() if line.strip()), "")
    return first_line or "No module summary available."


def discover_tool_records(tools_dir: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    if not tools_dir.exists():
        return records

    for path in sorted(tools_dir.glob("*.py")):
        records.append(
            {
                "name": path.stem,
                "filename": path.name,
                "summary": module_summary(path),
                "command": f"python tools/{path.name}",
                "source_path": str(path),
            }
        )
    return records


def render_tool_note(record: dict[str, str]) -> str:
    return (
        f"# {record['name']}\n\n"
        f"Command: `{record['command']}`\n\n"
        f"Summary: {record['summary']}\n\n"
        "## Source\n"
        f"- `{record['source_path']}`\n"
    )


def render_tools_index(records: list[dict[str, str]]) -> str:
    lines = [
        "# TK-Ai Tools Index",
        "",
        f"Total tools: {len(records)}",
        "",
    ]
    if not records:
        lines.append("No tools discovered.")
        return "\n".join(lines)

    for record in records:
        lines.append(f"- [[Tools/{record['name']}|{record['name']}]] - {record['summary']}")
    return "\n".join(lines)


def load_snapshot_records(snapshot_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not snapshot_root.exists():
        return records

    for path in sorted((item for item in snapshot_root.iterdir() if item.is_dir()), key=lambda item: item.name, reverse=True):
        manifest_path = path / "manifest.json"
        manifest: dict[str, Any] = {}
        if manifest_path.exists():
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = {}
            if isinstance(data, dict):
                manifest = data
        records.append(
            {
                "name": path.name,
                "label": manifest.get("label") or "-",
                "generated_at": manifest.get("generated_at") or "-",
            }
        )
    return records


def render_snapshot_index(records: list[dict[str, Any]]) -> str:
    lines = ["# TK-Ai Snapshots", ""]
    if not records:
        lines.append("No snapshots captured yet.")
        return "\n".join(lines)

    lines.extend(
        [
            "These snapshots freeze the kernel knowledge surface for time-travel reads.",
            "",
        ]
    )
    for record in records:
        lines.append(
            f"- `{record['name']}` - label={record['label']} generated_at={record['generated_at']}"
        )
    return "\n".join(lines)


def render_growth_focus(repo_root: Path, tool_records: list[dict[str, str]], snapshot_records: list[dict[str, Any]]) -> str:
    docs_dir = repo_root / "docs"
    has_acme = (docs_dir / "ACME_TKAI_INTERFACE.md").exists()
    has_snapshot = (docs_dir / "TKAI_SNAPSHOT_TIME_TRAVEL.md").exists()
    has_cluster = (docs_dir / "TKAI_CLUSTER_ARCHITECTURE.md").exists()
    lines = [
        "# TK-Ai Growth Focus",
        "",
        "TK-Ai is the kernel focus. Growth should reinforce the control plane instead of scattering logic across lineage repos.",
        "",
        "## Current Features",
        f"- Tool surface indexed: {len(tool_records)} scripts",
        f"- Snapshot memory active: {'yes' if has_snapshot else 'no'}",
        f"- Cluster architecture canonized: {'yes' if has_cluster else 'no'}",
        f"- ACME integration canonized: {'yes' if has_acme else 'no'}",
        f"- Frozen snapshots captured: {len(snapshot_records)}",
        "",
        "## Growth Priorities",
        "- Keep TK-Ai as the cluster control plane and operator entry.",
        "- Use Obsidian as the human-readable architecture mirror.",
        "- Grow agents behind deterministic registry, policy, and evidence surfaces.",
        "- Prefer snapshot-backed historical queries over current-head reconstruction.",
        "- Formalize repo authority boundaries so growth does not duplicate control logic.",
    ]
    return "\n".join(lines)


def render_index(tool_records: list[dict[str, str]], snapshot_records: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# TK-Ai Knowledge Hub",
            "",
            "This Obsidian surface mirrors the current TK-Ai kernel architecture, operator tools, inventories, and frozen snapshots.",
            "",
            "## Core Notes",
            "- [[Architecture/TKAI_CLUSTER_ARCHITECTURE]]",
            "- [[Architecture/ACME_TKAI_INTERFACE]]",
            "- [[Architecture/TKAI_SNAPSHOT_TIME_TRAVEL]]",
            "- [[Architecture/HADES_ASSIST_MODEL_POLICY]]",
            "- [[Operations/TOOLS_INDEX]]",
            "- [[Knowledge/CANONICAL_PROJECT_INVENTORY]]",
            "- [[Knowledge/TKAI_GROWTH_FOCUS]]",
            "- [[Knowledge/SNAPSHOTS]]",
            "",
            "## Status",
            f"- tools indexed: {len(tool_records)}",
            f"- snapshots indexed: {len(snapshot_records)}",
        ]
    )


def sync_tkai_knowledge(repo_root: Path, vault_root: Path) -> list[Path]:
    writer = KnowledgeWriter(vault_root)
    written: list[Path] = []

    tools_dir = repo_root / "tools"
    docs_dir = repo_root / "docs"
    inventory_dir = repo_root / "var" / "inventory" / "canonical-projects"
    snapshots_dir = repo_root / "snapshots"

    doc_exports = {
        "Architecture/TKAI_CLUSTER_ARCHITECTURE.md": docs_dir / "TKAI_CLUSTER_ARCHITECTURE.md",
        "Architecture/ACME_TKAI_INTERFACE.md": docs_dir / "ACME_TKAI_INTERFACE.md",
        "Architecture/TKAI_SNAPSHOT_TIME_TRAVEL.md": docs_dir / "TKAI_SNAPSHOT_TIME_TRAVEL.md",
        "Architecture/HADES_ASSIST_MODEL_POLICY.md": docs_dir / "HADES_ASSIST_MODEL_POLICY.md",
        "Architecture/CLUSTER_SSH_CONNECTIVITY.md": docs_dir / "CLUSTER_SSH_CONNECTIVITY.md",
        "Operations/SSH_SETUP.md": repo_root / "SSH_SETUP.md",
        "Operations/CLUSTER_STATUS.md": repo_root / "CLUSTER_STATUS.md",
        "Knowledge/CANONICAL_PROJECT_INVENTORY.md": inventory_dir / "INDEX.md",
    }

    for relative_path, source_path in doc_exports.items():
        note = writer.mirror_markdown(source_path, relative_path)
        if note is not None:
            written.append(note)

    tool_records = discover_tool_records(tools_dir)
    for record in tool_records:
        written.append(writer.write_note(f"Tools/{record['name']}.md", render_tool_note(record)))
    written.append(writer.write_note("Operations/TOOLS_INDEX.md", render_tools_index(tool_records)))

    snapshot_records = load_snapshot_records(snapshots_dir)
    written.append(writer.write_note("Knowledge/SNAPSHOTS.md", render_snapshot_index(snapshot_records)))
    written.append(writer.write_note("Knowledge/TKAI_GROWTH_FOCUS.md", render_growth_focus(repo_root, tool_records, snapshot_records)))
    written.append(writer.write_note("INDEX.md", render_index(tool_records, snapshot_records)))

    return written
