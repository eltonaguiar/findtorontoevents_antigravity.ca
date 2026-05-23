# TradingView Indicator Strategies - Quick Reference Card

## Most Effective 2-3 Indicator Combinations

### For Trend Following
| Primary | Secondary | Filter | Strategy Name |
|---------|-----------|--------|---------------|
| EMA(50/200) | MACD | ADX > 25 | Triple Confirmation |
| Supertrend | ADX | Volume | Strong Trend Filter |
| Ichimoku | Volume Profile | - | Cloud + POC |

### For Mean Reversion
| Primary | Secondary | Filter | Strategy Name |
|---------|-----------|--------|---------------|
| Bollinger Bands | RSI | - | BB + RSI |
| Keltner Channels | RSI | EMA(200) | KC Mean Reversion |
| VWAP | Stochastic | Volume | VWAP Bounce |

### For Breakout Trading
| Primary | Secondary | Filter | Strategy Name |
|---------|-----------|--------|---------------|
| Bollinger Squeeze | MACD | Volume > 1.5× | Squeeze Breakout |
| Keltner Channels | EMA(200) | - | KC Breakout |
| Volume Profile | Price Action | - | POC Break |

### For Momentum Trading
| Primary | Secondary | Filter | Strategy Name |
|---------|-----------|--------|---------------|
| MACD | RSI(50-70) | EMA trend | Momentum Combo |
| Stochastic | Williams %R | - | Dual Oscillator |
| ROC | Momentum | SMA(200) | Rate of Change |

## Indicator Categories Quick Reference

### Moving Averages
- **SMA**: Simple, best for long-term trends
- **EMA**: Responsive, best for entry/exit timing
- **WMA**: Weighted recent prices, reduces lag
- **VWAP**: Institutional benchmark, intraday reference

### Oscillators
- **RSI**: 0-100 scale, 30/70 extremes
- **MACD**: Trend-following momentum
- **Stochastic**: %K/%D crossover, 20/80 levels
- **CCI**: ±100 thresholds, commodity focus
- **Williams %R**: -100 to 0, -20/-80 extremes

### Volatility
- **Bollinger Bands**: StdDev-based, squeeze signals
- **Keltner Channels**: ATR-based, smoother than BB
- **ATR**: Stop-loss sizing, volatility measurement

### Volume
- **OBV**: Cumulative volume flow
- **VWAP**: Volume-weighted average
- **Volume Profile**: POC, Value Area
- **CMF**: Money flow accumulation

### Trend
- **ADX**: 0-100 strength, 25+ strong
- **Parabolic SAR**: Trailing stop dots
- **Ichimoku**: 5-component cloud system
- **Supertrend**: ATR-based trend line

### Momentum
- **Momentum**: Rate of price change
- **ROC**: Percentage change
- **Awesome Oscillator**: 5/34 SMA histogram
- **TSI**: Double-smoothed momentum

## Timeframe Recommendations

| Strategy Type | Entry TF | Confirmation TF | Trend TF |
|--------------|----------|-----------------|----------|
| Scalping | 1m-5m | 15m | 1H |
| Day Trading | 5m-15m | 1H | 4H |
| Swing Trading | 1H-4H | Daily | Weekly |
| Position Trading | Daily | Weekly | Monthly |

## Asset Class Suitability

| Indicator | Stocks | Forex | Crypto | Futures | Commodities |
|-----------|--------|-------|--------|---------|-------------|
| VWAP | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Bollinger Bands | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Ichimoku | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Supertrend | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Volume Profile | ⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| ADX | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Stochastic | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| MACD | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

## Entry/Exit Cheat Sheet

### Long Entry Checklist
- [ ] Price above trend filter (EMA 200 or SMA 200)
- [ ] Momentum indicator bullish (RSI > 50, MACD > Signal)
- [ ] Volume confirms (above average or rising)
- [ ] Volatility appropriate (ADX > 20, not in squeeze)
- [ ] No major resistance overhead

### Short Entry Checklist
- [ ] Price below trend filter
- [ ] Momentum indicator bearish (RSI < 50, MACD < Signal)
- [ ] Volume confirms
- [ ] Volatility appropriate
- [ ] No major support below

### Exit Rules
- **Trend Following**: Trailing stop (ATR-based or Parabolic SAR)
- **Mean Reversion**: Target at mean (VWAP, middle band)
- **Breakout**: When momentum fades (RSI extreme, MACD crossover)

## Risk Management Guidelines

### Position Sizing
- Risk 1-2% per trade
- Adjust for volatility (wider stops in high ATR)
- Reduce size in choppy markets (ADX < 20)

### Stop Loss Placement
- **ATR Method**: Entry ± (2-3 × ATR)
- **Support/Resistance**: Below/above key level
- **Indicator-Based**: Opposite side of moving average

### Take Profit Targets
- **1:1 Risk/Reward**: Conservative
- **1:2 Risk/Reward**: Balanced
- **1:3 Risk/Reward**: Aggressive trend following
- **Trailing**: Let winners run in strong trends

## Common Mistakes to Avoid

1. **Using too many indicators** (3 max recommended)
2. **Ignoring trend direction** (always check higher TF)
3. **Trading low volume periods** (false breakouts)
4. **Not adjusting for volatility** (ATR changes)
5. **Over-optimizing parameters** (curve fitting)

## Pine Script Template

```pinescript
//@version=5
strategy("My Strategy", overlay=true)

// Inputs
emaFast = input.int(20, "Fast EMA")
emaSlow = input.int(50, "Slow EMA")
rsiLength = input.int(14, "RSI Length")

// Indicators
emaF = ta.ema(close, emaFast)
emaS = ta.ema(close, emaSlow)
rsi = ta.rsi(close, rsiLength)

// Entry Conditions
longCondition = ta.crossover(emaF, emaS) and rsi > 50
shortCondition = ta.crossunder(emaF, emaS) and rsi < 50

// Execute
if longCondition
    strategy.entry("Long", strategy.long)
if shortCondition
    strategy.entry("Short", strategy.short)

// Plot
plot(emaF, "Fast EMA", color.blue)
plot(emaS, "Slow EMA", color.red)
```

---
*Quick reference for TradingView indicator strategies*
