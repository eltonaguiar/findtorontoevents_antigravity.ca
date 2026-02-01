# STOCKSUNIFY User Value Protocol

## Maximizing Value for Stock System Users & Algorithm Evaluators

**Version:** 1.0  
**Created:** 2026-01-28  
**Purpose:** A comprehensive protocol to translate algorithmic stock picks into actionable, understandable guidance for users of all experience levels.

---

## Table of Contents

1. [User Personas & Their Needs](#1-user-personas--their-needs)
2. [The Winning Picks Explanation Framework](#2-the-winning-picks-explanation-framework)
3. [Trade Specification Standards](#3-trade-specification-standards)
4. [Risk Communication Framework](#4-risk-communication-framework)
5. [Performance Transparency Requirements](#5-performance-transparency-requirements)
6. [Budget-Specific Portfolio Guidance](#6-budget-specific-portfolio-guidance)
7. [Algorithm Evaluator Requirements](#7-algorithm-evaluator-requirements)
8. [Website & GitHub Update Checklist](#8-website--github-update-checklist)

---

## 1. User Personas & Their Needs

### Persona A: The Beginner Investor
**Profile:**
- New to stock market investing
- Budget: $500 - $5,000
- Time commitment: Part-time, checks portfolio weekly
- Risk tolerance: Low to Medium
- Goals: Learn while growing wealth steadily

**What They Need:**
- Plain English explanations (no jargon)
- Clear "why" behind each pick
- Simple entry/exit instructions
- Risk warnings in understandable terms
- Confidence level as a simple rating (1-5 stars)
- "What could go wrong" scenarios

**Key Questions They Ask:**
1. "Should I buy this stock?"
2. "How much money could I lose?"
3. "When should I sell?"
4. "Is this safe?"

---

### Persona B: The Active Trader
**Profile:**
- Experienced with technical analysis
- Budget: $10,000 - $100,000+
- Time commitment: Daily monitoring
- Risk tolerance: Medium to High
- Goals: Short-term profits, momentum plays

**What They Need:**
- Precise entry price (with slippage consideration)
- Exact stop-loss and take-profit levels
- Risk/reward ratio
- Position sizing recommendations
- Key support/resistance levels
- Catalyst identification
- Volume analysis
- Timeframe clarity (day trade vs swing trade)

**Key Questions They Ask:**
1. "What's my entry and exit?"
2. "What's the R:R ratio?"
3. "What's the catalyst?"
4. "Position size for my account?"

---

### Persona C: The Long-Term Investor
**Profile:**
- Fundamental-focused, buy-and-hold mentality
- Budget: $25,000 - $500,000+
- Time commitment: Monthly review
- Risk tolerance: Medium
- Goals: Wealth accumulation, retirement planning

**What They Need:**
- Fundamental analysis context (PE, growth, sector outlook)
- Long-term trend assessment
- Dividend information (if applicable)
- Sector rotation context
- Macro environment considerations
- Portfolio fit assessment
- Quality vs. value classification

**Key Questions They Ask:**
1. "Is this company fundamentally sound?"
2. "Where does this fit in my portfolio?"
3. "What's the 1-year outlook?"
4. "How does this compare to holding SPY?"

---

### Persona D: The Algorithm Evaluator
**Profile:**
- Quantitative analyst, researcher, or skeptic
- Looking to validate/replicate methodology
- Needs statistical rigor and transparency

**What They Need:**
- Complete methodology documentation
- Historical performance data with statistical metrics
- Sharpe ratio, Sortino ratio, max drawdown
- Win rate by algorithm and timeframe
- Out-of-sample validation results
- Source code references (for open-source components)
- Immutable audit trail proof

**Key Questions They Ask:**
1. "What's the historical win rate?"
2. "What's the Sharpe ratio?"
3. "How do you prevent overfitting?"
4. "Can I verify these results independently?"

---

## 2. The Winning Picks Explanation Framework

Every stock pick MUST include explanations tailored to all user personas. This is the **mandatory template** for all picks:

---

### PICK EXPLANATION TEMPLATE

```markdown
# [RATING] [SYMBOL] - [COMPANY NAME]
**Pick Date:** YYYY-MM-DD | **Algorithm:** [Algorithm Name] | **Score:** XX/100

---

## Quick Summary (For Everyone)

> **One-sentence verdict:** [Plain English explanation of why this stock was picked]
>
> **Confidence Level:** [1-5 stars] [Confidence word: Low/Medium/High/Very High]
>
> **Best For:** [Beginner / Trader / Investor / All]

---

## The Trade Plan (For Active Traders)

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Position Type** | LONG / SHORT | Direction of the trade |
| **Time Horizon** | 24h / 3d / 7d / 1m / 3m / 1y | Recommended holding period |
| **Entry Price** | $XX.XX | Includes +0.5% slippage simulation |
| **Stop Loss** | $XX.XX | Exit if price falls below this |
| **Take Profit Target** | $XX.XX | Suggested exit for gains |
| **Risk/Reward Ratio** | X:X | Potential gain vs. potential loss |
| **Max Position Size** | X% of portfolio | Never exceed this allocation |

### Key Levels to Watch
- **Support:** $XX.XX (20-day low)
- **Resistance:** $XX.XX (52-week high)
- **Breakout Confirmation:** Price > $XX.XX with volume > Xm

---

## Why We Picked This Stock (Plain English)

### For Beginners:
[2-3 sentences explaining in simple terms why this stock was selected. 
Avoid jargon. Use analogies if helpful.]

**Example:** "Think of this like a sale at your favorite store. The stock price 
dipped recently, but the company is still healthy and strong. We expect the 
price to bounce back up, like it usually does after short dips."

### What Could Go Wrong:
[Honest assessment of risks in plain English]

1. **Risk 1:** [Description] - Likelihood: [Low/Medium/High]
2. **Risk 2:** [Description] - Likelihood: [Low/Medium/High]

---

## Technical Analysis (For Traders)

### Signal Strength Summary
| Indicator | Value | Signal | Contribution |
|-----------|-------|--------|--------------|
| RSI (14) | XX.X | Bullish/Bearish/Neutral | [Interpretation] |
| ADX (14) | XX.X | Strong/Weak Trend | [Interpretation] |
| Volume Z-Score | X.XX | Above/Below Average | [Interpretation] |
| Bollinger Squeeze | Yes/No | [Setup status] | [Interpretation] |
| VCP Pattern | Yes/No | [Consolidation status] | [Interpretation] |
| Inst. Footprint | Yes/No | [Accumulation detected] | [Interpretation] |

### Price Structure
- **Trend:** Uptrend / Downtrend / Sideways
- **Stage:** Stage 1 (Base) / Stage 2 (Uptrend) / Stage 3 (Top) / Stage 4 (Decline)
- **Pattern:** [Breakout / Pullback / Reversal / Continuation]

---

## Fundamental Context (For Long-Term Investors)

| Metric | Value | Assessment |
|--------|-------|------------|
| Market Cap | $XXB | [Large/Mid/Small Cap] |
| P/E Ratio | XX.X | [Undervalued/Fair/Overvalued] |
| Sector | [Sector Name] | [Sector outlook] |
| YTD Performance | +XX.X% | [vs. S&P 500: XX.X%] |
| Dividend Yield | X.XX% | [If applicable] |

### Long-Term Outlook
[2-3 sentences on the company's fundamental position and 6-12 month outlook]

---

## Confidence & Certainty Assessment

### Algorithm Confidence Breakdown
| Factor | Score | Weight | Contribution |
|--------|-------|--------|--------------|
| Technical Setup | XX/100 | 30% | XX points |
| Momentum | XX/100 | 25% | XX points |
| Volume Confirmation | XX/100 | 20% | XX points |
| Trend Alignment | XX/100 | 15% | XX points |
| Risk/Reward | XX/100 | 10% | XX points |
| **Total** | **XX/100** | 100% | **[Rating]** |

### Historical Accuracy Context
- **This Algorithm's Win Rate:** XX% (last 30 days)
- **Similar Setups Win Rate:** XX% (all-time)
- **Market Regime Adjustment:** [Bull market boost / Bear market penalty applied]

### Certainty Classification
| Certainty Level | Meaning | Recommended Position Size |
|-----------------|---------|---------------------------|
| Very High (90+) | Strong conviction, multiple confirming signals | Up to 5% of portfolio |
| High (80-89) | Good setup, most signals aligned | Up to 3% of portfolio |
| Medium (65-79) | Decent setup, some concerns | Up to 2% of portfolio |
| Lower (50-64) | Speculative, use caution | Up to 1% of portfolio |

**This Pick's Certainty:** [Level] - [Recommended Position Size]

---

## Audit & Verification

- **Pick Hash (SHA-256):** `[64-character hash]`
- **Timestamp (UTC):** YYYY-MM-DDTHH:MM:SS.SSSZ
- **Market Regime at Pick:** [BULL/BEAR/NEUTRAL]
- **Verification Date:** [When this pick will be verified]
- **Ledger Location:** `data/picks-archive/YYYY-MM-DD.json`

---

## Disclaimer

This pick is generated by an algorithmic system and is for **informational purposes only**. 
It does not constitute financial advice. Past performance does not guarantee future results. 
Always conduct your own research and consult with a licensed financial advisor before 
making investment decisions. Never invest more than you can afford to lose.
```

---

## 3. Trade Specification Standards

### Position Types Explained

| Position | What It Means | When Used |
|----------|---------------|-----------|
| **LONG** | Buy the stock, profit when price goes UP | Bullish outlook |
| **SHORT** | Borrow and sell, profit when price goes DOWN | Bearish outlook (advanced) |

**Note:** Our system currently only generates LONG positions. SHORT positions require margin accounts and carry higher risk.

---

### Timeframe Classifications

| Timeframe | Label | Typical Holding | Best For |
|-----------|-------|-----------------|----------|
| **24h** | Day Trade / Scalp | 1 day | Active traders, high-volume stocks |
| **3d** | Swing Trade (Short) | 2-4 days | Momentum players, breakout traders |
| **7d** | Swing Trade (Medium) | 5-10 days | Swing traders, pattern completion |
| **1m** | Position Trade | 2-6 weeks | Part-time traders, trend followers |
| **3m** | Investment (Short) | 1-4 months | Active investors, sector plays |
| **6m** | Investment (Medium) | 3-8 months | Growth investors, earnings cycles |
| **1y** | Investment (Long) | 6-18 months | Long-term investors, value plays |

---

### Entry Price Calculation

All entry prices include a **+0.5% slippage simulation** to account for:
- Bid/ask spread
- Market impact
- Execution timing

**Formula:**
```
Simulated Entry = Current Price * 1.005
```

**Example:**
- Current Price: $100.00
- Simulated Entry: $100.50

This provides more realistic performance tracking.

---

### Stop Loss Calculation

Stop losses are calculated using **ATR (Average True Range)** methodology:

| Risk Level | ATR Multiplier | Description |
|------------|----------------|-------------|
| Conservative | 1.0x ATR | Tighter stop, higher chance of being stopped out |
| Standard | 1.5x ATR | Balanced approach |
| Aggressive | 2.0x ATR | Wider stop, more room for volatility |

**Formula:**
```
Stop Loss = Entry Price - (ATR * Multiplier)
```

**Example (Standard):**
- Entry: $100.00
- ATR: $3.00
- Stop Loss: $100.00 - ($3.00 * 1.5) = $95.50

---

### Take Profit Calculation

Take profit targets are set based on Risk/Reward ratios:

| Strategy | R:R Target | Risk Tolerance |
|----------|------------|----------------|
| Conservative | 1.5:1 | Lower profit, higher probability |
| Standard | 2:1 | Balanced approach |
| Aggressive | 3:1 | Higher profit target, lower probability |

**Formula:**
```
Take Profit = Entry + (Risk Amount * R:R Ratio)
Risk Amount = Entry - Stop Loss
```

**Example (Standard 2:1):**
- Entry: $100.00
- Stop Loss: $95.50 (Risk = $4.50)
- Take Profit: $100.00 + ($4.50 * 2) = $109.00

---

## 4. Risk Communication Framework

### Risk Level Definitions

| Risk Level | Score Threshold | Description | Suitable For |
|------------|-----------------|-------------|--------------|
| **Low** | Any stock > $50B market cap, < 1.5 ATR/price ratio | Stable, blue-chip stocks | Beginners, conservative investors |
| **Medium** | $10B-$50B market cap, moderate volatility | Established companies with some volatility | Most investors |
| **High** | $1B-$10B market cap, or > 3% daily swings | Growth stocks, momentum plays | Experienced traders |
| **Very High** | < $1B market cap, penny stocks, > 5% daily swings | Speculative, high-volatility | Advanced traders only |

---

### Risk Warning Templates

**For Very High Risk Picks:**
```
RISK WARNING: This is a VERY HIGH RISK pick. It involves a speculative 
stock that can experience extreme price swings of 10%+ in a single day. 
You could lose 50% or more of your investment quickly. Only allocate 
money you can afford to lose completely. This is NOT suitable for beginners 
or retirement accounts.
```

**For High Risk Picks:**
```
CAUTION: This is a HIGH RISK pick. The stock has above-average volatility 
and could decline significantly before reaching the target. Use strict 
stop-losses and limit position size to 2-3% of your portfolio maximum.
```

**For Medium Risk Picks:**
```
NOTE: This pick carries MODERATE RISK typical of stock market investing. 
While the company is established, all stocks can decline. Use the 
recommended stop-loss and don't exceed 3-5% of your portfolio.
```

**For Low Risk Picks:**
```
This pick is classified as LOWER RISK due to the company's size and 
stability. However, no stock investment is truly "safe." Market-wide 
downturns can affect even the largest companies. Always diversify.
```

---

### What Could Go Wrong - Standard Scenarios

Every pick must address these potential failure scenarios:

1. **Market-Wide Selloff**
   - Description: The entire market drops 5%+ due to macro events
   - Impact on this trade: [Assessment]
   - Mitigation: Use stop-loss, don't over-allocate

2. **Sector Rotation**
   - Description: Investors move money out of this sector
   - Impact on this trade: [Assessment]
   - Mitigation: Monitor sector ETF performance

3. **Company-Specific News**
   - Description: Negative earnings, scandal, downgrade
   - Impact on this trade: [Assessment]
   - Mitigation: Keep position sizes reasonable

4. **Technical Breakdown**
   - Description: Price breaks below key support levels
   - Impact on this trade: Stop-loss triggered, exit trade
   - Mitigation: Honor your stop-loss, don't "hope"

5. **Liquidity Issues** (for smaller stocks)
   - Description: Can't sell at desired price due to low volume
   - Impact on this trade: [Assessment]
   - Mitigation: Trade during market hours, use limit orders

---

## 5. Performance Transparency Requirements

### Minimum Disclosure Requirements

Every public-facing page (website, GitHub) MUST display:

1. **Win Rate by Algorithm** (updated weekly)
   ```
   Algorithm Performance (Last 30 Days):
   - Alpha Predator: 67% win rate (12 wins / 18 total)
   - Technical Momentum: 58% win rate (7 wins / 12 total)
   - CAN SLIM: 62% win rate (5 wins / 8 total)
   - Composite Rating: 55% win rate (6 wins / 11 total)
   ```

2. **Average Return** (by rating category)
   ```
   Average Returns by Rating:
   - STRONG BUY: +4.2% average (last 30 days)
   - BUY: +1.8% average (last 30 days)
   - HOLD: -0.5% average (last 30 days)
   ```

3. **Benchmark Comparison**
   ```
   STOCKSUNIFY vs. S&P 500 (Last 30 Days):
   - Our Picks: +3.4% average return
   - S&P 500: +2.1%
   - Alpha Generated: +1.3%
   ```

4. **Max Drawdown Warning**
   ```
   Risk Disclosure:
   - Largest single-pick loss: -12.3% (XYZ on 2026-01-15)
   - Average losing trade: -3.8%
   - Win/Loss Ratio: 1.8:1
   ```

5. **Sample Size Disclosure**
   ```
   Data Reliability Note:
   - Total verified picks: 147
   - Verification period: 45 days
   - Statistical significance: Medium (need 200+ for high confidence)
   ```

---

### Performance Dashboard Components

The website and GitHub should display:

| Component | Description | Update Frequency |
|-----------|-------------|------------------|
| Live Win Rate Gauge | Visual representation of current win rate | Real-time |
| Algorithm Leaderboard | Ranking of algorithms by performance | Weekly |
| Recent Winners | Last 5 verified winning picks with returns | Daily |
| Recent Losers | Last 5 verified losing picks with returns | Daily |
| Equity Curve Chart | Simulated portfolio growth over time | Weekly |
| Drawdown Chart | Maximum peak-to-trough decline | Weekly |
| Risk-Adjusted Returns | Sharpe ratio, Sortino ratio | Monthly |

---

## 6. Budget-Specific Portfolio Guidance

### Small Budget ($500 - $5,000)

**Recommended Approach:**
- Focus on 3-5 positions maximum
- Prioritize LOWER and MEDIUM risk picks
- Avoid penny stocks (high volatility wipes small accounts)
- Use fractional shares for expensive stocks
- Consider ETFs for diversification

**Position Sizing:**
```
Account: $2,000
Max per position: $400-500 (20-25%)
Number of positions: 4-5

Example Allocation:
- Position 1 (Low Risk): $500 (25%)
- Position 2 (Medium Risk): $400 (20%)
- Position 3 (Medium Risk): $400 (20%)
- Position 4 (Higher Risk): $300 (15%)
- Cash Reserve: $400 (20%)
```

**Best Picks For This Budget:**
- STRONG BUY ratings with Medium risk
- Larger companies (less volatile)
- Timeframes: 1m, 3m, 1y (less monitoring needed)

---

### Medium Budget ($5,000 - $50,000)

**Recommended Approach:**
- Hold 6-10 positions
- Mix of risk levels (weighted to lower risk)
- Can include some swing trades
- Maintain 10-15% cash for opportunities

**Position Sizing:**
```
Account: $20,000
Position sizes: $1,500-3,000 (7.5-15%)
Number of positions: 8-10

Example Allocation:
- 3 x Low Risk @ 12%: $7,200
- 3 x Medium Risk @ 10%: $6,000
- 2 x Higher Risk @ 7%: $2,800
- Cash Reserve: $4,000 (20%)
```

**Best Picks For This Budget:**
- Mix of all ratings
- Some swing trades (3d, 7d) for active income
- Core holdings (3m, 1y) for stability

---

### Large Budget ($50,000+)

**Recommended Approach:**
- Hold 12-20 positions
- Sector diversification mandatory
- Can allocate small portion to speculative plays
- Consider hedging strategies
- Maintain 15-20% cash

**Position Sizing:**
```
Account: $100,000
Max per position: $5,000-7,000 (5-7%)
Number of positions: 15-20

Example Allocation:
- 5 x Low Risk (Core) @ 6%: $30,000
- 6 x Medium Risk @ 5%: $30,000
- 3 x Higher Risk @ 4%: $12,000
- 2 x Speculative @ 2%: $4,000
- Sector ETFs: $9,000
- Cash Reserve: $15,000 (15%)
```

**Best Picks For This Budget:**
- All categories applicable
- Consider building positions over time
- Can act on more short-term opportunities

---

### Budget-Specific Risk Allocation Table

| Budget Range | Max High Risk | Max Very High Risk | Min Cash Reserve |
|--------------|---------------|--------------------| -----------------|
| $500 - $2,000 | 0% | 0% | 25% |
| $2,000 - $5,000 | 15% | 0% | 20% |
| $5,000 - $20,000 | 20% | 5% | 15% |
| $20,000 - $50,000 | 25% | 10% | 15% |
| $50,000+ | 30% | 15% | 10% |

---

## 7. Algorithm Evaluator Requirements

For users evaluating our algorithm's accuracy and methodology:

### Required Disclosures

1. **Methodology Documentation**
   - Full algorithm descriptions in README
   - Scoring weights and thresholds
   - Indicator calculations (source code available)
   - Regime detection logic

2. **Statistical Rigor**
   | Metric | Current Value | Target | Notes |
   |--------|---------------|--------|-------|
   | Win Rate | XX% | > 55% | Statistically significant |
   | Sharpe Ratio | X.XX | > 1.0 | Risk-adjusted returns |
   | Max Drawdown | -XX% | < -20% | Worst peak-to-trough |
   | Profit Factor | X.XX | > 1.5 | Gross wins / Gross losses |
   | Sample Size | XXX picks | > 200 | Statistical validity |

3. **Verification Protocol**
   - All picks timestamped before market action
   - SHA-256 hash for immutability
   - Archived in Git history
   - Automated verification via GitHub Actions
   - Forward-testing (no look-ahead bias)

4. **Benchmark Comparisons**
   - vs. S&P 500 (SPY)
   - vs. Random selection
   - vs. Buy-and-hold individual stocks
   - Risk-adjusted comparisons (Sharpe vs. benchmark Sharpe)

### Data Export Formats

Evaluators can access:
- `data/daily-stocks.json` - Current picks
- `data/picks-archive/*.json` - Historical picks
- `data/pick-performance.json` - Verification results
- Raw indicator data available via API (future)

---

## 8. Website & GitHub Update Checklist

### Website (findtorontoevents.ca/findstocks)

**Missing Items to Add:**

- [ ] **Performance Dashboard Section**
  - Win rate by algorithm (with visual gauges)
  - Recent verified picks with outcomes
  - Equity curve chart

- [ ] **Trade Plan Display for Each Pick**
  - Entry price (with slippage)
  - Stop loss price
  - Take profit target
  - Risk/reward ratio

- [ ] **User Persona Tabs**
  - "Beginner View" - Simple explanations
  - "Trader View" - Technical details
  - "Investor View" - Fundamental focus

- [ ] **Risk Communication**
  - Color-coded risk badges
  - Explicit warnings for high-risk picks
  - Position sizing calculator

- [ ] **Educational Content**
  - "How to Use This Tool" guide
  - Glossary of terms
  - FAQ section

- [ ] **Budget Selector**
  - "I have $X to invest" input
  - Personalized allocation recommendations

### GitHub (STOCKSUNIFY2 README)

**Missing Items to Add:**

- [ ] **Installation & Setup Guide**
  - Dependencies list
  - Environment variable configuration
  - API key setup instructions

- [ ] **Performance Metrics Section**
  - Live win rate badges
  - Historical performance summary
  - Benchmark comparisons

- [ ] **Validation Protocol**
  - How to verify pick hashes
  - How to audit historical picks
  - Independent verification instructions

- [ ] **Contributing Guidelines**
  - How to submit algorithm improvements
  - Testing requirements
  - Code style guide

- [ ] **Changelog**
  - Version history
  - Major algorithm updates
  - Breaking changes

---

## Appendix A: Glossary for Beginners

| Term | Simple Definition |
|------|-------------------|
| **RSI** | Measures if a stock is "overbought" (expensive) or "oversold" (on sale) |
| **Stop Loss** | A price where you automatically sell to limit losses |
| **Take Profit** | A price where you sell to lock in gains |
| **Slippage** | The difference between expected and actual trade price |
| **ATR** | Average daily price movement (volatility measure) |
| **Breakout** | When price moves above a resistance level |
| **Support** | Price level where buying tends to happen |
| **Resistance** | Price level where selling tends to happen |
| **Long Position** | Buying a stock hoping it goes UP |
| **Short Position** | Betting a stock goes DOWN (advanced) |
| **Market Cap** | Total value of a company's shares |
| **P/E Ratio** | Price relative to earnings (valuation measure) |
| **Volume** | Number of shares traded |
| **Bull Market** | Rising market conditions |
| **Bear Market** | Falling market conditions |

---

## Appendix B: Quick Reference Card

### For Every Pick, Ask:

1. **What is it?** [Company name, sector, size]
2. **Why now?** [What triggered this pick]
3. **Buy at?** [Entry price with slippage]
4. **Sell if wrong at?** [Stop loss]
5. **Sell if right at?** [Take profit target]
6. **How long?** [Recommended holding period]
7. **How much?** [Position size for your budget]
8. **What could go wrong?** [Key risks]
9. **How confident?** [Score, certainty level]
10. **How do I track it?** [Verification date, hash]

---

## Implementation Priority

### Phase 1 (Immediate - This Week)
1. Update existing PICK_EXPLANATION_PROTOCOL.md with this framework
2. Create performance dashboard data feeds
3. Add risk warnings to all picks

### Phase 2 (Short-term - 2 Weeks)
1. Update website with trade plan display
2. Add user persona views
3. Implement position sizing calculator

### Phase 3 (Medium-term - 1 Month)
1. Full performance transparency dashboard
2. Educational content section
3. Budget-based recommendations engine

### Phase 4 (Long-term - 3 Months)
1. User accounts with personalized tracking
2. Alerts and notifications
3. Backtesting interface for evaluators

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-28  
**Author:** Claude AI Session  
**Review Cycle:** Monthly
