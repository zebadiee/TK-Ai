import json
import subprocess
import sys
from pathlib import Path

from memory.obsidian_bridge.entity_writer import EntityWriter


def test_entity_writer_creates_markdown_page(tmp_path: Path) -> None:
    writer = EntityWriter(tmp_path)

    path = writer.write_entity(
        "BTC",
        {
            "aliases": ["bitcoin", "BTCUSDT"],
            "type": "asset",
            "evidence_refs": ["ev-8831"],
            "claim_refs": ["cl-921"],
            "investigation_refs": ["investigate_funding_anomaly_v1"],
            "notes": "Funding anomalies observed.",
        },
    )

    content = path.read_text(encoding="utf-8")
    assert "# BTC" in content
    assert "Type: asset" in content
    assert "- bitcoin" in content
    assert "- [[ev-8831]]" in content
    assert "- [[cl-921]]" in content
    assert "- [[investigate_funding_anomaly_v1]]" in content


def test_sync_entities_to_obsidian_generates_pages(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    registry_dir = tmp_path / "vault" / "entities"
    registry_dir.mkdir(parents=True)
    (registry_dir / "entities.json").write_text(
        json.dumps(
            {
                "BTC": {"aliases": ["bitcoin"], "type": "asset"},
                "BINANCE": {"aliases": ["binance"], "type": "exchange"},
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(repo_root / "tools" / "sync_entities_to_obsidian.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Entities synced to Obsidian" in result.stdout
    assert (tmp_path / "vault" / "research" / "entities" / "BTC.md").exists()
    assert (tmp_path / "vault" / "research" / "entities" / "BINANCE.md").exists()
