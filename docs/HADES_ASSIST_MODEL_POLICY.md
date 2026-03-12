# HADES Assist Model Policy

HADES Assist uses a deterministic token-aware model policy layered on top of the existing TK-Ai and ACME routing philosophy.

## Selection Rules

- Prefer local Ollama for low-risk governed work:
  - inventories
  - wiki and fact reads
  - snapshot queries
  - Obsidian sync and catalogue updates
- Prefer free-tier OpenRouter rotation for medium-complexity analysis when local-only execution is not enough.
- Escalate to paid-capable routing for:
  - complex reasoning
  - multi-step planning
  - nuanced social-mode responses
  - requests marked `high-stakes` or `production`

## Rotation Inputs

Free-tier OpenRouter candidates are ranked by:

- remaining free quota
- recent error rate
- recent latency
- task fit: code, analysis, or chat

## Runtime Artifacts

The launcher writes:

- `vault/runtime/hades_assist_model_metrics.json`
- `vault/runtime/hades_assist_model_policy.json`
- `vault/runtime/hades_assist_model_selection.json` when an intent is supplied

## Launcher Usage

```bash
python tools/hades_assist_launcher.py
python tools/hades_assist_launcher.py --intent "sync the obsidian knowledge index" --skill snapshot-state
python tools/hades_assist_launcher.py --intent "perform a nuanced multi-step architecture review" --production
```
