# Deep Edge Analysis by Asset Class — 2026-04-11

> **Objective:** Find true winners and actionable enhancements to increase WR / PF across every asset class.  
> **Dataset:** 3,500 closed picks + 82 active picks from `dashboard_data.json`  
> **Methodology:** Multi-dimensional analysis: direction, strategy, system, symbol, score, hold duration, exit reason, RR ratio, entry time. Compound filters to isolate the strongest edges.

---

## Executive Summary — Where the Edge Lives

| Asset Class | Trades | Baseline WR | Baseline PF | Best Filter | Filtered WR | Filtered PF | Enhancement |
|-------------|--------|-------------|-------------|-------------|-------------|-------------|-------------|
| **CRYPTO** | 2,129 | 52.8% | 1.80 | LONG + Score≥65 + 4-24h hold | **87.9%** | **19.21** | +35pp WR |
| **FOREX** | 546 | 43.6% | 2.00 | Hold ≤1h or >3d only | **49.5%** | **2.58** | +6pp WR |
| **EQUITY** | 576 | 37.3% | 0.70 | Score≥50 + LONG | **57.5%** | **1.66** | +20pp WR |
| **COMMODITY** | 211 | 43.1% | 1.08 | Hold ≤1h + entry 16-20 UTC | **62.9%** | **8.69** | +20pp WR |
| **BOND** | 8 | 50.0% | 25.90 | SHORT + ≤1h (current) | 50.0% | 25.90 | Keep as-is |
| **ETF** | 15 | 33.3% | 0.21 | Score≥50 | 75.0% | 0.80 | Tiny sample |
| **FUTURES** | 15 | 6.7% | 0.08 | — | — | — | **Kill entirely** |

---

## CRYPTO — The Money Maker

**Baseline:** 2,129 trades | 52.8% WR | PF 1.80 | +1,155.7% total PnL

### The 3 Laws of Crypto Edge

**1. LONG only. Kill SHORT.**
- LONG: 1,886 trades, **55.0% WR**, PF 2.11, +1,281% total
- SHORT: 243 trades, **35.4% WR**, PF 0.57, **-126% total**
- SHORT is a consistent loser across all windows. Every SHORT trade placed is on average -0.52%. Removing SHORT alone lifts WR by +2.2pp and saves 126% in PnL bleed.

**2. Score ≥ 65 is the magic cutoff.**
- B tier (65-80): 255 trades, **83.1% WR**, PF 11.04, +514%
- C tier (50-65): 803 trades, 52.3% WR, PF 1.76
- D tier (30-50): 1,034 trades, 46.0% WR, PF 1.27
- The jump from C→B is massive: +31pp WR, PF goes from 1.76 to 11.04. Score is a real predictor.

**3. Hold 4-24 hours. Not shorter, not longer.**
- ≤1h: 306 trades, 37.9% WR, PF 0.95 — **net negative**
- 1-4h: 623 trades, 44.9% WR, PF 1.31
- **4-12h: 702 trades, 61.8% WR, PF 2.98** ◀ SWEET SPOT
- **12-24h: 221 trades, 71.5% WR, PF 3.66** ◀ SWEET SPOT
- 1-3d: 256 trades, 48.8% WR — decaying

### Compound Winning Filters (cumulative improvements)

| Filter | Trades | WR | PF | Total PnL | vs Baseline |
|--------|--------|-----|-----|-----------|-------------|
| Baseline (all crypto) | 2,129 | 52.8% | 1.80 | +1,156% | — |
| LONG only | 1,886 | 55.0% | 2.11 | +1,281% | +2.2pp WR |
| LONG + Score≥50 | 996 | 61.6% | 3.05 | +1,013% | +8.9pp WR |
| LONG + Score≥65 | 255 | 83.1% | 11.04 | +514% | +30.3pp WR |
| LONG + Score≥50 + 4-24h | 514 | **73.5%** | **5.00** | +742% | +20.7pp WR |
| **LONG + Score≥65 + 4-24h** | **190** | **87.9%** | **19.21** | **+432%** | **+35.1pp WR** |
| LONG + Score≥65 + RR≥2 + 4-24h | 184 | **88.6%** | **22.13** | +425% | +35.8pp WR |

**The golden filter: LONG + Score≥65 + hold 4-24h = 87.9% WR on 190 trades.** That's not noise — that's 190 trades with near-90% hit rate.

### Top Strategies to Amplify

| Strategy | Trades | WR | PF | Avg PnL | Action |
|----------|--------|-----|-----|---------|--------|
| st_fear_greed_contrarian | 238 | **86.1%** | 15.11 | +2.13% | **MAX ALLOCATION** — best strategy by far |
| st_multi_day_momentum | 51 | 76.5% | 11.33 | +2.94% | Increase allocation |
| st_obv_support_divergence | 68 | 73.5% | 4.44 | +1.02% | Increase allocation |
| kimi_signal_tracking | 8 | 75.0% | 5.79 | +4.40% | **UNBLOCK** (currently blocked!) |
| st_rsi_momentum_confluence | 103 | 55.3% | 1.84 | +0.64% | Good edge, keep |
| claude_ml_moderate_mut | 27 | 59.3% | 2.48 | +0.84% | Promising, scale up |
| MeanReversionBB | 15 | 60.0% | 3.01 | +1.14% | Small sample but strong |

### Strategies to Kill / Demote

| Strategy | Trades | WR | PF | Avg PnL | Action |
|----------|--------|-----|-----|---------|--------|
| enhanced_ml_A_xgboost | 152 | 30.9% | 0.67 | -0.45% | **KILL** — 152 losing trades |
| claude_gainer_1h | 15 | 46.7% | 0.25 | -3.34% | KILL — PF 0.25 is catastrophic |
| stochrsi_macd_combo | 6 | 16.7% | 0.12 | -1.43% | KILL |
| crypto_kalman_trend_residual_reversion_v1 | 11 | 9.1% | 0.03 | -0.45% | KILL |

### Top Crypto Symbols

| Symbol | Trades | WR | PF | Total PnL | Action |
|--------|--------|-----|-----|-----------|--------|
| ARBUSDT | 75 | 65.3% | 3.90 | +170.8% | Focus — best edge |
| DOTUSDT | 93 | 58.1% | 3.70 | +94.0% | Focus |
| APTUSDT | 61 | 68.9% | 3.26 | +78.7% | Focus |
| XRPUSDT | 67 | 76.1% | 3.84 | +69.9% | Focus |
| TIAUSDT | 18 | 83.3% | 7.89 | +36.9% | Focus — small but elite |
| ATOMUSDT | 23 | 82.6% | 7.16 | +31.8% | Focus |

### Symbols to Avoid / Blacklist

| Symbol | Trades | WR | PF | Total PnL | Action |
|--------|--------|-----|-----|-----------|--------|
| TRXUSDT | 48 | **6.2%** | 0.04 | **-76.0%** | **BLACKLIST** — 6% WR on 48 trades |
| JTOUSDT | 41 | 22.0% | 0.52 | -31.0% | BLACKLIST |
| ENAUSDT | 12 | 25.0% | 0.43 | -17.0% | BLACKLIST |
| DYDXUSDT | 12 | 25.0% | 0.16 | -12.7% | BLACKLIST |
| SHIBUSDT | 7 | 0.0% | 0.00 | -9.9% | BLACKLIST |
| ESPUSDT | 10 | 20.0% | 0.58 | -8.6% | Avoid |

### Best Entry Time (UTC)

| UTC Block | Trades | WR | PF | Total PnL |
|-----------|--------|-----|-----|-----------|
| 00-04 | 321 | 43.3% | 1.19 | +49% |
| **04-08** | 249 | **55.4%** | 2.25 | **+169%** |
| **08-12** | 254 | **55.9%** | 2.32 | **+170%** |
| **12-16** | 407 | **63.9%** | **2.80** | **+452%** |
| **16-20** | 360 | **57.2%** | 2.42 | +305% |
| 20-00 | 529 | 44.6% | 1.05 | +23% |

**Best window: 12-16 UTC (8am-12pm EST).** 63.9% WR, PF 2.80, +452% total. Worst: 20-00 UTC — 44.6% WR, barely breakeven.

### Exit Reason: What's Killing Crypto PnL?

- **SL_HIT:** 320 trades, **-671%** PnL impact. Avg loss -2.10%.
- **SL (generic):** 374 trades, -246% PnL impact. Avg loss -0.66%.
- **TP_HIT:** 416 trades, **+1,273%** PnL impact. Avg win +3.06%.
- **ATR Trailing Stop:** 35 trades, 71.4% WR, +27% — ATR trailing works well.
- Stop losses are the #1 PnL destroyer. Consider tighter SL on low-score picks, wider SL on high-score picks.

---

## EQUITY — Salvageable With Score Filtering

**Baseline:** 576 trades | 37.3% WR | PF 0.70 | **-413% total PnL**

Equity is a net loser, but there's a clear signal buried in the noise.

### The Score Wall

| Score Tier | Trades | WR | PF | Total PnL |
|------------|--------|-----|-----|-----------|
| B (65-80) | 9 | **88.9%** | 5.14 | +12.8% |
| C (50-65) | 147 | **54.4%** | 1.57 | **+138.0%** |
| D (30-50) | 368 | 31.8% | 0.54 | **-454.5%** |
| F (<30) | 52 | 19.2% | 0.31 | -109.2% |

**Score < 50 = guaranteed losses.** D-tier alone lost -455%. The entire equity loss (-413%) is caused by sub-50 score picks. Score≥50 picks are **profitable** (+151%).

### Compound Filters

| Filter | Trades | WR | PF | Total PnL | Improvement |
|--------|--------|-----|-----|-----------|-------------|
| Baseline | 576 | 37.3% | 0.70 | -413% | — |
| **Score≥50** | 156 | **56.4%** | **1.62** | **+151%** | +19pp WR, PF 0.70→1.62 |
| Score≥50 + LONG | 153 | 57.5% | 1.66 | +157% | +20pp WR |
| Score≥65 | 9 | 88.9% | 5.14 | +13% | Tiny sample |
| Kill SL_HIT | 416 | 51.7% | 1.75 | +417% | Remove SL_HIT trades → profitable |

### Exit Reason: SL_HIT is the Killer

- **SL_HIT:** 160 trades, 0% WR, avg -5.19%, **-830% PnL impact**
- **TP_HIT:** 54 trades, 100% WR, avg +8.17%, +441% PnL impact
- SL_HIT alone destroys -830%. Everything else is net positive (+417%).
- **Enhancement:** Tighten entry criteria so fewer picks hit SL. Score≥50 filter eliminates most SL hits.

### Winning Equity Strategies

| Strategy | Trades | WR | PF | Total |
|----------|--------|-----|-----|-------|
| stocks_rsi2_pullback | 9 | **88.9%** | 5.14 | +12.8% |
| rs-breakout-scout | 13 | **69.2%** | 4.90 | +25.8% |
| quality-minus-junk | 22 | 63.6% | 1.64 | +14.9% |
| Breakout Momentum | 33 | 54.5% | 1.58 | +31.8% |
| rsi-divergence-scout | 14 | 50.0% | 2.06 | +22.1% |

### Losing Equity Strategies to Kill

| Strategy | Trades | WR | PF | Total |
|----------|--------|-----|-----|-------|
| Value + Quality | 48 | **6.2%** | 0.14 | **-243%** |
| Consecutive Beats | 39 | 25.6% | 0.54 | -72% |
| Earnings Drift | 19 | 15.8% | 0.30 | -57% |
| Dividend Aristocrats | 8 | 0.0% | 0.00 | -50% |
| ML Ranker | 32 | 28.1% | 0.61 | -32% |

**Value + Quality alone lost -243% on 48 trades at 6.2% WR.** Kill it. That single strategy accounts for more than half the equity losses.

### Hold Duration

- **≤4h: AVOID** — 0-37% WR
- **1-3d: AVOID** — 32.4% WR, -70% PnL
- **>7d: GOOD** — 59.2% WR, +18% PnL. Equity needs time to work.

---

## FOREX — Scalp or Swing, Nothing In Between

**Baseline:** 546 trades | 43.6% WR | PF 2.00 | +211% total PnL

Forex is profitable but has a bizarre bimodal pattern: it works at **≤1h** and **>3d**, and **loses at everything in between**.

### Hold Duration: The Dead Zone

| Duration | Trades | WR | PF | Total PnL |
|----------|--------|-----|-----|-----------|
| **≤1h** | 312 | **49.4%** | 2.54 | **+28%** |
| 1-4h | 30 | **13.3%** | 0.24 | -2.0% |
| 4-12h | 20 | 30.0% | 0.83 | -0.5% |
| 12-24h | 22 | 18.2% | 0.37 | -4.4% |
| 1-3d | 29 | 31.0% | 1.03 | +0.2% |
| **>7d** | 56 | **50.0%** | 2.64 | **+207%** |

**1h-3d is a dead zone for forex.** Everything between 1h and 3d loses. Either scalp (≤1h) or swing (>7d).

### Winning Strategies

| Strategy | Trades | WR | PF | Total |
|----------|--------|-----|-----|-------|
| kimi_signal_tracking | 25 | 44.0% | 2.92 | +203% |
| forex_rsi2_mean_reversion | 326 | 48.2% | 3.69 | +35% |
| fx_smart_carry_trade_momentum | 10 | 60.0% | 165.83 | +2.4% |
| forex-rsi-ema-scout | 14 | 57.1% | 2.62 | +4.5% |
| Bollinger MR | 12 | 75.0% | 5.24 | +2.7% |

### Losing Strategies to Kill

| Strategy | Trades | WR | PF | Total |
|----------|--------|-----|-----|-------|
| Breakout Momentum | 26 | 30.8% | 0.27 | -17.8% |
| community_london_breakout_v2_forex | 8 | 0.0% | 0.00 | -7.9% |
| ML Ranker | 14 | 35.7% | 0.28 | -6.9% |
| forex_carry_momentum | 4 | 25.0% | 0.12 | -8.0% |

### Direction

- **BUY:** 25 trades, 44% WR, +203% PnL — high average due to outliers
- **LONG:** 348 trades, 42.5% WR, PF 0.90 — net loser
- **SHORT:** 173 trades, 45.7% WR, PF 1.89 — slight edge

SHORT marginally outperforms LONG on forex. Unlike crypto (LONG-only), forex has no strong directional bias.

---

## COMMODITY — Scalp the 16-20 UTC Window

**Baseline:** 211 trades | 43.1% WR | PF 1.08 | +6.5% total PnL

Barely breakeven, but one clear edge exists.

### The Time Window Edge

| UTC Block | Trades | WR | PF | Total PnL |
|-----------|--------|-----|-----|-----------|
| 00-04 | 35 | 40.0% | 0.72 | -5.0% |
| 04-08 | 32 | 28.1% | 0.27 | -14.3% |
| 08-12 | 23 | 34.8% | 0.27 | -4.4% |
| 12-16 | 28 | 25.0% | 0.25 | -13.2% |
| **16-20** | 62 | **62.9%** | **8.69** | **+40.8%** |
| 20-00 | 31 | 45.2% | 1.16 | +2.6% |

**16-20 UTC (12-4pm EST) is the only profitable commodity window.** 62.9% WR, PF 8.69. All other windows are net losers. Gate commodity entries to 16-20 UTC only.

### Hold Duration: ≤1h Only

- **≤1h:** 174 trades, 46.6% WR, +12.3% — only profitable duration
- 1-4h: 23 trades, 26.1% WR, -3.5% — collapse
- Commodities are pure scalp plays via `futures_momentum` on `multi_asset_copytrader`.

---

## BOND — Small but Efficient

**Baseline:** 8 trades | 50.0% WR | PF 25.90 | +4.9%

Only 8 trades, all SHORT via `futures_momentum` / `multi_asset_copytrader`. Avg loss is tiny (-0.05%) while avg win is +1.29%. Excellent risk/reward asymmetry but very low volume. No changes needed — just scale up if possible.

---

## ETF — Kill or Radically Reform

**Baseline:** 15 trades | 33.3% WR | PF 0.21 | -22.1%

ETFs are losing badly. `extreme_oversold_bounce` is 0% WR across 6 trades (-22.5%). `multi_asset_institutional` is 16.7% WR. The only hope: Score≥50 filter (4 trades, 75% WR) but sample is too small.

**Recommendation: Pause ETF picks** until strategies are redesigned. The current approach doesn't work.

---

## FUTURES — Kill Entirely

**Baseline:** 15 trades | 6.7% WR | PF 0.08 | -94.1%

One trade out of 15 won. PF 0.08. One outlier loss of -87.89% via `connors_rsi2`. `multi_asset_scanner` runs the system at 7.7% WR. There is no edge here.

**Recommendation: Hard-block all FUTURES picks.** Remove `futures_ema_stack_momentum` (already blocked). Consider blocking `connors_rsi2` on futures.

---

## Top 10 Enhancements — Ranked by PnL Impact

| # | Enhancement | Asset | Expected WR Impact | Expected PnL Saved/Gained | Complexity |
|---|-------------|-------|-------------------|---------------------------|------------|
| 1 | **Kill crypto SHORT** — remove all SHORT crypto picks | CRYPTO | +2.2pp → 55.0% | Saves **126%** in losses | Low — filter gate |
| 2 | **Enforce Score≥50 on equity** — gate all equity entries | EQUITY | +19pp → 56.4% | Saves **564%** in losses | Low — score gate |
| 3 | **Kill crypto ≤1h exits** — don't enter if expected hold <1h | CRYPTO | +15pp on affected | Saves **13%** in losses | Medium — duration estimate |
| 4 | **Kill `Value + Quality` strategy** on equity | EQUITY | Removes 48 losing trades | Saves **243%** in losses | Low — strategy block |
| 5 | **Kill `enhanced_ml_A_xgboost`** on crypto | CRYPTO | Removes 152 losing trades | Saves **69%** in losses | Low — strategy block |
| 6 | **Gate commodity entries to 16-20 UTC only** | COMMODITY | +20pp → 62.9% | Saves **37%** in losses | Low — time gate |
| 7 | **Forex: kill 1h-3d hold zone** — only scalp or swing | FOREX | +6pp → 49.5% | Saves **7%** in losses | Medium — hold gate |
| 8 | **Blacklist TRXUSDT** — 6% WR on 48 trades | CRYPTO | Removes 48 losing trades | Saves **76%** in losses | Low — symbol block |
| 9 | **Unblock kimi_signal_tracking** | CRYPTO | Adds winning trades | Gains **+46%** (blocked now) | Low — unblock |
| 10 | **Hard-block FUTURES + ETF** asset classes | FUTURES/ETF | Eliminates 30 losing trades | Saves **116%** in losses | Low — asset gate |

---

## Implementation Priority

### Phase 1 — Immediate (filter gates, no strategy changes)
- [ ] Add `direction === 'LONG'` gate for crypto picks
- [ ] Add `score >= 50` gate for equity picks  
- [ ] Add `16-20 UTC` time gate for commodity entries
- [ ] Blacklist TRXUSDT, JTOUSDT, SHIBUSDT, ENAUSDT, DYDXUSDT
- [ ] Unblock `kimi_signal_tracking` and `signal_validation`
- [ ] Hard-block FUTURES asset class

### Phase 2 — Strategy-level cleanup
- [ ] Kill `Value + Quality` on equity
- [ ] Kill `enhanced_ml_A_xgboost` on crypto
- [ ] Kill `Dividend Aristocrats` on equity
- [ ] Kill `Earnings Drift` on equity (15.8% WR)
- [ ] Kill `Breakout Momentum` on forex (30.8% WR)
- [ ] Promote `st_fear_greed_contrarian` to max allocation on crypto

### Phase 3 — Duration-based gating
- [ ] Crypto: prefer 4-24h hold targets, penalize <1h
- [ ] Forex: bifurcate into scalp (≤1h) and swing (>7d) modes
- [ ] Equity: prefer >7d holds, avoid 1-3d

---

*Generated 2026-04-11 from 3,500 closed picks across 7 asset classes. Raw analysis data: `deep_edge_analysis_raw.log`*
