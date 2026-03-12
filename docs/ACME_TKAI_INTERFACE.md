# ACME and TK-Ai Interface

Status: canonical operator runbook

This is the primary integration path between `ACME-AI` and `TK-Ai-Maxx`.

Use this document as the source of truth for:
- exporting ACME governance and telemetry as TK-Ai signals
- bridging ACME signals into the TK-Ai signal bus
- exporting TK-Ai runtime state back into ACME
- verifying that the combined control plane is healthy

## Control Model

`ACME-AI` produces:
- governance and audit events
- HADES mesh telemetry
- mission-control views over TK-Ai artifacts

`TK-Ai` provides:
- the cluster control plane
- the shared signal bus
- the evidence ledger
- topology and agent registry artifacts

The interface is intentionally asymmetric but bidirectional:

1. `ACME -> TK-Ai`
   `scripts/export_signals.py` writes `acme_signals_*.json`
   `tools/acme_signal_bridge.py` imports those records into `vault/runtime/signals.jsonl`

2. `TK-Ai -> ACME`
   `tools/acme_runtime_sync.py` writes a consolidated status snapshot to
   `~/ACME-AI/.acme-ai/runtime/tkai_status.json`

## Canonical Paths

ACME sources:
- `~/ACME-AI/.acme-ai/agent-audit.log`
- `~/ACME-AI/.acme-ai/hades/telemetry.db`
- `~/ACME-AI/.acme-ai/signal_exports/acme_signals_*.json`
- `~/ACME-AI/.acme-ai/signal_export_state.json`
- `~/ACME-AI/.acme-ai/runtime/tkai_status.json`

TK-Ai sinks and artifacts:
- `~/TK-Ai-Maxx/vault/runtime/signals.jsonl`
- `~/TK-Ai-Maxx/vault/evidence/evidence.jsonl`
- `~/TK-Ai-Maxx/vault/runtime/cluster_topology.json`
- `~/TK-Ai-Maxx/vault/runtime/agent_registry.json`
- `~/TK-Ai-Maxx/vault/runtime/acme_signal_bridge_state.json`

Canonical ACME mesh endpoint:
- `http://127.0.0.1:8088/health`

`8000` is not the canonical runtime health check for this integration path.

## Primary Run Sequence

Run these in order:

```bash
cd ~/ACME-AI
python3 scripts/export_signals.py
```

Expected:
- writes `acme_signals_*.json` when new events exist
- prints `No new ACME signals to export` when the export cursor is already current

```bash
cd ~/TK-Ai-Maxx
python3 tools/acme_signal_bridge.py
```

Expected:
- imports only new ACME export files
- writes normalized records into `vault/runtime/signals.jsonl`

```bash
cd ~/TK-Ai-Maxx
python3 tools/acme_runtime_sync.py
```

Expected:
- writes `~/ACME-AI/.acme-ai/runtime/tkai_status.json`
- includes cluster status, topology, registry, recent signals, recent evidence, and integration status

```bash
cd ~/TK-Ai-Maxx
python3 tools/acme_integration_status.py
python3 tools/cluster_doctor.py
```

Expected healthy output:
- `ACME root: OK`
- `ACME TK-Ai adapter: OK`
- `ACME runtime snapshot: OK`
- `ACME signal exporter: OK`
- `ACME mesh health on 127.0.0.1:8088: OK`

## API Trigger

If the ACME HADES mesh is already running, signals can also be exported via API:

```bash
curl -X POST http://127.0.0.1:8088/signals/export
```

Expected:
- JSON response with `signals_exported`

## Operator Shortcuts

From `TK-Ai`:

```bash
python3 tools/tkai_ui.py acme-status
python3 tools/tkai_ui.py acme-sync
```

## Canonical Rules

- Use `scripts/export_signals.py` as the only supported ACME export entrypoint.
- Use `tools/acme_signal_bridge.py` as the only supported import entrypoint into TK-Ai.
- Keep ACME export state outside `signal_exports/` so the bridge never ingests state files as signals.
- Treat `tools/acme_runtime_sync.py` as the canonical outbound TK-Ai snapshot for ACME consumers.
- Treat `tools/acme_integration_status.py` and `tools/cluster_doctor.py` as the canonical health checks.

## Current Live Notes

Verified on March 12, 2026:
- ACME export command runs successfully
- TK-Ai bridge imports without reprocessing
- TK-Ai snapshot export writes into ACME runtime
- ACME mesh health is live on `127.0.0.1:8088`
