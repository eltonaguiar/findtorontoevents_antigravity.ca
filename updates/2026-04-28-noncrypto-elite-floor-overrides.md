# 2026-04-28 Non-Crypto Elite-Floor Overrides (Bond/ETF/Futures)

## Problem

Bond/ETF/Futures agent workflows hard-coded `elite_score >= 50`, which over-pruned low-sample classes and contributed to under-deployment.

## Change

Updated workflow curators to use class-specific env-configurable floors instead of fixed `50`:

- `.github/workflows/bond-agent.yml`
  - `BOND_ELITE_FLOOR` (default `40`)
- `.github/workflows/etf-agent.yml`
  - `ETF_ELITE_FLOOR` (default `45`)
- `.github/workflows/futures-agent.yml`
  - `FUTURES_ELITE_FLOOR` (default `45`)

Each workflow now:
- reads env var,
- sets `_elite_floor`,
- filters picks with `elite_score >= _elite_floor`.

## Safety

- Scope limited to non-crypto agent workflows only.
- No crypto workflow behavior touched.
- Floors remain strict but class-aware and tunable via repository variables.

## Verification

- Added tests: `tests/test_noncrypto_floor_override_workflows.py`
  - asserts overrides are wired in non-crypto workflows,
  - asserts non-crypto floor env vars do **not** appear in `*crypto*.yml` workflows.
- Ran:
  - `python -m pytest tests/test_noncrypto_floor_override_workflows.py tests/test_stamp_pick_quality_dsr_gate.py tests/test_asset_class_freshness_report.py tests/test_bond_credit_spread_strategy.py tests/test_vt_baby_strategies_pead.py -q`
  - Result: `11 passed`

