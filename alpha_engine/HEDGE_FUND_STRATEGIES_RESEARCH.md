# Hedge Fund-Level Trading Strategies & Risk Management Research
> Compiled: 2026-03-11 | Focus: Actionable strategies with documented performance

---

## TABLE OF CONTENTS
1. [Stocks/Equities](#1-stocksequities)
2. [Penny Stocks](#2-penny-stocks)
3. [ETFs/Indexes](#3-etfsindexes)
4. [Futures](#4-futures)
5. [Forex](#5-forex)
6. [Crypto](#6-crypto)
7. [Mutual Funds](#7-mutual-funds)
8. [Risk Management](#8-risk-management)
9. [Portfolio Construction](#9-portfolio-construction)
10. [Regime Detection](#10-regime-detection)
11. [Strategy Summary Matrix](#11-strategy-summary-matrix)

---

## 1. STOCKS/EQUITIES

### 1.1 Statistical Arbitrage (Pairs Trading)
| Metric | Value |
|---|---|
| **Expected WR** | 55-65% |
| **Sharpe Ratio** | 1.1-3.0 (depending on frequency) |
| **Holding Period** | Intraday to 2 weeks |
| **Complexity** | HIGH |
| **Data Requirements** | Tick/minute data, cointegration libraries |

**How it works:** Identify pairs of stocks with a persistent statistical relationship (cointegration). When the spread deviates beyond a threshold (z-score > 2), go long the underperformer and short the outperformer. Exit when spread reverts to mean.

**Academic backing:**
- S&P 500 vine copula study (1990-2015): 9.25% annualized after costs, Sharpe 1.12, max DD 6.57%
- U.S. bank sector intraday pairs: 26.9% annual return, Sharpe 3.01
- ETF portfolio (45 pairs, 2007-2021): 15% annual, Sharpe 1.43
- Renko-based (US/AU exchanges): 1.4-3.6% monthly excess, Sharpe 1.5-3.4

**Implementation:**
1. Screen universe for cointegrated pairs (Engle-Granger or Johansen test, p < 0.05)
2. Calculate rolling z-score of spread
3. Entry: |z| > 2.0; Exit: |z| < 0.5 or |z| > 4.0 (stop)
4. Position size: equal dollar-neutral
5. Rebalance hedge ratio with Kalman filter for adaptive tracking

**Key risk:** Cointegration can break down (structural break). Use rolling window validation.

---

### 1.2 Connors RSI-2 Mean Reversion
| Metric | Value |
|---|---|
| **Expected WR** | 75% |
| **Sharpe Ratio** | 4.8-6.5 (backtested on SPY/QQQ) |
| **Holding Period** | 1-7 days |
| **Complexity** | LOW |
| **Data Requirements** | Daily OHLCV |

**How it works:** Buy when 2-period RSI drops below 5 (extreme oversold) while price is above 200-day SMA. Sell when RSI(2) rises above 70. The lower the RSI dip, the higher subsequent returns.

**Academic backing:**
- Larry Connors published research: 75.7% WR on SPY, 75.3% on QQQ
- 25-year backtest (2000-2025): CAGR 8.2%, max DD 16%
- Strategy remains robust despite being public since 2010

**Implementation:**
1. Filter: Price > 200-day SMA (bull market only)
2. Entry: RSI(2) < 5
3. Exit: RSI(2) > 70
4. Optional: Cumulative RSI variant for stronger signals

---

### 1.3 Factor Investing (Multi-Factor)
| Metric | Value |
|---|---|
| **Expected WR** | 52-58% (monthly rebalance) |
| **Sharpe Ratio** | 0.5-1.0 per factor, 1.0-1.5 combined |
| **Holding Period** | 1-3 months |
| **Complexity** | MEDIUM |
| **Data Requirements** | Fundamentals + price data |

**Factors with strongest academic backing:**
- **Value**: Book-to-market, earnings yield (Fama-French 1993)
- **Momentum**: 12-1 month return (Jegadeesh & Titman 1993)
- **Quality**: ROE, low accruals, stable earnings (Novy-Marx 2013)
- **Low Volatility**: Min-variance stocks outperform (Ang et al. 2006)
- **Size**: Small-cap premium (Fama-French, weaker post-publication)

**AQR implementation details:**
- Momentum: Rank by 12-month return ex last month; top 33% by market-cap weight
- Rebalance quarterly (March/June/September/December)
- Multi-factor: 5-year annualized return 11.31% as of 2025

---

### 1.4 Momentum (Cross-Sectional)
| Metric | Value |
|---|---|
| **Expected WR** | 55-60% |
| **Sharpe Ratio** | 0.6-1.0 |
| **Holding Period** | 1-12 months |
| **Complexity** | MEDIUM |
| **Data Requirements** | Daily/weekly price data |

**How it works:** Rank stocks by past 12-month return (skip last month). Go long top decile, short bottom decile. Rebalance monthly.

**Key risk:** Momentum crashes (sharp reversals in market regime changes). Mitigate with volatility scaling.

---

## 2. PENNY STOCKS

### 2.1 Volume-Confirmed Breakout
| Metric | Value |
|---|---|
| **Expected WR** | 35-45% (but high R:R) |
| **Sharpe Ratio** | 0.3-0.8 |
| **Holding Period** | Intraday to 3 days |
| **Complexity** | MEDIUM |
| **Data Requirements** | Real-time L2, volume, float data |

**How it works:** Scan for stocks with:
1. Price breakout above resistance with volume > 3x average
2. Float < 20M shares (low supply = explosive moves)
3. Relative volume (RVOL) > 3.0
4. No dilution risk (check SEC filings for shelf offerings)

**Risk management is CRITICAL:**
- Max 1-2% account risk per trade
- Hard stop below breakout level
- Scale out: 1/3 at 1R, 1/3 at 2R, trail remainder
- Never hold overnight in size

### 2.2 Momentum Scanner (Gap & Go)
| Metric | Value |
|---|---|
| **Expected WR** | 40-50% |
| **Sharpe Ratio** | 0.5-1.0 (intraday) |
| **Holding Period** | 15 min to 2 hours |
| **Complexity** | MEDIUM |
| **Data Requirements** | Pre-market scanner, L2 data |

**How it works:**
1. Pre-market scan: gap up > 5%, volume > 500K, price $1-$20
2. Wait for first pullback to VWAP or prior resistance-turned-support
3. Enter on bounce with volume confirmation
4. Stop below VWAP or low of day

**Note:** Penny stocks lack academic backing. These are practitioner strategies. Win rates are lower but reward-to-risk can be 3:1+.

---

## 3. ETFs/INDEXES

### 3.1 Sector Rotation (Trend Following)
| Metric | Value |
|---|---|
| **Expected WR** | 55-60% |
| **Sharpe Ratio** | 1.16 (backtested meta-rotation) |
| **Holding Period** | 1-3 months |
| **Complexity** | LOW-MEDIUM |
| **Data Requirements** | Monthly ETF prices |

**How it works:** Rank sector ETFs by momentum (3/6/12 month returns). Allocate to top N sectors. Rebalance monthly.

**Documented performance:**
- Meta sector ETF rotation: 12.8% annual profit, Sharpe 1.16 vs SPY 0.25
- Combining multiple rotations with low correlation significantly improves Sharpe
- Adding short sector rotation reduces drawdowns during difficult periods

**Implementation (11 SPDR sectors):**
1. Calculate 3-month, 6-month, 12-month returns for XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY
2. Composite score = 0.33 * R3m + 0.33 * R6m + 0.33 * R12m
3. Hold top 3 sectors, equal weight
4. Cash filter: if SPY < 200-day SMA, move 50% to SHY

### 3.2 Faber Tactical Asset Allocation (10-Month SMA)
| Metric | Value |
|---|---|
| **Expected WR** | N/A (binary in/out) |
| **Sharpe Ratio** | 0.7-1.0 |
| **Holding Period** | Months to years |
| **Complexity** | LOW |
| **Data Requirements** | Monthly prices only |

**How it works:** For each asset class (stocks, bonds, commodities, REITs, international), hold if price > 10-month SMA, else go to cash.

**Academic backing:** Meb Faber (2007), backtested 100+ years. Equity-like returns with bond-like volatility and drawdowns. Most importantly: max drawdown reduced from 50%+ to ~20%.

**5 asset classes:** SPY, EFA, AGG, DBC, VNQ. Equal weight when invested.

### 3.3 Risk Parity
| Metric | Value |
|---|---|
| **Expected WR** | N/A (continuous) |
| **Sharpe Ratio** | 0.8-1.2 |
| **Holding Period** | Monthly rebalance |
| **Complexity** | MEDIUM |
| **Data Requirements** | Daily prices, volatility estimates |

**How it works:** Allocate inversely proportional to each asset's volatility so each contributes equal risk. Bonds get higher allocation (lower vol), equities get lower allocation.

**Formula:** Weight_i = (1/vol_i) / sum(1/vol_j)

**Academic backing:** Risk parity rules produce much improved risk-adjusted returns compared to buy-and-hold, with higher Sharpe ratios and lower drawdowns.

---

## 4. FUTURES

### 4.1 Managed Futures / CTA Trend Following
| Metric | Value |
|---|---|
| **Expected WR** | 35-45% (but large winners) |
| **Sharpe Ratio** | 0.5-1.0 (long-term average) |
| **Holding Period** | Weeks to months |
| **Complexity** | HIGH |
| **Data Requirements** | Daily futures data across asset classes |

**How it works:** Apply trend following rules (moving average crossovers, breakout channels, or time-series momentum) across a diversified basket of 50+ futures markets (equities, bonds, currencies, commodities).

**Key features:**
- Positive convexity (profits from large moves in either direction)
- Low/negative correlation to equities (-0.1 to 0.1)
- Crisis alpha: tends to profit during equity crashes
- CTA ETFs like Simplify CTA took in $570M+ in 2025

**Classic implementation:**
1. Signal: 12-month return > 0 → Long; < 0 → Short (time-series momentum)
2. Position size: target volatility per position (e.g., 1% portfolio vol per market)
3. Diversify across 4+ asset classes, 20+ markets
4. Roll futures before expiry using optimal roll schedule

### 4.2 Carry Trade (Futures)
| Metric | Value |
|---|---|
| **Expected WR** | 55-60% |
| **Sharpe Ratio** | 0.5-0.8 |
| **Holding Period** | Monthly roll |
| **Complexity** | MEDIUM |
| **Data Requirements** | Futures term structure data |

**How it works:** Go long futures in backwardation (positive carry/roll yield), short futures in contango (negative carry). The roll yield provides a steady return stream.

**Implementation:** Rank futures by carry (near - far contract price / near price). Long top quintile, short bottom quintile.

### 4.3 Calendar Spreads
| Metric | Value |
|---|---|
| **Expected WR** | 55-65% |
| **Sharpe Ratio** | 0.5-1.0 |
| **Holding Period** | Days to weeks |
| **Complexity** | MEDIUM |
| **Data Requirements** | Futures term structure |

**How it works:** Trade the spread between near and far month contracts. Mean-reverts when spread deviates from normal levels. Lower margin requirements than outright positions.

---

## 5. FOREX

### 5.1 Carry Trade (FX)
| Metric | Value |
|---|---|
| **Expected WR** | 55-65% |
| **Sharpe Ratio** | 0.71 (simple), 1.29 (hedged) |
| **Holding Period** | Weeks to months |
| **Complexity** | MEDIUM |
| **Data Requirements** | Interest rate differentials, daily FX |

**How it works:** Long high-yield currencies, short low-yield currencies. Earns interest rate differential (carry) plus potential appreciation.

**Academic backing:**
- Simple carry: Sharpe 0.71
- Valuation-adjusted carry: Sharpe 0.64-0.87
- With real-time hedging of unpriced risks: Sharpe 1.29
- Higher Sharpe than equity portfolios

**Key pairs:** AUD/JPY, NZD/JPY, MXN/JPY (high carry). Hedge with options for tail risk.

### 5.2 Combined Momentum + Mean Reversion
| Metric | Value |
|---|---|
| **Expected WR** | 52-58% |
| **Sharpe Ratio** | 0.8-1.2 |
| **Holding Period** | 1-20 days |
| **Complexity** | MEDIUM |
| **Data Requirements** | Daily/4H FX data |

**Academic backing:** Combining mean reversion and momentum performs better in FX than equity markets and outperforms carry trades and MA rules individually.

**Implementation:**
1. Momentum signal: 3-month return direction
2. Mean reversion signal: RSI(14) extremes or Bollinger Band touches
3. Trade when both agree (momentum confirms reversion direction)
4. Use SMA for emerging currencies, oscillators for developed currencies

### 5.3 London Breakout
| Metric | Value |
|---|---|
| **Expected WR** | 55-62% |
| **Sharpe Ratio** | 0.6-1.0 |
| **Holding Period** | Intraday |
| **Complexity** | LOW |
| **Data Requirements** | Intraday (15m/1H) FX data |

**How it works:** Identify the Asian session range (00:00-08:00 GMT). Enter on breakout above/below range at London open. Stop at opposite end of range. TP at 1.5x range width.

---

## 6. CRYPTO

### 6.1 Funding Rate Arbitrage
| Metric | Value |
|---|---|
| **Expected WR** | 80%+ (delta neutral) |
| **Sharpe Ratio** | 2.0-4.0 |
| **Annual Return** | 19-115% documented |
| **Holding Period** | Days to weeks |
| **Complexity** | MEDIUM |
| **Data Requirements** | Real-time funding rates, spot + perp data |

**How it works:** When funding rate is positive (longs pay shorts), go long spot + short perpetual futures = delta-neutral carry. Collect funding every 8 hours.

**Documented rates:** Funding can reach 0.05-0.2% per 8 hours during bullish phases = 18-73% annualized from funding alone.

**Risks:** Exchange risk, liquidation on short leg if funding spikes further, basis risk.

### 6.2 BTC Momentum + Mean Reversion Blend
| Metric | Value |
|---|---|
| **Expected WR** | 55-65% |
| **Sharpe Ratio** | 1.71 (50/50 blend) |
| **Annual Return** | ~56% (blended) |
| **Holding Period** | Days to weeks |
| **Complexity** | MEDIUM |
| **Data Requirements** | 4H/Daily OHLCV |

**Academic backing:** BTC-neutral residual mean reversion: Sharpe ~2.3 (post-2021). 50/50 blend of momentum + mean reversion: Sharpe 1.71.

### 6.3 On-Chain Analytics Suite
| Metric | Value |
|---|---|
| **Expected WR** | 60-78% (varies by signal) |
| **Sharpe Ratio** | 0.8-2.0 |
| **Holding Period** | Days to months |
| **Complexity** | HIGH |
| **Data Requirements** | On-chain data (Glassnode, CryptoQuant) |

**Key signals (with documented performance):**
| Signal | Win Rate | Source |
|---|---|---|
| MVRV Z-Score < 0 (buy) | 70%+ | Mahmudov & Puell 2018 |
| Hash Ribbon Buy | 78% | Edwards 2019 |
| Fear & Greed ≤ 10 DCA | ~65% | Nasdaq backtest: 14.6% annual |
| NVT Overvaluation (sell) | 60-65% | Willy Woo 2017 |
| Funding Rate Reversal | 60-65% | CryptoQuant research |

### 6.4 Liquidation Cascade Bottom
| Metric | Value |
|---|---|
| **Expected WR** | 60-65% |
| **Sharpe Ratio** | 1.0-1.5 |
| **Holding Period** | Hours to days |
| **Complexity** | HIGH |
| **Data Requirements** | Liquidation data, order book depth |

**How it works:** Detect large liquidation cascades (>$100M in 1 hour), wait for V-bounce confirmation, enter long. Cascades create artificial oversold conditions that snap back.

---

## 7. MUTUAL FUNDS

### 7.1 Momentum Switching (Fund Rotation)
| Metric | Value |
|---|---|
| **Expected WR** | 55-60% (monthly selection) |
| **Sharpe Ratio** | 0.7-1.2 |
| **Annual Alpha** | 3.72% (top decile, 3-factor) |
| **Holding Period** | Monthly to quarterly |
| **Complexity** | LOW |
| **Data Requirements** | Monthly fund returns |

**Academic backing:** Investing in top decile of no-load funds ranked by momentum exposure yields 3.72% annualized 3-factor alpha (1973-2000). Strong evidence for momentum across asset classes (Kessler & Scherer).

**Implementation:**
1. Rank all no-load funds by 3/6/12-month return
2. Invest in top decile (or top 3-5 funds)
3. Rebalance quarterly
4. Cash filter: move to money market if aggregate market < 200-day SMA

### 7.2 Asset Class Rotation (SACEMS)
| Metric | Value |
|---|---|
| **Expected WR** | N/A (continuous) |
| **Sharpe Ratio** | 0.8-1.0 |
| **Holding Period** | Monthly |
| **Complexity** | LOW |
| **Data Requirements** | Monthly ETF/fund prices |

**How it works:** Simple Asset Class ETF Momentum Strategy: rank asset class ETFs (SPY, EFA, AGG, GLD, VNQ, etc.) by past performance. Hold top 2-3 with equal weight. Rebalance monthly.

---

## 8. RISK MANAGEMENT

### 8.1 Kelly Criterion
**Formula:** f* = (bp - q) / b
- f* = fraction of capital to bet
- b = odds received (win/loss ratio)
- p = probability of winning
- q = 1 - p

**Practical usage:**
- Full Kelly is TOO AGGRESSIVE for trading (huge drawdowns)
- Use **Half Kelly** (f*/2) or **Quarter Kelly** (f*/4) for smoother equity curves
- Kelly should be treated as the UPPER BOUND of position size
- Integrate with VaR/CVaR: reduce Kelly fraction when VaR exceeds threshold

**Example:** WR = 60%, avg win = 2R, avg loss = 1R
- Kelly = (2 * 0.6 - 0.4) / 2 = 0.40 = 40% → Use Half Kelly = 20%

### 8.2 Value at Risk (VaR)
**Types:**
- **Historical VaR:** Sort past returns, take the percentile
- **Parametric VaR:** Assume normal distribution, VaR = μ - z * σ
- **Monte Carlo VaR:** Simulate thousands of paths

**Usage:** "There is a 95% probability that the portfolio will not lose more than $X in one day."

**Limitations:** Assumes normal distribution; doesn't capture tail risk well.

### 8.3 Conditional Value at Risk (CVaR / Expected Shortfall)
**Better than VaR** because it answers: "If we breach VaR, how bad will it get on average?"

CVaR = average of losses beyond the VaR threshold. More conservative and recommended by Basel III.

### 8.4 Position Sizing Framework
```
Position Size = (Account Risk %) / (Entry - Stop) * Entry Price

Hierarchy:
1. Per-trade risk: 0.5-2% of account
2. Per-sector exposure: max 20% of account
3. Per-asset-class exposure: max 40% of account
4. Correlation adjustment: reduce size if correlated positions exist
5. Regime adjustment: reduce size in high-vol regimes (VIX > 25)
```

### 8.5 Correlation-Based Diversification
- Monitor rolling 60-day correlation matrix
- When correlations spike (>0.8), reduce position sizes
- Target portfolio-level diversification ratio > 1.5
- Use PCA to identify hidden correlation clusters
- Tail correlation (during crashes) is always higher than normal-period correlation

---

## 9. PORTFOLIO CONSTRUCTION

### 9.1 Risk Parity
**Formula:** w_i = (1/σ_i) / Σ(1/σ_j)

**Pros:** Equal risk contribution from each asset. Higher Sharpe than 60/40.
**Cons:** Requires leverage for competitive returns. Interest rate sensitivity.

**Implementation:**
1. Estimate volatility for each asset (60-day rolling or EWMA)
2. Allocate inversely proportional to volatility
3. Apply leverage to target overall portfolio volatility (e.g., 10%)
4. Rebalance monthly

### 9.2 Minimum Variance Portfolio
**Objective:** Minimize portfolio variance subject to weights summing to 1.

**Performance:** Research shows no statistically significant difference between MinVar and MaxSR in practice. MinVar offers stable, low-risk outcomes.

**Implementation:** Quadratic programming with covariance matrix. Use shrinkage estimator (Ledoit-Wolf) for stable covariance.

### 9.3 Maximum Sharpe Ratio (Tangency Portfolio)
**Objective:** Maximize (portfolio return - risk-free rate) / portfolio volatility.

**Challenges:** Highly sensitive to expected return estimates. Small errors in μ produce wildly different portfolios.

**Solution:** Use Black-Litterman model to blend market equilibrium returns with investor views.

### 9.4 Black-Litterman Model
**Purpose:** Combines market-implied expected returns (from CAPM equilibrium) with subjective views to produce stable, intuitive portfolio weights.

**Steps:**
1. Compute implied equilibrium returns: Π = δΣw_mkt
2. Express views as: P * μ = Q + ε
3. Combine: posterior μ = [(τΣ)^-1 + P'Ω^-1P]^-1 [(τΣ)^-1Π + P'Ω^-1Q]
4. Optimize with standard mean-variance using posterior μ

**Advantage:** Produces stable, diversified portfolios even with partial or uncertain views.

---

## 10. REGIME DETECTION

### 10.1 Hidden Markov Model (HMM)
| Metric | Value |
|---|---|
| **Regimes** | 3 states (Bull / Bear / Sideways) |
| **Sharpe (regime-adapted)** | 1.05 (backtested 2018-2024) |
| **Sortino** | 1.51 |
| **Complexity** | HIGH |
| **Data Requirements** | Daily returns, volatility, spreads |

**Implementation:**
1. Fit Gaussian HMM with 3 states on daily returns
2. States emerge as: low-vol positive (bull), high-vol negative (bear), low-vol flat (sideways)
3. Trading rules per regime:
   - **Bull:** Full allocation to momentum/trend strategies
   - **Bear:** Reduce equity exposure, increase managed futures, activate short strategies
   - **Sideways:** Mean reversion strategies, sell volatility
4. Transition matrix gives probability of regime change

### 10.2 Simple Regime Indicators (No ML Required)
| Indicator | Bull Signal | Bear Signal |
|---|---|---|
| 200-day SMA | Price above | Price below |
| VIX level | < 20 | > 30 |
| Yield curve | Normal (positive) | Inverted |
| Market breadth | > 60% above 200 SMA | < 40% above 200 SMA |
| Credit spreads | Tightening | Widening |
| Momentum factor | Positive returns | Negative returns |

**Composite regime score:** Average z-scores of all indicators. > 0.5 = Bull, < -0.5 = Bear, else Sideways.

---

## 11. STRATEGY SUMMARY MATRIX

### By Asset Class — Quick Reference

| # | Strategy | Asset Class | WR | Sharpe | Complexity | Data Needs |
|---|---|---|---|---|---|---|
| 1 | Pairs Trading (Cointegration) | Equities | 55-65% | 1.1-3.0 | HIGH | Tick/minute prices |
| 2 | Connors RSI-2 | Equities | 75% | 4.8-6.5 | LOW | Daily OHLCV |
| 3 | Multi-Factor (Value+Mom+Quality) | Equities | 52-58% | 1.0-1.5 | MEDIUM | Fundamentals + price |
| 4 | Cross-Sectional Momentum | Equities | 55-60% | 0.6-1.0 | MEDIUM | Daily/weekly price |
| 5 | Volume Breakout | Penny Stocks | 35-45% | 0.3-0.8 | MEDIUM | Real-time L2, float |
| 6 | Gap & Go Momentum | Penny Stocks | 40-50% | 0.5-1.0 | MEDIUM | Pre-market scanner |
| 7 | Sector Rotation | ETFs | 55-60% | 1.16 | LOW-MED | Monthly ETF prices |
| 8 | Faber 10-Month SMA | ETFs | N/A | 0.7-1.0 | LOW | Monthly prices |
| 9 | Risk Parity | ETFs | N/A | 0.8-1.2 | MEDIUM | Daily prices |
| 10 | CTA Trend Following | Futures | 35-45% | 0.5-1.0 | HIGH | Daily futures data |
| 11 | Futures Carry | Futures | 55-60% | 0.5-0.8 | MEDIUM | Term structure |
| 12 | Calendar Spreads | Futures | 55-65% | 0.5-1.0 | MEDIUM | Term structure |
| 13 | FX Carry Trade | Forex | 55-65% | 0.71-1.29 | MEDIUM | Interest rates + daily FX |
| 14 | FX Momentum + Mean Reversion | Forex | 52-58% | 0.8-1.2 | MEDIUM | Daily/4H FX |
| 15 | London Breakout | Forex | 55-62% | 0.6-1.0 | LOW | Intraday FX |
| 16 | Funding Rate Arbitrage | Crypto | 80%+ | 2.0-4.0 | MEDIUM | Real-time funding |
| 17 | BTC Mom + Mean Rev Blend | Crypto | 55-65% | 1.71 | MEDIUM | 4H/Daily OHLCV |
| 18 | On-Chain Analytics Suite | Crypto | 60-78% | 0.8-2.0 | HIGH | On-chain data |
| 19 | Liquidation Cascade Bottom | Crypto | 60-65% | 1.0-1.5 | HIGH | Liquidation data |
| 20 | Fund Momentum Switching | Mutual Funds | 55-60% | 0.7-1.2 | LOW | Monthly fund returns |
| 21 | Asset Class Rotation | Mutual Funds | N/A | 0.8-1.0 | LOW | Monthly ETF prices |

### Top Strategies by Risk-Adjusted Return (Sharpe)

1. **Connors RSI-2** (Equities) — Sharpe 4.8-6.5 ★★★
2. **Funding Rate Arbitrage** (Crypto) — Sharpe 2.0-4.0 ★★★
3. **Pairs Trading Intraday** (Equities) — Sharpe 1.5-3.0 ★★★
4. **BTC Mean Reversion** (Crypto) — Sharpe 2.3 ★★★
5. **BTC Mom+MR Blend** (Crypto) — Sharpe 1.71 ★★
6. **Multi-Factor** (Equities) — Sharpe 1.0-1.5 ★★
7. **ETF Pairs/Cointegration** (ETFs) — Sharpe 1.43 ★★
8. **FX Carry (Hedged)** (Forex) — Sharpe 1.29 ★★
9. **Sector Rotation** (ETFs) — Sharpe 1.16 ★★
10. **Risk Parity** (Multi-Asset) — Sharpe 0.8-1.2 ★★

### Strategy-Regime Matrix

| Strategy | Bull | Bear | Sideways |
|---|---|---|---|
| Momentum (all) | ★★★ | ★ | ★★ |
| Mean Reversion (RSI-2) | ★★★ | ★ | ★★★ |
| Pairs Trading | ★★ | ★★ | ★★★ |
| Trend Following (CTA) | ★★★ | ★★★ | ★ |
| Carry Trade | ★★★ | ★ | ★★ |
| Risk Parity | ★★ | ★★ | ★★★ |
| Funding Rate Arb | ★★★ | ★★ | ★★ |
| On-Chain Signals | ★★★ | ★★ | ★ |
| Sector Rotation | ★★★ | ★★ | ★★ |

---

## IMPLEMENTATION PRIORITY (Recommended Order)

### Phase 1: Quick Wins (1-2 weeks)
1. Connors RSI-2 on SPY/QQQ (already implemented)
2. Faber 10-Month SMA cash filter (trivial to add)
3. Sector Rotation (11 SPDR ETFs)
4. FX Carry Trade (rank by yield differential)

### Phase 2: Core Alpha (2-4 weeks)
5. Multi-Factor equity selection (value + momentum + quality)
6. Funding Rate Arbitrage (crypto, delta-neutral)
7. On-Chain composite score
8. Combined FX momentum + mean reversion

### Phase 3: Advanced (1-2 months)
9. Pairs Trading with Kalman filter hedge ratios
10. CTA Trend Following across 20+ futures
11. HMM Regime Detection to dynamically weight strategies
12. Risk Parity portfolio construction across all strategies

### Phase 4: Integration
13. Kelly-based position sizing with CVaR constraints
14. Correlation monitoring and dynamic de-risking
15. Black-Litterman overlay for strategic views
16. Full regime-adaptive portfolio

---

## SOURCES

- [Statistical Arbitrage: Record Inflows (Substack)](https://navnoorbawa.substack.com/p/statistical-arbitrage-the-quant-strategy)
- [Quant Hedge Funds 2026 Due Diligence (Resonanz Capital)](https://resonanzcapital.com/insights/quant-hedge-funds-in-2026-a-due-diligence-framework-by-strategy-type)
- [2026 Hedge Fund Outlook (BNP Paribas)](https://globalmarkets.cib.bnpparibas/2026-hedge-fund-outlook/)
- [Pairs Trading Copula Methods (MDPI)](https://www.mdpi.com/1911-8074/18/9/506)
- [Connors RSI: 75% Win Rate (QuantifiedStrategies)](https://www.quantifiedstrategies.com/connors-rsi/)
- [Connors RSI2 Mean Reversion (MQL5)](https://www.mql5.com/en/articles/17636)
- [AQR Momentum Factor Strategy](https://funds.aqr.com/Insights/Strategies/Momentum-Factor)
- [AQR: Fact, Fiction and Momentum Investing](https://www.aqr.com/-/media/AQR/Documents/Journal-Articles/JPM-Fact-Fiction-and-Momentum-Investing.pdf)
- [ETF Sector Rotation (Logical Invest)](https://logical-invest.com/app/strategy/ussect/us-sector-rotation-strategy)
- [Risk Parity & Trend Following in Global Markets (EFMA)](https://www.efmaefm.org/0efmameetings/efma%20annual%20meetings/2013-Reading/papers/EFMA2013_0130_fullpaper.pdf)
- [Faber Tactical Asset Allocation (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=962461)
- [Managed Futures Trend Following (Return Stacked)](https://www.returnstacked.com/managed-futures-trend-following/)
- [Managed Futures Positioning & Geopolitical Risks (AdvisorAnalyst)](https://advisoranalyst.com/2026/03/05/managed-futures-current-positioning-and-geopolitical-risks.html/)
- [FX Carry Trade (Quantpedia)](https://quantpedia.com/strategies/fx-carry-trade)
- [Advanced FX Carry with Valuation Adjustment (Macrosynergy)](https://macrosynergy.com/research/advanced-fx-carry-strategies-with-valuation-adjustment/)
- [Combining Mean Reversion & Momentum in FX (ResearchGate)](https://www.researchgate.net/publication/222554542_Combining_mean_reversion_and_momentum_trading_strategies_in_foreign_exchange_markets)
- [Systematic Crypto Strategies: Momentum & Mean Reversion (Medium)](https://medium.com/@briplotnik/systematic-crypto-trading-strategies-momentum-mean-reversion-volatility-filtering-8d7da06d60ed)
- [Funding Rate Arbitrage Guide (BingX)](https://bingx.com/en/learn/article/what-is-funding-rate-arbitrage-guide-for-futures-traders)
- [Crypto Arbitrage 2026 (WunderTrading)](https://wundertrading.com/journal/en/learn/article/crypto-arbitrage)
- [Momentum in Mutual Fund Returns (Quantpedia)](https://quantpedia.com/strategies/momentum-in-mutual-fund-returns)
- [Asset Class Momentum Rotational System (Quantpedia)](https://quantpedia.com/strategies/asset-class-momentum-rotational-system)
- [Kelly Criterion: Practical Portfolio Optimization](https://investwithcarl.com/learning-center/investment-basics/dynamic-adaptive-kelly-criterion-bridging-theory-and-practice-for-modern-portfolio-optimization)
- [Risk-Constrained Kelly Criterion (QuantInsti)](https://blog.quantinsti.com/risk-constrained-kelly-criterion/)
- [Kelly Criterion: Rebalancing for Equity Portfolios (Frontiers)](https://www.frontiersin.org/journals/applied-mathematics-and-statistics/articles/10.3389/fams.2020.577050/full)
- [Black-Litterman with Dynamic CAPM (MDPI)](https://www.mdpi.com/2227-7390/13/20/3265)
- [Portfolio Optimization Book (Palomar 2025)](https://portfoliooptimizationbook.com/portfolio-optimization-book.pdf)
- [HMM Regime Detection for Trading (Medium)](https://datadave1.medium.com/detecting-market-regimes-hidden-markov-model-2462e819c72e)
- [Regime-Switching Factor Investing with HMMs (MDPI)](https://www.mdpi.com/1911-8074/13/12/311)
- [HMM + Monte Carlo Short-Term Trading (CANA)](https://internationalpubls.com/index.php/cana/article/view/6029)
- [Pairs Trading Profitability (Yale Economics)](https://economics.yale.edu/sites/default/files/2024-05/Zhu_Pairs_Trading.pdf)
- [Penny Stock Strategies (Algorithmic Trading Library)](https://algotradinglib.com/en/pedia/p/penny_stock_strategies.html)
- [Penny Stock Trading 2026 (Humbled Trader)](https://www.humbledtrader.com/blog/penny-stock-strategy-tips-for-successful-trading/)
