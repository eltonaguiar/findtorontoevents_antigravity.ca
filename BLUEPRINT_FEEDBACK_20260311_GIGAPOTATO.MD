# Trading System Blueprint Feedback — Giga Potato Analysis
> **Date:** March 11, 2026
> **Blueprint Version:** Last updated Mar 10, 2026
> **Scope:** Full architecture, performance, and improvement recommendations

---

## Executive Summary
The trading system blueprint outlines a multi-portfolio, multi-system architecture designed to forward-test strategies and identify viable approaches for real capital deployment. While the system demonstrates ambition and complexity, it currently faces significant challenges with persistent negative expectancy across most portfolios. This analysis provides a structured assessment of the blueprint, identifies critical gaps, and offers actionable recommendations.

---

## Strengths of the Current Architecture

### 1. Comprehensive System Design
- **Multi-System Approach:** 12+ trading systems including Alpha Engine, KIMI, ML Battleground, and Genome DNA Evolution
- **Diverse Methodologies:** Signal-based, deep-value, higher timeframe, and prop firm challenge portfolios
- **Cross-System Aggregation:** sophisticated consensus engine that routes picks to appropriate tiers
- **Risk Management:** Well-defined risk parameters including position sizing, exposure limits, and trailing stops

### 2. Data-Driven Decision Making
- **Performance Tracking:** Detailed per-system and per-strategy statistics (win rate, profit factor, expectancy)
- **Proven Strategies Identification:** Tiered classification of strategies based on forward-testing results
- **Firewall Architecture:** Robust filtering system to block poor-performing strategies
- **Consensus Tracker:** Monitors multi-system agreement with 51.9% win rate

### 3. High-Performing Isolated Systems
- **Battleground System:** Exceptional performance with 64.1% WR and +1357% cumulative PnL
- **Tier 1 Strategies:** 5 strategies with WR > 60% and proven forward-testing results
- **DNA Evolution Winners:** Promising backtest results (up to 75% WR, 2.06 Sharpe)

---

## Critical Gaps and Weaknesses

### 1. Negative Expectancy Across Most Portfolios
- **Alpha Engine:** 35.9% WR, 0.71 profit factor, -3.24% per-trade expectancy
- **KIMI System:** Dead since March 1, 2026 (94 zombie positions)
- **Mercury2 Scanner:** Degraded performance with ~0% WR
- **ML Battleground:** Systems A/B/C at 0% WR

### 2. Signal Noise Overload
- **100+ Strategies in Alpha Engine:** Most picks are low-quality, drowning out good signals
- **Portfolio Overlap:** Same bad strategies appear in multiple portfolios
- **Lack of Statistical Significance:** Many "60% WR" strategies have <20 trades (low confidence)

### 3. Asymmetric Risk-Reward
- **Avg Win vs Avg Loss:** +17.73% vs -19.85% (losing at 50% WR)
- **Fixed TP/SL:** Ceiling on winners but no floor on losers
- **No Trailing Stops:** Winners not protected, losers run too long

### 4. Poor Regime and Asset Awareness
- **Strategy-Asset Mismatch:** Same strategy has 72% WR on BTC but 33% on ETH
- **No Volatility Filtering:** Breakout strategies run in choppy markets
- **Fragmented Data:** 35 SQLite databases make traceability impossible

### 5. Deployment and Integration Gaps
- **Genome DNA Evolution:** 100+ evolved strategies with no forward-testing integration
- **System Monitoring:** KIMI death went undetected for 10 days
- **Database Fragmentation:** Cannot trace live trades back to strategy formulas

---

## 10 Priority Recommendations for Improvement

### Immediate (0-2 Weeks)

#### 1. Restart KIMI System
- **Action:** Investigate GitHub Actions workflow failure and restart KIMI scanner
- **Impact:** Recover 94 zombie positions, restore system diversity
- **Success Metric:** KIMI scanner operational with new picks generated

#### 2. Implement Tier 1 Only Filter
- **Action:** Modify Alpha Engine to only include 5 Tier 1 strategies (WR>60%, PF>1.5)
- **Impact:** Eliminate 95% of signal noise, improve overall expectancy
- **Success Metric:** Alpha Engine WR > 50%, profit factor > 1.0

#### 3. Add Trailing Stops
- **Action:** Implement trailing stops that activate at +5% profit
- **Impact:** Lock in gains, reduce average loss size
- **Success Metric:** Average loss < 17%, average win preserved

### Short-Term (2-4 Weeks)

#### 4. Full Regime Filtering
- **Action:** Complete implementation of volatility regime filter (ADX<20 → mean-reversion only)
- **Impact:** Eliminate false breakouts in choppy markets
- **Success Metric:** Breakout strategy WR in ranging markets > 45%

#### 5. Kelly + Vol-Adjusted Sizing
- **Action:** Implement half-Kelly sizing with ATR-scaled position limits
- **Impact:** Optimize risk-reward, reduce drawdowns
- **Success Metric:** Max drawdown < 8%, profit factor > 1.3

#### 6. Symbol Locking Enforcement
- **Action:** Strictly enforce strategy-asset locking (e.g., Keltner Compression only on BTC)
- **Impact:** Eliminate mismatched strategy-asset pairs
- **Success Metric:** Strategy WR consistent across different assets

### Medium-Term (4-8 Weeks)

#### 7. Genome DNA Integration
- **Action:** Wire genome output into Alpha Engine scanner pipeline
- **Impact:** Deploy proven backtest strategies (68% WR, 1.59 Sharpe) to production
- **Success Metric:** 10+ DNA strategies with forward-testing results

#### 8. Database Consolidation
- **Action:** Migrate 35 SQLite databases to unified MySQL or single SQLite store
- **Impact:** Enable full trade-strategy traceability, improve data quality
- **Success Metric:** Single database with all trade and strategy data

#### 9. Walk-Forward Optimization
- **Action:** Implement periodic re-optimization of strategy parameters
- **Impact:** Adapt to changing market conditions
- **Success Metric:** Strategies re-optimized every 4 weeks

### Long-Term (8+ Weeks)

#### 10. Binary Risk-On/Risk-Off Switch
- **Action:** Develop market condition classifier that triggers 100% cash positions
- **Impact:** Avoid trading during extreme volatility or bear markets
- **Success Metric:** Cash position during F&G < 15 AND ADX < 20

---

## Expected Outcome of Improvements

If all 10 recommendations are implemented, the system should achieve:
- **Win Rate:** ~58% (up from 35.9%)
- **Profit Factor:** ~1.35 (up from 0.71)
- **Expectancy:** +2.1% per trade (up from -3.24%)
- **Max Drawdown:** < 8% (down from 7% current, with improved stability)
- **Sustainable Edge:** Focus on 5-10 proven strategies with statistical significance

---

## Research Questions to Address

### High Priority

1. **Is Battleground System Robust?** Test performance during bear markets (F&G < 20, BTC drawdown > 15%)
2. **Minimum Trade Count:** Determine statistically significant minimum trade count per strategy (t-test/bootstrap)
3. **Optimal Hold Duration:** Analyze PnL distribution by hold time to validate 14-day max
4. **Portfolio Correlation:** Measure correlation between 22 portfolios to assess diversification effectiveness

### Medium Priority

5. **Time-of-Day Effects:** Analyze performance across Asian/European sessions
6. **Cost Estimation Accuracy:** Verify 0.40% round-trip cost estimate with actual execution data
7. **Monte Carlo Simulation:** Model tail risk scenarios with current trade distribution

---

## Next Steps

1. **Week 1-2:** Restart KIMI, implement Tier 1 filter, add trailing stops
2. **Week 3-4:** Complete regime filtering, Kelly sizing, symbol locking
3. **Week 5-8:** Integrate Genome DNA, consolidate databases, walk-forward optimization
4. **Week 9+:** Develop binary risk switch, address research questions

---

## Final Assessment

The current trading system architecture is well-designed but suffering from critical execution gaps. The 5 proposed survival changes in `portfolio_survival_improvements.md` are essential, but additional improvements (especially restarting KIMI and integrating DNA evolution) are necessary to achieve real-money confidence. With focused implementation of the 10 recommendations, the system could become viable for real capital deployment within 4-8 weeks.
