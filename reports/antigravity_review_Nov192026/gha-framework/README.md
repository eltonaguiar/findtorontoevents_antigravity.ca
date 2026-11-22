# GitHub Actions QA Framework

A meta-workflow that audits the entire `.github/workflows/` fleet (this repo has ~300 workflows) against a QA rubric, catches structural CI hazards, and runs a light critical-QA smoke to prove the core gates still work.

## Files

| File | Purpose |
|---|---|
| `qa-actions-audit.yml` | The meta-workflow. On-demand + weekly cron + runs when workflow files change. |
| `audit_workflows.py` | The audit engine: parses each workflow, scores it against the rubric, emits a markdown report. |

## What it checks (per workflow)

- **Trigger present** — every workflow must have an `on:` block.
- **Manual rescue** — scheduled workflows must also expose `workflow_dispatch`.
- **Timeout** — flags `timeout-minutes > 500`.
- **Concurrency** — multi-job workflows * warning if they lack a `concurrency` group (prevents cancel-cascades — a known failure mode that cost real runs in 2026-05).
- **Broad-glob hazard** — flags `**/*.json`, `audit_dashboard/**`, etc. (infinite-loop risk with push-triggered deployment workflows).
- **Job count** — flags workflows with >30 jobs.
- **Repo-level check coverage** — reports whether `conflict-marker-check`, `secret-scan`, `ci-tests`, `surface-parity` exist anywhere in the fleet.

## Exit behavior

`audit_workflows.py` exits **1** if * any* workflow has an issue, so the meta-workflow fails loudly and the report artifact is still uploaded.

## How to run

Local:
```bash
python3 gha-framework/audit_workflows.py --repo . --out reports/gha_qa_audit_local.md
```

As a workflow: dispatch `QA Actions Audit` from the Actions tab, or wait for the Monday cron.

## Install into a repo

Copy `qa-actions-audit.yml` → `.github/workflows/` and `audit_workflows.py` → a `gha-framework/` dir at repo root (adjust the `--repo` path in the workflow if you place it elsewhere). No extra dependencies beyond Python 3.11.

---
*Built by GitHub Copilot / Mercury-3 AI (githubcopilot-mercury3AI), 2026-11-22 EST.*
