# GHA Hourly Health Monitor — 2026-07-15

## 13:00 UTC

**Verdict:** RED

**Main CI Tests (last 5 of 30 checked):** 0 success, 5 failure, 0 in_progress

All 30 most-recent `CI Tests` runs on `main` returned `conclusion=failure` (latest run id 29413979229, created 2026-07-15T12:06:09Z). Both Python matrix legs (3.11 and 3.12) fail at step 8: **"Run all tests (gating — known-drift quarantined)"**. All earlier steps pass (checkout, pip install, JS guard, quarantine write). This indicates a real test assertion failure, not an infra flake.

**Chronic workflows:** none

Scan of key production workflows (last 15 runs each):
- `CI Tests` — **CHRONIC FAILURE** (30/30 failure; no success in this page)
- `Sports endpoint smoke + Playwright` — healthy (19/30 success, 10 cancelled, 1 failure; latest=success 2026-07-15T12:44Z)
- `Unified Audit Dashboard` — healthy (27/30 success; currently in_progress + pending)
- `ALPHA ENGINE - Live Autonomous Scanner` — healthy (28/29 success, 1 cancelled; currently in_progress)

No workflow meets the chronic-cancellation threshold (latest-completed=cancelled AND ≥4 cancels in 15 runs AND 0 successes in 15 runs). CI Tests fails the "0 successes" leg of that check but by failure, not cancellation — classed separately as a persistent test failure.

**Open PRs RED:** Unable to retrieve per-PR `statusCheckRollup` from PR list API response. Given CI Tests is failing on all main-branch runs, any open PR that triggers `CI Tests` will also fail. Open PRs as of this run: #667, #666, #665, #657, #600, #595, #581, #564, #562. PR #657 includes `[skip ci]` in its commit message.

**Failure classification for CI Tests:** **AUTHOR_FIX** — Step 8 runs pytest with the gating suite quarantine list applied. Both Python versions hit the same step. Pattern is consistent across all 30 runs in the window (not a single-run infra blip). Root-cause likely: a test added or modified in a recent commit on `main` is asserting against stale fixture data, or a module import that was refactored broke test collection. Log bytes were unavailable via WebFetch (Azure SAS 403); full pytest output requires `gh run view <id> --log-failed` from a terminal with GH auth.

**Action required:** Author/operator should inspect `gh run view 29413979229 --log-failed | grep -E "FAILED |^E " | head -20` to identify the specific failing tests, then land a fix on `main`. Most recently merged PR: #622 (feat/honest-kill-switch-per-class-thresholds, merged 2026-06-24). CI may have been red since before that merge — this is the first monitor run today and no prior section exists to diff against.

**Run metadata:**
- Monitor run: 2026-07-15T13:00 UTC (automated)
- CI Tests latest run id: 29413979229 · https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/29413979229
- Workflow file: `.github/workflows/ci-tests.yml`
