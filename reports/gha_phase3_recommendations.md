# Phase 3 — Queue & Skip Monitoring Recommendations

## Current State

The `actions-failure-guardian.yml` workflow already runs every 30 minutes (`scripts/actions_failure_guardian.py`) and:
- Serializes itself with concurrency (`cancel-in-progress: false` — lets in-flight push finish)
- Retries failed workflows up to 3 times
- Excludes known verification jobs (`FAILURE_GUARD_EXCLUDE`)
- Writes `reports/actions_failure_guardian.json`

## Recommended Guardian Enhancements

The guardian should be extended to also detect and report:

### 1. Jobs queued > N minutes (phantom queued runs)
51 phantom queued runs were identified (2026-08-07 through 2026-11-11) that can't be cancelled or deleted via REST API (409/403 errors). The guardian should:
- Fetch per-workflow run history
- Flag any run stuck `queued` for > 60 minutes
- Document that these need GitHub Support or classic PAT with Actions admin scope

### 2. Long-running jobs (duration p90)
- Flag any `in_progress` run exceeding 4 hours (default GitHub job cap is 6 hours)
- Identify workflows without `timeout-minutes` that are running long

### 3. Failed without subsequent success (Bucket 1)
- For each workflow, compare latest conclusion against history
- Flag workflows where latest = failure AND no later success exists
- These are the ones that need manual intervention

### 4. Duplicate runs on non-main branches
- Flag non-main branches with > 3 concurrent runs of the same workflow
- These are usually storm-commit artifacts

### 5. Perpetual skips
- Flag workflows where `if:` conditions almost always evaluate false
- Flag path filters that never match

## Implementation Approach

Modify `scripts/actions_failure_guardian.py` to add these checks, outputting to `reports/actions_failure_guardian_queue_audit.json`. The guardian already has the GitHub token and API access pattern established.

## Safe Implementation

- Add checks incrementally, one at a time
- Output to a separate JSON file so existing guardian output is unaffected
- Log warnings, don't auto-fix (queue depth and phantom runs need human judgment)

## Documentation

- Phantom queued runs: `updates/2026-11-16-gha-phantom-queued-runs.md`
- QA Market Validation secrets: `updates/2026-11-16-gha-qa-market-validation-secrets.md`
- Broken workflow disables: `updates/2026-11-16-gha-disable-broken-workflows.md`
