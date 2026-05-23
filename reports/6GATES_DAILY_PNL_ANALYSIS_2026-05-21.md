# 6-Gates + Daily PnL Analysis — 2026-05-21

## TL;DR

**Daily PnL (exit-day attribution) is working.** Sharpe values are now realistic
(mean 2.65, median 2.76, max 8.44) vs the old per-trade annualized (max 148).

**7 strategies qualify** for daily PnL analysis (>=20 valid non-TIME_EXIT trades).
27 strategies qualify for the per-trade validation pipeline.

**Top-notch picks per asset class:**

| Class | Best strategy | WR | Daily Sharpe | n_trades | Caveat |
|-------|--------------|----|-------------|----------|--------|
| CRYPTO | Multi-Timeframe Trend Alignment | 97.1% | N/A (no daily) | 68 | Small n, need more data |
| CRYPTO | AuditEnsemble_LONG | 96.7% | N/A (no daily) | 123 | Excellent, needs daily PnL |
| CRYPTO | luxalgo_confluence | 42.5% | **4.75** | 109 | Daily PnL verified |
| CRYPTO | MomentumEMA | — | **3.32** | 43 | Daily PnL verified |
| EQUITY | MomentumEMA | 69.8% | **3.32** | 43 | Daily PnL verified |
| EQUITY | MeanReversionBB | 48.6% | **1.76** | 146 | Reliable but modest edge |
| FOREX | MeanReversionBB | 25.0% | N/A | 48 | Low WR, high PF from few wins |

---

## 1. Daily PnL Methodology Change

### Old approach (broken)
- Spread each trade's pnl_pct evenly across holding days
- Created artificially smooth daily returns (same 0.4% every day for a 5-day trade)
- Low standard deviation → inflated Sharpe (148, 128, etc.)

### New approach (exit-day attribution) ✅
- Each trade's full pnl_pct recorded on its **exit day only**
- Days with no exits = 0% return (opportunity cost of capital)
- Daily return = equal-weighted mean PnL of all exits that day
- Sharpe = mean(daily_returns) / std(daily_returns) × √252
- **Result:** Realistic Sharpe values (0.5–8.0 range)

---

## 2. Daily PnL Results — Top 7 Strategies

| Rank | Strategy | Sharpe | CumRet | MaxDD | WR(days) | n_trades | n_days |
|------|----------|--------|--------|-------|----------|----------|--------|
| 1 | unknown | **8.44** | +59.4% | -1.00% | 93% | 612 | 89 |
| 2 | luxalgo_confluence | **4.75** | +11.3% | -2.42% | 68% | 109 | 29 |
| 3 | MomentumEMA | **3.32** | +17.4% | -2.00% | 71% | 43 | 90 |
| 4 | clone_hl_copy_lb_None | **2.76** | +3.6% | 0.00% | 100% | 22 | 64 |
| 5 | MeanReversionBB | **1.76** | +8.7% | -3.42% | 55% | 135 | 90 |
| 6 | enhanced_ml_A_xgboost | **1.10** | +2.2% | -7.30% | 50% | 22 | 22 |
| 7 | hs_lb_None | **-3.55** | -8.0% | -10.18% | 10% | 99 | 61 |

**Global Sharpe distribution:** Mean=2.65, Median=2.76, Min=-3.55, Max=8.44
- % above 1.0: **85.7%** (6/7)
- % above 2.0: **57.1%** (4/7)
- % above 3.0: **42.9%** (3/7)

---

## 3. "unknown" Strategy Investigation

- **1,412 picks** (1,336 CRYPTO + 73 CRYPTO-capitalized)
- Sources: `quan_engine` (700), `kimi_signal_tracking` (500), `ml_crypto_pred_v12` (103)
- PnL range: -2.48 to +3.68 (tight range — no absolute PnL > 10%)
- Win rate: **48.2%** (barely above coin flip)
- Average PnL: **+0.84%** per trade
- **Daily Sharpe 8.44 is legitimate** — many small winning exits clustering on certain days creates a smooth equity curve with high win-rate days (93%)
- **Not a bug**, but the "unknown" catch-all name means we can't attribute this to a specific strategy

**Action:** Rename or split "unknown" into its source systems (`quan_engine`, `kimi_signal_tracking`, `ml_crypto_pred_v12`) for proper attribution.

---

## 4. Per-Asset-Class Analysis

### CRYPTO (strongest data)
| Strategy | n_trades | WR | AvgPnl | PF | Viable? |
|----------|----------|----|--------|----|---------|
| Multi-Timeframe Trend Alignment | 68 | **97.1%** | +3.35 | 68.14 | ✅ Top pick |
| AuditEnsemble_LONG | 123 | **96.7%** | +3.02 | 59.02 | ✅ Top pick |
| VWAP Deviation Scalp | 65 | **56.9%** | +1.26 | 2.07 | ☑️ Solid |
| RSI Divergence Scalp | 71 | **56.3%** | +1.18 | 2.02 | ☑️ Solid |
| unknown (quan_engine) | 1,409 | 48.1% | +0.84 | 2.26 | ☑️ Volume |
| luxalgo_confluence | 339 | 42.5% | +0.35 | 1.46 | ⚠️ Low WR |
| enhanced_ml_A_xgboost | 776 | 39.9% | -0.00 | 1.00 | ❌ No edge |

### EQUITY (thin data)
| Strategy | n_trades | WR | AvgPnl | PF | Daily Sharpe |
|----------|----------|----|--------|----|-------------|
| MomentumEMA | 43 | **69.8%** | +1.51 | 4.17 | **3.32** ✅ |
| MeanReversionBB | 146 | 48.6% | +0.26 | 1.27 | **1.76** ⚠️ |

**Note:** The 90.8% EQUITY→CRYPTO misclassification bug means most "EQUITY"
picks are actually crypto (ETH-USD, BTC-USD, DOGE-USD, etc.). Only ~18/218
are real equities. Fix is in `signal_tracker.py` which hardcodes
`asset_class = "EQUITY"`.

### FOREX (very thin data)
| Strategy | n_trades | WR | AvgPnl | PF | Viable? |
|----------|----------|----|--------|----|---------|
| MeanReversionBB | 48 | 25.0% | +0.27 | 2.48 | ❌ Low WR |
| MomentumEMA | 20 | 40.0% | +0.31 | 1.79 | ⚠️ Insufficient |

### COMMODITY / MEME
- No strategies with >=10 trades
- Need more data accumulation before any edge claim

---

## 5. Gap: 7 daily PnL vs 27 validation

The daily PnL builder is **stricter**:
1. Excludes **TIME_EXIT** picks (many strats have 30-50% TIME_EXIT)
2. Requires entry_date < exit_date (excludes same-day entries that fail)
3. Excludes picks with |pnl_pct| >= 100

Without TIME_EXIT filter: **9 strategies** would qualify (vs 7).
The validation pipeline has a softer filter (includes TIME_EXIT picks).

**Recommendation:** Add `--include-time-exit` flag to daily PnL builder,
and also add `--by-asset-class` to break down per-class.

---

## 6. 6-Gate Recommendations

### Gate 1 (Sharpe)
- **Use daily PnL exit-day Sharpe** instead of per-trade annualized
- Threshold: **>= 1.0** (not the old >= 2.0 which was easy to hit with inflated values)
- With exit-day Sharpe: 6/7 strategies pass (85.7%)

### Gate 2 (t-test)
- Also inflated by per-trade annualization
- **Recommendation:** Use daily return t-test instead

### Gate 3 (Max Drawdown)
- Already reasonable — no change needed

### Gate 4 (Walk-Forward)
- Requires >=42 trades minimum — only 4 strategies qualify
- No change needed

### Gate 5 (Monte Carlo Bootstrap)
- **FIX VERIFIED** — both `Gate5_MonteCarloStressTest` (research) and
  `MonteCarloStressTester` (production) use proper bootstrap WITH replacement
- Now discriminates correctly: weak/noise strategies fail

### Gate 6 (FDR / BH)
- Already works correctly — 16/27 significant by BH-FDR

---

## 7. Actionable Next Steps

1. **Rename "unknown" strategy** → split by source_system for proper attribution
2. **Integrate daily PnL into validation pipeline** → replace per-trade Gate 1 Sharpe
3. **Fix asset_class tagging** → `signal_tracker.py` hardcodes EQUITY for all signals
4. **Run daily PnL by asset class** → understand per-class daily Sharpe
5. **Accumulate more trades** for EQUITY, FOREX, COMMODITY, MEME
