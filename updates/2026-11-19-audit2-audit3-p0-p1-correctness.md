# audit2 + audit3 P0/P1 correctness pass (2026-11-19)

**Branch:** `fix/audit2-3-p0-p1` (from `origin/main`)
**Files:** `alpha_engine/audit3_tribunal.py`, `alpha_engine/forward_observations_ingest.py`,
`audit_trail/dashboard_generator.py`, `.github/workflows/audit3-ledger.yml`,
tests (`test_audit3_coverage_alpha.py`, `test_forward_observations_ingest.py`,
`test_audit2_page_deploy.py`, `test_excluded_cohort_audit.py`).

## What was broken

1. **Impossible coverage ratio.** The live ledger published
   `scored_share_of_valid_pct = 105.26` (8,605 canonical rows vs 8,175
   `valid_closed_picks`). A share above 100 is proof the two denominators
   disagree, not a measurement.
2. **Candidate KPI contradicted its own table.** `summary.n_candidate` counts
   strategy cells only, while `symbols`/`segments` carried CANDIDATE rows with no
   matching counter.
3. **audit2 deploy had no regression test.** The workflow already deploys to
   `/audit2/` (the live page is 200), but nothing asserted the *remote directory*,
   so a future edit could silently send it back to `/audit/` (404).
4. **Forward benchmark coverage 79.8% (< 90% gate).** The ingest fetch window
   stopped at `exit_ms`, but exits carry seconds and `close_at()` looks up to 6h
   forward for the settling bar. 63 of 87 null legs sat at each symbol's latest
   exit. No workflow ran the ingest, so pods could never accrue rows.
5. **Excluded cohorts were invisible.** 41.2% of the closed book is removed
   before export; only aggregate counts survived, so N6 could not tell a random
   exclusion from a biased one.

## What changed

- **Coverage (A):** `payload_coverage()` now withholds the share-of-valid
  headline when `scored > valid`, keeps the raw value in
  `scored_share_of_valid_pct_raw`, and adds `valid_denominator_inconsistent` +
  `denominator_reconciliation` (`canonical_rows`, `dashboard_valid_closed_picks`,
  `delta`, `scored_but_not_dashboard_valid`, `consistent`, `note`). The statement
  now says the denominators disagree instead of printing 105%.
- **Counters (B):** `summary.n_candidate_symbols` and `n_candidate_segments`,
  each computed from its own table.
- **audit2 deploy (C):** `tests/test_audit2_page_deploy.py` asserts the workflow
  creates/enters `audit2`, uploads `index.html`/`audit2.js`/`audit2_forward.json`
  there, deploys `audit3/audit3_ledger.json`, and that `audit2.js` reads
  `../audit3/audit3_ledger.json`. Optional live HEAD under `AUDIT2_LIVE_CHECK=1`.
- **Forward ingest (D):** `BENCHMARK_LOOKAHEAD_MS` is the single source for
  `close_at()`'s tolerance and the fetch-window pad
  (`max(hi, exit_ms + BENCHMARK_LOOKAHEAD_MS)`). `audit3-ledger.yml` now runs
  `forward_observations_ingest --apply` (guarded on DB creds) and commits
  `reports/forward_observations.jsonl`.
- **N6 sidecar (E):** `_excluded_cohort_audit()` in `dashboard_generator.py`
  emits `summary.excluded_cohort_audit` with per-reason n, WR, PF, mean PnL,
  long/short split, and 3 samples; it never raises into the payload.

## How it was verified

```
python3 -m pytest tests/test_audit3_coverage_alpha.py tests/test_audit3_tribunal.py \
  tests/test_audit3_expectancy_gates.py tests/test_audit3_selection_alpha.py \
  tests/test_forward_observations_ingest.py tests/test_forward_observations.py \
  tests/test_audit2_page_deploy.py tests/test_excluded_cohort_audit.py -q
# 122 passed, 1 skipped (live URL probe)
```

Plus: all three modules `py_compile` clean; `.github/workflows/audit3-ledger.yml`
parses; a synthetic `build_report` run is JSON-safe and shows
`scored_share_of_valid_pct=None` with `valid_denominator_inconsistent=False`
when no valid count is supplied.

## Doctrine

KILL/WEAK verdicts are untouched. The new fields add information and withhold a
false ratio; they never demote a claim without evidence.
