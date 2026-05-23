# Strategy Drift Analysis — 2026-04-12

> **Objective:** Identify strategies that look good in backtest/forward metrics but fail in actual live trading, and propose fixes.  
> **Dataset:** 3,500 closed picks from `dashboard_payload.json`, walk-forward results, forward test portfolios, per-strategy time decay

---

## Executive Summary

**The system has a systemic drift problem at every validation layer:**

1. **Walk-forward validation: 0 out of 5 strategies pass the anti-overfit test.** Every tested strategy fails.
2. **Forward test portfolios: 0 trades executed across 8 paper portfolios.** The "GOLDEN_FILTER" ($1,000 start, score ≥ 70) has made literally zero trades in 19 days — the filter is too strict or the pipeline is broken.
3. **Backtest → actual drift:** ML-enhanced strategies show -13pp to -33pp WR collapse. `quan_engine_swing` went from 33% BT WR to 0% actual (10 trades, -23%).
4. **Forward WR → actual drift:** The `strat_fwd_wr` field (used in scoring) overstates performance by 10-60pp for many strategies. `unknown` strategy: 77% forward WR → 17% actual.
5. **Time decay is real:** `enhanced_ml_A_xgboost` dropped from 41% WR (first half) to 22% WR (second half) — an 18.5pp collapse. `volume_spike_breakout` went from 52% to 21% — a 31pp collapse.

---

## 1. Walk-Forward Validation: Total Failure

```
Summary: 0 passing / 5 failing anti-overfit
Failing: ema_crossover, rsi_reversal, bollinger_bounce, macd_divergence, funding_rate_contrarian
Parameters: train=60d, test=30d, step=15d, interval=4h
```

**Every single strategy tested in walk-forward validation fails.** This means the backtest results used to justify these strategies cannot be trusted — they are overfit to in-sample data.

**Root cause:** The walk-forward test uses a 60-day train / 30-day test window. Crypto regime changes faster than 60 days. These strategies are fitting to a regime that no longer exists by the time they trade live.

**Fix:** Shorten train window to 14-21 days for crypto. Use regime-conditional training (only train on data from matching regime). Add online learning that adapts weights every 24h.

---

## 2. Forward Test Portfolios: Zero Execution

| Portfolio | Description | Capital | Return | Trades |
|-----------|-------------|---------|--------|--------|
| GOLDEN_FILTER | Top 5 traders + score ≥ 70 | $1,000 | +0.00% | **0** |
| MTF_GATED | MTF 3-timeframe + score ≥ 50 | $1,000 | +0.58% | **0** |
| ENSEMBLE_2OF3 | 2-of-3 ensemble gate | $1,000 | +0.06% | **0** |
| SHORT_DOMINANT | Short-dominant picks | $1,000 | +0.00% | **0** |
| ROCKET_PICKS | Rocket picks | $500 | +0.00% | **0** |
| PROVEN_FOREX | Proven forex | $500 | +0.00% | **0** |
| COT_CARRY | COT + carry | $500 | +0.00% | **0** |
| QUALITY_STOCKS | Quality momentum + RSI2 | $500 | +0.00% | **0** |

**8 portfolios, 19 days running, zero total trades.** The equity changes in MTF_GATED ($1,005.82) and ENSEMBLE_2OF3 ($1,000.57) appear to be from unrealized positions, not closed trades.

**Root causes:**
1. **Filter too strict:** GOLDEN_FILTER requires score ≥ 70, but the max `score` (ml_composite) in the entire dataset is 76. Only a tiny fraction of picks pass.
2. **Pipeline disconnect:** The forward test state file exists but the paper trading engine isn't executing against the live pick stream.
3. **No feedback loop:** Without trades, there's no validation data. Without validation data, no strategy improvement. Classic dead loop.

**Fix:** Lower GOLDEN_FILTER threshold to score ≥ 50 (where we see actual edge). Wire the paper trading engine to the live pick stream from `scanner.py`. Add a daily health check that alerts when a portfolio has zero trades for >48h.

---

## 3. Backtest → Actual Drift (Worst Offenders)

### Strategies that collapsed from BT promise to actual failure

| Strategy | Asset | N | BT WR | Actual WR | Drift | BT PF | Act PF | Total PnL |
|----------|-------|---|-------|----------|-------|-------|--------|-----------|
| quan_engine_swing | CRYPTO | 10 | 33.3% | **0.0%** | **-33pp** | 1.25 | 0.00 | -23.3% |
| ml_enhanced_AVAX_D_ensemble | CRYPTO | 5 | 52.9% | 20.0% | -33pp | 0.83 | 0.11 | -11.3% |
| ml_enhanced_RENDER_D_ensemble | CRYPTO | 5 | 70.6% | 40.0% | -31pp | 5.39 | 1.15 | +0.9% |
| ml_enhanced_ADA_B_lightgbm | CRYPTO | 5 | 73.3% | 60.0% | -13pp | 1.37 | 0.34 | -5.4% |
| ml_enhanced_FET_B_lightgbm | CRYPTO | 5 | 68.8% | 60.0% | -9pp | 1.28 | 0.25 | -9.6% |

**Pattern:** ML-enhanced per-symbol strategies consistently overfit. They train on one symbol's history and the model memorizes patterns that don't persist. The backtest PF of 5.39 for RENDER collapsing to 1.15 is textbook overfitting.

### Strategies that outperformed BT (pleasant surprises)

| Strategy | N | BT WR | Actual WR | Drift |
|----------|---|-------|----------|-------|
| ml_enhanced_ALGO_B_lightgbm | 5 | 66.7% | **100.0%** | +33pp |
| volume_spike_breakout | 67 | 10.8% | 35.8% | +25pp |
| quan_engine_scalp | 620 | 29.2% | 43.9% | +15pp |

Note: `volume_spike_breakout` overperformed its BT but is still losing money. The BT was just that pessimistic (10.8% WR in backtest).

---

## 4. Forward WR → Actual Drift (strat_fwd_wr Inflation)

The `strat_fwd_wr` field is used in scoring (it feeds `elite_scorer.py`). But it systematically overstates performance:

### Worst forward WR inflation

| Strategy | Asset | N | Fwd WR | Actual WR | Drift | Fwd Sample | Total PnL |
|----------|-------|---|--------|----------|-------|-----------|-----------|
| unknown | CRYPTO | 12 | **77.1%** | **16.7%** | **-60pp** | 581 | -11.5% |
| keltner_expansion_sol | CRYPTO | 5 | 50.6% | 0.0% | -51pp | 77 | -4.2% |
| soc_delta_divergence | CRYPTO | 8 | 44.7% | 0.0% | -45pp | 85 | -6.1% |
| keltner_expansion_v1 | CRYPTO | 6 | 58.2% | 16.7% | -42pp | 98 | -2.6% |
| quan_engine_swing | CRYPTO | 10 | 33.3% | 0.0% | -33pp | 90 | -23.3% |

**The "unknown" strategy is the most alarming:** 581-trade forward sample claiming 77% WR, but actual is 17%. This means the forward validation pipeline is either computing WR incorrectly, or the "forward" data is contaminated with in-sample results.

**Root cause analysis:**
1. **`strat_fwd_wr` may be stale.** It's computed at strategy registration time and may not update as new trades close. The 77% WR for "unknown" with 581 trades likely reflects historical data that predates the current market regime.
2. **Survivorship bias in forward metrics.** If forward WR is computed from a different time window than actual trades, regime shifts cause massive drift.
3. **Keltner strategies: complete collapse.** 0% actual WR across sol, v1 variants despite 50-58% forward claims. These are mean-reversion strategies that fail in trending markets.

---

## 5. Time Decay — Which Strategies Are Dying?

### Weekly system performance trend

| Week | Trades | WR | Avg PnL | Total PnL |
|------|--------|-----|---------|-----------|
| W07 (Feb) | 1 | 0.0% | -3.32% | -3.3% |
| W08 | 25 | 44.0% | -0.87% | -21.7% |
| W10 (Mar) | 182 | **16.5%** | -0.48% | -88.0% |
| W11 | 110 | 45.5% | -0.51% | -56.0% |
| W12 | 123 | 44.7% | +0.01% | +1.3% |
| W13 | 441 | 48.8% | +0.03% | +13.5% |
| **W14 (Apr)** | **2,246** | **49.2%** | **+0.54%** | **+1,206%** |

**W10 was catastrophic** (16.5% WR on 182 trades). The system has recovered in W13-W14, but W14's 49.2% WR with +0.54% avg PnL is driven by high-PnL outlier wins — the median trade is still negative.

### Per-strategy decay (first half vs second half)

| Strategy | First Half WR | Second Half WR | Drift | Status |
|----------|--------------|----------------|-------|--------|
| **st_fear_greed_contrarian** | 77.7% | **84.1%** | **+6.4pp** | 🟢 **Getting better** |
| **st_obv_support_divergence** | 59.4% | **87.9%** | **+28.5pp** | 🟢 **Surging** |
| **luxalgo_confluence** | 51.6% | **61.9%** | **+10.3pp** | 🟢 Improving |
| MeanReversionBB | 85.7% | 85.7% | 0pp | → Stable |
| st_rsi_momentum_confluence | 52.1% | 48.9% | -3.2pp | → Slight decay |
| quan_engine_scalp | 44.2% | 43.5% | -0.6pp | → Stable |
| st_multi_day_momentum | 71.4% | 61.1% | -10.3pp | 🔴 Decaying |
| **enhanced_ml_A_xgboost** | 40.9% | **22.4%** | **-18.5pp** | 🔴 **Collapsing** |
| **volume_spike_breakout** | 51.5% | **20.6%** | **-30.9pp** | 🔴 **Dead** |

**Three strategies are actively dying:** `enhanced_ml_A_xgboost` (-18.5pp), `volume_spike_breakout` (-31pp), and `st_multi_day_momentum` (-10pp). These should be paused immediately.

**Three strategies are getting stronger:** `st_fear_greed_contrarian`, `st_obv_support_divergence`, and `luxalgo_confluence`. Allocate more to these.

---

## 6. Root Causes of Drift

### A. Overfitting to regime

The walk-forward test explicitly shows 0/5 strategies pass anti-overfit. The 60-day training window captures one regime; by the time the strategy trades, the regime has changed. Crypto cycles every 2-4 weeks.

**Fix:** Regime-conditional training. Only train on data from matching regime (trending_up, choppy, crisis). The `regime_detector.py` already classifies regimes — use it to filter training data.

### B. stale `strat_fwd_wr` feeding scoring

The forward WR used in `elite_scorer.py` is a historical average that doesn't decay. A strategy with 77% WR from months ago keeps getting boosted even as it's currently at 17%.

**Fix:** Add exponential decay to forward WR:
```python
# Current: strat_fwd_wr is static
# Proposed: decay-weighted forward WR
decay_lambda = 0.05  # ~14 day half-life
days_since_last_update = (now - last_fwd_update).days
decayed_fwd_wr = actual_recent_wr + (strat_fwd_wr - actual_recent_wr) * exp(-decay_lambda * days_since_last_update)
```

### C. Per-symbol ML models overfit

`ml_enhanced_{SYMBOL}_{timeframe}_{variant}` models are trained on one symbol's history. Small sample (15-30 trades in forward), model memorizes noise.

**Fix:** Train cross-symbol models. Instead of BTCUSDT-specific, train one model per asset class that takes symbol as a feature. Minimum 100 forward trades before promoting from incubator.

### D. No automatic strategy demotion

Strategies like `enhanced_ml_A_xgboost` (40.9% → 22.4% WR) keep running indefinitely. The `status_enforcer.py` exists but the daily block is bypassed (`return False`).

**Fix:** Re-enable the daily block. Add automatic WR-decay demotion:
```python
# If rolling 50-trade WR drops 15+pp below forward WR: auto-pause
rolling_wr = compute_rolling_wr(strategy, window=50)
if strat_fwd_wr - rolling_wr > 15:
    pause_strategy(strategy, reason="WR drift > 15pp")
```

### E. Forward test portfolios not wired

8 paper portfolios with zero trades means there's no real-time validation loop. We can't detect drift if we're not measuring.

**Fix:** Wire `forward_test_state.json` portfolios to the live scanner output. Execute paper trades for every pick that passes each portfolio's filter. Report daily PnL for each portfolio.

---

## 7. Recommended Actions

### Immediate (kill the bleeding)

| # | Action | Impact |
|---|--------|--------|
| 1 | **Pause `enhanced_ml_A_xgboost`** — 18.5pp decay, 133 trades of dead weight | Stops ongoing -59% PnL bleed |
| 2 | **Pause `volume_spike_breakout`** — 31pp decay, now 20.6% WR | Stops ongoing -43% PnL bleed |
| 3 | **Pause all keltner variants** — 0% actual WR across all variants | Stops -13% total bleed |
| 4 | **Re-enable daily block** in `risk_controls.py` | Restores circuit breaker |

### Short-term (fix the validation pipeline)

| # | Action | Impact |
|---|--------|--------|
| 5 | Add exponential decay to `strat_fwd_wr` in `elite_scorer.py` | Stops stale WR from inflating scores |
| 6 | Wire forward test portfolios to live scanner | Enables real-time validation |
| 7 | Add rolling WR drift detector — auto-pause at 15pp decay | Catches dying strategies early |
| 8 | Lower GOLDEN_FILTER threshold to score ≥ 50 | Actually generates trades |

### Medium-term (fix the training pipeline)

| # | Action | Impact |
|---|--------|--------|
| 9 | Regime-conditional training (only train on matching regime data) | Reduces overfit to regime |
| 10 | Cross-symbol ML models instead of per-symbol | Larger training set, less overfit |
| 11 | Shorten walk-forward train window to 14-21d for crypto | Matches regime cycle |
| 12 | Minimum 100 forward trades before strategy promotion | Higher bar for live deployment |

---

## 8. What's Actually Working Right Now

Despite the drift problems, three strategies are **getting stronger over time**:

| Strategy | Recent WR | Trend | Total PnL | Why it works |
|----------|----------|-------|-----------|-------------|
| `st_fear_greed_contrarian` | 84.1% | 🟢 +6pp | +447% | Contrarian sentiment — regime-independent |
| `st_obv_support_divergence` | 87.9% | 🟢 +29pp | +65% | Volume-confirmed reversals — structural edge |
| `luxalgo_confluence` | 61.9% | 🟢 +10pp | +82% | Multi-indicator confluence — reduces noise |
| `MeanReversionBB` | 85.7% | → Stable | +24% | Bollinger band reversion — works in ranges |

These strategies share a common trait: **they don't rely on ML prediction of price direction.** They use structural/sentiment signals that are more robust to regime change.

The strategies that are dying are all **ML-based directional predictors** that overfit to recent price patterns. The fix is architectural: stop trusting ML direction predictions as the primary signal, and use them only as a secondary filter on structurally-driven entries.

---

*Generated 2026-04-12 from `dashboard_payload.json` (generated 2026-04-12T02:44 UTC), `walk_forward_results.json`, `forward_test_state.json`, and `validation_log.json`.*
