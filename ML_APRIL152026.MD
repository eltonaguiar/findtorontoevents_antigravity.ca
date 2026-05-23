# ML Systems QA Audit — April 15, 2026

## Executive Summary

We operate **7 ML systems** across this codebase. After thorough code review, data inspection, and performance analysis:

- **3 systems** are production-grade with real training data and dashboard integration
- **1 system** uses synthetic labels but is still useful for regime routing
- **1 system** is in heuristic/fallback mode awaiting CI training
- **1 system** (1,746 model files, 3.6 GB) is **completely orphaned** — never wired to anything
- **1 system** (Claude Gainer) has real data but shows **negative PnL** (-140% cumulative)

Overall win rate on alpha_engine closed picks: **90W / 145L = 38.3% WR** — the ML score shows only +0.014 discrimination between winners and losers, suggesting **ML is adding marginal signal at best**.

---

## System-by-System Analysis

### 1. Alpha Engine ML Ranker ⭐⭐⭐⭐⭐

| Attribute | Value |
|-----------|-------|
| **Location** | `alpha_engine/ml_ranker.py` |
| **Model** | `alpha_engine/data/rf_model.pkl` (365 KB, trained 2026-04-15) |
| **Architecture** | XGBoost + LightGBM + RandomForest stacking |
| **Training Data** | REAL — 313 closed picks from `closed_picks_fast.json` |
| **Labels** | Triple-barrier: WON (+1), LOST (-1), EXPIRED (0) |
| **Features** | 40 → ~15-20 via Boruta selection |
| **CV Method** | Purged walk-forward (5 folds, 2% embargo) |
| **Integration** | ✅ All scanners via `ml_composite = ml_score × 0.6 + confidence × 0.3 + forward_wr × 0.1` |
| **Status** | ACTIVE, production |

**What it does well:**
- Proper purged CV prevents temporal leakage (Phase 11 fixed AUC=1.0 overfitting)
- Boruta feature selection ensures statistical significance
- Drift detection triggers retrain at <45% accuracy
- Incremental warm-start training on new picks

**Concern — Marginal discrimination:**
```
Feature        WON avg    LOST avg    Diff
confidence     0.767      0.760      +0.007   (almost no signal)
ml_score       0.777      0.763      +0.014   (weak signal)
hold_days      1.722      0.759      +0.964   (winners held longer)
mfe            0.046      0.017      +0.028   (winners move further in favor)
mae           -0.012     -0.037      +0.024   (losers drawdown more)
pnl_pct        0.026     -0.025      +0.051
```

The ml_score and confidence show almost zero discrimination between WON and LOST picks. The strongest signal is actually **hold_days** (winners survive ~2x longer) and **mfe/mae** (winners have higher favorable excursion). These are post-hoc features that can't be used for prediction.

**Verdict:** The ML ranker methodology is excellent but may be predicting noise. With 313 samples split across 50+ strategies, per-strategy sample sizes are too small for reliable ML learning.

---

### 2. HyroTrader ML Pick Optimizer ⭐⭐⭐

| Attribute | Value |
|-----------|-------|
| **Location** | `tools/hyro_ml_pick_optimizer.py` |
| **Model** | NOT YET TRAINED (heuristic fallback mode) |
| **Architecture** | GradientBoosting + RandomForest |
| **Training Data** | Backtest pseudo-labels (11 samples, below 10 minimum) |
| **Features** | 26 features |
| **Integration** | ✅ Dashboard Tables 4-5, ML badges on Tables 2-3 |
| **Status** | Heuristic mode — sklearn not available locally; CI has `pip install scikit-learn` |

**What it does well:**
- Heuristic fallback produces meaningful edge scores without ML
- Dashboard integration is complete (ready for ML when trained)
- Drift detection built in

**Concern:** No actual ML model has been trained yet. Currently running on pure heuristics (technical indicators + strategy affinity rules). The system needs real hyrotrader closed trades to train on — these would need to come from the dashboard's outcome tracking.

**Action needed:** Accumulate hyrotrader closed outcomes, then retrain with real data.

---

### 3. ML Battleground System A — "The Filter" ⭐⭐⭐⭐⭐

| Attribute | Value |
|-----------|-------|
| **Location** | `ml_battleground/system_a_filter/` |
| **Model** | `filter_xgb.joblib` |
| **Architecture** | XGBoost classifier (200 trees, depth 4, isotonic calibrated) |
| **Training Data** | REAL — Triple-barrier labeling on Binance OHLCV history |
| **Features** | 38 features incl. fractional differentiation (López de Prado AFML Ch.5) |
| **CV Method** | Purged walk-forward (5 folds, 50-bar purge, 25-bar embargo) |
| **Integration** | ✅ System A scanner → dashboard |
| **Closed Picks** | 19 (all negative PnL in sample checked) |
| **Status** | ACTIVE but underperforming |

**What it does well:**
- Research-grade feature engineering (fractional differencing, Fear & Greed, funding rates)
- Proper SMOTE balancing on train folds only (no leakage)
- Isotonic calibration for reliable probabilities
- Triple-barrier labeling is industry standard

**Concern:** All 19 closed picks sampled show negative PnL (e.g., DOGEUSDT -12%, OPUSDT -10.5%, FETUSDT -14.6%). Despite excellent methodology, real-world performance is poor. This could be:
1. Market regime shift since training (Feb 2026 crypto crash)
2. Entry threshold (0.65) too low
3. Training data period not representative of live period

**Action needed:** Retrain on recent data (March-April 2026). Consider raising entry threshold to 0.70-0.75.

---

### 4. ML Battleground System B — "The Regime" ⭐⭐⭐

| Attribute | Value |
|-----------|-------|
| **Location** | `ml_battleground/system_b_regime/` |
| **Model** | `regime_xgb.joblib` |
| **Architecture** | XGBoost multi-class (4 regimes: trending_up/down, range_bound, high_vol) |
| **Training Data** | SYNTHETIC — Rule-based regime labels (ADX/DI+/DI- thresholds) |
| **Features** | 20 features |
| **Integration** | ✅ System B scanner → dashboard |
| **Closed Picks** | 19 (all negative PnL in sample) |
| **Status** | ACTIVE but **trained on synthetic labels** |

**What it does well:**
- Regime classification conceptually valid (route strategies by market state)
- Proper CV methodology
- 56.6% WR on backtest (noted in scanner docstring)

**Critical flaw — Synthetic labels:** The model learns to predict "what regime is this?" based on rules (ADX > 25 → trending). But it never validates "does this regime label lead to profitable trades?" The regime classification might be accurate but useless for making money.

**Action needed:** **RETRAIN WITH REAL LABELS.** Instead of rule-based regimes, label regimes *backward* from closed trades:
- Look at each closed trade's market context → was the trade profitable?
- Group profitable trades by their market conditions → those are the "good regimes"
- Train the model to detect "profitable regime" not just "trending up"

---

### 5. ML Battleground System C — "The Neural Net" ⭐⭐⭐⭐⭐

| Attribute | Value |
|-----------|-------|
| **Location** | `ml_battleground/system_c_deeplearn/` |
| **Model** | `gru_attention.pt` (PyTorch) |
| **Architecture** | GRU-Attention (128 hidden, 2 layers, 4-head attention, multi-task) |
| **Training Data** | REAL — Triple-barrier multi-task (entry_prob + TP_dist + SL_dist) |
| **Features** | 25 features incl. Fibonacci (Osler 2000), fractional diff |
| **CV Method** | Purged walk-forward (5 folds) |
| **Integration** | ✅ System C scanner → dashboard |
| **Closed Picks** | 5 (all negative PnL) |
| **Status** | ACTIVE but barely producing picks |

**What it does well:**
- State-of-the-art architecture (attention + GRU + multi-task learning)
- Cross-timeframe fusion (15m + 1h sequences)
- Research-backed features (Fibonacci Osler 2000, López de Prado frac diff)
- Multi-task learning (predicts entry prob AND optimal TP/SL distances)

**Concern:** Only 5 closed picks, all negative PnL. The entry threshold (0.65) combined with min risk/reward (1.5) creates extremely selective filtering — produces almost no signals. This system's methodology is the most sophisticated but it's barely participating.

**Action needed:** Lower entry threshold to 0.55-0.60 temporarily to generate more signals for performance evaluation. Can tighten back once we have 50+ closed trades.

---

### 6. Claude Gainer ML ⭐⭐⭐

| Attribute | Value |
|-----------|-------|
| **Location** | `claude_gainer_ml/` |
| **Models** | `claude_rf.joblib` + `claude_xgb.joblib` (retrained 2026-04-14) |
| **Architecture** | RandomForest + XGBoost ensemble, calibrated |
| **Training Data** | REAL — Binance 1h klines, multi-source failover |
| **Target** | Will this coin gain >3% in next 24 hours? |
| **Features** | 30 features (v3.0 incl. yesterday-gainer, sector momentum) |
| **Integration** | ✅ Live scanner → dashboard via outcome_resolver |
| **Status** | ACTIVE, daily retraining |

**Performance (the ugly truth):**
```
Main Gainer Scanner:
  Total picks: 166
  Win rate: 38.0% (63W / 103L)
  Avg win: +7.83%
  Avg loss: -6.15%
  Total PnL: -140.13%
  Profit factor: 0.78
  Sharpe: -1.11

Short-Term Subsystem:
  TP_HIT: 532, SL_HIT: 277, EXPIRED: 1,191
  WR (TP vs SL): 65.8%
  But 59.6% of picks expire (never hit TP or SL)
```

**Analysis:** The short-term subsystem looks great on TP vs SL (65.8% WR) but 60% of picks expire without resolution — meaning most signals are too weak to trigger either target. The main scanner is losing money overall (-140% cumulative). The adaptive threshold has been tightening repeatedly (now 0.80) because WR is only 27%.

**What's going right:**
- Daily retraining keeps model fresh
- Feature engineering is creative (yesterday-gainer edge at 62.5% continuation)
- Multi-source data failover is robust
- Short-term TP vs SL ratio is genuinely good

**What's going wrong:**
- 3% gain target is too easy to "almost hit" → many expires
- Main scanner confidence threshold hasn't prevented losers
- -140% cumulative PnL means this system is net destructive

**Action needed:**
1. Raise gain target from 3% → 5% to reduce false positives
2. Tighten entry threshold (already at 0.80, may need model architecture change)
3. Add exit timing logic — many picks expire because they're entered at wrong time
4. Consider: this system predicts *direction* but not *timing* — maybe add time-to-target as a feature

---

### 7. ML Crypto Predictor ❌ ORPHANED

| Attribute | Value |
|-----------|-------|
| **Location** | `ml_crypto_predictor/` |
| **Models** | 1,746 `.joblib` files across 47 symbols, 8 timeframes |
| **Architecture** | GradientBoosting + RandomForest per symbol-timeframe pair |
| **Training Data** | REAL — Local SQLite crypto_data.db historical klines |
| **Target** | >2% gain within 12h (base), >0.5% gain within 6h (scalping) |
| **Disk Usage** | **3,664 MB (3.6 GB)** |
| **Integration** | ❌ NONE — no scanner, no dashboard, no output |
| **Status** | ORPHANED since 2026-02-22 |

**Training metrics (sampling):**
```
Pair          Model     Accuracy   Precision   F1
ALGO/USDT     GB        0.754      0.286       0.242
BTC/USDT      GB        0.770      0.096       0.125   ← basically zero precision
DOGE/USDT     GB        0.764      0.000       0.000   ← can't identify ANY winners
SOL/USDT      RF        0.521      0.281       0.360
TRX/USDT      GB        1.000      0.000       0.000   ← class imbalance (no positive labels)
```

**Analysis:** High accuracy but near-zero precision and F1 across most pairs. The models are learning to predict "no gain" (majority class) rather than identifying actual gainers. TRX/USDT at 100% accuracy with 0% precision/F1 is a classic class imbalance failure (just predicts "no" every time).

**Verdict:** These 1,746 models and 3.6 GB of disk are providing zero value. The per-symbol approach doesn't scale, the models aren't calibrated, there's no drift detection, and there's no integration path.

**Recommendation:** **ARCHIVE** the directory. The concept (per-symbol prediction) has merit but the execution failed. If resurrecting, consolidate into a single model with symbol as a feature (not separate models per pair).

---

## Models Trained on Pseudo/Synthetic Data

| System | What's Synthetic | Impact | Fix |
|--------|-----------------|--------|-----|
| **System B Regime** | Rule-based regime labels (ADX/DI thresholds) | Predicts regime, not profitability | Retrain with closed-trade-based regime labels |
| **HyroTrader Optimizer** | Backtest pseudo-labels (11 samples) | Not enough data to train | Accumulate real hyrotrader outcomes |
| **Claude raw_market_data.json** | Contains `"synthetic": true` flag | Training data file has synthetic marker | Verify actual training pipeline uses Binance, not this file |

**Note:** Systems A and C use triple-barrier labeling on real OHLCV data — this is NOT synthetic. The "triple-barrier" approach is the gold standard from López de Prado's "Advances in Financial Machine Learning."

---

## The Hard Question: Are We ML-ing the Wrong Thing?

### What We're Predicting vs. What Matters

| What We Predict | What Actually Matters |
|----------------|----------------------|
| "Will price hit TP?" | "What is the expected risk-adjusted return?" |
| "Is this a good entry?" | "Is this a good entry *right now* at *this* price?" |
| "What regime is the market in?" | "Which strategy makes money in this regime?" |
| "Will this coin gain 3%?" | "Will this coin gain 3% *before* dropping 2%?" |

### Overlooked Opportunities

1. **EXIT TIMING** — We have no ML for when to exit. Every system uses fixed TP/SL, but the most profitable trades often run past TP while losers should be cut before SL. A trailing-exit ML model could dramatically improve PnL.

2. **POSITION SIZING** — No ML determines *how much* to bet. Kelly criterion + ML confidence = position sizing that compounds winners and minimizes losers. Right now every pick is implicitly equal weight.

3. **STRATEGY SELECTION META-MODEL** — We have 50+ strategies with wildly different win rates (swing_structure 83%, community_london_breakout 0%). Instead of ML-filtering individual signals, build a meta-model that predicts "which strategies will work THIS WEEK" based on current market conditions, then only run those strategies.

4. **CORRELATION/PORTFOLIO RISK** — No ML considers correlation between active picks. If we have 5 LONG crypto picks, they're all correlated. A portfolio-level ML that rejects redundant picks could improve risk-adjusted returns.

5. **TIME-OF-DAY EDGE** — The data shows winners have avg hold_days=1.72 vs losers at 0.76. There may be a time/session edge we're not exploiting. Asian session, London open, NY close — these have known biases.

6. **FEATURE IMPORTANCE ALIGNMENT** — The ml_score shows +0.014 discrimination. This is almost random. Instead of adding more models, we should investigate WHY the existing model can't discriminate. Possible reasons:
   - Too many strategies dilute the signal (each strategy has different dynamics)
   - Features are computed at entry time but the outcome depends on what happens after
   - The market regime at entry time matters more than technical indicators

### What We Should Be ML-ing Instead

**Priority 1: Strategy-Regime Router**
- Input: Current market conditions (volatility, trend, volume, macro)
- Output: Ranked list of strategies expected to perform well now
- Training data: All 313 closed picks with their market context at entry time
- This replaces "filter bad picks" with "only generate picks from currently-working strategies"

**Priority 2: Dynamic Exit Optimization**
- Input: Running position data (current PnL, time held, market momentum)
- Output: Optimal action (hold, partial-take, full-exit)
- Training data: MFE/MAE curves from closed picks
- Currently we know winners have +4.6% MFE and losers have -3.7% MAE — use this

**Priority 3: Ensemble Confidence Calibration**
- Input: All ML system scores (ranker, filter, regime, neural, gainer)
- Output: True probability of profit (calibrated)
- This replaces ad-hoc blending (`0.6 × ml_score + 0.3 × confidence + 0.1 × forward_wr`) with a learned weighting that adapts to which system is currently accurate

---

## Strategy Performance Highlights

Top performers (from 313 closed picks):
```
Strategy                         W    L    WR    Notes
options_25delta_skew             4    0   100%   Small sample but perfect
day_of_week_effect               3    0   100%   Exploits calendar anomaly
hayes_liquidity_index            3    0   100%   Macro liquidity signal
swing_structure                  5    1    83%   Breakout plays
cumulative_delta_divergence      4    1    80%   Order flow
hurst_mean_reversion             3    1    75%   Mean reversion
volume_profile_poc_reversion     3    2    60%   POC reversion
proven_vwap_mean_reversion       3    2    60%   VWAP plays
markov_zone_transition           3    2    60%   Zone transitions
```

Worst performers:
```
community_london_breakout_v2     0    8     0%   KILL THIS
tsmom_28d                        0    4     0%   Time-series momentum failing
ctrend_multi_horizon             0    3     0%   Multi-horizon trend
ascending_triangle_breakout      0    2     0%   Pattern recognition failing
bollinger_keltner_squeeze        1    6    14%   Squeeze breakout not working
autocorrelation_exploiter        3   10    23%   Negative edge
proven_propfirm_conservative     2    6    25%   Ironic name
```

---

## Action Items (Prioritized)

### Immediate (This Week)
1. [ ] **Kill `community_london_breakout_v2_forex`** — 0W/8L, pure loss generator
2. [ ] **Kill `tsmom_28d`** and **`ctrend_multi_horizon`** — 0% WR strategies
3. [ ] **Archive `ml_crypto_predictor/`** — 3.6 GB of unused models
4. [ ] **Verify Claude Gainer training data** — `raw_market_data.json` has `"synthetic": true` flag

### Short-Term (This Month)
5. [ ] **Retrain System B** with trade-outcome-based regime labels
6. [ ] **Lower System C threshold** from 0.65 → 0.55 to generate evaluation data
7. [ ] **Raise Claude Gainer target** from 3% → 5%, reduce expiration rate
8. [ ] **Build Strategy Selection Meta-Model** — predict which strategies work this week

### Medium-Term (Q2 2026)
9. [ ] **Build EXIT ML** — dynamic trailing stops based on MFE/MAE patterns
10. [ ] **Build Ensemble Calibrator** — replace hardcoded blending weights with learned weights
11. [ ] **Add position sizing** — Kelly criterion × ML confidence
12. [ ] **Portfolio correlation filter** — reject redundant correlated picks

---

## Conclusion

We have strong ML *infrastructure* (proper CV, drift detection, calibration) but **weak ML *signal*** (confidence shows +0.007 discrimination, ml_score shows +0.014). The systems are well-built but may be trying to predict something that's inherently unpredictable at the individual-pick level.

The biggest opportunities aren't in making existing ML better — they're in **ML-ing different things**: strategy selection timing, dynamic exits, and ensemble calibration. These meta-level predictions can work with our existing 313+ closed picks as training data and would compound the value of our existing (imperfect) signal generators.

*Generated: April 15, 2026 | Analysis covers 313 closed alpha picks, 2,000 claude short-term picks, 43 battleground picks, 1,746 orphaned predictor models*
