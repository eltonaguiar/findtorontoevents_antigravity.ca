# Excluded rows wired into the coverage summary (Block 59)

**Date:** 2026-11-24 · **Branch base:** `origin/main` (`325a7d8f9db`)
**Companion:** Block 58 (`473a0ff063c`, PR #1110) built the summariser; this block
supplies its input.

## What was broken

Block 58 taught `audit3_tribunal.payload_coverage` to read
`data["_excluded_cohort_rows"]`, but nothing in
[`audit_trail/dashboard_generator.py`](../../audit_trail/dashboard_generator.py)
ever wrote that key. On a live build `coverage.excluded_summary` was an empty
aggregate: `total: 0`, every `by_reason` at 0, `by_class: {}`.

## STEP 1 findings (file:line at `325a7d8f9db`)

| Question | Answer |
|---|---|
| Auto-expired site | `auto_expired` list in `collect_all_picks()` ([:9868](../../audit_trail/dashboard_generator.py), appended [:9872](../../audit_trail/dashboard_generator.py)); `_auto_expired` is stamped on **every** closed row at [:9871](../../audit_trail/dashboard_generator.py)/[:9874](../../audit_trail/dashboard_generator.py); the full list is returned as `all_closed_including_expired` ([:9891](../../audit_trail/dashboard_generator.py), returned [:10466](../../audit_trail/dashboard_generator.py)). |
| Integrity/mirror site | `resolved_closed = _filter_valid_resolved_picks(closed)` in `generate()` ([:15090](../../audit_trail/dashboard_generator.py)); the mirror dedupe loop ([:15095](../../audit_trail/dashboard_generator.py)–[:15111](../../audit_trail/dashboard_generator.py)); `resolved_closed = deduped_closed` ([:15113](../../audit_trail/dashboard_generator.py)). |
| Both sites in one run? | Yes. `collect_all_picks()` is called at [:14797](../../audit_trail/dashboard_generator.py) and its `all_closed_including_expired` is in `generate()`'s scope where the integrity filter runs. |
| Payload assembly | `payload = {...}` at [:17222](../../audit_trail/dashboard_generator.py); audit3 reads the written `dashboard_data.json` via `payload_coverage` ([:2094 of audit3_tribunal](../../alpha_engine/audit3_tribunal.py)), which already reads `data.get("_excluded_cohort_rows")` ([:694](../../alpha_engine/audit3_tribunal.py)). No signature change was needed. |
| Branch labels used as `exclude_reason` | Validity predicate → `resolved_closed_view.default_exclusion_reason(p)` ([:106-135 of resolved_closed_view](../../alpha_engine/resolved_closed_view.py)) falling back to `invalid_row`; mirror `continue` → `mirror_duplicate`; expiry split → the same classifier (`auto_expired` for `_auto_expired` rows). |

## What was wired

- `_stamp_excluded_cohort_row` / `_collect_excluded_cohort_rows` beside
  `_filter_valid_resolved_picks` ([:5034](../../audit_trail/dashboard_generator.py)).
  Rows are **copied** and projected to the six fields the summariser reads; the
  reason is stamped on the copy; a missing `asset_class` is filled by the
  existing `_coerce_asset_class` (the UNKNOWN-trap around `_derive_asset_class`,
  [:3678](../../audit_trail/dashboard_generator.py)) rather than a second
  derivation. `_derive_asset_class` alone defaults a truly classless row to
  `EQUITY`, which would be a guess.
- The mirror loop records its dropped rows ([:15108](../../audit_trail/dashboard_generator.py)) and
  `_excluded_cohort_rows` is collected ([:15117](../../audit_trail/dashboard_generator.py)) from the pre-dedupe valid list.
- The payload gains one key, `"_excluded_cohort_rows"` ([:17376](../../audit_trail/dashboard_generator.py)).

## Additive-only evidence

On a fixed synthetic book, `total_closed / valid_closed / mirror_dupes /
auto_expired / integrity_excluded / kept_after_dedupe` are
`5 / 2 / 1 / 1 / 3 / 1` with **and** without the wiring. No cap,
`MAX_CLOSED_PICKS`, verdict, threshold or tally moves; nothing else reads the
new key.

## Proof (RED then GREEN)

`tests/test_excluded_rows_wiring.py` (9 tests), against the real
`_collect_excluded_cohort_rows` + `payload_coverage` path with a synthetic list
and no DB loader:

- RED (pre-wiring generator): 7 failed, 2 passed.
- GREEN: 9 passed.

Required suite (`test_edge_research_tally_consistency`, `test_check_dossier_citations`,
`test_coverage_limits_doc`, `test_excluded_cohorts_summary`, `test_excluded_rows_wiring`):
53 passed.

## What the next live build will produce

`dashboard_data.json` gains `_excluded_cohort_rows`, and audit3's ledger gains
`coverage.excluded_summary` with real `total`, `by_reason`, `by_class`,
`by_class_and_reason`, `overlap` and `reason_detail` values. Those numbers are
**not** quoted here or in `COVERAGE_LIMITS.md` until that payload exists.

## What stays unknown

The **net direction** of the selection: whether the retained book is flattered
by what was dropped. That needs `excluded_cohorts.bias_report` (retained vs
excluded mean PnL) over the live rows.

## Premises this block falsified

1. "An absent key leaves `excluded_summary` as `None`" is false:
   `summarize_excluded_rows(None)` returns a zero-valued dict. The gap was an
   empty aggregate, not `None`.
2. "Pass a list of rows as `_excluded_cohort_rows`" is false: the summariser takes
   a Mapping of cohort → rows, and a flat list silently summarises as `total: 0`.
3. "`all_closed_including_expired` is the excluded set" is false: it also holds the
   kept rows, so the `_auto_expired` flag has to select them.
