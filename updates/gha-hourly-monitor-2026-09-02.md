# GHA Hourly Health Monitor — 2026-09-02

## 13:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** N/A — no workflow named "CI Tests" exists in this repository (404 on name lookup). Closest push-triggered checks are "Conflict Marker Check" and "No stale DB passwords", both showing `success` on recent pushes.

**Chronic workflows (failure — not cancellation):**
- `robust-edge-miner` — **15/15 failures** in last 15 runs (runs #119–#147, spanning 2026-08-19 through 2026-09-02 12:51 UTC). Each run attempts multiple retries (up to 9 attempts per run_number) and all end `failure`. Zero successes. This is a pre-existing chronic failure, present for at least 14 days. Run IDs: latest is [#33632302680](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/33632302680). Note: this meets a failure-chronic pattern, not the cancellation-chronic pattern defined in the monitor spec.

**Chronic cancellations:** none detected in 200-run sample of recent main activity.

**Other workflows (200-run sample, 2026-09-01 20:47 – 2026-09-02 13:06 UTC):** All `success` or `skipped`. Notable workflows all green: Meme Coin Scanner v2, Alpha Engine FAST, Claude Gainer ML, Forward Trade Tracking v2, Audit Dashboard, Deploy Competition to Live Site, Signal Engine, Swarm State Sync, Strategy Funnel Hourly Refresh, sports-data-snapshots, and ~30 others.

**Open PRs RED:** No PR CI check rollup data available without additional queries. 10 PRs are open (oldest: #562 from 2026-06-12). All appear to be long-standing feature branches, not recently pushed — no fresh CI runs expected on them.

**Action required:**
- **robust-edge-miner**: Investigate and fix the recurring failure. With 15+ consecutive failures and 6–9 retry attempts per run, this workflow is consuming significant GH Actions minutes with zero success. Check `.github/workflows/robust-edge-miner.yml` job logs for root cause (likely a dependency install failure, DB connection, or Python import error). No new code regression — this pre-dates the last 14 days of commits.
- **CI Tests workflow**: The monitor checklist targets a "CI Tests" workflow that does not exist in this repository. Either the workflow was renamed/removed, or this monitor should be updated to target the actual push-CI workflows ("Conflict Marker Check", "No stale DB passwords"). No operator action needed immediately; update monitor config when convenient.
