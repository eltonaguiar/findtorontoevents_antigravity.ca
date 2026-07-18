# GHA Hourly Health Monitor — 2026-07-18

## 13:00 UTC

**Verdict:** GREEN

**Note on "CI Tests" workflow:** No workflow with that exact name exists in this repository (404 on name lookup; 362 active/disabled workflows searched). The functional CI-gate equivalents used for this run are: "Conflict Marker Check", "No stale DB passwords", "sports-smoke-and-e2e", and "actions-failure-guardian".

**Main CI Gates (last 5 runs each):**

| Workflow | Last 5 conclusions | Latest run |
|---|---|---|
| Conflict Marker Check | 5 / 5 success | 2026-07-18T12:51:36Z |
| No stale DB passwords | success (in recent 30-run broad scan) | 2026-07-18T12:51:36Z |
| actions-failure-guardian | 30 / 30 success | 2026-07-18T12:48:15Z |
| sports-smoke-and-e2e | 30 / 30 success | 2026-07-18T12:34:24Z |

**Broad main-branch scan (last 30 runs across all workflows):** 27 success, 0 failure, 3 in_progress (robust-edge-miner, Cross-System Signal Aggregator, ALPHA ENGINE FAST — all normal scheduled executions)

**Chronic workflows:** none — no cancellations detected in any per-workflow sample (sports-smoke-and-e2e: 0/30 cancelled; actions-failure-guardian: 0/30 cancelled; conflict-marker-check: 5 recent = all success)

**Disabled workflows (intentional, not chronic):** AI Tournament Pipeline, Forex Agent, Forex Smart Picks Scanner — all `disabled_manually`, skipped per checklist rules.

**Open PRs RED:** none — 9 open PRs (#667, #666, #665, #657, #600, #595, #581, #564, #562), all are older feature/fix PRs from June 2026, no CI failures observed in their status. All are based on `main` sha `69c8ff54`, which is stable.

**Action required:** none
