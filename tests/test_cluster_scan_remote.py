import json
from pathlib import Path

from ct.skills import cluster_scan_remote, export_cluster_to_obsidian, promote_agents


class StubResult:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout


def test_fetch_remote_scan_parses_remote_json(monkeypatch) -> None:
    payload = json.dumps([{"node": "atlas", "path": "/tmp/tool.py", "type": ".py", "size": 10}])
    monkeypatch.setattr(
        "ct.skills.cluster_scan_remote.subprocess.run",
        lambda *args, **kwargs: StubResult(payload),
    )

    records = cluster_scan_remote.fetch_remote_scan("atlas", script="~/tool.py")

    assert records == [{"node": "atlas", "path": "/tmp/tool.py", "type": ".py", "size": 10}]


def test_promote_agents_merges_candidates_into_registry(tmp_path: Path) -> None:
    candidates_path = tmp_path / "agent_candidates.json"
    registry_path = tmp_path / "agent_registry.json"
    candidates_path.write_text(
        json.dumps(
            [
                {
                    "name": "cluster_doctor",
                    "node": "hades",
                    "entrypoint": "/tmp/tools/cluster_doctor.py",
                    "type": "python_agent",
                }
            ]
        ),
        encoding="utf-8",
    )
    registry_path.write_text(json.dumps({"existing": {"node": "atlas", "entrypoint": "/tmp/old.py"}}), encoding="utf-8")

    registry = promote_agents.promote_agents(candidates_path=candidates_path, registry_path=registry_path)

    assert registry["existing"]["node"] == "atlas"
    assert registry["cluster_doctor"] == {
        "node": "hades",
        "entrypoint": "/tmp/tools/cluster_doctor.py",
    }


def test_export_cluster_map_writes_grouped_markdown(tmp_path: Path) -> None:
    map_path = tmp_path / "cluster_map.json"
    out_path = tmp_path / "ClusterMap.md"
    map_path.write_text(
        json.dumps(
            [
                {"node": "atlas", "path": "/a/tool.py"},
                {"node": "hades", "path": "/b/doctor.py"},
            ]
        ),
        encoding="utf-8",
    )

    export_cluster_to_obsidian.export_cluster_map(map_path=map_path, out_path=out_path)

    content = out_path.read_text(encoding="utf-8")
    assert "# ClawX Cluster Map" in content
    assert "## atlas" in content
    assert "- `/a/tool.py`" in content
