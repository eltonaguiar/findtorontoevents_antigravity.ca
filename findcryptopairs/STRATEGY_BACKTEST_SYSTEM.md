# 100 Strategy Backtesting System for Volatile Crypto Pairs

## System Architecture

### Phase 1: Volatile Pair Identification ✅
**Source:** Kraken API (700+ pairs)
**Criteria for Volatility:**
- 24h price change > 10%
- Average true range (ATR) > 5% of price
- Volume > $1M USD
- Meme coins and low-cap alts prioritized

**Selected Volatile Pairs:**
1. POPCAT/USD - Meme coin, high social interest
2. PENGU/USD - NFT-based, volatile
3. DOGE/USD - Established meme, high volume
4. SHIB/USD - Extreme volatility
5. PEPE/USD - Meme coin with 100%+ moves
6. FLOKI/USD - Community-driven volatility
7. BONK/USD - Solana meme, high beta
8. WIF/USD - Dog-themed, viral potential
9. BTC/USD - Baseline (lower volatility)
10. ETH/USD - Smart contract leader

### Phase 2: 100 Strategy Catalog ✅
**File:** `crypto_trading_strategies_100.json`

**Categories:**
| Category | Count | Best For |
|----------|-------|----------|
| Momentum | 10 | Trend continuation |
| Mean Reversion | 10 | Oversold bounces |
| Breakout | 10 | Volatility expansion |
| Scalping | 10 | Quick profits |
| Trend Following | 10 | Sustained moves |
| Volatility-Based | 10 | ATR strategies |
| Machine Learning | 10 | Pattern recognition |
| Arbitrage | 5 | Exchange inefficiencies |
| Sentiment/Social | 5 | Narrative trading |
| Pattern Recognition | 10 | Chart patterns |
| Hybrid/Ensemble | 10 | Multi-factor |

### Phase 3: Backtesting Engine

**Timeframes to Test:**
- 1-minute (scalping strategies)
- 5-minute (intraday)
- 15-minute (swing trading)
- 1-hour (position trading)
- 4-hour (trend following)
- 1-day (long-term)

**Metrics Calculated:**
1. Win Rate (%)
2. Profit Factor (gross profit / gross loss)
3. Sharpe Ratio (risk-adjusted returns)
4. Max Drawdown (%)
5. Average Trade Return (%)
6. Total Return (%)
7. Recovery Factor
8. Sortino Ratio
9. Calmar Ratio
10. Expectancy

**Historical Data Periods:**
- Last 30 days (recent volatility)
- Last 90 days (quarter performance)
- Last 180 days (semi-annual)
- Full available history

### Phase 4: Strategy Elimination Framework

**Elimination Criteria (Progressive Filtering):**

**Round 1 - Basic Viability:**
- Win rate < 40% → ELIMINATE
- Profit factor < 1.2 → ELIMINATE
- Max drawdown > 50% → ELIMINATE
- Less than 20 trades in test period → ELIMINATE

**Round 2 - Risk-Adjusted Performance:**
- Sharpe ratio < 1.0 → ELIMINATE
- Sortino ratio < 1.5 → ELIMINATE
- Calmar ratio < 2.0 → ELIMINATE

**Round 3 - Consistency:**
- Negative returns in >50% of test periods → ELIMINATE
- High variance in performance across pairs → ELIMINATE
- Strategy fails on BTC/ETH (baseline) → ELIMINATE

**Round 4 - Real-World Applicability:**
- Requires >10 trades per day (too active) → ELIMINATE
- Stop loss >15% (too risky) → ELIMINATE
- Complex execution requirements → ELIMINATE

### Phase 5: Audit Trail Requirements

Every strategy decision must log:
1. **Selection Reasoning:** Why this strategy was considered
2. **Test Results:** Raw performance metrics
3. **Elimination Reason:** Specific criteria that failed
4. **Comparison Data:** How it performed vs others
5. **Timestamp:** When the decision was made
6. **Confidence Score:** 0-100 rating

### Phase 6: Top Picks Selection

**Final Selection Criteria:**
- Must pass all 4 elimination rounds
- Must perform on at least 3 volatile pairs
- Must have Sharpe ratio > 1.5
- Must have positive expectancy
- Must be executable in real-time

**Top Pick Categories:**
- **Tier 1 (The Elite):** Top 5 strategies with highest composite scores
- **Tier 2 (The Reliable):** Next 10 strategies with consistent performance
- **Tier 3 (The Specialists):** 5 strategies that excel in specific conditions

## Implementation Structure

```
findcryptopairs/
├── strategy_backtest/
│   ├── data/
│   │   ├── kraken_pairs.json
│   │   ├── volatile_pairs.csv
│   │   └── historical_ohlcv/
│   ├── strategies/
│   │   └── crypto_trading_strategies_100.json
│   ├── backtest_engine.py
│   ├── elimination_framework.py
│   ├── audit_logger.py
│   ├── results/
│   │   ├── round1_basic_viability.json
│   │   ├── round2_risk_adjusted.json
│   │   ├── round3_consistency.json
│   │   ├── round4_applicability.json
│   │   └── final_rankings.json
│   └── audit_logs/
│       ├── selection_decisions.log
│       ├── elimination_reasons.log
│       └── methodology_notes.md
└── ui/
    ├── backtest_dashboard.html
    ├── strategy_comparison.html
    ├── audit_trail_viewer.html
    └── top_picks_display.html
```

## Expected Timeline

1. **Data Collection:** 30 minutes
2. **Strategy Catalog Finalization:** 1 hour
3. **Backtest Execution:** 2-3 hours (across 100 strategies × 10 pairs × 6 timeframes)
4. **Elimination Rounds:** 30 minutes
5. **Audit Log Generation:** 30 minutes
6. **UI Development:** 1 hour
7. **Final Report:** 30 minutes

**Total: ~6-7 hours**

## Success Metrics

The system is successful if:
- [ ] At least 20 strategies pass Round 1
- [ ] At least 10 strategies pass Round 2
- [ ] At least 5 strategies pass all rounds
- [ ] Top pick has Sharpe > 2.0
- [ ] Complete audit trail for all decisions
- [ ] UI allows filtering by category, timeframe, pair
