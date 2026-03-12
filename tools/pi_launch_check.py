#!/usr/bin/env python3
"""Pi launch-condition checker.

Verifies every precondition in the SM2 contract and prints a status report.
Exit 0 = all conditions met, exit 1 = one or more failures.

Usage:
    python tools/pi_launch_check.py
    python tools/pi_launch_check.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MANIFEST = ROOT / "hades" / "assistant_manifest.md"
OBSIDIAN_SKILLS_INDEX = Path("~/Obsidian/TK-Ai/Skills/Index.md").expanduser()
OBSIDIAN_SKILLS_DIR = Path("~/Obsidian/TK-Ai/Skills").expanduser()
TKAI_ROOT = ROOT
ACME_ROOT = Path("~/ACME-AI").expanduser()
GATEWAY = ROOT / "gateway" / "hermes_api.py"


def check_manifest() -> tuple[bool, str]:
    if MANIFEST.exists():
        text = MANIFEST.read_text(encoding="utf-8")
        if "## Allowed Skills" in text:
            return True, f"Manifest present and contains skill table ({MANIFEST})"
    return False, f"Manifest missing or malformed ({MANIFEST})"


def check_skills() -> tuple[bool, str]:
    from hades.skill_resolver import resolve_skills
    skills = resolve_skills(MANIFEST)
    if not skills:
        return False, "No skills resolved from manifest"
    names = sorted(skills.keys())
    return True, f"{len(skills)} skills resolved: {', '.join(names)}"


def check_tkai_reachable() -> tuple[bool, str]:
    signals = TKAI_ROOT / "vault" / "runtime" / "signals.jsonl"
    evidence = TKAI_ROOT / "vault" / "evidence" / "evidence.jsonl"
    ok = signals.exists() and evidence.exists()
    return ok, f"TK-Ai signals={signals.exists()}, evidence={evidence.exists()}"


def check_acme_reachable() -> tuple[bool, str]:
    ok = ACME_ROOT.exists() and (ACME_ROOT / "acme_ai").is_dir()
    return ok, f"ACME-AI root={ACME_ROOT.exists()}, acme_ai pkg={'yes' if (ACME_ROOT / 'acme_ai').is_dir() else 'no'}"


def check_obsidian() -> tuple[bool, str]:
    index_ok = OBSIDIAN_SKILLS_INDEX.exists()
    dir_ok = OBSIDIAN_SKILLS_DIR.is_dir()
    ok = index_ok and dir_ok
    return ok, f"Obsidian Skills/Index.md={index_ok}, Skills dir={dir_ok}"


def check_model_routing() -> tuple[bool, str]:
    try:
        from hades.hades_assist_model_policy import choose_route
        route = choose_route("test probe", user_mood="focused")
        return True, f"Model routing OK: tier={route.tier}, backend={route.backend}"
    except Exception as exc:
        return False, f"Model routing failed: {exc}"


def check_pi_endpoint() -> tuple[bool, str]:
    if not GATEWAY.exists():
        return False, "gateway/hermes_api.py not found"
    text = GATEWAY.read_text(encoding="utf-8")
    if '"/pi"' in text or "'/pi'" in text:
        return True, "/pi endpoint wired in gateway/hermes_api.py"
    return False, "/pi endpoint not found in gateway"


def run_checks() -> list[dict]:
    checks = [
        ("manifest_parsed", check_manifest),
        ("skills_resolved", check_skills),
        ("tkai_reachable", check_tkai_reachable),
        ("acme_reachable", check_acme_reachable),
        ("obsidian_beacon", check_obsidian),
        ("model_routing", check_model_routing),
        ("pi_endpoint", check_pi_endpoint),
    ]
    results = []
    for name, fn in checks:
        ok, detail = fn()
        results.append({"check": name, "pass": ok, "detail": detail})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Pi SM2 launch-condition checker")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results = run_checks()
    all_pass = all(r["pass"] for r in results)

    if args.json:
        print(json.dumps({"launched": all_pass, "checks": results}, indent=2))
    else:
        print("Pi Launch Condition Check")
        print("=" * 40)
        for r in results:
            mark = "OK" if r["pass"] else "FAIL"
            print(f"  [{mark}] {r['check']}: {r['detail']}")
        print("=" * 40)
        if all_pass:
            print("RESULT: Pi is LAUNCHED. All conditions met.")
        else:
            failed = [r["check"] for r in results if not r["pass"]]
            print(f"RESULT: NOT READY. Failed: {', '.join(failed)}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
