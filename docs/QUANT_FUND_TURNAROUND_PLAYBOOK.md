# Quantitative Fund Turnaround Playbook

*Compiled from real hedge fund turnaround cases and quantitative trading best practices*

---

## Table of Contents

1. [Famous Turnaround Cases](#1-famous-turnaround-cases)
2. [The Turnaround Playbook](#2-the-turnaround-playbook)
3. [Speed to Winners](#3-speed-to-winners)
4. [Anti-Patterns](#4-anti-patterns)
5. [Actionable Turnaround Plans](#5-actionable-turnaround-plans)
6. [Metrics Tracking Framework](#6-metrics-tracking-framework)

---

## 1. Famous Turnaround Cases

### 1.1 Renaissance Technologies — The Medallion Fund (1988-1990)

**The Crisis:**
- Founded 1978 as "Monemetrics," primarily trading currencies
- Established Medallion Fund in 1988 using Leonard Baum's mathematical models expanded by James Ax
- By April 1989, peak-to-trough losses hit ~30%

**What Went Wrong:**
- Models were based on correlations that didn't hold under stress
- Ax insisted models accounted for such declines and wanted to continue trading
- The team was using mathematical models that hadn't been validated across enough market regimes

**The Turnaround:**
1. **Leadership change**: Simons (majority owner) paused trading and replaced Ax with Elwyn Berlekamp (UC Berkeley professor)
2. **6-month system overhaul**: Berlekamp worked with Sandor Straus, Jim Simons, and Henry Laufer to overhaul Medallion's trading system
3. **Reduced leverage**: During the overhaul, the fund traded more conservatively
4. **Regime-aware modeling**: Expanded models to account for different market environments

**Results:**
- 1990: +55.9% net of fees
- 1991: +39.4%
- 1992: +34.0%
- 1993: +39.1%
- From 1994-2014: averaged 71.8% annual return before fees

**Key Lesson:** When models fail, don't double down. Pause, bring in fresh talent with different expertise, and rebuild the system from first principles. Renaissance hired people with non-financial backgrounds (physicists, mathematicians, computer scientists) rather than Wall Street veterans.

---

### 1.2 Bridgewater Associates — Pure Alpha (2008-2009)

**The Crisis:**
- Bridgewater's Pure Alpha fund navigated 2008 well (spared investors most of the meltdown)
- But in 2009, economic growth responded faster than anticipated
- Pure Alpha gained only 2-4% while the Dow surged 19%

**What Went Wrong:**
- The "d-process" (deleveraging/deflationary process) framework was too slow to adapt when the recovery came faster than expected
- Models were trained on historical data that didn't include this type of V-shaped recovery

**The Turnaround:**
1. **Radical transparency culture**: All meetings recorded, anyone can challenge anyone regardless of hierarchy
2. **Principle-based decision making**: Compiled hundreds of "decision rules" incorporated into computer analysis
3. **Separation of alpha and beta**: Maintained separate strategies for market exposure (beta) and skill-based returns (alpha)
4. **Systematic diversification**: 30-40 simultaneous uncorrelated positions across bonds, currencies, stock indexes, commodities
5. **Launched Pure Alpha Major Markets (2010)**: $10 billion fund with enhanced liquidity focus

**Results:**
- Pure Alpha II: historic average return of 10.4%, only three losing years
- 2022: Pure Alpha II posted 32% return in volatile bear market
- Remains largest hedge fund by AUM (~$124B as of 2024)

**Key Lesson:** Don't let a single bad year destroy conviction in a sound framework. Bridgewater's response was to double down on systematic diversification and radical transparency, not to abandon their approach.

---

### 1.3 Tiger Management — The Drawdown Before Closing (1998-2000)

**The Crisis:**
- Tiger Management was one of the largest hedge funds ($22B at peak)
- Julian Robertson's value-oriented approach suffered as tech bubble inflated
- 1999-2000: massive underperformance as growth stocks crushed value

**What Went Wrong:**
- **Style drift**: Robertson resisted tech but eventually capitulated near the top
- **Revenge trading**: Increased position sizes to "make back" losses
- **Investor redemptions**: As performance suffered, investors pulled money, forcing position liquidation at worst times
- **Ego**: Robertson refused to adapt the framework or acknowledge the regime change

**The Closing:**
- Robertson closed Tiger Management in March 2000 — just months before the tech bubble burst
- Had he held firm, value would have dramatically outperformed in 2000-2002

**Key Lesson:** The irony of Tiger is that Robertson's thesis was correct, but his execution was wrong. He couldn't survive the drawdown long enough to be proven right. **Survival is prerequisite to being right.**

---

### 1.4 Long-Term Capital Management (LTCM) — What Went Wrong (1998)

**The Crisis:**
- $4.7 billion equity, $124.5 billion borrowed, $1.25 trillion in derivative positions
- 25:1 debt-to-equity ratio
- Lost $4.6 billion in less than four months

**What LTCM Did Wrong:**
1. **Excessive leverage**: 25:1 ratio meant even small moves could wipe out equity
2. **Short historical data**: Models used only 5 years of data, missing 1987 crash, 1994 bond crisis, and the 1917 Russian default
3. **No stress testing**: VaR model implied the August loss "ought never to have happened in the entire life of the universe"
4. **Correlation assumption failure**: Assumed positions were uncorrelated, but in crisis everything correlated to 1
5. **Illiquidity risk**: Positions so large there was no diversity in buyers — "impossible to determine a price for its assets"
6. **Strategy drift**: Moved from core fixed-income arbitrage into emerging markets, merger arbitrage, and S&P 500 options — areas with no informational advantage
7. **Dependency on counterparties**: Required continuous repo financing to maintain positions

**What They Could Have Done:**
- Use 80+ years of data instead of 5 years
- Cap leverage at 10:1 instead of 25:1
- Maintain liquidity reserves for forced margin calls
- Stick to core competency (fixed-income arbitrage) rather than drifting into unfamiliar markets
- Stress test for 1987-style events, not just normal distributions
- Maintain counterparty diversification

**The Lesson:** Nobel Prize winners Scholes and Merton "knew plenty of mathematics, but not enough history." Models are only as good as the data they're trained on.

---

## 2. The Turnaround Playbook

### 2.1 First Thing a Struggling Fund Should Do

**IMMEDIATE (Week 1): STOP THE BLEEDING**

1. **Cut position sizes by 50-75%** across all strategies
   - Renaissance paused trading entirely in 1989
   - LTCM should have done this but didn't until forced

2. **Halt new strategy deployment**
   - No new positions, no new strategies, no new data sources
   - Freeze the portfolio at current (reduced) levels

3. **Conduct a full attribution analysis**
   - Which strategies are actually losing money?
   - Which asset classes contribute losses vs. returns?
   - Which timeframes show the most degradation?

4. **Separate signal from noise**
   - Is the system actually broken, or is this a normal drawdown?
   - Compare current performance to historical backtest expectations
   - Check if the market regime has changed

5. **Establish a war room**
   - Daily P&L review
   - Daily position review
   - Daily risk metrics review

### 2.2 How to Identify Which Strategies Are Actually Working

**Step 1: Strategy Decomposition**

Break down the 324 files into the ~5 unique ideas:

| Strategy Category | Files | Trades | Win Rate | Edge per Trade | Verdict |
|-------------------|-------|--------|----------|----------------|---------|
| Strategy A (momentum) | X | Y% | Z% | $W | Keep/Modify/Kill |
| Strategy B (mean reversion) | X | Y% | Z% | $W | Keep/Modify/Kill |
| Strategy C (breakout) | X | Y% | Z% | $W | Keep/Modify/Kill |
| Strategy D (pattern) | X | Y% | Z% | $W | Keep/Modify/Kill |
| Strategy E (sentiment) | X | Y% | Z% | $W | Keep/Modify/Kill |

**Step 2: Per-Asset-Class Analysis**

| Asset Class | Trades | Win Rate | Avg Win | Avg Loss | Expectancy | Sharpe |
|-------------|--------|----------|---------|----------|------------|--------|
| CRYPTO | | | | | | |
| FOREX | | | | | | |
| EQUITY | | | | | | |
| COMMODITY | | | | | | |

**Step 3: Source Analysis**

| Source | % of Picks | Win Rate | Quality Score |
|--------|-----------|----------|---------------|
| kimi_riseoftheclaw | 76% | 28.4% | |
| Source B | X% | Y% | |
| Source C | X% | Y% | |
| Source D | X% | Y% | |

**Key Insight from Renaissance:** They didn't try to fix everything. They brought in fresh expertise (Berlekamp), overhauled the core system in 6 months, and came out stronger. The key was identifying the ~5 unique ideas vs. the 324 files of variations.

### 2.3 How to Cut Losers Without Missing the Rebound

**The Core Problem:**
- Cutting a strategy right before it rebounds = missed opportunity
- Keeping a losing strategy too long = death by a thousand cuts

**The Solution: Regime-Conditional Position Sizing**

1. **Define regime triggers:**
   - "If VIX > 30 and correlation > 0.7, reduce Strategy X by 75%"
   - "If BTC is in a downtrend (below 50-day MA), reduce CRYPTO strategies by 50%"
   - "If yield curve inverts, reduce EQUITY strategies by 60%"

2. **Use time-based stops:**
   - If a strategy underperforms for 20 trading days, reduce size by 50%
   - If it underperforms for 40 trading days, reduce to minimum size (10%)
   - If it underperforms for 60 trading days, pause entirely

3. **Scale out, don't dump:**
   - Week 1: Reduce by 25%
   - Week 2: Reduce by another 25% (total: 50%)
   - Week 3: Reduce by another 25% (total: 75%)
   - Week 4: If still losing, reduce to 10% (minimum)

4. **Maintain a "watch list" of paused strategies:**
   - Review weekly for regime changes that might reactivate them
   - Renaissance kept strategies in reserve and brought them back when conditions changed

### 2.4 Position Sizing During Recovery

**The Kelly Criterion (Modified for Recovery):**

```
f* = (p × b - q) / b

Where:
f* = optimal fraction of capital to risk
p = win probability
b = average win / average loss
q = 1 - p
```

**Recovery-Specific Adjustments:**

1. **Start at 25% of Kelly:**
   - During drawdowns, reduce position sizes dramatically
   - Kelly suggests optimal, but you need survival margin
   - 25% Kelly = "fractional Kelly" for safety

2. **Scale up linearly with equity:**
   - For every 5% recovery in equity, increase position size by 10%
   - Never exceed 50% of original position sizes until full recovery

3. **Hard limits during recovery:**
   - Maximum 2% risk per trade (down from whatever it was)
   - Maximum 10% portfolio risk at any time
   - Maximum 20% in any single asset class

**Bridgewater's Approach:** They use risk parity — equal risk contribution from each position, not equal dollar amounts. This naturally scales positions based on volatility.

### 2.5 Risk Management During Turnaround

**Daily Risk Metrics (Non-Negotiable):**

1. **Value at Risk (VaR) — 95% and 99%**
   - Must be calculated on 80+ years of data (LTCM lesson), not just 5 years

2. **Maximum Drawdown Tracking**
   - Current drawdown vs. historical max drawdown
   - If current exceeds 75% of historical max, cut all positions by 50%

3. **Correlation Monitoring**
   - Are your strategies becoming correlated? (LTCM's fatal flaw)
   - If average cross-strategy correlation > 0.5, reduce leverage

4. **Liquidity Monitoring**
   - Can you exit all positions within 5 trading days without >2% slippage?
   - If not, you're over-leveraged

5. **Counterparty Exposure**
   - No single counterparty > 15% of total exposure
   - LTCM's dependency on repo financing was fatal

**Weekly Risk Reviews:**

1. Stress test against 1987, 1998, 2008, 2020 scenarios
2. Review position concentration limits
3. Review strategy correlation matrix
4. Review liquidity conditions in all markets

**Monthly Risk Reviews:**

1. Full historical backtest with updated data
2. Regime detection analysis (are we in a new regime?)
3. Model validation against out-of-sample data
4. Leverage review and adjustment

---

## 3. Speed to Winners

### 3.1 How Funds Find Winning Strategies FAST

**Renaissance's Approach:**
1. Hire non-traditional talent (physicists, mathematicians, computer scientists)
2. Use massive datasets (petabyte-scale)
3. Focus on finding non-random movements, not predicting direction
4. Automate everything — remove human emotion
5. Low personnel turnover = institutional knowledge preserved

**Bridgewater's Approach:**
1. "Radical transparency" — every decision is recorded and reviewable
2. Decision rules compiled into computer systems
3. Hire from elite universities, train from scratch
4. All meetings recorded for institutional learning

**Practical Steps for Your System:**

1. **Create a strategy incubator:**
   - Deploy new strategies at minimum size (0.1% of capital)
   - Run for 60 trading days
   - Promote to 1% if Sharpe > 1.0 and win rate > 45%
   - Promote to 5% if Sharpe > 1.5 and win rate > 50%
   - Kill if Sharpe < 0.5 after 60 days

2. **Run parallel testing:**
   - Backtest on 80+ years of data (not 5)
   - Out-of-sample test on 30% of data
   - Walk-forward optimization
   - Monte Carlo simulation (1000+ runs)

3. **Use ensemble methods:**
   - Don't rely on single strategies
   - Combine 5-10 uncorrelated strategies
   - Equal weight or risk-parity allocation

### 3.2 Minimum Sample Size for Strategy Validation

**Statistical Significance Framework:**

| Metric | Minimum Required | Ideal | Notes |
|--------|-----------------|-------|-------|
| Trades | 200 | 500+ | Fewer trades = higher noise |
| Trading Days | 250 (1 year) | 500+ (2 years) | Must include different regimes |
| Win Rate Confidence | p < 0.05 | p < 0.01 | Statistical significance test |
| Sharpe Ratio | > 1.0 | > 1.5 | Risk-adjusted return |
| Profit Factor | > 1.2 | > 1.5 | Gross wins / gross losses |
| Max Drawdown | < 20% | < 15% | From peak to trough |

**The 5-Strategy Problem in Your System:**

With 5 unique ideas across 324 files, you likely have:
- 1-2 strategies with genuine edge
- 2-3 strategies that are noise
- 1 strategy that's actively destroying value (likely the kimi_riseoftheclaw at 28.4% WR producing 76% of picks)

**Action:** Run statistical significance tests on each of the 5 core ideas. The one with p > 0.10 is probably random.

### 3.3 Exploration vs. Exploitation

**The Multi-Armed Bandit Problem:**

In quantitative trading, you're constantly choosing between:
- **Exploitation**: Running known winning strategies with larger sizes
- **Exploration**: Testing new strategies that might be better

**The Optimal Balance:**

| Phase | Exploration % | Exploitation % | Duration |
|-------|---------------|----------------|----------|
| Crisis (current) | 20% | 80% | 30 days |
| Stabilization | 30% | 70% | 60 days |
| Growth | 40% | 60% | Ongoing |

**Implementation:**

1. Allocate 80% of capital to proven strategies
2. Allocate 20% to strategy incubator
3. Promote winners from incubator monthly
4. Kill losers from incubator every 60 days

**From Renaissance:** They constantly search for new signals while maintaining existing profitable strategies. The key is that new strategies start at tiny size and only scale up with proven edge.

### 3.4 Role of Alternative Data

**Modern Edge Sources:**

1. **Satellite imagery**: Track physical activity (parking lots, oil storage, shipping)
2. **Social media sentiment**: Real-time mood analysis
3. **Web scraping**: Job postings, product reviews, patent filings
4. **Supply chain data**: Track B2B transactions
5. **Credit card data**: Real-time consumer spending
6. **IoT sensors**: Weather, traffic, energy consumption
7. **NLP on filings**: SEC filings, earnings calls, news

**Renaissance's Data Advantage:**
- Petabyte-scale data warehouse
- Non-financial data (weather, politics, social trends)
- "Staff attribute the breadth of data on events peripheral to financial and economic phenomena"

**For Your System:**
- Don't add more data until you've fixed the core strategies
- Data doesn't fix bad models — it makes them more precisely wrong
- Fix the 5 strategies first, then consider data expansion

---

## 4. Anti-Patterns

### 4.1 What Struggling Funds Do WRONG

**Anti-Pattern 1: Doubling Down**
- "If I just increase position size, I'll make back my losses faster"
- LTCM did this: increased leverage as losses mounted
- Result: 25:1 leverage → 250:1 effective leverage → bankruptcy

**Anti-Pattern 2: Strategy Hopping**
- "This strategy isn't working, let me try something completely new"
- Result: You abandon strategies right before they recover
- Tiger Management did this — abandoned value too late, then capitulated at the worst time

**Anti-Pattern 3: Adding Complexity**
- "I need more indicators, more filters, more parameters"
- Result: Overfitting increases, out-of-sample performance decreases
- 324 files for 5 ideas = massive overfitting risk

**Anti-Pattern 4: Revenge Trading**
- "I need to make back what I lost"
- Result: Larger positions, worse entries, emotional decisions
- This is how drawdowns become blowups

**Anti-Pattern 5: Ignoring Regime Changes**
- "The market will come back to normal"
- Result: Strategies that worked in one regime fail in another
- Bridgewater's 2009 underperformance was exactly this

### 4.2 How Overfitting Happens During Turnaround

**The Overfitting Trap:**

When a fund is losing money, there's pressure to "fix" the system. This leads to:

1. **Adding parameters to explain losses**
   - "Let me add a filter for high VIX environments"
   - "Let me add a time-of-day filter"
   - "Let me add a correlation filter"

2. **Curve-fitting to recent data**
   - Optimizing on the last 6 months of losses
   - This makes the system perfectly fit the past and fail in the future

3. **Data snooping**
   - Testing 100 variations and picking the one that works
   - With 324 files, this is almost certainly happening

**How to Prevent It:**

1. **Out-of-sample validation**: Always test on data the model hasn't seen
2. **Cross-validation**: Split data into 10 folds, test on each
3. **Minimum backtest length**: 10+ years including multiple regimes
4. **Parameter stability**: If changing a parameter by 10% changes results by 50%, it's overfit
5. **Parsimony**: Prefer fewer parameters. A 3-parameter model that works is better than a 30-parameter model that works better in backtest

### 4.3 How Position Sizing Destroys Funds

**The Kelly Criterion Failure Mode:**

```
Optimal f* = 20% of bankroll
Actual bet = 40% (overbetting by 2x)
Expected result: Ruin 100% of the time in the long run
```

**Real-World Examples:**

| Fund | Leverage | Result |
|------|----------|--------|
| LTCM | 25:1 | Bankruptcy |
| Archegos | 5:1 (hidden) | $20B+ loss |
| Melvin Capital | 6:1 (GME) | Needed $2.75B bailout |
| Your System | ? | 32.3% WR = losing money |

**Position Sizing Rules During Recovery:**

1. **Never risk more than 1% per trade**
2. **Never have more than 10% at risk simultaneously**
3. **Never exceed 3:1 leverage**
4. **Always maintain 20% cash buffer**
5. **Reduce size when equity is declining, increase when growing**

### 4.4 The Revenge Trading Trap

**Cycle of Revenge Trading:**

```
Loss → Emotional Decision → Larger Position → Bigger Loss → More Emotional Decisions → Blowup
```

**How to Break the Cycle:**

1. **Mandatory cool-down period**: After 3 consecutive losses, no trading for 24 hours
2. **Hard loss limits**: Daily loss limit of 2%, weekly 5%, monthly 10%
3. **Automated position sizing**: Remove human judgment from sizing decisions
4. **Trading journal**: Record every decision with rationale
5. **Accountability partner**: Someone reviews all trades weekly

---

## 5. Actionable Turnaround Plans

### 5.1 30-Day Turnaround Plan

**Week 1: Emergency Stabilization**

| Day | Action | Owner | Deliverable |
|-----|--------|-------|-------------|
| 1 | Reduce all position sizes by 50% | Risk Manager | Updated portfolio |
| 2 | Full attribution analysis | Quant Researcher | Attribution report |
| 3 | Identify top 5 losing strategies | Quant Researcher | Kill list |
| 4 | Pause all strategies with WR < 35% | Risk Manager | Paused strategies list |
| 5 | Review correlation matrix | Quant Researcher | Correlation report |
| 6-7 | Weekend: Regime analysis | Lead Quant | Regime report |

**Week 2: Strategy Diagnosis**

| Day | Action | Owner | Deliverable |
|-----|--------|-------|-------------|
| 8-9 | Backtest each of 5 core ideas | Quant Researcher | Backtest reports |
| 10 | Statistical significance testing | Quant Researcher | p-values for each strategy |
| 11 | Walk-forward validation | Quant Researcher | OOS performance |
| 12 | Source analysis (kimi_riseoftheclaw) | Quant Researcher | Source quality report |
| 13-14 | Weekend: Decision meeting | All | Strategy keep/kill decisions |

**Week 3: Rebuild Core**

| Day | Action | Owner | Deliverable |
|-----|--------|-------|-------------|
| 15-16 | Redesign top 2 strategies | Lead Quant | New strategy code |
| 17 | Stress test new strategies | Quant Researcher | Stress test results |
| 18 | Deploy at minimum size (0.1%) | Risk Manager | Live test begins |
| 19-21 | Monitor and adjust | All | Daily reports |

**Week 4: Stabilize**

| Day | Action | Owner | Deliverable |
|-----|--------|-------|-------------|
| 22-24 | Review live test results | All | Performance report |
| 25-26 | Scale up winning strategies | Risk Manager | Updated portfolio |
| 27-28 | Kill remaining losers | Risk Manager | Cleaned portfolio |
| 29-30 | Document everything | Lead Quant | Turnaround report |

**30-Day Targets:**
- Reduce position count by 60% (from 324 to ~130)
- Achieve Sharpe > 0.5 (from negative)
- Max drawdown < 5% for the month
- Win rate > 40% (from 32.3%)

### 5.2 90-Day Turnaround Plan

**Month 1: Stabilization (Days 1-30)**
- Follow 30-day plan above
- Target: Break-even month

**Month 2: Optimization (Days 31-60)**

| Week | Action | Deliverable |
|------|--------|-------------|
| 5 | Walk-forward optimization of top 2 strategies | Optimized parameters |
| 6 | Add strategy #3 from incubator | 3 strategies running |
| 7 | Correlation rebalancing | Risk parity allocation |
| 8 | First monthly review | Monthly performance report |

**Month 3: Growth (Days 61-90)**

| Week | Action | Deliverable |
|------|--------|-------------|
| 9 | Scale up strategies to 50% of target size | Updated portfolio |
| 10 | Add strategy #4 from incubator | 4 strategies running |
| 11 | Implement alternative data (if ready) | Data pipeline |
| 12 | Full 90-day review | Comprehensive report |

**90-Day Targets:**
- Sharpe > 1.0
- Win rate > 45%
- Max drawdown < 10% (for the period)
- 4-5 strategies running at moderate size
- Positive expectancy across all asset classes

### 5.3 1-Year Turnaround Plan

**Quarter 1: Foundation (Months 1-3)**
- Complete stabilization
- Rebuild core strategies
- Establish risk framework
- Target: Break-even quarter

**Quarter 2: Validation (Months 4-6)**
- Full backtesting suite running
- Walk-forward validation complete
- Alternative data integrated
- Target: 5% return, Sharpe > 1.0

**Quarter 3: Scaling (Months 7-9)**
- Scale positions to full size
- Add 2-3 new strategies from incubator
- Optimize across all asset classes
- Target: 8% return, Sharpe > 1.5

**Quarter 4: Optimization (Months 10-12)**
- Fine-tune all strategies
- Reduce correlation between strategies
- Build ensemble model
- Target: 10% return, Sharpe > 1.5, max drawdown < 15%

**1-Year Targets:**
- Cumulative return > 20%
- Sharpe ratio > 1.5
- Win rate > 50%
- Max drawdown < 15%
- 8-10 strategies running
- All asset classes profitable
- System fully automated

---

## 6. Metrics Tracking Framework

### 6.1 Daily Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Daily P&L | > 0 | < -2% |
| Win Rate (trailing 20 trades) | > 45% | < 35% |
| Average Win / Average Loss | > 1.2 | < 1.0 |
| Max Position Size | < 2% of equity | > 3% |
| Total Portfolio Heat | < 10% | > 15% |
| Cash Buffer | > 20% | < 15% |
| VaR (95%, 1-day) | < 2% | > 3% |
| Correlation (top 2 strategies) | < 0.3 | > 0.5 |

### 6.2 Weekly Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Weekly Return | > 0 | < -3% |
| Sharpe (trailing 20 days) | > 1.0 | < 0.5 |
| Profit Factor (trailing 50 trades) | > 1.3 | < 1.0 |
| Strategy Count (active) | 5-10 | < 3 or > 15 |
| Strategy Win Rates (each) | > 45% | < 35% |
| Cross-Strategy Correlation | < 0.3 | > 0.5 |
| Liquidity Score | > 8/10 | < 6/10 |

### 6.3 Monthly Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Monthly Return | > 1.5% | < -5% |
| Sharpe (trailing 60 days) | > 1.2 | < 0.7 |
| Max Drawdown (trailing 30 days) | < 5% | > 8% |
| Max Drawdown (trailing 90 days) | < 10% | > 15% |
| Win Rate (trailing 200 trades) | > 48% | < 40% |
| Strategy Attribution | Balanced | > 60% from 1 strategy |
| Asset Class Attribution | Balanced | > 50% from 1 class |
| New Strategy Incubation | 2-3 in test | 0 or > 5 |

### 6.4 Quarterly Review Checklist

- [ ] Full backtest with updated data (80+ years)
- [ ] Walk-forward validation complete
- [ ] Correlation matrix reviewed
- [ ] Stress test against 1987, 1998, 2008, 2020 scenarios
- [ ] Liquidity analysis for all positions
- [ ] Counterparty exposure review
- [ ] Strategy retirement decisions
- [ ] New strategy promotion decisions
- [ ] Position sizing recalibration
- [ ] Risk limit review and adjustment
- [ ] Team performance review
- [ ] Documentation update

### 6.5 Scorecard Template

```
WEEKLY TURNAROUND SCORECARD
===========================
Date: ___________
Week # : ___________

PERFORMANCE
- Weekly Return: _____% (Target: > 0%)
- Trailing 20d Sharpe: _____ (Target: > 1.0)
- Win Rate (20 trades): _____% (Target: > 45%)
- Max Drawdown (current): _____% (Target: < 5%)

RISK
- VaR 95% 1-day: _____% (Target: < 2%)
- Portfolio Heat: _____% (Target: < 10%)
- Cash Buffer: _____% (Target: > 20%)
- Max Correlation: _____ (Target: < 0.3)

STRATEGIES
- Active Strategies: _____ (Target: 5-10)
- Strategies in Incubation: _____
- Strategies Paused: _____
- Strategies Killed This Week: _____

ASSET CLASS BALANCE
- CRYPTO: _____% of P&L
- FOREX: _____% of P&L
- EQUITY: _____% of P&L
- COMMODITY: _____% of P&L

SOURCE QUALITY
- kimi_riseoftheclaw: _____% of picks, _____% WR
- Other sources: _____% of picks, _____% WR

SCORE: ___/10 (Target: > 7/10)
```

---

## Appendix A: Key Principles Summary

1. **Stop first, fix second** — Never try to fix a bleeding portfolio while it's still bleeding
2. **Simple beats complex** — 5 strategies > 324 files
3. **Data over instinct** — Renaissance hired scientists, not traders
4. **Survive first, profit second** — Tiger was right but didn't survive
5. **Leverage kills** — LTCM's 25:1 was suicide
6. **Diversify truly** — Correlated strategies aren't diversified (LTCM lesson)
7. **Test with history** — Use 80+ years, not 5 (LTCM lesson)
8. **Hire for expertise, not pedigree** — Renaissance hired physicists and mathematicians
9. **Transparency wins** — Bridgewater's radical transparency catches mistakes early
10. **The market will be there tomorrow** — Don't risk everything today

---

## Appendix B: Recommended Reading

1. *The Man Who Solved the Market* by Gregory Zuckerman — Renaissance Technologies story
2. *Principles* by Ray Dalio — Bridgewater's decision framework
3. *When Genius Failed* by Roger Lowenstein — LTCM collapse
4. *The Quants* by Scott Patterson — Quantitative trading revolution
5. *The Ascent of Money* by Niall Ferguson — Financial history including LTCM
6. *Market Wizards* by Jack Schwager — Interviews with top traders

---

*Document created: 2026-06-12*
*Purpose: Turnaround playbook for quantitative trading system with 32.3% win rate*
*Status: Reference document — implement based on specific system characteristics*
