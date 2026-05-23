# Hedge Fund Quality Trading System — Master Plan

**Date:** March 11, 2026
**Objective:** Transform our multi-asset trading system from amateur-grade (14% WR) to hedge-fund-quality (60%+ WR, Sharpe >1.5) across all asset classes.

---

## Current State Assessment

### Systems Inventory
| System | Asset Class | Picks | WR | Avg PnL | Status |
|--------|-------------|-------|----|---------|--------|
| Alpha Engine | Crypto (25 strats) | 45 active | **71%** | +0.01% | WORKING |
| KIMI RiseOfTheClaw | Crypto (81 algos) | 4 signals | TBD | TBD | ACTIVE |
| Multi-Asset Scanner | Futures/Stocks/Forex/ETF/Penny | 27 active | 14% | -0.51% | BROKEN |
| Tournament Agents | Futures/Forex (60 portfolios) | 60 ports | N/A | +3.71% | DECENT |
| Consensus Tracker | Crypto cross-system | 4 outcomes | TBD | TBD | NEW |
| Genome Evolver | Strategy DNA | 70 results | N/A | N/A | RESEARCH |

### Critical Problems
1. **Multi-asset WR is 14%** — catastrophic. vix_reversal strategy dominated and failed
2. **26/27 active picks are LONG** — zero hedging, massive directional risk
3. **No drawdown circuit breaker** — unlimited loss potential
4. **No regime detection** — same strategies in bull/bear markets
5. **No correlation management** — SPY + QQQ + ES=F + NQ=F = same trade 4x
6. **Tournament portfolios disconnected** from audit dashboard
7. **No mutual funds, options, or commodities-specific strategies**
8. **Penny stocks barely covered** (1/6 symbols active)

### What's Actually Working
- **Alpha Engine crypto: 71% WR** — proven strategies, good diversification
- **Hyperopt backtests: 73-92% WR** — on specific symbol+strategy combos
- **Tournament forex portfolios: avg +6.17%** — StatisticalArb leading
- **Tournament futures portfolios: avg +4.63%** — MeanReversion doing well

---

## Phase 1: Emergency Fixes (Immediate — Day 1)

### 1.1 Drawdown Circuit Breaker
**Priority: CRITICAL**
- Add global drawdown monitor to `multi_asset/scanner.py`
- If portfolio drawdown exceeds -5%, pause all new entries for 24h
- If any single pick hits -3%, auto-close immediately
- Log all circuit breaker triggers

### 1.2 Correlation-Based Position Limits
**Priority: CRITICAL**
- Group correlated assets: {SPY, QQQ, ES=F, NQ=F, XLK} = "US Equity Index" group
- Max 2 picks per correlation group
- Implement using a correlation matrix computed from 60d returns

### 1.3 Mandatory Short-Side Exposure
**Priority: HIGH**
- Require minimum 20% short-side exposure
- When market regime = bearish (SPY < 200d SMA), increase to 40%
- Add short signals: RSI(2) > 95 + below SMA200 = SHORT

### 1.4 Regime Detection Module
**Priority: HIGH**
```
regime = BULL  if SPY > SMA200 and VIX < 20
regime = BEAR  if SPY < SMA200 and VIX > 25
regime = CHOP  otherwise

Strategy allocation by regime:
  BULL: 70% trend-following, 30% mean-reversion
  BEAR: 30% trend-following (short), 50% mean-reversion, 20% cash
  CHOP: 80% mean-reversion, 20% cash
```

---

## Phase 2: Strategy Upgrade (Days 2-5)

### 2.1 Stocks & Equities — Factor-Based Approach
**Target: 60-65% WR, Sharpe >1.5**

| Strategy | Description | Expected WR | Data Needed |
|----------|-------------|-------------|-------------|
| **Momentum Factor** | Buy top-decile 12-1 month momentum, short bottom | 55-60% | Price history |
| **Mean Reversion (RSI-2)** | Already proven via hyperopt (92% on GLD) | 75-92% | Price + RSI |
| **Pairs Trading** | Cointegrated pairs (KO/PEP, XOM/CVX) | 60-65% | Price correlation |
| **Earnings Drift** | Buy PEAD (post-earnings announcement drift) | 58-62% | Earnings calendar |
| **Quality Factor** | High ROE + low debt + consistent earnings | 55-60% | Fundamentals API |

**Implementation:**
- Expand stock universe: Add KO, PEP, XOM, CVX, WMT, JNJ, UNH, HD, PG, MRK (20 total)
- Add pairs scanner: compute rolling cointegration, trade when z-score > 2
- Add sector-relative momentum: rank stocks within each sector

### 2.2 Penny Stocks — Momentum Scanner
**Target: 55-60% WR, high R:R**

| Strategy | Description | Expected WR | Risk |
|----------|-------------|-------------|------|
| **Volume Breakout** | 5x avg volume + price above 20d high | 50-55% | HIGH |
| **Gap-and-Go** | Pre-market gap > 5%, buy on pullback | 55-60% | HIGH |
| **Short Squeeze** | High short interest + rising volume | 50-55% | HIGH |

**Implementation:**
- Expand penny universe: Add LCID, RIVN, HOOD, OPEN, WISH, CLOV, BB, NOK, TELL, SNDL
- Tight risk: -8% SL, +15% TP, 3-day max hold
- Volume filter: only trade when volume > 2x 20d average
- Position size: max 5% of portfolio per penny pick

### 2.3 ETFs & Indexes — Sector Rotation + Risk Parity
**Target: 60-70% WR, Sharpe >2.0**

| Strategy | Description | Expected WR | Sharpe |
|----------|-------------|-------------|--------|
| **Sector Rotation** | Monthly: buy top 3 sectors by momentum | 60-65% | 1.5-2.0 |
| **Risk Parity** | Equal risk allocation across SPY/TLT/GLD/DBC | 55-60% | 1.2-1.8 |
| **Dual Momentum** | Absolute + relative momentum (Antonacci) | 65-70% | 1.5-2.5 |
| **TQQQ/TMF Rebalance** | Leveraged risk parity (HFEA strategy) | 60-65% | 1.0-1.5 |

**Implementation:**
- Add sector ETFs: XLC, XLB, XLI, XLP, XLRE, XLU, XLV (complete all 11 sectors)
- Add commodity ETFs: DBC, USO, UNG, WEAT
- Monthly sector momentum ranking with 3-month lookback
- Risk parity rebalancing: target equal volatility contribution

### 2.4 Futures — Managed Futures / CTA Approach
**Target: 55-65% WR, Sharpe >1.5**

| Strategy | Description | Expected WR | Sharpe |
|----------|-------------|-------------|--------|
| **Trend Following** | 20/50/200 EMA crossover on futures | 45-55% | 1.0-2.0 |
| **Calendar Spread** | Long front month, short back month | 55-60% | 1.5-2.0 |
| **Mean Reversion** | Bollinger MR (proven 75-89% in hyperopt) | 75-89% | 15-24 |
| **Roll Yield** | Exploit contango/backwardation | 55-60% | 1.0-1.5 |

**Implementation:**
- Add more futures: RTY=F (Russell), HG=F (Copper), NG=F (Nat Gas), ZS=F (Soybeans)
- Implement calendar spread scanner
- Use COT (Commitment of Traders) data for positioning context
- Managed futures trend signal: buy when price > 200d EMA, short when below

### 2.5 Forex — Carry + Technical Hybrid
**Target: 60-70% WR, Sharpe >1.5**

| Strategy | Description | Expected WR | Sharpe |
|----------|-------------|-------------|--------|
| **Bollinger MR** | Proven 85-88% WR on NZDUSD, GBPUSD, EURUSD | 85-88% | 19-21 |
| **Carry Trade** | Long high-yield, short low-yield currencies | 55-60% | 0.8-1.5 |
| **London Breakout** | Trade London session open range breakout | 55-62% | 1.0-1.5 |
| **Momentum** | 1-month momentum on major pairs | 55-60% | 1.0-1.5 |

**Implementation:**
- Already expanded to 8 pairs (USDCAD, USDCHF, EURJPY added)
- Add: EURGBP=X, AUDNZD=X, CADJPY=X for carry diversification
- Implement carry trade: long AUDJPY (high carry), short EURCHF (low carry)
- London breakout: scan at 08:00 GMT, trade range break with 1.5:1 R:R

### 2.6 Crypto — Leverage Alpha Engine Success
**Target: Maintain 71%+ WR**

- Alpha Engine is already working well at 71% WR
- Focus: integrate alpha_engine picks into the audit dashboard
- Add: funding rate arbitrage from KIMI signals
- Add: on-chain whale tracking from proven strategies
- Cross-reference with consensus tracker for higher-confidence picks

### 2.7 Mutual Funds — Tactical Allocation (NEW)
**Target: 55-65% WR**

| Strategy | Description | Expected WR |
|----------|-------------|-------------|
| **Dual Momentum** | Switch between SPY/EFA/AGG based on 12m momentum | 65-70% |
| **Sector Momentum** | Rotate sector funds monthly | 60-65% |
| **Risk-On/Risk-Off** | Switch between equity/bond funds based on regime | 55-60% |

**Implementation:**
- Track: VFINX, VGTSX, VBMFX, VGSIX (Vanguard core funds)
- Monthly signal: rank by 3/6/12 month momentum, hold top 2
- Use regime detection to scale equity allocation

---

## Phase 3: Risk Management Framework (Days 3-7)

### 3.1 Position Sizing — Kelly Criterion
```
f* = (bp - q) / b
where:
  b = odds received (avg_win / avg_loss)
  p = probability of winning (win_rate)
  q = probability of losing (1 - win_rate)

Use half-Kelly for safety:
  position_size = 0.5 * f* * portfolio_value
```

### 3.2 Portfolio-Level Risk Limits
| Metric | Limit | Action |
|--------|-------|--------|
| Max drawdown | -5% | Pause new entries 24h |
| Max single-pick loss | -3% | Auto-close |
| Max correlation group exposure | 20% | Block new entries |
| Max asset class exposure | 30% | Block new entries |
| Max strategy concentration | 25% | Block new entries |
| Min short-side exposure | 20% | Force short scans |
| Max total long exposure | 80% | Cash reserve |
| VaR (95%, 1-day) | -2% | Alert + reduce |

### 3.3 Equity Curve Tracking
- Log daily portfolio NAV to `multi_asset/data/equity_history.json`
- Compute rolling 30d Sharpe, Sortino, Calmar ratios
- Display on audit dashboard with equity curve chart
- Track per-strategy and per-asset-class equity curves separately

### 3.4 Strategy Kill Switch
- If any strategy's rolling 20-trade WR drops below 35%, auto-disable it
- If any strategy's rolling Sharpe drops below -0.5, auto-disable it
- Re-enable after 50 new backtest trades show WR > 55%
- Log all kill switch events

---

## Phase 4: Dashboard & Audit Enhancement (Days 5-10)

### 4.1 Unified Audit Dashboard Upgrade
The audit dashboard at https://findtorontoevents.ca/audit/ needs:

1. **All Asset Classes** — Currently has crypto/equity/forex. Add: futures, ETF, penny, mutual funds
2. **Tournament Portfolio Integration** — Show 60 tournament portfolios alongside scanner picks
3. **Risk Metrics Panel** — Live Sharpe, Sortino, VaR, max DD, correlation matrix
4. **Regime Indicator** — Bull/Bear/Chop badge with VIX level
5. **Strategy Performance Ranking** — Sort strategies by Sharpe, not just WR
6. **Equity Curve Chart** — Interactive chart with benchmark (SPY buy-and-hold) overlay
7. **Correlation Heatmap** — Show cross-asset correlations
8. **Position Sizing Display** — Show Kelly % and actual allocation per pick

### 4.2 Portfolio History Dashboard Enhancement
- Add mutual fund tracking
- Add options strategies when implemented
- Show long/short breakdown per portfolio
- Add benchmark comparison (SPY, 60/40, risk-free rate)

### 4.3 Claude's Test Dashboard Enhancement
- Integrate multi-asset picks alongside crypto
- Add forward-test vs backtest comparison charts
- Show strategy degradation alerts

---

## Phase 5: Data Infrastructure (Days 7-14)

### 5.1 Additional Data Sources
| Data | Source | Purpose | Priority |
|------|--------|---------|----------|
| Earnings calendar | Yahoo Finance API | PEAD strategy | HIGH |
| COT data | CFTC weekly | Futures positioning | MEDIUM |
| Sector fundamentals | Yahoo Finance | Quality factor | MEDIUM |
| Short interest | FINRA | Short squeeze scanner | HIGH |
| Options flow | Unusual Whales API | Smart money tracking | LOW |
| Economic calendar | FRED API | Macro regime detection | MEDIUM |
| Fund flows | ETF.com | Sector rotation signal | LOW |

### 5.2 Backtest Infrastructure
- Extend hyperopt to all new strategies
- Walk-forward validation: 70% in-sample, 30% out-of-sample
- Monte Carlo simulation: 1000 random paths to estimate expected Sharpe range
- Out-of-sample testing mandatory before any strategy goes live

---

## Phase 6: Implementation Priority & Timeline

### Week 1 (Immediate)
- [x] Disable vix_reversal (DONE)
- [x] Add hyperopt-tuned strategies (DONE)
- [x] Add extreme_oversold_bounce (DONE)
- [x] Expand forex to 8 pairs (DONE)
- [ ] Add drawdown circuit breaker
- [ ] Add correlation-based position limits
- [ ] Add regime detection module
- [ ] Implement short-side strategies

### Week 2
- [ ] Expand stock universe to 20 symbols
- [ ] Add pairs trading (KO/PEP, XOM/CVX)
- [ ] Add sector rotation for ETFs (all 11 sectors)
- [ ] Expand penny stock universe to 16 symbols
- [ ] Add volume breakout scanner for pennies
- [ ] Implement Kelly criterion position sizing

### Week 3
- [ ] Add managed futures (calendar spreads, trend following)
- [ ] Add mutual fund tactical allocation
- [ ] Implement equity curve tracking
- [ ] Upgrade audit dashboard with all asset classes
- [ ] Add strategy kill switch

### Week 4
- [ ] Add additional data sources (earnings, COT, short interest)
- [ ] Full hyperopt sweep on all new strategies
- [ ] Out-of-sample validation
- [ ] Monte Carlo simulation
- [ ] Performance benchmark comparison

---

## Success Criteria

| Metric | Current | Target (30d) | Target (90d) |
|--------|---------|--------------|--------------|
| Overall Win Rate | 14% | >50% | >60% |
| Sharpe Ratio | -0.78 | >0.5 | >1.5 |
| Sortino Ratio | -0.57 | >0.5 | >2.0 |
| Profit Factor | 0.05 | >1.2 | >2.0 |
| Max Drawdown | -3.8% | <-5% | <-3% |
| Asset Classes | 5 | 7 | 8+ |
| Active Strategies | 8 | 15+ | 25+ |
| Short Exposure | 4% | >20% | >30% |
| Correlation Diversification | POOR | MODERATE | GOOD |

---

## Monitoring & Feedback Loop

1. **Every 20 minutes**: Scanner runs, checks PnL, enforces risk limits
2. **Daily**: Equity curve update, strategy performance ranking, regime check
3. **Weekly**: Full hyperopt re-run, strategy kill switch evaluation
4. **Monthly**: Sector rotation rebalance, out-of-sample validation
5. **Quarterly**: Full system review, strategy sunset/sunrise decisions
