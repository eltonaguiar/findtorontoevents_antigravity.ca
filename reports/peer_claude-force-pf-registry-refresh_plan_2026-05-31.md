# Force PF Registry Refresh — BEFORE (Diagnosis)

Date: 2026-05-31  
Author: peer Claude (force-refresh agent)

## Context
- PR #182 (SHA `fc5d2f9f2`) RETIRED `cta_golden_cross_200` + `prediction_market_consensus` at 05:47Z.
- Published JSONs still showed pre-merge `generated_at = 2026-05-31T03:54Z` per Phase-8 / PR #191 checkpoint.
- Phase-8 triggered run `26704818902` to force refresh.

## Findings on run 26704818902
- Workflow: **Unified Audit Dashboard** (`.github/workflows/audit-dashboard.yml`)
- Status: `completed` / Conclusion: **cancelled**
- Created 05:58:18Z, updated 06:06:07Z. Cancelled at job step 0 (no steps recorded).
- Cancellation was caused by the workflow's concurrency group (line ~28 of YAML: collapsed single group) — a newer workflow_dispatch / scheduled run preempted it. Run history shows a chain of 5 cancellations in 14 min as multiple dispatches stacked up.

## Subsequent state
- Run `26704966861` (workflow_dispatch, SHA `705e8d3` — post-#182, post-Phase-9) queued at 06:06:09Z and is the head of the concurrency queue.
- Per workflow YAML lines 733-742, the commit step DOES stage `audit_dashboard/data/pf_registry.json` and `audit_dashboard/data/money_ready_verdict.json`, and runs `tools/money_ready_snapshot.py` (line 509) + `tools/build_pf_registry.py` (line 513).
- Therefore there is NO pipeline bug — the prior runs were just cancelled. Letting run 26704966861 complete should refresh both JSONs with post-#182 retirements applied.

## Plan
1. Monitor run 26704966861 until completion (concurrency-protected; nothing else should be dispatched against this workflow until it finishes).
2. After completion, curl both published JSONs and verify `generated_*` > 05:47Z and that the retired strategies are absent from promotable / top-edges lists.
3. If failure or still stale, capture log + diagnose (likely candidates: DB secrets, `build_pf_registry.py` exit code masked by `|| echo`).

## Risk
- If another agent fires another workflow_dispatch before 26704966861 starts, it will be cancelled too. No more dispatches will be issued by this agent until verification.
