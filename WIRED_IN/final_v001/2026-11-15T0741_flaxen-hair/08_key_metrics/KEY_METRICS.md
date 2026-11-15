# KEY METRICS — From Multiple Perspectives

**Worktree:** flaxen-hair_2026-11-15T0020 | **Date:** 2026-11-15T00:27Z | **Repo:** findtorontoevents_antigravity.ca

---

## Executive Summary

Different stakeholders evaluate performance differently. A pure quant cares about Sharpe ratios; a mutual fund manager cares about expense ratios and tracking error; a bank's top stock trader cares about daily PnL consistency. This document defines key metrics from each perspective so the team can evaluate strategies consistently.

---

## Perspective 1: Pure Statistical Trader (Algo/Math)

**Focus:** Statistical significance, risk-adjusted returns, multiple-testing correction

| Metric | Minimum | Target | Source |
|--------|---------|--------|--------|
| Profit Factor | ≥ 1.5 | > 2.0 | Gross wins / gross losses |
| Sharpe Ratio | > 0.5 | > 1.0 | Return per unit of total risk |
| Sortino Ratio | > 1.0 | > 2.0 | Return per unit of downside risk |
| Calmar Ratio | > 0.5 | > 1.0 | Return per unit of max drawdown |
| Win Rate | > 50% | > 60% | Frequency of winning trades |
| Expectancy | > 0 | > 0.5% per trade | (Win% × Avg Win) − (Loss% × Avg Loss) |
| Max Drawdown | < 15% | < 10% | Worst peak-to-trough decline |
| Deflated Sharpe Ratio | ≥ 0.95 | ≥ 0.95 | Multiple testing correction |
| Probabilistic Sharpe | > 0.80 | > 0.95 | Probability true Sharpe > 0 |
| Kelly Fraction | > 0 after shrinkage | > 0.10 | Optimal position size |
| Ulcer Index | < 5% | < 3% | Depth and duration of drawdowns |

**Key Question:** "Is this edge statistically real or just luck?"

---

## Perspective 2: Professional Investor (Long-Only, Fundamental)

**Focus:** Capital preservation, benchmark-relative performance, business quality

| Metric | Minimum | Target | Why |
|--------|---------|--------|-----|
| CAGR (5+ years) | > Market | > Market + 2% | Beat benchmark over full cycle |
| Max Drawdown | < 20% | < 15% | Permanent capital loss avoidance |
| Beta | 0.8-1.2 | < 1.0 | Market sensitivity |
| Alpha | > 0 | > 2% | Excess return after benchmark |
| Information Ratio | > 0.5 | > 1.0 | Active return per unit active risk |
| Tracking Error | < 5% | < 3% | Deviation from benchmark |
| Dividend Yield | > 2% | > 3% | Cash flow component |
| P/E Ratio | < Market | < Market | Valuation discipline |
| ROE | > 15% | > 20% | Business quality |
| Debt/Equity | < 1.0 | < 0.5 | Balance sheet strength |

**Key Question:** "Can I sleep at night knowing this won't lose permanent capital?"

---

## Perspective 3: Mutual Fund Manager

**Focus:** Low cost, low turnover, long track record, benchmark adherence

| Metric | Minimum | Target | Why |
|--------|---------|--------|-----|
| Expense Ratio | < 0.50% | < 0.20% | Costs compound over time |
| AUM | > $100M | > $1B | Liquidity and stability |
| Turnover | < 50% | < 20% | Transaction costs |
| Tracking Error | < 3% | < 1% | Benchmark adherence |
| Inception Date | > 10 years | > 20 years | Multiple market cycles |
| Manager Tenure | > 5 years | > 10 years | Manager stability |
| Morningstar Rating | 3 stars | 4-5 stars | Independent quality screen |
| Max Drawdown | < 15% | < 10% | Investor retention |
| Alpha (3yr) | > 0 | > 1% | Skill after fees |
| Sharpe (3yr) | > 0.5 | > 1.0 | Risk-adjusted return |

**Key Question:** "Is this a cheap, reliable fund I can hold for decades?"

---

## Perspective 4: Bank's Top Stock Trader

**Focus:** High frequency, low latency, consistent daily profits

| Metric | Minimum | Target | Why |
|--------|---------|--------|-----|
| Daily PnL | Positive | Consistently positive | Daily profitability |
| Win Rate | > 55% | > 65% | Frequency of winning days |
| Avg Win / Avg Loss | > 1.5 | > 2.0 | Risk-reward ratio |
| Max Daily Loss | < -1% | < -0.5% | Daily risk limit |
| Max Consecutive Losses | < 5 | < 3 | Emotional and capital resilience |
| Position Turnover | Minutes-hours | Seconds-minutes | Speed of execution |
| Slippage | < 1 bps | < 0.5 bps | Execution quality |
| Commission per Trade | < $1 | < $0.50 | Volume-based pricing |

**Key Question:** "Can I make money every day without blowing up?"

---

## Perspective 5: Risk Manager (Institutional)

**Focus:** Capital preservation, crisis survival, regulatory compliance

| Metric | Maximum | Target | Why |
|--------|---------|--------|-----|
| VaR (95%, 1-day) | < 2% of NAV | < 1.5% | Daily risk exposure |
| CVaR / Expected Shortfall | < 3% of NAV | < 2% | Tail risk |
| Max Drawdown | < 20% | < 10% | Capital preservation |
| Stress Test (2008 scenario) | Survive | Survive with < 30% loss | Crisis resilience |
| Leverage Ratio | < 3:1 | < 2:1 | Balance sheet risk |
| Correlation to Market | < 0.8 | < 0.5 | Diversification benefit |
| Liquidity Coverage | > 30 days | > 60 days | Survival without new capital |
| Counterparty Exposure | < 10% | < 5% | Single counterparty risk |
| Regulatory Capital | > Minimum | > 1.5× Minimum | Compliance buffer |

**Key Question:** "Can we survive a crisis without blowing up?"

---

## Perspective 6: Retirement Investor (Long-Term, Passive)

**Focus:** Simplicity, low cost, reliable income

| Metric | Minimum | Target | Why |
|--------|---------|--------|-----|
| Expense Ratio | < 0.20% | < 0.10% | Costs compound over decades |
| Dividend Yield | > 2% | > 3% | Retirement income |
| Max Drawdown | < 10% | < 5% | Sleep-at-night factor |
| Time in Market | > 95% | > 99% | Avoid market timing |
| Rebalance Frequency | < 2x/year | < 1x/year | Minimize taxes and costs |
| Tax Efficiency | High | Very High | Minimize capital gains distributions |

**Key Question:** "Will I have enough money when I retire?"

---

## Consolidated Metric Framework for This Repo

| Metric | Threshold | Source | Application |
|--------|-----------|--------|-------------|
| Profit Factor | ≥ 1.5 | finpredict-v4 Gate 3 | Gross profitability |
| Sharpe Ratio | ≥ 0.5 | Risk management | Risk-adjusted return |
| Sortino Ratio | > 1.0 | Risk management | Downside risk |
| Win Rate | > 50% | finpredict-v4 Gate 3 | Frequency of wins |
| Max Drawdown | < 15% | Risk management | Capital preservation |
| Deflated Sharpe | ≥ 0.95 | finpredict-v4 Gate 4 | Multiple testing |
| DSR after best day | ≥ 0.95 | finpredict-v4 Gate 4 | Single-day robustness |
| 2-day-lag Sharpe | ≥ 1.0 | finpredict-v4 Gate 4 | Execution robustness |
| Expectancy | > 0 | Probability framework | Average profit per trade |
| Forward Sample | n ≥ 100 | finpredict-v4 Gate 4 | Statistical significance |
| Kelly Fraction | > 0 after shrinkage | Probability framework | Optimal position sizing |

---

## How to Use These Metrics

### For Strategy Evaluation
1. Calculate ALL metrics for each strategy
2. Apply finpredict-v4 6-gate pipeline
3. Require ALL gates to pass before paper trading
4. Require forward n ≥ 100 before live capital

### For Asset Class Allocation
1. Mutual funds/ETFs: Use Perspective 3 (Mutual Fund Manager) metrics
2. Individual stocks: Use Perspective 2 (Professional Investor) metrics
3. Active trading: Use Perspective 1 (Statistical Trader) metrics
4. Risk oversight: Use Perspective 5 (Risk Manager) metrics

### For Dashboard Display
- Show Sharpe, Sortino, Calmar prominently
- Show Max Drawdown in red if > 15%
- Show Win Rate with confidence intervals
- Show forward sample count (n)
- Flag any metric below threshold in red

---
