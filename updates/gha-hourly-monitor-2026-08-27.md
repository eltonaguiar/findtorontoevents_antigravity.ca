# GHA Hourly Health Monitor — 2026-08-27

## 13:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** N/A — no workflow named "CI Tests" exists (404); nearest equivalent is overall workflow health below.

**Overall main branch health (last 100 runs):**
- ~95+ success / 2 failure / 5 skipped / 0 cancelled
- All high-frequency scanner workflows (Meme Coin, Alpha Engine, ML Forward Test, Copy Trader, Dynamic Universe, etc.) are GREEN

**Workflows with failures today:**
- `Deploy Competition to Live Site` — 2 failures in last 30 runs (runs #12533 @ 10:35 UTC, #12535 @ 11:46 UTC). Most recent completed run (#12534 @ 11:14 UTC) was SUCCESS; run #12536 @ 12:40 UTC was SKIPPED (workflow_run trigger condition not met). Pattern: intermittent failure, not chronic (successes between failures, no cancelled runs, 0 cancelled in 100-run sample). Failure log shows only git credential cleanup/teardown — actual deploy step failure not captured in tail (likely FTP/deploy step error).

**Chronic workflows:** none — no workflow met chronic criteria (0 cancelled runs in 100-run sample)

**Open PRs RED:** Unable to determine — statusCheckRollup not fetched. 9 open PRs found:
- #667 feat(b5): forward-track cell selector
- #666 fix(resolver): B1 backfill price guard
- #665 audit(stalled-producer-detector): v2.0+2 (branch: fix/ci-tests-drift-reconciliation)
- #657 feat(contract-test): cold-merge atomic contract-test gate
- #600, #595, #581, #564, #562 (older, stale)

**Action required:** Operator should investigate `Deploy Competition to Live Site` failure logs for runs #12533 and #12535 to determine if FTP credentials expired or deploy target is unreachable. Failures are intermittent (not blocking production continuously) but occurring 2× today so far.

---
_Run by GHA monitor scheduled task. Read-only — no production code modified._
