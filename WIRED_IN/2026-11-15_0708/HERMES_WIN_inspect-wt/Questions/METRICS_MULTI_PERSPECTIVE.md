# Key Metrics — Multi-Perspective Thresholds

A strategy can look great on one lens and be uninvestable on another. These are the thresholds each stakeholder applies, and **all** relevant lenses must pass before capital moves.

## 1. Risk-adjusted return lenses

| Metric | What it measures | Caution |
|---|---|---|
| Sharpe | Excess return per unit total volatility | Rewards both upside and downside vol; inflated by non-normal returns |
| Sortino | Excess return per unit *downside* vol | Better for asymmetric strategies; can hide tail risk |
| Calmar | CAGR / max drawdown | Single-event denominator; one bad period dominates |
| Sterling | CAGR / average of N worst drawdowns | More robust than Calmar; needs long history |
| Treynor | Excess return per unit beta | Only meaningful if returns are beta-driven |
| Information ratio | Active return / tracking error vs benchmark | The right metric for benchmark-relative mandates |

## 2. Thresholds by perspective

### Pro / institutional allocator
- Net Sharpe ≥ **1.0** over ≥5 years, and ≥0.7 in the worst rolling 3-year window
- Max drawdown ≤ **15%**, recovery ≤ 12 months
- Capacity stated at target AUM; edge survives slippage at 10× our size
- Attribution: alpha ≥ 60% of total return (not a repackaged factor tilt)
- **Reject:** Sharpes without deflated-Sharpe correction, or without an out-of-sample record

### Mutual fund manager (retail mandate)
- Consistent risk-adjusted excess vs category benchmark, net of ER
- Drawdown tolerable for retail: typically ≤ 20–25% equity, ≤ 10% balanced
- Low turnover (tax + cost drag), high capacity, liquidity daily
- Style not drifting away from mandate
- **Reject:** anything requiring leverage or illiquid instruments

### Bank / prop desk trader
- Sharpe is secondary to **hit rate × payoff ratio** and expected value per trade
- Payoff ratio (avg win / avg loss) ≥ **1.5** with hit rate ≥ 40%; or hit ≥ 55% with payoff ≥ 1.0
- Max intraday loss limit respected; kill switch tested
- Slippage model validated against real fills, not assumed
- **Reject:** strategies whose edge lives inside the assumed fill price

### Risk manager
- Tail metrics dominate: VaR95/99, Expected Shortfall, **max drawdown**, probability of ruin
- Worst rolling 12-month return acceptable for the mandate
- Stress tests: 2008, Mar-2020, 2022 rate shock, crypto May-2021
- Correlation to existing book < 0.5; concentration limits respected
- **Reject:** any strategy whose 5th-percentile Monte Carlo path breaches the drawdown halt

### Quant researcher / statistician
- Deflated Sharpe after the **project-wide** trial count ≥ threshold
- White's Reality Check p < 0.05
- Walk-forward efficiency ≥ 0.5, parameter stability across windows
- Bootstrap CI for mean excess return excludes zero
- Shuffle control shows no leak
- **Reject:** anything passing only in-sample or only after parameter search

## 3. Trade-level statistics (all candidates must report)

Win rate · profit factor · expectancy per trade · avg win / avg loss · payoff ratio ·
longest losing streak · average holding period · trades per year · **effective N**
(trades after removing overlapping/correlated ones).

## 4. Distribution diagnostics

Skewness · kurtosis · serial autocorrelation of returns · fat-tail tests ·
**% of paths positive after cost** (block bootstrap) · 5th-percentile net return.

## 5. Gate summary (what actually decides promotion)

| Gate | Threshold | Source |
|---|---|---|
| Cost multiple | edge / round-trip cost ≥ 3× | `tools/per_class_cost_gate.py` (`REQUIRED_COST_MULTIPLE = 3.0`) |
| Walk-forward consistency | ≥ 0.5 pass-rate | `walk_forward_validator.py` (`min_consistency`) |
| Min train trades | ≥ 10–20 per window | `walk_forward_validator.py` (`min_train_trades`) |
| Deflated Sharpe | must clear after project-wide trial count | proof step 3 (not yet automated — **gap**) |
| FDR gate | **currently OFF by default** (`MONEY_READY_FDR_GATE=0`) | `alpha_engine/money_ready_verdict.py` |
| Single-source gate | **currently OFF by default** | `alpha_engine/money_ready_verdict.py` |

**Two of the repo's own promotion gates ship disabled.** Any "money-ready" verdict reached with them off is not a promotion — enabling both is a prerequisite for the first deployable candidate.
