# TK-Ai Cluster Architecture

Status: frozen operational architecture

## Scheduler Autonomy

ClawX emits policy artifacts.
The policy daemon enforces runtime state.
Systemd manages processes.
Operators retain override control.

Control loop:

`Evidence -> ClawX detectors -> SchedulerPolicyRules -> scheduler_policy.json -> tkai_policy_daemon -> tkai-start/tkai-stop -> systemd`

## Node Roles

Cluster node roles are declared in [node_roles.json](/home/zebadiee/TK-Ai-Maxx/cluster/node_roles.json).

- `hades`: control plane, scheduler, ClawX, policy daemon, signals, evidence
- `atlas`: GPU inference worker
- `hermes`: support worker

ACME-AI currently joins the cluster at `hades` through three operational seams:
- `acme_signal_bridge` imports ACME-exported JSON signals into the TK-Ai signal bus
- `acme_hades_mesh` exposes ACME service-mesh and governance APIs on the control node
- `acme_mission_control` reads TK-Ai runtime artifacts through ACME's `tkai_adapter`

To reduce cross-repo scraping, TK-Ai can also export a consolidated snapshot into
`~/ACME-AI/.acme-ai/runtime/tkai_status.json` via `tools/acme_runtime_sync.py`.

The canonical operator sequence for this interface is documented in
[ACME_TKAI_INTERFACE.md](/home/zebadiee/TK-Ai-Maxx/docs/ACME_TKAI_INTERFACE.md).

## Node Identity

Cluster-aware tools should resolve node identity through `tools/cluster_registry.py`.

This registry is the canonical source for:
- cluster role to topology role mapping
- SSH transport targets
- node host and IP metadata
- declared per-node services

Topology generation, diagnostics, remote agent invocation, and runtime status
artifacts should all consume this registry instead of duplicating node logic.

## Governance Model

- ClawX never starts or stops processes directly.
- Only policy artifacts request runtime state.
- Only the policy daemon applies those artifacts.
- Systemd remains the process supervisor.
- Operators can override desired runtime state by editing `vault/policy/scheduler_policy.json`.

## Mobile Observability Layer

Apollo provides mobile monitoring and policy override.
All interactions occur through Hermes API.
Apollo never communicates directly with runtime services.

## Operator Entry

The canonical entry point for cluster operations is:

`tkai-launch`

This command initializes the runtime stack, verifies cluster health, launches
Mission Control, and enters the ClawX operator console.
