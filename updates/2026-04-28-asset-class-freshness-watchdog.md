# 2026-04-28 Asset-Class Freshness Watchdog

## What was broken

We had no automated daily artifact that answered:

- per asset class `n`,
- realized `WR` and `PF`,
- and whether each class was stale by last closed pick age.

That made it easy to miss under-fed classes and stale pipelines.

## What changed

- Added `tools/generate_asset_class_freshness_report.py`.
  - Reads `audit_dashboard/data/dashboard_data.json`.
  - Computes per-class `n`, `win_rate_pct`, `profit_factor`, average `pnl_pct`.
  - Computes freshness via `last_closed_age_days` and `last_pick_age_days`.
  - Outputs both JSON and Markdown artifacts.
  - Supports `--warn-only` for CI non-blocking mode.
- Added workflow `.github/workflows/asset-class-freshness-watchdog.yml`.
  - Daily schedule + manual dispatch + PR-path triggers.
  - Runs report generator in warn-only mode.
  - Uploads JSON/MD artifacts for review.
- Added unit test `tests/test_asset_class_freshness_report.py`.
- Patched age calculation to clamp negative ages to `0.0` (guards clock/future timestamp skew).

## Verification

- `python -m pytest tests/test_asset_class_freshness_report.py -q`
  - `1 passed`
- `python -m pytest tests/test_asset_class_freshness_report.py tests/test_bond_credit_spread_strategy.py tests/test_vt_baby_strategies_pead.py -q`
  - `7 passed`
- `python tools/generate_asset_class_freshness_report.py --warn-only --json-out reports/asset_class_freshness_latest.json --md-out reports/asset_class_freshness_latest.md`
  - artifacts generated successfully.

