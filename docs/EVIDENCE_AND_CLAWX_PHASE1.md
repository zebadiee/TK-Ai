# Evidence And ClawX Phase 1

Status: frozen implementation boundary

This note defines the Phase 1 boundary for the Evidence layer and the standalone
ClawX research layer. It exists so future changes can be reviewed against a
stable contract instead of relying on team memory.

## Core Invariant

All execution must follow:

`WorkflowJob -> Kernel -> TaskGraph -> Executor -> Provider -> Worker`

**If a change lets anything execute work without going through
WorkflowJob -> Kernel -> TaskGraph -> Executor -> Provider -> Worker,
it must be rejected or redesigned.**

## Phase 1 Goal

Phase 1 adds persistent evidence recording and a standalone ClawX analysis layer
without changing kernel semantics, routing policy, scheduler behavior, or
provider contracts.

The split is:

- Execution: kernel, task graph engine, executor, providers, workers
- Memory: evidence store, evidence index, append-only vault records
- Research: ClawX subscriber, ClawX engine, anomaly detection, signal adapter
- Sensing: signal engine and external sensors

## Phase 1 Non-Goals

- No entity resolution. `BTC`, `bitcoin`, and `BTCUSDT` are not unified yet.
- No execution decisions based on Evidence or ClawX output.
- No direct `ClawX -> Executor` or `ClawX -> Kernel` calls.
- No writes to Evidence from inside kernel, providers, or workers.
- No investigation trees, research cases, contradiction scoring, or knowledge queries.

## Evidence Layer

Phase 1 evidence is append-only and traceable. It records:

- `Evidence` for raw observations
- `Claim` for derived inference output

Vault layout:

- `vault/evidence/evidence.jsonl`
- `vault/evidence/claims.jsonl`
- `vault/evidence/links.jsonl` reserved

Evidence must always carry provenance fields sufficient to trace it back to a
workflow run:

- `trace_id`
- `workflow_job_id`
- `graph_id` when available
- `node_id` when available
- `provider` when available

Evidence is memory only. It must not trigger workflows or influence execution in
Phase 1.

## Evidence Observer Boundary

The only execution-to-memory seam is the observer interface:

`on_node_result(context, result) -> None`

Rules:

- The executor may call the observer once after a node result is returned.
- The observer records evidence or claims and returns nothing.
- The observer must never modify execution results.
- Observer failures must be swallowed and logged; workflow execution continues.

Phase 1 emission scope is intentionally narrow:

- observation action -> `Evidence`
- `model_infer` -> `Claim`
- everything else ignored

Async accepted jobs do not emit evidence at submission time in Phase 1.

## ClawX Research Layer

ClawX is a subscriber to the evidence stream, not part of the execution path.

Allowed responsibilities:

- consume evidence and claim events
- detect anomalies
- build coarse hypotheses
- emit normalized signals through a signal adapter

Disallowed responsibilities:

- calling the kernel directly
- calling the executor directly
- invoking providers
- modifying graphs, routing, or scheduling

The ClawX flow is:

`EvidenceStore -> Subscribers -> ClawXEngine -> SignalAdapter -> SignalEngine`

This preserves the primary ingress invariant because any follow-up work must
still re-enter as a signal-derived `WorkflowJob`.

## Review Gate

Before approving a change in this area, verify:

1. Does execution still follow `WorkflowJob -> Kernel -> TaskGraph -> Executor -> Provider -> Worker`?
2. Is evidence append-only and traceable by `trace_id` and `workflow_job_id`?
3. Does the observer remain observational only?
4. Does ClawX remain outside the execution path?
5. Can the change be explained as execution, memory, research, or sensing without mixing layers?

If any answer is no, reject or redesign the change.
