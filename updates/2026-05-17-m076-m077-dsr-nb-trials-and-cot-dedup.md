# M-076 & M-077: DSR nb_trials Per Asset Class + COT Over-Emission Dedup

**Date:** 2026-05-17  
**Branch:** `chore/m072-contradiction-backfill-snapshot`  
**Review:** Code-reviewer-deepseek — approved with minor observations

---

## M-076: Per-Asset-Class `nb_trials` for Deflated Sharpe Ratio

### Problem
`money_ready_verdict.py` was calling `deflated_sharpe_ratio(nb_trials=1)` — the "selected-best fallacy" (Bailey & Lopez de Prado, 2014). Each asset class aggregate combines picks from N independent source systems (strategy families), each a trial in the multiple-testing sense. `nb_trials=1` was under-deflating the DSR, making verdicts too lenient.

### Fix
- Added `ASSET_CLASS_SOURCE_SYSTEMS` dict mapping each asset class → number of independent source systems
- Counts derived from `alpha_engine/config.py` strategy families + copy-trader intel sources (as of 2026-05-17)
- `_dsr_gate()` now accepts `nb_trials` parameter (default 1), passes it through to `deflated_sharpe_ratio()`
- `money_ready_verdict()` looks up per-class `nb_trials` from `ASSET_CLASS_SOURCE_SYSTEMS` dict
- `nb_trials` is returned in the output dict for audit trail visibility

### Files Changed
- `alpha_engine/money_ready_verdict.py` — added `ASSET_CLASS_SOURCE_SYSTEMS`, updated `_dsr_gate()` and `money_ready_verdict()`
- `tests/test_money_ready_verdict.py` — added 2 tests: plumbing test (nb_trials reaches DSR formula) and integration test (per-class mapping)

### Verification
- `test_m076_dsr_nb_trials_passed_to_deflated_sharpe_ratio` — PASSED
- `test_m076_per_class_nb_trials_mapping` — PASSED
- All 5 money_ready_verdict zone tests — PASSED
- Syntax check — CLEAN

---

## M-077: COT Over-Emission Dedup in Dashboard Fallback Path

### Problem
PR #961 added 1-per-(symbol, release_week, direction) dedup for go-forward COT emissions in `cot_paper_pilot.py`, but the dashboard fallback path's historical reads (`dashboard_generator.py::generate()`) never applied it. This inflated COMMODITY win rate and profit factor with re-emissions of the same CFTC weekly release.

### Fix
- Added `_cot_release_week_key()` — maps a pick's entry timestamp to its CFTC COT release week (ISO year-week anchored to Tuesday)
- Added `_dedup_cot_over_emission()` — deduplicates COT picks by (symbol, release_week, direction), keeping the first chronological emission
- Integrated into `generate()` — applied to `closed` picks in fallback path when `COT_DEDUP_SYSTEMS` is non-empty (imported from `quality_gates.py`)

### Files Changed
- `audit_trail/dashboard_generator.py` — added `_cot_release_week_key`, `_dedup_cot_over_emission`, wired into `generate()`
- `audit_trail/quality_gates.py` — already had `COT_DEDUP_SYSTEMS` frozenset (imported by dashboard_generator)

### Verification
- All 21 `test_cot_over_emission_dedup.py` tests — PASSED
- All 5 `test_cot_dedup_guard.py` tests — PASSED
- All 26 COT dedup tests — PASSED

---

## Code Review Notes (from code-reviewer-deepseek)

1. **`datetime.max` fallback**: COT picks without `created_at` get `datetime.max`, which produces a real ISO week from year 9999 — the `"UNKNOWN"` fallback is never hit. All untimestamped picks for same (symbol, direction) collapse to one. Acceptable in practice.
2. **Redundant datetime imports**: Both helper functions re-import `datetime`/`timedelta` inline. Only `date` is genuinely missing from module-level import. Minor style issue.
3. **Nested functions**: `_cot_release_week_key` and `_dedup_cot_over_emission` live inside `generate()`, making them untestable in isolation. Future refactoring candidate.
