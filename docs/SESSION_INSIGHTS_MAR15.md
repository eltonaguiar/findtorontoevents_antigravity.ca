# Session Insights — March 15, 2026

## Current Portfolio State
- **108 active picks** (73 crypto, 19 forex, 16 equity)
- **59.1% quality** | 39W / 25L / 2F | Avg P&L: +0.31%
- **Market Regime: RELIEF RALLY** (F&G=23 Extreme Fear + short-term +3.2% bounce)

---

## Market Regime Analysis

The audit dashboard was showing **"BULLISH"** — this was wrong. The actual state:

| Factor | Value | Interpretation |
|--------|-------|---------------|
| Fear & Greed | 23 | Extreme Fear (34+ days) |
| BTC vs 50d SMA | +2.1% | Neutral (not confirmed uptrend) |
| 24h Top 10 Change | +3.2% | Strong short-term bounce |
| All 10 cryptos green | 10/0 | Relief rally, not trend |

**Correct regime: RELIEF RALLY** — A bounce inside extreme fear. Fragile, not confirmed bullish. This matters because:
- LONGs are performing (+3.2% avg) but it could reverse
- SHORTs are getting crushed (all worst 5 performers are shorts)
- KIMI's all-BUY signals are temporarily working (66.7% WR) but historically 8% WR

**Fix deployed:** Audit page now uses multi-factor regime detection (F&G + BTC trend + PnL). New regimes: RELIEF RALLY, EXTREME FEAR, EUPHORIA, CAUTIOUS, GREED FADING.

---

## Strategy Performance (What's Working vs Not)

### Winners (100% WR)
| Strategy | Source | Avg PnL | Why It Works |
|----------|--------|---------|-------------|
| bollinger-squeeze | KIMI | +3.71% | Volatility compression breakout in relief rally |
| crypto-momentum-scout | KIMI | +3.49% | RSI oversold catches bounce perfectly |
| entropy_regime_breakout | Alpha | +1.08% | Regime-change detection |

### Losers (0% WR) — Inverse Candidates
| Strategy | Source | Avg PnL | Problem |
|----------|--------|---------|---------|
| ctrend_multi_horizon | Alpha | -2.86% | Cross-sectional momentum shorts wrong in bounce |
| cumulative_rsi_signal | Alpha | -2.83% | RSI overbought shorts punished by rally |

### KIMI System — Inverse Edge
- **Historical:** 8% WR on 339 closed trades = -112% cumulative PnL
- **Inverse analysis:** 97.2% inverse WR, Sharpe 23.6, walk-forward validated
- **Current batch:** 66.7% WR (relief rally helping BUYs) — inverse would lose short-term
- **Conclusion:** KIMI inverse is a long-term statistical edge, not a short-term signal

---

## New Tools Built This Session

### 1. KIMI Inverse Scanner (`alpha_engine/kimi_inverse_scanner.py`)
- Reads KIMI active picks, flips direction (BUY->SELL, SELL->BUY)
- Multi-factor regime detection (F&G + BTC 50d SMA + 24h changes)
- Won't short in confirmed bull; inverts everything in relief rally / extreme fear
- 28 inverse picks now tracking

### 2. Mutation Forward Scanner (`alpha_engine/mutation_forward_scanner.py`)
- Scans 9 genome survivors from 400K mutation evaluations
- Implements Keltner compression-expansion with each genome's specific parameters
- **Current picks:** SOL LONG (4-genome consensus), DOGE LONG (2-genome consensus)
- Consensus = multiple independent genomes agreeing = higher confidence

### 3. Vectorized Backtest Engine (`alpha_engine/vectorized_backtest.py`)
- 2.4ms per backtest (67x faster than event-driven)
- 1M mutations in ~42 minutes
- Multi-fidelity screen: 200 -> 500 -> 2000 candle funnel
- Deflated Sharpe ratio for multiple testing correction

---

## Quick Wins Implemented (from Gemini Research)

| Change | File | Impact |
|--------|------|--------|
| OBI live mode | config.py | +30% alpha from orderbook data (was in shadow) |
| Keltner UTC filter | keltner_evolved.py | BTC/ETH only fire 05:00-13:00 UTC (>80% WR) |
| Quant strategies imported | scanner.py | Pairs trading now reachable from scanner |
| Untapped strategies imported | scanner.py | Google Trends contrarian now reachable |
| Scanner v1.5 | scanner.py | Added QUANT + UNTAPPED to strategy count |

---

## 10 Crypto Techniques Audit (Gemini Research)

| # | Technique | Status | Notes |
|---|-----------|--------|-------|
| 1 | Funding Rate Arbitrage | READY | Market-neutral, all regimes, 19-30% APR |
| 2 | Orderbook Imbalance (OBI) | READY | Flipped to LIVE this session |
| 3 | Liquidation Cascade | READY | Price action + volume based |
| 4 | CVD Divergence | READY | In statistical_strategies + ML feature |
| 5 | TVL Momentum (DefiLlama) | PARTIAL | API helpers exist, no strategy wrapper |
| 6 | Keltner Squeeze | READY | UTC 05:00-13:00 time gate added |
| 7 | Cross-Sectional Momentum | READY | Top-3 by 7d return |
| 8 | XGBoost ML Ensemble | READY | 33 features, auto-trains at 50+ picks |
| 9 | Copula Pairs Trading | FIXED | Was not imported into scanner — now is |
| 10 | Google Trends Contrarian | FIXED | Was not imported into scanner — now is |

**Gemini also added (during this session):**
- VPIN (Volume-Synchronized Probability of Informed Trading) — new strategy + ML feature
- LunarCrush Galaxy Score — social sentiment using new `LUNARCRUSH_API` key
- Strategy Regime Mapping — every strategy tagged with optimal regime
- ML ranker expanded to 33 features (added VPIN + Galaxy Score)

---

## Key Insight from Gemini Research

> **Market-neutral > Directional.** With 43% directional win rate in the AI tournament,
> market-neutral strategies (funding arb, pairs trading, calendar spreads) should get
> priority capital. They don't need direction prediction.

> **Simple models + good features > complex ML.** XGBoost with 33 engineered features
> matches or beats deep learning. The bottleneck is feature quality and regime awareness,
> not model complexity.

> **Time-of-day is a top-5 feature.** Keltner BTC >80% WR during UTC 05:00-13:00.
> Funding settlements at 00/08/16 UTC create exploitable windows.

> **Tight TP / wide SL wins in this regime.** TP=0.5x ATR, SL=2.1x ATR (micro-scalp).
> Our mutation survivor MM-69727 independently found TP=0.5x, SL=2.5x with 93% WR.

---

## Next Priorities

1. **TVL Momentum wrapper** — create strategy function wrapping DefiLlama signals
2. **Saturday overnight mutation run** — 1M+ genomes through vectorized funnel
3. **COT positioning for forex** — 0/8 forex wins, biggest gap
4. **Monitor relief rally** — if F&G stays <25 and BTC reverses, inverse picks activate
5. **Timeframe field on picks** — enhancement added, all picks should include timeframe
