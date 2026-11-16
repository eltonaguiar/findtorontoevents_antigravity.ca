# GHA Phantom Queued Runs (51 runs)

## What they are

51 GitHub Actions workflow runs stuck `queued` forever with 0 jobs ever materialized. Discovered in the GHA triage analysis (GHACTIONS_2026-11-16/2026-11-15_20-57_EST_ghactions/GHA_TRIAGE_ANALYSIS.md, section 3a "Phantom queued runs"), performed 2026-11-15 20:13–21:05 EST via browser HTML scraping cross-checked against a 6-hour 1,000-run API snapshot.

Batch breakdown (UTC dates):

| Date | Count | Age at discovery |
|------|-------|------------------|
| 2026-08-07 | 1 | 100 days |
| 2026-08-19 | 6 | ~90 days |
| 2026-09-13 / 2026-09-15 | 9 | ~60–65 days |
| 2026-10-07 | 14 | ~40 days |
| 2026-11-11 | 21 | 5 days (20:24–20:43 UTC cron stampede) |

The 2026-11-11 batch formed inside a cron stampede (20:24–20:43 UTC). Phantom state: status `queued` but GitHub reports they were "never queued yet."

## Why they can't be removed

All four removal paths were attempted and failed:

1. REST cancel → `409 Cannot cancel a workflow run that has not been queued yet` (phantom state)
2. REST delete run → `403 Could not delete the workflow run` (token lacks admin delete scope)
3. Browser UI "Cancel workflow" → `Failed to cancel workflow.`
4. Browser UI "Delete workflow run" → not offered for queued runs

## Resolution required

Repo owner action needed — either:

- Open a GitHub Support ticket to purge the phantom runs, or
- Delete them with a classic `repo`-scoped PAT or fine-grained token carrying Actions administration/delete scope.

## Impact

- Does NOT block current scheduling: affected workflows all run successfully since the phantom batches formed.
- Permanently pollutes the queue view and distorts concurrency accounting (phantom runs hold concurrency slots with no associated jobs).

## Monitoring / revert criterion

Baseline batch count = 51. Monitor via the 4-hour session cron (monitoring plan step 1). Alert on any new batch (new timestamps). Count must stay at 51 and must not grow.

Source: GHA_TRIAGE_ANALYSIS.md:48–58, 128, 133.
