# GHA Hourly Health Monitor — 2026-06-05

## 13:00 UTC

**Verdict:** DEGRADED

**Main CI Tests (last 5):** 5 success, 0 failure, 0 in_progress

**Chronic workflows:** `auto-shutdown-monitor.yml` — CHRONIC FAILURE (not cancellation)
- 15/15 runs are `failure`, 0 successes ever
- First run: 2026-06-05T11:48:37Z — all 15 attempts failed through 13:00:38Z
- 0 jobs found in runs (fail before any job is queued) — strong indicator of missing secret, missing Python dependency (`tools/db_env.py`?), or workflow-level error
- Not technically a chronic-cancellation (0 cancels), but a chronic-failure of equal or greater severity
- Workflow path: `.github/workflows/auto-shutdown-monitor.yml` (created today 2026-06-05T09:37Z)

**sports-smoke-and-e2e:** 26/26 consecutive successes — GREEN (last: 2026-06-05T11:25Z)

**Open PRs RED:** none (0 open PRs)

**Action required:** Operator should investigate `auto-shutdown-monitor.yml` — check that secrets `DB_PASS_STOCKS` and `DB_USER_STOCKS` are set in repo settings, and verify `tools/db_env.py::get_stocks_creds()` is importable. Run ID of most recent failure: [27016333972](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/27016333972)
