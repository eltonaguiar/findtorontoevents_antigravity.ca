# ANTIGRAVITY ALPHA SYSTEM — METHODOLOGY & AUDIT TRAIL
## Generated: February 17, 2026 7:45 PM EST
## Author: Antigravity AI (Gemini-based agent)

---

## TABLE OF CONTENTS
1. [Executive Summary](#executive-summary)
2. [Data Sources & Costs](#data-sources)
3. [Strategy Methodologies](#strategies)
4. [Validation Framework](#validation)
5. [Live Proof Results — Feb 17 2026](#live-proof)
6. [Honest Assessment & Failures](#honest-assessment)
7. [Audit Trail — Complete File List](#audit-trail)

---

## 1. EXECUTIVE SUMMARY <a name="executive-summary"></a>

Three independent research engines were built and backtested:
- **Alpha Research Engine v3**: 71 academic/institutional strategies tested
- **Renaissance Killer Ensemble**: 13 signals × 19 assets with regime detection
- **Alternative Data Engine**: Fear & Greed, Funding Rates, BTC Dominance

**Total strategies tested:** 117
**Proven winners (all checks passed):** 24
**Data cost:** $0 (all free public APIs)
**Best Sharpe ratio:** 4.99 (BTC-ETH Pairs Trade)

**CRITICAL CAVEAT:** These are BACKTEST results. The live proof (Section 5) shows
strategies that looked great in backtests FAILED in the recent market crash
(Jan 29 – Feb 7, 2026). This is documented honestly below.

---

## 2. DATA SOURCES & COSTS <a name="data-sources"></a>

| Source | API | Cost | Data Type | Period |
|--------|-----|------|-----------|--------|
| yfinance | `yf.download()` | FREE | OHLCV daily | 5 years |
| alternative.me | REST API (no key) | FREE | Fear & Greed Index | ~2000+ days |
| Binance fapi | REST API (no key) | FREE | Funding rates (8h) | ~333 days |
| CoinGecko | N/A (proxy via yfinance) | FREE | BTC dominance proxy | 5 years |

**No Bloomberg terminal. No paid APIs. No proprietary data.**
All data is publicly available and reproducible by anyone.

---

## 3. STRATEGY METHODOLOGIES <a name="strategies"></a>

### 3.1 Connors RSI(2) Mean Reversion
- **Academic source:** Larry Connors, "Short Term Trading Strategies That Work" (2004)
- **Logic:** RSI with 2-period lookback identifies extreme oversold conditions
- **Entry:** RSI(2) < 10 (extreme oversold)
- **Exit:** RSI(2) > 65 or 5-day max hold
- **Why it works:** Short-term price reversals are well-documented in academic literature
- **5-year backtest:** 81.7% WR on SPY, 70.1% on BTC, p<0.005
- **Live 90-day proof:** 77.3% WR on SPY (17/22 wins, +11.69%), 70% on QQQ (14/20)
- **Live 90-day FAILURE:** 50% WR on BTC (-55.46%), 50% on SOL (-67.44%)
- **Conclusion:** Works on equities, FAILS on crypto during crash

### 3.2 BTC-ETH Pairs Trade (Statistical Arbitrage)
- **Academic source:** Gatev, Goetzmann & Rouwenhorst (2006), "Pairs Trading"
- **Logic:** BTC and ETH are cointegrated; when spread deviates >2 std devs, mean reverts
- **Entry:** Z-score of price ratio > 2 or < -2
- **Exit:** Z-score crosses 0 (mean reversion)
- **Why it works:** Cointegrated assets maintain long-run equilibrium
- **5-year backtest:** Sharpe 4.99, +396.7% total P&L, 57.7% WR
- **Limitation:** Requires both assets; doesn't work in structural breaks

### 3.3 Fear & Greed Contrarian
- **Source:** alternative.me/crypto/fear-and-greed-index/
- **Logic:** "Be fearful when others are greedy" (Buffett)
- **Entry:** Index < 20 (Extreme Fear) → buy BTC
- **Exit:** Hold 14 or 30 days
- **Why it works:** Behavioral finance — crowd panic creates buying opportunities
- **5-year backtest:** Sharpe 4.05, 59.3% WR, +1592% total P&L
- **Live 90-day proof:** 54.9% WR, BUT total P&L = -114.50%
- **Key insight:** The Jan-Feb 2026 crash destroyed recent performance.
  Strategy bought at $89K and held through crash to $62K. Massive drawdowns.
- **CURRENT SIGNAL (Feb 17):** F&G = 8 (Extreme Fear) → BUY signal is ACTIVE

### 3.4 BTC Dominance Rotation
- **Logic:** When BTC dominance rises, hold BTC; when falling, rotate to alts
- **Proxy:** BTC normalized price / altcoin basket normalized price
- **Entry:** 20-day change in BTC strength ratio >5% or <-5%
- **Hold period:** 14 days
- **5-year backtest:** +1804% combined, 1085 trades, Sharpe 1.62
- **Live 90-day proof:** 2/4 wins (50%), total P&L = -27.93%
- **Note:** Large backtest PnL inflated by crypto's overall uptrend 2020-2025

### 3.5 Binance Funding Rate Fade
- **Logic:** Negative funding = shorts paying longs = market oversold
- **Source:** Binance futures API (free, public)
- **Entry:** Average daily funding rate < -0.01%
- **Exit:** Next day
- **Limitation:** Very few extreme signals; insufficient sample size for proof
- **CURRENT SIGNAL (Feb 17):** SOL funding = -0.0107% → BUY signal on SOL

### 3.6 End-of-Month Effect
- **Academic source:** Ariel (1987), "A Monthly Effect in Stock Returns"
- **Logic:** Stocks and crypto tend to rise in last 3 days + first 2 days of month
- **Live 6-month proof:**
  - BTC: 3/6 wins (50%), total = -2.51%
  - SOL: 2/6 wins (33%), total = -2.84%
  - ETH: 2/6 wins (33%), total = -10.76%
- **Assessment:** NOT confirmed in recent crypto data

### 3.7 Multi-Factor Renaissance Ensemble
- **Technique:** 13 signals across 5 categories:
  - Mean reversion: RSI(2), RSI(3), Bollinger Band Z-score
  - Momentum: 12m-1m, 1-month, Rate of Change, Price vs SMA200
  - Volatility: Vol compression ratio, Realized vol trend
  - Structural: End-of-month, Day-of-week
  - Cross-asset: Relative strength vs BTC, Correlation breakdown
- **Regime detection:** 4-state (Bull Trend, Bear Trend, High Vol, Mean Revert)
- **Signal weighting:** Information Coefficient × regime weight
- **Position sizing:** Half-Kelly criterion
- **Backtesting:** Walk-forward (252d train / 63d test, sliding)
- **Validation:** 8-check system (sample size, WR, p-value, Sharpe, PF, max DD, expectancy, Calmar)
- **Results:** 2/19 passed as Proven Winners (MATIC-USD, IWM)
- **Signal decay monitoring:** IC slope regression to detect dying signals

---

## 4. VALIDATION FRAMEWORK <a name="validation"></a>

### 8-Check Institutional Validation System

| # | Check | Threshold | Rationale |
|---|-------|-----------|-----------|
| 1 | Sample Size | ≥ 20 trades | Minimum for statistical meaning |
| 2 | Win Rate | ≥ 45% | Above random chance |
| 3 | P-value (one-sided t-test) | ≤ 0.05 | 95% confidence mean return > 0 |
| 4 | Sharpe Ratio | ≥ 1.0 | Risk-adjusted return threshold |
| 5 | Profit Factor | ≥ 1.3 | Gross profit / gross loss |
| 6 | Max Drawdown | ≤ 20% | Capital preservation |
| 7 | Expectancy | ≥ 0.1 | Expected value per trade |
| 8 | Calmar Ratio | ≥ 1.0 | Annual return / max drawdown |

### Tier Classification
- **🏆 INSTITUTIONAL GRADE:** 7+ checks passed
- **✅ PROVEN WINNER:** 6 checks passed
- **✅ STRONG:** 5 checks passed
- **⚠️ PROMISING:** 4 checks passed
- **❌ NOT PROVEN:** <4 checks passed

---

## 5. LIVE PROOF RESULTS — February 17, 2026 <a name="live-proof"></a>

### Current Live Signals (7:45 PM EST)
| Signal | Value | Action |
|--------|-------|--------|
| Fear & Greed Index | **8** (Extreme Fear) | **BUY** |
| RSI(2) BTC-USD | **4.1** | **STRONG BUY** |
| RSI(2) ETH-USD | **90.7** | **SELL** |
| RSI(2) SPY | 50.0 | NEUTRAL |
| BTC Dominance | +11.6% rising | **LONG BTC** |
| Funding Rate SOL | -0.0107% | **BUY SOL** |
| End of Month | 11 days left | WAIT |

### 90-Day Out-of-Sample Results (HONEST)

| Strategy | Asset | Trades | WR | Total P&L | Status |
|----------|-------|--------|-----|-----------|--------|
| RSI(2) | SPY | 22 | **77.3%** | **+11.69%** | ✅ CONFIRMED |
| RSI(2) | QQQ | 20 | **70.0%** | **+11.56%** | ✅ CONFIRMED |
| RSI(2) | ETH | 31 | 61.3% | -23.18% | ⚠️ MIXED |
| RSI(2) | BTC | 34 | 50.0% | -55.46% | ⚠️ MIXED |
| RSI(2) | SOL | 34 | 50.0% | -67.44% | ⚠️ MIXED |
| Fear&Greed | BTC | 51 | 54.9% | -114.50% | ⚠️ MIXED |
| BTC Dom | Mixed | 4 | 50.0% | -27.93% | ⚠️ MIXED |
| EOM | BTC | 6 | 50.0% | -2.51% | ❌ NOT CONFIRMED |
| EOM | SOL | 6 | 33.3% | -2.84% | ❌ NOT CONFIRMED |
| EOM | ETH | 6 | 33.3% | -10.76% | ❌ NOT CONFIRMED |

### Key Takeaway
**RSI(2) on equities (SPY, QQQ) is the ONLY strategy confirmed on live recent data.**
Crypto strategies all suffered during the Jan 29 – Feb 7 crash.
This is an honest result, not a cherry-picked one.

---

## 6. HONEST ASSESSMENT & FAILURES <a name="honest-assessment"></a>

### What Worked
- ✅ RSI(2) on SPY: 77.3% WR on 22 trades, +11.69% in 90 days
- ✅ RSI(2) on QQQ: 70.0% WR on 20 trades, +11.56% in 90 days
- ✅ Multi-factor framework is sound (regime detection, signal combination)
- ✅ All data truly free, reproducible, verifiable

### What Failed
- ❌ ALL crypto strategies lost money in last 90 days
- ❌ Fear & Greed "institutional grade" backtest doesn't hold in crash
- ❌ BTC Dominance rotation lost 27.93% recently
- ❌ End-of-month effect NOT confirmed on recent crypto data
- ❌ Funding rate: insufficient extreme signals for statistical proof

### Why Backtests ≠ Reality
1. **Survivorship bias in crypto:** Backtests over 2020-2025 include massive bull runs
2. **Regime change:** Jan-Feb 2026 crash represents a regime our models haven't seen
3. **Crowding:** If Fear & Greed strategy is well-known, other traders front-run it
4. **Slippage:** Our backtests assume perfect fills at close prices

### Honest Renaissance Comparison
- Renaissance's edge is NOT from any single strategy — it's from combining thousands
- Our 5-year Sharpe of 4.99 on pairs trade is misleading; it doesn't hold in all regimes
- Renaissance achieves 66%/yr CONSISTENTLY across all market conditions — we don't
- We can compete on NICHE markets, but we're not Renaissance-level. That's honest.

---

## 7. AUDIT TRAIL — Complete File List <a name="audit-trail"></a>

### Source Code
| File | Purpose | Lines |
|------|---------|-------|
| `alpha_research_engine.py` | v3 academic strategy backtester | ~440 |
| `renaissance_killer.py` | Multi-factor ensemble engine | ~550 |
| `alternative_data_engine.py` | Fear/Greed + Funding + BTC Dom | ~360 |
| `live_proof.py` | Live signal verification engine | ~470 |

### Data Files
| File | Generated | Contents |
|------|-----------|----------|
| `data/alpha_research_v3.json` | Feb 17 2026 | 71 strategy backtest results |
| `data/renaissance_killer_v1.json` | Feb 17 2026 | 19 ensemble backtest results |
| `data/alternative_data_results.json` | Feb 17 2026 | 27 alt-data signal results |
| `data/live_proof.json` | Feb 17 2026 19:45 EST | Live signal + 90-day verification |
| `data/live_proof_full.txt` | Feb 17 2026 19:45 EST | Human-readable full output |
| `data/renaissance_dump.txt` | Feb 17 2026 | Ensemble scoreboard |
| `data/alt_dump.txt` | Feb 17 2026 | Alternative data scoreboard |

### Updates Page
| File | Section | Commit |
|------|---------|--------|
| `updates/index.html` | Renaissance Killer entry | `398995c`, `1859db5` |

### Methodology References
| Strategy | Academic Source |
|----------|---------------|
| Connors RSI(2) | Connors, "Short Term Trading Strategies" (2004) |
| Pairs Trading | Gatev, Goetzmann & Rouwenhorst (2006) |
| Cross-Sectional Momentum | Jegadeesh & Titman (1993) |
| End-of-Month Effect | Ariel, "A Monthly Effect in Stock Returns" (1987) |
| Fear & Greed Contrarian | Behavioral finance, Baker & Wurgler (2006) |
| Kelly Criterion | Kelly (1956), "A New Interpretation of Information Rate" |

---

*Generated by Antigravity AI — February 17, 2026*
*All results are reproducible. Run the Python files to verify.*
