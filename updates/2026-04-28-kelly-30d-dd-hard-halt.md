# 2026-04-28 Kelly 30d Drawdown Hard-Halt (Opt-In)

## Problem

Volatility scaling had a lower clamp (`0.25x`) and no explicit emergency halt for severe rolling drawdowns.

## Change

Updated `alpha_engine/kelly_position_sizer.py` with an opt-in hard-halt:

- New env gate: `KELLY_DD_HALT_ENABLED` (default OFF).
- New threshold: `KELLY_DD_HALT_MAX` (default `0.30` = 30%).
- New helper extraction reads 30d rolling drawdown from:
  - `pick.extra.rolling_dd_30d`, `pick.extra.drawdown_30d`, `pick.extra.dd_30d`,
  - or top-level equivalents.
- Supports both decimal format (`0.35`) and percent-point format (`35.0`).
- When enabled and threshold is breached:
  - `compute_position_size()` returns `0.0`,
  - sets `dd_halt_triggered=true` and `dd_halt_30d`.

## Safety

- Fully opt-in by environment flag (no default behavior change).
- If drawdown metric is absent, sizing logic is unchanged.

## Verification

- Added tests: `tests/test_kelly_dd_halt.py`
  - halt triggers when enabled + DD above threshold,
  - no halt when feature disabled,
  - recovery path (DD below threshold) resumes normal sizing.
- Ran:
  - `python -m pytest tests/test_kelly_dd_halt.py tests/test_noncrypto_floor_override_workflows.py tests/test_stamp_pick_quality_dsr_gate.py tests/test_asset_class_freshness_report.py tests/test_bond_credit_spread_strategy.py tests/test_vt_baby_strategies_pead.py -q`
  - Result: `14 passed`
- `py_compile` check passed for `alpha_engine/kelly_position_sizer.py`.

