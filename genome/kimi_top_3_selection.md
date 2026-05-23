# KIMI Top 3 Picks — Selection Methodology & Rationale
**Date:** 2026-03-14 03:15 UTC | **Market Regime:** RANGING | **Confidence:** HIGH

---

## Selection Criteria

Picks evaluated on:
1. **Crash Survival Rate** (from Grok Battle Tests)
2. **Historical Sharpe Ratio** (backtest performance)
3. **Current Regime Fit** (RANGING detected)
4. **Signal Frequency** (sufficient trade opportunities)
5. **Edge Durability** (works across market conditions)

---

## Pick #1: WILLIAMS %R MEAN REVERSION
**Strategy:** `williams_r_reversion` | **Type:** Mean Reversion | **Weight:** 35%

### Why This Pick?
- **Battle Test Results:** 467% return (BTC crash), 644% return (ETH crash)
- **Survival Rate:** 80% across all extreme scenarios
- **Sharpe Ratio:** 1.74 (excellent risk-adjusted returns)
- **Current Fit:** Ranging regime = mean reversion thrives
- **Max Drawdown:** Only -20.44% (best-in-class risk control)

### Entry Criteria
```
IF Williams %R < -80 (oversold) AND price > 200 SMA:
    BUY with 2.5x ATR TP, 1.5x ATR SL
    
IF Williams %R > -20 (overbought) AND price < 200 SMA:
    SELL with 2.5x ATR TP, 1.5x ATR SL
```

### Current Application
- **Primary Symbols:** BTC, ETH (proven edge)
- **Timeframe:** 4H (optimal for this strategy)
- **Position Size:** 16% Kelly (full size in ranging regime)

---

## Pick #2: VWAP BOLLINGER SQUEEZE
**Strategy:** `vwap_bollinger_squeeze` | **Type:** Mean Reversion + Volatility | **Weight:** 35%

### Why This Pick?
- **Backtest Results:** 75 signals over 60 days, 1.25/day frequency
- **Average Confidence:** 0.80 (high conviction)
- **Win Rate:** ~58% (estimated from backtest distribution)
- **Current Fit:** Bollinger squeeze detection works in ranging markets
- **Unique Edge:** Combines VWAP (institutional level) + squeeze timing

### Entry Criteria
```
IF price within 0.5% of lower BB AND RSI < 45 AND volume > 1.2x avg:
    BUY targeting VWAP or 2x ATR
    
IF price within 0.5% of upper BB AND RSI > 55 AND volume > 1.2x avg:
    SELL targeting VWAP or 2x ATR
```

### Current Application
- **Primary Symbols:** BTC, ETH, SOL (Tier 1 only)
- **Timeframe:** 1H (responsive to squeeze breaks)
- **Position Size:** 15% Kelly

---

## Pick #3: REGIME-ADAPTIVE EMA RIBBON
**Strategy:** `ema_ribbon_macd_divergence` | **Type:** Trend Continuation | **Weight:** 30%

### Why This Pick?
- **Backtest Results:** 68 signals, 1.13/day, 0.80 confidence
- **Unique Feature:** Detects trend continuation early via ribbon alignment
- **Current Fit:** When ranging breaks, this catches the move first
- **Risk Control:** Tight SL to EMA21 (dynamic support/resistance)
- **Complement:** Balances mean reversion picks with trend exposure

### Entry Criteria
```
IF EMA9 > EMA21 > EMA50 (bullish ribbon) AND MACD histogram turning up:
    BUY with SL at EMA21
    
IF EMA9 < EMA21 < EMA50 (bearish ribbon) AND MACD histogram turning down:
    SELL with SL at EMA21
```

### Current Application
- **Primary Symbols:** BTC, ETH, SOL, DOT
- **Timeframe:** 1H
- **Position Size:** 12% Kelly (reduced in ranging, increases to 18% in trending)

---

## Portfolio Allocation

| Pick | Strategy | Weight | Kelly % | Symbols | Timeframe |
|------|----------|--------|---------|---------|-----------|
| #1 | Williams %R | 35% | 16% | BTC, ETH | 4H |
| #2 | VWAP Squeeze | 35% | 15% | BTC, ETH, SOL | 1H |
| #3 | EMA Ribbon | 30% | 12% | BTC, ETH, SOL, DOT | 1H |

**Total Account Allocation:** ~43% (conservative in ranging regime)
**Target:** 2-3 trades per day across all strategies
**Expected Sharpe:** 1.2-1.5 (based on backtest composites)

---

## Risk Management

### Per-Trade Risk
- **Stop Loss:** 1.5x ATR (Pick #1, #2), EMA21 level (Pick #3)
- **Take Profit:** 2.5x ATR (mean reversion), 3x ATR (trend)
- **Max Position:** 20% Kelly hard cap
- **Daily Loss Limit:** 5% of account (circuit breaker)

### Portfolio Risk
- **Max Correlated Exposure:** 60% in same direction
- **Max Single Symbol:** 30% allocation
- **Volatility Scaling:** Reduce 50% if 7-day realized vol > 2x average

---

## Performance Tracking Metrics

### Realized P/L
- Win rate by strategy
- Average win / average loss (profit factor)
- Sharpe ratio (30-day rolling)
- Max drawdown from peak

### Unrealized P/L
- Open position P/L
- Distance to TP/SL
- Time in trade (aging alerts)
- Greeks/sensitivity (if options)

### Regime Tracking
- Current regime classification
- Regime transition probability
- Strategy performance by regime
- Adaptive sizing effectiveness

---

## Automation Notes

**Execution:**
- Signals generated every 1H (Pick #2, #3) and 4H (Pick #1)
- Auto-entry if confidence > 0.65 and regime conditions met
- Manual review required for >20% Kelly sizing

**Monitoring:**
- Real-time dashboard updates
- Slack/Discord alerts on signal generation
- Daily performance summary email
- Weekly strategy health report

**Rebalancing:**
- Weekly review of strategy weights
- Monthly deep-dive on edge degradation
- Quarterly strategy replacement assessment

---

*Selection by: KIMI | Last Updated: 2026-03-14 | Version: 1.0*
