# ML Data Flow Audit — Complete Pipeline Trace
**Date:** 2026-03-16
**Auditor:** Claude Code (automated trace)

---

## 1. Alpha Engine ML Ranker

### Flow Diagram

```
                        +----------------------------+
                        |  closed_picks.json (281)   |
                        |  (committed to repo)       |
                        +-------------+--------------+
                                      |
                    import_closed_picks_json()
                                      |
                                      v
                        +----------------------------+
                        |  SQLite picks table        |
                        |  (ephemeral on CI)         |
                        +-------------+--------------+
                                      |
                          get_ml_training_data()
                          (SQL query: WON/LOST/EXPIRED)
                                      |
                                      v
                        +----------------------------+
                        |  _build_features()         |
                        |  39 features per signal    |
                        |  extra_json merged in      |
                        +-------------+--------------+
                                      |
                            XGBoost > LightGBM > RF
                            StandardScaler + Pipeline
                            TimeSeriesSplit CV (5-fold)
                                      |
                                      v
                        +----------------------------+
                        |  rf_model.pkl              |  <-- DOES NOT EXIST
                        |  ml_weights.json           |  <-- exists, populated
                        +----------------------------+
                                      |
                              score_signal()
                              predict_proba -> ml_score
                                      |
                                      v
                        +----------------------------+
                        |  scanner.py applies:       |
                        |  - regime penalty (0.70x)  |
                        |  - volume penalty (0.80x)  |
                        |  - SHORT gate (>=0.90)     |
                        |  - MIN_ML_SCORE >= 0.65    |
                        +----------------------------+
```

### Feature Population Audit (281 closed picks in JSON)

| Feature | Data Source | Populated | Pct | Impact |
|---|---|---|---|---|
| `strategy_encoded` | strategy name hash | 281/281 | 100% | OK |
| `category_encoded` | pick category field | 281/281 | 100% | OK |
| `confidence` | strategy output | 281/281 | 100% | OK |
| `risk_reward` | computed TP/SL/entry | 281/281 | 100% | OK |
| `hour_of_day` / `day_of_week` | timestamp field | 281/281 | 100% | OK |
| `regime_encoded` | regime_at_entry | ~281/281 | ~100% | OK |
| `strategy_win_rate` | computed from DB | 281/281 | 100% | OK |
| `strategy_sharpe` | computed from DB | 281/281 | 100% | OK |
| `rsi_at_entry` | **strategy must emit** | **34/281** | **12%** | **RED FLAG** |
| `volume_ratio` | **strategy must emit** | **23/281** | **8%** | **RED FLAG** |
| `atr_at_entry` | **strategy must emit** | **14/281** | **5%** | **RED FLAG** |
| `spread_pct` | not populated | 0/281 | 0% | DEAD |
| `wick_ratio` | not populated | 0/281 | 0% | DEAD |
| `market_fear_greed` | **F&G API** | **0/281** | **0%** | **DEAD** |
| `funding_rate` | **Binance API** | **0/281** | **0%** | **DEAD** |
| `entry_distance_vwap` | not populated | 0/281 | 0% | DEAD |
| `orderbook_imbalance` | **Binance L2 depth** | **0/281** | **0%** | **DEAD** |
| `ema_position` | not populated | 0/281 | 0% | DEAD |
| `cvd_divergence` | stub (Phase 3b) | 0/281 | 0% | DEAD |
| `smoothed_momentum` | needs `close_prices` array | 0/281 | 0% | DEAD |
| `vpin` | VPIN module | 0/281 | 0% | DEAD |
| `ofi` | OFI module | 0/281 | 0% | DEAD |
| `galaxy_score` | LunarCrush API | 0/281 | 0% | DEAD |
| `accel_10` through `cci_20` (10 Kimi features) | needs `close_prices`/`high_prices`/`low_prices`/`volumes` arrays | 0/281 | 0% | DEAD |

### RED FLAGS

1. **Model file does not exist on disk** (`alpha_engine/data/rf_model.pkl` is missing). This means `is_trained = False` and ALL scoring falls through to the **heuristic fallback** every single run. The 39-feature ML model has NEVER successfully trained and persisted. The `ml_weights.json` file exists but is generated from `_save_weights()` which runs off strategy stats, not the ML model.

2. **26 out of 39 features are ALWAYS zero/default.** The ML model (if it ever trains) would learn from a feature matrix where 67% of columns are constant. These features provide zero information gain:
   - `market_fear_greed`, `funding_rate`, `orderbook_imbalance`, `ema_position`, `vpin`, `ofi`, `galaxy_score` -- data source APIs are called in scanner.py but the values are NOT saved into the `extra_json` field when picks are stored to the DB. The enrichment happens for live scoring only, never for training data.
   - `smoothed_momentum` + all 10 Kimi Blueprint features require `close_prices`/`high_prices`/`low_prices`/`volumes` arrays in the signal dict. These price history arrays are never stored in `closed_picks.json` or the DB.

3. **Even `rsi_at_entry` (88% null) and `volume_ratio` (92% null)** are mostly empty because many strategies don't emit these fields, and the scanner doesn't retroactively compute them before storing the pick.

4. **Heuristic fallback IS the production scorer.** Since `rf_model.pkl` doesn't exist, the `_heuristic_score()` method runs for every signal. This means the regime-aware bonuses (+0.08 for aligned trades, -0.12 for counter-regime longs) and funding rate adjustments work, but only because they read live signal data, not trained weights.

5. **281 closed picks > MIN_SAMPLES_TO_TRAIN (50)** -- the model SHOULD be training. Likely reason it fails: the CI ephemeral DB starts empty, `import_closed_picks_json()` runs, but the resulting DataFrame might have issues (extra_json parsing, etc.) or the model trains but the pkl file isn't committed back to the repo, so it's lost after each CI run.

---

## 2. Claude Gainer ML

### Flow Diagram

```
                        +----------------------------+
                        |  Binance USDT pairs        |
                        |  (ALL pairs > $500K vol)   |
                        |  1h klines, 168 bars       |
                        +-------------+--------------+
                                      |
                          data_fetcher.py (multi-source)
                          Binance -> OKX -> Bybit fallover
                          + CoinGecko enrichment (mcap, ath, atl)
                                      |
                                      v
                        +----------------------------+
                        |  compute_features_live()   |
                        |  30 features per coin      |
                        |  (20 original + 10 v3.0)   |
                        +-------------+--------------+
                                      |
                          predict_coins()
                          RF (0.45) + XGB (0.55) ensemble
                          StandardScaler transform
                                      |
                          IF model AUC < 0.50:
                            -> _heuristic_pump_score()
                                      |
                                      v
                        +----------------------------+
                        |  pump_probability per coin |
                        |  generate_picks() applies: |
                        |  - BUY threshold ~0.27     |
                        |  - SELL threshold ~0.20    |
                        |  - relative ranking floor  |
                        |  - BTC trend filter        |
                        +----------------------------+
                                      |
                                      v
                        +----------------------------+
                        | claude_live_picks.json     |
                        | (14 active, 39 resolved)   |
                        +----------------------------+


    TRAINING PIPELINE (separate: train_model.py):

    Binance 1h klines (200 coins, 168h)
           |
    build_features_for_coin() -> 30 features + label (>3% next 24h)
           |
    SMOTE-ENN rebalancing -> purged walk-forward split (75/2/23)
           |
    RF (depth 8, calibrated) + XGB (depth 5, calibrated)
           |
    -> claude_rf.joblib, claude_xgb.joblib, claude_scaler.joblib
```

### Feature Population Audit (53 picks, sample of 5)

| Feature Category | Example Features | Populated | Notes |
|---|---|---|---|
| Volume features (3) | vol_mcap_ratio, vol_change_24h/12h | ~15/20 populated | Real Binance data |
| Momentum features (3) | price_momentum_7d/3d/1d | populated | Computed from klines |
| RSI features (2) | rsi_14, rsi_slope | populated | Computed from closes |
| Bollinger features (2) | bb_width, bb_percentb | populated | Computed from closes |
| Pattern features (4) | consolidation, consec_green, mom_ignition, obv_div | partially 0 | Binary flags, 0 is valid |
| ATH/ATL features (2) | distance_from_ath/atl_pct | populated | From CoinGecko |
| mcap_tier (1) | mcap_tier | populated | log10 normalized |
| Compression/spike (2) | price_compression, relative_vol_spike | mostly 0 | Binary, 0 is valid |
| Fear/greed proxy (1) | fear_greed_proxy | populated | Computed heuristic |

### RED FLAGS

1. **Model AUC = 0.4078 (ANTI-PREDICTIVE).** The `training_meta.json` shows ROC-AUC of 0.4078, which is BELOW 0.50 (random). The code correctly detects this (`use_heuristic = model_auc < 0.50`) and falls back to `_heuristic_pump_score()`. **The RF+XGB ensemble is trained but its predictions are INVERTED -- worse than a coin flip.** All live picks are generated by the heuristic scorer, NOT the ML model.

2. **Model trained on only 20 features, code computes 30.** The `training_meta.json` says `num_features: 20` and lists only the original 20 features. The live scanner computes 30 features (v3.0 additions: yesterday_gainer, sector, hourly_volatility, etc.) but the model was trained on 20. The `predict_coins()` function handles this gracefully by using `model_meta.get("feature_names", FEATURE_COLS)` to select only the features the model expects, but the 10 new v3.0 features are completely wasted.

3. **Positive rate is ~1% (extreme class imbalance).** Only 1.26% of test samples are positive (>3% gain in 24h). Even with SMOTE-ENN, the model couldn't learn meaningful patterns. The precision is 1.0 but recall is 0.026 -- it almost never predicts positive, and when it does it's right, but that's useless for a scanner.

4. **Self-retraining loop may be degrading.** The `training_meta.json` shows `online_samples_used: 39` and version `1.0.2 (retrained)`. The `trigger_retraining.py` / `self_improver.py` scripts incorporate live picks into retraining, but with only 39 resolved picks mixed into 15K training samples, and the model already anti-predictive, retraining is not improving things.

5. **Heuristic scorer has no backtested validation.** The `_heuristic_pump_score()` uses hand-tuned weights (volume 0.25, momentum 0.20, etc.) without any systematic optimization. The 61.54% WR mentioned in comments needs verification.

---

## 3. KIMI Rise of the Claw ML Ranker

### Flow Diagram

```
                        +----------------------------+
                        | live_competition.json      |
                        | (275 closed picks across   |
                        |  all algorithms)           |
                        +-------------+--------------+
                                      |
                        _load_closed_picks()
                        (extracts closedPicks from
                         each algorithm's history)
                                      |
                                      v
                        +----------------------------+
                        | _build_features()          |
                        | 15 features per pick       |
                        | (9 algo-level + 6 market)  |
                        +-------------+--------------+
                                      |
                        RandomForestClassifier
                        (500 trees, depth 8, balanced)
                        TimeSeriesSplit CV (5-fold)
                                      |
                              AUC check >= 0.55
                                      |
                                      v
                        +----------------------------+
                        | rf_model.pkl               | <-- EXISTS (trained)
                        | ml_weights.json            | <-- per-algo probabilities
                        | ml_training_stats.json     | <-- AUC=0.7066
                        +----------------------------+
                                      |
                        predict_win_probability()
                        get_allocation_multiplier()
                                      |
                                      v
                        +----------------------------+
                        | live_scanner.py injects    |
                        | __ml_weights__ into        |
                        | all_data for ranking       |
                        +----------------------------+
```

### Feature Importance (from trained model, AUC=0.7066)

| Feature | Importance | Data Source | Populated | Assessment |
|---|---|---|---|---|
| `algo_wr` | **0.278** | tournament.json win rate | 275/275 | PRIMARY DRIVER |
| `symbol_enc` | **0.204** | symbol hash -> int | 275/275 | OK (symbol matters) |
| `algo_sharpe` | **0.175** | tournament.json Sharpe | 275/275 | OK |
| `algo_drought` | 0.093 | droughtScans counter | 275/275 | OK |
| `algo_closed` | 0.083 | closed pick count | 275/275 | OK |
| `algo_id_enc` | 0.079 | algo ID hash | 275/275 | OK |
| `algo_kelly` | 0.037 | Kelly fraction | 275/275 | OK |
| `category_enc` | 0.033 | stock/crypto/forex | 275/275 | OK |
| `tier_enc` | 0.018 | TIER_1 vs SCOUT | 275/275 | OK |
| `rsi_at_entry` | **0.000** | pick-level RSI | **0/275** | **DEAD** |
| `volume_ratio` | **0.000** | pick-level volume | **0/275** | **DEAD** |
| `fear_greed` | **0.000** | Fear & Greed index | **0/275** | **DEAD** |
| `risk_reward` | **0.000** | TP/SL ratio | **0/275** | **DEAD** |
| `hour_of_day` | **0.000** | entry hour UTC | **0/275** | **DEAD** |
| `btc_24h_change` | **0.000** | BTC price change | **0/275** | **DEAD** |

### RED FLAGS

1. **6 out of 15 features have ZERO importance and ZERO data.** The market-context features (`rsi_at_entry`, `volume_ratio`, `fear_greed`, `risk_reward`, `hour_of_day`, `btc_24h_change`) are all 0.0 importance because they are NEVER populated in `closedPicks` within `live_competition.json`. The `_extract_market_context()` method is well-written but gets defaults for every pick because the data isn't stored.

2. **The model is essentially a strategy-reputation scorer, not a signal scorer.** With 6 dead features, the model learns entirely from algo-level metadata (win rate, Sharpe, drought, pick count). It answers "which algorithm tends to win?" not "is THIS specific signal likely to win?". This is valuable but it's not signal-level ML.

3. **AUC of 0.7066 is the best of all three systems** but is partially misleading. Since the model only uses algo-level features, it's essentially memorizing which algorithms have historically performed well. This could overfit to recent algo performance and fail during regime changes.

4. **The `predict_win_probability()` function passes pick-level features** but they have no effect because the RF model assigned them zero weight. The feature row is correctly built in `_build_single_feature_row()` with market context, but training data never had these values, so the model ignores them.

5. **The model DOES successfully persist** (`rf_model.pkl` exists, loads on startup). This is the only ML system where the trained model survives across CI runs because the file is committed or cached.

---

## Cross-System Summary

### ML Effectiveness Matrix

| System | Model Exists | AUC | Actually Used | Effective Method |
|---|---|---|---|---|
| Alpha Engine | NO (pkl missing) | N/A | Heuristic | Hand-tuned rules with regime awareness |
| Claude Gainer ML | YES (3 files) | 0.4078 | Heuristic (AUC < 0.50) | Hand-tuned weighted features |
| KIMI ML Ranker | YES (pkl) | 0.7066 | YES (RF) | Algo-reputation scoring (not signal-level) |

### Critical Data Flow Gaps

```
PROBLEM 1: Training data doesn't store what scoring needs
+-----------------------------------------------------+
| At SCORING time, scanner enriches signal with:      |
|   funding_rate, orderbook_imbalance, fear_greed,    |
|   ema_position, VPIN, OFI, galaxy_score             |
|                                                      |
| At STORAGE time, pick goes to DB/JSON WITHOUT:      |
|   these enriched values (not in extra_json)          |
|                                                      |
| At TRAINING time, ML reads DB/JSON and gets:        |
|   all enriched features = 0/null/default             |
|                                                      |
| RESULT: Model trains on zeros, learns nothing       |
|         from the most valuable features             |
+-----------------------------------------------------+

PROBLEM 2: Price history arrays are never persisted
+-----------------------------------------------------+
| Kimi Blueprint features need close_prices[],        |
| high_prices[], low_prices[], volumes[]              |
| These exist at scan time but are not stored.        |
| Result: 10 features always compute to 0.0           |
+-----------------------------------------------------+

PROBLEM 3: CI ephemeral state
+-----------------------------------------------------+
| Alpha Engine trains model -> rf_model.pkl           |
| But pkl is not committed to repo                    |
| Next CI run: model is gone, back to heuristic       |
| The 281 closed picks DO exist in committed JSON     |
| but the trained model artifact doesn't survive      |
+-----------------------------------------------------+
```

### Specific Recommendations

#### Alpha Engine (Priority: HIGH)
1. **Store enriched features in extra_json.** In `scanner.py`, before calling `db.store_pick()`, serialize the enriched signal fields (funding_rate, fear_greed, orderbook_imbalance, etc.) into the `extra_json` column. This is a ~10-line fix.
2. **Commit the trained model pkl.** Add `alpha_engine/data/rf_model.pkl` to git (or use GitHub Actions artifacts) so the model persists across CI runs. Alternatively, train locally and commit.
3. **Remove or fix 26 dead features.** Either populate them (recommendation 1) or remove them from the FEATURES list. Training on 26 constant-zero columns adds noise and wastes model capacity.
4. **Store price history arrays for Kimi Blueprint features.** At minimum store last-50 closes in extra_json for the 10 derived features to work.

#### Claude Gainer ML (Priority: MEDIUM)
5. **Retrain with v3.0 features.** The model was trained on 20 features but code computes 30. Run `train_model.py` with fresh Binance data to get a 30-feature model.
6. **Investigate anti-predictive AUC.** AUC=0.4078 means predictions are inversely correlated with outcomes. Consider: (a) the model learned the wrong patterns from synthetic data, (b) the gain threshold of 3% doesn't match the feature timescale, (c) SMOTE-ENN is creating unrealistic synthetic samples. Try training WITHOUT SMOTE-ENN and with a higher gain threshold.
7. **The heuristic scorer is actually working.** With 61.54% WR claimed, validate this against resolved picks. If confirmed, the heuristic may be better than ML for this task.

#### KIMI ML Ranker (Priority: LOW — working but limited)
8. **Populate market-context features in closedPicks.** When closing a pick in `live_scanner.py`, store `rsi_at_entry`, `volume_ratio`, `fear_greed`, `risk_reward`, `hour_of_day`, `btc_24h_change` in the pick dict before writing to `live_competition.json`. This would give the RF model actual signal-level features.
9. **Don't remove dead features yet.** The model AUC is 0.7066 using only 9 features. Adding real data to the 6 dead features could improve it. Remove them only if they remain zero after fixing data flow.
10. **Consider overfitting to algo reputation.** The model's #1 feature is `algo_wr` (tournament win rate). This is backward-looking and may not predict future performance. Add a temporal decay or use only recent-window win rates.

---

### Files Referenced

| File | Role |
|---|---|
| `alpha_engine/ml_ranker.py` | 39-feature ML ranker (XGB/LGB/RF) |
| `alpha_engine/scanner.py` | Live scanner, applies ML scores |
| `alpha_engine/database.py` | SQLite persistence, ML training data export |
| `alpha_engine/data/closed_picks.json` | 281 closed picks (training data) |
| `alpha_engine/data/rf_model.pkl` | **MISSING** — model never persisted |
| `alpha_engine/data/ml_weights.json` | Strategy weights (from heuristic, not ML) |
| `claude_gainer_ml/live_scanner.py` | v4.0 gainer scanner with 30 features |
| `claude_gainer_ml/train_model.py` | Training pipeline (RF+XGB+SMOTE+calibration) |
| `claude_gainer_ml/models/training_meta.json` | AUC=0.4078 (anti-predictive) |
| `claude_gainer_ml/models/claude_rf.joblib` | Trained but anti-predictive |
| `claude_gainer_ml/tracker/claude_live_picks.json` | 53 picks (14 active, 39 resolved) |
| `KIMI_RISEOFTHECLAW/ml_signal_ranker.py` | 15-feature RF ranker |
| `KIMI_RISEOFTHECLAW/data/live_competition.json` | 275 closed picks |
| `KIMI_RISEOFTHECLAW/data/rf_model.pkl` | Trained model (AUC=0.7066) |
| `KIMI_RISEOFTHECLAW/data/ml_training_stats.json` | Training stats with feature importances |
