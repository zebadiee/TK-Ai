# TK-Ai (TinyKernelAi) - System Architecture

## Overview

TinyKernelAi (TK-Ai) is a minimal AI workflow kernel designed to govern and orchestrate autonomous tasks using deterministic workflows, capability constraints, and optional model-assisted planning.

It is not an AI assistant.
It is a control plane for AI-driven workflows.

The kernel enforces strict governance over:

- capabilities
- workflow planning
- provider usage
- cost and resource budgets
- graph versioning
- performance fitness

External systems are treated as workers under the kernel.

## Core Design Principles

### 1. Governance First

Every workflow passes through:

- Capability Registry
- Graph Registry
- Budget Rules
- Provider Router
- Fitness Scoring

No provider or worker may execute outside these policies.

### 2. Deterministic Core

The kernel must operate correctly without any LLM present.

LLMs may assist planning but must never be required for execution.

Fallback chain:

`LLM Planner -> Deterministic Planner -> No-op Graph`

### 3. Workers Are Replaceable

External tools are adapters implementing a worker interface.

The core kernel has no direct dependency on them.

### 4. Graph-Driven Execution

All workflows are represented as `TaskGraph` objects.

Example graph:

`monitor -> analyse -> notify`

Graphs may run:

- synchronously
- asynchronously
- scheduled
- event triggered

## Kernel Execution Loop

`Intent / Trigger / Signal -> Graph Planner -> Capability Validation -> Graph Registry -> TaskGraph Runner -> Provider Execution -> Fitness Scoring -> Vault Persistence`

The vault stores:

- graph versions
- graph metrics
- execution state
- events

## Core Components

### Kernel

Responsible for:

- receiving intents
- resolving graphs
- running graph execution
- managing async tasks
- logging events
- updating fitness metrics

### Capability Registry

Defines allowed actions.

Example actions:

- `model_infer`
- `notify`
- `monitor`
- `noop`

Each action maps to a provider.

### Graph Planner

Two planner modes exist.

Deterministic planner:

- hard-coded templates
- semantic capability resolution
- registry-constrained node limits

LLM planner:

- optional
- proposes semantic steps
- validated against the capability registry before execution

### Graph Registry

Manages workflow versions through:

- `register_version`
- `promote_version`
- `rollback`
- `record_failure`

### Graph Fitness

Each graph execution records:

- success rate
- latency
- cost
- token usage

These metrics drive graph promotion and rollback.

### Provider Layer

Providers implement capabilities and must not bypass the kernel.

### Worker Interface

External tools implement:

- `submit_job(payload)`
- `job_status(job_id)`
- `job_result(job_id)`

Workers return results but never create workflows.

## Repository Layout

The public bootstrap layout is:

```text
TK-Ai/
├ kernel/
├ providers/
├ adapters/
├ vault/
├ tests/
├ README.md
├ SYSTEM.md
└ requirements.txt
```

The current implementation behind that surface lives in:

```text
hades/   deterministic kernel internals
atlas/   execution and provider plumbing
athena/  intake interface
```

## Security Model

Rules:

1. Providers cannot spawn workflows.
2. Workers cannot modify the vault.
3. All model calls must pass through the model router.
4. Async workers must be sandboxed.

## Async Execution

Async nodes return:

- `status = accepted`
- `job_id`

The kernel tracks them until completion.

## Trigger System

Triggers allow automatic workflows such as:

- `schedule_tick`
- `market_move`
- `repo_commit`
- `manual_intent`

## Vault

Persistent storage includes:

- `graph_index.json`
- `graph_metrics.json`
- `state.json`
- `solution_graphs/`

## Design Philosophy

`brain -> workflow kernel -> worker tools`

The kernel governs.
Workers execute.
