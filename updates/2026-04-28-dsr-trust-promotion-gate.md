# 2026-04-28 DSR Trust-Tier Promotion Gate

## What was broken

`trust_tier` promotion to `PROVEN` relied on WR/N only.  
That allowed promotion even when risk-adjusted robustness (DSR) was known to be negative.

## What changed

- Updated `audit_trail/stamp_pick_quality.py`:
  - Added `_extract_dsr()` helper to read DSR from common fields (`dsr`, `deflated_sharpe`, nested `extra`).
  - Added promotion guard:
    - if computed trust tier is `PROVEN` and `DSR < 0`, block promotion and downgrade to `WATCH` (or `MONITOR` when WR/N do not meet WATCH floor).
  - Added per-pick marker: `trust_promotion_block_reason=dsr_lt_zero:<value>`.
  - Added summary metric: `dsr_promotions_blocked`.
  - Added CLI output line for DSR block count.

## Why this is safe

- Only affects promotion to `PROVEN`.
- If DSR is missing, behavior is unchanged (existing WR/N rules still apply).
- Retirement states (`BANNED`/`UNTRUSTED`) remain preserved.

## Verification

- Added tests `tests/test_stamp_pick_quality_dsr_gate.py`:
  - negative DSR blocks PROVEN promotion.
  - non-negative DSR keeps PROVEN promotion.
- Ran:
  - `python -m pytest tests/test_stamp_pick_quality_dsr_gate.py tests/test_asset_class_freshness_report.py tests/test_bond_credit_spread_strategy.py tests/test_vt_baby_strategies_pead.py -q`
  - Result: `9 passed`
- `py_compile` checks passed on modified modules.

