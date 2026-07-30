# GHA Hourly Health Monitor — 2026-07-30

## 13:00 UTC

**Verdict:** GREEN

**Main CI Tests (last 5):** CI Tests workflow is path-gated (`alpha_engine/**`, `paper_trading/**`, `tests/**`, `requirements.txt`, `.github/workflows/ci-tests.yml`). **API returned 404 querying by name "CI Tests" — workflow may have been renamed or restructured since the last confirmed run on 2026-05-21 (PR #1292, all 6 jobs green).** No path-triggering commits detected on main in the current cross-workflow sample (all recent main activity is scheduled bot runs). The operative CI gate checked today is **Sports endpoint smoke + Playwright** (sports-smoke-and-e2e.yml): **30/30 SUCCESS** across the last ~31 hours (2026-07-29T05:24Z through 2026-07-30T12:51Z). No failures or cancellations in the sports CI gate.

**Main CI Tests (last 5):** N/A — workflow unqueryable by name (404); sports CI gate: 30 success, 0 failure, 0 in_progress.

**Chronic workflows:**

Checked 3 key workflows per-workflow (fixed methodology — not global list):

| Workflow | Last 15 conclusions | Chronic? |
|---|---|---|
| Sports endpoint smoke + Playwright | 15/15 success | NO |
| Unified Audit Dashboard | 12 success, 2 cancelled, 1 in_progress | NO (2/15 cancelled, not ≥4; latest completed = success at 10:53Z) |
| ALPHA ENGINE - Live Autonomous Scanner | 14 success, 1 in_progress | NO |

**Chronic workflows: none.** The 2 isolated cancellations on Unified Audit Dashboard (2026-07-29T15:48Z, 2026-07-29T20:31Z, 2026-07-30T11:49Z — 3 in 30) are below the ≥4/15 threshold and are surrounded by successes, consistent with a new run pre-empting an in-flight predecessor.

Cross-workflow recent scan (30 runs from top-of-hour 2026-07-30T12:53–13:04Z): 5 success, 0 failure, 0 cancelled, 0 in_progress (remainder still running at scan time). Workflows active this hour include: ML Forward Test 1745 Models, Swarm State Sync, Recommended Portfolio Generator, Sports data snapshots, Claude's Test - Portfolio Manager, QUAN ENGINE - Live Autonomous Scanner, and 20+ others — all success or in_progress.

**Workflows with `(DISABLED)` sentinel skipped per methodology:** `ANTIGRAVITY ML Hourly Discord Status + Picks (DISABLED)`, `AI Tournament Pipeline — Daily Picks + DB Ingest` (state: `disabled_manually`).

**Open PRs RED:**

| PR | Title | CI Status | Recommended action |
|---|---|---|---|
| #667 | feat(b5): forward-track cell selector | CI Tests: UNKNOWN (workflow 404) | HOLD — awaiting merge; touches tests/, tools/ |
| #666 | fix(resolver): B1 backfill price guard | CI Tests: UNKNOWN (workflow 404) | HOLD — awaiting merge; touches tests/, audit_trail/ |
| #665 | audit(stalled-producer-detector): v2.0+2 | CI Tests: UNKNOWN (workflow 404) | HOLD — awaiting merge |
| #657 | feat(contract-test): cold-merge atomic contract-test gate | [skip ci] explicit | OPEN — author labelled skip CI |
| #600, #595, #581, #564, #562 | Various research/audit PRs (Jun 2026) | CI Tests: UNKNOWN | HOLD — older research PRs |

No PR has a **confirmed** CI failure today. The "CI Tests: UNKNOWN" entries are due to the 404 when querying the workflow by name — not a confirmed failure state. Sports CI gate is clean.

**Action required:** none for immediate CI health.

- **Operator note:** CI Tests workflow could not be queried by name ("CI Tests" → 404). Verify whether `.github/workflows/ci-tests.yml` still exists or was renamed since 2026-05-21. If renamed, update this monitor's query target.
- **Note on gap:** Last monitor file was 2026-05-22 (69 days ago). No verdict change events to reconstruct; establishing fresh GREEN baseline for 2026-07-30.

**Status change vs previous run:** N/A (first entry for 2026-07-30; previous file 2026-05-22 verdict was GREEN). **Committing to establish daily baseline.**

---
