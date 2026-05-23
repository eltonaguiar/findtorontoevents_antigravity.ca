# Proposed Bundle: VWM Robust MR Ensemble

**Date:** Feb 28, 2026  
**Proposer:** AI Assistant  
**Bundle ID:** `bundle_vwm_robust_mr_ensemble_20260228`

---

## Bundle Composition

| # | Strategy | Type | Weight | Validation Status | Expected Sharpe |
|---|----------|------|--------|-------------------|-----------------|
| 1 | **Volume-Weighted Median Z-Score** (NEW) | Mean Reversion (Robust) | 30% | Pending 8-check | 0.9-1.2 |
| 2 | **Supertrend** | Trend/Momentum (PROVEN) | 25% | TIER_3_WATCH | 1.18 |
| 3 | **Connors RSI-2** | Mean Reversion (PROVEN) | 25% | TIER_1_PROVEN | 1.17 |
| 4 | **Bollinger Mean Reversion** | Mean Reversion (PROVEN) | 20% | TIER_1_PROVEN | 0.72 |

---

## Strategy Details

### 1. Volume-Weighted Median Z-Score (NEW)

```python
Class: VolumeWeightedMedianZScoreStrategy
File: baby_strategies/volume_weighted_median_zscore.py
```

**Logic:**
- Compute typical price (HLC/3) and volume-weighted median (VWM) over `lookback` (default 20)
- Scale deviations using Median Absolute Deviation (MAD) → robust z-score
- Long when `z < -entry_z` (default -2.0); Short when `z > +entry_z`
- Exit: TP=3×ATR, SL=2×ATR, or `z` returns to `±exit_z` (0.5), or `max_hold_days=15`

**Differentiation:**
- Uses **median** (not mean) and **MAD** (not stddev) → robust to outliers
- Volume-weighted median resists spoofing vs VWAP survivor
- Completely different from RSI, MACD, Bollinger families

**Expected:**
- Win Rate: 60-68%
- Trades: 100-200/year on BTC-1h
- Sharpe: 0.8-1.2

---

### 2. Supertrend (PROVEN - TIER_3_WATCH)

```python
Class: SupertrendStrategy
File: baby_strategies/supertrend_atr.py
```

**Performance:** 34 trades, 52.9% WR, Sharpe 1.18, PF 6.25

**Logic:** ATR-based trailing stop trend following. Go long when price > supertrend line, exit when price crosses below. ONLY non-mean-reversion survivor.

**Role in Bundle:** Provides **trend-capture** to balance mean-reversion; expected negative correlation during strong trends.

---

### 3. Connors RSI-2 (PROVEN - TIER_1)

```python
Class: ConnorsRSI2MeanReversionStrategy
File: baby_strategies/connors_rsi2_mean_reversion.py
```

**Performance:** 895 trades, 68.4% WR, Sharpe 1.17, PF 1.53, p=0.000000

**Logic:** RSI(2) < 5 + Close > 200SMA → LONG, exit RSI(2) > 65.

**Role:** Ultra-fast mean-reversion workhorse; high trade count smoothes equity curve.

---

### 4. Bollinger Mean Reversion (PROVEN - TIER_1)

```python
Class: BollingerMeanReversionStrategy
File: baby_strategies/bollinger_mean_reversion.py
```

**Performance:** 361 trades, 60.7% WR, Sharpe 0.72, PF 1.53, p=0.00003

**Logic:** Price touches lower Bollinger Band (20,2) + price > 90% of 200SMA → LONG, exit at middle band.

**Role:** Volatility-based mean reversion; different indicator family from RSI.

---

## Uncorrelated Rationale (Mathematical)

| Strategy Pair | Why Low/Zero Correlation |
|---------------|--------------------------|
| **VWM vs VWAP** | VWM uses median + MAD (robust statistics) vs VWAP uses mean + stddev. Different sensitivities to outliers → different entry timing. |
| **VWM vs RSI-2** | RSI is a rate-of-change oscillator (velocity); VWM is price vs volume benchmark (level). Signal sources are orthogonal. |
| **VWM vs Bollinger** | Bollinger: SMA ± k·σ (mean-based); VWM: median ± k·MAD (median-based). Different central tendency and dispersion. |
| **VWM vs Supertrend** | VWM: mean-reversion (counter-trend); Supertrend: trend-following (momentum). Mathematically negative correlation in trending regimes; low/flat in choppy. |
| **RSI-2 vs Bollinger** | RSI is bounded oscillator; Bollinger is price-based bands. Independent signals. |
| **RSI-2 vs Supertrend** | Oscillator vs ATR trend filter; typically opposing signals in trends. |
| **Bollinger vs Supertrend** | Mean-reversion exit vs trend entry; opposite bias. |

**Expected Bundle Sharpe:** 1.1–1.3 (weighted sum of components; diversification reduces volatility).

---

## Classification

- **Symbol Scope:** Multi_symbol (BTC/ETH/SOL + equities, forex)
- **Timeframe Scope:** Multi_timeframe (works on 1h and 4h; RSI-2 also on 1d)
- **Direction Bias:** Both (VWM allows LONG/SHORT; others are LONG-only → net long bias but still balanced)

---

## Registration

To activate this bundle:

1. Add entry to `BABY_BUNDLE_REGISTRY.md` (see format in that file)
2. Insert into `battleground/data/bundle_babies.db` via `register_bundle.py`
3. Run forward test with `incubator/backtest_team/forward_test_coordinator.py` (min 100 trades)
4. Monitor against real BTC/ETH/SOL data on `incubator/testing/forward_dashboard.py`

---

## Risk Notes

- **Overlap:** VWM and Bollinger both MR → possible duplicate entries; monitor correlation.
- **Mean-reversion concentration:** 3 of 4 are MR → vulnerable to strong trending regimes. Supertrend offsets but doesn't fully hedge.
- **Parameter stability:** VWM `lookback` and `entry_z` must be validated across assets; avoid overfit.
- **Minimum trades required:** Expect 200–400 bundle trades/year; wait for 100+ before judging.
