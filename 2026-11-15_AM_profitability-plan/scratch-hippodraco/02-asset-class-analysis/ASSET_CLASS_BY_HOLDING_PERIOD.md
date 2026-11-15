# Asset-Class Analysis by Holding Period × Trading Style
**Date:** 2026-11-15  
**Purpose:** For each asset class, assess which trading style (long-term, short-term, swing, day trading, scalping) has the highest probability of profitability, and list proven/famous algorithms that have won TradingView or other contests (e.g., Hoffman).  
**Core caution:** Contest wins and backtest WRs are not live edges. The profitable-approach audit found only ONE pre-specified procedure (Variant C) surviving honest multiple-testing across V0–V6. Treat all contest/backtest claims as hypotheses until they clear clean OOS + cost gates.

---

## Trading-style definitions (used throughout)

| Style | Typical holding period | Primary edge source | Key risk |
|-------|----------------------|---------------------|----------|
| **Long-term / buy-and-hold** | Months to years | Equity risk premium, dividend income, beta capture | Drawdown duration, concentration |
| **Short-term** | Days to weeks | Mean reversion, momentum, event-driven | Overnight gap, news risk |
| **Swing** | Several days to weeks | Trend continuation, pullback entries, S/R | Whipsaws in choppy regimes |
| **Day trading** | Intraday (minutes to hours, flat by close) | Intraday momentum, order flow, VWAP, opening range | Spreads, commissions, overtrading, pattern day-trader rules |
| **Scalping** | Seconds to minutes | Micro-structure, liquidity rebates, tiny edges repeated | Transaction costs dominate; needs extreme win rate or volume |

---

## Per-asset-class: best-fit style + proven algorithms

### CRYPTO
**Best-fit styles:** Short-term, swing, scalping (24/7 market, high volatility, funding-rate structure).  
**Poor fit:** Long-term buy-and-hold (single-asset crypto has no dividend/cash-flow beta; extreme drawdowns).

**Proven / famous algorithms & contest references:**
- **Connors RSI-2 (crypto)** — 62.5% WR, p=0.009, Sharpe 2.35 (Alpha Engine Core Crypto). Mean-reversion pullback; proven statistical edge in backtest.
- **Hash Ribbon Buy** — 78% WR (Charles Edwards, 2019). Bitcoin on-chain accumulation signal.
- **Funding Rate Extreme / Carry** — 71% WR (Kraken Research). Captures funding-rate mean reversion and carry.
- **Wyckoff Accumulation** — 60–70% WR (Wyckoff, 1931). Smart-money accumulation detection.
- **ML-enhanced LightGBM sleeves** — e.g., `ml_enhanced_INJUSDT_1d_B_lightgbm` (100% WR, n=27, DSR≥0.9995) and `ml_enhanced_FETUSDT_1d_B_lightgbm` (100% WR, n=25). **Small-n; intrabar replay needed.**
- **Coinglass DNA Bundle** — extreme reversion, whale divergence, ratio momentum, exchange spread, leverage squeeze, funding confluence, sentiment composite, spike detector. Multi-source on-chain/derivatives.

**Reality check:** Crypto intrabar replay drops WR 52.3%→42.9% (26.4% of TP_HITs hit SL first). All crypto edges here are small-n and unproven live. **Probability: low.**

---

### EQUITY (US)
**Best-fit styles:** Swing and short-term (pullback entries, mean reversion, opening-range breakout). Long-term buy-and-hold of quality names is valid but is a *separate allocation*, not this system's proven edge.  
**Poor fit:** Scalping (US equity commissions/spreads + PDT rules make micro-edges hard).

**Proven / famous algorithms & contest references:**
- **Connors RSI-2** — 75.7% WR, p=6×10⁻⁶, Sharpe 4.84 (SPY/QQQ). **The system's only proven equity sleeve.** Classic short-term mean-reversion pullback (Connors & Raschke).
- **VIX Spike Reversal Scanner** — 72% WR (SPX). Volatility-spike mean reversion.
- **stocks_rsi2_pullback** — 80.0% WR on blue-chip trends (JNJ, XOM). Institutional-grade but needs larger n.
- **World Class v2.1 night alpha** — 72% WR (seasonality / mean reversion, institutional pilot).
- **World Class v2.1 regime mom** — 81% WR (regime / momentum, institutional pilot).
- **World Class v2.1 sector_rel** — 77% WR (relative strength / sector).
- **Hoffman EMA / IRB** — `hoffman_ema_irb` (Hoffman EMA inventory retracement bar) and `hoffman_irb_reversal` (Hoffman IRB reversal bars). Referenced in proven-research strategies; Hoffman is a known contest/prop-firm name (IRB = Inventory Retracement Bar).
- **Multi-timeframe EMA stack** — 65–72% WR (Pentoshi/DonAlt style).

**Reality check:** Equity is the only class with a pre-registered SPY benchmark test path and some positive cost-margin signals. Best candidate for P2 benchmark test. **Probability: moderate.**

---

### ETF
**Best-fit styles:** Swing and short-term (sector rotation, dual momentum, mean reversion on tight bands). Long-term buy-and-hold of broad ETFs (SPY, VTI) is valid allocation but separate from prediction edge.  
**Poor fit:** Scalping (expense ratio + spread erodes micro-edges).

**Proven / famous algorithms:**
- **ETF mean reversion (600-variant bundle, variants 501–600)** — mean reversion on tight volatility bands, target WR 70%.
- **ETF dual momentum / sector rotation** — multiple `test_etf_*` gates exist (`test_etf_dual_momentum_backtest`, `test_etf_sector_rotation_backtest`, `test_etf_relative_strength_gate`).
- **ETF economic momentum** — existing backtest (`test_etf_economic_backtest.py`).
- **FreshPicks DNA** — funding rate carry, 95% WR claimed, +1.61% expectancy (multi-asset; unverified live).

**Reality check:** ETF has the cleanest OOS profile in the profitable approach (WF consistency 100%, OOS WR 75%, decay +23%) but n is at floor (88–100). Expand universe (XLF/XLE/XLK). **Probability: moderate, not yet proven.**

---

### FOREX
**Best-fit styles:** Short-term, swing (session momentum — London/NY; carry trade).  
**Poor fit:** Scalping (spread ~1-2 pips = ~4bp/side destroys micro-edges; retail cost model underestimated); long-term (no carry-beta certainty).

**Proven / famous algorithms:**
- **Carry Trade Momentum** — carry + momentum (major pairs).
- **Forex TSMOM 12m** — 12-month time-series momentum (Moskowitz-style).
- **Forex RSI-2 Mean Reversion** — classic short-term MR.
- **London Session Breakout** — 62% WR (KIMI RoTC proven crypto/forex).
- **IG Contrarian Sentiment** — SHORT-axis 57% WR vs LONG 21% (36pp spread) but NO strategy passes DSR≥0.5.

**Reality check:** True clean 14d FOREX WR ~5%, PF 0.077. Catastrophic. **Probability: very low. Do not unblock while drift_alert TRUE.**

---

### COMMODITY / FUTURES
**Best-fit styles:** Swing and short-term (CTA trend, COT positioning, seasonal). Futures scalping possible but commission/tick structure demands care.  
**Poor fit:** Long-term buy-and-hold (commodities have no cash-flow beta; contango/roll drag).

**Proven / famous algorithms:**
- **COT Positioning family** — DSR=1.0000, WR 86.5%, Sharpe +1.377, n=104; `cot_positioning_CT_locked` LONG WR 89.8%, PF 13.1, n=49 (Antigravity verified). **Small-n; verify concentration (multi_asset_cot PF 21.33 likely one-symbol CT=F artifact).**
- **CFTC COT Commercial Signal** — WR 79.3%, n=58.
- **Volatility Squeeze (Commodities)** — 600-variant bundle variants 301–400: Bollinger Band Squeeze + Volume Spike, target WR 58%.
- **Futures Gap Continuation** — variants 401–500: overnight gap fill + momentum, target WR 62%.

**Reality check:** COMMODITY generator maps crypto proxies (RNDR→silver, XLM→oil) — no real feed. FUTURES dead. Blind unblock vetoed. **Probability: low until real feed + mapping fixed.**

---

### BOND
**Best-fit styles:** Long-term / short-term (yield-curve regimes, carry). Not suited to day trading/scalping (illiquid, wide spreads, T+1).  
**Poor fit:** Scalping, day trading.

**Proven / famous algorithms:** Bond strategies exist (`bond_strategies.py`) but n=1–18, thin. FRED unblock needed. No proven contest-winning bond sleeve in this system yet.

**Reality check:** n far below floor. **Probability: low until n accumulates.**

---

### MUTUAL FUNDS
**Best-fit style:** Long-term only (NAV struck once daily after close; orders fill at next NAV; 30-day frequent-trading limits).  
**Poor fit:** Everything else (intraday TP/SL meaningless; scalping/day trading impossible).

**Proven algorithms:** None in this system. MF is not a predicted class (class id −1). No scanner, no NAV data source, no dashboard tile.

**Reality check:** Do not build MF prediction picks. Hold low-cost index MFs as allocation instead. **Probability: near 0% as a prediction edge.**

---

### PENNY / MEMECOIN
**Best-fit style:** None proven.  
**Reality check:** MEMECOIN PF 0.50 over 1,869 trades (class-wide quarantined); PENNY BLOCKED by Gate 0. **Probability: very low.**

---

## Summary table: best-fit style × probability

| Asset Class | Best-fit styles | Probability of profitability (system edge) | Primary blocker |
|-------------|----------------|--------------------------------------------|-----------------|
| EQUITY | Swing, short-term | Moderate | n, clean OOS, SPY benchmark |
| ETF | Swing, short-term | Moderate (not yet proven) | n at floor (~88–100) |
| CRYPTO | Short-term, swing, scalping | Low | OHLCV backfill, intrabar truth, toxic sources |
| COMMODITY / FUTURES | Swing | Low | No real feed, crypto-proxy mapping, n too small |
| BOND | Long-term, short-term | Low | n=18, FRED unblock |
| FOREX | Short-term | Very Low | Clean PF 0.077, drift_alert TRUE |
| MUTUAL FUNDS | Long-term only | Near 0% | No infrastructure, not a class |
| PENNY / MEME | None | Very Low | Blocked, quarantined |

---

## Top "proven/famous" algorithms referenced (with caveats)

| Algorithm | Source / context | Claimed WR / metric | Caveat |
|-----------|-----------------|---------------------|--------|
| Connors RSI-2 | Alpha Engine (equity SPY/QQQ; crypto) | 75.7% / 62.5%, Sharpe 4.84 / 2.35 | Backtest; needs live OOS |
| Hoffman EMA / IRB | Proven-research strategies; Hoffman (contest/prop name) | Referenced, no live n | Small-sample / backtest |
| Hash Ribbon Buy | Charles Edwards (2019), crypto on-chain | 78% WR | BTC-specific, small-n |
| Funding Rate Carry | Kraken Research | 71% WR | Funding-structure dependent |
| London Session Breakout | KIMI RoTC proven | 62% WR | FX-specific |
| COT Positioning | Antigravity verified | 89.8% WR, PF 13.1, n=49 | **Likely concentration artifact** (multi_asset_cot PF 21.33 on CT=F) |
| FreshPicks DNA | Multi-asset | 95% WR, +1.61% expectancy | Unverified live |
| World Class v2.1 suite | Institutional pilot (rescued) | 72–81% WR | Pilot data; not live-validated |

**Ground rule:** A contest win or backtest WR is a hypothesis, not an edge. Only Variant C (equity/ETF walk-forward) survived honest multiple-testing (p<0.005, Bonferroni) in this system's own audit.

---
