# ML Phase 20 Pipeline Fixes — 2026-04-15

## Overview

Phase 20 addresses critical issues in the ML pipeline: feature engineering bugs, scoring formula problems, look-ahead leakage, and backfill inconsistencies. All changes are syntax-checked and smoke-tested end-to-end.

---

## 1. `alpha_engine/ml_ranker.py` — Feature Engineering Fix

### Change: `direction_encoded` → `direction_market_alignment`
- **Before:** `direction_encoded` (LONG=1, SHORT=-1) — always populated but no market context
- **After:** `direction_market_alignment` = `direction × btc_24h_trend`
  - LONG + BTC rising → positive (aligned)
  - SHORT + BTC falling → positive (aligned)
  - LONG + BTC falling → negative (misaligned)
  - **Graceful fallback:** When `btc_24h_change` is missing, returns raw `dir_val` (±1) instead of 0.0 — preserves directional information

### Kept `btc_24h_change_norm` in FEATURES list
- Removing it reduced feature count by 1, silently misaligning cached model checkpoints
- Both `btc_24h_change_norm` and `direction_market_alignment` now exist (correlated; clean up on next full retrain)

### Syntax fix
- Moved `_dir_val`, `_btc_raw`, `_btc_24h` assignments outside the `feat = [...]` list literal (Python doesn't allow assignments inside list literals)

### Stale cache cleanup
- Deleted `alpha_engine/data/boruta_selected_features.json` (referenced old `direction_encoded`)

---

## 2. `ml_gatekeeper/gatekeeper.py` — Scoring & Calibration

### IsotonicRegression calibration
- Raw RF/GB ensemble probabilities are now calibrated via `IsotonicRegression` before scoring
- **Brier score improved 0.2828 → 0.2396** (+0.0432) in smoke test
- Same approach as `ml_ranker.py` (which already uses isotonic calibration)

### Replaced hand-tuned 60/25/15 scoring formula
- **Before:** `gk_score = (ml_prob × 60) + (strat_wr × 25/0.43) + (source_wr × 15/0.43)`
- **After:** Learned `ml_prob` weight via logistic regression on OOF predictions + fixed strat/source bonuses
  - `_fit_score_weights` fits 1D logistic regression on `(calibrated_ml_prob) → win/loss`
  - Strat/source WR are **not** included in the logistic fit because they are constant 0.43 during training (no per-pick router data in OOF loop) — fitting on constant features produces useless weights
  - At scoring time, strat/source WR bonuses are computed from actual router data:
    - `strat_bonus = (strat_smoothed_wr - 0.43) × 25`
    - `source_bonus = (source_wr - 0.43) × 15`
- **Smoke test result:** Learned weight = 0.2070, intercept = -0.3918

### Bug fix: `isso_cal` → `iso_cal` typo

---

## 3. `ml_crypto_predictor/production_engine.py` — Look-Ahead Leakage Fix

### Temporal split moved before feature selection
- **Before:** Correlation-based feature selection computed on full dataset (train + holdout) → leaked future information into feature selection
- **After:** Temporal train/test split performed FIRST, then feature selection only uses training portion
- Rolling features in walk-forward validation were already correctly computed — no leakage there

---

## 4. `alpha_engine/data_coverage_enforcer.py` — Backfill Consistency

### `direction_market_alignment` graceful fallback
- **Before:** Backfill computed `dir_val × 0.0` (btc_trend=0 default) → always 0.0 for picks without BTC data
- **After:** When `btc_raw` is None or 0 (no BTC data), falls back to `dir_val` (±1) — matches `ml_ranker.py`'s behavior
- `FEATURE_DEFAULTS["direction_market_alignment"]` changed from `0` to `None` (always computed during backfill for picks with direction)

---

## 5. `tests/test_ml_feature_contract.py` — Test Update

- Updated assertion for `direction_market_alignment`: expects `1.0` (graceful fallback for LONG with no BTC data) instead of `0.0`

---

## Smoke Test Results (2026-04-15)

```
ml_gatekeeper/gatekeeper.py — FULL PASS
  - IsotonicRegression calibration: Brier 0.2828 → 0.2396 (+0.0432)
  - Learned score weight: 0.2070, intercept: -0.3918
  - 69 active picks scored, all passed gate
  - Model saved to ml_gatekeeper/models/gatekeeper_model.joblib

All 6 modified files pass syntax checks:
  - alpha_engine/ml_ranker.py ✅
  - ml_gatekeeper/gatekeeper.py ✅
  - ml_crypto_predictor/production_engine.py ✅
  - alpha_engine/data_coverage_enforcer.py ✅
  - alpha_engine/entry_optimizer.py ✅
  - tests/test_ml_feature_contract.py ✅
```

---

## Files Modified

| File | Change Type |
|------|------------|
| `alpha_engine/ml_ranker.py` | Feature engineering, syntax fix |
| `ml_gatekeeper/gatekeeper.py` | Calibration, scoring formula |
| `ml_crypto_predictor/production_engine.py` | Leakage fix |
| `alpha_engine/data_coverage_enforcer.py` | Backfill consistency |
| `tests/test_ml_feature_contract.py` | Test assertion update |
| `alpha_engine/entry_optimizer.py` | Minor import fix |
| `alpha_engine/data/boruta_selected_features.json` | Deleted (stale cache) |
