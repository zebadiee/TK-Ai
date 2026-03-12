import json
from pathlib import Path

from ct.skills import agent_classifier, cluster_cartographer, skill_classifier


def test_cluster_cartographer_scans_files(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    file_path = root / "tool.py"
    file_path.write_text("print('ok')\n", encoding="utf-8")

    records = cluster_cartographer.scan(scan_roots=[root], node="atlas")

    assert records == [
        {
            "node": "atlas",
            "path": str(file_path),
            "type": ".py",
            "size": len("print('ok')\n"),
        }
    ]


def test_cluster_cartographer_skips_ignored_directories(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    git_dir = root / ".git"
    git_dir.mkdir(parents=True)
    ignored_file = git_dir / "config"
    ignored_file.write_text("[core]\n", encoding="utf-8")

    records = cluster_cartographer.scan(scan_roots=[root], node="atlas")

    assert records == []


def test_cluster_cartographer_write_map_deduplicates_by_node_and_path(tmp_path: Path) -> None:
    output = tmp_path / "cluster_map.json"
    output.write_text(
        json.dumps([{"node": "atlas", "path": "/tmp/a.py", "type": ".py", "size": 1}]),
        encoding="utf-8",
    )

    cluster_cartographer.write_map(
        [
            {"node": "atlas", "path": "/tmp/a.py", "type": ".py", "size": 2},
            {"node": "hades", "path": "/tmp/b.sh", "type": ".sh", "size": 3},
        ],
        output=output,
    )

    records = json.loads(output.read_text(encoding="utf-8"))
    assert records == [
        {"node": "atlas", "path": "/tmp/a.py", "type": ".py", "size": 2},
        {"node": "hades", "path": "/tmp/b.sh", "type": ".sh", "size": 3},
    ]


def test_cluster_cartographer_write_map_filters_stale_ignored_entries(tmp_path: Path) -> None:
    output = tmp_path / "cluster_map.json"
    output.write_text(
        json.dumps(
            [
                {"node": "atlas", "path": "/tmp/work/.git/config", "type": "", "size": 1},
                {"node": "atlas", "path": "/tmp/work/tool.py", "type": ".py", "size": 2},
            ]
        ),
        encoding="utf-8",
    )

    cluster_cartographer.write_map([], output=output)

    records = json.loads(output.read_text(encoding="utf-8"))
    assert records == [{"node": "atlas", "path": "/tmp/work/tool.py", "type": ".py", "size": 2}]


def test_skill_classifier_finds_python_skills(tmp_path: Path) -> None:
    map_path = tmp_path / "cluster_map.json"
    map_path.write_text(
        json.dumps(
            [
                {"node": "atlas", "path": "/tmp/tool.py", "type": ".py", "size": 10},
                {"node": "atlas", "path": "/tmp/readme.md", "type": ".md", "size": 10},
            ]
        ),
        encoding="utf-8",
    )

    skills = skill_classifier.classify(map_path=map_path)

    assert skills == [
        {"node": "atlas", "path": "/tmp/tool.py", "type": "python_skill"},
    ]


def test_agent_classifier_finds_agent_entrypoints(tmp_path: Path) -> None:
    map_path = tmp_path / "cluster_map.json"
    map_path.write_text(
        json.dumps(
            [
                {"node": "hades", "path": "/tmp/tkai_investigation_daemon.py", "type": ".py", "size": 10},
                {"node": "hades", "path": "/tmp/helper.py", "type": ".py", "size": 10},
            ]
        ),
        encoding="utf-8",
    )

    agents = agent_classifier.classify(map_path=map_path)

    assert agents == [
        {
            "name": "tkai_investigation_daemon",
            "node": "hades",
            "entrypoint": "/tmp/tkai_investigation_daemon.py",
            "type": "python_agent",
        }
    ]
