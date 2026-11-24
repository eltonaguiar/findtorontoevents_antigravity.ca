# Excluded rows measured per class and reason (2026-11-24, Block 58)

## What STEP 1 found

Recon was done on a fresh non-shallow clone (`git rev-parse --is-shallow-repository`
→ `false`). `origin/main` had advanced from the dispatched tip `d8c29b1e…` to
`e380ccd8…` (a `[skip ci]` daily refresh); nothing in the recon depends on that
commit.

1. **`summarize_excluded()` contract** ([`audit_trail/excluded_cohorts.py:31`](audit_trail/excluded_cohorts.py:31)).
   Accepts an iterable of mappings plus an optional `reason` override. Each row's
   reason comes from the `reason` argument, else `exclude_reason`, else
   `_exclude_reason`, else `"unknown"`. Returns a dict
   `{"total_excluded": int, "by_reason": {reason: {n, n_with_pnl, win_rate,
   mean_pnl_pct, sum_pnl_pct, long, short, unknown, top_symbols, first_closed,
   last_closed}}}`. It has **no class dimension** and is called by no generator
   code path (only `tools/excluded_cohorts_report.py` and its tests).

2. **Are the excluded rows materialised?** Yes, at three sites, as list members:
   - auto-expired: `auto_expired.append(p)` in
     [`audit_trail/dashboard_generator.py:9769`](audit_trail/dashboard_generator.py:9769),
     with the full list retained as `all_closed_including_expired` at
     [`audit_trail/dashboard_generator.py:9788`](audit_trail/dashboard_generator.py:9788).
   - integrity / mirror duplicates: `resolved_closed` is filtered at
     [`audit_trail/dashboard_generator.py:14987`](audit_trail/dashboard_generator.py:14987)
     and deduped into `deduped_closed` at
     [`audit_trail/dashboard_generator.py:15005`](audit_trail/dashboard_generator.py:15005),
     so the excluded rows are `[p for p in resolved_closed if p not in deduped_closed]`
     (identity), available at
     [`audit_trail/dashboard_generator.py:15007`](audit_trail/dashboard_generator.py:15007).
   - canonical reasons: `build_view(closed, ...)` iterates every input row at
     [`alpha_engine/resolved_closed_view.py:197`](alpha_engine/resolved_closed_view.py:197)
     and attributes drops to `invalid_row` / `mirror_duplicate` /
     `non_performance_exit` / `resolver_breakeven_fallback` at
     [`alpha_engine/resolved_closed_view.py:200`](alpha_engine/resolved_closed_view.py:200)
     and [`alpha_engine/resolved_closed_view.py:204`](alpha_engine/resolved_closed_view.py:204).

   At the *decision* sites the code keeps only aggregate counts
   (`invalid_closed_count`, `mirror_dupe_count`, `len(all_closed_including_expired)
   - total_closed`); it does not retain the excluded row dicts as a named list.

3. **Fields on those rows.** They are normalised picks from
   `closed.append(_normalize_pick(p, sys_name, "CLOSED"))`
   ([`audit_trail/dashboard_generator.py:9104`](audit_trail/dashboard_generator.py:9104)),
   which stamps `asset_class` via `_coerce_asset_class()`
   ([`audit_trail/dashboard_generator.py:3678`](audit_trail/dashboard_generator.py:3678))
   using `_derive_asset_class()`
   ([`audit_trail/dashboard_generator.py:3440`](audit_trail/dashboard_generator.py:3440)).
   So `asset_class` is present or derivable, but can be missing (→ `"UNKNOWN"`).
   `exclude_reason` is **not** a field on the rows: it is computed at the filter
   branch (`default_exclusion_reason(pick) or "invalid_row"`, `"mirror_duplicate"`),
   so it is recoverable at that site but not carried by the row.

4. **Verdict.** The rows are materialised; only the *reasons* must be recomputed at
   the filter site. That is additive, not a restructuring of the filter path, so
   STEP 2 proceeded.

## What was implemented

- `summarize_excluded_rows(cohorts)` in
  [`audit_trail/excluded_cohorts.py`](audit_trail/excluded_cohorts.py) (new).
  It takes a mapping of cohort name → rows, counts each row once in `total`
  (cohorts overlap), counts a row once per **distinct reason** it carries in
  `by_reason` / `by_class_and_reason`, buckets classless rows under the explicit
  `"UNKNOWN"` class, and delegates reason detail to the existing
  `summarize_excluded()` so the counting lives in one place.
- `coverage.excluded_summary` in
  [`alpha_engine/audit3_tribunal.py`](alpha_engine/audit3_tribunal.py)
  (`payload_coverage`). It reads an optional `_excluded_cohort_rows` block from the
  payload, so it is **additive**: the 18 pre-existing `coverage` keys are
  byte-identical with and without the block (verified by comparing `payload_coverage`
  on the same summary with and without rows: `changed non-new keys: []`).
- Registered `tests/test_excluded_cohorts_summary.py` in the existing
  [`.github/workflows/verification-tests.yml`](.github/workflows/verification-tests.yml)
  path filters and pytest invocation.

No verdict, threshold, gate, cap or tally was touched; `COVERAGE_LIMITS.md` was not
edited.

## Tests

`tests/test_excluded_cohorts_summary.py` (new, 8 tests, synthetic rows only):

- RED (deliberately wrong expectation): `1 failed, 7 passed`,
  `assert 2 == 3` on the overlapping-cohort total.
- GREEN: `8 passed`.

The brief's command
`python3 -m pytest tests/test_edge_research_tally_consistency.py tests/test_check_dossier_citations.py tests/test_coverage_limits_doc.py tests/test_excluded_cohorts_summary.py -q`
→ **44 passed**. Existing coverage/view suites
(`test_audit3_coverage_alpha`, `test_resolved_closed_view`, `test_excluded_cohorts`,
`test_excluded_cohorts_report`, `test_audit3_ledger_e2e`) → **35 passed**.

## What is still unknown

- **The per-class, per-reason counts of the real 6,111-row gap are still
  UNMEASURED.** This block ships the measuring function and the payload key, but the
  dashboard does not yet write the excluded rows into `_excluded_cohort_rows`, so
  on a live build `excluded_summary` is `None`. Producing real numbers needs a small
  generator-side change: collect the excluded rows at
  [`audit_trail/dashboard_generator.py:15007`](audit_trail/dashboard_generator.py:15007)
  (integrity/mirror) and
  [`audit_trail/dashboard_generator.py:9788`](audit_trail/dashboard_generator.py:9788)
  (auto-expired), stamp each with its reason, and pass them (with
  `_derive_asset_class` applied where `asset_class` is empty) into the payload that
  audit3 reads. That is the remaining work for moving the label from UNMEASURED to
  measured (Block 59), and it must follow from real output, not be guessed.
- `summarize_excluded()` itself was not extended with a class dimension; the class
  rollup lives in the new wrapper. If a future consumer wants class detail from
  `summarize_excluded` directly, it would need that function changed.
