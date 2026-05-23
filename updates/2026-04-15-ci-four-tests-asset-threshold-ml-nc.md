# CI: fix four stale / regression tests (2026-04-15)

## What was broken

1. **`test_optional_fields` (AssetClassThreshold)** — On runners without pydantic, the fallback `AssetClassThreshold` stub only set attributes from kwargs, so `reason` (and other optionals) were missing; the test expects `config.reason is None`.
2. **`test_ml_feature_contract` (×2)** — `_signal_to_features()` always returned `None` because `signal.get(btc_24h_change)` used an undefined name (`btc_24h_change` instead of the string key `"btc_24h_change"`), triggering the broad `except` and hiding a real production bug.
3. **`test_nc_asset_category_for_pick` (AAPL)** — `nc_asset_category_for_pick` now uses `classify_asset` for plain tickers; AAPL correctly resolves to `EQUITY`. The test still expected `None`.

## What changed

- `alpha_engine/validate_thresholds.py` — Stub class: default `reason`, `weighted_win_pnl`, `weighted_loss_pnl` when not passed.
- `alpha_engine/ml_ranker.py` — Use `"btc_24h_change"` as dict key in two places.
- `tests/test_nc_asset_category_for_pick.py` — Expect `"EQUITY"` for `{"symbol": "AAPL", "asset_class": ""}`.

## How verified

```powershell
python -m pytest tests/test_code_review_fixes.py::TestAssetClassThreshold::test_optional_fields `
  tests/test_ml_feature_contract.py::test_feature_vector_length_matches_features_list `
  tests/test_ml_feature_contract.py::test_feature_names_match_vector_values `
  tests/test_nc_asset_category_for_pick.py -q
```

Exit code 0 (12 passed including parametrized NC cases).

## Regression origin (git)

The bare identifier bug in `ml_ranker.py` was introduced in **`8b2cb61c37`** (2026-04-15, “Smart Picks pipeline fixes…”). That commit added `direction_market_alignment` and rewrote the `btc_24h_change_norm` line, replacing the correct `signal.get("btc_24h_change")` / `mf.get("btc_24h_change")` string keys with `btc_24h_change` as an undefined name. **Impact window:** from that commit until this fix, `_signal_to_features` hit `NameError`, was swallowed, and returned `None` for all signals on that code path (ML ranking fell back to heuristics where applicable).
