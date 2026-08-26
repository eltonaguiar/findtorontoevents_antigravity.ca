# GHA Hourly Health Monitor — 2026-08-26

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5):** 0 success, 5 failure, 0 in_progress

- Run #2206 — failure (completed 2026-08-26T00:18Z) https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/32899180833
- Run #2205 — failure (completed 2026-08-25T20:47Z)
- Run #2204 — failure (completed 2026-08-25T19:47Z)
- Run #2203 — failure (completed 2026-08-25T18:15Z)
- Run #2202 — failure (completed 2026-08-25T16:50Z)

Failing step (both Python 3.11 and 3.12): **"Run all tests (gating — known-drift quarantined)"**
Pattern: 30+ consecutive failures on main going back to 2026-08-24T06:47Z — persistent regression, not a flake.

**Chronic workflows (cancellations):** none

Note: `robust-edge-miner` shows `failure` conclusion on all 15 recent runs, but this is **intentional design** — step 7 is named "Alert if a ROBUST candidate appeared (fail-LOUD = good news, review now)" and fails on purpose to create a loud alert when a robust trading candidate is detected. The upstream scan step (5) succeeds. Not a broken workflow.

**Open PRs RED:** All 9 open PRs (#667, #666, #665, #657, #600, #595, #581, #564, #562) are affected by the main CI Tests regression. PR #665 ("audit(stalled-producer-detector): v2.0+2 frame-correction + health-step cron wiring") is directly CI-related.

- Recommended action: AUTHOR_FIX — "Run all tests (gating — known-drift quarantined)" step is failing real test assertions on both Python 3.11 and 3.12. Investigate the test suite for assertions broken by recent auto-commit changes.

**Action required:** Operator/author should investigate and fix the CI Tests suite. The failure is in gating tests (non-quarantined), not infra. 30+ consecutive failures across 2+ days indicates a real regression, not a flake.
