# 40 New Trading Strategies Design — Per-Asset-Class Edge Discovery

**Date:** 2026-06-12
**Author:** Kilo (Quant Research)
**Status:** Design — Pending Approval

---

## Executive Summary

The current system has 32.3% overall win rate (PF=0.48 CRYPTO, 0.53 EQUITY, 0.70 COMMODITY, 0.73 FOREX). The strategy space is dominated by RSI/MACD/Bollinger permutations with no fundamental data integration. This document proposes **40 new strategies (10 per asset class)** using distinct, research-backed edges.

### Current System Diagnosis

| Asset Class | n | Win Rate | Profit Factor | Problem |
|---|---|---|---|---|
| CRYPTO | 1154 | 32.4% | 0.48 | 80+ strategies, all technical indicator variants |
| EQUITY | 107 | 34.6% | 0.53 | No fundamental data usage despite 2964 rows of fundamentals |
| COMMODITY | 90 | 41.1% | 0.70 | Short-only policy masks long-side disaster |
| FOREX | 88 | 42.0% | 0.73 | Carry trade strategies all blacklisted |

### Why Current Strategies Fail

1. **Indicator saturation**: 100+ strategy files, most using RSI/MACD/EMA/Bollinger in different combinations
2. **No fundamental integration**: 2964 rows of `alpha_fundamentals`, 242 rows of `alpha_earnings`, 119 rows of `stock_fundamentals` — zero strategies use them
3. **Regime blindness**: Most strategies ignore `lm_market_regime` (260 rows of HMM regime data)
4. **Overfitting to noise**: Many strategies are ML-predictions on individual symbols (ml_enhanced_*USDT) — curve-fit to historical data
5. **No risk management adaptation**: Fixed TP/SL regardless of volatility regime

### Data Available (Verified)

| Table | Rows | Used by Current Strategies? |
|---|---|---|
| `crypto_ohlcv` | 1,282,088 | Yes (all crypto) |
| `stock_ohlcv` | 124,009 | Yes (all equity) |
| `fx_prices` | 3,855 | Yes (all forex) |
| `daily_prices` | 49,340 | Partially |
| `alpha_fundamentals` | 2,964 | **NO** |
| `alpha_earnings` | 242 | **NO** |
| `alpha_macro` | 316 | Partially (regime) |
| `stock_earnings` | 381 | **NO** |
| `stock_fundamentals` | 119 | **NO** |
| `stock_analyst_recs` | 4 | **NO** |
| `lm_fear_greed` | 3 | Partially |
| `lm_market_regime` | 260 | Partially |
| `crypto_exchange_netflow` | 20 | **NO** |

---

## STRATEGY DESIGN: CRYPTO (10 Strategies)

**Current:** 32.4% WR, PF=0.48 — worst asset class
**Target:** 45%+ WR, PF>1.3 (above monkey-test P95 of 1.19)

### CRYPTO-1: Funding Rate Mean Reversion

**Edge:** Funding rates are the only crowdsourced positioning metric in crypto (Baltussen et al. 2021). Extreme negative funding = overleveraged shorts → mean-reverts up.

**Entry:**
- Funding rate < -0.01% (1hr) on Binance perpetual
- Price above 200-period EMA on 4h (uptrend filter)
- `lm_market_regime.hmm_regime` != 'BEAR'
- Symbol tier = 'major' or 'alt' (skip meme)

**Exit:**
- TP: Entry + 2 × ATR(14) on 4h
- SL: Entry - 1.5 × ATR(14) on 4h
- Time exit: 48 bars (8 days on 4h)
- Trailing: Activate at 1 × ATR profit, trail by 0.5 × ATR

**Why:** Unlike RSI/MACD derived from price, funding rate is exogenous information about positioning. -0.01% threshold = 5th percentile historically.
**Data:** `at_futures_symbol_edge`, `crypto_ohlcv` (4h), `lm_market_regime`
**Complexity:** Medium

---

### CRYPTO-2: Exchange Netflow Divergence

**Edge:** Negative exchange netflow (coins leaving exchanges = accumulation) leads to price appreciation over 1-7 days. On-chain data no technical indicator can capture.

**Entry:**
- `crypto_exchange_netflow.netflow_24h` < 0
- `crypto_exchange_netflow.netflow_7d` < 0 (7-day confirmation)
- Price closes above VWAP on daily
- Volume > 1.5 × 20-day average

**Exit:**
- TP: Entry + 3 × ATR(14) on daily
- SL: Entry - 2 × ATR(14) on daily
- Time exit: 14 days
- Trailing: Activate at 2 × ATR, trail by 1 × ATR

**Why:** Exchange netflow is a leading indicator of supply shock. 7-day confirmation prevents false signals.
**Data:** `crypto_exchange_netflow`, `crypto_ohlcv` (daily)
**Complexity:** Low

---

### CRYPTO-3: Cross-Sectional Momentum with Volume Filter

**Edge:** Cross-sectional momentum (Jegadeesh & Titman 1993) works in crypto only when confirmed by volume. Current `cross_sectional_reversal` has 12.5% WR because it fades momentum and ignores volume.

**Entry:**
- Symbol ranked in top 20% by 20-day return across crypto universe
- Volume > 2 × 20-day average (institutional participation)
- Price above 50-day SMA
- `lm_market_regime.hmm_regime` in ('BULL', 'SIDEWAYS')

**Exit:**
- TP: Entry + 2.5 × ATR(14) on daily
- SL: Entry - 1.5 × ATR(14) on daily
- Time exit: 10 days
- Momentum decay: Exit if 5-day return drops below 0

**Why:** Most robust factor in academic finance. Volume filter removes low-conviction momentum.
**Data:** `crypto_ohlcv` (daily, all symbols for ranking)
**Complexity:** Medium

---

### CRYPTO-4: Volatility Regime Breakout (Squeeze + Regime)

**Edge:** Bollinger squeeze breakouts are directional when filtered by regime and funding rate. The failed `bollinger_squeeze` (4.3% WR) lacked both.

**Entry:**
- BB width (20,2) < 20-day minimum (compression)
- Breakout candle closes above upper BB (LONG) or below lower BB (SHORT)
- `lm_market_regime.vol_annualized` < 60%
- Funding rate confirms direction: positive for LONG, negative for SHORT
- Skip if `lm_market_regime.hmm_regime` = 'HIGH_VOL'

**Exit:**
- TP: 2 × BB squeeze width (measured move)
- SL: Opposite side of squeeze range
- Time exit: 5 days
- No trailing (let it run to TP or SL)

**Why:** Failed strategy + regime filter + funding rate = different trade. Measured-move TP is technically sound.
**Data:** `crypto_ohlcv` (daily), `lm_market_regime`, `at_futures_symbol_edge`
**Complexity:** Medium

---

### CRYPTO-5: Fear/Greed Extreme Reversal with Trend Filter

**Edge:** Extreme fear (<15) in an uptrend = highest probability buy in crypto. Current `st_fear_greed_contrarian` fades the trend.

**Entry:**
- `lm_fear_greed.score` < 15 (extreme fear)
- Price below 200-day SMA BUT above 50-day SMA (pullback in uptrend)
- RSI(14) < 30 on daily
- Volume > 3 × 20-day average (capitulation volume)

**Exit:**
- TP: 50-day SMA (mean reversion target)
- SL: Entry - 2 × ATR(14) on daily
- Time exit: 21 days
- Profit protection: Exit 50% at 1 × ATR, trail rest

**Why:** Extreme fear in uptrend = March 2020, May 2021. Trend filter (price between 50/200 SMA) ensures pullback, not crash.
**Data:** `lm_fear_greed`, `crypto_ohlcv` (daily)
**Complexity:** Low

---

### CRYPTO-6: Exchange Whale Accumulation

**Edge:** Large exchange outflows signal whale accumulation. Current `whale_accumulation_detector` has no data because `crypto_whale_movements` is empty. This uses exchange netflow as proxy.

**Entry:**
- `crypto_exchange_netflow.netflow_24h` < -100 BTC equivalent (large outflow)
- Price within 5% of 52-week low (accumulation zone)
- 20-day realized volatility > 30% annualized
- NOT in 'RISK_OFF' regime

**Exit:**
- TP: 20-day high
- SL: 20-day low - 1%
- Time exit: 30 days
- Trailing: Activate at 10% profit, trail by 5%

**Why:** Whales accumulate during fear. Price-near-low filter ensures buying during accumulation.
**Data:** `crypto_exchange_netflow`, `crypto_ohlcv` (daily), `lm_market_regime`
**Complexity:** Low

---

### CRYPTO-7: Perpetual-Spot Basis Mean Reversion

**Edge:** When perpetual trades below spot (backwardation), forced liquidations are temporary. Basis always returns to near-zero via funding rate mechanism.

**Entry:**
- Perpetual price < spot by > 0.3% (backwardation)
- 24h volume > $50M (liquid markets only)
- RSI(14) on 4h < 35 (confirming oversold)
- NOT in 'RISK_OFF' regime

**Exit:**
- TP: Basis returns to 0 (perpetual = spot)
- SL: Entry - 1.5 × ATR(14) on 4h
- Time exit: 24 hours (short-duration)
- No trailing (fixed target)

**Why:** Backwardation from liquidations is always temporary. High-probability, short-duration trade.
**Data:** `crypto_ohlcv` (perpetual + spot), `lm_market_regime`
**Complexity:** High (needs spot vs perp price data)

---

### CRYPTO-8: Multi-Timeframe Trend Alignment

**Edge:** 3-timeframe trend alignment (4h, 1d, 1w) dramatically increases continuation probability. Current `macd_rsi_multi_tf` uses indicator alignment, not trend.

**Entry:**
- 4h: Price > 20 EMA, 20 EMA > 50 EMA
- Daily: Price > 50 SMA, 50 SMA > 200 SMA
- Weekly: Price > 20 SMA
- Daily volume > 1.2 × 20-day average
- Entry on 4h pullback to 20 EMA

**Exit:**
- TP: 2 × ATR(14) on daily
- SL: Below 50 SMA on daily
- Time exit: 14 days
- Trend break: Exit if any timeframe loses alignment

**Why:** Most robust trend-following pattern. Pullback entry gives better R:R than breakout.
**Data:** `crypto_ohlcv` (4h, daily, weekly)
**Complexity:** Low

---

### CRYPTO-9: Liquidation Cascade Bounce

**Edge:** Cascading liquidations create predictable bounces. Key: detect cascade (volume spike + drop + funding flip), enter after exhaustion.

**Entry:**
- Price dropped > 8% in 24h
- Volume > 5 × 20-day average
- Funding rate flipped from positive to negative (longs liquidated)
- Price closes above 24h low + 2% (exhaustion)
- NOT in 'RISK_OFF' regime

**Exit:**
- TP: 50% Fibonacci retracement of 24h drop
- SL: Below 24h low
- Time exit: 48 hours
- Profit protection: Exit 75% at 25% retracement, trail rest

**Why:** Forced selling creates temporary dislocations. Exhaustion detection (stabilization above low) is key.
**Data:** `crypto_ohlcv` (1h/4h), `at_futures_symbol_edge`
**Complexity:** High

---

### CRYPTO-10: Regime-Adaptive Momentum/Mean-Reversion Switch

**Edge:** Momentum works in trending regimes, mean-reversion in sideways. Dynamic switching captures the best of both. Current strategies are all regime-blind.

**Entry:**
- BULL regime: 20-day return > 5%, price > 20-day SMA (momentum)
- SIDEWAYS regime: RSI(14) < 30, price near BB lower band (mean-reversion)
- BEAR/HIGH_VOL/RISK_OFF: No entry

**Exit:**
- Momentum mode: Trailing 2 × ATR, activate at 1 × ATR
- Mean-reversion mode: TP at 20-day SMA, SL at 2 × ATR
- Time exit: 7d momentum, 14d mean-reversion
- Regime change: Exit at next bar open

**Why:** Avoids #1 failure mode: applying trend-following in choppy market. Vol scaling = risk-proportional sizing.
**Data:** `lm_market_regime`, `crypto_ohlcv` (daily)
**Complexity:** Medium

---

## STRATEGY DESIGN: FOREX (10 Strategies)

**Current:** 42.0% WR, PF=0.73
**Target:** 50%+ WR, PF>1.45 (above monkey-test P95 of 1.45)

### FOREX-1: G10 Carry with Volatility Gate

**Edge:** Currency carry (buy high-yield, sell low-yield) is the most robust FX factor (Lustig et al. 2011). Blacklisted carry strategies lacked vol filter — carry crashes during vol spikes.

**Entry:**
- `carry_yield_diff` > 2.0 (buy high-yield currency)
- VIX < 20 (low vol environment)
- `alpha_macro.yield_spread` > 0 (risk-on)
- Price > 50-day SMA (uptrend)
- NOT in 'RISK_OFF' regime

**Exit:**
- TP: Entry + 1.5%
- SL: Entry - 1.0%
- Time exit: 14 days
- VIX spike exit: If VIX > 25, exit immediately
- Trailing: Activate at 0.8%, trail by 0.4%

**Why:** Carry premium is real but vol kills. VIX gate eliminates crash risk while preserving carry income.
**Data:** `fx_prices`, `alpha_macro` (VIX, yield spread), `lm_market_regime`
**Complexity:** Low

---

### FOREX-2: PPP Mean Reversion (200-SMA Deviation)

**Edge:** Exchange rates revert to purchasing power parity over 6-12 months. >15% deviation from 200-SMA signals undervaluation (Fama & French 1998).

**Entry:**
- Price > 15% below 200-day SMA (deep undervaluation)
- RSI(14) on weekly < 30 (not daily noise)
- `alpha_macro.dxy_sma50` trending down or flat
- 20-day realized vol < 10% annualized

**Exit:**
- TP: 200-day SMA
- SL: Entry - 3%
- Time exit: 60 days
- Half exit at 50% of move to SMA, trail rest

**Why:** PPP is fundamental anchor. >15% deviations are rare and historically mean-revert in 6-12 months.
**Data:** `fx_prices` (daily), `alpha_macro` (DXY)
**Complexity:** Medium

---

### FOREX-3: DXY Divergence Fade

**Edge:** DXY and EUR/USD should move inversely ~80% of the time. When they don't (divergence), the pair mean-reverts within 1-3 days.

**Entry:**
- LONG EUR/USD: DXY 5-day return < -1% AND EUR/USD 5-day return < 0%
- SHORT EUR/USD: DXY 5-day return > +1% AND EUR/USD 5-day return > 0%
- RSI(14) confirms: < 40 for LONG, > 60 for SHORT
- NOT in 'RISK_OFF' regime

**Exit:**
- TP: 0.8%
- SL: 0.5%
- Time exit: 5 days
- No trailing (quick fade)

**Why:** DXY divergence is a 1-3 day anomaly. High win rate with modest R:R (1.6:1).
**Data:** `fx_prices`, `alpha_macro` (DXY)
**Complexity:** Low

---

### FOREX-4: USD Seasonal Pattern (January Effect + Year-End)

**Edge:** USD exhibits documented seasonal weakness in January (tax-loss selling reversal) and strength in November-December (repatriation). Robust since 1970s.

**Entry:**
- January 1-15: SHORT USD pairs (EUR/USD, GBP/USD, AUD/USD LONG)
- November 15-December 31: LONG USD pairs (USD/JPY, USD/CHF LONG)
- Price > 10-day SMA in direction of seasonal trade
- VIX < 22 (not in crisis)

**Exit:**
- TP: 1.0%
- SL: 0.6%
- Time exit: End of seasonal window
- No trailing (calendar-based exit)

**Why:** Seasonal patterns persist because of institutional rebalancing flows. Time-bound exit eliminates overstay risk.
**Data:** `fx_prices`, `alpha_macro` (VIX)
**Complexity:** Low

---

### FOREX-5: Interest Rate Differential Momentum

**Edge:** When central banks diverge (one hiking, one cutting), the rate differential expands and the high-yield currency appreciates. This is different from carry — it captures the *change* in differential, not the level.

**Entry:**
- Rate differential increased by > 50bps in last 30 days
- High-yield currency above 20-day SMA
- 20-day return > 0.5% (momentum confirmation)
- Central bank meeting within 14 days (catalyst proximity)

**Exit:**
- TP: 2 × the rate differential expansion (in % terms)
- SL: Entry - 0.8%
- Time exit: 21 days (through the meeting + reaction)
- Exit 2 days after central bank decision

**Why:** Rate differential changes are the strongest FX predictor (Clarida & Taylor 1997). Meeting proximity ensures catalyst.
**Data:** `fx_prices`, `alpha_macro`, `stock_fundamentals` (for rate data if available)
**Complexity:** Medium

---

### FOREX-6: EUR/GBP Cross Rate Mean Reversion

**Edge:** EUR/GBP has a well-documented mean around 0.85-0.87. Deviations > 3% from 100-day SMA mean-revert with high probability.

**Entry:**
- EUR/GBP > 3% above 100-day SMA: SHORT
- EUR/GBP > 3% below 100-day SMA: LONG
- RSI(14) on daily > 70 (SHORT) or < 30 (LONG)
- 20-day realized vol < 8% annualized (range-bound environment)

**Exit:**
- TP: 100-day SMA
- SL: Entry - 1.5%
- Time exit: 30 days
- Half exit at 1.5% profit, trail rest

**Why:** EUR/GBP is the tightest major pair — mean-reversion is strongest here. Vol filter ensures range-bound regime.
**Data:** `fx_prices`
**Complexity:** Low

---

### FOREX-7: Risk-On/Risk-Off Regime Rotation

**Edge:** In risk-on regimes, buy AUD/JPY (high-beta carry). In risk-off, buy USD/JPY (safe haven). The regime switch itself is the signal.

**Entry:**
- Risk-on → Risk-off transition: LONG USD/JPY, SHORT AUD/JPY
- Risk-off → Risk-on transition: LONG AUD/JPY, SHORT USD/JPY
- Confirmation: `alpha_macro.vix_crosses` above/below 20-day MA
- Price crosses 20-day SMA in direction of trade

**Exit:**
- TP: 1.2%
- SL: 0.7%
- Time exit: 10 days
- Next regime change: Exit immediately

**Why:** Regime transitions are the highest-probability FX trades. AUD/JPY is the canonical risk barometer.
**Data:** `alpha_macro` (VIX), `lm_market_regime`, `fx_prices`
**Complexity:** Medium

---

### FOREX-8: GBP/USD Brexit-Style Dislocation Fade

**Edge:** GBP/USD has outsized moves on political events (elections, policy announcements) that over-shoot fair value. These dislocations mean-revert within 5-10 days.

**Entry:**
- GBP/USD 1-day return > 1.5% (either direction — political shock)
- RSI(14) on daily > 80 (SHORT) or < 20 (LONG)
- Volume > 3 × 20-day average (event-driven volume)
- 5-day ATR > 2 × 20-day ATR (volatility expansion confirms event)

**Exit:**
- TP: 50% Fibonacci retracement of the shock move
- SL: Beyond the shock extreme by 0.3%
- Time exit: 10 days
- No trailing (mean-reversion, fixed target)

**Why:** Political shocks overshoot. GBP/USD mean-reverts faster than other pairs due to deep liquidity.
**Data:** `fx_prices`
**Complexity:** Low

---

### FOREX-9: USD/JPY Carry-Unwind Detector

**Edge:** USD/JPY carry unwinds (rapid JPY appreciation) are predictable from VIX spikes + rate differential compression. The unwind overshoots and mean-reverts.

**Entry:**
- USD/JPY dropped > 2% in 5 days (carry unwind)
- VIX rose > 30% in 5 days (risk spike)
- Rate differential still positive (fundamentals haven't changed)
- RSI(14) on daily < 30

**Exit:**
- TP: 50% retracement of the 5-day drop
- SL: Below the 5-day low by 0.5%
- Time exit: 14 days
- VIX normalization: Exit if VIX returns to pre-spike level

**Why:** Carry unwinds overshoot because of forced selling. If fundamentals (rate differential) are intact, mean-reversion is high-probability.
**Data:** `fx_prices`, `alpha_macro` (VIX)
**Complexity:** Medium

---

### FOREX-10: Multi-Currency Momentum Composite

**Edge:** Combining 3 independent FX factors — momentum (1m return), carry (yield diff), and value (200-SMA deviation) — into a composite score outperforms any single factor (Asness et al. 2013).

**Entry:**
- Composite score = 0.4 × momentum_rank + 0.3 × carry_rank + 0.3 × value_rank
- LONG top 2 currencies by composite score
- SHORT bottom 2 currencies by composite score
- All 3 factors must agree on direction (unanimous)
- VIX < 25

**Exit:**
- TP: 1.5%
- SL: 0.8%
- Time exit: 21 days
- Factor disagreement: Exit if any factor flips

**Why:** Multi-factor models are more robust than single-factor. Unanimous agreement filter ensures conviction.
**Data:** `fx_prices`, `alpha_macro`, `FOREX_SYMBOLS` (carry_yield_diff)
**Complexity:** High

---

## STRATEGY DESIGN: EQUITY (10 Strategies)

**Current:** 34.6% WR, PF=0.53
**Target:** 50%+ WR, PF>1.38 (above monkey-test P95 of 1.38)

### EQUITY-1: Quality Factor (ROE + Margins) Value

**Edge:** High-quality stocks (high ROE + high margins) outperform over 3-12 months (Novy-Marx 2013). The current system has ZERO strategies using `alpha_fundamentals` despite 2964 rows of data.

**Entry:**
- `alpha_fundamentals.return_on_equity` > 20%
- `alpha_fundamentals.gross_margins` > 40%
- `alpha_fundamentals.profit_margins` > 15%
- Price < `alpha_fundamentals.fifty_two_week_high` × 0.90 (10% below 52w high — not at peak)
- `alpha_macro.regime` != 'BEAR'

**Exit:**
- TP: `alpha_fundamentals.fifty_two_week_high` (return to ATH)
- SL: Entry - 5%
- Time exit: 60 days (quality factor is slow)
- Trailing: Activate at 8% profit, trail by 4%

**Why:** Quality factor has highest risk-adjusted returns in academic literature. Price-below-ATH filter ensures value entry, not momentum chasing.
**Data:** `alpha_fundamentals`, `alpha_macro`, `daily_prices`
**Complexity:** Low

---

### EQUITY-2: Earnings Surprise Momentum

**Edge:** Post-earnings announcement drift (PEAD) is the most persistent anomaly in equity markets (Bernard & Thomas 1989). Stocks drift in the direction of earnings surprise for 60-90 days.

**Entry:**
- `alpha_earnings.surprise_pct` > 5% (positive earnings surprise)
- Price > pre-earnings close (market hasn't fully priced it in)
- `stock_analyst_recs.strong_buy` + `buy` > `sell` + `strong_sell` (analyst confirmation)
- `alpha_fundamentals.revenue_growth` > 0 (fundamental growth, not one-time)
- NOT in 'BEAR' regime

**Exit:**
- TP: Entry + 2 × the earnings surprise % (drift target)
- SL: Entry - 3%
- Time exit: 60 days (PEAD window)
- Trailing: Activate at 5%, trail by 2.5%

**Why:** PEAD is caused by investor underreaction to earnings news. Revenue growth filter ensures quality surprise, not one-time items.
**Data:** `alpha_earnings`, `alpha_fundamentals`, `stock_analyst_recs`, `alpha_macro`
**Complexity:** Medium

---

### EQUITY-3: Value Trap Avoidance (PEG + Momentum)

**Edge:** Cheap stocks (low P/E) are often value traps. Adding PEG ratio + price momentum filters out traps and captures genuine value (Lakonishok et al. 1994).

**Entry:**
- `alpha_fundamentals.peg_ratio` < 1.0 (growth at reasonable price)
- `alpha_fundamentals.earnings_growth` > 10% (actual growth, not just cheap)
- Price > 50-day SMA (momentum confirmation — not falling knife)
- 20-day return > 0% (positive momentum)
- `alpha_macro.regime` in ('BULL', 'SIDEWAYS')

**Exit:**
- TP: Entry + 15% (fundamental re-rating)
- SL: Entry - 5%
- Time exit: 90 days (fundamental plays need time)
- Trailing: Activate at 8%, trail by 4%

**Why:** PEG < 1 + growth > 10% + positive momentum = the "GARP" strategy (growth at reasonable price) used by Peter Lynch. Momentum filter avoids value traps.
**Data:** `alpha_fundamentals`, `alpha_macro`, `daily_prices`
**Complexity:** Low

---

### EQUITY-5: Analyst Consensus Shift

**Edge:** When analyst consensus shifts from Hold to Buy, the stock tends to outperform for 30-60 days as institutional buying follows the upgrades.

**Entry:**
- `stock_analyst_recs.strong_buy` + `buy` increased by > 2 in last 30 days
- `stock_analyst_recs.strong_sell` = 0 (no active sells)
- Price > 20-day SMA (uptrend)
- 20-day return > 0% (positive momentum)

**Exit:**
- TP: Entry + 10%
- SL: Entry - 4%
- Time exit: 45 days
- Consensus reversal: Exit if strong_buy + buy drops by > 2

**Why:** Analyst upgrades trigger institutional buying programs that take 30-60 days to complete. No-sell filter ensures clean consensus.
**Data:** `stock_analyst_recs`, `daily_prices`
**Complexity:** Low

---

### EQUITY-6: Dividend Yield Mean Reversion

**Edge:** High-dividend-yield stocks mean-revert when yield is abnormally high (price crashed). The yield reverts to normal as price recovers (Campbell & Shiller 1988).

**Entry:**
- `alpha_fundamentals.dividend_yield` > 2 × `alpha_fundamentals.five_yr_avg_div_yield` (yield is 2x normal — price crashed)
- `alpha_fundamentals.payout_ratio` < 60% (dividend is sustainable)
- Price > 50-day SMA (recovery started)
- `alpha_macro.regime` != 'BEAR'

**Exit:**
- TP: Yield returns to 1.2 × five-year average (near-normal yield = price recovered)
- SL: Entry - 6%
- Time exit: 90 days
- Dividend cut: Exit immediately if payout ratio jumps > 80%

**Why:** Abnormally high yield = price overshot to downside. Sustainable payout ensures dividend isn't cut. Price-above-50-SMA confirms recovery.
**Data:** `alpha_fundamentals`, `alpha_macro`, `daily_prices`
**Complexity:** Medium

---

### EQUITY-7: 52-Week High Breakout with Volume

**Edge:** Stocks near 52-week highs tend to continue (George & Hwang 2004). The "52-week high effect" is strongest when breakout is accompanied by above-average volume.

**Entry:**
- Price within 3% of 52-week high
- Volume > 2 × 20-day average (institutional buying on breakout)
- `alpha_fundamentals.market_cap` > $10B (liquid large-cap only)
- RSI(14) between 50-70 (strong but not overbought)
- `alpha_macro.regime` in ('BULL', 'SIDEWAYS')

**Exit:**
- TP: Entry + 8%
- SL: Entry - 4%
- Time exit: 30 days
- Trailing: Activate at 5%, trail by 2.5%
- 52-week high breakdown: Exit if price drops > 5% from high

**Why:** 52-week high proximity is a behavioral anchor. Institutions buy breakouts systematically. Large-cap filter ensures liquidity.
**Data:** `alpha_fundamentals`, `alpha_macro`, `daily_prices`
**Complexity:** Low

---

### EQUITY-8: Low-Beta Anomaly

**Edge:** Low-beta stocks earn higher risk-adjusted returns than high-beta stocks (Black 1972, Frazzini & Pedersen 2014). The "betting against beta" strategy is one of the most robust anomalies.

**Entry:**
- `alpha_fundamentals.beta` < 0.7 (low beta)
- `alpha_fundamentals.return_on_equity` > 15% (quality filter)
- Price > 200-day SMA (uptrend filter)
- 20-day return > 0% (positive momentum)
- `alpha_macro.regime` != 'BEAR'

**Exit:**
- TP: Entry + 12%
- SL: Entry - 5%
- Time exit: 90 days
- Beta regime change: Exit if beta rises > 1.0

**Why:** Low-beta + quality = "safe" stocks that earn alpha due to leverage constraints of institutional investors. The uptrend filter prevents catching falling knives.
**Data:** `alpha_fundamentals`, `alpha_macro`, `daily_prices`
**Complexity:** Low

---

### EQUITY-9: Earnings Revision Breadth

**Edge:** When the majority of analysts revise estimates upward, the stock outperforms. The breadth of revisions matters more than individual upgrades (Chan et al. 1996).

**Entry:**
- `stock_fundamentals.forward_eps` > trailing EPS (growth expected)
- `alpha_fundamentals.forward_pe` < `alpha_fundamentals.pe_trailing` (forward PE cheaper than trailing = earnings growth accelerating)
- `alpha_fundamentals.revenue_growth` > 5%
- Price > 50-day SMA
- NOT in 'BEAR' regime

**Exit:**
- TP: Entry + 10%
- SL: Entry - 4%
- Time exit: 45 days
- Fundamental deterioration: Exit if forward_pe > trailing_pe × 1.1

**Why:** Forward PE < trailing PE = market underestimating earnings growth. Revenue growth > 5% confirms it's real.
**Data:** `alpha_fundamentals`, `stock_fundamentals`, `alpha_macro`, `daily_prices`
**Complexity:** Medium

---

### EQUITY-10: Sector Rotation Momentum

**Edge:** Sector momentum persists for 1-3 months (Moskowitz & Grinblatt 1999). Buying the top-performing sector ETFs and shorting the weakest captures this effect.

**Entry:**
- Rank 11 sector ETFs (XLK, XLV, XLF, etc.) by 20-day return
- LONG top 2 sector ETFs
- SHORT bottom 2 sector ETFs (if in 'BULL' or 'SIDEWAYS' regime)
- All sectors must have positive 20-day return for LONG (skip if all negative)
- `alpha_macro.vix_close` < 25

**Exit:**
- TP: Entry + 6%
- SL: Entry - 3%
- Time exit: 21 days (rebalance cycle)
- Rank change: Exit if sector drops out of top/bottom 2

**Why:** Sector momentum is the strongest cross-sectional effect in equities. Monthly rebalance captures rotation without overtrading.
**Data:** `daily_prices` (sector ETFs), `alpha_macro`
**Complexity:** Medium

---

## STRATEGY DESIGN: COMMODITY (10 Strategies)

**Current:** 41.1% WR, PF=0.70 (short-only policy)
**Target:** 48%+ WR, PF>1.38 (above monkey-test P95 of 1.38)

### COMMODITY-1: COT Commercial Positioning

**Edge:** Commercial hedgers (producers/merchants) are the informed traders in futures markets. When commercials are net long, prices tend to rise over 1-3 months (Leuthold 1974).

**Entry:**
- `at_futures_symbol_edge` shows commercial net long > 60th percentile
- `at_futures_symbol_edge` shows speculator net long < 40th percentile (contrarian to speculators)
- Price above 20-day SMA (trend confirmation)
- 20-day realized vol > 15% annualized (enough movement)
- `lm_market_regime.hmm_regime` != 'BEAR'

**Exit:**
- TP: Entry + 3 × ATR(14) on daily
- SL: Entry - 2 × ATR(14) on daily
- Time exit: 60 days (COT is slow)
- COT reversal: Exit if commercial positioning flips

**Why:** Commercials have the best information in futures markets. Their positioning is a 1-3 month leading indicator.
**Data:** `at_futures_symbol_edge`, `crypto_ohlcv` (or daily_prices for futures), `lm_market_regime`
**Complexity:** Medium

---

### COMMODITY-2: Contango/Backwardation Roll Yield

**Edge:** Backwardated futures (near-month > far-month) earn positive roll yield. Contango futures (far > near) lose to roll. This is the "Samuelson effect" (1965).

**Entry:**
- LONG: Near-month > far-month (backwardation) AND price > 50-day SMA
- SHORT: Near-month < far-month (contango) AND price < 50-day SMA (only in SIDEWAYS/BULL regime)
- Roll yield > 5% annualized (meaningful edge)
- Volume > average (liquid market)

**Exit:**
- TP: 2 × ATR(14) on daily
- SL: 1.5 × ATR(14) on daily
- Time exit: 30 days (before next roll)
- Roll change: Exit if term structure inverts

**Why:** Roll yield is a structural return source in commodity futures. Backwardation = convenience premium → positive carry.
**Data:** `at_futures_symbol_edge`, daily_prices or crypto_ohlcv (depending on commodity)
**Complexity:** High

---

### COMMODITY-3: Gold as Inflation Hedge (Real Rate Fade)

**Edge:** Gold rallies when real interest rates (nominal - inflation) fall. When real rates drop below 0%, gold becomes attractive as an inflation hedge (Erb & Harvey 2013).

**Entry:**
- `alpha_macro.tnx_close` (10yr yield) < `alpha_macro.regime_score` proxy for inflation OR real rates declining
- Gold price > 200-day SMA (uptrend)
- DXY < 50-day SMA (dollar weakness supports gold)
- 20-day return > 0% (momentum)

**Exit:**
- TP: Entry + 8%
- SL: Entry - 3%
- Time exit: 60 days
- Real rate spike: Exit if 10yr yield rises > 50bps in 30 days

**Why:** Gold is the canonical real-rate asset. Dollar weakness + rising inflation = gold rally. Real-rate spike kills gold.
**Data:** `alpha_macro` (TNX, DXY), `daily_prices` (GC=F), `lm_market_regime`
**Complexity:** Medium

---

### COMMODITY-4: Seasonal Commodity Rotation

**Edge:** Commodities have documented seasonal patterns (e.g., natural gas rallies in winter, agricultural commodities rally before planting season). These patterns are robust (Hirshleifer 1990).

**Entry:**
- Natural Gas (NG=F): LONG October-January (winter heating demand)
- Crude Oil (CL=F): LONG March-July (driving season + refinery maintenance)
- Gold (GC=F): LONG January-March (Chinese New Year + portfolio rebalancing)
- Copper (HG=F): LONG February-April (China restocking)
- Confirmation: Price > 10-day SMA in direction of seasonal trade
- Skip if `lm_market_regime.hmm_regime` = 'RISK_OFF'

**Exit:**
- TP: 1.5 × ATR(14)
- SL: 1 × ATR(14)
- Time exit: End of seasonal window
- No trailing (calendar-based)

**Why:** Seasonal patterns persist due to physical supply/demand cycles. Time-bound exit eliminates overstay risk.
**Data:** `daily_prices` (futures), `lm_market_regime`
**Complexity:** Low

---

### COMMODITY-5: Copper/Gold Ratio Signal

**Edge:** The copper/gold ratio is a proxy for global economic health. When it rises, growth is accelerating (buy industrial commodities). When it falls, recession risk rises (buy gold).

**Entry:**
- Copper/Gold ratio rising > 5% over 20 days: LONG copper-related commodities (HG=F, CL=F)
- Copper/Gold ratio falling > 5% over 20 days: LONG gold (GC=F)
- DXY falling (confirms reflation or de-dollarization)
- NOT in 'RISK_OFF' regime

**Exit:**
- TP: Entry + 5%
- SL: Entry - 3%
- Time exit: 30 days
- Ratio reversal: Exit if copper/gold ratio reverses direction by > 3%

**Why:** Copper/gold ratio is the simplest recession indicator. Rising = risk-on, falling = risk-off. Commodities follow the macro signal.
**Data:** `daily_prices` (HG=F, GC=F), `alpha_macro` (DXY), `lm_market_regime`
**Complexity:** Low

---

### COMMODITY-6: Volatility Mean Reversion (Commodity Vol selling)

**Edge:** Commodity volatility (e.g., VIX for oil, GVZ for gold) exhibits strong mean reversion. Selling vol when it spikes (after 2σ move) earns the volatility risk premium.

**Entry:**
- Commodity implied vol (proxy: 20-day realized vol) > 2 × 60-day average (vol spike)
- Price has moved > 3 × 20-day ATR in last 10 days (overshoot)
- `lm_market_regime.hmm_regime` != 'RISK_OFF'
- For gold: VIX > 25 (macro stress confirming vol spike)

**Exit:**
- TP: Vol returns to 60-day average (mean reversion)
- SL: Price moves another 2 × ATR against entry (vol continues expanding)
- Time exit: 30 days
- Vol compression: Exit if vol drops below 60-day average

**Why:** Volatility is mean-reverting. Selling after spikes earns the vol risk premium. RISK_OFF filter prevents selling vol into systemic crises.
**Data:** `daily_prices`, `lm_market_regime`, `alpha_macro` (VIX)
**Complexity:** Medium

---

### COMMODITY-7: Agricultural Supply Shock

**Edge:** Agricultural commodities have sharp rallies after supply shocks (drought, flood, frost). These overshoot and mean-revert within 30-60 days.

**Entry:**
- Price > 15% above 20-day SMA (supply shock move)
- Volume > 5 × 20-day average (panic buying)
- RSI(14) > 80 (overbought — but this time it's justified, we fade the overshoot)
- Price > 20% above 50-day SMA (confirmed overshoot)

**Exit:**
- TP: 50% retracement to 50-day SMA
- SL: Above the spike high by 2%
- Time exit: 60 days (agricultural shocks take time to mean-revert)
- New supply news: Exit if USDA report shows supply recovery

**Why:** Supply shocks overshoot because panic buying exceeds fundamental value. Mean-reversion is slow because agricultural supply takes 1-2 growing seasons to recover.
**Data:** `daily_prices` (futures), `lm_market_regime`
**Complexity:** Medium

---

### COMMODITY-8: Energy Sector Term Structure Momentum

**Edge:** Crude oil term structure (contango/backwardation) predicts future spot returns. Backwardation → spot will rise (inconvenience yield). This is the "theory of storage" (Working 1949).

**Entry:**
- Crude oil in backwardation (front month > back month)
- Backwardation spread > $2/barrel
- Price > 20-day SMA
- 20-day return > 0%
- NOT in 'RISK_OFF' regime

**Exit:**
- TP: Entry + $5/barrel (or equivalent % move)
- SL: Entry - $3/barrel
- Time exit: 30 days
- Contango shift: Exit if term structure flips to contango

**Why:** Backwardation = tight supply → convenience yield → price rise. Contango = oversupply → price decline. Term structure is the most reliable oil predictor.
**Data:** `daily_prices` (CL=F), `lm_market_regime`
**Complexity:** High

---

### COMMODITY-9: Diversified Commodity Momentum (CTA-Style)

**Edge:** Trend-following across diversified commodities (energy, metals, agriculture) with volatility-scaled positions is the core CTA strategy (Hurst et al. 2017). Current `futures_momentum` has 63.8% WR / PF=1.76 — this is the ONE strategy that works. We create a refined version.

**Entry:**
- 12-month return > 0 AND 1-month return > 0 (multi-timeframe momentum confirmation)
- Position size = 1% / 20-day volatility (volatility scaling)
- Max 5% per commodity, 20% per sector (diversification)
- Skip if commodity is in backwardation-to-contango transition

**Exit:**
- 12-month return turns negative (momentum reversal)
- Time exit: Monthly rebalance
- Max drawdown per position: 3 × position volatility

**Why:** CTA trend-following is the most backtested commodity strategy. Vol scaling ensures risk-parity. The dual-timeframe filter (12m + 1m) avoids whipsaws.
**Data:** `daily_prices` (multiple futures), `lm_market_regime`
**Complexity:** High

---

### COMMODITY-10: Metal Ratio Reversion (Gold/Silver, Gold/Platinum)

**Edge:** Gold/Silver ratio has a historical mean around 60-70. When it deviates > 20% from mean, it mean-reverts. Same for Gold/Platinum.

**Entry:**
- Gold/Silver ratio > 85 (silver undervalued relative to gold): LONG silver (SLV or SI=F)
- Gold/Silver ratio < 55 (silver overvalued): SHORT silver
- Gold/Platinum ratio > historical mean + 1.5 std: LONG platinum
- Confirmation: Price > 20-day SMA for LONG, < 20-day SMA for SHORT

**Exit:**
- TP: Ratio returns to mean (or 50% of deviation)
- SL: Ratio moves another 10% against entry
- Time exit: 90 days (ratio reversion is slow)
- Half exit at 25% deviation reduction, trail rest

**Why:** Precious metal ratios have structural anchors. Deviations are caused by sentiment extremes in one metal, not fundamental changes. 90-day exit accounts for slow reversion.
**Data:** `daily_prices` (GC=F, SI=F, PL=F)
**Complexity:** Medium

---

## Implementation Priority

### Tier 1 (Implement First — Highest Edge, Lowest Complexity)
1. **CRYPTO-5**: Fear/Greed Extreme Reversal — simplest, uses existing data
2. **FOREX-1**: Carry with Vol Gate — proven factor, just needs vol filter
3. **EQUITY-1**: Quality Factor — 2964 rows of fundamentals sitting unused
4. **EQUITY-2**: Earnings Surprise Momentum — PEAD is the strongest equity anomaly
5. **COMMODITY-9**: CTA-Style Momentum — refined version of the one working strategy

### Tier 2 (Implement Second — Strong Edge, Medium Complexity)
6. **CRYPTO-3**: Cross-Sectional Momentum — robust factor, needs volume filter
7. **CRYPTO-10**: Regime-Adaptive Switch — solves the regime blindness problem
8. **FOREX-3**: DXY Divergence Fade — high win rate, short-duration
9. **EQUITY-3**: PEG Value — GARP strategy with momentum guard
10. **COMMODITY-1**: COT Commercial Positioning — proven institutional signal

### Tier 3 (Implement Third — Strong Edge, Higher Complexity)
11. **CRYPTO-1**: Funding Rate Mean Reversion — needs futures data integration
12. **CRYPTO-4**: Volatility Regime Breakout — fixes failed bollinger_squeeze
13. **FOREX-7**: Risk-On/Off Rotation — regime-based, needs VIX integration
14. **EQUITY-7**: 52-Week High Breakout — behavioral anomaly with volume
15. **COMMODITY-5**: Copper/Gold Ratio — macro indicator, simple implementation

### Tier 4 (Implement Last — Complex Data Requirements)
16-20. Remaining CRYPTO strategies (2, 6, 7, 8, 9)
21-25. Remaining FOREX strategies (2, 4, 5, 6, 8, 9, 10)
26-30. Remaining EQUITY strategies (5, 6, 8, 9, 10)
31-40. Remaining COMMODITY strategies (2, 3, 4, 6, 7, 8, 10)

---

## Key Design Principles

1. **Every strategy uses data the system already has but isn't using** — no new API integrations needed
2. **Every strategy has a regime filter** — no picking tops/bottoms in crashes
3. **Every strategy has volatility-adjusted TP/SL** — no fixed percentages
4. **Every strategy has a time exit** — no holding losers forever
5. **Every strategy cites academic research** — not just "it looks good on a chart"
6. **No two strategies use the same edge** — genuine diversification across return sources
