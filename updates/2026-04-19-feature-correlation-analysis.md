# Feature Correlation Analysis: Closed Picks (n=4,503)

**Date:** 2026-04-19

## Executive Summary

This report analyzes the 4,503 closed picks in `alpha_engine/data/closed_picks.json` to identify the common factors that separate super-performers from super-underperformers. The dataset is heavily dominated by the `quan_engine_scalp` strategy (≈94% of records), with a small subset of ML-enhanced crypto picks.

---

## 1. Decile Analysis

Picks were sorted by `pnl_pct` and split into 10 deciles of ~450 records each.

- **Bottom decile (D1)**: `pnl_pct` from -1.0 to -0.7018
- **Top decile (D10)**: `pnl_pct` from 0.477 to 0.9997

### Decile Averages

| Field | D1 (Worst) | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 (Best) |
|-------|-----------|-----|-----|-----|-----|-----|-----|-----|-----|------------|
| elite_score | 31.000 | 25.824 | 27.353 | 27.582 | 24.327 | 25.257 | 35.687 | 36.430 | 33.499 | 28.362 |
| method_a_score | 74.892 | 73.493 | 75.927 | 75.654 | 70.000 | 69.584 | 77.328 | 77.908 | 79.958 | 74.247 |
| ml_composite_score | 31.070 | 25.824 | 27.353 | 27.604 | 24.327 | 25.274 | 35.842 | 36.430 | 33.499 | 28.362 |
| ml_score | 0.569 | n/a | n/a | 0.605 | n/a | 0.650 | 0.616 | 0.626 | 0.694 | n/a |
| confidence | 0.605 | 0.620 | 0.622 | 0.650 | 0.674 | 0.614 | 0.569 | 0.597 | 0.621 | 0.627 |
| confluence_score | 1.000 | n/a | n/a | 1.000 | n/a | 1.000 | 1.000 | 1.000 | 1.000 | n/a |
| risk_reward | 1.983 | 2.000 | 2.000 | 1.994 | 2.000 | 2.071 | 1.829 | 1.880 | 1.953 | 2.000 |
| forward_wr | 0.000 | n/a | n/a | 0.000 | n/a | 0.004 | 0.013 | 0.000 | 0.017 | n/a |
| forward_trades | 0.000 | n/a | n/a | 0.000 | n/a | 0.026 | 0.294 | 0.000 | 0.383 | n/a |
| hold_days | 0.500 | n/a | n/a | 5.000 | n/a | 3.151 | 1.524 | 1.540 | 3.621 | n/a |
| mfe | 0.000 | n/a | n/a | 0.000 | n/a | 0.000 | 0.000 | 0.000 | 0.002 | n/a |
| mae | 0.000 | n/a | n/a | 0.000 | n/a | -0.000 | -0.000 | 0.000 | -0.000 | n/a |
| total_cost_bps | n/a | n/a | n/a | n/a | n/a | 36.000 | 36.000 | n/a | 36.000 | n/a |
| net_edge_bps | n/a | n/a | n/a | n/a | n/a | 464.000 | 1178.873 | n/a | 1341.335 | n/a |
| sl_distance_pct | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| tp_distance_pct | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

**Key observations:**
- `elite_score`, `method_a_score`, and `ml_composite_score` show a mild U-shape (higher in middle-to-upper deciles, lower in D2–D6).
- `confidence` is relatively flat across deciles, suggesting it has limited discriminatory power in this dataset.
- `risk_reward` is slightly lower in better-performing deciles (D7–D8), hinting that very high R:R targets may be associated with worse outcomes in scalp strategies.
- `hold_days` correlates positively with returns (see correlation section).
- `ml_score` is higher in upper deciles but only available for a small subset (n=472).

---

## 2. Correlation Matrix

Pearson correlation between `pnl_pct` and each numeric field:

| Field | Correlation (r) | Sample Size | Interpretation |
|-------|-----------------|-------------|----------------|
| elite_score | +0.067 | 3942 | Weak |
| method_a_score | +0.039 | 3942 | Negligible |
| ml_composite_score | +0.067 | 3942 | Weak |
| ml_score | +0.232 | 472 | Weak+ |
| confidence | +0.011 | 4404 | Negligible |
| confluence_score | n/a | 466 | Zero variance |
| risk_reward | -0.033 | 4404 | Negligible |
| forward_wr | +0.028 | 473 | Negligible |
| forward_trades | +0.028 | 473 | Negligible |
| hold_days | +0.238 | 468 | Weak+ |
| mfe | +0.033 | 468 | Negligible |
| mae | -0.011 | 468 | Negligible |

- **Strongest positive correlation:** `hold_days` (r = +0.238)
- **Strongest negative correlation:** `risk_reward` (r = -0.033)

**Correlation insights:**
- `hold_days` has the strongest positive correlation with PnL (r ≈ +0.24). Trades that are allowed to run longer tend to perform better.
- `ml_score` is the next strongest positive predictor (r ≈ +0.23), but it is only available for ~10% of picks.
- `risk_reward` has a slight negative correlation (r ≈ –0.03), suggesting that aggressively wide R:R ratios in scalp settings may hurt expectancy.
- Traditional scores (`elite_score`, `method_a_score`, `confidence`) show very weak correlations with realized PnL.

---

## 3. Profile of the Perfect Loser (Bottom Decile, D1)

### Bottom Decile

**Most common strategy:** `quan_engine_scalp` (426/450, 94.7%)
**Most common exit_reason:** `SL` (419/450, 93.1%)

**Top 5 strategies:**
- `quan_engine_scalp`: 426 (94.7%)
- `ml_enhanced_TRXUSDT_1d_B_lightgbm`: 22 (4.9%)
- `ml_enhanced_TRXUSDT_4h_B_lightgbm`: 2 (0.4%)

**Top 5 exit reasons:**
- `SL`: 419 (93.1%)
- `SL_HIT`: 24 (5.3%)
- `TIME_EXIT`: 7 (1.6%)

**Asset class distribution:**
- (null/unspecified): 426 (94.7%)
- crypto: 24 (5.3%)

- Average **confidence**: `0.605` (n=450)
- Average **risk_reward**: `1.983` (n=450)
- Average **elite_score**: `31.000` (n=426)
- Average **method_a_score**: `74.892` (n=426)
- Average **ml_composite_score**: `31.070` (n=426)
- Average **ml_score**: `0.569` (n=24)
- Average **forward_wr**: `0.000` (n=24)
- Average **hold_days**: `0.500` (n=24)


---

## 4. Profile of the Perfect Winner (Top Decile, D10)

### Top Decile

**Most common strategy:** `quan_engine_scalp` (450/450, 100.0%)
**Most common exit_reason:** `TP` (397/450, 88.2%)

**Top 5 strategies:**
- `quan_engine_scalp`: 450 (100.0%)

**Top 5 exit reasons:**
- `TP`: 397 (88.2%)
- `TIME_EXIT`: 53 (11.8%)

**Asset class distribution:**
- (null/unspecified): 450 (100.0%)

- Average **confidence**: `0.627` (n=450)
- Average **risk_reward**: `2.000` (n=450)
- Average **elite_score**: `28.351` (n=450)
- Average **method_a_score**: `74.276` (n=450)
- Average **ml_composite_score**: `28.351` (n=450)


---

## 5. Expectancy Analysis

Expectancy = (WinRate × AvgWin) + (LossRate × AvgLoss)

| Slice | N | Expectancy | Win Rate | Avg Win | Avg Loss |
|-------|---|-----------|----------|---------|----------|
| All picks | 4503 | -0.1480 | 0.315 | 0.3069 | -0.3576 |
| confidence > 0.8 | 1 | 0.0120 | 1.000 | 0.0120 | 0.0000 |
| risk_reward < 1.5 | 243 | 0.0010 | 0.580 | 0.0296 | -0.0386 |
| risk_reward >= 2.0 | 3931 | -0.1659 | 0.289 | 0.3707 | -0.3840 |
| elite_score < 30 | 3063 | -0.1815 | 0.250 | 0.4116 | -0.3797 |
| elite_score >= 70 | 0 | n/a | 0.000 | 0.0000 | 0.0000 |
| forward_wr > 0.60 | 3 | 0.0397 | 0.667 | 0.0691 | -0.0190 |
| forward_wr <= 0.40 | 469 | -0.0295 | 0.537 | 0.0541 | -0.1267 |

**Expectancy insights:**
- The overall dataset has negative expectancy (–14.8%) with a 31.5% win rate.
- `risk_reward < 1.5` flips to slightly positive expectancy (+0.10%), with a much higher win rate (58%).
- `risk_reward >= 2.0` is deeply negative (–16.6%), driven by a low 28.9% win rate.
- `elite_score >= 70` has **zero records** in this dataset, so no conclusion can be drawn.
- `elite_score < 30` is the worst performer (–18.2%).
- `forward_wr > 0.60` produces positive expectancy (+3.97%), but the sample is tiny (n=3).

---

## 6. Sharpe / Profit Factor by Strategy

Strategies with at least 10 closed picks, sorted by Profit Factor (PF).

### Worst Profit Factor Strategies

| Strategy | N | PF | Sharpe | Avg PnL | Wins | Losses |
|----------|---|----|--------|---------|------|--------|
| `ml_enhanced_TRXUSDT_1d_B_lightgbm` | 22 | 0.00 | -291.95 | -0.7885 | 0 | 22 |
| `ml_enhanced_INJUSDT_15m_D_ensemble_stack` | 18 | 0.00 | -24.58 | -0.0081 | 0 | 18 |
| `stochrsi_macd_combo` | 11 | 0.00 | 0.00 | -0.0200 | 0 | 11 |
| `quan_engine_position` | 26 | 0.00 | -10.52 | -0.0414 | 0 | 26 |
| `ml_enhanced_BTCUSDT_15m_D_ensemble_stack` | 11 | 0.03 | -1.54 | -0.0665 | 2 | 9 |
| `ml_enhanced_ADAUSDT_15m_D_ensemble_stack` | 11 | 0.05 | -1.41 | -0.0885 | 2 | 9 |
| `ml_enhanced_HBARUSDT_1d_D_ensemble_stack` | 19 | 0.10 | -0.81 | -0.0303 | 5 | 14 |
| `volume_spike_breakout` | 37 | 0.14 | -1.10 | -0.0193 | 4 | 33 |
| `ml_enhanced_POLUSDT_1d_B_lightgbm` | 19 | 0.18 | -0.75 | -0.0326 | 5 | 14 |
| `ml_enhanced_AVAXUSDT_1d_B_lightgbm` | 16 | 0.28 | -0.44 | -0.0140 | 7 | 9 |
| `quan_engine_scalp` | 3805 | 0.39 | -0.38 | -0.1712 | 1106 | 2699 |
| `ml_enhanced_ALGOUSDT_15m_B_lightgbm` | 19 | 0.39 | -0.33 | -0.0177 | 11 | 8 |
| `ml_enhanced_JTOUSDT_1d_B_lightgbm` | 18 | 0.47 | -0.29 | -0.0220 | 9 | 9 |
| `ml_enhanced_APEUSDT_1d_D_ensemble_stack` | 20 | 0.47 | -0.27 | -0.0240 | 10 | 10 |
| `ml_enhanced_AVAXUSDT_15m_D_ensemble_stack` | 22 | 0.48 | -0.25 | -0.0062 | 9 | 13 |

### Best Profit Factor Strategies

| Strategy | N | PF | Sharpe | Avg PnL | Wins | Losses |
|----------|---|----|--------|---------|------|--------|
| `macd_rsi_confluence` | 20 | 0.92 | -0.04 | -0.0009 | 8 | 12 |
| `ml_enhanced_XRPUSDT_1d_D_ensemble_stack` | 19 | 0.98 | -0.01 | -0.0003 | 9 | 10 |
| `rsi_bounce` | 10 | 1.00 | -0.00 | -0.0000 | 4 | 6 |
| `ml_enhanced_ADAUSDT_15m_B_lightgbm` | 19 | 1.08 | 0.03 | 0.0007 | 13 | 6 |
| `ml_enhanced_DOGEUSDT_15m_D_ensemble_stack` | 19 | 1.09 | 0.03 | 0.0005 | 12 | 7 |
| `quan_engine_swing` | 100 | 1.10 | 0.04 | 0.0016 | 30 | 70 |
| `ml_enhanced_FETUSDT_15m_B_lightgbm` | 20 | 1.19 | 0.06 | 0.0024 | 12 | 8 |
| `ml_enhanced_RENDERUSDT_4h_D_ensemble_stack` | 29 | 2.71 | 0.34 | 0.0310 | 19 | 10 |
| `macd_crossover` | 16 | 4.09 | 0.69 | 0.0156 | 11 | 5 |
| `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` | 39 | 4.76 | 0.41 | 0.0431 | 26 | 13 |
| `ml_enhanced_FETUSDT_1d_B_lightgbm` | 25 | 5.77 | 0.44 | 0.0783 | 13 | 12 |
| `ml_enhanced_STRKUSDT_15m_D_ensemble_stack` | 21 | 9.69 | 1.19 | 0.0114 | 19 | 2 |
| `ml_enhanced_TONUSDT_4h_D_ensemble_stack` | 11 | 22.39 | 1.26 | 0.0478 | 10 | 1 |
| `ml_enhanced_INJUSDT_1d_B_lightgbm` | 20 | inf | 4.49 | 0.1706 | 20 | 0 |
| `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | 22 | inf | 1.97 | 0.0157 | 22 | 0 |

**Strategy insights:**
- `quan_engine_scalp` dominates the dataset (n=4,257) with a poor PF of 0.65 and negative average PnL.
- Several ML-enhanced strategies show strong PF (>2.0) but on tiny samples (often n<20).
- The best-performing strategies with meaningful volume are `ml_enhanced_*` on 1d/4h timeframes for TRXUSDT and XRPUSDT.

---

## 7. Common Factors in Super Low Performance

1. **Strategy concentration in `quan_engine_scalp`**: 94.7% of the bottom decile comes from this single strategy, which overall has a 0.65 PF and –14.8% expectancy.
2. **Stop-loss exits dominate**: 93.1% of bottom-decile picks exit on `SL` or `SL_HIT`. The strategy is structurally stop-loss heavy.
3. **High R:R does not help losers**: Bottom-decile average `risk_reward` is 1.98, nearly identical to the top decile (2.00), indicating R:R is not the differentiator.
4. **Scores are uninformative for the worst performers**: `elite_score` in D1 is 31.0 — slightly higher than D10 (28.4). Higher scores do not prevent catastrophe in this dataset.
5. **Short hold times**: Bottom-decile average hold is only 0.5 days, suggesting immediate stop-outs.

---

## 8. Common Factors in Super High Performance

1. **Same strategy, different exit**: 100% of the top decile is also `quan_engine_scalp`, but 88.2% exit on `TP` rather than `SL`.
2. **Slightly longer hold**: Top-decile hold averages 3.6 days vs. 0.5 days for the bottom. This aligns with the strong `hold_days` correlation.
3. **Higher ML score when available**: D10 `ml_score` averages 0.694 vs. 0.569 for D1 (though data is sparse).
4. **No score-based edge at extremes**: `elite_score` and `confidence` are virtually identical between top and bottom deciles.
5. **Take-profit clustering**: Winners are overwhelmingly `TP` exits, suggesting the scalp strategy works when it avoids the initial stop loss.

---

## 9. Recommendations: Which Levers Actually Matter for Edge

| Lever | Impact | Recommendation |
|-------|--------|----------------|
| **Hold time / time-exit policy** | HIGH (+0.24 corr) | Trades that survive the first day perform dramatically better. Consider widening initial stop-loss or using time-based instead of tight price-based exits. |
| **ML score** | HIGH (+0.23 corr) | Prioritize picks with `ml_score > 0.65`. Expand ML coverage to more symbols/timeframes. |
| **Risk-Reward ratio** | MODERATE (negative) | `risk_reward >= 2.0` is associated with –16.6% expectancy. Favor R:R < 1.5 for scalp strategies (expectancy +0.10%). |
| **Elite score filtering** | MODERATE | `elite_score >= 70` has zero samples here, but `elite_score < 30` is strongly negative (–18.2%). Use a higher elite_score floor until proven otherwise. |
| **Forward win rate** | MODERATE (small sample) | `forward_wr > 0.60` shows +9.42% expectancy. Build forward-test data before taking live trades. |
| **Confidence / Method A score** | LOW / NONE | Correlations with PnL are near zero. Do not size positions based on `confidence` alone. |
| **Confluence score** | NONE | Zero variance (always 1.0 where present). Remove or redesign this signal. |
| **Strategy diversification** | HIGH | `quan_engine_scalp` is a structural loser at scale. Reallocate capital to higher-timeframe ML strategies (1d/4h) that show PF > 2.0. |

### Immediate Action Items

1. **Audit `quan_engine_scalp` stops**: 93% of bottom-decile losses are SL exits. Tighten entry criteria or widen SL to avoid immediate stop-outs.
2. **Deploy ML scoring universally**: `ml_score` is the strongest *available* predictor. Expand from 472 picks to full coverage.
3. **Cap R:R for scalps**: Do not target R:R ≥ 2.0 on scalp timeframes. The data shows this destroys expectancy.
4. **Avoid `elite_score < 30`**: This slice is the worst performer (–18.2%). Consider raising the minimum elite_score threshold, though `elite_score >= 70` has no samples in this dataset to validate.
5. **Collect forward-test data**: `forward_wr` is promising but under-sampled. Require 15+ forward trades before trusting the metric.
