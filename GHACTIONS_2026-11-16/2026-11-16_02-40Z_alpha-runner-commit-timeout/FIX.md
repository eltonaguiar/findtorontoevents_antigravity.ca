# Fix — ALPHA Dynamic Runner "Commit results" step timeout

- Date: 2026-11-16T02:40Z
- File: `.github/workflows/dynamic-alpha-engine.yml`
- Commit: this PR (branch `fix/alpha-runner-commit-timeout-2026-11-16`)

## Problem
The `Commit results` step had `timeout-minutes: 5`, but its own push-retry loop is
designed to run up to ~12 min worst case (exponential backoff, `min(i*i*3,90)+RANDOM%15`
over 10 attempts). Under push contention (40+ workflows push `main`), all rebase attempts
fail slowly and the step hits the 5-min cap:

```
##[error]The action 'Commit results' has timed out after 5 minutes.
```

This turns an otherwise **non-fatal** condition (the script already treats "all retries
failed" as a `::warning::` and self-heals next cycle) into a **RED job failure**. Observed
on run `43785912883` (2026-11-16T01:22Z).

## Change
`timeout-minutes: 5` → `timeout-minutes: 15` on the `Commit results` step only.
Job-level timeout was already 90 (from PR #811). No other logic changed.

## Downstream impact on findtorontoevents.ca/audit
`git grep alpha_engine/data` shows `/audit` **does** depend on this data:
- `audit_trail/quality_gates.py`
- `audit_trail/universal_pick_resolver.py`
- `audit_trail/regime_filter.py`
- `audit_trail/backfill_local_sources.py`, `hf_pick_validator.py`, `import_to_backtest_trades.py`

The workflow commits `alpha_engine/data/` (7,903 files), which these modules read. This fix
**improves** /audit freshness by letting the push complete (or exit green + self-heal)
instead of failing red mid-retry. It does not change data schema or any /audit page.

## Revert
```bash
git fetch origin && git checkout main && git pull --ff-only
git checkout origin/main -- .github/workflows/dynamic-alpha-engine.yml   # if main already has it
# OR to undo just this hunk:
#   set timeout-minutes: 15 back to 5 under "Commit results"
git commit -m "revert(ci): restore 5m Commit results timeout on dynamic-alpha-engine"
git push origin main
```
Verification after revert: `grep -n 'timeout-minutes' .github/workflows/dynamic-alpha-engine.yml`
should show job level `90` (line ~115) and step level `5`.

## Verification (post-merge)
Watch the next scheduled `:18`/`:48` run of `ALPHA ENGINE - Dynamic Runner`. Expected:
- If push succeeds → `success`.
- If push fails after 10 retries → step exits with `::warning::` (green), NOT the 5-min timeout red.

## Note / follow-up
The underlying rebase failures during contention (`git pull --rebase` failing repeatedly on a
`fetch-depth: 1` shallow clone) are a separate, deeper issue. This fix stops those from
becoming red failures; a future change could deepen the fetch (e.g. `--deepen`) to reduce
rebase failures outright.
