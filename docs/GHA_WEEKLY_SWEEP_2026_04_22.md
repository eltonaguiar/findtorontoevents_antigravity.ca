# GitHub Actions Weekly Sweep — 2026-04-22

## Snapshot (CLI)

Command: `gh run list --limit 15` (2026-04-22 ~02:00 UTC): **most recent scheduled runs completed successfully** (Portfolio Trackers, Rapid Fire, Signal Quality Monitor, Outcome Resolver, Claude Gainer ML Live Scanner, etc.).

## Recent failures (`gh run list --status failure --limit 12`)

| Workflow | Notes |
|----------|--------|
| **CI Tests** | Multiple **main** pushes and **PR** runs failed in the same ~3m window (OBI snapshot, merge commits, doc/research pushes, Phase 4 M1 draft PR). Treat as **one root cause** until logs show otherwise — likely test matrix, env, or import regression. |
| **ALPHA ENGINE - Dynamic Runner** | Failed after **~1h27m–1h38m** — typical of **timeout**, hung runner, or long external dependency. Needs log inspection on the failed job ID. |
| **feat/phase4-m1-feed-risk-metrics** PR | CI Tests failure on PR #314 / related branch — expected to block until dependencies or tests align with draft Phase 4 M1. |

## Recommendations

1. **CI Tests on main:** Open the latest failed `CI Tests` run on `main`, expand the first failing job, and fix the earliest error (often a single import or missing optional dependency). Re-run after fix.
2. **Dynamic Runner:** Check whether `timeout-minutes` or a stuck subprocess (broker API, GPU lock) explains the 1h+ failure; add heartbeat logging if indeterminate.
3. **Deprecation:** Periodically grep workflows for `actions/checkout@v3` / `upload-artifact@v3` and bump per GitHub deprecation notices (not enumerated here; run repo-wide search when touching workflows).

## Parity / audit workflows

`hc-parity.yml` exists for HC evaluator drift; ensure it stays **required** or manually watched on strategy changes to `audit_trail/` HC logic.
