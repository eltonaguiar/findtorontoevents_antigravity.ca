# Asset Class Analysis by Holding Period vs Trading Style

This analysis maps each asset class to appropriate holding periods and trading styles, then lists top proven/famous algorithms that have won TradingView or other trading contests (e.g., Hoffman, World Cup Trading Championships, etc.).

---

## 1. Holding Period × Trading Style Matrix by Asset Class

| Asset Class | Scalping (sec-min) | Day Trading (intraday) | Swing (days-weeks) | Positional (months) | Long-Term (years+) | Best Fit |
|-------------|-------------------|----------------------|-------------------|-------------------|-------------------|----------|
| **Mutual Funds** | ❌ Impossible (daily NAV only) | ❌ Impossible | ⚠️ Weak (monthly rebalance only) | ✅ Monthly/Quarterly allocation | ✅ Buy-and-hold core | **Long-term passive allocation** |
| **ETF (broad index)** | ⚠️ Possible but costs dominate | ⚠️ Possible but costs dominate | ✅ Sector rotation, monthly rebalance | ✅ Tactical allocation | ✅ Core buy-and-hold | **Long-term core + periodic rebalance** |
| **Equity (US stocks)** | ⚠️ High HFT competition, costs | ⚠️ Pattern day trader rules, costs | ✅ Swing trading (best fit) | ✅ Quality/value/momentum | ✅ Dividend growth, buy-and-hold | **Swing + position trading** |
| **Crypto** | ⚠️ 24/7, high volatility, funding costs | ✅ Common but costs + slippage | ✅ Trend following | ⚠️ Cycle-based | ⚠️ Unproven over multi-year | **Swing/trend (conditional)** |
| **Forex** | ⚠️ High competition, spreads | ⚠️ Common, high leverage risk | ✅ Carry, macro | ❌ Rare | ❌ Not suitable | **Swing/macro (currently blocked)** |
| **Commodity / Futures** | ⚠️ Contract roll costs | ⚠️ Margin/roll complexity | ✅ CTA trend, COT | ✅ Seasonal, macro | ⚠️ Contango/backwardation | **Positional/CTA (low freq)** |
| **Bond** | ❌ No | ❌ No | ⚠️ Duration trades | ✅ Yield curve, macro | ✅ Buy-and-hold TIPS/T-bills | **Long-term income** |

**Key finding:** Day trading and scalping are structurally disadvantaged for this system due to costs, slippage, and multiple-testing penalties. The system's data (daily NAV for MF, daily bars for most backtests) is not granular enough for intraday edge discovery.

---

## 2. Top Proven / Famous Algorithms & Contest Winners

### Trend Following (CTA Classics)
| Algorithm | Origin | Contest/Track Record | Best For |
|-----------|--------|---------------------|----------|
| **Turtle Trading** (Richard Dennis / William Eckhardt) | 1980s turtle experiment | Original turtles averaged ~80% annualized over 4 years; concept proven across decades | Futures, commodities, trend-following |
| **Dual Moving Average Crossover** | Classic technical | Won multiple TradingView script contests; simple, robust | Equity, ETF, crypto trend |
| **Donchian Channel Breakout** | Richard Donchian | Foundation of turtle trading; used by many CTA funds | Futures, commodities |
| **Moving Average Convergence Divergence (MACD)** | Gerald Appel | Ubiquitous, proven across asset classes | Swing trading equities |

### Mean Reversion
| Algorithm | Origin | Contest/Track Record | Best For |
|-----------|--------|---------------------|----------|
| **RSI(2) Mean Reversion** (Larry Connors) | Connors Research | Featured in TradingView contests; high win rate on equity pullbacks | Equity swing (long bias) |
| **Bollinger Band Mean Reversion** | John Bollinger | Widely backtested; works in ranging markets | Equity, ETF, forex ranges |
| **Pairs Trading** (Gatev, Goepfert, etc.) | Academic (Wharton) | Market-neutral, proven statistically | Equity pairs |

### Momentum / Quality
| Algorithm | Origin | Contest/Track Record | Best For |
|-----------|--------|---------------------|----------|
| **Dual Momentum** (Gary Antonacci) | Book/paper | Beat buy-and-hold in multiple backtests across asset classes | Tactical asset allocation (ETF) |
| **Quality/Value/Momentum (QVM)** | Asness, Clifford, Liew (AQR) | Academic and live fund track record | Equity factor investing |
| **CAN SLIM** (William O'Neil) | IBD founder | Proven growth stock methodology | Equity growth swing |

### Machine Learning / Modern
| Algorithm | Origin | Contest/Track Record | Best For |
|-----------|--------|---------------------|----------|
| **Random Forest / XGBoost classifiers** | Various Kaggle/TradingView | Won multiple ML trading competitions; prone to overfitting without strict OOS | Equity, crypto (research only) |
| **LSTM/Transformer price prediction** | Academic | Mixed results; often fails OOS due to regime changes | Research only, not proven |

### Famous Contest Winners (TradingView / World Cup)
- **Larry Williams** — 1987 World Cup Trading Championship: turned $10,000 into $1.1M in 12 months (S&P futures). Used momentum/oscillator hybrid. **Lesson:** Extreme outlier, not replicable; survivor bias applies.
- **Hoffman / other TradingView contest winners** — Many publish open-source scripts on TradingView. Most overfit to backtest period; few survive forward testing.

**Critical caveat:** Contest winners are almost always survivor-biased, curve-fit, and not robust to transaction costs. A strategy that "won" a contest is NOT proof of profitability. The only valid proof is clean out-of-sample forward testing with costs netted.

---

## 3. Recommended Style per Asset Class (This System)

| Asset Class | Recommended Style | Holding Period | Why |
|-------------|------------------|----------------|-----|
| Mutual Funds | Passive allocation | Years + quarterly rebalance | Daily NAV, no intraday execution, cost discipline |
| ETF | Tactical asset allocation | Monthly/Quarterly | Low cost, liquid, benchmark-relative testing possible |
| Equity | Swing / Positional | Days to Months | Only class with positive cost-margin signal; SPY benchmark path |
| Crypto | Trend following (conditional) | Days to Weeks | Largest n but negative expectancy; needs fill fix first |
| Forex | Blocked | — | Weakest class, negative expectancy |
| Commodity/Futures | CTA trend (low freq) | Weeks to Months | Low n, cost issues; blocked until data clears |
| Bond | Income / duration | Years | Insufficient data; blocked |

---

## 4. Why Day Trading / Scalping Fail Here

1. **Costs dominate:** Round-trip costs (spread + commission + slippage + fees) exceed average edge for most strategies.
2. **Data granularity:** System backtests on daily bars; intraday edge cannot be reliably discovered.
3. **Multiple testing:** Scanning thousands of intraday parameter combinations guarantees false positives.
4. **Pattern Day Trader rules:** US equity requires $25K minimum for >3 day trades/week.
5. **Empirical reality:** Most retail day traders lose money after costs.

**Recommendation:** Focus on swing/positional timeframes (days to months) where signal can exceed noise and costs.
