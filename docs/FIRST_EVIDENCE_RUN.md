# First Evidence Run

Purpose: verify that the first live Evidence + ClawX research loop is
operational without violating architecture boundaries.

Expected pipeline:

`Worker -> Executor -> EvidenceObserver -> EvidenceStore -> Subscribers -> SignalEngine -> WorkflowJob`

## 1. Confirm System Boot

Start TK-Ai normally.

Example:

```bash
python run_system.py
```

Confirm logs show:

- `Kernel started`
- `Executor ready`
- `EvidenceStore initialized`
- `ClawX subscriber registered`
- `Obsidian bridge registered`

Green condition:

- no errors
- all subscribers registered

## 2. Trigger Test Workflow

Run a simple investigation workflow that includes:

- `acme_monitor`
- `model_infer`
- `notify`

Example:

```bash
python run_workflow.py investigate_funding_anomaly
```

Green condition:

- workflow completed
- no kernel exceptions

## 3. Verify Evidence Capture

Check vault evidence files:

- `vault/evidence/evidence.jsonl`
- `vault/evidence/claims.jsonl`

Expected observation entry:

```json
{
  "type": "observation",
  "source": "acme_monitor",
  "content": {
    "exchange": "binance",
    "funding_rate": 0.23
  }
}
```

Expected claim entry:

```json
{
  "statement": "BTC funding anomaly detected",
  "confidence": 0.84
}
```

Green condition:

- JSONL entries created
- valid JSON
- correct `trace_id`
- correct `workflow_job_id`

## 4. Verify Evidence Index

Inside the runtime console or REPL, inspect:

- `index.by_trace`
- `index.by_entity`
- `index.by_investigation_key`

Expected example:

`investigate_funding_anomaly::binance`

Green condition:

- lookup works
- no `None::entity` keys

## 5. Verify Obsidian Notes

Check vault paths:

- `vault/research/evidence/`
- `vault/research/claims/`

Expected:

- `vault/research/evidence/2026/ev-XXXX.md`
- `vault/research/claims/2026/cl-XXXX.md`

Green condition:

- markdown readable
- metadata intact
- links possible

## 6. Verify ClawX Subscriber

ClawX should receive the event.

Expected logs:

- `ClawX received evidence: acme_monitor`
- `ClawX anomaly detected`

Green condition:

- no subscriber crash
- engine processes event

## 7. Verify Signal Emission

Expected log:

- `Signal emitted: funding_rate_anomaly`

Expected signal payload:

```json
{
  "type": "funding_rate_anomaly",
  "payload": {
    "exchange": "binance",
    "funding_rate": 0.23
  }
}
```

Green condition:

- signal emitted once
- payload correct

## 8. Verify Signal To WorkflowJob

Signal engine converts the signal into a job.

Expected log:

- `SignalEngine created WorkflowJob`

Expected job:

- `intent: investigate_funding_anomaly`
- `source: clawx`

Green condition:

- job accepted by kernel

## 9. Verify Architecture Invariant

Confirm that ClawX did not bypass the execution path.

Allowed:

- `ClawX -> SignalEngine`
- `SignalEngine -> WorkflowJob`

Forbidden:

- `ClawX -> Kernel`
- `ClawX -> Executor`
- `ClawX -> Provider`

Green condition:

- only `WorkflowJob` ingress is used

## 10. Verify Evidence Isolation

Optional failure test:

```bash
chmod -w vault/evidence
```

Run the workflow again.

Expected result:

- workflow still completes
- observer logs a warning
- execution outcome unchanged

Green condition:

- evidence failure does not break workflow

## Final Green State

If everything works, the system has a closed research loop:

`ACME Worker -> TK-Ai Execution -> Evidence Memory -> ClawX Research -> Signal Generation -> New WorkflowJob`

This means the system is now capable of:

- continuous investigation
- pattern detection
- autonomous follow-up
- research accumulation

## What Success Looks Like

After several runs you should see:

- `vault/evidence` growing
- `vault/claims` growing
- Obsidian investigation notes
- ClawX signals appearing
- new jobs triggered

That is the point where the research loop is live.
