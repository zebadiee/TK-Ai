"""Mirror canonical entity registry entries into Obsidian markdown pages."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class EntityWriter:
    """Writes entity registry records into Obsidian-friendly markdown pages."""

    def __init__(self, vault: str | Path = "vault/research/entities") -> None:
        self.base = Path(vault)
        self.base.mkdir(parents=True, exist_ok=True)

    def write_entity(self, name: str, data: dict[str, Any]) -> Path:
        path = self.base / f"{name}.md"

        aliases = data.get("aliases", [])
        if not isinstance(aliases, list):
            aliases = []
        alias_lines = "\n".join(f"- {alias}" for alias in aliases) or "- none"

        evidence_refs = self._render_refs(data.get("evidence_refs", []))
        claim_refs = self._render_refs(data.get("claim_refs", []))
        investigation_refs = self._render_refs(data.get("investigation_refs", []))
        notes = str(data.get("notes", "")).strip()

        content = (
            f"# {name}\n\n"
            f"Type: {data.get('type', 'unknown')}\n\n"
            "Aliases\n"
            f"{alias_lines}\n\n"
            "## Evidence\n"
            f"{evidence_refs}\n\n"
            "## Claims\n"
            f"{claim_refs}\n\n"
            "## Investigations\n"
            f"{investigation_refs}\n\n"
            "## Notes\n"
            f"{notes}\n"
        )
        path.write_text(content, encoding="utf-8")
        return path

    def _render_refs(self, refs: list[Any]) -> str:
        if not isinstance(refs, list) or not refs:
            return "- none"
        return "\n".join(f"- [[{ref}]]" for ref in refs if str(ref).strip()) or "- none"
