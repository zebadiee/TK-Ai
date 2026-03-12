# ACME-AI Example Workload

This pack defines a simple BTC funding watch workflow for TK-Ai:

`schedule_tick -> clawx_monitor -> model_infer -> notify`

Use it through the repo-level runner:

```bash
python examples/basic_run.py
```

The pack only contains workload assets. It reuses the repository's base capability
registry and routing configuration.

Included files:

- `solution_graph.json`: tracked graph family for the example
- `solution_graphs/acme_btc_funding_watch_v1.json`: versioned graph payload
- `graph_index.json`: active graph version mapping
- `triggers.json`: launch rule for the scheduled funding check
- `signals.json`: placeholder signal configuration for future expansion
