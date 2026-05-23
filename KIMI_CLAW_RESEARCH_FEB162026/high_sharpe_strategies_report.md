# High Sharpe Ratio Investment Strategies - Competition Report

## Executive Summary

This report presents five rigorously researched investment strategies with demonstrated ability to achieve superior Sharpe ratios compared to traditional market-cap weighted approaches. Each strategy is backed by extensive academic research and empirical validation spanning multiple decades and international markets.

---

## Strategy 1: Low Volatility Anomaly Strategy (Betting Against Beta)

### Core Concept and Edge

The Low Volatility Anomaly, also known as "Betting Against Beta" (BAB), exploits a fundamental violation of the Capital Asset Pricing Model (CAPM). Contrary to CAPM's prediction of a positive linear relationship between beta and expected returns, empirical evidence shows that low-beta stocks deliver higher risk-adjusted returns than high-beta stocks.

**The Economic Intuition:**
- Leverage-constrained investors (pension funds, mutual funds with leverage restrictions) cannot use leverage to enhance returns
- These investors overweight high-beta stocks to achieve higher expected returns, creating artificial demand
- This demand inflates high-beta stock prices, depressing their future returns
- Conversely, low-beta stocks become underpriced, offering superior risk-adjusted returns
- Additional factors include lottery ticket preferences (investors favor high-volatility stocks with small chances of large payoffs) and regulatory constraints that don't differentiate risk levels

### Entry/Exit Rules

**Universe Selection:**
- Start with liquid large-cap universe (top 1,000 stocks by market cap)
- Exclude stocks with insufficient trading history (minimum 12 months of returns data)
- Filter out stocks with extreme illiquidity or trading halts

**Beta Calculation:**
- Calculate rolling 60-month (5-year) beta relative to market index
- Use weekly or monthly returns to reduce noise
- Winsorize beta estimates at 5th and 95th percentiles to handle outliers

**Portfolio Construction:**
- Rank stocks by beta and divide into deciles
- Go LONG the lowest beta decile (bottom 10%)
- Go SHORT the highest beta decile (top 10%)
- Within each decile, weight stocks by market cap or equal weight

**Rebalancing:**
- Rebalance monthly to capture updated beta estimates
- Alternatively, quarterly rebalancing reduces transaction costs with minimal performance degradation

**Exit Conditions:**
- Exit individual positions when they no longer qualify for their respective decile
- Consider full strategy exit when low-volatility stocks exhibit extreme growth valuations (expensive regime)

### Position Sizing

**Long Side (Low Beta):**
- Allocate 100% of capital to low-beta stocks
- Leverage the low-beta portfolio to achieve beta = 1.0 (market neutral exposure)
- Leverage factor = 1 / (average beta of low-beta portfolio)

**Short Side (High Beta):**
- Short high-beta stocks and deleverage to beta = 1.0
- Deleverage factor = 1 / (average beta of high-beta portfolio)

**Example:**
- Low-beta portfolio average beta = 0.5 → Apply 2x leverage
- High-beta portfolio average beta = 1.5 → Apply 0.67x deleverage

### Expected Sharpe Ratio

| Metric | Value |
|--------|-------|
| Historical Sharpe Ratio (1926-2012) | 0.78 |
| Market Sharpe Ratio (same period) | ~0.40-0.45 |
| Value Factor Sharpe Ratio | ~0.38 |
| Momentum Factor Sharpe Ratio | ~0.55 |

**Key Finding:** The BAB factor achieved approximately **double the Sharpe ratio of the market** and 40% higher than momentum during the same period.

### Backtest Rationale

**Frazzini & Pedersen (2014) - Original Study:**
- Period: 1926 to March 2012 (86+ years)
- Universe: U.S. equities
- BAB Sharpe: 0.78 vs Market Sharpe: 0.40
- BAB showed positive returns in all four 20-year subperiods
- Highly significant alphas after controlling for market, value, size, momentum, and liquidity factors

**International Validation:**
- Tested across 19 international equity markets
- Consistent results across countries and time periods
- BAB factor positive in stocks, Treasury bonds, credit markets, and futures (currencies/commodities)

**Robustness:**
- Results hold within size deciles (not just small-cap effect)
- Results hold within idiosyncratic risk deciles
- Alphas decline almost monotonically as beta increases across all asset classes

### Why It Beats the Market

1. **Behavioral Bias Exploitation:** Investors systematically overpay for high-beta "lottery ticket" stocks while underpricing stable, boring low-beta stocks

2. **Institutional Constraints:** Leverage restrictions force investors to reach for return through high-beta exposure, creating persistent mispricing

3. **Risk-Based Explanation:** Low-beta stocks have bond-like characteristics (stable cash flows, dividends) and benefit from falling interest rate environments

4. **Factor Diversification:** BAB returns have low correlation with traditional factors (market, value, momentum), providing portfolio diversification benefits

5. **Time-Varying Premium:** BAB returns are predictable - higher following strong market returns, allowing for tactical enhancement

---

## Strategy 2: Quality Factor Strategy (Quality Minus Junk - QMJ)

### Core Concept and Edge

The Quality Factor strategy invests in high-quality companies while avoiding or shorting "junk" stocks. Quality is defined across multiple dimensions: profitability, growth, safety, and payout. The QMJ factor captures the premium associated with owning high-quality businesses.

**The Economic Intuition:**
- High-quality companies have durable competitive advantages, stable earnings, and strong balance sheets
- Investors systematically underprice quality due to preference for speculative growth stories
- Quality stocks provide defensive characteristics during market downturns
- Profitability (gross profits-to-assets) is the strongest predictor of quality returns (Novy-Marx research)

**Quality Dimensions (Asness, Frazzini, Pedersen):**
1. **Profitability:** Gross profits-to-assets, ROE, ROA
2. **Growth:** Stability and improvement in profitability metrics
3. **Safety:** Low beta, low volatility, low leverage, stable earnings
4. **Payout:** Dividend yield, share buybacks, low equity issuance

### Entry/Exit Rules

**Universe Selection:**
- Large liquid universe (top 1,000-2,000 stocks by market cap)
- Minimum $500M market cap for liquidity
- Exclude financials for certain quality metrics (use adjusted metrics)

**Quality Scoring:**
- Calculate z-scores for each quality dimension:
  - **Profitability:** Gross profits / Total assets
  - **Safety:** Beta (lower = better), Volatility (lower = better), Leverage (lower = better)
  - **Growth:** 5-year growth in profitability metrics
  - **Payout:** Dividend yield + buyback yield - equity issuance yield

- Combine dimensions into overall quality score (equal weight or profitability-weighted)

**Portfolio Construction:**
- Rank stocks by composite quality score
- Go LONG top 30% highest quality stocks
- Go SHORT bottom 30% lowest quality ("junk") stocks
- Within each side, weight by quality score or market cap

**Rebalancing:**
- Rebalance annually (quality is a slower-moving factor)
- Alternatively, quarterly updates for faster-moving metrics

**Exit Conditions:**
- Exit when quality score deteriorates significantly (drops out of top/bottom 30%)
- Consider profit-taking when quality spreads compress to historical lows

### Position Sizing

**Long Side (High Quality):**
- 100% allocation to top 30% quality stocks
- Equal weight or quality-score weight within portfolio
- Consider value-weighting to reduce small-cap bias

**Short Side (Junk):**
- 100% allocation to short bottom 30% quality stocks
- Dollar-neutral or beta-neutral to market

**Risk Management:**
- Maximum 5% position in any single stock
- Sector constraints (max 25% in any sector) to avoid concentration

### Expected Sharpe Ratio

| Metric | Value |
|--------|-------|
| QMJ Factor Sharpe Ratio (1963-2011) | 0.50-0.60 |
| Market Sharpe Ratio | ~0.40 |
| Profitability Factor Alone Sharpe | ~0.45-0.55 |

**Key Finding:** Quality stocks delivered significant risk-adjusted returns with lower volatility than the market, resulting in superior Sharpe ratios.

### Backtest Rationale

**Asness, Frazzini, Pedersen (2013) - QMJ Study:**
- Period: 1956-2011 (55+ years)
- Universe: U.S. equities
- QMJ factor earned significant risk-adjusted returns
- Quality stocks outperformed despite having lower risk (beta < 1)
- Results robust across international markets

**Novy-Marx (2013) - Profitability Premium:**
- Period: 1963-2010
- Gross profitability had same predictive power as book-to-market (value)
- Controlling for profitability dramatically improved value strategy performance
- Profitability and value are uncorrelated (correlation ~0.1), providing diversification

**Verdad Research (1998-2021):**
- Quality stocks returned 13.2% annually vs 9.1% for market
- Quality returns driven by: 6.8% multiple expansion + 4.6% EBITDA growth
- Value stocks returned 14.7% but with different drivers (14.0% multiple expansion - 2.6% earnings decline)

### Why It Beats the Market

1. **Profitability Persistence:** Highly profitable companies tend to remain profitable due to competitive moats

2. **Behavioral Underpricing:** Investors underprice stable, profitable businesses in favor of exciting growth stories with uncertain futures

3. **Defensive Characteristics:** Quality stocks have lower beta and volatility, providing downside protection during market stress

4. **Earnings Growth:** Quality companies deliver consistent earnings growth (~5% annually, in line with nominal GDP)

5. **Factor Orthogonality:** Quality has low correlation with value (0.1) and momentum, providing true diversification

6. **Institutional Preference:** Quality stocks benefit from institutional demand during risk-off periods

---

## Strategy 3: Dividend Growth + Low Volatility Strategy

### Core Concept and Edge

This strategy combines two complementary factors: dividend growth (indicating financial health and management confidence) and low volatility (indicating stability and reduced risk). The combination provides "defensive growth" - capturing upside while limiting downside.

**The Economic Intuition:**
- Dividend growth signals sustainable cash flows and management confidence in future earnings
- Low volatility stocks have historically delivered superior risk-adjusted returns
- Combining both factors creates a "double filter" for quality and stability
- The strategy benefits from both income (dividends) and capital appreciation
- Particularly effective in low-interest-rate environments where bond-like equities are attractive

**Why the Combination Works:**
- Low volatility alone may select stocks with unsustainable high yields (value traps)
- Dividend growth alone may select volatile cyclical companies with temporary payout increases
- Together, they select stable companies with growing, sustainable cash flows

### Entry/Exit Rules

**Universe Selection:**
- Large-cap universe (top 1,000 stocks by market cap)
- Minimum $1B market cap
- Minimum 5-year dividend history (for growth calculation)
- Exclude REITs and MLPs (different tax/structure considerations)

**Dividend Growth Screening:**
- Calculate 5-year dividend growth rate (CAGR)
- Require positive dividend growth (growing, not just maintaining)
- Minimum current dividend yield of 1.5% (avoid pure growth stocks)
- Dividend payout ratio < 80% (sustainable payout)

**Low Volatility Screening:**
- Calculate 3-year rolling volatility (standard deviation of returns)
- Select stocks in the bottom 50% of volatility within dividend-growers universe
- Alternative: Use beta < 1.0 relative to market

**Portfolio Construction (Two-Step Process):**

*Step 1 - Low Volatility Filter:*
- Select 500 stocks with lowest 3-year volatility from top 1,000

*Step 2 - Dividend Growth + Value Overlay:*
- From the 500 low-volatility stocks, select top 100 by:
  - Combined score of net payout yield (dividends + buybacks) and 12-month momentum
  - Or dividend growth rate ranking

**Rebalancing:**
- Rebalance monthly for momentum component
- Quarterly rebalancing acceptable for lower turnover
- Review dividend sustainability quarterly

**Exit Conditions:**
- Exit if dividend is cut or suspended
- Exit if volatility increases significantly (top quartile)
- Exit if payout ratio exceeds 90% (unsustainable)

### Position Sizing

**Equal Weight Approach:**
- 100 positions, each 1% of portfolio
- Reduces concentration risk
- Natural small-cap tilt within large-cap universe

**Risk-Parity Weighting:**
- Weight inversely by volatility (lower vol = higher weight)
- Normalizes risk contribution across positions

**Maximum Position Limits:**
- Single stock max: 2%
- Sector max: 20%

### Expected Sharpe Ratio

| Metric | Value |
|--------|-------|
| Low Volatility Alone Sharpe | 0.50-0.60 |
| Dividend Growth Alone Sharpe | 0.45-0.55 |
| **Combined Strategy Sharpe** | **0.65-0.75** |
| Market Sharpe Ratio | ~0.40 |

**Key Finding:** Research by van der Linden, Soebhag, and van Vliet (2024) showed that integrating momentum and value (net payout yield) into low volatility improved Sharpe ratios by approximately 47% compared to generic low volatility.

### Backtest Rationale

**Van der Linden, Soebhag, van Vliet (2024) - Enhanced Low Volatility:**
- Period: 1990-2023 (33 years)
- Universe: Largest 1,000 U.S. stocks
- Standard LowVol: Select 100 lowest volatility stocks
- Enhanced LowVol+: Filter 500 lowest vol, then select top 100 by net payout yield + momentum

**Results:**
| Strategy | Annual Return | Volatility | Sharpe Ratio |
|----------|---------------|------------|--------------|
| Market | ~10% | ~15% | ~0.40 |
| Standard LowVol | ~9% | ~10% | ~0.55 |
| Enhanced LowVol+ | ~11% | ~10% | ~0.75 |

**CIBC Research:**
- Combining low volatility with dividend strategies improves sustainability of cash flows
- Low volatility provides downside protection; dividend growth provides upside participation

### Why It Beats the Market

1. **Double Factor Exposure:** Benefits from both low volatility anomaly and dividend growth premium

2. **Income Component:** Dividends provide steady cash flow and downside cushion (dividend floor)

3. **Quality Signal:** Dividend growth is a strong signal of financial health and management confidence

4. **Behavioral Edge:** Combines two underexploited anomalies that persist due to institutional constraints and investor preferences

5. **Defensive Growth:** Captures growth through dividend increases while maintaining defensive characteristics

6. **Lower Drawdowns:** Significantly reduced maximum drawdowns compared to market (often 30-40% lower)

---

## Strategy 4: Minimum Variance Portfolio (MVP)

### Core Concept and Edge

The Minimum Variance Portfolio uses mathematical optimization to construct the portfolio with the lowest possible variance (risk) for a given universe of assets. Unlike equal-weight or market-cap-weighted approaches, MVP explicitly considers correlations between assets to minimize portfolio-level volatility.

**The Economic Intuition:**
- Portfolio variance depends on both individual asset volatilities AND correlations
- Diversification benefits are maximized by considering covariance structure
- Low-volatility stocks often have low correlations with each other
- MVP tilts toward low-beta, low-volatility stocks while optimizing diversification
- Mathematical optimization can achieve lower portfolio risk than naive diversification

**Key Insight:** MVP maximizes diversification benefits by accounting for how assets move together, not just their individual risks.

### Entry/Exit Rules

**Universe Selection:**
- Large liquid universe (top 500-1,000 stocks by market cap)
- Minimum $500M market cap
- Minimum 3 years of return history for covariance estimation
- Exclude stocks with extreme illiquidity

**Covariance Matrix Estimation:**
- Calculate rolling covariance matrix using 1-3 years of historical returns
- Use daily or weekly returns for precision
- Apply shrinkage estimators (Ledoit-Wolf) to improve stability
- Alternatively, use factor models to estimate covariance

**Optimization Problem:**
```
Minimize: w'Σw (portfolio variance)
Subject to:
  - Σwi = 1 (fully invested)
  - wi ≥ 0 (no short selling, optional)
  - wi ≤ 5% (maximum position limit)
  - Sector constraints (optional)
```
Where w = weight vector, Σ = covariance matrix

**Portfolio Construction:**
- Solve quadratic programming problem for minimum variance weights
- Reject solutions with extreme concentrations
- Apply turnover constraints (max 20% turnover per rebalance)

**Rebalancing:**
- **Quarterly rebalancing** provides best balance of tracking error vs turnover costs
- Monthly rebalancing: Lower tracking error, higher costs
- Semi-annual rebalancing: Higher tracking error, lower costs
- Consider threshold-based rebalancing (rebalance when weights drift >X%)

**Exit Conditions:**
- Rebalance when optimization indicates new optimal weights
- Emergency exit: If portfolio volatility exceeds target by >20%

### Position Sizing

**Optimization-Driven:**
- Position sizes determined by optimizer, not arbitrary rules
- Lower volatility stocks and those with better diversification benefits receive higher weights
- Natural tendency toward 50-150 positions depending on universe

**Constraint-Based Limits:**
- Maximum single position: 3-5%
- Maximum sector allocation: 20-25%
- Minimum position size: 0.1% (avoid dust positions)

**Leverage (Optional Enhancement):**
- Apply modest leverage (1.2-1.5x) to MVP to match market volatility
- Results in higher returns while maintaining similar or better Sharpe ratio

### Expected Sharpe Ratio

| Metric | Value |
|--------|-------|
| MVP Sharpe Ratio | 0.55-0.70 |
| Market-Cap Weighted Sharpe | ~0.40 |
| Equal Weight Sharpe | ~0.45 |
| MVP with Leverage Sharpe | 0.60-0.75 |

**Key Finding:** MVP typically achieves 30-50% reduction in volatility while maintaining 80-90% of market returns, resulting in significantly higher Sharpe ratios.

### Backtest Rationale

**STOXX Minimum Variance Indices:**
- Period: Multi-decade backtests
- Quarterly rebalancing with 5% one-way turnover constraint
- MVP achieved higher Sharpe ratios than market-cap weighted with lower drawdowns

**Clarke, de Silva, Thorley (2006, 2011):**
- Minimum variance portfolios outperformed market-cap benchmarks
- MVP had lower beta (0.6-0.7) but similar or higher returns
- Information ratios of 0.3-0.5 vs market benchmark

**Haugen and Baker (1991, 2012):**
- Low volatility portfolios outperformed high volatility portfolios
- Efficient frontier is "inverted" - low risk stocks have higher returns
- MVP captures this anomaly through optimization

**Empirical Results (Typical):**
| Metric | MVP | Market Cap |
|--------|-----|------------|
| Annual Return | 9-11% | 10% |
| Volatility | 8-11% | 15% |
| Sharpe Ratio | 0.60-0.70 | 0.40 |
| Max Drawdown | -25% | -50% |
| Beta | 0.60-0.70 | 1.00 |

### Why It Beats the Market

1. **Mathematical Efficiency:** Explicit optimization of diversification benefits vs naive weighting

2. **Low Volatility Tilt:** Inherits benefits of low volatility anomaly through optimization

3. **Correlation Exploitation:** Identifies and exploits low-correlation relationships that equal-weight misses

4. **Downside Protection:** Significantly lower drawdowns (often 40-50% less than market)

5. **Beta Arbitrage:** Captures the flat security market line - lower beta with similar returns

6. **Rebalancing Premium:** Regular rebalancing harvests volatility through disciplined buying low/selling high

---

## Strategy 5: Risk Parity Approach

### Core Concept and Edge

Risk Parity allocates capital such that each asset contributes equally to portfolio risk, rather than allocating equal capital (equal weight) or by market cap. This approach recognizes that equal dollar allocations create unequal risk contributions because assets have different volatilities and correlations.

**The Economic Intuition:**
- Traditional portfolios are dominated by the riskiest assets (typically equities)
- In a 60/40 stock/bond portfolio, stocks contribute 80-90% of total risk
- Risk parity equalizes risk contributions, forcing true diversification
- Lower-risk assets (bonds) receive higher allocations to balance their lower volatility
- Often uses leverage to achieve target return while maintaining diversification

**Key Principle:** True diversification requires equal risk contribution, not equal capital allocation.

### Entry/Exit Rules

**Universe Selection:**
- Multi-asset approach: Equities, bonds, commodities, REITs, alternatives
- Within equities: Factor ETFs or broad market indices
- Minimum 4-6 asset classes for diversification
- Liquid, investable instruments only

**Risk Contribution Calculation:**
For each asset i:
```
Risk Contribution (RCi) = wi × (∂σp/∂wi) = wi × (Σw)i / σp
```
Where:
- wi = weight of asset i
- σp = portfolio volatility
- Σ = covariance matrix

**Target:** RCi = RCj for all assets i, j (equal risk contribution)

**Portfolio Construction:**
- Solve inverse volatility weighting as starting point: wi ∝ 1/σi
- Iterate to find weights where risk contributions are equal
- Alternative: Use optimization to minimize distance from equal risk contribution

**Leverage Application:**
- Apply leverage to achieve target portfolio volatility (e.g., 10%)
- Leverage = Target Vol / Unlevered Risk Parity Vol
- Typical leverage: 2-3x for diversified risk parity portfolios

**Rebalancing:**
- Monthly rebalancing to maintain risk parity
- Or threshold-based: Rebalance when risk contributions deviate >20% from target
- More frequent rebalancing needed during high volatility periods

**Exit Conditions:**
- Rebalance when risk contributions become unbalanced
- Tactical overlay: Reduce equity risk parity weight during extreme market stress
- Stop-loss: If portfolio drawdown exceeds 15%

### Position Sizing

**Inverse Volatility Weighting (Approximation):**
```
wi = (1/σi) / Σ(1/σj)
```

**Example Allocation (Unlevered):**
| Asset | Volatility | Weight | Risk Contribution |
|-------|------------|--------|-------------------|
| Stocks | 15% | 20% | 25% |
| Bonds | 5% | 60% | 25% |
| Commodities | 15% | 20% | 25% |

**With 2x Leverage:**
- Stocks: 40%
- Bonds: 120% (requires leverage)
- Commodities: 40%
- Total: 200% (2x levered)

**Position Limits:**
- Maximum single asset: 40% (unlevered)
- Maximum leverage: 3x
- Minimum assets: 4 for diversification

### Expected Sharpe Ratio

| Metric | Value |
|--------|-------|
| Risk Parity Sharpe Ratio | 0.60-0.80 |
| 60/40 Portfolio Sharpe | ~0.45-0.50 |
| Equal Weight Sharpe | ~0.45 |
| All Weather (Bridgewater) Sharpe | ~0.60 |

**Key Finding:** Risk parity portfolios can achieve Sharpe ratios 60% higher than traditional portfolios due to superior diversification and risk balancing.

### Backtest Rationale

**AQR Research - Understanding Risk Parity:**
- Risk parity Sharpe ratio more than 60% higher than traditional portfolios
- Equal risk contribution maximizes diversification benefits
- Works best when asset Sharpe ratios are similar and correlations moderate

**Bridgewater All Weather Fund (Ray Dalio):**
- Launched 1996
- Risk parity approach across economic environments
- Achieved approximately 0.6 Sharpe ratio consistently
- Outperformed during various market regimes (inflation, deflation, growth, recession)

**Maillard, Roncalli, Teïletche (2010):**
- Mathematical proof of risk parity properties
- Risk parity is mean-variance efficient when asset Sharpe ratios are equal
- Empirical tests show superior risk-adjusted returns

**Empirical Results (Typical):**
| Metric | Risk Parity | 60/40 Portfolio |
|--------|-------------|-----------------|
| Annual Return | 8-10% | 7-8% |
| Volatility | 8-10% | 10-12% |
| Sharpe Ratio | 0.65-0.75 | 0.45-0.55 |
| Max Drawdown | -15% | -30% |

### Why It Beats the Market

1. **True Diversification:** Equal risk contribution means no single asset dominates portfolio outcomes

2. **Volatility Harvesting:** Regular rebalancing naturally buys low (after vol spikes) and sells high

3. **Leverage Efficiency:** Uses leverage on low-risk assets (bonds) to achieve target returns - more efficient than concentrating in high-risk equities

4. **All-Weather Performance:** Balanced risk contributions perform across different economic regimes

5. **Downside Protection:** Maximum drawdowns typically 50% lower than equity-heavy portfolios

6. **Mathematical Optimality:** Risk parity is the maximum diversification portfolio when Sharpe ratios are equal

---

## Strategy Comparison Summary

| Strategy | Expected Sharpe | Volatility | Max Drawdown | Complexity | Best For |
|----------|-----------------|------------|--------------|------------|----------|
| **Low Volatility (BAB)** | 0.70-0.80 | Low | Low | Medium | Equity-only, leverage-constrained |
| **Quality Factor (QMJ)** | 0.50-0.60 | Low-Med | Low-Med | Medium | Long-only quality tilt |
| **Dividend Growth + Low Vol** | 0.65-0.75 | Low | Low | Low-Med | Income-focused investors |
| **Minimum Variance** | 0.55-0.70 | Very Low | Very Low | High | Institutional, risk-focused |
| **Risk Parity** | 0.60-0.80 | Low | Low | High | Multi-asset, sophisticated |

## Implementation Recommendations

### For Competition Entry:

1. **Highest Sharpe Potential:** Risk Parity or Low Volatility (BAB) - both demonstrate 0.70+ Sharpe ratios historically

2. **Easiest Implementation:** Dividend Growth + Low Volatility - requires only screening, no complex optimization

3. **Best Risk-Adjusted Returns:** Minimum Variance - lowest volatility with competitive returns

4. **Most Academic Support:** Quality Factor (QMJ) - extensive research from AQR and Novy-Marx

### Key Success Factors:

1. **Discipline:** All strategies require systematic implementation without emotional overrides
2. **Rebalancing:** Regular rebalancing is critical for capturing factor premiums
3. **Costs:** Use low-cost ETFs or patient trading to minimize implementation drag
4. **Patience:** Factor premiums exist but can experience multi-year drawdowns
5. **Diversification:** Consider combining multiple strategies for more stable results

---

*Report compiled based on academic research from Frazzini & Pedersen (BAB), Asness et al. (QMJ), Novy-Marx (Profitability), van Vliet et al. (Enhanced Low Vol), and Bridgewater/Ray Dalio (Risk Parity).*
