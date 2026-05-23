# TradingView Strategies, Indicators, and Pine Script Research Report

## Executive Summary

This report compiles 50+ TradingView strategies, indicators, and Pine Script implementations based on extensive research of community-published scripts, built-in strategies, and popular authors. The strategies are categorized by type, with detailed information on entry/exit conditions, indicators used, timeframes, and performance characteristics.

---

## Table of Contents
1. [Trend-Following Strategies](#1-trend-following-strategies)
2. [Mean Reversion Strategies](#2-mean-reversion-strategies)
3. [Momentum Strategies](#3-momentum-strategies)
4. [Breakout Strategies](#4-breakout-strategies)
5. [Multi-Indicator Strategies](#5-multi-indicator-strategies)
6. [Volume-Based Strategies](#6-volume-based-strategies)
7. [Built-in TradingView Strategies](#7-built-in-tradingview-strategies)
8. [Popular Community Indicators](#8-popular-community-indicators)
9. [Pine Script Code Examples](#9-pine-script-code-examples)
10. [Strategy Performance Summary](#10-strategy-performance-summary)

---

## 1. Trend-Following Strategies

### 1.1 SuperTrend Strategy (Long Only)
**Author:** holdon_to_profits  
**Type:** Trend Following  
**Favorites:** High (Popular community script)

**Pine Script Logic:**
```pinescript
//@version=5
strategy("SuperTrend Strategy", overlay=true)
atr_length = input.int(10, "ATR Length")
factor = input.float(3.0, "Factor", step=0.1)
[supertrend, direction] = ta.supertrend(factor, atr_length)

long_condition = direction < 0
short_condition = direction > 0

if (long_condition)
    strategy.entry("Long", strategy.long)
if (short_condition)
    strategy.close("Long")
```

**Entry Conditions:**
- Long: SuperTrend flips from bearish to bullish (direction < 0)
- Uses ATR-based volatility tracking

**Exit Conditions:**
- Close position when SuperTrend flips bearish
- No short entries (long-only strategy)

**Indicators Used:**
- ATR (Average True Range) with SMA
- SuperTrend line

**Settings:**
- ATR Period: 10
- ATR Multiplier: 3.0
- Source: hl2
- Commission: 0.015%

**Timeframe:** All timeframes (adjust ATR for asset)
**Asset Class:** All asset classes

---

### 1.2 Advanced Supertrend Strategy
**Author:** taurus79  
**Type:** Trend Following with Filters

**Features:**
- Enhanced Supertrend with configurable ATR
- RSI Filter to avoid overbought/oversold
- Moving Average Filter (SMA/EMA/WMA)
- Risk Management with ATR-based stops
- Trend Strength Analysis
- Breakout Confirmation

**Entry Conditions:**
- Supertrend direction change
- RSI confirmation (optional)
- MA trend confirmation
- Minimum trend duration filter

**Exit Conditions:**
- Supertrend reversal
- Stop-loss at ATR multiple
- Take-profit at ATR multiple

**Indicators Used:**
- SuperTrend
- RSI
- Moving Averages (SMA/EMA/WMA)
- ATR

---

### 1.3 SuperTrend with Trend-Based Exits
**Author:** Community  
**Type:** Trend Following with Dynamic Sizing

**Logic:**
- Entries on SuperTrend direction change
- Dynamic position sizing based on stop-loss distance
- Risk per trade: Fixed dollar amount
- Lot size rounding for exchange precision

**Position Sizing Formula:**
```
position_size = floor((risk_per_trade / stop_loss_distance) / lot_step) * lot_step
```

**Settings:**
- ATR Length: 300
- Factor: 7.5
- Risk per trade: $90 (3% of $3,000 capital)
- Commission: 0.05%
- Slippage: 5 ticks

**Best For:** STXUSDT 15M at Bybit (optimized)

---

### 1.4 Cyatophilum SuperTrend Backtest
**Author:** cyatophilum  
**Type:** Multi-Strategy SuperTrend
**Access:** Invite-only (Paid)

**Strategies Available:**
1. CyatoTrend (improved SuperTrend with range filtering)
2. SuperTrend (classic)
3. Double SuperTrend (fast + slow)
4. Adaptive SuperTrend (dynamic ATR factor)

**Features:**
- ADX sideways filter
- MTF (Multi-Timeframe) parameters
- Backtest results panel
- Alert system

---

### 1.5 Moving Average Crossover (Golden/Death Cross)
**Type:** Classic Trend Following
**Built-in:** Yes

**Entry Conditions:**
- Golden Cross: 50 EMA crosses above 200 EMA (Bullish)
- Death Cross: 50 EMA crosses below 200 EMA (Bearish)

**Exit Conditions:**
- Opposite crossover
- Trailing stop

**Indicators Used:**
- 50-period EMA/SMA
- 200-period EMA/SMA

**Timeframe:** Daily, Weekly (best for long-term)
**Asset Class:** Stocks, Indices, Forex

---

### 1.6 EMA Crossover with Volume
**Author:** Community  
**Type:** Trend Following with Volume Confirmation

**Entry Conditions:**
- Fast EMA (9) crosses above Slow EMA (21)
- Price above Fast EMA
- Higher timeframe confirms uptrend
- Volume > 1.2x average

**Exit Conditions:**
- Opposite crossover
- RSI > 75 (overbought)

**Indicators Used:**
- 9 EMA
- 21 EMA
- Volume MA
- RSI

---

### 1.7 Ichimoku Cloud Strategy
**Type:** Comprehensive Trend Analysis

**Pine Script Logic:**
```pinescript
conversionPeriod = input.int(9, "Conversion Line Periods")
basePeriod = input.int(26, "Base Line Periods")
laggingSpan2Period = input.int(52, "Lagging Span 2 Periods")
displacement = input.int(26, "Displacement")

tenkan = ta.ema(high + low, conversionPeriod / 2)
kijun = ta.ema(high + low, basePeriod / 2)
senkouA = (tenkan + kijun) / 2
senkouB = ta.ema(high + low, laggingSpan2Period / 2)

long_condition = ta.crossover(tenkan, kijun)
short_condition = ta.crossunder(tenkan, kijun)
```

**Entry Conditions:**
- Tenkan-sen crosses above Kijun-sen (bullish)
- Price above Cloud (Senkou Span A/B)

**Exit Conditions:**
- Tenkan crosses below Kijun
- Price enters Cloud

**Indicators Used:**
- Tenkan-sen (Conversion Line)
- Kijun-sen (Base Line)
- Senkou Span A/B (Cloud)
- Chikou Span (Lagging Line)

---

### 1.8 Ichimoku + Keltner Channel Strategy
**Author:** Flexa  
**Type:** Trend Following with Volatility Filter

**Logic:**
- Use Ichimoku to identify trend direction
- Keltner Channel for entry/exit timing
- Don't open LONG if Cloud is upper
- Don't open SHORT if Cloud is lower

**Entry Conditions:**
- Ichimoku trend alignment
- Keltner Channel breakout

**Exit Conditions:**
- Keltner Channel touch
- Ichimoku trend change

---

### 1.9 Donchian Channel Breakout
**Type:** Trend Following / Breakout

**Pine Script Logic:**
```pinescript
length = input.int(20, "Donchian Length")
upper = ta.highest(high, length)
lower = ta.lowest(low, length)

long_condition = ta.crossover(close, upper[1])
short_condition = ta.crossunder(close, lower[1])
```

**Entry Conditions:**
- Long: Price crosses above upper channel
- Short: Price crosses below lower channel

**Exit Conditions:**
- Opposite channel touch
- Trailing stop

**Indicators Used:**
- Donchian Channels (highest high, lowest low)

**Best For:** Trending markets, commodities

---

### 1.10 Supertrend Advance Pullback Strategy
**Author:** JS_TechTrading  
**Type:** Trend Following with Pullback Entries

**Features:**
- Multiple indicator combinations
- EMA, RSI, MACD, CCI filters
- Pullback entries on trend continuation
- Configurable SL/TP

**Entry Conditions:**
- Trend established (EMA alignment)
- Pullback to Supertrend line
- RSI/MACD confirmation

**Exit Conditions:**
- Supertrend reversal
- Fixed TP/SL
- ATR-based stops

---

## 2. Mean Reversion Strategies

### 2.1 RSI Overbought/Oversold Reversal
**Type:** Mean Reversion / Oscillator

**Pine Script Logic:**
```pinescript
length = input.int(14, "RSI Length")
ob_level = input.int(70, "Overbought Level")
os_level = input.int(30, "Oversold Level")

rsi = ta.rsi(close, length)

long_condition = ta.crossunder(rsi, os_level)
short_condition = ta.crossover(rsi, ob_level)
```

**Entry Conditions:**
- Long: RSI crosses back above 30 (oversold bounce)
- Short: RSI crosses back below 70 (overbought pullback)

**Exit Conditions:**
- RSI reaches opposite extreme
- Price reaches mean (VWAP/MA)

**Indicators Used:**
- RSI (14-period default)

**Timeframe:** Any (best on 1H, 4H, Daily)

---

### 2.2 Bollinger Bands Mean Reversion
**Type:** Volatility-Based Mean Reversion

**Pine Script Logic:**
```pinescript
length = input.int(20, "BB Length")
std_dev = input.float(2.0, "StdDev Factor")

basis = ta.sma(close, length)
dev = std_dev * ta.stdev(close, length)
upper_band = basis + dev
lower_band = basis - dev

long_condition = close < lower_band
short_condition = close > upper_band
```

**Entry Conditions:**
- Long: Price touches or crosses below lower band
- Short: Price touches or crosses above upper band

**Exit Conditions:**
- Price reaches middle band (basis)
- Price reaches opposite band

**Indicators Used:**
- Bollinger Bands (20, 2)
- SMA/EMA basis

---

### 2.3 VWAP + RSI Mean Reversion
**Type:** Intraday Mean Reversion
**Best For:** 5m, 15m charts

**Entry Conditions:**
- RSI > 70 (overbought) + Price above VWAP = Short
- RSI < 30 (oversold) + Price below VWAP = Long
- RSI divergence adds confluence

**Exit Conditions:**
- Take profit at VWAP
- Stop beyond recent swing high/low

**Indicators Used:**
- VWAP (Volume Weighted Average Price)
- RSI

---

### 2.4 Fibonacci Retracement Strategy
**Type:** Pullback Trading

**Pine Script Logic:**
```pinescript
length = input.int(100, "Lookback Period")
high_range = ta.highest(high, length)
low_range = ta.lowest(low, length)
range = high_range - low_range

f61_8 = low_range + range * 0.618

if (close > f61_8 and close[1] <= f61_8)
    strategy.entry("Fib Buy", strategy.long)
```

**Entry Conditions:**
- In uptrend, buy at 61.8% retracement (Golden Zone)
- Look for bullish candlestick patterns
- Stochastic confirmation

**Exit Conditions:**
- Next Fibonacci level
- Support/Resistance

**Key Levels:**
- 23.6%, 38.2%, 50%, 61.8%, 78.6%

---

### 2.5 Keltner Channel Mean Reversion
**Type:** Volatility-Based

**Entry Conditions:**
- RSI 50-80 for bullish setups
- RSI 20-50 for bearish setups
- Price closes outside channel
- RSI confirms momentum

**Exit Conditions:**
- Price returns to channel
- RSI reaches extreme

**Indicators Used:**
- Keltner Channels (ATR-based)
- RSI

---

## 3. Momentum Strategies

### 3.1 MACD Crossover Momentum
**Type:** Momentum / Trend

**Pine Script Logic:**
```pinescript
fast_length = input.int(12, "Fast Length")
slow_length = input.int(26, "Slow Length")
signal_length = input.int(9, "Signal Length")

[macd_line, signal_line, hist] = ta.macd(close, fast_length, slow_length, signal_length)

long_condition = ta.crossover(macd_line, signal_line)
short_condition = ta.crossunder(macd_line, signal_line)
```

**Entry Conditions:**
- Long: MACD line crosses above signal line
- Short: MACD line crosses below signal line

**Exit Conditions:**
- Opposite crossover
- MACD histogram divergence

**Indicators Used:**
- MACD (12, 26, 9 default)

---

### 3.2 MACD + RSI + EMA Strategy
**Author:** abishek_philip24  
**Type:** Multi-Factor Momentum

**Long Entry:**
1. Trend is Up (Price > EMA)
2. MACD Bullish Crossover
3. RSI 50-70 (healthy momentum)

**Short Entry:**
1. Trend is Down (Price < EMA)
2. MACD Bearish Crossover
3. RSI 30-50 (healthy selling)

**Exit Conditions:**
- RSI > 75 (long exit - overbought)
- RSI < 25 (short exit - oversold)
- Trend reversal

**Indicators Used:**
- EMA
- MACD
- RSI

---

### 3.3 Stochastic RSI Strategy
**Type:** Momentum Oscillator

**Entry Conditions:**
- Long: StochRSI crosses above 20
- Short: StochRSI crosses below 80

**Exit Conditions:**
- Opposite signal
- Overbought/Oversold extreme

**Indicators Used:**
- Stochastic RSI

---

### 3.4 Volume-MACD-RSI Triple Check
**Type:** Multi-Confirmation Momentum

**Logic:**
1. **Volume First:** Confirm with increasing volume
2. **MACD Second:** Check for momentum shift
3. **RSI Third:** Verify not at extreme

**Entry Conditions:**
- Volume > average
- MACD crossover
- RSI not overbought/oversold

**Best For:** Range-bound markets, choppy conditions

---

## 4. Breakout Strategies

### 4.1 Bollinger Bands Breakout
**Type:** Volatility Breakout

**Pine Script Logic:**
```pinescript
length = input.int(20, "BB Length")
std_dev = input.float(2.0, "StdDev Factor")

basis = ta.sma(close, length)
dev = std_dev * ta.stdev(close, length)
upper_band = basis + dev
lower_band = basis - dev

long_condition = close > upper_band
short_condition = close < lower_band
```

**Entry Conditions:**
- Long: Close above upper band (volatility expansion)
- Short: Close below lower band

**Exit Conditions:**
- Price returns to basis
- Trailing stop

**Best For:** Low volatility periods before major moves

---

### 4.2 Breakout and Retest Strategy
**Type:** Support/Resistance Breakout

**Entry Conditions:**
- Identify horizontal range/consolidation
- Strong candle closing beyond range
- Limit order at retest of range high/low

**Stop Loss:**
- Below range low (bullish)
- Above range high (bearish)

**Take Profit:**
- Key support/resistance levels

---

### 4.3 Bollinger Band Squeeze + MACD
**Type:** Volatility Contraction Breakout

**Entry Conditions:**
- Bollinger Bands constrict (low volatility)
- MACD confirms breakout direction
- Strong price movement in MACD direction

**Stop Loss:**
- Beyond opposite Bollinger Band edge

**Take Profit:**
- Opposite edge of Bollinger Bands

---

### 4.4 Donchian Channel Breakout (Turtle Style)
**Type:** Classic Breakout

**Entry Conditions:**
- Long: Price breaks 20-period high
- Short: Price breaks 20-period low

**Exit Conditions:**
- 10-period channel exit (opposite)

**Indicators Used:**
- Donchian Channels (20, 10)

**Best For:** Commodities, trending markets

---

## 5. Multi-Indicator Strategies

### 5.1 MACD + RSI + EMA + BB + ATR Day Trading Strategy
**Type:** Multi-Layer Filter

**Long Entry Requirements:**
1. Trend Filter: Fast EMA (9) > Slow EMA (21), Price > Fast EMA, HTF confirms uptrend
2. MACD Signal: Bullish crossover
3. RSI Condition: 40-70 (healthy)
4. Volume & Volatility: Volume > 1.2x average, sufficient ATR
5. Time Filter: 9:30-11:30 AM ET

**Exit Strategies:**
- Initial Stop: 2.0x ATR
- Trailing Stop: 1.5x ATR
- Time-Based: Close by 4:00 PM ET

**Chart Setup:** 5-minute with 15-minute confirmation

---

### 5.2 Multifactor Buy/Sell Strategy V2
**Type:** Comprehensive Multi-Factor

**Indicators:**
- RSI (oversold/overbought)
- EMA (trend direction)
- MACD (momentum)
- ATR (volatility)
- Bollinger Bands (levels)

**Long Signal:**
- Uptrend (Fast EMA > Slow EMA, Price > Fast EMA)
- RSI oversold (<30)
- Positive MACD histogram
- High volatility + volume
- Strong momentum

**Short Signal:**
- Downtrend
- RSI overbought (>70)
- Negative MACD histogram
- High volatility + volume

---

### 5.3 Bollinger Bands + RSI + MACD Strategy
**Type:** Multi-Confirmation

**Entry Conditions:**
- Buy: Price crosses lower BB upward + RSI confirmation + MACD alignment
- Sell: Price crosses upper BB downward + RSI confirmation + MACD alignment

**Exit Conditions:**
- Partial close at middle band
- Full close at opposite band
- Fixed TP option
- Trailing stop option

---

### 5.4 Multi-Timeframe EMA Strategy
**Type:** Trend Confirmation

**Pine Script Logic:**
```pinescript
ema_length = input.int(20, "EMA Length")
long_timeframe = input.string("60", "Higher Timeframe")

mtf_ema = request.security(syminfo.tickerid, long_timeframe, ta.ema(close, ema_length))

long_condition = close > ta.ema(close, ema_length) and close > mtf_ema
short_condition = close < ta.ema(close, ema_length) and close < mtf_ema
```

**Entry Conditions:**
- Price above current TF EMA AND above higher TF EMA

**Exit Conditions:**
- Price below either EMA

---

## 6. Volume-Based Strategies

### 6.1 Wyckoff-Inspired VWAP Strategy
**Type:** Volume Analysis / Accumulation-Distribution

**Pine Script Logic:**
```pinescript
vol_mult = input.float(2.0, "Volume Multiplier")
vwap = ta.vwap(close)
avg_volume = ta.sma(volume, 20)
vol_spike = volume > (avg_volume * vol_mult)

long_condition = close < vwap and vol_spike
short_condition = close > vwap and vol_spike
```

**Entry Conditions:**
- Long: Price below VWAP + volume spike (accumulation)
- Short: Price above VWAP + volume spike (distribution)

**Indicators Used:**
- VWAP
- Volume SMA

---

### 6.2 Volume-Based Support/Resistance
**Type:** Volume Profile Analysis

**Logic:**
- Identify bars with unusually high volume
- Mark high-volume price levels as S/R
- Trade breakouts from these levels

**Entry Conditions:**
- Long: Close above previous high-volume resistance
- Short: Close below previous high-volume support

---

### 6.3 EMA Crossover with Volume Filter
**Type:** Trend + Volume Confirmation

**Entry Conditions:**
- EMA crossover
- Volume > 1.2x average

**Exit Conditions:**
- Opposite crossover
- Volume divergence

---

## 7. Built-in TradingView Strategies

### 7.1 Simple MA Crossover
**Built-in:** Yes  
**Type:** Trend Following

**Logic:**
- Fast MA crosses above Slow MA = Buy
- Fast MA crosses below Slow MA = Sell

**Settings:**
- Adjustable MA periods
- MA type (SMA, EMA, WMA)

---

### 7.2 RSI Strategy
**Built-in:** Yes  
**Type:** Mean Reversion

**Logic:**
- Buy when RSI crosses above oversold level
- Sell when RSI crosses below overbought level

**Settings:**
- RSI period
- Overbought/Oversold levels

---

### 7.3 MACD Strategy
**Built-in:** Yes  
**Type:** Momentum

**Logic:**
- MACD line crosses signal line for entries

**Settings:**
- Fast, Slow, Signal periods

---

### 7.4 Bollinger Bands Strategy
**Built-in:** Yes  
**Type:** Mean Reversion/Breakout

**Logic:**
- Price crosses bands for entries

**Settings:**
- Period, Standard Deviation

---

### 7.5 Supertrend Strategy
**Built-in:** Yes  
**Type:** Trend Following

**Logic:**
- Direction change for entries/exits

**Settings:**
- ATR period, Factor

---

### 7.6 Ichimoku Strategy
**Built-in:** Yes  
**Type:** Trend Following

**Logic:**
- Tenkan/Kijun crosses
- Cloud breaks

---

## 8. Popular Community Indicators

### 8.1 WaveTrend Oscillator (LazyBear)
**Author:** LazyBear  
**Type:** Momentum Oscillator  
**Popularity:** Very High

**Features:**
- Overbought/Oversold detection
- Divergence identification
- Smoothed signals

**Settings:**
- Channel Length: 10
- Average Length: 21

---

### 8.2 Squeeze Momentum Indicator (LazyBear)
**Author:** LazyBear  
**Type:** Volatility + Momentum  
**Popularity:** Very High

**Features:**
- Identifies Bollinger Bands + Keltner Channel squeezes
- Momentum histogram
- Directional coloring

**Use Case:**
- Trade breakouts after volatility contraction

---

### 8.3 CM_Ultimate RSI Multi Time Frame
**Author:** ChrisMoody  
**Type:** RSI Enhancement  
**Popularity:** High

**Features:**
- Multi-timeframe RSI
- Overbought/Oversold detection
- Divergence alerts

---

### 8.4 %R Trend Exhaustion (upslidedown)
**Type:** Counter-Trend  
**Rating:** #1 Community Indicator (per Reddit)

**Features:**
- Catches tops/bottoms
- Counter-trend trading
- Exhaustion signals

---

### 8.5 Lorentzian Classification (jdehorty)
**Author:** jdehorty  
**Type:** Machine Learning  
**Rating:** Most technically advanced

**Features:**
- ML-based price classification
- Pattern recognition
- Highly customizable

---

### 8.6 Hull Suite (insillico)
**Type:** Trend Identification  
**Rating:** Excellent trend tool

**Features:**
- Hull Moving Average
- Multiple HMA variations
- Trend strength

---

### 8.7 Machine Learning Adaptive SuperTrend (AlgoAlpha)
**Author:** AlgoAlpha  
**Award:** Most Boosted Pine Script 2024

**Features:**
- AI-optimized parameters
- Adaptive to market conditions
- Reduced false signals

---

### 8.8 Linear Regression Oscillator (ChartPrime)
**Author:** ChartPrime  
**Award:** Most Boosted 2024

**Features:**
- Statistical trend analysis
- Mean reversion signals
- Regression channels

---

### 8.9 DTFX Algo Zones (LuxAlgo)
**Author:** LuxAlgo  
**Award:** Most Boosted 2024

**Features:**
- Algorithmic support/resistance
- Zone-based trading
- Multi-timeframe

---

### 8.10 Ichimoku Oscillator (LonesomeTheBlue)
**Author:** LonesomeTheBlue  
**Award:** Most Commented Pine Script 2024

**Features:**
- Ichimoku-based oscillator
- Cloud momentum
- Trend strength

---

## 9. Pine Script Code Examples

### 9.1 Basic Strategy Template
```pinescript
//@version=5
strategy("My Strategy", overlay=true)

// Inputs
fastLength = input.int(12, "Fast Length")
slowLength = input.int(26, "Slow Length")

// Calculations
fastMA = ta.ema(close, fastLength)
slowMA = ta.ema(close, slowLength)

// Conditions
longCondition = ta.crossover(fastMA, slowMA)
shortCondition = ta.crossunder(fastMA, slowMA)

// Entries
if longCondition
    strategy.entry("Long", strategy.long)

if shortCondition
    strategy.entry("Short", strategy.short)

// Plots
plot(fastMA, "Fast MA", color.blue)
plot(slowMA, "Slow MA", color.orange)
```

### 9.2 Strategy with Stop Loss and Take Profit
```pinescript
//@version=5
strategy("Strategy with SL/TP", overlay=true)

// Entry condition
longCondition = ta.crossover(ta.sma(close, 14), ta.sma(close, 28))

if longCondition
    strategy.entry("Long", strategy.long)
    
// Exit with SL and TP
strategy.exit("Exit", "Long", 
     stop=close * 0.95,      // 5% stop loss
     limit=close * 1.10)     // 10% take profit
```

### 9.3 Multi-Timeframe Strategy
```pinescript
//@version=5
strategy("MTF Strategy", overlay=true)

// Get higher timeframe data
htfClose = request.security(syminfo.tickerid, "60", close)
htfSMA = request.security(syminfo.tickerid, "60", ta.sma(close, 20))

// Current timeframe
ctfSMA = ta.sma(close, 20)

// Entry when both timeframes align
longCondition = close > ctfSMA and htfClose > htfSMA

if longCondition
    strategy.entry("Long", strategy.long)
```

### 9.4 ATR-Based Position Sizing
```pinescript
//@version=5
strategy("ATR Sizing", overlay=true, default_qty_type=strategy.cash)

riskPercent = input.float(2.0, "Risk %") / 100
atrPeriod = input.int(14, "ATR Period")
atrMultiplier = input.float(2.0, "ATR Multiplier")

atr = ta.atr(atrPeriod)
stopDistance = atr * atrMultiplier

// Calculate position size based on risk
riskAmount = strategy.equity * riskPercent
qty = riskAmount / stopDistance

if longCondition
    strategy.entry("Long", strategy.long, qty=qty)
    strategy.exit("Stop", "Long", stop=close - stopDistance)
```

---

## 10. Strategy Performance Summary

### 10.1 Performance Metrics to Track
- **Net Profit/Loss:** Total returns
- **Profit Factor:** Gross profit / Gross loss
- **Win Rate:** % of winning trades
- **Average Win/Loss:** Expectancy
- **Max Drawdown:** Largest peak-to-trough decline
- **Sharpe Ratio:** Risk-adjusted returns
- **Sortino Ratio:** Downside risk-adjusted returns

### 10.2 Strategy Categories Summary

| Category | Best Market Condition | Complexity | Win Rate Potential |
|----------|----------------------|------------|-------------------|
| Trend Following (SuperTrend) | Strong Trends | Low-Medium | 40-50% |
| Mean Reversion (RSI/BB) | Ranging Markets | Low | 55-65% |
| Momentum (MACD) | Trending Markets | Low | 45-55% |
| Breakout (Donchian/BB) | Low Volatility → High | Medium | 35-45% |
| Multi-Indicator | All (filtered) | High | 50-60% |

### 10.3 Recommended Strategy Combinations

**For Beginners:**
1. EMA Crossover (simple, visual)
2. RSI Mean Reversion (clear signals)
3. Basic SuperTrend (trend following)

**For Intermediate Traders:**
1. MACD + RSI + EMA combo
2. Bollinger Bands Squeeze
3. Multi-Timeframe EMA

**For Advanced Traders:**
1. Machine Learning Adaptive SuperTrend
2. Lorentzian Classification
3. Custom multi-factor strategies

### 10.4 Timeframe Recommendations

| Strategy Type | Best Timeframes | Holding Period |
|--------------|-----------------|----------------|
| Scalping | 1m, 5m | Minutes |
| Day Trading | 5m, 15m, 1H | Hours |
| Swing Trading | 1H, 4H, Daily | Days-Weeks |
| Position Trading | Daily, Weekly | Weeks-Months |

---

## 11. Key Pine Script Authors (Wizards)

### Most Popular Authors:
1. **LazyBear** - Foundation of Pine Script, Squeeze Momentum, WaveTrend
2. **RicardoSantos** - Pushes Pine Script limits
3. **ChrisMoody** - Practical trading tools
4. **LonesomeTheBlue** - Creative, elegant code
5. **LuxAlgo** - Professional toolkits
6. **AlgoAlpha** - Machine learning strategies
7. **ChartPrime** - Advanced oscillators
8. **jdehorty** - Machine learning expertise
9. **KivancOzbilgic** - Turkish community leader
10. **everget** - Specialist indicators

---

## 12. Risk Management Best Practices

### 12.1 Position Sizing
- Risk 1-2% per trade maximum
- Use ATR for volatility-adjusted sizing
- Account for commission and slippage

### 12.2 Stop Loss Strategies
- Fixed percentage (1-3%)
- ATR-based (1.5-3x ATR)
- Technical levels (swings, S/R)
- Trailing stops

### 12.3 Take Profit Strategies
- Fixed R:R ratio (1:2, 1:3)
- Technical targets
- Partial profits (scale out)
- Trailing profits

### 12.4 Backtesting Checklist
- [ ] Test on multiple timeframes
- [ ] Test on multiple assets
- [ ] Include commission costs
- [ ] Include slippage
- [ ] Test in different market conditions
- [ ] Forward test before live trading
- [ ] Check for curve-fitting

---

## 13. Common Pitfalls to Avoid

1. **Curve Fitting:** Over-optimizing for past data
2. **Lookahead Bias:** Using future data in backtests
3. **Repainting:** Signals that change after bar close
4. **Overtrading:** Too many signals, high commission costs
5. **Ignoring Market Regimes:** Strategy not suited to current conditions
6. **Poor Risk Management:** No stops or oversized positions
7. **Commission Neglect:** Not accounting for trading costs

---

## 14. Resources for Further Learning

### Official Resources:
- TradingView Pine Script Documentation
- TradingView Strategy Tester Guide
- PineCoders Community

### Community Resources:
- Pine Script Wizards page
- TradingView Scripts section (100,000+ scripts)
- Reddit r/TradingView
- Discord trading communities

### Educational Content:
- Pine Script Mastery courses
- The Art of Trading tutorials
- LuxAlgo blog and guides

---

## Conclusion

This report provides a comprehensive overview of 50+ TradingView strategies covering all major categories: trend following, mean reversion, momentum, breakout, and multi-indicator approaches. The strategies range from simple built-in templates to advanced machine learning implementations by community wizards.

**Key Takeaways:**
1. No single strategy works in all market conditions
2. Risk management is more important than entry signals
3. Backtest thoroughly before live trading
4. Combine multiple indicators for confirmation
5. Adjust position size based on volatility
6. Forward test to validate backtest results

**Next Steps:**
1. Select 3-5 strategies matching your trading style
2. Backtest on your preferred assets and timeframes
3. Paper trade for validation
4. Implement proper risk management
5. Monitor and adjust as market conditions change

---

*Report compiled: February 2025*  
*Sources: TradingView Community Scripts, Pine Script Documentation, TradingView 2024 Community Awards, Reddit r/TradingView, Various Trading Blogs*
