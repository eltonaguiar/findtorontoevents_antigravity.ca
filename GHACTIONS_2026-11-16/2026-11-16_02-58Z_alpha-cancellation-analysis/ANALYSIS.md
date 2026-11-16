# ALPHA Dynamic Runner — cancellation/flapping root-cause analysis

- Date: 2026-11-16T02:58Z
- Workflow: `.github/workflows/dynamic-alpha-engine.yml` (`ALPHA ENGINE - Dynamic Runner`)
- Evidence source: live run durations (last 10) + workflow YAML concurrency config.

## Symptom (from subagent stale/flapping recheck)
`dynamic-alpha-engine.yml` is the only flapper: ~9/15 non-success = **1 failure + 8 cancelled**.
`gainer-predictor`, `copy-trader-intelligence`, `signal-engine`, `baby-strat`, `meme-scanner`
are all 0/15. `regime-terminal` 2/15, `multi-asset-scanner` 1/15, `audit-dashboard` 1/15.

## Two distinct causes (both structural, both now addressed)

### A. Long cancellations = old 60-min JOB timeout
Observed durations of cancelled runs:
| created | ended | dur | note |
|---|---|---|---|
| 22:48 | 00:09 | ~80m | job ran to the 60-min cap (after ~20m queue) then killed → "cancelled" |
| 21:48 | 23:08 | ~80m | same |
| 23:49 | 01:05 | 76m | **succeeded** (finished just under) |

GitHub reports a **job `timeout-minutes` hit as "cancelled"** (not failure). At the old
`timeout-minutes: 60`, any run needing >60 min of job time was killed mid-flight → data not pushed.
**Fix: PR #811 bumped the job timeout 60 → 90** (merged, on main line 115).

### B. Red failure = 5-min "Commit results" STEP timeout
Run `43785912883` (01:22Z) failed at `##[error]The action 'Commit results' has timed out after 5 minutes`
while its own retry loop (worst case ~12 min) was still running.
**Fix: PR #813 bumped the step 5 → 15 min** (merged `edda8b53277`).

### C. Short cancellations (15–26 min) = pending-run replacement
`concurrency.group: dynamic-alpha-engine-push`, `cancel-in-progress: false`. GitHub keeps only
**one pending run per group**; cron fires `*/30` but runs need 15–80 min, so each new trigger
cancels the previous *pending* run. These are cheap (never materialized a runner) — noise, not waste.

## Decision
- **No cron change now.** A. + B. fixes let runs reach 90 min and push, which should clear both the
  false-red and the long-cancel classes. Reducing cron cadence (e.g. `18 */2 * * *`) would eliminate
  the class-C pending churn *and* reduce queue load, but also slightly reduce alpha-data cadence
  feeding /audit — so it is **deferred** as an option, not done without evidence it's still flapping.
- **Monitor the next post-02:39 runs.** Expected: successes, or at worst `cancelled` at the 90-min cap
  (not 60), never a 5-min step timeout.

## If it still flaps after the next 3–4 runs
Option (safe, reversible): change cron to `18 */2 * * *` (every 2h) so runtime < interval and no
run ever overlaps — eliminates class C entirely. Revert = restore `18,48 * * * *`.
