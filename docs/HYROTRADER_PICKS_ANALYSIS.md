# HyroTrader Picks Analysis — Are They Good Enough?

**Date:** April 12, 2026
**Scope:** Evaluate current Hyro picks & backtested strategies against prop firm challenge rules, then recommend enhancements informed by Hyro's own blog research.

---

## 1. Challenge Rules Summary (Confirmed from hyrotrader.com, Apr 2026)

| Rule | 1-Step | 2-Step (Our program) |
|------|--------|----------------------|
| **Profit target** | 10% | P1: **10% ($500)** / P2: **5% ($250)** |
| **Max daily loss** | 4% | **5% ($250)** |
| **Max overall loss** | 6% | **10% ($500)** |
| **Min trading days** | 10 | **10** per phase |
| **Time limit** | Unlimited | Unlimited |
| **SL obligation** | Yes (within 5 min) | Yes (within 5 min) |
| **Drawdown type** | Trailing | **Trailing (tick-by-tick)** |
| **Consistency rule** | ~40% | **~40%** (no single day > 40% of target) |

**Key constraint:** The trailing DD ratchets from **peak equity** (including unrealized), not starting balance. This is the #1 killer — 95% of failures in our backtests are trailing DD breaches.

---

## 2. Current Live Account Status

| Metric | Value |
|--------|-------|
| Phase | 2-Step · Phase 1 |
| Start equity | $5,000 |
| Current equity | **$4,929.34** |
| Cumulative PnL | **−$70.66** |
| High-water mark | $5,070.30 |
| DD used from HWM | **$140.96** |
| DD budget remaining | **$359.04** (of $500 max) |
| Trading days logged | 0 |

**Verdict:** Account is **down 1.4%** with **$359 of DD budget left**. The HWM already ratcheted to $5,070, meaning $141 of trailing DD was consumed by a gain that was given back. This is exactly the trailing DD trap our playbook warns about.

---

## 3. Backtest Results — Original Playbook Strategies

The 5 strategies in `HYROTRADER_CHALLENGE_STRATEGY.md` were backtested over 6 months on BTC/ETH/SOL/BNB:

| Strategy | Symbol | PnL | WR | Max DD | Status |
|----------|--------|-----|-----|--------|--------|
| RSI(2) Extreme | BTCUSDT | −$71.65 | 33.3% | $212 | Incomplete |
| Volume Breakout | BTCUSDT | −$37.50 | 30.8% | **$513** | **FAILED** (DD) |
| S/R Bounce | BTCUSDT | −$337.43 | 32.8% | **$502** | **FAILED** (DD) |
| RSI(2) Extreme | ETHUSDT | −$201.29 | 28.6% | $236 | Incomplete |
| Volume Breakout | ETHUSDT | +$337.50 | 38.6% | $391 | Incomplete |
| S/R Bounce | ETHUSDT | −$421.35 | 15.0% | **$507** | **FAILED** (DD) |
| RSI(2) Extreme | SOLUSDT | −$55.84 | 41.7% | $233 | Incomplete |
| Volume Breakout | SOLUSDT | +$122.85 | 35.8% | $449 | Incomplete |
| S/R Bounce | SOLUSDT | −$359.49 | 33.3% | **$502** | **FAILED** (DD) |
| RSI(2) Extreme | BNBUSDT | +$28.30 | 50.0% | $186 | Incomplete |
| Volume Breakout | BNBUSDT | −$150.19 | 31.0% | $465 | Incomplete |
| S/R Bounce | BNBUSDT | −$381.69 | 34.7% | **$505** | **FAILED** (DD) |

**Pass rate: 0/12 (0%).** Not a single original strategy passed the challenge in backtesting.

- S/R Bounce **failed on every symbol** (trailing DD breach).
- Volume Breakout failed on BTC, came close on SOL/ETH but never hit the $500 target.
- RSI(2) Extreme was too infrequent (9–14 trades over 6 months) to generate enough profit.

### Extended Strategies (EMA 9/21 Crossover)

| Symbol | PnL | WR | PF | Max DD | Status |
|--------|-----|-----|-----|--------|--------|
| SOLUSDT | +$208 | 38% | 1.18 | $340 | Incomplete |
| ETHUSDT | +$188 | 36% | 1.16 | $362 | Incomplete |
| BTCUSDT | −$346 | 28.6% | 0.77 | $449 | Incomplete |

Better, but still no passes. BTC is the worst performer across all strategies.

---

## 4. Batch 2 Strategies — Where the Winners Are

The batch2 sweep tested **176 strategy × symbol combinations** over 6 months. Results:

| Outcome | Count | % |
|---------|-------|---|
| **PASSED** | **35** | 19.9% |
| Failed | 105 | 59.7% |
| Incomplete | 36 | 20.5% |

**Failure breakdown:** 95% of failures were trailing DD breaches, 3% daily DD, 2% consistency rule.

### Top 15 Challenge Passers

| Rank | Symbol | Strategy | PnL | WR | PF | Max DD | Trades |
|------|--------|----------|-----|-----|-----|--------|--------|
| 1 | BTCUSDT | **CCI Divergence** | **+$1,125** | 51.9% | 2.15 | $263 | 54 |
| 2 | AVAXUSDT | **CMF Cross** | +$962 | 43.5% | 1.53 | $230 | 85 |
| 3 | XRPUSDT | **BB Squeeze Breakout** | +$947 | 39.6% | 1.41 | $279 | 101 |
| 4 | AVAXUSDT | **BB Squeeze Breakout** | +$932 | 42.6% | 1.46 | $388 | 94 |
| 5 | XRPUSDT | **DEMA Crossover** | +$898 | 42.2% | 1.50 | $399 | 83 |
| 6 | AVAXUSDT | **ADX Vol Breakout** | +$780 | 38.3% | 1.56 | $267 | 60 |
| 7 | ETHUSDT | **ADX Vol Breakout** | +$769 | 41.3% | 1.76 | **$207** | 46 |
| 8 | ETHUSDT | **True Strength Index** | +$769 | 39.6% | 1.64 | $428 | 53 |
| 9 | SOLUSDT | **Hull MA Trend** | +$749 | 40.0% | 1.33 | $356 | 100 |
| 10 | XRPUSDT | **Hull MA Trend** | +$736 | 37.5% | 1.33 | $356 | 96 |
| 11 | BTCUSDT | Hull MA Trend | +$648 | 38.9% | 1.26 | $359 | 108 |
| 12 | SOLUSDT | CCI Divergence | +$638 | 42.6% | 1.49 | $208 | 61 |
| 13 | BTCUSDT | ADX Vol Breakout | +$619 | 36.8% | 1.46 | $327 | 57 |
| 14 | SOLUSDT | **Multi-EMA Stack** | +$601 | **48.6%** | **1.89** | **$172** | 35 |
| 15 | BTCUSDT | TTM Squeeze Momentum | +$563 | 41.3% | 1.41 | $292 | 63 |

---

## 5. Honest Assessment: Can We Pass?

### The Original Playbook: NO

The 5 strategies in `HYROTRADER_CHALLENGE_STRATEGY.md` (Bollinger reversion, RSI(2), funding contrarian, volume breakout, S/R bounce) are **not passing the challenge** in backtesting. Zero passes out of 12 runs.

**Why they fail:**
1. **S/R Bounce** is a death trap — low win rate (15–35%) with DD that consistently exceeds $500.
2. **RSI(2) Extreme** generates too few signals (9–14 trades/6mo) to compound to +$500.
3. **Volume Breakout** works on ETH/SOL but not BTC/BNB — inconsistent.
4. **Bollinger Reversion** (not even in the backtest results) — missing from the main backtest run entirely.

### The Batch 2 Strategies: YES, selectively

35 out of 176 combos pass (20%). The **best performers** share traits:
- **Profit factor > 1.4** (winners outsize losers by 40%+)
- **Max DD < $300** (leaves $200+ buffer vs the $500 limit)
- **Win rate 38–52%** (enough to grind, not so high that losses are catastrophic)
- **40–100 trades** over 6 months (enough for consistency, not overtrading)

### The Live Account: IN DANGER

The account is already down $140.96 from HWM with $359 budget left. Using the original playbook strategies that have a 0% pass rate would very likely blow the remaining DD budget. **The playbook needs to pivot to proven batch2 strategies immediately.**

---

## 6. Strategies from Hyro's Blog — Mapped to Our Backtest Data

The [Hyrotrader blog post](https://www.hyrotrader.com/blog/most-profitable-trading-strategy/) recommends these strategy families. Here's how they map to our data:

### a) Trend Following (Blog: 29–58% CAGR, 25–50% WR)

**Our best matches:**
- **Hull MA Trend** — Passed on BTC/SOL/XRP. PF 1.26–1.33. This is a clean trend-following approach.
- **ADX Volatility Breakout** — Passed on AVAX/ETH/BTC. PF 1.46–1.76. ADX confirms trend strength before entry.
- **DEMA Crossover** — Passed on XRP. Fast crossover = early trend entry.

**Blog alignment:** Blog says trend following works exceptionally well in crypto given extended directional moves. Our data confirms: trend strategies (Hull MA, ADX, DEMA) pass at higher rates than mean reversion strategies on most symbols.

### b) Mean Reversion (Blog: 68–71% WR, but hidden tail risk)

**Our best matches:**
- **CCI Divergence** — #1 passer ($1,125 PnL, 52% WR, PF 2.15). Uses divergence between price and CCI to catch reversions.
- **BB Squeeze Breakout** — Passed on XRP/AVAX. Squeeze → breakout catches the exit from low-vol compression.
- **Keltner Channel Reversion** (12-month data) — 50% WR, PF 3.38 but failed consistency rule due to one huge day.

**Blog alignment:** Blog warns that mean reversion carries hidden danger of catastrophic losses when markets trend beyond extremes. Our data confirms: most pure mean-reversion strategies (RSI(2), S/R Bounce, Bollinger) **fail** due to trailing DD. The ones that pass (CCI, BB Squeeze) add divergence/momentum confirmation to avoid catching falling knives.

### c) Swing Trading (Blog: 35–50% WR, 12–45% per trade)

**Our best matches:**
- **Multi-EMA Stack (9/21/55)** — 48.6% WR, PF 1.89, lowest DD of any passer ($172). This is essentially a swing setup.
- **True Strength Index** — 39.6% WR, PF 1.64. TSI is a momentum oscillator ideal for 4h/1d swing setups.
- **TTM Squeeze Momentum** — 41.3% WR, PF 1.41. Squeeze → momentum breakout = classic swing entry.

**Blog alignment:** Blog recommends swing trading as the sweet spot for crypto (captures moves without constant screen time). Our data agrees: swing-oriented strategies with 35–100 trades over 6 months have the best pass rates.

### d) Breakout Trading (Blog: 36% success, but 62% on false breakouts)

**Our data:**
- **Volume Breakout** (original playbook) — mixed results, failed on BTC/BNB.
- **BB Squeeze Breakout** — passed on XRP/AVAX, suggesting squeeze-filtered breakouts > raw breakouts.
- **ADX Vol Breakout** — passed on 3 symbols. ADX filter ensures you're breaking out into a real trend.

**Blog alignment:** Blog notes only 36% of breakouts succeed, but **filtered** breakouts (volume, squeeze, ADX confirmation) perform much better. Our data strongly confirms this — raw breakout strategies fail, filtered ones pass.

### e) Scalping (Blog: 55–65% WR, eroded by costs)

**Not recommended for Hyro challenge.** The 0.75% risk per trade and $37.50 risk budget make scalping impractical — you'd need too many trades to compound, and the consistency rule caps daily profit at $200 (P1) / $100 (P2).

---

## 7. Recommended Strategy Changes

### Immediate (for current live account)

**STOP using** S/R Bounce, raw Volume Breakout, and RSI(2) Extreme on BTC as primary strategies. They have 0% pass rates.

**SWITCH to a top-3 proven strategy:**

| Priority | Strategy | Best Symbol(s) | Why |
|----------|----------|-----------------|-----|
| 1 | **CCI Divergence** | BTC, SOL | Best PnL ($1,125), highest PF (2.15), moderate DD ($263) |
| 2 | **ADX Vol Breakout** | ETH, AVAX | Best risk-adjusted (PF 1.76 on ETH, lowest DD $207) |
| 3 | **Multi-EMA Stack** | SOL | Highest WR (48.6%), lowest DD ($172), great PF (1.89) |

### Position Sizing Adjustment

With only **$359 DD budget remaining**, reduce risk from 0.75% to **0.50%** ($25/trade) until equity recovers above $5,000. This gives ~14 consecutive losses before DD breach vs ~9.5 at 0.75%.

### Trading Day Cadence

Need **10 trading days minimum** and account has **0 logged**. At ~$50/day target:
- Conservative path: 10–15 days × $33–50/day = $330–750 → enough for Phase 1 target ($500)
- No hero days: cap at ~$150/day (well under $200 consistency limit) to avoid trailing DD ratchet

---

## 8. New Strategies to Backtest (from Blog Research)

These strategies are **not yet in our backtester** but are recommended by the Hyrotrader blog with academic backing:

### a) MACD + EMA Trend Following (Blog: "foundation for most profitable forex traders")
- **Setup:** MACD(12,26,9) crossover with EMA(50) directional filter
- **Timeframe:** 1h/4h
- **Why:** Combines momentum (MACD signal line cross) with trend confirmation (above/below 50 EMA)
- **Backtest params:** Long when MACD crosses above signal + price > EMA50; short when MACD crosses below signal + price < EMA50; SL = 1.5× ATR; TP = 2× risk

### b) RSI + Bollinger Band Combo (Blog: "71% win rate during ranging conditions")
- **Setup:** RSI(14) < 30 + price touches lower BB(20,2) = long; RSI > 70 + upper BB = short
- **Timeframe:** 1h
- **Why:** Dual confirmation reduces false signals vs single-indicator mean reversion
- **Key difference from our Bollinger strategy:** Uses RSI(14) not RSI(2), and requires BOTH indicators to agree (our current Bollinger strategy uses RSI(14) but with loose thresholds of 35/65)
- **Enhancement:** Add ADX < 25 filter to only take mean-reversion trades in non-trending regimes

### c) False Breakout Reversal (Blog: "62% success rate, 1:2.5 R:R")
- **Setup:** Price breaks above/below 20-period high/low → fails to hold within 3 bars → enter counter-direction
- **Timeframe:** 1h
- **Why:** Blog data shows false breakout reversal (62% WR) beats traditional breakout (54% WR)
- **Backtest params:** Breakout level = 20-bar high/low; failure = 3 bars close back inside range; entry on failure bar close; SL beyond breakout extreme; TP at opposite range boundary

### d) Carry/Funding Rate + Reversion Hybrid (Blog: "steady income in stable markets")
- **Setup:** Extreme negative funding rate on BTC/ETH perps → long with BB/RSI reversion confirmation
- **Timeframe:** 4h/1d
- **Why:** Funding rate < -0.01% signals crowded shorts → mean reversion more likely
- **Note:** Requires funding rate data feed (available from Binance API fapi/v1/fundingRate)

### e) Wheel-Inspired Risk Scaling (Blog: "15–40% annual, 70–75% WR" — adapted for futures)
- **Concept:** Not options wheel, but the risk management philosophy: start small → scale up on winners → reduce on losers
- **Implementation:** Begin at 0.50% risk; after 3 consecutive wins, scale to 0.75%; after any loss, back to 0.50%
- **Why:** Asymmetric risk scaling compounds wins and limits DD — critical for trailing DD prop accounts

---

## 9. Backtest Priority Queue

Ranked by expected impact × implementation effort:

| Priority | Strategy | Effort | Expected Impact | Rationale |
|----------|----------|--------|-----------------|-----------|
| **1** | MACD + EMA50 Trend | Low (indicators exist) | High | Blog's #1 recommendation; straightforward to implement |
| **2** | RSI(14) + BB Dual Confirm + ADX filter | Low | High | Tightens our existing Bollinger strategy; adds regime filter |
| **3** | False Breakout Reversal | Medium | High | Counter-trend with better stats than raw breakout |
| **4** | Adaptive Risk Scaling (0.50%→0.75%) | Low | Medium | Meta-strategy; works on top of any signal |
| **5** | Funding Rate Contrarian + Reversion | Medium | Medium | Needs funding data integration; powerful but rare signals |

---

## 10. Summary

**Are the current picks good enough?** The original playbook strategies have a **0% backtest pass rate**. The live account is already down $141 from HWM. Continuing with S/R Bounce and raw Volume Breakout would very likely fail the challenge.

**What should change?**
1. **Immediately pivot** to proven batch2 strategies (CCI Divergence, ADX Vol Breakout, Multi-EMA Stack)
2. **Reduce risk** to 0.50% per trade given reduced DD budget
3. **Backtest** 5 new strategies from the Hyro blog research (MACD+EMA, dual RSI+BB, false breakout reversal, funding rate hybrid, adaptive risk scaling)
4. **Wire the best batch2 passers** into `hyro_live_signals.js` and `hyro_live_strategies.json` so the live dashboard shows actionable signals from strategies that actually pass

**Bottom line:** The research infrastructure is solid — 176 strategy combinations backtested with prop-firm-constrained simulation. The problem is the live playbook is using the wrong strategies. The batch2 data shows 35 combinations that pass; the playbook should be rebuilt around the top 5.

---

*Analysis based on: `hyro_backtest_results.json`, `hyro_backtest_extended_results.json`, `hyro_batch2_results.json`, `hyro_backtest_12m_new_strategies.json`, `hyrotrader_picks.json`, and https://www.hyrotrader.com/blog/most-profitable-trading-strategy/. Not financial advice.*
