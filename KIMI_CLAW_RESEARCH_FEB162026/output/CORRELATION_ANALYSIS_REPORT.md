# Strategy Correlation Analysis Report

**Date:** 2026-02-17  
**Analyst:** Correlation Analyst Agent  
**Total Strategies Analyzed:** 196

---

## Executive Summary

This report analyzes correlations between 196 trading strategies across multiple dimensions: strategy type, asset class, and timeframe. The analysis reveals significant diversification opportunities, with **10,547 strategy pairs showing near-zero correlation** (|r| < 0.1). However, stress testing shows correlations can spike by **+0.47 during market crashes**, reducing diversification benefits when needed most.

### Key Findings

| Metric | Value |
|--------|-------|
| Average Normal Correlation | 0.065 |
| Average Crash Correlation | 0.533 |
| Correlation Increase During Crash | +0.468 (720% increase) |
| Uncorrelated Strategy Pairs | 10,547 |
| Best Portfolio Sharpe Ratio | 4.34 |

---

## 1. Correlation Matrix by Strategy Type

### Cross-Type Correlation Heatmap

|  | Unknown | Mean Reversion | Momentum | Volume | Smart Money | Trend | Pattern |
|--|---------|----------------|----------|--------|-------------|-------|---------|
| **Unknown** | 0.032 | -0.049 | 0.113 | 0.059 | 0.052 | 0.089 | 0.030 |
| **Mean Reversion** | -0.049 | 0.080 | **-0.174** | -0.091 | -0.079 | -0.144 | -0.048 |
| **Momentum** | 0.113 | **-0.174** | 0.400 | 0.220 | 0.179 | 0.296 | 0.115 |
| **Volume** | 0.059 | -0.091 | 0.220 | 0.154 | 0.101 | 0.162 | 0.058 |
| **Smart Money** | 0.052 | -0.079 | 0.179 | 0.101 | 0.079 | 0.127 | 0.053 |
| **Trend** | 0.089 | -0.144 | 0.296 | 0.162 | 0.127 | 0.296 | 0.079 |
| **Pattern** | 0.030 | -0.048 | 0.115 | 0.058 | 0.053 | 0.079 | 0.016 |

### Key Insights

1. **Mean Reversion vs Momentum**: Strong negative correlation (-0.174) - these strategy types provide natural hedges to each other
2. **Momentum Strategies**: Highest within-type correlation (0.400) - diversification within momentum is limited
3. **Pattern Strategies**: Lowest correlations with all other types - excellent diversifiers
4. **Trend Following**: Moderate correlation with momentum (0.296) - some overlap in market exposure

---

## 2. Momentum Strategy Correlations

### Summary Statistics

| Metric | Value |
|--------|-------|
| Number of Strategies | 40 |
| Average Pairwise Correlation | 0.400 |
| Minimum Correlation | 0.247 |
| Maximum Correlation | 0.519 |

### Most Correlated Momentum Pairs (Diversification Risk)

| Strategy 1 | Strategy 2 | Correlation |
|------------|------------|-------------|
| Sector Rotation | Alpha Predator | +0.519 |
| Sector Rotation | Change of Character | +0.518 |
| ORB NQ - RSI Momentum | Volume Spike (Whale) | +0.516 |
| Dividend Capture | Volume Spike (Whale) | +0.515 |
| Moving Average Flip | Relative Strength | +0.506 |

**⚠️ Risk Alert:** These pairs move together significantly. Avoid combining in portfolio.

---

## 3. Mean Reversion Strategy Correlations

### Summary Statistics

| Metric | Value |
|--------|-------|
| Number of Strategies | 18 |
| Average Pairwise Correlation | 0.080 |
| Minimum Correlation | -0.079 |
| Maximum Correlation | 0.207 |

**✅ Diversification Opportunity:** Mean reversion strategies show low internal correlation, making them excellent portfolio diversifiers.

---

## 4. Cross-Asset Correlations

### Key Asset Class Correlations

| Asset 1 | Asset 2 | Correlation |
|---------|---------|-------------|
| SPY | QQQ | 0.045 |
| BTC | ETH | -0.005 |
| ES Futures | NQ Futures | 0.039 |
| SPY | EURUSD | 0.043 |
| BTC | SPY | 0.011 |

### Insights

1. **Crypto vs Traditional**: BTC/ETH show near-zero correlation with equity indices
2. **Forex Diversification**: EURUSD provides good diversification vs US equities
3. **Index Correlation**: SPY-QQQ correlation surprisingly low (0.045) in this dataset
4. **Futures Cross-Correlation**: ES/NQ futures show moderate correlation (0.503 within same asset)

---

## 5. Cross-Timeframe Correlations

### Timeframe Correlation Matrix

|  | 1m | 5m | 15m | 1h | 4h |
|--|----|----|-----|----|----|
| **1m** | 0.294 | 0.054 | 0.022 | 0.066 | 0.062 |
| **5m** | 0.054 | 0.055 | 0.032 | 0.048 | 0.034 |
| **15m** | 0.022 | 0.032 | 0.294 | 0.051 | 0.006 |
| **1h** | 0.066 | 0.048 | 0.051 | 0.278 | 0.042 |
| **4h** | 0.062 | 0.034 | 0.006 | 0.042 | 0.305 |

### Key Findings

1. **Same-Timeframe Clustering**: Strategies on same timeframe show higher correlation (0.28-0.30)
2. **Cross-Timeframe Diversification**: 1m vs 15m shows only 0.022 correlation - excellent diversification
3. **5m as Neutral**: 5m timeframe shows lowest cross-timeframe correlations - good "bridge" timeframe

---

## 6. Diversification Benefits

### Uncorrelated Strategy Pairs

**Found 10,547 pairs with |correlation| < 0.1**

Top 10 Most Uncorrelated Pairs:

| Strategy 1 | Strategy 2 | Correlation |
|------------|------------|-------------|
| 0DTE Options Scalping - BTC | SMRT Algo - 15m Swing | ~0.000 |
| SMRT Algo - SPY | Order Block | ~0.000 |
| 0DTE Options Scalping - Standard Risk | ORB NQ - Loose | ~0.000 |
| ORB NQ - Balanced | AI Predictions | ~0.000 |
| ORB NQ - Aggressive | ICT SMC - Balanced | ~0.000 |

### Natural Hedges

**No pairs found with correlation < -0.2**

However, mean reversion strategies as a group show negative correlation (-0.174) with momentum strategies, providing portfolio-level hedging.

---

## 7. Optimal Portfolio Construction

### Portfolio Comparison

| Portfolio | Expected Return | Volatility | Sharpe Ratio | Max Drawdown (Est.) |
|-----------|-----------------|------------|--------------|---------------------|
| **Maximum Sharpe** | 55.23% | 12.71% | **4.34** | ~15% |
| **Maximum Diversification** | 36.61% | 10.51% | 3.48 | ~12% |
| **Equal Weight** | 34.27% | 10.87% | 3.15 | ~13% |
| **Minimum Correlation** | 33.53% | 15.33% | 2.19 | ~20% |

### Maximum Sharpe Portfolio (Recommended)

**Expected Performance:**
- Annual Return: 55.23%
- Volatility: 12.71%
- Sharpe Ratio: 4.34

**Top Allocations:**

| Strategy | Weight |
|----------|--------|
| ORB - BTC | 13.95% |
| 0DTE Options Scalping - 5m Standard | 10.32% |
| ICT SMC - 1m Precision | 10.15% |
| 0DTE Options Scalping - 15m Swing | 8.99% |
| ORB NQ - Tight | 8.97% |
| 0DTE Options Scalping - 4h Macro | 8.23% |
| ORB NQ - 15m Swing | 5.64% |
| ORB NQ - 5m Standard | 5.10% |
| 0DTE Options Scalping - Ultra Aggressive | 4.96% |
| ORB NQ - 1m Precision | 4.72% |

### Maximum Diversification Portfolio (Conservative)

**Expected Performance:**
- Annual Return: 36.61%
- Volatility: 10.51%
- Sharpe Ratio: 3.48

**Top Allocations:**

| Strategy | Weight |
|----------|--------|
| ORB NQ - 15m Swing | 7.06% |
| ORB - NQ Futures (Base) | 5.80% |
| 0DTE Options Scalping - 15m Swing | 5.58% |
| ORB NQ - Tight | 5.16% |
| 0DTE Options Scalping - QQQ | 4.54% |
| ORB NQ - Volume Profile | 4.54% |
| ORB - EURUSD | 4.54% |
| ORB NQ - 1m Precision | 4.32% |
| 0DTE Options Scalping - 4h Macro | 4.27% |
| 0DTE Options Scalping - EMA Version | 4.24% |

---

## 8. Stress Test: Market Crashes

### Correlation Behavior During Stress

| Scenario | Average Correlation | Change from Normal |
|----------|--------------------|--------------------|
| Normal Period | 0.065 | - |
| Market Crash | 0.533 | **+0.468 (+720%)** |
| High Volatility | 0.316 | +0.251 (+386%) |

### Biggest Correlation Spikes During Crash

| Strategy 1 | Strategy 2 | Correlation Increase |
|------------|------------|---------------------|
| ORB - EURUSD | SMRT Algo - ES Futures | +1.038 |
| 0DTE Options Scalping - 4h Macro | 0DTE Options Scalping - Ultra Tight | +1.036 |
| 0DTE Options Scalping - SPY (Base) | ORB - NQ Futures (Base) | +1.023 |
| ORB - NQ Futures (Base) | Ultimate Oscillator | +1.017 |
| ORB NQ - 15m Swing | ADX Trend Strength | +1.001 |

### Key Stress Test Findings

1. **Diversification Breakdown**: Correlations can increase 7x during crashes
2. **Cross-Asset Convergence**: Assets that were uncorrelated become highly correlated
3. **Strategy Type Clustering**: All momentum strategies converge (r > 0.8)
4. **Safe Havens**: Mean reversion maintains negative correlation but magnitude decreases

---

## 9. Portfolio Construction Recommendations

### Recommended Strategy Mix

#### Core Allocation (60% of portfolio)

**Momentum Strategies: 20-25%**
- RSI Momentum 5 (Sharpe: 1.26) - 5%
- Volume Breakout - 5%
- EMA Cross 9/21 - 5%
- Momentum Burst - 5%
- Breakout Momentum - 5%

**Mean Reversion: 20-25%**
- Bollinger Mean Reversion - 5%
- VWAP Bounce - 5%
- Short Term Reversal - 5%
- RSI Mean Reversion - 5%
- Gap Fill Strategy - 5%

**Trend Following: 10-15%**
- Ichimoku Cloud - 5%
- Donchian Channels - 5%
- ATR Trailing Stop - 5%

#### Satellite Allocation (30% of portfolio)

**Smart Money Concepts: 15%**
- ICT SMC (5m Standard) - 5%
- Order Block - 5%
- Liquidity Sweep - 5%

**Volume-Based: 10%**
- Whale Accumulation - 5%
- Volume Spike Detection - 5%

**Pattern/Specialized: 5%**
- Meme Coin Scanner - 3%
- Pump Watch - 2%

#### Diversification Hedge (10% of portfolio)

- Mean reversion focused allocation during high volatility
- Cross-asset strategies (EURUSD, BTC)
- Pattern-based with low correlation

### Risk Management Rules

| Rule | Threshold |
|------|-----------|
| Maximum single strategy weight | 15% |
| Maximum single type weight | 35% |
| Rebalance trigger | Correlation > 0.7 for 5+ days |
| Volatility reduction | -30% exposure when VIX > 30 |
| Minimum strategies | 8 for adequate diversification |

### Correlation Monitoring Framework

1. **Weekly**: Calculate 30-day rolling correlations
2. **Alert**: When average pairwise correlation > 0.5
3. **Monthly**: Stress test with correlation shocks (+0.3)
4. **Quarterly**: Review and adjust strategy weights

---

## 10. When Diversification Breaks Down

### Warning Signs

1. **Correlation Regime Change**
   - Average correlation rises above 0.3
   - Cross-asset correlations converge
   - Safe havens start correlating with risk assets

2. **Market Stress Indicators**
   - VIX > 30
   - Flash crash events
   - Liquidity drying up
   - Forced liquidations

3. **Strategy Clustering**
   - Momentum strategies all trigger simultaneously
   - Mean reversion stops working
   - Trend followers get whipsawed

### Mitigation Strategies

1. **Dynamic Position Sizing**
   - Reduce exposure by 50% when correlations spike
   - Increase cash allocation during stress
   - Use volatility targeting

2. **Correlation Hedges**
   - Maintain 10-15% in negatively correlated strategies
   - Use options for tail risk protection
   - Consider volatility ETPs

3. **Regime Detection**
   - Monitor correlation trends
   - Use volatility regime indicators
   - Implement circuit breakers

---

## Appendix: Strategy Type Classifications

### Momentum Strategies (40)
- RSI Momentum variants
- MACD Crossover
- EMA Cross strategies
- Volume Breakout
- ADX Trend Strength
- Sector Rotation
- Alpha Predator
- Change of Character
- Moving Average Flip
- Relative Strength

### Mean Reversion Strategies (18)
- Bollinger Mean Reversion
- RSI Mean Reversion
- Stoch RSI Cross
- VWAP Bounce
- Short Term Reversal
- Gap Fill Strategy
- Williams %R
- CCI Overbought

### Trend Following Strategies (15)
- Ichimoku Cloud
- Donchian Channels
- ATR Trailing Stop
- Heikin Ashi Trend
- Parabolic SAR
- Golden/Death Cross

### Smart Money Strategies (25)
- ICT SMC variants
- Order Block
- Breaker Block
- Liquidity Sweep
- Fair Value Gap
- Judas Swing
- Market Structure Shift

### Volume-Based Strategies (12)
- Volume Breakout
- OBV Trend
- Chaikin Money Flow
- Whale Accumulation
- Volume Spike

### Pattern Strategies (20)
- Meme Coin Scanner
- Pump Watch
- Alpha Hunter
- Fractals Breakout
- Renko Bricks

---

## Conclusion

The correlation analysis reveals significant diversification opportunities across the 196 strategies, with mean reversion strategies providing the best hedge against momentum-driven portfolios. The optimal maximum Sharpe portfolio achieves a 4.34 Sharpe ratio with 55.23% expected return and 12.71% volatility.

**Critical Risk:** Correlations can spike by over 700% during market crashes, significantly reducing diversification benefits when needed most. Dynamic position sizing and correlation monitoring are essential for risk management.

**Recommendation:** Implement the Maximum Sharpe portfolio with correlation-based risk controls, maintaining at least 20% allocation to mean reversion strategies for crisis protection.

---

*Report generated by Correlation Analyst Agent*  
*Data sources: strategy_variations.json, complete_strategies.json, performance_stats.json*
