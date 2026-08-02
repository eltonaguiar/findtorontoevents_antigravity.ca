# GHA Hourly Health Monitor — 2026-08-02

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 30 runs):** 0 success, 30 failure, 0 in_progress

**Chronic workflows:** none detected (sports-smoke-and-e2e: 30/30 success — healthy)

**Open PRs RED:**
- #667 — `feat(b5): forward-track cell selector` — test (3.11) FAILURE, test (3.12) FAILURE → AUTHOR_FIX
- #666 — `fix(resolver): B1 backfill price guard` — test (3.11) FAILURE, test (3.12) FAILURE → AUTHOR_FIX
- #665 — `audit(stalled-producer-detector): v2.0+2` — test (3.11) FAILURE, test (3.12) FAILURE → AUTHOR_FIX
- #657, #600, #595, #581, #564, #562 — not individually checked; likely same pattern given root cause is on main

**Failure detail:** Both Python 3.11 and 3.12 jobs fail at step 8: "Run all tests (gating — known-drift quarantined)". Log content unavailable (Azure Blob Storage blocked by proxy). Failure is reproducible across 30 consecutive runs spanning ≥35 hours (earliest in window: 2026-08-01T01:22Z, latest: 2026-08-02T12:26Z), across 30 distinct head SHAs — ruling out a single bad commit or infra flake.

**Run URL (most recent failure):** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/30747810531

**Action required:** operator should investigate why "Run all tests (gating — known-drift quarantined)" has been failing on every commit since at least 2026-08-01T01:22Z. The consistent failure across 30 distinct SHAs and both Python versions points to a broken test dependency, schema change, or environment regression — not a code-level PR bug. Recommend pulling the repo locally and running `pytest` with `-x` to isolate the failing test(s). Also check if any shared fixture, DB config, or secret was rotated around 2026-08-01 00:00 UTC.
