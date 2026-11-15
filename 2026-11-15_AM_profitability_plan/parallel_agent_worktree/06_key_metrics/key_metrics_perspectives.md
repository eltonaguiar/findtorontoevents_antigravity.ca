# Key Metrics That Must Be Satisfied — Multi-Perspective Framework

No single metric proves profitability. Different stakeholders look at different metrics. Below is a comprehensive framework covering Sharpe Ratio, pro investor, mutual fund manager, bank trader, and risk-manager perspectives.

---

## 1. Quantitative / Algorithmic Trader Perspective

| Metric | Minimum Threshold | Why It Matters |
|--------|------------------|----------------|
| **Profit Factor (PF)** | ≥ 1.15 (equity), ≥ 1.5 (ideal) | Gross profits / gross losses. Below 1.0 = losing system. |
| **Sharpe Ratio** | ≥ 1.0 (annualized) | Return per unit of total risk. Below 0.5 = poor risk-adjusted return. |
| **Sortino Ratio** | ≥ 1.0 | Return per unit of downside risk. Better than Sharpe for asymmetric strategies. |
| **Calmar Ratio** | ≥ 0.5 | Annual return / max drawdown. Measures return relative to worst-case loss. |
| **Win Rate (WR)** | ≥ 50% | Percentage of winning trades. Below 50% requires very high avg win/avg loss ratio. |
| **Avg Win / Avg Loss** | ≥ 1.5:1 | Risk-reward ratio. Compensates for sub-50% win rates. |
| **Max Drawdown** | < 15% (monthly), < 30% (annual) | Worst peak-to-trough decline. Capital preservation limit. |
| **Recovery Factor** | ≥ 3.0 | Net profit / max drawdown. How quickly the system recovers from losses. |
| **Expectancy per Trade** | > 0 after costs | (Win% × Avg Win) − (Loss% × Avg Loss). Must be positive. |
| **DSR (Deflated Sharpe Ratio)** | ≥ 0.95 | Probability that the Sharpe is not due to luck, accounting for multiple testing. |
| **PBO (Probability of Backtest Overfitting)** | ≤ 0.10 | Probability the backtest results are overfitted. Lower is better. |
| **SPA Test p-value** | ≤ 0.10 | Superior Predictive Ability vs benchmark. Must be statistically significant. |
| **Block-Bootstrap CI Lower Bound** | > 0 on net expectancy | Confidence interval for expectancy must exclude zero. |
| **Forward Sample (n)** | ≥ 100 closed trades over ≥ 3 months | Out-of-sample forward performance. |
| **Effective N** | ≥ 30 after autocorrelation adjustment | Sample size adjusted for overlapping/autocorrelated returns. |
| **Information Coefficient (IC)** | > 0.05 (ideally > 0.10) | Correlation between predicted and actual returns. Currently ≈ 0. |

**Current system status:** IC ≈ 0, WR ~40%, PF < 1.0 for most classes. **FAILS all quantitative thresholds.**

---

## 2. Professional Investor Perspective (Institutional / Hedge Fund)

| Metric | Minimum Threshold | Why It Matters |
|--------|------------------|----------------|
| **Alpha (Jensen's)** | > 0 after costs, statistically significant | Excess return over benchmark (SPY total return). Must be positive and significant. |
| **Beta** | Close to 0 (market-neutral) or clearly managed | Market exposure should be intentional, not accidental long bias. |
| **Tracking Error** | < 5-10% vs benchmark | How much the strategy deviates from the benchmark. High TE = active risk. |
| **Information Ratio** | ≥ 0.5 | Alpha / tracking error. Risk-adjusted active return. |
| **Up/Down Capture** | Up capture > 100%, Down capture < 100% | Capture more upside than downside vs benchmark. |
| **Hit Rate vs Benchmark** | > 50% of periods beat benchmark | Consistency of outperformance, not just aggregate. |
| **Rolling Window Consistency** | Positive alpha in ≥ 60% of rolling 12-month windows | Robustness across regimes. |
| **Style Drift** | Minimal | Strategy should not drift from its stated mandate. |
| **Capacity** | Clear AUM limit before capacity decay | How much capital can the strategy absorb before edge erodes? |
| **Liquidity Profile** | Can exit positions within 1-5 days without market impact | Critical for redemption management. |

**Current system status:** EQUITY failed SPY gate (t=1.05, median excess -0.57%). **FAILS alpha vs benchmark.**

---

## 3. Mutual Fund Manager Perspective

| Metric | Minimum Threshold | Why It Matters |
|--------|------------------|----------------|
| **Expense Ratio** | ≤ 0.09% (index), ≤ 0.20% (active) | Costs directly reduce investor returns. High ER = structural disadvantage. |
| **Turnover Ratio** | ≤ 20% | High turnover = trading costs + tax inefficiency. |
| **Tracking Error vs Benchmark** | ≤ 0.25% (index), controlled (active) | How closely the fund follows its benchmark. |
| **AUM** | ≥ $1B (preferred) | Scale indicates institutional trust and liquidity. |
| **Min Initial Investment** | ≤ $3,000 (retail accessible) | Accessibility for individual investors. |
| **Load / 12b-1 Fees** | None (no-load) | Front-end/back-end loads and 12b-1 fees are pure drag. |
| **Track Record** | ≥ 10 years | Long enough to see multiple market cycles. |
| **Manager Tenure** | ≥ 5 years (if active) | Continuity of strategy execution. |
| **Tax Efficiency** | High (low capital gains distributions) | Important for taxable accounts. |
| **Style Consistency** | Clear, documented investment objective | Investors need to know what they're buying. |
| **Risk-Adjusted Return (3-5 yr)** | Top quartile vs category | Must beat peers on risk-adjusted basis. |
| **Maximum Drawdown** | < category average | Capital preservation relative to peers. |

**Current system status:** Mutual funds have **zero production infrastructure**. Not even registered as an asset class (class id = -1). The only MF path is passive core allocation using existing low-cost funds (VFIAX, VTSAX, etc.).

---

## 4. Bank's Top Stock Trader (Desk Trader) Perspective

| Metric | Minimum Threshold | Why It Matters |
|--------|------------------|----------------|
| **PnL per Day** | Consistently positive | Daily profitability after all costs. |
| **Win Rate** | ≥ 55% | Desk traders need high frequency of small wins. |
| **Average Win / Average Loss** | ≥ 2:1 | Let winners run, cut losers quickly. |
| **Max Daily Loss (Stop)** | -0.5% to -2% of capital | Daily circuit breaker. |
| **Max Weekly Loss** | -1.5% to -5% | Weekly drawdown halt. |
| **Max Monthly Loss** | -3% to -10% | Monthly drawdown halt. |
| **Position Size per Trade** | 1-2% of capital at risk | Risk per trade. |
| **Max Single Position** | 5% of portfolio | Concentration limit. |
| **Correlation Limit** | < 0.70 between positions | Avoid correlated losses. |
| **Turnover** | High (but cost-controlled) | Desk traders turn positions quickly but watch costs. |
| **Fill Quality** | VWAP or better | Execution quality matters for desk profitability. |
| **Slippage** | Minimized via smart order routing | Every basis point counts. |
| **Regulatory Compliance** | Full (MiFID II, Reg NMS, etc.) | Banks cannot trade non-compliantly. |
| **VaR Limit** | Defined daily VaR cap | Risk management constraint. |

**Current system status:** No desk-trader risk controls implemented. No daily/weekly/monthly drawdown halts. No position sizing rules. No VaR. **FAILS all desk-trader risk thresholds.**

---

## 5. Risk Manager Perspective (Independent Oversight)

| Metric | Minimum Threshold | Why It Matters |
|--------|------------------|----------------|
| **Value at Risk (VaR 95%)** | Defined and monitored | Maximum expected loss at 95% confidence over horizon. |
| **Expected Shortfall (CVaR)** | Defined and monitored | Expected loss in the worst 5% of cases. Tail risk. |
| **Ulcer Index** | < 5% | Measures duration and depth of drawdowns. |
| **Maximum Drawdown** | < 15% quarterly, < 30% annual | Hard capital preservation limit. |
| **Drawdown Duration** | < 3 months to recover | How long underwater before new highs. |
| **Stress Test Results** | Survive 2008-style crash, 2020 COVID crash | Scenario analysis. |
| **Kill Switch** | Defined trigger levels | Automatic halt at breach points. |
| **Concentration Limit** | < 20% in any single asset/sector | Diversification requirement. |
| **Leverage Limit** | ≤ 2:1 (or unlevered) | Borrowing constraint. |
| **Liquidity Buffer** | ≥ 10% cash or T-bills | Ability to meet redemptions/margin calls. |
| **Counterparty Risk** | Monitored per broker/exchange | Exchange failure risk (crypto especially). |
| **Model Risk** | Backtest vs forward gap monitored | Is the model still valid in live trading? |

---

## 6. Integrated Scorecard — All Metrics Combined

| Category | Metric | Threshold | Current Status | Pass/Fail |
|----------|--------|-----------|----------------|-----------|
| Quantitative | PF | ≥ 1.15 | < 1.0 (most classes) | ❌ Fail |
| Quantitative | Sharpe | ≥ 1.0 | Not computed / negative | ❌ Fail |
| Quantitative | WR | ≥ 50% | ~40% | ❌ Fail |
| Quantitative | DSR | ≥ 0.95 | Not computed | ❌ Fail |
| Quantitative | PBO | ≤ 0.10 | Not computed | ❌ Fail |
| Quantitative | Forward n | ≥ 100 over ≥ 3 mo | 0 (no clean forward) | ❌ Fail |
| Institutional | Alpha vs SPY | > 0, significant | Failed (t=1.05) | ❌ Fail |
| Institutional | Beta | Controlled | 100% long bias | ❌ Fail |
| Mutual Fund | ER | ≤ 0.09% | N/A (no infrastructure) | ⚠️ Blocked |
| Mutual Fund | Track record | ≥ 10 years | N/A | ⚠️ Blocked |
| Desk Trader | Daily loss limit | -0.5% to -2% | Not implemented | ❌ Fail |
| Desk Trader | Position size | 1-2% risk | Not implemented | ❌ Fail |
| Risk Manager | Max DD | < 15% | Not monitored | ❌ Fail |
| Risk Manager | Kill switch | Defined | Not implemented | ❌ Fail |

**Overall: 0/15+ metrics pass. System is not money-ready from any perspective.**

---

## 7. What "Proven Profitable" Looks Like

A strategy that would satisfy all perspectives simultaneously:

1. **Quant:** PF ≥ 1.5, Sharpe ≥ 1.2, DSR ≥ 0.95, PBO ≤ 0.10, forward n ≥ 100 over 3+ months, block-bootstrap CI excludes zero.
2. **Institutional:** Positive alpha vs SPY total return, beta controlled, information ratio ≥ 0.5, rolling-window consistency.
3. **Mutual Fund:** If used as core, ER ≤ 0.10%, turnover ≤ 20%, track record ≥ 10 years, no load.
4. **Desk Trader:** Daily/weekly/monthly loss limits, position sizing 1-2%, kill switch defined.
5. **Risk Manager:** VaR/CVaR monitored, max DD < 15%, stress-tested, correlation limits enforced.

**Until all five perspectives are satisfied, do not deploy capital.**
