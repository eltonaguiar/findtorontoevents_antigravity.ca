# 2026-04-28 Bond Credit-Spread Wire-Up (LQD-HYG)

## Goal

Integrate a real, production-callable bond credit-spread strategy for Goal #1 with safe rollout controls.

## Implementation

- Added `bond_credit_spread_mean_reversion()` to `alpha_engine/bond_strategies.py`.
- Strategy logic:
  - spread proxy = `log(HYG) - log(LQD)`
  - rolling `zscore(spread, 60)`
  - `z <= -1.25` -> `BUY HYG` (credit oversold rebound)
  - `z >= +1.25` -> `SELL HYG` (credit overbought mean reversion)
- Added rollout guard: `BOND_ENABLE_CREDIT_SPREAD=1` (default OFF).
- Registered in `BOND_STRATEGIES` as `bond_credit_spread_mean_reversion`.
- Added package/script dual import fallback for `config` and `indicators` so module works in both scanner runtime and package-based tests.

## Tests

Added `tests/test_bond_credit_spread_strategy.py`:

- Disabled-by-default guard returns no signals.
- BUY signal emitted for deeply negative spread z-score.
- SELL signal emitted for deeply positive spread z-score.

## Verification

- `python -m pytest tests/test_bond_credit_spread_strategy.py tests/test_vt_baby_strategies_pead.py -q`
  - `6 passed`
- `python -m pytest tests/test_outcome_resolver_v2.py -q`
  - `30 passed`
- `py_compile` checks passed for touched modules.

