# TK-Ai (TinyKernelAi)

TinyKernelAi is a minimal AI workflow kernel designed to orchestrate autonomous workflows under strict governance.

It provides a deterministic control plane for AI-assisted systems.

## Features

- Graph-based workflows
- Capability-gated execution
- Optional LLM planning
- Async task orchestration
- Graph versioning and rollback
- Performance fitness scoring
- Pluggable provider architecture

## Philosophy

TK-Ai treats AI as a tool under governance, not a controller.

The kernel plans and validates workflows.

Workers execute them.

## Repository Structure

The public bootstrap surface is exposed through:

- `kernel/`: core execution API facade
- `providers/`: provider and worker interfaces
- `adapters/`: external integrations and bridges
- `vault/`: persistent state and graph versions
- `tests/`: automated coverage

The current implementation is backed by the existing runtime modules in `hades/`, `atlas/`, and `athena/`.

## Quick Start

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the kernel:

```python
from pathlib import Path

from kernel.kernel import build_default_kernel

kernel = build_default_kernel(Path("."))

kernel.handle_intent({
    "intent": "analyse btc funding rates",
})
```

Run the packaged example workload:

```bash
python examples/basic_run.py
```

Run the continuous scheduler example:

```bash
python examples/acme_ai/run_scheduler.py
```

## Optional Model Support

TK-Ai can optionally use local or remote models through the provider layer.

If no model is available the deterministic planner is used.

## Worker Adapters

External tools can integrate through adapters that implement the async worker interface:

- `submit_job(payload)`
- `job_status(job_id)`
- `job_result(job_id)`

## Architecture Notes

- [Evidence And ClawX Phase 1](docs/EVIDENCE_AND_CLAWX_PHASE1.md)
- [First Evidence Run](docs/FIRST_EVIDENCE_RUN.md)

## Knowledge Mirror

Canonical entities live in [vault/entities/entities.json](/home/zebadiee/TK-Ai-Maxx/vault/entities/entities.json).
Mirror them into Obsidian markdown pages with:

```bash
python tools/sync_entities_to_obsidian.py
python tools/sync_tkai_knowledge_to_obsidian.py
python tools/hades_assist_launcher.py
```

Global helpers available on HADES:

```bash
tkai-kickoff
tkai-kickoff-scheduler
tkai-launch
tkai-try
tkai-live
tkai-start
tkai-restart
tkai-status
tkai-stop
tkai-logs
tkai-policy-start
tkai-policy-stop
tkai-policy-restart
tkai-policy-status
tkai-policy-logs
```

Cross-node handshake or remote command execution:

```bash
python tools/cluster_exec.py --all
python tools/cluster_exec.py atlas -- hostname
```

ACME integration health:

```bash
python tools/acme_integration_status.py
python tools/cluster_doctor.py
python tools/acme_runtime_sync.py
```

Canonical ACME/TK-Ai operator runbook:

- [ACME and TK-Ai Interface](/home/zebadiee/TK-Ai-Maxx/docs/ACME_TKAI_INTERFACE.md)
- [TK-Ai Snapshot Time Travel](/home/zebadiee/TK-Ai-Maxx/docs/TKAI_SNAPSHOT_TIME_TRAVEL.md)
- [HADES Assist Model Policy](/home/zebadiee/TK-Ai-Maxx/docs/HADES_ASSIST_MODEL_POLICY.md)

Mission Control summary:

```bash
python tools/tkai_mission_control.py
```

Canonical operator entrypoint:

```bash
tkai-launch
```

To force a ClawX sandbox probe first so the runtime signal stream is populated:

```bash
tkai-launch --probe-clawx
```

Global shortcut for that path on HADES:

```bash
tkai-try
```

## Example Workflow

`monitor -> analyse -> notify`

## License

MIT
