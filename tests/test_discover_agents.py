import json
from pathlib import Path

from tools import discover_agents


def test_is_executable_python_accepts_main_guard(tmp_path: Path) -> None:
    script = tmp_path / "agent.py"
    script.write_text("if __name__ == '__main__':\n    pass\n", encoding="utf-8")

    assert discover_agents.is_executable_python(script) is True


def test_is_executable_python_rejects_ignored_paths(tmp_path: Path) -> None:
    script = tmp_path / ".git" / "agent.py"
    script.parent.mkdir()
    script.write_text("if __name__ == '__main__':\n    pass\n", encoding="utf-8")

    assert discover_agents.is_executable_python(script) is False


def test_scan_skips_registered_and_duplicate_names(tmp_path: Path) -> None:
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    (root_a / "registered.py").write_text("if __name__ == '__main__':\n    pass\n", encoding="utf-8")
    (root_a / "candidate.py").write_text("if __name__ == '__main__':\n    pass\n", encoding="utf-8")
    (root_b / "candidate.py").write_text("if __name__ == '__main__':\n    pass\n", encoding="utf-8")

    registry_path = tmp_path / "agent_registry.json"
    registry_path.write_text(json.dumps({"registered": {"node": "hades", "entrypoint": "/tmp/registered.py"}}), encoding="utf-8")

    discovered = discover_agents.scan(roots=[root_a, root_b], registry_path=registry_path)

    assert discovered == {
        "candidate": {
            "node": "hades",
            "entrypoint": str(root_a / "candidate.py"),
        }
    }


def test_write_candidates_persists_json(tmp_path: Path) -> None:
    path = tmp_path / "discovered_agents.json"
    discover_agents.write_candidates({"candidate": {"node": "hades", "entrypoint": "/tmp/candidate.py"}}, path=path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["candidate"]["entrypoint"] == "/tmp/candidate.py"
