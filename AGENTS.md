# Repository Guidelines

## Project Structure & Module Organization
This repository is currently uninitialized (no source files yet). Keep new code organized from the start:

- `src/`: application or library code
- `tests/`: automated tests mirroring `src/` paths
- `assets/`: static files (images, sample data)
- `docs/`: architecture notes and contributor docs

Example: `src/agent/runner.py` should have tests in `tests/agent/test_runner.py`.

## Build, Test, and Development Commands
No build system is configured yet. For Python-first development, use these baseline commands:

- `python3 -m venv .venv && source .venv/bin/activate`: create and activate local environment
- `pip install -r requirements.txt`: install dependencies (once added)
- `pytest -q`: run tests
- `python3 -m py_compile src/**/*.py`: quick syntax check

Add a `Makefile` or task runner when commands stabilize.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation.
- Prefer type hints on public functions and methods.
- Use `snake_case` for modules/functions, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- Keep modules focused; avoid files that mix unrelated concerns.

Recommended tooling once configured: `ruff` (lint/format) and `pytest`.

## Testing Guidelines
- Place tests under `tests/` and name files `test_<module>.py`.
- Use clear arrange-act-assert structure.
- Add unit tests for new logic and regression tests for bug fixes.
- Target meaningful coverage for changed code, not only line-count metrics.

Run locally with `pytest -q`; add markers only when truly needed.

## Commit & Pull Request Guidelines
Git history is not available in this workspace, so use a clear default convention:

- Commit format: `type(scope): short summary` (example: `feat(auth): add token refresh flow`)
- Keep commits small and logically grouped.
- PRs should include purpose, key changes, test evidence, and linked issue/task IDs.
- Include screenshots or sample CLI output when behavior changes are user-visible.

## Architectural Discipline
Agents must prioritize:

1. deterministic logic before model calls
2. pattern reuse before generating new code
3. minimal file creation
4. small readable modules

Avoid unnecessary frameworks and dependencies.
