# 2026-04-28 Hurst Regime + Hyro Risk Sizer Wiring

## Scope

Integrated two previously orphaned risk controls into active scoring/sizing paths:

1. Hurst regime mismatch penalty (scoring path)
2. HyroTrader risk-sizer overlay (position sizing path)

## Changes

### 1) Hurst regime penalty in smart scoring

- File: `audit_trail/quality_gates.py`
- Added opt-in block in `calculate_smart_score()`:
  - env gate: `HURST_REGIME_PENALTY_ENABLED=1`
  - reads Hurst value from:
    - `pick.hurst_exponent`
    - fallback `pick.extra.hurst`
  - infers regime by thresholds:
    - `H > 0.55` -> `TRENDING`
    - `H < 0.45` -> `MEAN_REVERTING`
    - otherwise `RANDOM_WALK`
  - calls `tools.hurst_regime.strategy_regime_match(strategy, regime)`
  - applies `-6` score penalty on mismatch
- Default OFF, so no behavior change unless explicitly enabled.

### 2) Hyro risk-sizer overlay in Kelly sizing

- File: `alpha_engine/kelly_position_sizer.py`
- Added optional overlay:
  - env gate: `HYRO_RISK_SIZER_ENABLED=1`
  - imports `tools.hyrotrader_risk_sizer.size_pick`
  - computes conservative cap based on Hyro rules
  - if Hyro rejects pick (e.g., daily soft-stop), returns size `0.0`
  - otherwise caps final Kelly size using `min(kelly_size, hyro_size)`
  - annotates picks with:
    - `hyro_size_usd`
    - `hyro_rationale`
    - `hyro_reject_reasons` (when rejected)
- Keeps legacy sizing when feature is disabled or helper unavailable.

## Verification

- Added tests:
  - `tests/test_kelly_dd_halt.py` (extended with Hyro overlay cases)
  - `tests/test_quality_gates.py` (Hurst mismatch penalty coverage)
- Executed:
  - `python -m pytest tests/test_kelly_dd_halt.py -q` -> `5 passed`
  - `python -m pytest tests/test_quality_gates.py -k "hurst_regime_penalty" -q` -> `1 passed`
  - `python -m pytest tests/test_noncrypto_floor_override_workflows.py tests/test_stamp_pick_quality_dsr_gate.py tests/test_asset_class_freshness_report.py tests/test_bond_credit_spread_strategy.py tests/test_vt_baby_strategies_pead.py -q` -> `11 passed`
- `py_compile` and lint checks passed on modified files.

