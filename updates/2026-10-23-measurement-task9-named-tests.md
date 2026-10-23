# Task 9 — Remaining Named Tests (Measurement Hygiene V1, spec §6)

## What was broken / missing

The Measurement Hygiene V1 spec (§6) lists 17 named tests. Tasks 1–5 covered 9
of them. Task 9 adds the remaining 8 named tests. Two of them exercised behavior
that the production code did not yet enforce:

- `test_gate_requires_stage_b_first` — `compute_ledger_gates` silently fell back
  to a gross-PF pass when rows were not stamped with net-of-cost, instead of
  raising on unstamped rows.
- `test_staleness_marks_class_verified_false` — ledgers whose newest resolution
  was stale (older than 30 days) were still reported `OK` with an empty
  `gate_failures`.

The existing `tests/test_ledger_gates.py` fixtures used unstamped rows and stale
Jan–May 2026 dates, which would have violated these new invariants.

## What changed

### Production — `audit_trail/ledger_gates.py`
- Added `STALE_THRESHOLD_DAYS = 30`.
- Added `_newest_resolution(rows)` (reuses `_exit_ts` to parse resolution
  timestamps).
- `compute_ledger_gates` now raises a clear `AssertionError` if any row is
  missing the `net_of_cost_pnl_pct` key (Stage-B-first invariant). This replaces
  the old silent gross-PF fallback.
- `_evaluate_ledger` appends `"stale"` to `gate_failures` (→ verdict
  `UNVERIFIED`) when the ledger's newest resolution is older than the threshold.

### Tests
- Added `tests/test_measurement_hygiene_task9.py` with the 8 named tests from
  spec §6:
  1. `test_stamp_net_of_cost_applies_to_all_closed`
  2. `test_net_of_cost_uses_class_bucket`
  3. `test_gate_uses_net_not_gross_pf`
  4. `test_gate_requires_stage_b_first`
  5. `test_overlap_aware_compounding_differs_from_sequential`
  6. `test_same_instant_batch_not_compounded_sequentially`
  7. `test_staleness_marks_class_verified_false`
  8. `test_aggregators_exclude_unverified`
- Updated `tests/test_ledger_gates.py` fixtures: rows are now stamped with
  `net_of_cost_pnl_pct` and use dates relative to `now` (inside the staleness
  window) so they comply with the new invariants.

## How it was verified (TDD: Red → Green)

- **Red** (before production changes): `test_gate_requires_stage_b_first` and
  `test_staleness_marks_class_verified_false` failed for the expected reasons
  (no assertion raised; no `"stale"` failure).
- **Green** (after production changes): all 8 named tests pass.
- Regression suites pass:
  - `tests/test_ledger_gates.py` (7 tests)
  - `tests/test_compound_overlap_aware.py` (7 tests)
  - `tests/test_transaction_cost_model.py`
  - `tests/test_dashboard_generator_net_pf_wireup.py`
  - `tests/test_compound_equal_weight_pnl.py`
  - `tests/test_compound_and_sharpe_redesign.py`
- Total: 90 tests pass across the touched areas; production caller
  `dashboard_generator.generate()` stamps rows before calling
  `compute_ledger_gates`, so the new assertion does not affect the live path.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
