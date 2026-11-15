# Professional Investor Metrics Reference
## A Structured Guide to Strategy Evaluation Across Six Investment Perspectives

**Date:** 2026-11-15
**Purpose:** Reference document for evaluating trading strategies and investment opportunities through the lens of six distinct professional investor types.

---

## Table of Contents

1. [Quantitative Hedge Fund (Renaissance-style)](#1-quantitative-hedge-fund-renaissance-style)
2. [Mutual Fund Manager](#2-mutual-fund-manager)
3. [Bank Prop Trader](#3-bank-prop-trader)
4. [Retail-Facing Robo-Advisor](#4-retail-facing-robo-advisor)
5. [Crypto Fund](#5-crypto-fund)
6. [Commodity Trading Advisor (CTA)](#6-commodity-trading-advisor-cta)
7. [Cross-Cutting Pitfalls](#7-cross-cutting-pitfalls)
8. [Quick Reference Tables](#8-quick-reference-tables)

---

## 1. Quantitative Hedge Fund (Renaissance-style)

### Investment Context
Quantitative hedge funds (e.g., Renaissance Technologies, Two Sigma, Citadel) prioritize statistically robust, capacity-constrained strategies that generate alpha through systematic edge. Their focus is on **risk-adjusted returns**, **drawdown control**, and **scalability**.

### Top 5 Most Important Metrics

#### 1.1 Sharpe Ratio
**Definition:** Risk-adjusted return measuring excess return per unit of total volatility.
- **Formula:** (Rp - Rf) / sigma_p
- **Good:** > 2.0 (exceptional), > 1.5 (strong)
- **Acceptable:** 1.0 - 1.5
- **Poor:** < 1.0
- **Context:** Renaissance's Medallion Fund reportedly achieved Sharpe ratios above 3.0 over multi-decade periods. For a quant fund, a Sharpe below 1.0 is generally not viable for external capital.

#### 1.2 Sortino Ratio
**Definition:** Risk-adjusted return using only downside deviation (penalizes harmful volatility, not upside volatility).
- **Formula:** (Rp - Rf) / sigma_d (downside deviation)
- **Good:** > 2.5
- **Acceptable:** 1.5 - 2.5
- **Poor:** < 1.0
- **Why it matters:** Quant strategies often have asymmetric return profiles. A strategy with frequent small gains and rare large losses may show a decent Sharpe but a poor Sortino.

#### 1.3 Deflated Sharpe Ratio (DSR)
**Definition:** Adjusts the Sharpe ratio to account for multiple testing bias, non-normality, and data mining. Developed by Marcos Lopez de Prado.
- **Formula:** Adjusts SR for number of trials, skewness, and kurtosis.
- **Good:** DSR > 0.95 (high confidence the strategy is not a statistical fluke)
- **Acceptable:** 0.50 - 0.95
- **Poor:** < 0.50
- **Why it matters:** In a quant fund running hundreds or thousands of backtests, a "significant" Sharpe of 1.5 may actually have a very high probability of being a false discovery. DSR is the gatekeeper metric.

#### 1.4 Maximum Drawdown (MDD)
**Definition:** The largest peak-to-trough decline in portfolio value before a new peak is achieved.
- **Formula:** (Trough Value - Peak Value) / Peak Value
- **Good:** < 10% annualized (or < 5% for low-volatility strategies)
- **Acceptable:** 10% - 20%
- **Poor:** > 25%
- **Why it matters:** MDD is the most intuitive measure of capital preservation. Many quant funds have hard stops at 10-15% MDD. It also drives client redemptions more than any other metric.

#### 1.5 Capacity
**Definition:** The amount of capital a strategy can deploy before returns degrade due to market impact, liquidity constraints, or signal decay.
- **Good:** > $1B with < 100bps annual return degradation
- **Acceptable:** $100M - $1B with manageable degradation
- **Poor:** < $100M or rapid degradation with scale
- **Why it matters:** A strategy with a Sharpe of 2.0 but capacity of only $50M is valuable but not a franchise builder. The interaction between Sharpe and capacity determines the total economic value of a strategy.

### Key Metric Interactions
- **High Sharpe + Low Capacity = Boutique strategy.** May be valuable for internal capital or a small fund, but cannot support a large AUM business.
- **High Sharpe + High MDD = Hidden tail risk.** The "nickels in front of a steamroller" problem. Strategies selling options or crash insurance can show high Sharpes until they don't.
- **High DSR + Low Sharpe = True but weak edge.** The strategy is statistically real but may not clear cost-of-capital hurdles.

### Common Pitfalls
1. **Sharpe manipulation:** Managers can inflate Sharpe by using longer sampling intervals (annual vs. monthly), which lowers measured volatility.
2. **Cherry-picked lookback:** Selecting the most favorable historical period can distort all metrics.
3. **Ignoring non-normality:** Standard deviation assumes normal distributions. Quant strategies with tail risk will understate true risk.
4. **Capacity blindness:** Backtests assume frictionless execution. Real-world slippage and market impact often destroy edge at scale.

---

## 2. Mutual Fund Manager

### Investment Context
Mutual fund managers operate within a benchmark-relative framework. Their goal is to **outperform a stated benchmark** (e.g., S&P 500) while managing tracking error and keeping costs reasonable for retail investors.

### Top 5 Most Important Metrics

#### 2.1 Alpha (vs. Benchmark)
**Definition:** Excess return relative to a benchmark, adjusted for systematic risk (beta).
- **Formula:** Rp - [Rf + beta_p * (Rm - Rf)]
- **Good:** > 3% annualized (gross of fees)
- **Acceptable:** 0% - 3%
- **Poor:** < 0% (negative alpha after fees is the norm for most active funds)
- **Context:** Studies show fewer than 10% of active mutual funds generate positive alpha over 10+ years after fees.

#### 2.2 Information Ratio (IR)
**Definition:** Measures consistency of excess returns relative to tracking error.
- **Formula:** (Rp - Rb) / Tracking Error
- **Good:** > 0.70 (top-quartile active manager)
- **Acceptable:** 0.40 - 0.70
- **Poor:** < 0.30
- **Context:** A manager who beats the benchmark by 2% with 4% tracking error has an IR of 0.50. A manager who beats by 5% with 15% tracking error has an IR of 0.33 — worse risk-adjusted skill despite higher raw returns.

#### 2.3 Tracking Error
**Definition:** Standard deviation of the difference between portfolio and benchmark returns.
- **Good:** 1% - 3% (for core strategies), 4% - 8% (for concentrated/active strategies)
- **Acceptable:** Matches stated mandate
- **Poor:** Deviates significantly from mandate (a "closet indexer" with high fees and low tracking error is a poor deal)
- **Context:** Low tracking error (< 2%) with high fees is a red flag — the investor is paying active fees for passive-like deviation.

#### 2.4 Upside / Downside Capture
**Definition:** Upside capture measures participation in benchmark gains; downside capture measures participation in benchmark losses.
- **Good Upside:** > 100% (captures more than benchmark in up markets)
- **Good Downside:** < 100% (loses less than benchmark in down markets)
- **Acceptable:** Upside > 90%, Downside < 110%
- **Poor:** Downside > 120% or Upside < 80%
- **Ideal combination:** Upside capture > 100% + Downside capture < 100% (rare and valuable)

#### 2.5 Expense Ratio
**Definition:** Annual fee charged as a percentage of assets under management.
- **Good:** < 0.50% for active equity, < 0.20% for passive/index
- **Acceptable:** 0.50% - 1.00%
- **Poor:** > 1.50% (especially if alpha is negative or IR is low)
- **Context:** Expense ratio is the only guaranteed drag on returns. A fund charging 1.5% must generate 150bps of alpha just to break even versus a zero-cost alternative.

### Key Metric Interactions
- **High Alpha + High Tracking Error + Low IR = Inconsistent outperformance.** The manager may have had one or two big years but lacks reliable skill.
- **Low Expense Ratio + Low Tracking Error = Closet indexing.** If tracking error is < 1.5% and fees are > 0.75%, investors would be better off in an index ETF.
- **Downside Capture < Upside Capture = Asymmetric skill.** The holy grail of mutual fund management — participating fully in gains while protecting in drawdowns.

### Common Pitfalls
1. **Benchmark mismatch:** A small-cap manager benchmarking to the S&P 500 can show spurious alpha from style effects alone.
2. **Survivorship bias:** Databases only show surviving funds. The true distribution of alpha is worse than reported.
3. **Fee blindness:** Gross alpha may look attractive, but net-of-fee alpha is what matters to investors.
4. **Style drift:** A manager drifting into higher-beta stocks to chase returns will show alpha during bull markets but expose investors to unintended risk.

---

## 3. Bank Prop Trader

### Investment Context
Proprietary traders at banks trade the firm's own capital with tight risk limits, regulatory capital requirements, and daily P&L scrutiny. Their focus is on **short-term risk control**, **tail risk management**, and **capital efficiency**.

### Top 5 Most Important Metrics

#### 3.1 Value at Risk (VaR)
**Definition:** Estimates the maximum potential loss over a specific time period at a given confidence level.
- **Example:** A 95% one-day VaR of $1M means there is a 5% chance of losing more than $1M in a single day.
- **Good:** Lower is better, but must be calibrated to strategy. A market-making desk might target < $5M daily VaR.
- **Acceptable:** Within firm-wide risk appetite and regulatory limits.
- **Poor:** Exceeds limits or is poorly calibrated.
- **Context:** VaR is widely used but flawed — it says nothing about the magnitude of losses *beyond* the threshold.

#### 3.2 Conditional Value at Risk (CVaR) / Expected Shortfall
**Definition:** The average loss in the tail — i.e., the expected loss *given* that the VaR threshold is breached.
- **Good:** CVaR is not dramatically larger than VaR (indicates thin tails)
- **Acceptable:** CVaR / VaR ratio < 1.5x
- **Poor:** CVaR is 2-3x VaR (indicates severe tail risk)
- **Why it matters:** CVaR addresses the key weakness of VaR. During the 2008 crisis, firms relying solely on VaR underestimated true risk because they ignored the shape of the tail.

#### 3.3 Daily P&L Volatility
**Definition:** Standard deviation of daily profit and loss.
- **Good:** Stable, predictable range. No outsized daily swings.
- **Acceptable:** Volatility in line with risk budget.
- **Poor:** Sudden spikes in daily volatility, especially negative skew.
- **Context:** Prop traders live and die by daily P&L. Large daily losses trigger immediate review, position reduction, or termination.

#### 3.4 Hit Ratio (Win Rate)
**Definition:** Percentage of trading days or individual trades that are profitable.
- **Good:** > 55% for directional strategies, > 60% for market-making
- **Acceptable:** 50% - 55%
- **Poor:** < 45% (unless average win / average loss ratio is very high)
- **Context:** A low hit ratio with high average wins can still be profitable (trend-following), but it is psychologically and institutionally difficult to sustain.

#### 3.5 Kelly Criterion (Fractional)
**Definition:** Formula for optimal bet sizing to maximize long-term wealth growth.
- **Formula:** K% = W - [(1 - W) / R] where W = win probability, R = win/loss ratio
- **Good:** Position sizing in the 0.10x - 0.25x of full Kelly (fractional Kelly is standard practice)
- **Acceptable:** < 0.50x Kelly
- **Poor:** > 0.50x Kelly or no Kelly-based sizing framework
- **Why it matters:** Full Kelly is too aggressive and leads to massive drawdowns. Prop traders typically use 1/4 to 1/10 Kelly to balance growth with survival.

### Key Metric Interactions
- **Low VaR + High CVaR = Hidden tail risk.** The trader appears safe on a day-to-day basis but faces catastrophic losses in extreme events.
- **High Hit Ratio + Negative Skew = Short gamma profile.** The trader is likely collecting premiums or providing liquidity — profitable until a dislocation occurs.
- **Kelly sizing + Regulatory capital constraints = Optimal but bounded.** Even if Kelly suggests a large position, regulatory capital rules (Basel III/IV) may cap exposure.

### Common Pitfalls
1. **VaR false security:** VaR does not measure worst-case loss — only a threshold. A 99% VaR of $10M is breached 2-3 times per year.
2. **Procyclical risk:** VaR models based on recent low-volatility periods underestimate risk just before crises.
3. **Over-leverage near Kelly:** Full Kelly bet sizing maximizes expected log-wealth but produces 50%+ drawdowns with high probability.
4. **Ignoring correlation breakdown:** In crises, correlations approach 1.0, rendering diversification and VaR models useless.

---

## 4. Retail-Facing Robo-Advisor

### Investment Context
Robo-advisors (e.g., Betterment, Wealthfront, Schwab Intelligent Portfolios) serve retail clients with automated, low-cost portfolio construction. Their success metrics blend **investment outcomes** with **behavioral** and **business** metrics.

### Top 5 Most Important Metrics

#### 4.1 Time-Weighted Return (TWR)
**Definition:** Measures compound growth of a portfolio, eliminating the distorting effects of cash flows in and out.
- **Good:** Matches or exceeds benchmark-appropriate passive allocation
- **Acceptable:** Within 50bps of target allocation benchmark
- **Poor:** Underperforms a simple ETF portfolio by > 100bps after fees
- **Why it matters:** TWR isolates the advisor's investment decisions from the client's bad timing of contributions/withdrawals.

#### 4.2 Risk-Adjusted Return (Sharpe of Client Portfolios)
**Definition:** Sharpe ratio of the overall client base's portfolio returns.
- **Good:** > 0.80 for a 60/40 allocation, > 1.0 for more conservative allocations
- **Acceptable:** 0.50 - 0.80
- **Poor:** < 0.50
- **Context:** Robo-advisors typically construct diversified ETF portfolios. The Sharpe should reflect the benefits of diversification, rebalancing, and tax-loss harvesting.

#### 4.3 Behavioral Alpha (or "Vanguard Advisor's Alpha")
**Definition:** The value added by preventing clients from making behavioral mistakes (panic selling, performance chasing, market timing).
- **Estimated Value:** 1.5% - 2.0% annualized according to Vanguard research
- **Good:** Clients stick to plan through volatility; rebalancing is systematic, not emotional
- **Poor:** Clients abandon strategy during drawdowns, locking in losses
- **Measurement:** Compare dollar-weighted returns (irradiated by client flows) to time-weighted returns. The gap is behavioral drag.

#### 4.4 Client Retention Rate
**Definition:** Percentage of clients who remain with the service over a given period.
- **Good:** > 95% annually
- **Acceptable:** 90% - 95%
- **Poor:** < 85%
- **Why it matters:** Acquisition costs for retail clients are high. Retention is the key driver of lifetime value (LTV) and unit economics.

#### 4.5 Maximum Drawdown (Client-Facing)
**Definition:** Largest decline from peak to trough, heavily influencing client satisfaction and retention.
- **Good:** < 15% for balanced portfolios
- **Acceptable:** 15% - 25% (during severe bear markets)
- **Poor:** > 25% or drawdowns that exceed client risk-tolerance questionnaire thresholds
- **Context:** Robo-advisors live or die by managing expectations. A client who indicated "moderate" risk tolerance but experiences a 30% drawdown will churn, regardless of long-term returns.

### Key Metric Interactions
- **High TWR + Low Dollar-Weighted Return = Behavioral failure.** The advisor's strategy is sound, but clients are buying high and selling low.
- **Low Fees + Tax-Loss Harvesting + Rebalancing = Structural alpha.** These are the three main sources of robo-advisor value beyond simple ETF allocation.
- **Low MDD + High Retention = Business success.** Clients don't leave because of low returns — they leave because of large unexpected losses.

### Common Pitfalls
1. **Focusing only on TWR:** The advisor may show strong TWR while clients actually lose money due to poor timing.
2. **Over-optimizing for Sharpe:** Excessive bond allocations can inflate Sharpe but produce insufficient long-term returns for younger clients.
3. **Ignoring tax drag:** Pre-tax returns look fine, but after-tax returns may underperform a simple buy-and-hold strategy without tax management.
4. **One-size-fits-all risk profiling:** A questionnaire-based risk score may not capture true client behavior under stress.

---

## 5. Crypto Fund

### Investment Context
Crypto funds operate in a 24/7, highly volatile market with unique risks: exchange counterparty risk, regulatory uncertainty, and extreme correlation to BTC/ETH during risk-off events.

### Top 5 Most Important Metrics

#### 5.1 Beta to BTC/ETH
**Definition:** Sensitivity of fund returns to Bitcoin and Ethereum returns.
- **Good:** Beta < 0.50 for a market-neutral or alpha strategy; Beta ~0.80 - 1.0 for a long-only beta product
- **Acceptable:** Matches stated mandate
- **Poor:** Beta > 1.2 for non-leveraged funds (excessive systematic risk) or Beta significantly different from stated strategy
- **Why it matters:** Many "alpha" crypto funds are simply levered beta. A fund claiming to generate alpha but with a 0.90 BTC beta is mostly riding the market.

#### 5.2 Alpha Generation (Residual Return)
**Definition:** Return unexplained by BTC/ETH beta — i.e., true idiosyncratic skill.
- **Good:** > 10% annualized alpha in a volatile market
- **Acceptable:** 0% - 10%
- **Poor:** Negative alpha (underperforming a simple BTC/ETH hold)
- **Context:** In crypto, a simple 50/50 BTC/ETH portfolio is the baseline. Any fund charging 2/20 must beat this benchmark on a risk-adjusted basis.

#### 5.3 Downside Deviation / Sortino Ratio
**Definition:** Measures volatility of negative returns only; Sortino ratio is the risk-adjusted return using downside deviation.
- **Good Sortino:** > 2.0
- **Acceptable:** 1.0 - 2.0
- **Poor:** < 1.0
- **Why it matters:** Crypto markets have massive upside volatility that punishes Sharpe ratios. Sortino is more appropriate for assessing whether a strategy manages downside well.

#### 5.4 Recovery Time (Time to New High)
**Definition:** Average or maximum time required to recover from a drawdown to a new equity high.
- **Good:** < 3 months for drawdowns < 20%
- **Acceptable:** 3 - 6 months
- **Poor:** > 12 months or never recovering (common in crypto bear markets)
- **Context:** Crypto cycles are violent and fast. A fund that takes 18 months to recover from a 50% drawdown may miss the entire next bull cycle.

#### 5.5 Slippage-Adjusted Returns
**Definition:** Returns adjusted for execution costs, including bid-ask spreads, market impact, and exchange fees.
- **Good:** Slippage < 10bps per trade for liquid pairs; < 50bps for illiquid altcoins
- **Acceptable:** Slippage consistent with backtest assumptions
- **Poor:** Actual slippage is 2-3x backtest assumptions, erasing edge
- **Why it matters:** Crypto markets are fragmented and illiquid outside of top-20 tokens. Backtests assuming Coinbase Pro fills on low-cap tokens are fantasy.

### Key Metric Interactions
- **High Alpha + High BTC Beta = Alpha may be illusory.** The alpha may simply be loading on an unobserved risk factor (e.g., DeFi yield, leverage, or small-cap crypto beta).
- **High Sharpe + Long Recovery Time = Misleading metric.** A strategy that makes steady gains then crashes 70% can have a decent long-term Sharpe but unacceptable client experience.
- **Low Slippage in Backtest + High Slippage in Live = Strategy decay.** The edge exists on paper but not in practice.

### Common Pitfalls
1. **Benchmark omission:** Crypto funds often report absolute returns without comparing to BTC/ETH buy-and-hold, making mediocre performance look exceptional.
2. **Exchange risk blindness:** A fund can show great returns but hold assets on FTX-equivalent exchanges. Counterparty risk is not captured in standard performance metrics.
3. **Survivorship bias in altcoins:** Backtests assume you could have held the winners and avoided the zeros. In reality, most altcoins go to zero.
4. **Ignoring funding rates:** Perpetual futures funding rates can be a massive drag (or boost) that isn't captured in spot backtests.

---

## 6. Commodity Trading Advisor (CTA)

### Investment Context
CTAs manage futures-based strategies, often trend-following, across diversified asset classes (commodities, rates, FX, equities). They are judged on **absolute returns**, **crisis alpha**, and **per-trade economics**.

### Top 5 Most Important Metrics

#### 6.1 MAR Ratio
**Definition:** Return over Maximum Drawdown — annualized return divided by maximum drawdown.
- **Formula:** CAGR / |Maximum Drawdown|
- **Good:** > 1.0
- **Acceptable:** 0.50 - 1.0
- **Poor:** < 0.50
- **Context:** A MAR of 1.0 means the fund generates annual returns equal to its worst drawdown. This is the classic CTA efficiency benchmark.

#### 6.2 Profit Factor
**Definition:** Gross profits divided by gross losses over a period.
- **Formula:** Sum of winning trade profits / Sum of losing trade losses
- **Good:** > 1.5
- **Acceptable:** 1.2 - 1.5
- **Poor:** < 1.2
- **Why it matters:** Profit factor directly answers: "Does the strategy make more on winners than it loses on losers?" A PF of 1.0 is breakeven before costs.

#### 6.3 Win Rate + Average Win/Loss Ratio
**Definition:** Percentage of winning trades and the ratio of average winner to average loser.
- **Good:** Win rate > 40% with average win / average loss > 2.0 (trend-following profile)
- **Acceptable:** Win rate > 35% with ratio > 1.5
- **Poor:** Win rate < 30% with ratio < 1.0
- **Context:** CTAs typically have low win rates (35-45%) but large average wins. A high win rate with small wins and large losses indicates a mean-reversion or short-gamma profile, which is dangerous in trending markets.

#### 6.4 Expectancy
**Definition:** Expected value (in dollars or R-multiples) of a single trade.
- **Formula:** (Win% * Avg Win) - (Loss% * Avg Loss)
- **Good:** > 0.5 R per trade (positive expectancy)
- **Acceptable:** > 0 R per trade
- **Poor:** < 0 R per trade (negative expectancy — the strategy loses money over time)
- **Why it matters:** Expectancy tells you whether the edge is real. A strategy can have a 30% win rate and still be highly profitable if expectancy is positive.

#### 6.5 Regime-Adjusted Sharpe
**Definition:** Sharpe ratio calculated separately for different market regimes (trending, mean-reverting, high vol, low vol) and then weighted or reported distinctly.
- **Good:** Positive Sharpe across all major regimes, or strongly positive in the fund's target regime
- **Acceptable:** Positive in target regime, neutral in others
- **Poor:** Negative in the fund's stated target regime
- **Why it matters:** A trend-following CTA should show its best Sharpe in strong trending regimes. If it performs poorly during trends, the strategy is broken or mislabeled.

### Key Metric Interactions
- **High MAR + Low Profit Factor = Drawdown luck.** The fund may have avoided a major drawdown historically, but the trade-level economics suggest it is vulnerable.
- **Low Win Rate + High Expectancy = Trend-following profile.** This is the classic CTA signature. It requires psychological and institutional tolerance for frequent small losses.
- **Positive Sharpe overall + Negative Sharpe in crises = Failed value proposition.** CTAs are marketed as "crisis alpha" providers. If they crash when equities crash, they fail their core mandate.

### Common Pitfalls
1. **Overfitting to historical trends:** Futures markets have changed. The 1970s-2000s saw strong sustained trends in commodities and rates. Post-2010 markets have been noisier.
2. **Ignoring roll yield:** Backtests on continuous contracts may not account for contango/backwardation costs in futures rolling.
3. **Volatility targeting illusion:** Targeting constant volatility can mask deteriorating edge by reducing position sizes as volatility rises.
4. **Sharpe ratio decay at scale:** Many CTA strategies are capacity-constrained. A small managed account may show great returns that cannot be replicated at $1B AUM.

---

## 7. Cross-Cutting Pitfalls

### Pitfalls That Affect All Perspectives

1. **Multiple Testing / Data Mining Bias**
   - Running 1,000 backtests and selecting the best one guarantees a high Sharpe by chance alone. Use DSR, Bonferroni corrections, or out-of-sample testing.

2. **Look-Ahead Bias**
   - Using information not available at the time of the trade. Common in point-in-time data errors and survivorship-biased datasets.

3. **Survivorship Bias**
   - Databases only include funds that are still alive. Dead funds (which likely had poor metrics) are excluded, inflating the apparent performance of the surviving set.

4. **Non-Stationarity**
   - Markets change. A strategy with a 2.0 Sharpe from 2010-2020 may have a 0.5 Sharpe from 2020-2025. Metrics must be regime-conditional.

5. **Correlation Breakdown in Crisis**
   - Diversification metrics assume stable correlations. In crises, correlations spike to 1.0, rendering diversification benefits illusory.

6. **Fee Blindness**
   - Always evaluate metrics net of fees, transaction costs, and taxes. A gross Sharpe of 1.5 can become a net Sharpe of 0.8 after all costs.

7. **Illiquidity and Capacity**
   - Backtests assume perfect execution. Real-world slippage, market impact, and capacity constraints can turn a winning strategy into a loser.

8. **Behavioral Gap (Investor Returns vs. Investment Returns)**
   - The best strategy is worthless if investors cannot stick with it. High Sharpe with 50% drawdowns may produce negative dollar-weighted returns due to panic selling.

---

## 8. Quick Reference Tables

### Sharpe Ratio Thresholds by Investor Type

| Investor Type | Good | Acceptable | Poor |
|---------------|------|------------|------|
| Quant Hedge Fund | > 2.0 | 1.0 - 2.0 | < 1.0 |
| Mutual Fund | > 1.0 | 0.5 - 1.0 | < 0.5 |
| Bank Prop Trader | > 2.0 (desks vary) | 1.0 - 2.0 | < 1.0 |
| Robo-Advisor | > 0.80 | 0.50 - 0.80 | < 0.50 |
| Crypto Fund | > 1.5 | 0.8 - 1.5 | < 0.8 |
| CTA | > 1.0 | 0.5 - 1.0 | < 0.5 |

### Maximum Drawdown Tolerance by Investor Type

| Investor Type | Good | Acceptable | Poor |
|---------------|------|------------|------|
| Quant Hedge Fund | < 10% | 10% - 20% | > 25% |
| Mutual Fund | < 15% | 15% - 25% | > 30% |
| Bank Prop Trader | < 5% daily VaR | Within risk budget | Breach limits |
| Robo-Advisor | < 15% (balanced) | 15% - 25% | > 25% |
| Crypto Fund | < 30% | 30% - 50% | > 60% |
| CTA | < 20% | 20% - 30% | > 35% |

### Metric Interaction Matrix

| Interaction | Interpretation | Action |
|-------------|----------------|--------|
| High Sharpe + Low Sortino | Strategy has upside volatility but bad downside tails | Investigate tail risk |
| High Alpha + High Tracking Error + Low IR | Inconsistent outperformance | Demand longer track record |
| High DSR + Low Sharpe | Real edge, but weak economic value | Evaluate cost of capital |
| Low VaR + High CVaR | Hidden tail risk | Stress test beyond VaR |
| High Win Rate + Low Profit Factor | Many small wins, rare large losses | Check for short-gamma profile |
| Positive TWR + Negative Dollar-Weighted Return | Behavioral failure / bad client timing | Advisor must improve coaching |
| High Beta + Claimed Alpha | Likely beta in disguise | Benchmark correctly |
| Positive Expectancy + Low MAR | Good trade economics but bad drawdown timing | Review position sizing |

---

## Sources and Methodology

This document synthesizes:
- Standard financial definitions from Investopedia and CFA Institute materials
- Academic literature on performance measurement (Sharpe, Sortino, Calmar, Information Ratio)
- Industry practice from quantitative finance (Lopez de Prado's DSR, Kelly Criterion applications)
- Regulatory frameworks (Basel III/IV for bank prop trading)
- Behavioral finance research (Vanguard's "Advisor's Alpha")
- CTA industry norms (MAR ratio, Profit Factor, Expectancy)

**Disclaimer:** Thresholds are approximate and vary by strategy, mandate, and market regime. Always calibrate to peer groups and historical context.

---

*Document compiled for internal strategy evaluation and cross-functional reference.*
