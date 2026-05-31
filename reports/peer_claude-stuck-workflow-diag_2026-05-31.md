# Stuck Workflow Diagnosis — Run 26706712727

**Date:** 2026-05-31T07:47Z
**Workflow:** Run Backtests & Deploy Dashboards
**Event:** workflow_dispatch (manual)
**Branch:** main
**Run URL:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26706712727

## State

- `status`: pending
- `conclusion`: (empty)
- `createdAt`: 2026-05-31T07:37:51Z
- Run-level `startedAt`: 2026-05-31T07:37:51Z (run accepted)
- Job `backtest` (id 78709723073): `status=queued`, `startedAt=2026-05-31T07:46:35Z`
- Wall-clock waiting at probe time (07:47:52Z): ~10 min run-level / ~1m17s since job entered queued state
- Steps array empty — runner has not been assigned yet.

## Root cause: GHA queue saturation

Concurrent system snapshot at 07:47Z:

**Queued (15+):** No stale DB passwords (x2), Conflict Marker Check (x2), Secret Scan (M-043), Branch Large File Duplicate Guard, Social Media Prediction Tracker, Recommended Portfolio Generator, ALPHA Verify Predictions, LIVE SPIKE TRADING, LuxAlgo Signal Generator, Feed Health Check, Audit Drift Telemetry, CI Tests, Rise of the Claw deploy.

**In-progress (15+):** Branch Large File Duplicate Guard (x9 concurrent — saturating runners), Mirror torontoevent.net, ALPHA ENGINE Dynamic Runner, Unified Audit Dashboard, Run Backtests & Deploy Dashboards (ROOCODE variant id 26706209258, in-progress since 07:12:37Z, 35+ min).

**Blocker hypothesis:**
1. The ROOCODE-variant Run Backtests workflow (26706209258) has been running 35+ min and likely shares a concurrency group with run 26706712727.
2. Branch Large File Duplicate Guard is spawning x9 concurrent and consuming the hosted-runner budget.

This is NOT a workflow failure. No `--log-failed` output is retrievable (steps haven't run). It is queue contention on hosted runners.

## Action

**LEAVE ALONE — wait.** Per task rules, this workflow touches the production-scoring/backtest path; do not cancel/retry blindly. Expected sequence:

1. The ROOCODE-variant Run Backtests should finish first (estimated ~10–20 more min based on its 35-min runtime).
2. Branch Large File Duplicate Guard runs are short (~2–5 min each) and will free runners.
3. Job 78709723073 will pick up a runner once concurrency-group slot is free.

**ETA:** ~15–25 min from probe time.

## Operator-flag conditions (not yet met)

- If still queued at 08:15Z (30+ min), suspect concurrency-group deadlock — operator should inspect `.github/workflows/run_backtests_and_deploy_dashboards.yml` for `concurrency:` block and check ROOCODE variant for matching group key.
- If runner shortage chronic, operator should consider rate-limiting the Branch Large File Duplicate Guard workflow (x9 concurrent is the prime suspect for runner exhaustion).

## Decision

`STUCK_DIAG:state=queued:action=wait:eta_min=20`
