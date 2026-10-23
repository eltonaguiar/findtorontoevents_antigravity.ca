# Overlap-Aware Compounding (Sub-project 1, Task 3)

**Date:** 2026-10-22
**Module:** `audit_trail/compound_overlap_aware.py`
**Tests:** `tests/test_compound_overlap_aware.py`

## What was broken

The dashboard's `total_pnl_pct_compounded_ew` metric (via
`_compound_equal_weight_capped_sequence` in `audit_trail/dashboard_generator.py`)
compounds trades **sequentially**, pretending every trade used 100% of capital,
one after another. That math is physically impossible whenever positions overlap
in time:

- With two trades open simultaneously, each would (incorrectly) get a full 100%
  of capital and compound at full weight.
- With resolver **batch-closes** — where dozens of trades share one `closed_at`
  instant — the model treats them as sequential and inflates the number
  catastrophically (e.g. ten 5% trades compound to ~62.9% instead of ~5.1%).

At large N the distortion grows without bound (the legacy metric already carried
a "fictitious sequential reinvestment" disclaimer).

## What changed

1. **New module `compound_overlap_aware()`** — an overlap-aware, equal-weight
   compounding model that:
   - Detects concurrency by interval overlap (active from entry to exit).
   - Allocates capital equally among concurrently active positions
     (**1/N_active** each), using each trade's time-weighted mean inverse
     concurrency over its lifetime.
   - Applies each trade's return only to its allocated capital share
     (not the whole account).
   - Caps per-trade PnL at ± `max_pnl_pct` (same convention as existing helpers).
   - Treats same-instant batches (identical entry/exit) as **concurrent**,
     not sequential.
   - Fails-soft: unparseable/missing timestamps are handled as a sequential
     tail applied after the timed trades, tracked in the returned diagnostics.
   - Returns `(compounded_pct, diagnostics)` including `sequential_pct` and
     `distortion_pp` so the size of the old distortion is visible.

2. **Wired into `generate()`** in `dashboard_generator.py` (~line 14874). The
   old sequential `total_pnl_pct_compounded_ew` assignment is left **unchanged**
   (annotate-don't-delete). Immediately after it, the new
   `total_pnl_pct_compounded_overlap_aware` + `payload_overlap_diagnostics` are
   computed and published side-by-side for one release cycle (spec §2.2), then
   the sequential figure gets retired. `payload_overlap_diagnostics` is a local
   variable that Task 6 will pick up when it assembles the
   `measurement_hygiene` payload block.

## How it was verified

All 7 tests in `tests/test_compound_overlap_aware.py` pass:

- `test_two_overlapping_trades_share_capital` — two concurrent 10% trades →
  10.25% (shared 50/50), `max_concurrency == 2`.
- `test_sequential_trades_match_old_model_when_no_overlap` — zero overlap →
  reproduces the old sequential 0.94% exactly, `distortion_pp ≈ 0`.
- `test_same_instant_batch_is_concurrent_not_sequential` — ten identical 5%
  trades → 5.114% (not 62.9%); `max_concurrency == 10`; `distortion_pp > 50`.
- `test_max_pnl_cap_is_applied` — 999% clipped to 10%.
- `test_untimed_rows_do_not_crash_and_are_counted` — missing/unparseable
  timestamps don't crash; counted in `n_untimed`.
- `test_net_of_cost_field_preferred_over_gross` — net-of-cost PnL wins.
- `test_empty_input_returns_zero` — empty input → `(0.0, zeros)`.

Smoke test: `python3 -c "import audit_trail.dashboard_generator; from
audit_trail.compound_overlap_aware import compound_overlap_aware; print('PASS',
compound_overlap_aware([], 10.0))"` → PASS.

Regression: `tests/test_dashboard_generator_net_pf_wireup.py` → 10 passed.
The `test_dashboard_generator_measurement_hygiene.py` suite referenced in the
plan belongs to Task 6 and is not yet present in the tree.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
