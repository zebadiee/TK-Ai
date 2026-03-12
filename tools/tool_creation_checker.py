#!/usr/bin/env python3
"""Validate governed skill structure before catalogue or promotion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    metadata: dict[str, str] = {}
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        key, sep, value = stripped.partition(":")
        if not sep:
            continue
        metadata[key.strip()] = value.strip()
    return metadata


def check_skill(skill_dir: Path) -> dict[str, Any]:
    skill_path = skill_dir / "SKILL.md"
    errors: list[str] = []
    warnings: list[str] = []

    if not skill_path.exists():
        return {
            "skill": skill_dir.name,
            "path": str(skill_dir),
            "valid": False,
            "errors": ["missing SKILL.md"],
            "warnings": [],
        }

    text = skill_path.read_text(encoding="utf-8")
    metadata = parse_frontmatter(text)
    if not metadata.get("name"):
        errors.append("missing frontmatter name")
    if not metadata.get("description"):
        errors.append("missing frontmatter description")
    if text.strip().count("\n") < 3:
        errors.append("skill body is too small")

    agent_yaml = skill_dir / "agents" / "openai.yaml"
    if not agent_yaml.exists():
        warnings.append("missing agents/openai.yaml")

    return {
        "skill": metadata.get("name", skill_dir.name),
        "path": str(skill_dir),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def scan_skills(skills_root: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if not skills_root.exists():
        return results
    for child in sorted(skills_root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        results.append(check_skill(child))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate one skill or an entire skills root")
    parser.add_argument("path", type=Path, help="Skill directory or skills root")
    args = parser.parse_args()

    path = args.path.expanduser()
    if (path / "SKILL.md").exists():
        print(json.dumps(check_skill(path), indent=2, sort_keys=True))
        return 0

    print(json.dumps(scan_skills(path), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
