# GHA Hourly Health Monitor — 2026-09-05

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 15):** 0 success, 15 failure, 0 in_progress

All 15 runs are from 2026-08-30 (runs #2235–#2249); no new CI Tests run has triggered since then (6 days). Both `test (3.11)` and `test (3.12)` jobs fail at step 8: **"Run all tests (gating — known-drift quarantined)"**. All failing commits are "Merge branch 'main'" merge-bot pushes. Last successful CI Tests run predates run #2235 (before 2026-08-30T03:45Z).

Most recent failure: run #2249 (attempt 7) — https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/33339421177

**Specific test names**: log ZIP not directly extractable via API; failure step confirmed as the gated pytest run. Recommend: operator visits the run URL above and expands "Run all tests" step to identify failing test IDs.

**Chronic workflows:** none — single-run window contains 1 cancellation (ALPHA ENGINE - Dynamic Runner) which does not meet the ≥4 threshold. All other workflows in the 100-run window show ≥1 success with no chronic cancel pattern.

**Secondary failures today (2026-09-05):**
- `Feed Health Check` — 1 failure at 12:35 UTC (run https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/33966481477) — unrelated workflow, not CI Tests
- `robust-edge-miner` — 1 failure in today's 100-run window

**Open PRs CI snapshot (9 open PRs):**

| PR | Title | CI Tests verdict | Recommended action |
|---|---|---|---|
| #667 | feat(b5): forward-track cell selector | ❌ FAILURE (test 3.11 + 3.12, stale run from 2026-06-24) | AUTHOR_FIX — failure pre-dates Aug-30 main regression; needs rebase + fresh run |
| #666 | fix(resolver): B1 backfill price guard | Not checked (no fresh run visible) | Awaiting rebase onto fixed main |
| #665 | audit(stalled-producer-detector): v2.0+2 | Not checked | Branch named `fix/ci-tests-drift-reconciliation` — may be related to the current CI failure |
| #657, #600, #595, #581, #564, #562 | Various features | Not checked (all opened before Aug-30 regression) | Likely affected by main CI RED state |

**Open PRs RED:** PR #667 has stale CI failure. PRs #665 (`fix/ci-tests-drift-reconciliation`) is a candidate fix branch worth reviewing first.

**Action required:** **OPERATOR MUST ACT** — CI Tests has been RED on main for 6 consecutive days (since 2026-08-30T03:45Z). Root cause is unknown without log inspection. PR #665 (`fix/ci-tests-drift-reconciliation`) may contain the fix — recommend reviewing and merging or escalating. All open PRs are blocked until main CI is green.

**Status change vs previous monitor (2026-05-22 06:00 UTC):** GREEN → RED (verdict changed). Committing.

---
