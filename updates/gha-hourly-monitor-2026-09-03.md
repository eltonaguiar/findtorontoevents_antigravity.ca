# GHA Hourly Health Monitor — 2026-09-03

## 13:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** N/A — no workflow named "CI Tests" exists in this repo. Closest push-triggered
checks are "Conflict Marker Check" and "No stale DB passwords" — both show `success` on the most recent push
(run #6108 / #6093, 2026-09-03T12:48Z). All other completed scheduled workflows in the last ~60 scanned
runs returned `success`.

**Chronic failures (not cancellations):** `robust-edge-miner` — 15/15 consecutive `failure` results,
going back to run #120 (2026-08-20). Each run auto-retried 5-9 times before ultimately failing.
This is a long-standing pre-existing condition, not a new regression (no successes since at least
2026-08-20, total run count = 149). Log tail of latest failure (run 33757657332, 2026-09-03 12:51Z)
shows only post-job teardown — actual root cause is earlier in the job body and likely a persistent
dependency / environment issue. Run #149 had only 1 attempt (vs 7-9 for prior days), suggesting the
retry budget may be exhausted or the cron timing changed.

**Chronic workflows (cancellation criteria):** none — no workflows meet the cancelled-only criteria
(latest=cancelled AND ≥4 cancels in last 15 AND 0 successes AND no success in 48h).

**Open PRs RED:** Not individually checked via CI rollup (API pagination constraint). 9 open PRs found:
#667, #666, #665, #657, #600, #595, #581, #564, #562. All are stale branches vs main
(base sha 69c8ff54); CI status requires per-PR check-run queries.

**Action required:** Owner should investigate `robust-edge-miner` — 15+ consecutive daily failures
indicate a broken workflow that needs a root-cause fix or explicit disable/archive.
No "CI Tests" workflow exists; if the project added one recently it may not have triggered on main yet.
