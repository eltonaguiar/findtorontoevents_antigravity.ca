# GHA Hourly Health Monitor — 2026-08-19

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

All 5 of the last 5 CI Tests runs on `main` are `failure`. The most recent run was
2026-08-11T21:16 UTC (8 days ago, run id 31537099985, run_attempt 8 — retried 8 times
on the same commit). CI Tests has not been triggered since then because all subsequent
main commits are bot `[skip ci]` pushes.

Failing step (both Python 3.11 and 3.12): **"Run all tests (gating — known-drift quarantined)"**
(step 8 of the job). Setup, install, and the JS guard all pass — the failure is in the
gating pytest run itself (assertion/import error, not an infra flake). The known-drift
non-blocking run (step 9) passes, indicating the failing tests are not in the known-drift
quarantine list.

Failing run URL: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/31537099985

**Chronic workflows:** none detected

`robust-edge-miner` shows 14 "failure" conclusions in the last 15 runs, but this is
**intentional**: the step that fails is "Alert if a ROBUST candidate appeared
(fail-LOUD = good news, review now)" — meaning the miner found a candidate each time
and used a deliberate fail to surface it. Not a chronic problem. No workflows meet the
chronic-cancellation threshold (≥4 cancellations / 0 successes in 15 runs).

**Open PRs RED:** unknown — 9 open PRs (#667, #666, #665, #657, #600, #595, #581, #564,
#562) have not been individually queried for CI status. CI Tests on main is the primary
signal and it is RED.

**Action required:** AUTHOR_FIX required — the gating pytest suite on main has been
failing continuously since 2026-08-11. The failing step is the real test run (not an
infra flake). Someone should fetch the log from run
https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/31537099985
to identify which test(s) are broken and push a fix.

**Status change vs previous run (2026-05-22 06:00 UTC):** GREEN → RED
(gap of ~88 days with no monitoring runs in between)

---
