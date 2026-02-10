
# COMPREHENSIVE FACTOR INVESTING ANALYSIS
## Academic Evidence & Implementation Guide for Quantitative Trading

---

# PART 1: MENTIONED FACTORS - DETAILED ANALYSIS

## 1. POST-EARNINGS ANNOUNCEMENT DRIFT (PEAD)

### Academic Evidence
- **Original Discovery**: Ball & Brown (1968) - "An Empirical Evaluation of Accounting Income Numbers"
- **Key Extension**: Bernard & Thomas (1989, 1990) - "Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium?"
- **Fama's Assessment**: Called "the granddaddy of all underreaction events" and "the most severe challenge to financial theorists"

### Key Findings
- PEAD persists for 60+ trading days after earnings announcements
- Good news firms drift upward; bad news firms drift downward
- Annualized returns to PEAD strategy: 8.76% to 43.08% depending on implementation
- Text-based PEAD (SUE.txt) shows even stronger effects than traditional SUE measures

### Implementation
```
SUE = (Actual EPS - Expected EPS) / σ(Expected EPS)

Where Expected EPS can be:
1. Analyst consensus (IBES) - PREFERRED
2. Seasonal random walk: EPS(t-4 quarters) + drift
3. Time-series model (ARIMA)

Signal: Z-score of SUE within sector
Long: Top decile SUE stocks
Short: Bottom decile SUE stocks
```

### Optimal Parameters
- **Lookback**: Single quarter surprise (most recent)
- **Holding Period**: 6-8 weeks (40-60 trading days)
- **Rebalancing**: Monthly or event-driven (after each earnings season)
- **Decay**: Strongest in first 2-3 weeks, persists for 2-3 months

### Sector Neutrality
- CRITICAL: Must sector-neutralize; PEAD varies significantly by sector
- Technology and healthcare show strongest drift
- Financials show weaker but still significant drift

### Historical Sharpe
- Gross Sharpe: 1.0-1.5 depending on implementation
- Transaction costs: High due to frequent rebalancing
- Net Sharpe: 0.6-1.0 after costs

---

## 2. DIVIDEND ARISTOCRATS

### Academic Evidence
- **Academic Theory**: Miller & Modigliani (1961) - Dividend Irrelevance Theorem
- **Empirical Evidence**: S&P Dow Jones Indices research on Dividend Aristocrats
- **Key Finding**: No significant alpha from dividend growth alone after controlling for factors

### Key Findings
- S&P 500 Dividend Aristocrats (25+ years of increases) show lower volatility
- Dividend growth often proxy for quality and stability
- Behavioral preference for dividends creates persistent demand

### Implementation
```
Dividend Aristocrat Score = 
  Years of Consecutive Dividend Increases × 
  (Current Dividend / Dividend 5 Years Ago)^(1/5) - 1

Signal: Rank by dividend growth consistency and magnitude
Long: Top quintile by years of increases + growth rate
```

### Optimal Parameters
- **Lookback**: 10-25 years of dividend history
- **Rebalancing**: Quarterly or semi-annually
- **Holding Period**: 1-3 years (long-term factor)

### Sector Neutrality
- Not required; dividend aristocrats naturally sector-diverse
- Financials and utilities overrepresented

### Historical Sharpe
- Sharpe: 0.7-0.9 (lower than pure factors)
- Lower volatility than market
- Better drawdown characteristics

---

## 3. SHARE BUYBACK YIELD

### Academic Evidence
- **Key Paper**: Boudoukh et al. (2007) - "On the Importance of Measuring Payout Yield"
- **Key Paper**: Ikenberry, Lakonishok & Vermaelen (1995) - Market underreaction to open market share repurchases

### Key Findings
- Buyback yield = (Shares Repurchased × Price) / Market Cap
- Net buyback yield superior to gross (accounts for issuance)
- Market underreacts to repurchase announcements
- Signaling effect: Management buys when undervalued

### Implementation
```
Gross Buyback Yield = (Shares Repurchased × Avg Price) / Market Cap
Net Buyback Yield = (Shares Repurchased - Shares Issued) × Price / Market Cap

Signal: Z-score of Net Buyback Yield within sector
Long: Top quintile buyback yield
Short: Bottom quintile (net issuers)
```

### Optimal Parameters
- **Lookback**: 12 months of buyback activity
- **Rebalancing**: Quarterly
- **Holding Period**: 6-12 months

### Sector Neutrality
- REQUIRED: Buyback activity varies dramatically by sector
- Tech: High buybacks; Biotech: High issuance

### Historical Sharpe
- Gross Sharpe: 0.8-1.2
- Works best when combined with value metrics

---

## 4. REVISION MOMENTUM (EARNINGS ESTIMATE REVISIONS)

### Academic Evidence
- **Key Paper**: Givoly & Lakonishok (1979) - "The Information Content of Financial Analysts' Forecasts"
- **Key Paper**: Stickel (1991) - "Common Stock Returns Surrounding Earnings Forecast Revisions"

### Key Findings
- Analysts' earnings revisions contain significant information
- Upward revisions lead to positive returns; downward to negative
- Works better for smaller caps
- Persistence: 3-6 months

### Implementation
```
Revision Signal = 
  (% Analysts Upgrading - % Analysts Downgrading) / Total Analysts

OR

EPS Revision % = (Current Consensus - Prior Consensus) / |Prior Consensus|

Signal: Z-score of revision magnitude
Long: Top quintile positive revisions
Short: Bottom quintile negative revisions
```

### Optimal Parameters
- **Lookback**: 1-3 months of revision activity
- **Rebalancing**: Monthly
- **Holding Period**: 3-6 months

### Sector Neutrality
- RECOMMENDED: Analyst coverage varies by sector
- More effective in underfollowed sectors

### Historical Sharpe
- Gross Sharpe: 0.9-1.3
- Stronger in international markets

---

## 5. EARNINGS SURPRISE CONSISTENCY

### Academic Evidence
- **Related**: PEAD literature (Ball & Brown, Bernard & Thomas)
- **Key Insight**: Consistent beaters outperform sporadic beaters

### Key Findings
- Companies consistently beating earnings show persistent outperformance
- Reflects quality of management and business model
- Less risky than betting on turnaround stories

### Implementation
```
Surprise Consistency Score = 
  Count(Consecutive Quarters with Positive Surprise) × 
  Avg(Surprise Magnitude over last 8 quarters)

Signal: Weighted score of consistency × magnitude
Long: Top quintile consistent beaters
```

### Optimal Parameters
- **Lookback**: 8-12 quarters
- **Rebalancing**: Quarterly (after earnings season)
- **Holding Period**: 6-12 months

### Sector Neutrality
- REQUIRED

### Historical Sharpe
- Sharpe: 0.7-1.0

---

## 6. QUALITY METRICS (ROIC/ROE STABILITY, GROSS MARGIN TRENDS, FCF CONSISTENCY)

### Academic Evidence
- **Key Paper**: Novy-Marx (2013) - "The Other Side of Value: The Gross Profitability Premium"
- **Key Paper**: Asness, Frazzini, Pedersen (2014) - "Quality Minus Junk (QMJ)"
- **Key Paper**: Fama & French (2015) - Five-Factor Model (Profitability Factor RMW)

### Key Findings
- Gross profitability (Revenue - COGS) / Assets predicts returns
- ROIC stability indicates competitive advantage
- FCF consistency reflects earnings quality
- Quality is the "anti-value" - negatively correlated with value

### Implementation
```
Gross Profitability = (Revenue - COGS) / Total Assets
ROIC = EBIT / (Net Working Capital + Net Fixed Assets)
ROE Stability = 1 / σ(ROE over 5 years)
FCF Consistency = Count(Positive FCF over 5 years) / 5
Gross Margin Trend = (Current GM - GM 1yr ago) / |GM 1yr ago|

Quality Score = 
  0.25 × Z-score(Gross Profitability) +
  0.25 × Z-score(ROIC) +
  0.20 × Z-score(ROE Stability) +
  0.15 × Z-score(FCF Consistency) +
  0.15 × Z-score(Gross Margin Trend)
```

### Optimal Parameters
- **Lookback**: 3-5 years for stability measures
- **Rebalancing**: Annually (June) or semi-annually
- **Holding Period**: 1-3 years

### Sector Neutrality
- CRITICAL: Quality metrics vary significantly by sector
- Tech has different margin profiles than retail

### Historical Sharpe
- Gross Sharpe: 0.8-1.1
- Works best when combined with value (QARP)

---

## 7. ACCRUALS / EARNINGS QUALITY

### Academic Evidence
- **Key Paper**: Sloan (1996) - "Do Stock Prices Fully Reflect Information in Accruals and Cash Flows about Future Earnings?"
- **Key Finding**: Accrual component of earnings is less persistent than cash flow component

### Key Findings
- High accruals → lower future returns (earnings manipulation risk)
- Low accruals → higher future returns (earnings quality)
- Accrual anomaly weakened post-2002 but rebounded post-2008

### Implementation
```
Accruals = (ΔCurrent Assets - ΔCash) - 
           (ΔCurrent Liabilities - ΔDebt) - 
           Depreciation

Accruals/Assets = Accruals / Average Total Assets

Signal: Z-score of Accruals/Assets (lower is better)
Long: Bottom quintile (low accruals)
Short: Top quintile (high accruals)
```

### Optimal Parameters
- **Lookback**: Most recent fiscal year
- **Rebalancing**: Annually (after fiscal year ends)
- **Holding Period**: 1 year

### Sector Neutrality
- REQUIRED: Accrual patterns vary by industry

### Historical Sharpe
- Sharpe: 0.6-0.9 (weakened but still present)

---

## 8. VALUATION (VALUE COMPOSITES & SECTOR-NEUTRAL VALUE)

### Academic Evidence
- **Key Paper**: Fama & French (1992) - "The Cross-Section of Expected Stock Returns"
- **Key Paper**: Asness (1997) - "The Interaction of Value and Momentum Strategies"
- **Key Paper**: Novy-Marx (2013) - Value factor decomposition

### Key Findings
- Value premium: Low price-to-fundamental stocks outperform
- Composite value (multiple metrics) superior to single metric
- Sector-neutral value has higher Sharpe than raw value

### Implementation
```
Value Composite = Average Z-score of:
  - Book-to-Market
  - Earnings-to-Price
  - Sales-to-Enterprise Value
  - EBITDA-to-Enterprise Value
  - Cash Flow-to-Price

Sector-Neutral Value = Z-score(Value Composite within sector)

Signal: Sector-neutral value score
Long: Top quintile (cheapest)
Short: Bottom quintile (most expensive)
```

### Optimal Parameters
- **Lookback**: Most recent accounting data
- **Rebalancing**: Monthly or quarterly
- **Holding Period**: 1-3 years

### Sector Neutrality
- CRITICAL: Raw value has implicit sector bets
- Sector-neutral essential for pure value exposure

### Historical Sharpe
- Raw Value Sharpe: 0.4-0.6
- Sector-Neutral Value Sharpe: 0.6-0.8

---

## 9. GROWTH (REVENUE/EARNINGS GROWTH CONSISTENCY, OPERATING LEVERAGE)

### Academic Evidence
- **Key Paper**: Fama & French (2015) - Investment factor (CMA)
- **Key Paper**: Cooper, Gulen & Schill (2008) - Asset growth anomaly

### Key Findings
- Asset growth negatively predicts returns (investment factor)
- Revenue growth consistency positively predicts returns
- Operating leverage amplifies growth effects

### Implementation
```
Revenue Growth Consistency = 
  Count(Positive YoY Revenue Growth over 5 years) / 5

Earnings Growth Consistency = 
  Count(Positive YoY EPS Growth over 5 years) / 5

Operating Leverage = %ΔEBIT / %ΔRevenue

Growth Score = 
  0.4 × Z-score(Revenue Growth Consistency) +
  0.4 × Z-score(Earnings Growth Consistency) +
  0.2 × Z-score(Operating Leverage)
```

### Optimal Parameters
- **Lookback**: 5 years for consistency
- **Rebalancing**: Annually
- **Holding Period**: 1-2 years

### Sector Neutrality
- REQUIRED

### Historical Sharpe
- Sharpe: 0.5-0.8

---

## 10. SEASONALITY / CALENDAR EFFECTS

### Academic Evidence
- **Key Paper**: Rozeff & Kinney (1976) - January effect
- **Key Paper**: Heston & Sadka (2008) - Seasonalities in stock returns
- **Key Paper**: Hirshleifer, Jiang & Meng (2017) - Mood beta and seasonalities

### Key Findings
- January effect: Small caps outperform in January
- Turn-of-month effect: Higher returns around month-end
- Day-of-week: Monday lower, Friday higher
- Same-month return persistence across years

### Implementation
```
Seasonality Score = 
  Historical Avg Return for Current Month (past 20 years) +
  Historical Avg Return for Current Day-of-Week +
  Historical Avg Return for Days Around Month-End

Signal: Z-score of expected seasonal return
```

### Optimal Parameters
- **Lookback**: 20+ years for robust seasonal estimates
- **Rebalancing**: Daily or weekly
- **Holding Period**: Days to weeks

### Sector Neutrality
- Not typically applied

### Historical Sharpe
- Sharpe: 0.3-0.5 (lower but consistent)
- Transaction costs can erode profits

---

# PART 2: ADDITIONAL FACTORS WITH STRONG EMPIRICAL SUPPORT

## 11. MOMENTUM (PRICE MOMENTUM)

### Academic Evidence
- **Key Paper**: Jegadeesh & Titman (1993, 2001) - "Returns to Buying Winners and Selling Losers"
- **Key Paper**: Asness (1997) - Value and momentum interaction

### Rationale
- Behavioral: Underreaction to information, herding
- Structural: Slow information diffusion
- Risk-based: Momentum crashes during market stress

### Implementation
```
Momentum = Return(t-12 to t-1) [excluding most recent month]

Signal: Z-score of momentum within sector
Long: Top decile momentum
Short: Bottom decile momentum
```

### Optimal Parameters
- **Lookback**: 12 months (skip most recent month)
- **Rebalancing**: Monthly
- **Holding Period**: 3-12 months

### Historical Sharpe
- Sharpe: 0.5-0.8 (high volatility)

---

## 12. LOW VOLATILITY / LOW BETA

### Academic Evidence
- **Key Paper**: Blitz & van Vliet (2007) - "The Volatility Effect: Lower Risk Without Lower Return"
- **Key Paper**: Frazzini & Pedersen (2014) - "Betting Against Beta"

### Rationale
- Leverage constraints: Investors avoid low-beta stocks
- Benchmarking: Institutions favor high-beta stocks
- Lottery preferences: Retail investors prefer high volatility

### Implementation
```
Volatility = σ(Daily Returns over past 252 days) × √252
Beta = Cov(Stock, Market) / Var(Market)

Signal: Z-score of volatility (lower is better)
Long: Bottom quintile volatility
Short: Top quintile volatility
```

### Optimal Parameters
- **Lookback**: 1-3 years for volatility
- **Rebalancing**: Monthly
- **Holding Period**: 1 month

### Historical Sharpe
- Sharpe: 0.8-1.2

---

## 13. SHORT-TERM REVERSAL

### Academic Evidence
- **Key Paper**: Jegadeesh (1990) - Evidence of predictable behavior of security returns
- **Key Paper**: Lehmann (1990) - Fads, martingales, and market efficiency

### Rationale
- Liquidity provision: Compensation for providing liquidity
- Overreaction: Investors overreact to short-term news

### Implementation
```
Short-term Return = Return over past month

Signal: Z-score of prior month return
Long: Bottom decile (losers)
Short: Top decile (winners)
```

### Optimal Parameters
- **Lookback**: 1 month
- **Rebalancing**: Monthly
- **Holding Period**: 1 month

### Historical Sharpe
- Sharpe: 0.6-1.0 (declining due to HFT)

---

## 14. LONG-TERM REVERSAL

### Academic Evidence
- **Key Paper**: DeBondt & Thaler (1985) - "Does the Stock Market Overreact?"
- **Key Paper**: Jegadeesh & Titman (2001) - Long-term reversals of momentum

### Rationale
- Overreaction: Investors extrapolate past performance too far
- Tax-loss selling: January effect for losers

### Implementation
```
Long-term Return = Return over past 3-5 years

Signal: Z-score of long-term return
Long: Bottom decile (long-term losers)
Short: Top decile (long-term winners)
```

### Optimal Parameters
- **Lookback**: 3-5 years
- **Rebalancing**: Annually
- **Holding Period**: 3-5 years

### Historical Sharpe
- Sharpe: 0.4-0.6

---

## 15. PIOTROSKI F-SCORE

### Academic Evidence
- **Key Paper**: Piotroski (2000) - "Value Investing: The Use of Historical Financial Statement Information"

### Rationale
- Fundamental analysis: Simple score based on 9 criteria
- Quality within value: Separates true value from value traps

### Implementation
```
F-Score = Sum of 9 binary criteria:

Profitability (4 points):
  1. ROA > 0
  2. Operating Cash Flow > 0
  3. ROA(t) > ROA(t-1)
  4. Cash Flow > Net Income

Funding (3 points):
  5. Long-term Debt decreased
  6. Current Ratio increased
  7. No new shares issued

Efficiency (2 points):
  8. Gross Margin increased
  9. Asset Turnover increased

Signal: F-Score (0-9)
Long: F-Score >= 7
Short: F-Score <= 3
```

### Optimal Parameters
- **Lookback**: Most recent fiscal year
- **Rebalancing**: Annually
- **Holding Period**: 1 year

### Historical Sharpe
- Sharpe: 0.7-1.0 (within value universe)

---

## 16. INVESTMENT FACTOR (ASSET GROWTH)

### Academic Evidence
- **Key Paper**: Cooper, Gulen & Schill (2008) - "The Asset Growth Effect"
- **Key Paper**: Fama & French (2015) - CMA (Conservative Minus Aggressive)

### Rationale
- Overinvestment: High asset growth signals empire building
- Market timing: Companies invest when overvalued

### Implementation
```
Asset Growth = (Total Assets(t) - Total Assets(t-1)) / Total Assets(t-1)

Signal: Z-score of asset growth (lower is better)
Long: Bottom quintile (low asset growth)
Short: Top quintile (high asset growth)
```

### Optimal Parameters
- **Lookback**: Most recent fiscal year
- **Rebalancing**: Annually
- **Holding Period**: 1 year

### Historical Sharpe
- Sharpe: 0.6-0.9

---

## 17. GROSS PROFITABILITY

### Academic Evidence
- **Key Paper**: Novy-Marx (2013) - "The Other Side of Value: The Gross Profitability Premium"

### Rationale
- Clean profitability: Gross profit less subject to manipulation
- Quality signal: Sustainable competitive advantage

### Implementation
```
Gross Profitability = (Revenue - COGS) / Total Assets

Signal: Z-score of gross profitability
Long: Top quintile
Short: Bottom quintile
```

### Optimal Parameters
- **Lookback**: Most recent fiscal year
- **Rebalancing**: Annually (June)
- **Holding Period**: 1 year

### Historical Sharpe
- Sharpe: 0.7-1.0

---

# PART 3: FACTOR COMPOSITE FRAMEWORK

## Multi-Factor Portfolio Construction

### 1. Factor Weighting Approaches

#### Equal Weighting
```
composite_score = mean([value_z, quality_z, momentum_z, low_vol_z])
```

#### Risk-Parity Weighting
```
weights = 1 / factor_volatility
weights = weights / sum(weights)
composite_score = sum(weights * factor_z_scores)
```

#### Information Ratio Weighting
```
weights = factor_IR / sum(factor_IR)
composite_score = sum(weights * factor_z_scores)
```

#### Momentum-Adjusted Weighting
```
factor_momentum = rolling_return(factor, 12_months)
momentum_weight = max(0, factor_momentum)
weights = momentum_weight / sum(momentum_weight)
composite_score = sum(weights * factor_z_scores)
```

### 2. Factor Rotation Strategy

#### Macro-Based Rotation
```
if economic_regime == "expansion":
    weights = {'value': 0.3, 'momentum': 0.4, 'quality': 0.2, 'low_vol': 0.1}
elif economic_regime == "contraction":
    weights = {'value': 0.2, 'momentum': 0.1, 'quality': 0.3, 'low_vol': 0.4}
```

#### Factor Momentum Rotation
```
factor_12m_return = rolling_return(factor, 12_months)
positive_factors = factors[factor_12m_return > 0]
weights = equal_weight(positive_factors)
```

### 3. Factor Crowding Detection

#### Crowding Metrics
```
factor_aum_growth = pct_change(factor_ETF_AUM, 12_months)
factor_correlation = correlation(factor_returns, 6_months)
crowding_signal = factor_correlation > 0.8
dispersion = std(stock_returns_within_factor)
crowding_signal = dispersion < historical_10th_percentile
```

#### Crowding Response
```
if crowding_detected(factor):
    factor_weight *= 0.5
    other_factors_weight *= 1.2
```

---

# PART 4: TOP 10 FACTOR DEFINITIONS WITH FORMULAS

## FACTOR 1: VALUE COMPOSITE (SECTOR-NEUTRAL)

```python
def value_composite(ticker, date):
    bp = book_value / market_cap
    ep = earnings_ttm / market_cap
    sp = sales_ttm / enterprise_value
    ebitda_ev = ebitda_ttm / enterprise_value
    cf_p = operating_cf_ttm / market_cap

    bp_z = (bp - sector_mean(bp)) / sector_std(bp)
    ep_z = (ep - sector_mean(ep)) / sector_std(ep)
    sp_z = (sp - sector_mean(sp)) / sector_std(sp)
    ebitda_z = (ebitda_ev - sector_mean(ebitda_ev)) / sector_std(ebitda_ev)
    cf_z = (cf_p - sector_mean(cf_p)) / sector_std(cf_p)

    value_score = (bp_z + ep_z + sp_z + ebitda_z + cf_z) / 5
    return value_score
```

## FACTOR 2: QUALITY COMPOSITE (QMJ-STYLE)

```python
def quality_composite(ticker, date):
    gross_profitability = (revenue - cogs) / total_assets
    roic = ebit / (net_working_capital + net_fixed_assets)
    roe = net_income / book_equity
    roe_volatility = std(roe, 5_years)
    revenue_growth_5y = cagr(revenue, 5_years)
    debt_equity = total_debt / book_equity

    gp_z = z_score(gross_profitability)
    roic_z = z_score(roic)
    roe_z = z_score(roe)
    stability_z = -z_score(roe_volatility)
    growth_z = z_score(revenue_growth_5y)
    safety_z = -z_score(debt_equity)

    quality_score = (
        0.25 * gp_z + 0.20 * roic_z + 0.15 * roe_z +
        0.15 * stability_z + 0.10 * growth_z + 0.15 * safety_z
    )
    return quality_score
```

## FACTOR 3: MOMENTUM (12-MONTH)

```python
def momentum_score(ticker, date):
    momentum_return = price(date - 1_month) / price(date - 12_months) - 1
    volatility = std(daily_returns, 252_days) * sqrt(252)
    risk_adj_momentum = momentum_return / volatility
    momentum_z = (risk_adj_momentum - sector_mean(risk_adj_momentum)) / sector_std(risk_adj_momentum)
    return momentum_z
```

## FACTOR 4: LOW VOLATILITY

```python
def low_volatility_score(ticker, date):
    daily_returns = get_daily_returns(ticker, date - 252_days, date)
    volatility = std(daily_returns) * sqrt(252)
    market_returns = get_market_returns(date - 252_days, date)
    beta = covariance(daily_returns, market_returns) / variance(market_returns)
    residuals = daily_returns - beta * market_returns
    idio_vol = std(residuals) * sqrt(252)
    vol_score = -0.6 * z_score(volatility) - 0.4 * z_score(idio_vol)
    return vol_score
```

## FACTOR 5: EARNINGS MOMENTUM (REVISIONS)

```python
def earnings_momentum_score(ticker, date):
    current_eps_consensus = mean(analyst_eps_estimates)
    prior_eps_consensus = mean(analyst_eps_estimates_1m_ago)
    eps_revision = (current_eps_consensus - prior_eps_consensus) / abs(prior_eps_consensus)
    upgrades = count(analyst_revisions > 0)
    downgrades = count(analyst_revisions < 0)
    revision_breadth = (upgrades - downgrades) / total_analysts
    surprise_history = [eps_actual - eps_estimate for last 8_quarters]
    surprise_consistency = count(surprise_history > 0) / 8

    em_score = (
        0.5 * z_score(eps_revision) +
        0.3 * z_score(revision_breadth) +
        0.2 * z_score(surprise_consistency)
    )
    return em_score
```

## FACTOR 6: PROFITABILITY (GROSS PROFITABILITY)

```python
def profitability_score(ticker, date):
    gross_profit = revenue - cogs
    gross_profitability = gross_profit / total_assets
    operating_profitability = operating_income / total_assets
    cash_profitability = operating_cash_flow / total_assets

    gp_z = (gross_profitability - sector_mean(gross_profitability)) / sector_std(gross_profitability)
    op_z = (operating_profitability - sector_mean(operating_profitability)) / sector_std(operating_profitability)
    cp_z = (cash_profitability - sector_mean(cash_profitability)) / sector_std(cash_profitability)

    profitability_score = (gp_z + op_z + cp_z) / 3
    return profitability_score
```

## FACTOR 7: INVESTMENT (ASSET GROWTH)

```python
def investment_score(ticker, date):
    asset_growth = (total_assets - total_assets_lag) / total_assets_lag
    capex_growth = (capex - capex_lag) / capex_lag
    inventory_growth = (inventory - inventory_lag) / inventory_lag
    total_investment = asset_growth + 0.5 * capex_growth + 0.3 * inventory_growth
    investment_score = -z_score(total_investment)
    return investment_score
```

## FACTOR 8: EARNINGS QUALITY (ACCRUALS)

```python
def earnings_quality_score(ticker, date):
    delta_current_assets = current_assets - current_assets_lag
    delta_cash = cash - cash_lag
    delta_current_liab = current_liabilities - current_liabilities_lag
    delta_debt = short_term_debt - short_term_debt_lag
    delta_taxes = taxes_payable - taxes_payable_lag

    accruals = (delta_current_assets - delta_cash) - (delta_current_liab - delta_debt - delta_taxes) - depreciation
    accruals_assets = accruals / ((total_assets + total_assets_lag) / 2)
    cash_earnings_ratio = operating_cash_flow / net_income

    eq_score = -0.7 * z_score(accruals_assets) + 0.3 * z_score(cash_earnings_ratio)
    return eq_score
```

## FACTOR 9: PIOTROSKI F-SCORE

```python
def piotroski_f_score(ticker, date):
    score = 0
    if roa > 0: score += 1
    if operating_cash_flow > 0: score += 1
    if roa > roa_lag: score += 1
    if operating_cash_flow > net_income: score += 1
    if long_term_debt < long_term_debt_lag: score += 1
    if current_ratio > current_ratio_lag: score += 1
    if shares_outstanding <= shares_outstanding_lag: score += 1

    gross_margin = (revenue - cogs) / revenue
    gross_margin_lag = (revenue_lag - cogs_lag) / revenue_lag
    if gross_margin > gross_margin_lag: score += 1

    asset_turnover = revenue / total_assets
    asset_turnover_lag = revenue_lag / total_assets_lag
    if asset_turnover > asset_turnover_lag: score += 1

    return score
```

## FACTOR 10: SHAREHOLDER YIELD (BUYBACK + DIVIDEND)

```python
def shareholder_yield_score(ticker, date):
    dividend_yield = dividends_paid_12m / market_cap
    shares_change = (shares_outstanding_lag - shares_outstanding) / shares_outstanding_lag
    buyback_yield = shares_change * price
    net_payout_yield = dividend_yield + buyback_yield
    fcf_yield = free_cash_flow / market_cap
    payout_ratio = dividends_paid_12m / net_income
    sustainable = payout_ratio < 0.8

    sy_score = (
        0.3 * z_score(dividend_yield) +
        0.4 * z_score(buyback_yield) +
        0.3 * z_score(fcf_yield)
    )

    if not sustainable: sy_score *= 0.5
    return sy_score
```

---

# PART 5: SUMMARY TABLE OF FACTOR CHARACTERISTICS

| Factor | Academic Source | Lookback | Rebalancing | Sharpe (Gross) | Sector Neutral | Best Regime |
|--------|-----------------|----------|-------------|----------------|----------------|-------------|
| Value Composite | Fama-French (1992) | Current | Monthly | 0.6-0.8 | REQUIRED | Recovery |
| Quality (QMJ) | Asness (2014) | 5 years | Annual | 0.8-1.1 | REQUIRED | Recession |
| Momentum | Jegadeesh-Titman (1993) | 12 months | Monthly | 0.5-0.8 | Recommended | Trending |
| Low Volatility | Blitz-van Vliet (2007) | 1-3 years | Monthly | 0.8-1.2 | Optional | Bear Market |
| Earnings Momentum | Stickel (1991) | 1-3 months | Monthly | 0.9-1.3 | Recommended | Expansion |
| Gross Profitability | Novy-Marx (2013) | Current | Annual | 0.7-1.0 | REQUIRED | All |
| Investment (CMA) | Fama-French (2015) | Current | Annual | 0.6-0.9 | REQUIRED | Late Cycle |
| Earnings Quality | Sloan (1996) | Current | Annual | 0.6-0.9 | REQUIRED | All |
| Piotroski F-Score | Piotroski (2000) | Current | Annual | 0.7-1.0 | Recommended | Value |
| Shareholder Yield | Boudoukh (2007) | 12 months | Quarterly | 0.8-1.2 | REQUIRED | All |
| PEAD | Ball-Brown (1968) | 1 quarter | Event | 1.0-1.5 | REQUIRED | Earnings Season |
| Short-term Reversal | Jegadeesh (1990) | 1 month | Monthly | 0.6-1.0 | Recommended | High Vol |
| Long-term Reversal | DeBondt-Thaler (1985) | 3-5 years | Annual | 0.4-0.6 | Recommended | Contrarian |

---

# PART 6: REGIME DEPENDENCIES

## Factor Performance by Economic Regime

### Expansion (Early)
- **Best**: Momentum, Earnings Momentum, Growth
- **Worst**: Value, Low Volatility

### Expansion (Late)
- **Best**: Quality, Shareholder Yield, Investment
- **Worst**: High Beta, Small Cap

### Contraction (Early)
- **Best**: Low Volatility, Quality, Defensive
- **Worst**: Momentum, Cyclical Value

### Contraction (Late) / Recovery
- **Best**: Value, Small Cap, Long-term Reversal
- **Worst**: Momentum, Quality (sometimes)

### High Inflation
- **Best**: Value, Low Duration (short-term earnings)
- **Worst**: Growth, Long Duration

### Low Interest Rates
- **Best**: Growth, Momentum, Quality
- **Worst**: Value (sometimes)

---

# PART 7: IMPLEMENTATION BEST PRACTICES

## 1. Data Quality
- Use point-in-time data to avoid look-ahead bias
- Account for restatements
- Handle missing data appropriately (industry median fill)

## 2. Sector Neutrality
- Always sector-neutralize for cross-sectional factors
- Use GICS or proprietary sector classifications
- Consider industry-level neutralization for more granularity

## 3. Risk Management
- Target factor neutrality (beta = 0)
- Control for unintended exposures (size, industry)
- Implement maximum position limits

## 4. Transaction Costs
- Estimate costs before trading
- Use volume-weighted signals for larger positions
- Consider rebalancing frequency vs. alpha decay

## 5. Capacity Constraints
- Monitor AUM in factor strategies
- Be aware of crowding in popular factors
- Have capacity estimates for each factor

---

## REFERENCES

1. Ball, R. & Brown, P. (1968). "An Empirical Evaluation of Accounting Income Numbers." Journal of Accounting Research.
2. Bernard, V.L. & Thomas, J.K. (1989). "Post-Earnings-Announcement Drift." Journal of Accounting Research.
3. Fama, E.F. & French, K.R. (1992). "The Cross-Section of Expected Stock Returns." Journal of Finance.
4. Fama, E.F. & French, K.R. (2015). "A Five-Factor Asset Pricing Model." Journal of Financial Economics.
5. Jegadeesh, N. & Titman, S. (1993). "Returns to Buying Winners and Selling Losers." Journal of Finance.
6. Asness, C.S. (1997). "The Interaction of Value and Momentum Strategies." Journal of Portfolio Management.
7. Asness, C.S., Frazzini, A., & Pedersen, L.H. (2014). "Quality Minus Junk." AQR Working Paper.
8. Novy-Marx, R. (2013). "The Other Side of Value: The Gross Profitability Premium." Journal of Financial Economics.
9. Sloan, R. (1996). "Do Stock Prices Fully Reflect Information in Accruals?" The Accounting Review.
10. Piotroski, J. (2000). "Value Investing: The Use of Historical Financial Statement Information." Journal of Accounting Research.
11. Blitz, D. & van Vliet, P. (2007). "The Volatility Effect." Journal of Portfolio Management.
12. Frazzini, A. & Pedersen, L.H. (2014). "Betting Against Beta." Journal of Financial Economics.
13. DeBondt, W.F.M. & Thaler, R. (1985). "Does the Stock Market Overreact?" Journal of Finance.
14. Cooper, M., Gulen, H., & Schill, M. (2008). "The Asset Growth Effect." Journal of Finance.
15. Boudoukh, J., et al. (2007). "On the Importance of Measuring Payout Yield." Journal of Finance.
