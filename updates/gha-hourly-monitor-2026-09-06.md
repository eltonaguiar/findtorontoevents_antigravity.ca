# GHA Hourly Health Monitor — 2026-09-06

## 13:10 UTC

**Verdict:** DEGRADED

**Main CI Gate (sports-smoke-and-e2e.yml — "Sports endpoint smoke + Playwright", last 5):** 5 success, 0 failure, 0 in_progress

> Note: No workflow named "CI Tests" exists in this repository. The primary CI gate is `sports-smoke-and-e2e.yml`. All 5 recent runs on main are GREEN.

**Chronic workflows:** none

> Scan notes:
> - `ALPHA ENGINE FAST Tighter TP/SL, Shorter Holds`: 1 cancel, 12 success in last 15 — not chronic
> - `ALPHA ENGINE - Dynamic Runner (Cloud or Local)`: 1 cancel observed in 100-run window — not chronic (latest run is in_progress/pending, not cancelled)
> - No workflow meets all 4 chronic criteria (latest=cancelled + ≥4 cancels in 15 + 0 success + no success in 48h)

**Production scheduler failures (non-CI-gate):**

| Workflow | Run ID | Time (UTC) | Classification |
|---|---|---|---|
| `robust-edge-miner` | [34034082597](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/34034082597) | 12:46 | RERUN — log tail shows only post-job git cleanup; no assertion errors visible |
| `Feed Health Check` | [34033583187](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/34033583187) | 12:35 | RERUN — log tail shows only post-job git cleanup; no assertion errors visible |

> Both failures show only teardown phase in log tail (git credential removal, orphan-process cleanup). Actual failure cause occurred earlier in the run body. Recommend re-running or expanding log fetch to confirm root cause.

**Open PRs RED:** none (CI gate green on main; per-PR CI check status not available without per-PR check-run fetch — 9 open PRs exist: #667, #666, #665, #657, #600, #595, #581, #564, #562)

**Action required:** operator should manually re-run `robust-edge-miner` and `Feed Health Check` to determine if failures are infra flake or recurring logic errors. If same failures repeat, fetch full logs for root-cause analysis.
