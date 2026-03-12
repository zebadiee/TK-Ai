from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_sync_tkai_knowledge_to_obsidian_cli(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    vault_root = tmp_path / "vault"
    (repo_root / "tools").mkdir(parents=True)
    (repo_root / "docs").mkdir()
    (repo_root / "var" / "inventory" / "canonical-projects").mkdir(parents=True)

    (repo_root / "tools" / "cluster_doctor.py").write_text('"""Inspect the cluster health."""\n', encoding="utf-8")
    (repo_root / "docs" / "TKAI_CLUSTER_ARCHITECTURE.md").write_text("# Cluster Architecture\n", encoding="utf-8")
    (repo_root / "var" / "inventory" / "canonical-projects" / "INDEX.md").write_text("# Canonical Inventory\n", encoding="utf-8")

    script = Path(__file__).resolve().parents[1] / "tools" / "sync_tkai_knowledge_to_obsidian.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--repo-root",
            str(repo_root),
            "--vault-root",
            str(vault_root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "TK-Ai knowledge synced to Obsidian" in result.stdout
    assert (vault_root / "INDEX.md").exists()
    assert (vault_root / "Tools" / "cluster_doctor.md").exists()
