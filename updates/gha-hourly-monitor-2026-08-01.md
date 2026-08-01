# GHA Hourly Health Monitor — 2026-08-01

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

**Chronic workflows:** none detected (all other bot/scanner workflows running success or in_progress)

**Open PRs RED:**
- #667 `feat(b5): forward-track cell selector` — test (3.11) + test (3.12) FAILURE (checks from 2026-06-24; stale open PR) → AUTHOR_FIX
- #665 `audit(stalled-producer-detector): v2.0+2 frame-correction + health-step cron wiring` — test (3.11) + test (3.12) FAILURE (checks from 2026-06-24; stale open PR) → AUTHOR_FIX

**Action required:** AUTHOR/OPERATOR should investigate "Run all tests (gating — known-drift quarantined)" step failing on both Python 3.11 and 3.12 across ALL of today's CI Tests runs on main (at least 10 consecutive failures, 01:22 UTC → 12:21 UTC). Failing run: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/30699545571

**Notes:**
- CI Tests has been RED all day (runs 1943–1952 all failure). First monitor run today so transition point unknown but failure started no later than 01:22 UTC.
- Failing step in both Python matrix jobs: step 8 "Run all tests (gating — known-drift quarantined)" — test infrastructure (checkout, pip install, JS guard, quarantine list) all pass; this is a real test assertion failure, not an infra flake → classify as AUTHOR_FIX.
- No chronic-cancellation workflows detected in last 100 main branch runs.
- 9 open PRs total; PRs #667 and #665 have CI Tests failures but their last check runs are from 2026-06-24 (5+ weeks stale).
