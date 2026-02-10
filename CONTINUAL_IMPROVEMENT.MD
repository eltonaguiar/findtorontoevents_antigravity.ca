# Continual Improvement — Stock Trading Algorithm System

> **Purpose:** Living document summarizing all stock algorithms, self-learning mechanisms, features, current picks, and consensus signals. Intended for sharing with AI assistants and collaborators for feedback and improvement ideas.
>
> **Last Updated:** 2026-02-09
>
> **Site:** https://findtorontoevents.ca/findstocks/portfolio2/hub.html

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Self-Learning Engine](#2-self-learning-engine)
3. [All Algorithms (75+)](#3-all-algorithms)
4. [How Picks Are Generated](#4-how-picks-are-generated)
5. [Consensus Detection](#5-consensus-detection)
6. [Current Picks by Horizon](#6-current-picks-by-horizon)
7. [Backtesting Framework](#7-backtesting-framework)
8. [What-If Scenarios (30+)](#8-what-if-scenarios)
9. [Alpha Forge Quant Lab](#9-alpha-forge-quant-lab)
10. [KIMI ML Framework (Designed, Not Yet Deployed)](#10-kimi-ml-framework)
11. [Daily Automation Pipeline](#11-daily-automation-pipeline)
12. [Known Issues & Improvement Areas](#12-known-issues--improvement-areas)
13. [Questions for AI Feedback](#13-questions-for-ai-feedback)

---

## 1. System Architecture

```
┌──────────────────────────────────────────────────────────┐
│  GitHub Actions (Daily 6:30 PM ET)                       │
│  refresh-stocks-portfolio.yml                            │
│  ┌─────┐ ┌─────────┐ ┌────────┐ ┌─────────┐ ┌────────┐ │
│  │Seed │→│Import   │→│Fetch   │→│Backtest │→│Learning│ │
│  │Algos│ │Picks    │ │Prices  │ │& Compare│ │Engine  │ │
│  └─────┘ └─────────┘ └────────┘ └─────────┘ └────────┘ │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  PHP Backend (findstocks/portfolio2/api/)                 │
│  Server: PHP 5.2.17, MySQL, shared hosting               │
│                                                          │
│  Core APIs:                                              │
│  • learning.php — Self-adjusting parameter optimizer     │
│  • horizon_picks.php — Time-horizon pick generator       │
│  • consolidated_picks.php — Cross-table consensus        │
│  • backtest.php — Full backtesting engine                │
│  • whatif.php — 30+ preset scenario comparisons          │
│  • alpha_forge.php — 20+ quant metrics per ticker        │
│  • advanced_stats.php — Leaderboard, walk-forward, risk  │
│  • stock_intel.php — Per-stock deep dive (TA + fund.)    │
│  • fetch_dividends_earnings.php — Yahoo Finance data     │
│  • saved_portfolio.php — Portfolio tracker with SL/TP    │
│  • track_portfolio.php — Daily equity snapshots          │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  Frontend (HTML + vanilla JS)                            │
│  • hub.html — Main navigation                           │
│  • picks.html — All algorithm picks                     │
│  • horizon-picks.html — Quick/Swing/Long-term picks     │
│  • consolidated.html — Consensus picks across tables    │
│  • learning-dashboard.html — Self-learning visualizer   │
│  • leaderboard.html — Algorithm rankings                │
│  • dashboard.html — Portfolio equity curves             │
│  • dividends.html — Dividend & earnings data            │
│  • stock-intel.html — Per-stock deep dive               │
└──────────────────────────────────────────────────────────┘
```

### Data Sources

| Source | What It Provides | Refresh Frequency |
|--------|------------------|-------------------|
| **Yahoo Finance v8** | OHLCV price data, dividend history | Daily (2 batches) |
| **Yahoo Finance v10** | Earnings, fundamentals, analyst recs | Daily (6 batches of 5 tickers) |
| **JSON feeds** (daily-stocks.json) | Algorithm picks with scores | Daily import |
| **stock_picks table** | 55+ portfolio algorithm picks | Continuous |
| **miracle_picks2 table** | DayTrades Miracle v2 picks | External feed |
| **miracle_picks3 table** | DayTraders Miracle v3 (Claude-generated) | External feed |

### Database Tables (MySQL: `ejaguiar1_favcreators`)

| Table | Purpose |
|-------|---------|
| `stocks` | Master ticker list (ticker, company, sector) |
| `daily_prices` | OHLCV price history (1 year per ticker) |
| `stock_picks` | All algorithm picks (55+ algos) |
| `miracle_picks2` | DayTrades Miracle v2 picks |
| `miracle_picks3` | DayTraders Miracle v3 picks |
| `algorithms` | Algorithm definitions & metadata |
| `algorithm_performance` | Learning engine recommendations (auto-updated) |
| `backtest_results` | Aggregate backtest metrics per run |
| `backtest_trades` | Individual trade records |
| `market_regimes` | Daily regime classification (SPY, VIX) |
| `report_cache` | Cached API responses (6-hour TTL) |
| `consensus_history` | Daily consensus snapshots |
| `saved_portfolios` | User-created portfolio tracking |
| `portfolio_positions` | Open/closed positions in tracked portfolios |
| `portfolio_daily_equity` | Daily equity snapshots for tracked portfolios |
| `stock_dividends` | Historical dividend data |
| `stock_earnings` | Quarterly earnings data |
| `stock_fundamentals` | Company fundamentals (P/E, EPS, etc.) |

---

## 2. Self-Learning Engine

### 2.1 Core Mechanism (`learning.php`)

The learning engine runs daily and performs **exhaustive grid search** over parameter space for every algorithm.

**What it optimizes:**

| Parameter | Default | Grid Values (Standard) | Grid Values (Exhaustive) |
|-----------|---------|----------------------|-------------------------|
| Take Profit (TP) | 10% | 5, 10, 15, 20, 30, 50 | 3, 5, 7, 10, 15, 20, 25, 30, 40, 50, 75, 100, 999 |
| Stop Loss (SL) | 5% | 3, 5, 8, 10, 15 | 2, 3, 5, 7, 10, 15, 20, 30, 999 |
| Max Hold Days | 7 | 1, 2, 5, 7, 14, 30 | 1, 2, 3, 5, 7, 10, 14, 21, 30, 60, 90 |

**Fixed constants:**
- Initial Capital: $10,000
- Commission: $10/trade ($20 round trip)
- Slippage: 0.5%
- Position Size: 10% of capital

**Total combinations tested:**
- Standard scan: 6 × 5 × 6 = **180 per algorithm**
- Exhaustive scan: 13 × 9 × 11 = **1,287 per algorithm**

### 2.2 How It Works (Step by Step)

```
For each algorithm with picks in stock_picks:
  1. Run quick_backtest() with DEFAULT params (TP=10, SL=5, Hold=7)
  2. For each (TP, SL, Hold) in the grid:
     a. Load all picks for this algorithm
     b. Simulate trading each pick:
        - Entry = pick_price × (1 + 0.5% slippage)
        - For each day after entry:
          - If LOW ≤ SL_price → exit at SL (stop loss hit)
          - If HIGH ≥ TP_price → exit at TP (take profit hit)
          - If days ≥ max_hold → exit at CLOSE (time exit)
        - PnL = (exit - entry) × shares - $20 commission
     c. Record: return_pct, win_rate, total_pnl
  3. Find best (TP, SL, Hold) by total return %
  4. Compare best vs. default → calculate improvement
  5. Classify: PROFITABLE / IMPROVABLE / NO_PROFIT
  6. Store to algorithm_performance table (UPSERT)
```

### 2.3 Verdict System

| Verdict | Meaning | Action |
|---------|---------|--------|
| `PROFITABLE_PARAMS_EXIST` | Best combo yields positive returns | Use recommended TP/SL/Hold |
| `IMPROVABLE_BUT_STILL_LOSING` | Best is better than default, but still negative | Consider as inverse/SHORT signal |
| `NO_PROFITABLE_PARAMS_FOUND` | No combo profits | Strong SHORT signal candidate |

### 2.4 Inverse Algorithm Detection (`bear_analysis`)

When an algorithm's picks consistently decline, the engine proposes **inverse algorithms**:

| Inverse Algorithm | Based On | Strategy |
|-------------------|----------|----------|
| **Inverse Technical Momentum** | Technical Momentum | SHORT when original says BUY. Profit from decline. |
| **Inverse VAM V2** | Volatility-Adjusted Momentum V2 | SHORT immediately on signal. 5% target decline, 10% stop. |
| **Bear Sentiment Fade** | All algorithms | SHORT high-score picks (90+) that drop >2% on Day 1. |

### 2.5 What Gets Better vs. Worse

The system tracks **improvement_pct** = (best_return - default_return). This tells us:

- **Positive improvement:** The learning engine found better parameters than the default
- **Large improvement:** The default params were poorly chosen; the algo works but was misconfigured
- **Zero improvement:** Default params were already optimal (or both are at zero)
- **Negative improvement:** This shouldn't happen (best ≥ default by definition)

### 2.6 Self-Learning Dashboard

**URL:** https://findtorontoevents.ca/findstocks/portfolio2/learning-dashboard.html

Live page that displays:
- All algorithms with current vs. optimal parameters
- Verdict badges (Profitable / Improvable / No Profit)
- Improvement percentages
- Profitable combo count per algorithm
- Bear/inverse algorithm detection
- Top 20 exhaustive permutation scan results
- Sortable columns, expandable detail rows

---

## 3. All Algorithms

### 3.1 Algorithm Families

#### CAN SLIM Family (4 algorithms)
Based on William O'Neil's CAN SLIM methodology.

| Algorithm | Description | Ideal Timeframe |
|-----------|-------------|-----------------|
| CAN SLIM | Classic CAN SLIM: Current earnings, Annual earnings, New products, Supply/demand, Leader, Institutional, Market direction | Swing (2-8 weeks) |
| CAN SLIM + 1 | Enhanced with momentum overlay (RS rating > 80) | Swing |
| CAN SLIM + 2 | Added sector rotation filter (only top 3 sectors) | Swing |
| CAN SLIM + 3 | Macro regime overlay (reduces exposure in bearish regime) | Swing |

#### Technical Momentum Family (3 algorithms)
Price-action and trend-following signals.

| Algorithm | Description |
|-----------|-------------|
| Technical Momentum | RSI + MACD + Moving Average crossovers |
| Technical Momentum + 1 | Enhanced with volume confirmation (OBV, VWAP) |
| Technical Momentum + 2 | Volatility-adjusted (ATR-normalized signals) |

#### Composite & ML (2 algorithms)

| Algorithm | Description |
|-----------|-------------|
| Composite Rating | Multi-factor score combining fundamentals + technicals + sentiment |
| ML Ensemble | XGBoost + Gradient Boosting model (trained on historical features → forward returns) |

#### Speculative / Penny (2 algorithms)

| Algorithm | Description |
|-----------|-------------|
| Penny Sniper | Sub-$5 stocks with volume spikes and momentum |
| Penny Sniper + 2 | Added volume confirmation filter |

#### Alpha & StatArb (2 algorithms)

| Algorithm | Description |
|-----------|-------------|
| Alpha Predator | Aggressive multi-signal alpha capture |
| Statistical Arbitrage | Mean reversion pairs and cross-sectional rank |

#### Inverse / Bear (3 algorithms)

| Algorithm | Description |
|-----------|-------------|
| Inverse Technical Momentum | SHORT when Technical Momentum says BUY |
| Inverse VAM V2 | SHORT Volatility-Adjusted Momentum signals |
| Bear Sentiment Fade | SHORT high-conviction picks that decline on Day 1 |

#### Blue Chip & Quality (2 algorithms)

| Algorithm | Description |
|-----------|-------------|
| Blue Chip Compounder | MCD, JNJ, WMT-style dividend growers |
| Blue Chip Growth | High-quality growth (GOOGL, MSFT type) |

#### Claude AI Meta (2 algorithms)

| Algorithm | Description |
|-----------|-------------|
| Claude Genius | AI-generated meta-strategy combining all signals |
| Claude Genius Aggressive | Higher risk tolerance, wider targets |

#### ETF & Sector (5 algorithms)

| Algorithm | Description |
|-----------|-------------|
| ETF Masters | Diversified ETF portfolio selection |
| ETF Index Tracker | Passive index-tracking strategy |
| Sector Rotation | Monthly rotation to strongest sectors |
| Sector Momentum | Technical momentum applied to sector ETFs |
| News Sentiment Sector | NLP-driven sector allocation based on news |

#### Earnings & Estimates (3 algorithms)

| Algorithm | Description |
|-----------|-------------|
| Earnings Drift PEAD | Post-Earnings Announcement Drift (Ball & Brown 1968) |
| Earnings Beat Streak | Companies with consecutive earnings beats |
| Revision Momentum | Analyst estimate revision momentum |

#### Quality & Value (4 algorithms)

| Algorithm | Description |
|-----------|-------------|
| Dividend Aristocrats | 25+ years of consecutive dividend increases |
| Share Buyback Yield | Companies with significant buyback programs |
| Quality Compounder | High ROE, stable margins, low debt |
| Value Momentum Combo | Cheap stocks (low P/E) with upward momentum |

#### Flow & Insider (5 algorithms)

| Algorithm | Description |
|-----------|-------------|
| Insider Cluster Buy | Multiple insiders buying within 30 days |
| Dark Pool Flow | Large block trades on dark pools |
| Congressional Alpha | Trades by US Congress members (long bias) |
| Congressional Negative | Inverse of Congressional trades (short) |
| Short Squeeze Detector | High short interest + increasing borrow cost |

#### Regime & Macro (4 algorithms)

| Algorithm | Description |
|-----------|-------------|
| Macro Regime Adaptive | Switches strategy based on DXY + 10Y yield |
| Volatility Regime Filter | Silences momentum in high VIX, boosts mean reversion |
| Supply Chain Monitor | Supply chain disruption detector |
| Geopolitical Risk Filter | Reduces exposure during geopolitical events |

#### Advanced Quant (6 algorithms)

| Algorithm | Description |
|-----------|-------------|
| Cross-Sectional Ranker | Top-K ranking by combined factor scores |
| Mean Reversion Z-Score | Buy oversold (Z < -2), sell overbought (Z > 2) |
| Sentiment Velocity | Rate of change in sentiment (not level) |
| Seasonal Calendar | Calendar-based patterns (January effect, etc.) |
| Multi-Horizon Momentum | Combined 1M + 3M + 6M + 12M momentum |
| Beta Decay Monitor | Tracks leveraged ETF decay for short opportunities |

#### ESG & Human Capital (4 algorithms)

| Algorithm | Description |
|-----------|-------------|
| Human Capital Quality | Employee satisfaction, Glassdoor ratings, talent retention |
| ESG Momentum | Improving ESG scores (not absolute level) |
| Climate Physical Risk | Physical climate risk exposure screening |
| ESG Quality Composite | Combined ESG + Quality factor |

#### Innovation & IP (3 algorithms)

| Algorithm | Description |
|-----------|-------------|
| Patent Innovation Surge | Spike in patent filings relative to peers |
| Innovation Compounder | R&D efficiency (revenue growth / R&D spend) |
| Network Effect Mapper | Companies with strong network effects |

#### Meta-Ensembles (5 algorithms)

| Algorithm | Description |
|-----------|-------------|
| Meta-Learner Arbitrator | Monitors ALL algorithms, dynamically weights by regime |
| God-Mode Alpha | Requires 4+ signal alignment (earnings + flow + regime + quality) |
| Alpha Forge Ensemble | All factor families combined, walk-forward validated |
| Alpha Forge Ultimate | Ensemble + regime weighting + Kelly sizing |
| Three Sleeve Plus | Momentum + Quality + Event arbitrage sleeves |

#### Alpha Forge Sleeves (5 algorithms)

| Algorithm | Description |
|-----------|-------------|
| AF Momentum Hunter | Multi-horizon momentum with trend consistency |
| AF Event Arbitrage | Earnings drift + M&A catalyst plays |
| AF Mean Reversion | Z-score based oversold bounce |
| AF Sector Relative | Relative strength within sector |
| AF Meta Ensemble | Dynamic sleeve allocation |

#### Academic / Research-Backed (7 algorithms)

| Algorithm | Description | Paper |
|-----------|-------------|-------|
| PEAD Earnings Drift | Post-Earnings Announcement Drift | Ball & Brown (1968) |
| 13F Hedge Fund Clone | Replicate top hedge fund 13F positions | |
| Sentiment Alpha | NLP/LLM sentiment scoring | |
| Risk Parity HRP | Hierarchical Risk Parity allocation | Lopez de Prado (2016) |
| Multi-Factor AIPT | 8-factor asset pricing model | |
| Overnight Return Alpha | Close-to-open overnight premium capture | |
| Firm-Specific Momentum | Isolate firm momentum from market/sector | |

---

## 4. How Picks Are Generated

### 4.1 Horizon Picks (`horizon_picks.php`)

Three time-based strategies with different risk/reward profiles:

| Horizon | Name | TP | SL | Max Hold | Min Score | Risk | Preferred Algos |
|---------|------|----|----|----------|-----------|------|----------------|
| **Quick** | Quick Gains | 10% | 5% | 10 days | 60 | High | Momentum, Scalp, Day, Technical |
| **Swing** | Swing Trades | 20% | 8% | 60 days | 55 | Medium | Swing, CAN SLIM, Composite, Momentum |
| **Long-term** | Long-Term Growth | 40% | 15% | 252 days | 50 | Low | Blue Chip, Dividend, Quality, ETF, Growth |

**Pick selection process:**
1. Query `stock_picks` where `entry_price > 0` and `score >= min_score`
2. Rank by algorithm preference (CASE WHEN match → priority 1-5)
3. Get latest price from `daily_prices`
4. Calculate TP/SL levels, current return, distance to targets, risk:reward ratio
5. Deduplicate (1 pick per ticker)
6. Return top 6 picks per horizon
7. Run inline backtest on last 500 picks → win rate, avg win/loss, $1000 projection
8. Cache for 6 hours in `report_cache`

### 4.2 Quick Picks (Day Trade / Swing / Long-term)

| Category | TP | SL | Max Hold | Algo Boost |
|----------|----|----|----------|-----------|
| **Day Trade** | 5% | 3% | 2 days | Momentum > Scalp > Day > Technical |
| **Swing Trade** | 15% | 7% | 20 days | Swing > Trend > Momentum > Composite |
| **Long-Term** | 40% | 15% | 180 days | Blue Chip > Value > Growth > ETF > Sector |

### 4.3 $1000 Projection Formula

```
expected_per_trade = (win_rate × avg_win) - ((1 - win_rate) × avg_loss)
projection = $1000 × (1 + expected_per_trade × 6 / 100)    // 6 trades
best_case  = $1000 × (1 + avg_win × 6 / 100)
worst_case = $1000 × (1 - avg_loss × 3 / 100)
```

---

## 5. Consensus Detection

### 5.1 Cross-Table Consensus (`consolidated_picks.php`)

Aggregates picks from **3 independent data sources**:

| Source | Table | Description |
|--------|-------|-------------|
| Portfolio Algorithms | `stock_picks` | 55+ algorithms, main system |
| DayTrades Miracle v2 | `miracle_picks2` | External day trading signals |
| DayTraders Miracle v3 | `miracle_picks3` | Claude-AI generated signals |

### 5.2 Consensus Scoring Formula

```
weighted_score = Σ (pick_score × recency_weight × algorithm_win_rate)
```

**Recency weights:**

| Days Since Pick | Weight |
|-----------------|--------|
| Same day (0) | 1.0 |
| 1 day | 0.9 |
| 2 days | 0.8 |
| 3 days | 0.7 |
| 4-7 days | 0.5 |
| 8-14 days | 0.3 |
| 15+ days | 0.1 |

### 5.3 Consensus Process

1. Collect all picks from past 14 days across all 3 tables
2. Group by ticker (case-insensitive)
3. Count distinct `source_table:algorithm_name` combinations
4. Filter where `consensus_count >= min_consensus` (default: 2)
5. Calculate weighted score using recency + win rate
6. Rank by weighted_score descending
7. Get latest price, compute current return vs. avg entry
8. Include source breakdown per ticker
9. Cache for 30 minutes

### 5.4 Consensus Picks = Highest Conviction

A ticker flagged by **3+ distinct algorithms from 2+ data sources** represents the system's highest conviction call. These are the "consensus picks" — when multiple independent models agree on the same trade.

---

## 6. Current Picks by Horizon

> **Note:** These picks are from the last data refresh. Visit the live pages for real-time data.
>
> **Live URLs:**
> - Horizon Picks: https://findtorontoevents.ca/findstocks/portfolio2/horizon-picks.html
> - Consensus Picks: https://findtorontoevents.ca/findstocks/portfolio2/consolidated.html
> - All Picks: https://findtorontoevents.ca/findstocks/portfolio2/picks.html

### 6.1 Tracked Tickers (from daily-stocks.json, last updated 2026-01-29)

| Ticker | Company | Score | Algorithm | Entry Price | RS Rating |
|--------|---------|-------|-----------|-------------|-----------|
| INTC | Intel | 100 | CAN SLIM | $48.78 | 96 |
| BBIG | Vinco Ventures | 100 | CAN SLIM | $0.005 | 99 |
| HUT | Hut 8 Mining | 100 | CAN SLIM + Tech Momentum | $64.60 | 99 |
| STX | Seagate | 95 | CAN SLIM | $442.93 | 99 |
| WDC | Western Digital | 95 | CAN SLIM | $279.70 | 99 |
| GDX | VanEck Gold Miners ETF | 90 | Sector ETF | $112.16 | 99 |
| SOXL | Semiconductor Bull 3X | 90 | Leveraged ETF | $70.09 | 99 |
| LABU | Biotech Bull 3X | 90 | Leveraged ETF | $170.76 | 94 |
| GOOGL | Alphabet | 60 | Blue Chip | $336.01 | — |
| AMZN | Amazon | 60 | Blue Chip | $243.01 | — |
| NVDA | Nvidia | 60 | Blue Chip | $191.52 | — |
| PFE | Pfizer | 60 | Blue Chip | $25.86 | — |
| COP | ConocoPhillips | 60 | Blue Chip | $101.39 | — |
| CAT | Caterpillar | 60 | Blue Chip | $643.28 | — |
| RTX | RTX Corp | 60 | Blue Chip | $199.46 | — |

**Also tracking:** K, XLK, XLU, XLC, CRON, MCD, DUK, URA, BBBY, PLUG, CLSK, SOS, OCGN, NCTY

### 6.2 Algorithm Distribution

| Algorithm | Pick Count | Avg Score |
|-----------|------------|-----------|
| Alpha Predator | 19 | 70-80 |
| Technical Momentum | 7 | 80-90 |
| CAN SLIM | 3 | 95-100 |
| Composite Rating | 1 | 80 |

### 6.3 Quick Reference: Which Picks for Which Goal

| Goal | Horizon | Look At | Top Tickers (by score) |
|------|---------|---------|----------------------|
| **Day Trading** | Quick (1-2 weeks) | Momentum + high RS | HUT, SOXL, LABU |
| **Swing Trading** | Swing (1-3 months) | CAN SLIM + Composite | INTC, STX, WDC |
| **Long-Term Investing** | Long-term (6-12 months) | Blue Chip + Dividend | GOOGL, AMZN, NVDA, CAT |
| **Speculative** | Quick | Penny Sniper | BBIG, BBBY, SOS, OCGN |
| **Consensus** | Any | 2+ algos agree | Check consolidated.html |

---

## 7. Backtesting Framework

### 7.1 Standard Backtest Flow (`backtest.php`)

```
1. Load picks from stock_picks (filter by algorithm, date, score)
2. Get OHLCV from daily_prices for each ticker
3. For each pick:
   a. entry_price = pick_price × (1 + 0.5% slippage)
   b. shares = floor((10% of capital - $10 commission) / entry)
   c. For each trading day:
      - Check LOW ≤ SL price → exit at SL (stop loss)
      - Check HIGH ≥ TP price → exit at TP (take profit)
      - Check days ≥ max_hold → exit at CLOSE (time exit)
   d. exit_price = exit × (1 - 0.5% slippage)
   e. PnL = (exit - entry) × shares - $20 commission
   f. Update capital, track peak for drawdown
4. Calculate aggregate metrics:
   - Win rate, avg win %, avg loss %
   - Sharpe ratio, Sortino ratio, profit factor
   - Max drawdown, commission drag
   - Expectancy = (win_rate × avg_win) - ((1-win_rate) × avg_loss)
5. Store results in backtest_results + backtest_trades tables
```

### 7.2 Metrics Tracked

| Metric | Description |
|--------|-------------|
| Total Return % | (Final - Initial) / Initial × 100 |
| Annualized Return % | Total return scaled to 252 trading days |
| Win Rate % | Winning trades / Total trades × 100 |
| Avg Win % | Mean return of profitable trades |
| Avg Loss % | Mean return of losing trades |
| Best Trade % | Highest single-trade return |
| Worst Trade % | Lowest single-trade return |
| Max Drawdown % | Largest peak-to-trough decline |
| Sharpe Ratio | Return / Volatility (risk-adjusted return) |
| Sortino Ratio | Return / Downside Deviation |
| Profit Factor | Gross Profit / Gross Loss |
| Expectancy | Expected $ per trade |
| Commission Drag % | Total commissions / Initial capital × 100 |
| Avg Hold Days | Mean days per position |

---

## 8. What-If Scenarios (30+)

The system includes **30+ preset scenarios** for comparison:

### Day Trading
| Scenario | TP | SL | Hold | Description |
|----------|----|----|------|-------------|
| Day Trader (EOD Exit) | 5% | 3% | 1d | Buy at open, sell at close |
| Day Trader (2-Day Max) | 10% | 5% | 2d | Quick overnight hold |
| Tight Scalp | 3% | 2% | 1d | Ultra-fast scalping |

### Swing Trading
| Scenario | TP | SL | Hold | Description |
|----------|----|----|------|-------------|
| Weekly Hold (10% Target) | 10% | 5% | 7d | Standard weekly |
| Weekly Hold (20% Target) | 20% | 8% | 7d | Aggressive weekly |
| Conservative Swing | 10% | 5% | 20d | Tight stops, 2-4 weeks |
| Aggressive Swing | 30% | 15% | 20d | Wide stops, let it run |
| Momentum Ride | 50% | 10% | 30d | Let winners run big |

### Long-Term
| Scenario | TP | SL | Hold | Description |
|----------|----|----|------|-------------|
| Buy & Hold (3M) | None | None | 60d | Pure buy and hold |
| Buy & Hold (6M) | None | None | 126d | 6-month hold |
| Blue Chip Hold (1Y) | None | None | 252d | Full year, no exits |
| Blue Chip Quarterly | 15% | 8% | 63d | Quarterly rebalance |
| Safe Bet (Annual) | None | None | 252d | Dividend Aristocrats + Quality |

### AI-Driven
| Scenario | TP | SL | Hold | Description |
|----------|----|----|------|-------------|
| Claude Genius Standard | 20% | 5% | 14d | AI meta-algo, $0 commission |
| Claude Genius Aggressive | 30% | 8% | 7d | Higher risk AI picks |
| Claude Genius Patient | 50% | 10% | 30d | Longer hold AI |

### God-Mode (Meta-Ensemble)
| Scenario | TP | SL | Hold | Description |
|----------|----|----|------|-------------|
| God-Mode Standard | 25% | 8% | 21d | Meta-learner, $0 comm |
| God-Mode Aggressive | 40% | 12% | 30d | Full alpha capture |
| God-Mode Conservative | 15% | 5% | 14d | Quality + safety focus |

### Questrade-Specific ($0 Commission)
| Scenario | TP | SL | Hold | Description |
|----------|----|----|------|-------------|
| Questrade CDR Weekly | 10% | 5% | 7d | CDR stocks, no FX fee |
| Questrade CDR Momentum | 50% | 10% | 30d | CDR momentum ride |
| Questrade US (1.5% FX) | 10% | 5% | 7d | US stocks, 1.5% FX fee |

### Academic / Factor
| Scenario | TP | SL | Hold | Description |
|----------|----|----|------|-------------|
| Earnings Drift (6 Week) | 25% | 10% | 42d | PEAD play after beats |
| Smart Money Flow | 20% | 8% | 14d | Insider + dark pool signals |
| Factor Rank Monthly | 15% | 8% | 30d | Cross-sectional top-K |
| Mean Reversion (3-Day) | 8% | 3% | 3d | Oversold bounce |
| Regime-Adaptive Swing | 20% | 8% | 21d | Strategy switches by regime |
| Kelly Criterion Optimal | 20% | 8% | 21d | Mathematically optimal sizing |
| All-Weather Portfolio | 15% | 10% | 30d | Long quality + short failures |

---

## 9. Alpha Forge Quant Lab

### 9.1 Regime Detection (4 Quadrants)

| Regime | Condition | Strategy |
|--------|-----------|----------|
| **Bull + Low Vol** | SPY > SMA200, VIX < 20 | Full momentum, aggressive sizing |
| **Bull + High Vol** | SPY > SMA200, VIX ≥ 20 | Momentum with tighter stops |
| **Bear + Low Vol** | SPY < SMA200, VIX < 20 | Mean reversion, defensive |
| **Bear + High Vol** | SPY < SMA200, VIX ≥ 20 | Risk-off, cash heavy, inverse signals |

### 9.2 20+ Expanded Metrics Per Ticker

| Metric Category | Specific Metrics |
|-----------------|-----------------|
| **Momentum** | 1M/3M/6M/12M returns, multi-horizon composite |
| **Risk** | 60-day volatility, beta, downside deviation, max drawdown |
| **Liquidity** | Amihud illiquidity ratio, average volume, volume profile |
| **Quality** | ROE, margins, FCF yield, debt/equity |
| **Technical** | RSI(14), SMA(20/50/200), golden/death cross |
| **Behavioral** | Return autocorrelation, overnight gaps, trend consistency |
| **Advanced** | PEAD score, Kelly optimal %, tail risk (VaR 95%) |

### 9.3 Composite Score

```
Composite = Momentum(0-25) + Quality(0-25) + Risk(0-25) + Signal(0-25) = 0-100
Grades: A (80+), B (65+), C (50+), D (35+), F (<35)
```

### 9.4 Feature Importance (Ablation Analysis)

The `feature_importance` action removes each feature one at a time and measures the score change, revealing which factors matter most for each ticker.

---

## 10. KIMI ML Framework (Designed, Not Yet Deployed)

> **Status:** These are comprehensive Python designs (`KIMI*.py`, `KIMI*.md`) that describe a production ML pipeline. They are NOT yet deployed to the live PHP system but represent the target architecture.

### 10.1 Strategy Arbitrator

```python
class StrategyArbitrator:
    def calculate_performance_score(strategy_returns):
        # Recency-weighted: recent performance gets 60% weight
        recent_sharpe = sharpe(returns[-20:])
        medium_sharpe = sharpe(returns[-lookback:])
        score = 0.6 * recent_sharpe + 0.4 * medium_sharpe
```

### 10.2 Regime-Based Strategy Allocation

| Regime | Momentum Weight | Mean Reversion Weight | Quality Weight |
|--------|----------------|----------------------|----------------|
| Goldilocks (Bull + Low Vol) | 1.5x | 0.7x | 1.0x |
| Late Cycle | 0.8x | 1.2x | 1.3x |
| Risk-Off | 0.5x | 1.5x | 1.5x |
| Crisis | 0.3x | 0.5x | 2.0x |

### 10.3 Dynamic Risk Management

- **Volatility targeting:** Adjusts leverage inversely to realized volatility
- **Kelly criterion:** Fractional Kelly (15-30%) for position sizing
- **Drawdown circuit breakers:** 5 levels (5%→warning, 10%→75%, 15%→50%, 20%→25%, 25%→cash)
- **Correlation penalties:** Reduces allocation to crowded strategies during stress

### 10.4 Walk-Forward Validation

```python
class WalkForwardValidator:
    # Train: 756 days (~3 years)
    # Test: 126 days (~6 months)
    # Step: 63 days (~3 months roll forward)
    # Measures: in-sample vs out-of-sample Sharpe decay → detects overfitting
```

---

## 11. Daily Automation Pipeline

**GitHub Actions workflow:** `refresh-stocks-portfolio.yml`
**Schedule:** Mon-Fri 6:30 PM ET (23:30 UTC) + Sunday midnight (comprehensive)

### Pipeline Steps (in order)

| Step | API Call | Purpose |
|------|----------|---------|
| 1 | `setup_schema.php` | Ensure all tables and algorithms exist |
| 2 | `import_picks.php?source=json` | Import new picks from JSON feeds (3 retries) |
| 3 | `fetch_prices.php?range=1y` (×2) | Fetch Yahoo Finance OHLCV (2 batches) |
| 4 | `fetch_dividends_earnings.php?action=fetch_all` (×6) | Fetch div/earnings (6 batches of 5 tickers) |
| 5 | `track_portfolio.php?key=stocksrefresh2026` | Update portfolio positions, check SL/TP/max_hold |
| 6 | `horizon_picks.php?nocache=1` | Regenerate horizon picks cache |
| 7 | `backtest.php?take_profit=50&stop_loss=10&max_hold_days=30&save=1` | Full backtest (Momentum Ride) |
| 8 | `whatif.php?compare=1` | Run all 10+ strategy comparison |
| 9 | `whatif.php?compare_algos=1&scenario=momentum_ride` | Compare algorithms under Momentum Ride |
| 10 | **`learning.php?action=analyze_and_adjust`** | **SELF-LEARNING: update optimal params** |
| 11 | `data.php?type=stats` | Print database statistics |
| 12 | Mutual Funds, Forex, Crypto refreshes | Other asset classes |
| 13 | `advanced_stats.php?action=top_picks` | Regenerate cross-asset top picks |
| 14 | Verify all dashboard pages (HTTP status checks) | Smoke test |
| 15 | Verify dividend/earnings data for AAPL | Data quality check |

---

## 12. Known Issues & Improvement Areas

### 12.1 Current Limitations

| Issue | Impact | Potential Fix |
|-------|--------|---------------|
| **PHP 5.2 server** | No modern PHP features, no prepared statements, no short array syntax | Migrate to modern hosting |
| **No real-time data** | Prices fetched once daily, stale during market hours | WebSocket or 15-min polling |
| **Commission model is static** | $10/trade for most, $0 for Questrade scenarios | Make commission dynamic per broker |
| **No position sizing optimization** | Always uses 10% of capital per trade | Implement Kelly criterion or volatility-based sizing |
| **No correlation-based portfolio** | Picks are independent, no portfolio-level risk | Add correlation matrix and portfolio optimization |
| **Learning engine scope** | Only tunes TP/SL/Hold; doesn't tune algorithm selection | Add meta-learning layer that selects which algos to use |
| **No live paper trading** | Backtest only, no forward-testing validation | Add paper trade mode with daily PnL tracking |
| **Consensus doesn't weight by recency enough** | 14-day window may include stale signals | Shorten to 7 days or increase recency decay |
| **KIMI ML framework not deployed** | Sophisticated designs exist but are Python-only | Port key concepts to PHP or add Python API layer |

### 12.2 Self-Learning Gaps

| Gap | Description | Priority |
|-----|-------------|----------|
| **No adaptive position sizing** | Learning only tunes exit params, not entry sizing | High |
| **No regime-conditional params** | Same optimal params used in bull and bear markets | High |
| **No walk-forward validation in PHP** | Backtests use all data; no out-of-sample testing | Medium |
| **No algorithm retirement** | Losing algorithms stay active forever | Medium |
| **No feature importance tracking** | Alpha Forge has it, but learning engine doesn't use it | Low |
| **No ensemble weight optimization** | Meta-ensembles use fixed weights | Medium |

### 12.3 Data Quality Issues

| Issue | Status |
|-------|--------|
| Some tickers have stale price data (>10 days old) | Filtered out in horizon_picks |
| Penny stocks may have unreliable OHLCV | No special handling |
| Yahoo Finance rate limits can cause missing data | Retries implemented |
| miracle_picks2/3 tables may have different schemas | Normalized in consolidated_picks |

---

## 13. Questions for AI Feedback

When sharing this document with AI assistants, ask them:

### Strategy & Architecture
1. **Are our 75+ algorithms too many?** Should we prune to a focused set of 10-15 based on backtest performance?
2. **Is our consensus mechanism sound?** The weighted_score formula uses recency × win_rate × score. What improvements would you suggest?
3. **How should we deploy the KIMI ML framework?** Port to PHP? Add a Python microservice? Use cloud functions?

### Self-Learning
4. **What other parameters should the learning engine tune?** Beyond TP/SL/Hold, what else matters?
5. **Should we implement regime-conditional optimization?** (Different optimal params for bull vs. bear markets)
6. **Is our grid search approach optimal?** Should we use Bayesian optimization, genetic algorithms, or random search instead?

### Risk Management
7. **How should we implement portfolio-level risk?** Correlation-based position limits? Sector caps?
8. **Is our $1000 projection formula reasonable?** It assumes 6 independent trades.
9. **Should we add a max drawdown circuit breaker** that stops trading after N% loss?

### Data & Signals
10. **What additional data sources would improve signal quality?** Options flow? Social media sentiment? Macro indicators?
11. **Should we add real-time intraday signals** or stick with end-of-day?
12. **How can we better validate that our algorithms aren't overfitting** to historical data?

### Consensus & Picks
13. **What's the optimal consensus threshold?** Currently 2+ algorithms. Should it be 3+?
14. **Should consensus picks be weighted by backtest Sharpe ratio** instead of raw win rate?
15. **How should we handle conflicting signals** (one algo says BUY, another says SHORT for same ticker)?

---

## Appendix A: API Quick Reference

| Endpoint | Action | Description |
|----------|--------|-------------|
| `learning.php` | `analyze_and_adjust` | Run full learning scan, store results |
| `learning.php` | `get_recommendations` | View recommendations without storing |
| `learning.php` | `permutation_scan` | Exhaustive 1,287-combo scan |
| `learning.php` | `bear_analysis` | Inverse algorithm detection |
| `horizon_picks.php` | (default) | All 3 horizons with backtests |
| `consolidated_picks.php` | `consensus` | Cross-table consensus picks |
| `consolidated_picks.php` | `by_ticker` | All picks for one stock |
| `consolidated_picks.php` | `freshness` | Data health check |
| `consolidated_picks.php` | `snapshot` | Store consensus to history (admin) |
| `backtest.php` | (params) | Run backtest with custom params |
| `whatif.php` | `compare=1` | Compare all preset scenarios |
| `whatif.php` | `compare_algos=1` | Compare algorithms under same scenario |
| `alpha_forge.php` | `regime` | 4-quadrant regime detection |
| `alpha_forge.php` | `metrics` | 20+ metrics for a ticker |
| `alpha_forge.php` | `composite_rank` | Rank all tickers by composite score |
| `alpha_forge.php` | `sleeves` | Multi-sleeve portfolio backtest |
| `advanced_stats.php` | `leaderboard` | Best algorithms/scenarios ranked |
| `advanced_stats.php` | `ticker_profile` | Deep per-stock analysis |
| `advanced_stats.php` | `top_picks` | Cross-asset top picks |
| `stock_intel.php` | `full` | Complete stock intelligence |
| `stock_intel.php` | `technicals` | Technical analysis with horizon filter |
| `saved_portfolio.php` | `create/list/detail` | Portfolio management |
| `track_portfolio.php` | (admin key) | Daily portfolio tracking |

---

## Appendix B: File Reference

| File | Location | Purpose |
|------|----------|---------|
| `learning.php` | `findstocks/portfolio2/api/` | Self-learning engine |
| `horizon_picks.php` | `findstocks/portfolio2/api/` | Time-horizon picks |
| `consolidated_picks.php` | `findstocks/portfolio2/api/` | Cross-table consensus |
| `backtest.php` | `findstocks/portfolio2/api/` | Backtesting engine |
| `whatif.php` | `findstocks/portfolio2/api/` | Scenario comparison |
| `alpha_forge.php` | `findstocks/portfolio2/api/` | Quant lab engine |
| `advanced_stats.php` | `findstocks/portfolio2/api/` | Pro analytics |
| `stock_intel.php` | `findstocks/portfolio2/api/` | Per-stock deep dive |
| `setup_schema.php` | `findstocks/portfolio2/api/` | Schema + algorithm seeder |
| `fetch_prices.php` | `findstocks/portfolio2/api/` | Yahoo Finance price fetcher |
| `fetch_dividends_earnings.php` | `findstocks/portfolio2/api/` | Dividend/earnings fetcher |
| `saved_portfolio.php` | `findstocks/portfolio2/api/` | Portfolio tracker |
| `track_portfolio.php` | `findstocks/portfolio2/api/` | Daily equity snapshots |
| `learning-dashboard.html` | `findstocks/portfolio2/` | Self-learning visualization |
| `hub.html` | `findstocks/portfolio2/` | Main navigation hub |
| `picks.html` | `findstocks/portfolio2/` | All picks dashboard |
| `horizon-picks.html` | `findstocks/portfolio2/` | Horizon picks display |
| `consolidated.html` | `findstocks/portfolio2/` | Consensus picks display |
| `leaderboard.html` | `findstocks/portfolio2/` | Algorithm leaderboard |
| `dashboard.html` | `findstocks/portfolio2/` | Portfolio equity curves |
| `dividends.html` | `findstocks/portfolio2/` | Dividend & earnings dashboard |
| `refresh-stocks-portfolio.yml` | `.github/workflows/` | Daily automation pipeline |
| `KIMIml_trading_system_design.py` | Root | ML framework design (Python) |
| `KIMIcomprehensive_risk_framework.py` | Root | Risk management framework (Python) |
| `daily-stocks.json` | Root | Daily algorithm picks feed |

---

*This document is auto-maintained. For live data, visit the dashboard pages linked above.*
*For educational and research purposes only. Not financial advice.*
