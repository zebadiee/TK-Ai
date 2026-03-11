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

## Optional Model Support

TK-Ai can optionally use local or remote models through the provider layer.

If no model is available the deterministic planner is used.

## Worker Adapters

External tools can integrate through adapters that implement the async worker interface:

- `submit_job(payload)`
- `job_status(job_id)`
- `job_result(job_id)`

## Example Workflow

`monitor -> analyse -> notify`

## License

MIT
