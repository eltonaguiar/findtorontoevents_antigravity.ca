# GHA Hourly Health Monitor — 2026-07-06

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

**Failure detail:**
- Run 28791662785 triggered at 2026-07-06T12:31Z on sha `f4997355a3`
- Jobs: `test (3.11)` ❌, `test (3.12)` ❌
- Failing step: **step 8 — "Run all tests (gating — known-drift quarantined)"** (ran ~3 min, then failed)
- Steps 1–7 (setup, checkout, Python install, cache, pip install, JS guard, quarantine write) all ✅
- Step 9 "Known-drift tests (non-blocking)" ✅ — failure is in the gated suite, not known-drift
- **Prolonged failure:** all 120+ CI Tests runs scanned (ci-tests.yml pages 1–4, covering 2026-06-30T00:22Z through 2026-07-06T12:31Z) concluded `failure`. 0 successes found in the last 120+ executions.
- **Last confirmed green:** PR #1292 merged 2026-05-21T19:15Z (run 26245197357, all 6 jobs ✅). Monitor went dormant after 2026-05-22 00:00Z. Last human-authored merged PR is **#622** (2026-06-24T15:45Z).

**Chronic workflows:** none — scanned 60 most-recent main-branch runs across all active workflows; every non-CI-Tests workflow concluded `success`. No pattern of ≥4 cancellations + 0 successes detected.

**Open PRs RED:** 9 open PRs (#667, #666, #665, #657, #600, #595, #581, #564, #562) all predating June 24; CI Tests on their branches is expected to fail with the same underlying test suite breakage. No PR-specific triage possible until main CI is restored.

**Action required:** AUTHOR FIX — the gated test suite ("Run all tests") has been failing on both Python 3.11 and 3.12 for **7+ days** continuously (since before 2026-06-30). Root cause is a real test logic failure introduced sometime between 2026-05-22 and 2026-06-30 (monitor gap). Most likely culprit window: commits merged to main between May 22 and June 24 (last merged PR #622). Operator should:
1. Run `pytest tests/ -x` locally to identify the failing test(s)
2. Check if a new test added in a recent PR imports a missing dependency or references a DB/file not available in CI
3. Fix or quarantine the failing test(s) and push to main

---
