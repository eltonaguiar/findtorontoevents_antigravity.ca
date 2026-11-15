# FRAMEWORK ANSWERS — Responses to Key Questions

**Worktree:** flaxen-hair_2026-11-15T0020 | **Date:** 2026-11-15T00:27Z | **Repo:** findtorontoevents_antigravity.ca

---

## ANSWER 1: Thorough List of Asset Classes the System Has Attempted to Predict

Based on ALL_STRATEGIES.md and all money-maker skill files, the system has attempted to predict the following asset classes:

| Asset Class | Strategies | Data Source | Status |
|-------------|-----------|-------------|--------|
| **CRYPTO** | 700+ | Binance, Coinglass, ML predictors | 0/23 proven; entry_price ~29% clean |
| **EQUITY (US)** | 14+ | Nasdaq, yfinance | Positive cost margin (3.23×), n=738 |
| **FOREX** | 12 | er-api, Binance | Zero DSR survivors; PF 0.29 |
| **ETF** | 9 | yfinance | All 9 hypotheses NOT_PROVED |
| **COMMODITY** | ~6 | CME, COT data | WR 67.8%, PF 3.94 (cumulative, likely inflated) |
| **BOND** | ~4 | Treasury.gov, Nasdaq ETFs | n=11-18, thin data |
| **FUTURES** | 0 | CME futures | Dead; WR 5.9%, PnL -96% |
| **MEMECOIN** | ~29 | Various | Quarantined; PF 0.50 |
| **PENNY** | 8 | Various | Deep oversold BLOCKED |
| **MUTUAL FUNDS** | 0 | None | Zero infrastructure exists |

**Other Related Surfaces:**
- HyroTrader (prop challenge tracker) — 0 journal trades logged
- Mercury2 — ensemble strategies
- Crypto ML Edge — ML-based crypto predictions
- Claude Gainer ML — token sniffer, self-improver
- DNA Genome — strategy genetics
- AI Tournament — 39 models forward-tested
- Copy Trader Intel — copy trading signals

**Main Dashboard Tabs:** Active Picks, Closed Picks

---

## ANSWER 2: Which Classes Have Highest Probability of Profitability with Lower Risk?

**Realistic Ranking (probability of positive real returns + lower permanent capital-loss risk):**

### Tier 1: Core Allocation (NOT prediction, but highest probability)

| Asset Class | Expected Return | Risk | Basis |
|-------------|----------------|------|-------|
| Low-cost broad index ETFs (SPY, VTI, etc.) | Market return (~7-10% annualized) | Low-Medium | Equity risk premium over multi-year periods |
| Low-cost mutual funds (index-based) | Market return (~7-10% annualized) | Low-Medium | Equity risk premium |
| Short-duration bond ETFs (SHY, BIL) | ~4-5% | Very Low | Bond yields + low duration risk |
| T-bills / Cash equivalents | ~4-5% | Very Low | Risk-free rate |

**Criteria:** ER ≤ 0.10-0.20%, high AUM, low turnover, long track record (≥10 years), no load fees, no 12b-1 fees.

**This is allocation and cost discipline, NOT ML prediction.**

### Tier 2: Secondary Research (EQUITY)

| Asset Class | Expected Return | Risk | Basis |
|-------------|----------------|------|-------|
| EQUITY (systematic) | Unknown (unproven) | Medium | Only class with positive cost margin (3.23×) |

**Status:** Only class with a pre-registered benchmark test path vs SPY total return. Still unproven; requires n≥500, PF≥1.15 after costs, clean OOS.

### Tier 3: Selective (COMMODITY / BOND)

| Asset Class | Expected Return | Risk | Basis |
|-------------|----------------|------|-------|
| COMMODITY | Unknown | Medium-High | Better historical PF but n too small |
| BOND (selective) | Unknown | Low-Medium | Better historical PF but n far below floor |

**Status:** Low risk when sized properly, but insufficient data for validation.

---

### Tier 4: Satellite / Speculative (ETF tactical, single stocks)

| Asset Class | Expected Return | Risk | Basis |
|-------------|----------------|------|-------|
| ETF tactical / quality single stocks | Unknown | High | Concentration and volatility raise permanent-loss risk |
| Long-term quality growth (e.g., NVDA-style) | Unknown | High | Has worked historically; not guaranteed |

**Status:** Possible satellite, NOT core. Daytrading/scalping has NOT worked (costs + overfitting dominate).

---

### Tier 5: Conditional (CRYPTO)

| Asset Class | Expected Return | Risk | Basis |
|-------------|----------------|------|-------|
| CRYPTO | Unknown (potential in isolated elite strategies) | Very High | Overall drag from retired toxic paths, data/fill bugs |

**Status:** High risk. Only after fill bugs fixed and clean forward test.

---

### Tier 6: Weakest (FOREX)

| Asset Class | Expected Return | Risk | Basis |
|-------------|----------------|------|-------|
| FOREX | Negative expected value | High | Currently the weakest |

---

## ANSWER 3: Framework for Finding Profitability Despite Struggles

### Principle: The System is Research Infrastructure, Not a Money-Ready Engine

Treat the prediction system as a research lab, not a trading engine. The framework below is the only defensible path forward.

### Step 1: Fix Measurement Before Anything Else

**Recompute PnL from entry/exit prices vs real market data.**

| Check | Method | Source |
|-------|--------|--------|
| PnL=0% with price movement | `(exit/entry - 1) * direction` vs stored pnl_pct | Binance/Nasdaq/er-api |
| Blank required fields | All required fields present for status | All pick files |
| Stale open positions (>72h) | `now - entry_time > 72h` | live_picks.json |
| Recently closed missing exit data | exit_price, exit_date, closed_at, pnl_pct present | All pick files |
| Cost leakage | Transaction costs included in net PnL | All pick files |

**Open Positions (>72 hours):** Flag as HIGH severity; >168 hours as CRITICAL. These are zombie positions that distort PnL.

**Recently Closed Items:** Must have exit_price, exit_date, closed_at, AND pnl_pct. Missing any = HIGH severity flag.

---

### Step 2: Separate Beta Capture from Alpha Generation

**Core Portfolio (Beta Capture):**
- Low-cost diversified ETFs/mutual funds (total market, international, short-duration bonds/T-bills)
- This is the highest-probability lower-risk path
- Does NOT require the prediction system to work
- Criteria: ER ≤ 0.10-0.20%, high AUM, low turnover, long track record

**Alpha Research (Alpha Generation):**
- Keep the scanners, but enforce existing promotion gates
- All classes currently fail them
- Focus first on EQUITY pre-registered SPY benchmark test

---

### Step 3: Strict Research Protocol

| Rule | Requirement |
|------|-------------|
| Pre-register hypotheses | Before running any backtest |
| Clean OOS | Out-of-sample data not used in development |
| Effective N | n ≥ 30 per filter bucket, n ≥ 100 for class verdict |
| Cost-adjusted PF | PF after commissions, slippage, spread |
| Sharpe/Sortino/Calmar/DSR | All must meet thresholds |
| Forward sample | n ≥ 100-500 before live capital |
| Kill or mutate | Paths that fail (FOREX already on mutation protocol) |
| Build missing infrastructure only if testing rigorously | MF/ETF only if testing selection criteria |

---

### Step 4: Risk-Management Overlay (Independent of Signal Quality)

| Parameter | Value |
|-----------|-------|
| Position sizing | 1-2% risk per trade |
| Kelly fraction | 0.25× max |
| Daily loss cap | -2% |
| Weekly loss cap | -5% |
| Monthly loss cap | -10% |
| Stop loss | ATR-based (1.0× SL / 1.5× TP) |
| Min R:R | 1.5:1 |
| Correlation limit | Max 3 per correlated group |

These protect capital while the edge search continues.

---

### Step 5: Practical Prioritization Order

| Priority | Action | Reason |
|----------|--------|--------|
| **1** | Measurement and cost integrity | Foundation for all decisions |
| **2** | EQUITY benchmark test vs SPY | Only class with positive cost margin |
| **3** | CRYPTO forward test (after fill fix) | Only conditional candidate |
| **4** | Everything else remains blocked | Arithmetic and data quality must clear first |
| **5** | Parallel: low-cost ETF/MF allocation | Actual money deployment vehicle |

---

## ANSWER 4: Essential Questions for Finding a Profitable Algorithm

Before declaring any algorithm profitable, answer these questions:

### Data Quality Questions
1. **Is entry_price accurate?** (Was it the actual fill price, or a stale/mispriced quote?)
2. **Was entry on the signal bar or the next bar?** (Signal-bar entry is look-ahead biased)
3. **Was exit on the actual fill price?** (Or an idealized price?)
4. **Were slippage and commissions included?** (Most backtests ignore these)
5. **Were expired picks counted as non-wins?** (Old methods dropped them, inflating WR)
6. **Was intrabar validation performed?** (Did price hit SL before TP intraday?)
7. **Is the data free of reverse-splits and feed bugs?** (e.g., CADJPY +428%, NZDUSD -100%)
8. **Is the sample size sufficient?** (n ≥ 100 for class verdict, n ≥ 30 for strategy)

### Statistical Questions
9. **Does the strategy pass Bonferroni/FDR correction?** (Multiple testing penalty)
10. **Is the Sharpe ratio positive after costs?** (Not just gross)
11. **Is the Max Drawdown acceptable?** (< 15% for most strategies)
12. **Is the expectancy positive?** ((Win Rate × Avg Win) > (Loss Rate × Avg Loss))
13. **Is the Kelly fraction positive?** (After shrinkage)
14. **Does performance hold across time periods?** (First half ≈ second half PF)
15. **Is it robust to regime changes?** (Works in bull AND bear markets)

### Execution Questions
16. **Can the strategy be executed in real-time?** (Or is it backtest-only?)
17. **Are signals actionable at the prices assumed?** (Or do they require better fills?)
18. **What is the capacity limit?** (How much capital before edge decays?)
19. **What is the correlation with existing positions?** (Avoid concentration)
20. **What is the maximum drawdown scenario?** (And can you survive it?)

### Process Questions
21. **Was the hypothesis pre-registered?** (Or is it data mining?)
22. **Has it been walk-forward tested?** (Not just one backtest)
23. **Has it been tested on out-of-sample data?** (Not the same data used for development)
24. **Has it been tested across multiple market regimes?** (Bull, bear, sideways)
25. **Is there a kill switch?** (At what loss level do you stop?)

### Mutual Fund / ETF Specific Questions
26. **Is the expense ratio ≤ 0.20%?** (For mutual funds)
| 27. | Are there load fees or 12b-1 fees? | Should be zero |
| 28. | Is AUM ≥ $1B? | For liquidity and stability |
| 29. | Is turnover ≤ 20%? | Lower transaction costs |
| 30. | Is tracking error ≤ 0.25%? | For index funds |

---

## ANSWER 5: Financial Prediction & Risk Management Company Turnarounds

### Pattern: Companies That Went From "No Edge" to Trustworthy

Based on general industry knowledge (not specific to this repo), here is how legitimate financial firms typically transitioned from struggling to trustworthy:

| Company/Type | Initial Struggle | Turnaround Strategy | Key Lesson |
|-------------|-----------------|---------------------|------------|
| **Renaissance Technologies** | Early Medallion fund struggled | Hired PhD non-financial scientists (physicists, statisticians); focused on short-term statistical patterns; massive data infrastructure; extreme secrecy | Edge comes from data + compute + statistical rigor, not market wisdom |
| **Two Sigma** | Early models overfit | Built massive data engineering team; emphasized feature engineering over model complexity; rigorous out-of-sample testing; separate research and production teams | Data quality > model complexity |
| **AQR Capital** | Early strategies underperformed | Focused on academic factors (value, momentum, quality, low vol); transparent about what works/doesn't; multi-strategy diversification; risk budgeting | Diversify across proven factors; don't chase single edges |
| **Bridgewater Associates** | Early volatility | Developed "Principles" systematic decision-making; emphasized risk parity; extreme transparency about failures; independent risk team | Risk management first; alpha second |
| **Citadel** | Early losses | Massive technology investment; multi-strategy platform (allows uncorrelated strategies); real-time risk monitoring; separate PM risk limits | Diversification + real-time risk control |

### Common Patterns Across Successful Firms

| Pattern | Description | Application to This Repo |
|---------|-------------|--------------------------|
| **Data engineering > Model complexity** | Spent more time cleaning data than building models | Fix entry_price integrity (~29% clean) before hunting edge |
| **Out-of-sample testing** | Never trade on data used for development | Pre-register all backtests; test on truly unseen data |
| **Risk budgeting** | Each strategy gets a risk budget; blow it and you're out | Implement weekly/monthly drawdown halts |
| **Strategy decomposition** | Separate alpha generation from execution | Fix fills before hunting edge |
| **Multiple independent strategies** | Don't rely on one edge | Don't put all capital in one strategy/class |
| **Transparency about failures** | Document what didn't work | Keep the NOT_PROVED list; don't hide failures |
| **Cost awareness** | Commissions/slippage are real | Include costs in all backtests |
| **Capacity awareness** | Edge decays with more capital | Size appropriately; don't over-size |

### Specific Turnaround Lessons for This Repo

1. **Fix the data first** (like Renaissance did with data infrastructure)
   - entry_price integrity (~29% clean)
   - OHLCV history depth (≥180d 1h bars)
   - Pick resolution (~90% never resolve)

2. **Separate research from production** (like Two Sigma)
   - Research team tests ideas; production team only deploys proven ones
   - No direct path from backtest to live

3. **Risk budget per strategy** (like Bridgewater)
   - Each strategy gets max loss budget
   - Blow it → strategy is killed

4. **Diversify across uncorrelated edges** (like Citadel)
   - Don't rely on one strategy or asset class
   - But only add edges that pass all gates

5. **Document failures openly** (like Bridgewater's Principles)
   - Keep the NOT_PROVED list public within the team
   - Don't hide failed strategies

---

## ANSWER 6: Key Metrics from Different Perspectives

### Perspective 1: Pure Statistical Trader (Algo/Math)

| Metric | Minimum | Target | Why |
|--------|---------|--------|-----|
| Sharpe Ratio | > 0.5 | > 1.0 | Risk-adjusted return |
| Sortino Ratio | > 1.0 | > 2.0 | Downside risk adjustment |
| Calmar Ratio | > 0.5 | > 1.0 | Return vs max drawdown |
| Profit Factor | > 1.5 | > 2.0 | Gross wins vs gross losses |
| Win Rate | > 50% | > 60% | Frequency of winning trades |
| Expectancy | > 0 | > 0.5% per trade | Average profit per trade |
| Max Drawdown | < 15% | < 10% | Worst peak-to-trough |
| Deflated Sharpe Ratio | ≥ 0.95 | ≥ 0.95 | Multiple testing correction |
| Probabilistic Sharpe | > 0.80 | > 0.95 | Probability Sharpe > 0 |
| Kelly Fraction | > 0 after shrinkage | > 0.10 | Optimal position size |
| Ulcer Index | < 5% | < 3% | Depth and duration of drawdowns |

### Perspective 2: Professional Investor (Long-Only, Fundamental)

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

**Long-term investor priority:** Capital preservation > Alpha generation

### Perspective 3: Mutual Fund Manager

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

**Mutual fund priority:** Low cost, low turnover, long track record, benchmark adherence

### Perspective 4: Bank's Top Stock Trader

| Metric | Minimum | Target | Why |
|--------|---------|--------|-----|
| Daily PnL | Positive | Consistently positive | Daily profitability |
| Win Rate | > 55% | > 65% | Frequency of winning days |
| Avg Win / Avg Loss | > 1.5 | > 2.0 | Risk-reward ratio |
| Max Daily Loss | < -1% | < -0.5% | Daily risk limit |
| Max Consecutive Losses | < 5 | < 3 | Emotional and capital resilience |
| Turnover | High | Very High | Scalping/day trading volume |
| Position Turnover | Minutes-hours | Seconds-minutes | Speed of execution |
| Slippage | < 1 bps | < 0.5 bps | Execution quality |
| Commission per Trade | < $1 | < $0.50 | Volume-based pricing |

**Bank trader priority:** High frequency, low latency, consistent daily profits

### Perspective 5: Risk Manager (Institutional)

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

**Risk manager priority:** Capital preservation and crisis survival above all

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
