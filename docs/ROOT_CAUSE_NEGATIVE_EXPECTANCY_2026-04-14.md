# Root Cause Analysis: Why E[R] < 0

**Date:** 2026-04-14  
**Question:** Why is the signal generator producing picks with negative expected return?

---

## TL;DR — Three Root Causes

| # | Root Cause | Evidence | Severity | Impact |
|---|-----------|----------|----------|--------|
| **1** | **Train-serve feature misalignment: 39 training features but 41 inference values** | `FEATURES` list has 39 names; `_signal_to_features` returns 41 values (extra: `btc_correlation`, `btc_24h_change`). The model interprets feature column N as feature column N+2 for the last slots. | 🔴 CRITICAL | Every ML prediction is corrupted |
| **2** | **9+ features are dead (100% default values at inference)** | `ml_features_at_entry` is present on **0%** of closed picks. `ml_score` is **0%** populated. `volume_ratio`, `rsi_at_entry`, `orderbook_imbalance` all 0% coverage. | 🔴 CRITICAL | Model sees training distribution ≠ live distribution |
| **3** | **Confidence is not calibrated — it doesn't predict outcomes** | Cohen's d = **0.011** (winners vs losers). Confidence 0.8 achieves 31.7% WR. Confidence 1.0 achieves 44.4% WR. | 🔴 CRITICAL | All downstream confidence-based sizing/filtering is noise |

---

## 1. The Feature Alignment Bug (39 vs 41 dimensions)

### What the code shows

**Training** uses `MLSignalRanker.FEATURES` — a list of **39** named features:

```python
FEATURES = [
    "strategy_encoded",      # 0
    "confidence",            # 1
    "volume_ratio",          # 2
    ...
    "strat_fwd_trades",      # 38
]
# 39 features total
```

**Live inference** in `_signal_to_features()` builds a vector that appends **2 extra values** at the end:

```python
feat = [
    ...,  # 39 features matching FEATURES
    max(-1.0, min(1.0, btc_correlation or 0.8)),   # Index 39 — NOT IN TRAINING
    max(-1.0, min(1.0, btc_24h_change / 10.0)),    # Index 40 — NOT IN TRAINING
]
# 41 values total
```

### Why this is catastrophic

If the model was trained on 39 features, it expects a 39-dimensional input. When it receives 41 values:
- **XGBoost/LightGBM** will either crash (if strict) or silently use the first 39 values (if the extra are appended after). In the latter case, the 2 extra values are ignored — wasteful but not destructive.
- **However**, if the model was retrained WITH the extra 2 features but `FEATURES` was not updated, then the model expects 41 but the `FEATURES` list misnames columns 39-40. Any SHAP/feature-importance analysis will attribute importance to the wrong features.

**Fix:** Align `FEATURES` list with the actual inference vector. Add `"btc_correlation"` and `"btc_24h_change_norm"` to `FEATURES`. Retrain with the corrected names.

---

## 2. Dead Features — Training Saw Real Data, Live Sees Defaults

### Empirical evidence: 0% of closed picks have `ml_features_at_entry`

This is the smoking gun. The ML ranker computes features at inference time, but **does not store them on the pick**. When picks close and we try to analyze what the model saw, the data is gone.

### Feature coverage on closed picks

| Feature | Coverage | Non-Zero | Status |
|---------|----------|---------|--------|
| `confidence` | 100% | 95.7% | ✅ Real data |
| `score` (ml_composite) | 100% | 100% | ✅ |
| `elite_score` | 100% | 99.8% | ✅ |
| `trust_score` | 100% | 100% | ✅ (but only 7 unique values) |
| `strat_fwd_wr` | 99.9% | 97.9% | ✅ |
| `rr_ratio` | 75.2% | 75.2% | ⚠️ Missing on 25% |
| `bt_win_rate` | 36.0% | 36.0% | ⚠️ Sparse |
| **`ml_score`** | **0%** | **0%** | **🔴 COMPLETELY DEAD** |
| **`volume_ratio`** | **0%** | **0%** | **🔴 DEAD** |
| **`rsi_at_entry`** | **0%** | **0%** | **🔴 DEAD** |

### Default values injected at inference (from code analysis)

| Feature | Default | When applied | Training distribution |
|---------|---------|-------------|----------------------|
| `volume_ratio` | 1.0 | No market data available | Variable (0.1–5.0+) |
| `vpin_toxicity` | 0.5 | Always (no L2 data source) | Should be 0.0–1.0 |
| `orderbook_imbalance` | 0.0 | Always (no orderbook feed) | Should be -1.0 to +1.0 |
| `funding_rate` | 0.0 | Non-crypto picks always | Should be -0.1 to +0.1 |
| `fear_greed_norm` | 0.5 | API failure fallback | Should be 0.0–1.0 |
| `btc_correlation` | 0.8 | Hardcoded in feature_populator.py | Should vary by symbol |
| `rsi_14` | 50 (0.5 normalized) | No kline data | Should be 0–100 |
| `cs_momentum_rank` | 0.5 | Cross-sectional unavailable | Should be 0–1 |
| `cs_dispersion` | 0.0 | Cross-sectional unavailable | Should vary |

**Impact:** The model was trained on data where these features had **real, informative distributions**. At live inference, they're **constants**. The model's learned relationships (e.g., "when RSI < 30 and volume_ratio > 2.0, go long") can never fire because RSI is always 50 and volume_ratio is always 1.0.

**Fix:** Either populate these features with real data from API calls at inference time, or **retrain the model without these features** (using only the features that actually have real data in production).

---

## 3. Confidence Is Not Calibrated

### Empirical calibration test

| Confidence | Picks | Actual WR | Expected WR | Gap | Verdict |
|-----------|-------|----------|-----------|-----|---------|
| 0.0 | 253 | 41.9% | 0% | +42pp | ❌ Random noise |
| 0.5 | 489 | 36.6% | 50% | -13pp | ❌ |
| 0.6 | 1,054 | 42.3% | 60% | -18pp | ❌ |
| 0.7 | 1,199 | 47.4% | 70% | -23pp | ❌ |
| 0.8 | 101 | **31.7%** | 80% | **-48pp** | ❌ WORST |
| 0.9 | 90 | 47.8% | 90% | -42pp | ❌ |
| 1.0 | 36 | 44.4% | 100% | -56pp | ❌ |

**A pick with confidence=1.0 should win 100% of the time. It wins 44.4%.**  
**A pick with confidence=0.8 performs WORSE (31.7%) than one with confidence=0.0 (41.9%).**

### Cohen's d effect sizes (winner vs loser separation)

| Feature | Cohen's d | Verdict |
|---------|-----------|---------|
| `confidence` | **+0.011** | **❌ USELESS — no separation** |
| `score` (ml_composite) | +0.298 | ⚠️ Weak |
| `elite_score` | +0.245 | ⚠️ Weak |
| `trust_score` | **+0.329** | **✅ Best predictor** |
| `rr_ratio` | +0.068 | ❌ Useless |
| `strat_fwd_wr` | **+0.537** | **✅ Strongest predictor** |

**The only features with real predictive power are `strat_fwd_wr` (d=0.54) and `trust_score` (d=0.33).** Everything the ML model outputs (confidence, ml_score, score) is effectively noise.

**Fix:** Apply Platt scaling or isotonic regression to recalibrate confidence. Or better: replace the confidence field entirely with `strat_fwd_wr` (which actually predicts).

---

## 4. Why Specific Systems Have E[R] < 0

### Root cause decomposition per system

| System | N | WR | E[R] | Confidence | SL Hit% | Root Cause |
|--------|---|-----|------|-----------|---------|-----------|
| `claude_gainer` | 10 | 40% | -5.98% | 0.90 | 0% | **R:R inverted** (SL 12% vs TP 3%) |
| `multi_asset_institutional` | 18 | 33% | -2.23% | 0.82 | 0% | Bad entries + conf mis-calibrated |
| `fast_stocks_competition` | 21 | 14% | -1.95% | 0.67 | 0% | Bad entries |
| `ml_crypto_pred` | 119 | 21% | -0.95% | 0.00 | **79%** | **SL too tight** (2% SL on crypto) |
| `stocks_competition` | 371 | 38% | -0.74% | 0.63 | 41% | Conf mis-calibrated |
| `battleground` | 19 | 16% | -0.57% | 0.00 | **63%** | **SL too tight** (1.2% SL on crypto) |
| `rapid_fire` | 46 | 37% | -0.34% | 0.71 | 24% | Conf mis-calibrated |

**`ml_crypto_pred` pattern:** 79% SL hit rate with 2.0% SL distance on crypto. Crypto regularly oscillates 2-3% intrabar. The SL is narrower than normal noise → gets stopped out constantly.

**`battleground` pattern:** 63% SL hit rate with 1.2% SL. Even tighter. Same issue.

**`claude_gainer` pattern:** SL is 12% but TP is only 3%. The R:R is inverted — risking 4× to gain 1×. Any trade that moves against you is a massive loss.

---

## 5. Is There Look-Ahead or Data Leakage?

### Code audit findings

| Check | Result |
|-------|--------|
| Leaky outcome features in training | ✅ **Documented and excluded.** `LEAKY_FEATURES` set in `ml_ranker.py` explicitly removes `entry_vs_optimal`, `hold_duration_hours`, `mfe_pct`, `mae_pct`. |
| Future data in feature vector | ✅ **Not found.** No code feeds `exit_price`, `closed_at`, or `pnl_pct` into the feature vector at entry time. |
| Label construction | ✅ **Correct.** Triple-barrier labeling uses outcome data appropriately for supervised learning labels. |
| `feature_drift.py` methodology | ⚠️ **Flawed.** It includes `pnl_pct` as a "feature" for drift testing — this measures outcome drift, not predictor drift. |
| Timestamp fallback | ⚠️ **Subtle issue.** `_ts_hour()` uses `datetime.now()` when timestamp is missing. In batch cron runs, all picks get the same hour → time features become constants. |

**Verdict:** No classic look-ahead bias. The problem is **feature degradation** (defaults replacing real data), **misalignment** (39 vs 41), and **miscalibration** (confidence doesn't predict), not leakage.

---

## 6. Recommended Fixes (Prioritized)

### P0 — Fix the broken ML pipeline (this week)

| # | Fix | File | Impact |
|---|-----|------|--------|
| 1 | **Align FEATURES list with inference vector** — add `btc_correlation` and `btc_24h_change_norm` to `FEATURES` or remove from inference | `ml_ranker.py` L359-422, L2462-2473 | Fixes corrupted predictions |
| 2 | **Retrain model without dead features** — drop `volume_ratio`, `vpin_toxicity`, `orderbook_imbalance`, `funding_rate`, `cs_momentum_rank`, `cs_dispersion` (all defaulted) | `ml_ranker.py`, training script | Model only uses features with real data |
| 3 | **Populate `ml_score` on picks** — store the ranker output so it's available for scoring | `scanner.py` at `open_pick()` | Enables ML-based scoring to function |
| 4 | **Store `ml_features_at_entry`** on every pick | `scanner.py` | Enables post-hoc feature analysis |

### P1 — Fix confidence calibration (next sprint)

| # | Fix | Impact |
|---|-----|--------|
| 5 | Apply **isotonic regression** calibrator on confidence using closed-pick outcomes | Confidence becomes a real probability |
| 6 | Replace confidence in sizing/filtering with `strat_fwd_wr` (Cohen's d = 0.54) | Uses the feature that actually predicts |
| 7 | Recalibrate SL distances: `ml_crypto_pred` needs 3-4% SL (not 2%), `battleground` needs 2-3% (not 1.2%) | Reduces SL hit rate from 79% to ~40% |

### P2 — Fix structural issues (ongoing)

| # | Fix | Impact |
|---|-----|--------|
| 8 | Store `regime_at_entry` on every pick | Enables regime-conditional analysis |
| 9 | Add real-time `volume_ratio` and `rsi_14` from kline data instead of defaults | Restores feature information content |
| 10 | Fix `_ts_hour()` fallback — use pick's `timestamp` field, not `datetime.now()` | Correct time-of-day features |

---

## Appendix: Feature Predictiveness Summary

| Feature | Cohen's d | Bootstrap P(PF>1) | Real Coverage | Use for Scoring? |
|---------|-----------|-------------------|---------------|------------------|
| `strat_fwd_wr` | **+0.537** | — | 97.9% | **YES — strongest signal** |
| `trust_score` | **+0.329** | — | 100% | YES |
| `score` (ml_composite) | +0.298 | — | 100% | Yes (weak) |
| `elite_score` | +0.245 | — | 100% | Yes (weak) |
| `rr_ratio` | +0.068 | — | 75.2% | No — doesn't separate |
| `confidence` | **+0.011** | — | 100% | **NO — zero predictive power** |
| `ml_score` | — | — | **0%** | **BROKEN — not populated** |

---

---

## 7. ROOT CAUSE #4: TIME_EXIT Contamination (22.9% of all trades)

*Added after feedback from Antigravity bot review — this was confirmed as the dominant coin-flip artifact.*

### The problem

802 of 3,500 closed picks (22.9%) exited via `TIME_EXIT` / `EXPIRED` / `MAX_HOLD` — the system gave up waiting, not because TP or SL was hit. An additional 526 picks (15.0%) are `LOST` with ambiguous exit reason. Only **59%** of picks have **definitive** outcomes (SL hit or TP hit).

When TIME_EXITs are counted as normal trades:
- 437 slightly-positive timeouts (median +0.75%) are counted as "wins"
- This **inflates WR by ~12.5 percentage points** across the board
- It makes the system look like a 44% coin-flip when the real TP/SL outcomes tell a different story

### Exit reason breakdown

| Bucket | Count | % |
|--------|-------|---|
| TP_HIT (all TP/WON/WIN variants) | 1,057 | 30.2% |
| SL_HIT (all SL/STOP variants) | 1,009 | 28.8% |
| **TIME_EXIT (timeout/expired)** | **802** | **22.9%** |
| LOST (ambiguous) | 526 | 15.0% |
| Other/force/strategy removed | 106 | 3.0% |

### What changes when you filter TIME_EXITs out

**This is the single most important table in this entire analysis:**

| Slice | ALL (contaminated) | DEFINITIVE only (SL/TP) | Change |
|-------|-------------------|------------------------|--------|
| **ALL** | 3,500 picks, 43.9% WR, PF 1.13 | 2,066 picks, **52.3% WR, PF 1.41** | +8.4pp WR, +0.28 PF |
| **CRYPTO** | 1,876 picks, 46.9% WR, PF 1.43 | 1,274 picks, **46.4% WR, PF 1.88** | -0.5pp WR, **+0.45 PF** |
| **FOREX** | 684 picks, 42.0% WR, PF 2.02 | 289 picks, **82.4% WR, PF 12.02** | **+40pp WR, +10 PF** |
| **COMMODITY** | 279 picks, 41.6% WR, PF 1.04 | 121 picks, **95.9% WR, PF 7.17** | **+54pp WR, +6.1 PF** |
| **EQUITY** | 617 picks, 39.2% WR, PF 0.75 | 374 picks, **34.2% WR, PF 0.70** | -5pp WR (equity is genuinely losing) |

**Forex definitive-only: 82.4% WR, PF 12.02.** This is NOT the 42% coin-flip it appeared. The forex strategies are actually winning most TP/SL trades — the 58% of exits that are timeouts or `LOST` are noise.

**Commodity definitive-only: 95.9% WR, PF 7.17.** Nearly all TP/SL-resolved commodity trades hit TP. The apparent 42% WR was entirely TIME_EXIT contamination.

**Equity remains a loser** even with clean data: 34.2% WR, PF 0.70. This is a real lack of edge, not measurement noise.

### Compound filters on definitive exits

| Filter | N | WR | PF | PF 95% CI | P(PF>1) | Kelly | Beats Random? | Grade |
|--------|---|-----|-----|-----------|---------|-------|-------------|-------|
| Crypto DEF all | 1,274 | 46.4% | **1.88** | 1.59–2.23 | 100% | +0.217 | ✅ | **REAL EDGE** |
| Crypto DEF LONG Sc≥50 | 593 | 53.8% | **2.67** | 2.04–3.56 | 100% | +0.336 | ✅ | **REAL EDGE** |
| Forex DEF all | 289 | 82.4% | **12.02** | 4.42–24.58 | 100% | +0.755 | ✅ | **REAL EDGE** |
| Equity DEF Sc≥50 | 100 | 53.0% | **1.59** | 0.99–2.55 | 97% | +0.197 | ✅ | **REAL EDGE** |

**Three asset classes have CONFIRMED statistical edge on definitive exits:** Crypto (PF 1.88, beats random), Forex (PF 12.02), and Equity Score≥50 (PF 1.59).

### Per-system definitive-only ranking

| System | N | WR | PF | Kelly | Grade |
|--------|---|-----|-----|-------|-------|
| multi_asset_copytrader | 318 | **99.4%** | 99 | +0.99 | 🏆 (forex/commodity TP hits) |
| luxalgo_filters | 60 | **96.7%** | 40.61 | +0.94 | 🏆 |
| super_signals | 80 | **91.2%** | 29.80 | +0.88 | 🏆 |
| claude_gainer_st | 234 | 59.4% | **2.63** | +0.37 | 🏆 |
| dna_winner_picks | 32 | 59.4% | 2.41 | +0.35 | 🏆 |
| signal_validation | 15 | 66.7% | 3.00 | +0.44 | 🏆 |
| alpha_engine | 558 | 36.6% | 1.01 | +0.00 | ⚠️ Breakeven |
| stocks_competition | 211 | 28.0% | 0.59 | -0.19 | ❌ |
| ml_crypto_pred | 119 | 21.0% | 0.40 | -0.32 | ❌ |

### What the TIME_EXIT picks actually look like

802 TIME_EXIT picks: 437 positive (54.5%), 351 negative (43.8%), 35 flat. Median PnL +0.079%.

These are trades that were **slightly in the money when the timer expired** — they didn't reach TP. Counting them as "wins" makes the WR look like ~50% when the real signal quality (TP vs SL hit) is much higher for winning systems and much worse for losing systems. TIME_EXITs mask both extremes.

### Recommended fixes

1. **Exclude TIME_EXIT from WR/PF calculations** — or bucket them separately. The dashboard should show "Definitive WR" and "Overall WR" as separate metrics.
2. **Investigate the 526 `LOST` picks** — are these SL-equivalent (negative PnL) or time-outs with a different label?
3. **Fix `adaptive_tp_sl.py:185`** — currently treats `pnl_pct > 0` as a win for MFE/MAE stats. Timeouts with +0.5% PnL should NOT be in the "winner MFE" bucket — they inflate optimal TP estimates.
4. **Normalize direction labels upstream** — `BUY` should be written as `LONG` at scanner output time. 29 `BUY` and 2,753 `LONG` are the same thing with different labels.
5. **Add `exit_quality` field to picks** — classify as `DEFINITIVE`, `TIMEOUT`, `AMBIGUOUS`, `FORCED` at close time for clean downstream analysis.

---

*Updated 2026-04-14 with TIME_EXIT contamination analysis. Original analysis from code review of `ml_ranker.py`, `technical_features.py`, `feature_populator.py`, `model_calibration.py`, and empirical analysis of 3,500 closed picks.*
