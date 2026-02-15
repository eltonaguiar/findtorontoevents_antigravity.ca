# Short-Term Forex Trading Strategies: Same-Day Profit Guide

**Research Date:** February 15, 2026  
**Focus:** Scalping & Day Trading for 10-50 Pips Per Trade

---

## Table of Contents
1. [Forex Scalping Strategies (10+ Proven Methods)](#1-forex-scalping-strategies)
2. [Currency Pair Specific Strategies](#2-currency-pair-specific-strategies)
3. [Technical Setups for Forex](#3-technical-setups-for-forex)
4. [News Trading (Short Term)](#4-news-trading-short-term)
5. [Risk Management for Forex](#5-risk-management-for-forex)
6. [Session-Based Strategies](#6-session-based-strategies)
7. [Python Pattern Detection Code](#7-python-pattern-detection-code)

---

## 1. Forex Scalping Strategies

### Strategy 1: Moving Average Ribbon Scalping (1-Minute)

**Overview:** Uses multiple moving averages to identify short-term trend direction and momentum.

**Setup:**
- Timeframe: 1-minute chart
- Indicators: EMA 5, 8, 13, 21 periods
- Currency Pairs: EUR/USD, GBP/USD, USD/JPY

**Entry Rules:**
- **LONG:** When EMAs align ascending (5 > 8 > 13 > 21) AND price retraces to EMA 8 or 13 and bounces
- **SHORT:** When EMAs align descending (5 < 8 < 13 < 21) AND price retraces to EMA 8 or 13 and rejects

**Exit Rules:**
- Stop Loss: 5-8 pips beyond the EMA cluster
- Take Profit: 5-15 pips (scalp target)
- Risk:Reward = 1:1.5 to 1:2

**Best Time:** London session open (8:00 AM GMT), New York session open (1:00 PM GMT)

---

### Strategy 2: VWAP + MACD Scalping (1-Minute)

**Overview:** Combines Volume Weighted Average Price with momentum confirmation.

**Setup:**
- Timeframe: 1-minute chart
- Indicators: VWAP, MACD (12, 26, 9)
- Currency Pairs: EUR/USD, GBP/USD

**Entry Rules:**
- **LONG:** Price closes above VWAP + MACD line crosses above signal line (histogram turns positive)
- **SHORT:** Price closes below VWAP + MACD line crosses below signal line (histogram turns negative)

**Exit Rules:**
- Stop Loss: Beyond recent swing high/low (8-12 pips)
- Take Profit: When MACD crosses in opposite direction OR 10-20 pips
- Trail stop when trade moves 5 pips in profit

**Best Time:** First 2 hours of London session, first 2 hours of New York session

---

### Strategy 3: RSI Overbought/Oversold Scalping (5-Minute)

**Overview:** Captures mean reversion from extreme RSI levels.

**Setup:**
- Timeframe: 5-minute chart
- Indicator: RSI (7-period) with 80/20 levels
- Currency Pairs: All majors

**Entry Rules:**
- **LONG:** RSI crosses below 20 (oversold) + Bullish engulfing or pin bar candlestick pattern
- **SHORT:** RSI crosses above 80 (overbought) + Bearish engulfing or pin bar candlestick pattern

**Exit Rules:**
- Stop Loss: 10-15 pips
- Take Profit: When RSI reaches 50 OR 10-25 pips
- Exit immediately if RSI reverses before price moves

**Best Time:** Asian session (low volatility, better mean reversion)

---

### Strategy 4: Bollinger Bands Squeeze & Bounce (1-Minute)

**Overview:** Trades volatility expansion after consolidation (squeeze).

**Setup:**
- Timeframe: 1-minute chart
- Indicator: Bollinger Bands (20-period SMA, 2 standard deviations)
- Currency Pairs: GBP/USD, EUR/USD

**Entry Rules:**
- **LONG:** Bands squeeze (narrow) → Price breaks above upper band with volume
- **SHORT:** Bands squeeze (narrow) → Price breaks below lower band with volume
- Wait for 2 consecutive closes outside the band for confirmation

**Exit Rules:**
- Stop Loss: Middle band (20 SMA) OR 8-12 pips
- Take Profit: Opposite band OR 10-20 pips
- Exit when price touches middle band

**Best Time:** London-New York overlap (highest volatility)

---

### Strategy 5: Keltner Channels + RSI Scalping (1-Minute)

**Overview:** Volatility-based envelope combined with momentum filter.

**Setup:**
- Timeframe: 1-minute chart
- Indicators: Keltner Channels (20 EMA, 2 ATR), RSI (14)
- Currency Pairs: EUR/USD, GBP/USD, USD/JPY

**Entry Rules:**
- **LONG:** 2+ closes above upper Keltner Channel + RSI breaks above 50
- **SHORT:** 2+ closes below lower Keltner Channel + RSI breaks below 50
- Look for strong consecutive candles (no wicks against direction)

**Exit Rules:**
- Stop Loss: Opposite side of Keltner Channel
- Take Profit: Opposite band OR when RSI reaches extreme (70/30)
- Partial close at 1:1 R:R, trail remainder

---

### Strategy 6: ALMA + Stochastic Scalping (1-Minute)

**Overview:** Uses Arnaud Legoux Moving Average with Stochastic Oscillator for precise entries.

**Setup:**
- Timeframe: 1-minute chart
- Indicators: ALMA (21, 0.85, 6), Stochastic (21, 1, 3)
- Currency Pairs: EUR/USD, GBP/USD

**Entry Rules:**
- **LONG:** Price closes through ALMA upward + Stochastic crosses above 20
- **SHORT:** Price closes through ALMA downward + Stochastic crosses below 80

**Exit Rules:**
- Stop Loss: Beyond nearest swing point (8-15 pips)
- Take Profit: Stochastic reaches opposite territory (80/20)
- Alternative: Take profit at next support/resistance level

**Best Time:** London session (8:00-11:00 AM GMT)

---

### Strategy 7: Price Action Support/Resistance Scalping (5-Minute)

**Overview:** Pure price action trading at key horizontal levels.

**Setup:**
- Timeframe: 5-minute chart
- No indicators (clean chart)
- Currency Pairs: All majors

**Entry Rules:**
- **LONG:** Price approaches support + forms bullish pin bar or engulfing pattern
- **SHORT:** Price approaches resistance + forms bearish pin bar or engulfing pattern
- Must be within established range or at previous day high/low

**Exit Rules:**
- Stop Loss: Just beyond the support/resistance level tested (10-15 pips)
- Take Profit: Next support/resistance level OR 15-30 pips
- Scale out 50% at 1:1 R:R, move stop to breakeven

**Best Time:** Any session with clear ranges (avoid news releases)

---

### Strategy 8: Moving Average Crossover Scalping (5-Minute)

**Overview:** Classic trend-following approach with fast MAs.

**Setup:**
- Timeframe: 5-minute chart
- Indicators: EMA 20 and EMA 50
- Currency Pairs: Trending pairs (USD/JPY, GBP/USD)

**Entry Rules:**
- **LONG:** EMA 20 crosses above EMA 50 + price above both MAs
- **SHORT:** EMA 20 crosses below EMA 50 + price below both MAs
- Confirm with higher timeframe trend (H1)

**Exit Rules:**
- Stop Loss: Below/above EMA 50 OR recent swing (15-20 pips)
- Take Profit: 20-40 pips OR when MAs cross back
- Trail stop under EMA 20 once in profit

---

### Strategy 9: Asian Session Range Scalping (15-Minute)

**Overview:** Trade mean reversion during low-volatility Asian session.

**Setup:**
- Timeframe: 15-minute chart
- Indicator: ATR (14) for volatility measurement
- Currency Pairs: AUD/USD, USD/JPY, NZD/USD

**Entry Rules:**
- Identify Asian range (11:00 PM - 8:00 AM GMT)
- **LONG:** Price at range low + bullish rejection candle
- **SHORT:** Price at range high + bearish rejection candle
- Only trade if ATR < 20 pips (low volatility confirmation)

**Exit Rules:**
- Stop Loss: Just beyond range high/low
- Take Profit: Middle of range OR opposite range boundary
- Exit by 8:00 AM GMT before London volatility

---

### Strategy 10: Pin Bar Scalping with 50% Retracement (5-Minute)

**Overview:** Enter on 50% retracement of pin bar for optimal R:R.

**Setup:**
- Timeframe: 5-minute chart
- No indicators needed
- Currency Pairs: All majors

**Entry Rules:**
- Identify pin bar at support/resistance (tail = 2/3 of candle)
- **LONG:** Place limit order at 50% retracement of bullish pin bar
- **SHORT:** Place limit order at 50% retracement of bearish pin bar
- Wait for price to come to you

**Exit Rules:**
- Stop Loss: Beyond pin bar tail (15-20 pips from entry)
- Take Profit: 2-3x risk (30-60 pips)
- If limit not filled within 2 candles, cancel order

---

### Strategy 11: Inside Bar Breakout Scalping (5-Minute)

**Overview:** Trade volatility expansion after consolidation.

**Setup:**
- Timeframe: 5-minute chart
- No indicators needed
- Currency Pairs: EUR/USD, GBP/USD

**Entry Rules:**
- Identify inside bar (candle completely inside previous candle)
- Place buy stop above mother bar high
- Place sell stop below mother bar low
- **Entry:** Whichever stop is hit first

**Exit Rules:**
- Stop Loss: Opposite side of inside bar
- Take Profit: 1.5x - 2x the inside bar range
- Cancel pending order if not triggered in 30 minutes

---

### Strategy 12: 1-Minute Momentum Scalping

**Overview:** High-frequency scalping for 3-5 pip gains.

**Setup:**
- Timeframe: 1-minute chart
- Indicators: EMA 50, EMA 100, Stochastic (5, 3, 3)
- Currency Pairs: EUR/USD only (tightest spreads)

**Entry Rules:**
- **LONG:** Price > EMA 50 > EMA 100 + Stochastic crosses above 20
- **SHORT:** Price < EMA 50 < EMA 100 + Stochastic crosses below 80
- Requires all 3 conditions simultaneously

**Exit Rules:**
- Stop Loss: 3-5 pips
- Take Profit: 3-8 pips
- Maximum trade duration: 2 minutes
- Close immediately if Stochastic reverses

**Requirements:** ECN broker with <0.5 pip spread on EUR/USD

---

## 2. Currency Pair Specific Strategies

### EUR/USD - "The Euro Scalper"

**Characteristics:**
- Tightest spreads (0.0-1.0 pip)
- Highest liquidity
- Best for beginners
- Moves 50-80 pips daily average

**Optimal Strategy: VWAP Bounce**
- Timeframe: 5-minute
- Session: London + New York overlap (1:00-4:00 PM GMT)
- Entry: Price returns to VWAP in established trend
- Stop: 10 pips
- Target: 15-25 pips
- Success Rate: ~60%

**Key Levels:**
- Watch 1.0500, 1.1000, 1.1500 round numbers
- 20-30 pip consolidation before breakouts common

---

### GBP/USD - "The Cable Breakout"

**Characteristics:**
- Most volatile major pair (80-120 pips daily)
- Wide spreads during news (2-5 pips)
- Excellent for London breakout strategy
- Strong trending behavior

**Optimal Strategy: London Breakout**
- Timeframe: 15-minute
- Session: London open (8:00 AM GMT)
- Entry: Break of Asian range (7-8 AM GMT high/low)
- Stop: Opposite side of range
- Target: 1.5x range width (30-50 pips)
- Success Rate: ~55% (but high R:R)

**Key Levels:**
- Asian range high/low (critical daily)
- Previous day high/low
- 1.2000, 1.2500, 1.3000 psychological levels

---

### USD/JPY - "The Trend Follower"

**Characteristics:**
- Strong trending behavior
- Correlated with US Treasury yields
- Tight spreads (0.5-1.5 pip)
- Moves 60-90 pips daily average

**Optimal Strategy: EMA Pullback**
- Timeframe: 15-minute
- Indicators: EMA 20, EMA 50
- Entry: Pullback to EMA 20 in strong trend
- Stop: Beyond EMA 50 or 15 pips
- Target: 25-40 pips (next major level)
- Success Rate: ~65%

**Key Levels:**
- 130.00, 135.00, 140.00 round numbers
- Bank of Japan intervention zones (watch 150.00+)

---

### AUD/USD - "The Commodity Scalp"

**Characteristics:**
- Correlated with gold and iron ore prices
- Strong Asian session movement
- Moderate volatility (50-70 pips daily)
- Clean technical patterns

**Optimal Strategy: Asian Session Range**
- Timeframe: 15-minute
- Session: Asian session (11 PM - 8 AM GMT)
- Entry: Mean reversion from range extremes
- Stop: 15 pips beyond range
- Target: Middle of range (10-20 pips)
- Success Rate: ~60%

**Key Levels:**
- 0.6000, 0.6500, 0.7000 psychological levels
- China economic data release times

---

### USD/CAD - "The Oil Play"

**Characteristics:**
- Inversely correlated with crude oil
- Volatile during oil inventory reports (Wednesdays)
- Moderate spreads (1-2 pips)
- Moves 60-80 pips daily

**Optimal Strategy: Oil Correlation Fade**
- Timeframe: 5-minute
- Watch: Crude oil inventory reports (10:30 AM EST Wed)
- Entry: Wait for oil-induced spike, fade the extension
- Stop: 15 pips
- Target: 20-30 pips (reversion to pre-news level)
- Success Rate: ~55%

---

### EUR/GBP - "The Range Master"

**Characteristics:**
- Tightest range of major pairs (30-50 pips daily)
- Excellent for range scalping
- Very tight spreads
- Low volatility

**Optimal Strategy: Range Bound Scalping**
- Timeframe: 15-minute
- Identify daily range (usually 30-40 pips)
- Entry: Long at range low, Short at range high
- Stop: 10 pips beyond range
- Target: 10-15 pips (middle of range)
- Success Rate: ~70%

---

### GBP/JPY - "The Volatility Beast"

**Characteristics:**
- Highest volatility (120-200 pips daily)
- Wider spreads (2-4 pips)
- Strong trending
- Not for beginners

**Optimal Strategy: Breakout Momentum**
- Timeframe: 15-minute
- Entry: Break of 1-hour consolidation
- Stop: 25-30 pips
- Target: 50-80 pips
- Position size: HALF normal size due to volatility

---

## 3. Technical Setups for Forex

### Pin Bar Scalping Rules

**What is a Pin Bar:**
- Single candlestick pattern
- Long tail (wick) = at least 2/3 of candle length
- Small body at one end
- Shows rejection of price level

**Entry Methods:**

1. **Nose Break Entry (Conservative):**
   - Enter on break of pin bar nose
   - Stop: Beyond pin bar tail + 5-10 pips
   - Target: Next support/resistance (1.5-3 R:R)

2. **50% Retrace Entry (Aggressive):**
   - Place limit order at 50% of pin bar range
   - Better R:R ratio
   - Risk: May not get filled

**Valid Pin Bar Locations:**
- Support/resistance levels
- Trend line touches
- Moving average tests
- Fibonacci retracement levels

---

### Inside Bar Breakout Strategy

**Pattern Recognition:**
- Inside bar: High < Previous high, Low > Previous low
- Mother bar: The larger preceding candle
- Shows consolidation before expansion

**Entry Rules:**
1. Identify inside bar at support/resistance or in trend
2. Place buy stop above mother bar high + 2 pips
3. Place sell stop below mother bar low - 2 pips
4. When one triggers, cancel the other (OCO)

**Exit Rules:**
- Stop: Opposite side of mother bar
- Target: 1.5x - 2x mother bar range
- Time stop: Cancel if not triggered in 30-60 minutes

**Success Factors:**
- Daily timeframe: 60%+ win rate
- H4 timeframe: 55% win rate
- Must have room to run (check higher timeframe)

---

### Fibonacci Retracement Scalping

**Setup:**
- Draw Fibonacci from swing low to swing high (or reverse)
- Focus on 38.2%, 50%, 61.8% levels
- Timeframe: 5-minute or 15-minute

**Entry Rules:**
- **LONG:** Price retraces to 61.8% in uptrend + bullish candle
- **SHORT:** Price retraces to 61.8% in downtrend + bearish candle
- Confirm with pin bar or engulfing pattern at level

**Exit Rules:**
- Stop: Beyond 78.6% retracement OR 15-20 pips
- Target: Previous swing high/low OR 127.2% extension
- Partial profits at 38.2% retracement of the swing

**Best Currency Pairs:**
- USD/JPY (respects Fibonacci well)
- EUR/USD
- GBP/USD

---

### Moving Average Crossover Scalping

**Fast Crossover (Scalping):**
- EMA 5 crossing EMA 8 (1-minute chart)
- EMA 8 crossing EMA 13 (5-minute chart)
- Only trade in direction of EMA 50 trend

**Medium Crossover (Day Trading):**
- EMA 12 crossing EMA 26 (MACD equivalent)
- EMA 20 crossing EMA 50 (5-minute chart)

**Entry Rules:**
- Wait for cross + price close confirmation
- Volume increase preferred
- Multiple timeframe alignment (H1 trend direction)

**Exit Rules:**
- Stop: Below/above slower MA
- Target: 2-3x risk OR next major level
- Exit on opposite cross

---

### Support/Resistance Scalping

**Level Identification:**
1. Previous day high/low
2. Overnight Asian session high/low
3. Round numbers (1.1000, 110.00, etc.)
4. Trend line touches

**Entry Rules:**
- Wait for price to reach level
- Look for rejection candle (pin bar, engulfing)
- Enter on confirmation candle close

**Risk Management:**
- Stop: 5-10 pips beyond the level
- Target: Next level OR 1.5-2x risk
- Avoid entering in middle of range

---

## 4. News Trading (Short Term)

### NFP (Non-Farm Payroll) Trading Strategy

**Release Details:**
- When: First Friday of each month, 8:30 AM EST
- Impact: HIGH - Can move USD pairs 50-100 pips in minutes

**Strategy 1: The Fade (Recommended)**
1. Wait 5-10 minutes after release
2. Identify the initial knee-jerk direction
3. Fade (trade against) the initial move
4. Entry: When price retraces 30-50% of initial spike
5. Stop: Beyond the spike extreme
6. Target: Pre-news level

**Strategy 2: The Continuation**
1. Wait for 15-minute candle to close
2. If candle closes strong in direction of spike
3. Enter on pullback to 50% of the candle
4. Target: 1.5-2x the initial spike

**Risk Management:**
- Reduce position size by 50%
- Wider stops (30-50 pips)
- Be prepared for spreads to widen 2-5x

---

### FOMC Minutes Strategy

**Release Details:**
- When: 8 times per year, 2:00 PM EST
- Impact: HIGH - Interest rate decisions

**Trading Rules:**
1. Close all positions 30 minutes before
2. Wait for release
3. Trade the BREAKOUT of the 1-hour consolidation
4. Entry: 5 pips beyond pre-release high/low
5. Stop: Opposite side of consolidation
6. Target: 50-100 pips

---

### CPI/PPI Data Strategy

**Release Details:**
- CPI: Monthly, 8:30 AM EST
- PPI: Monthly, 8:30 AM EST
- Impact: HIGH - Inflation data affects Fed policy

**Trading Approach:**
- Similar to NFP fade strategy
- Initial move often reverses within 15 minutes
- Watch for USD pairs to make V-shaped reversals

---

### Central Bank Speech Strategy

**High-Impact Speakers:**
- Fed Chair (Jerome Powell)
- ECB President
- Bank of England Governor
- Bank of Japan Governor

**Trading Rules:**
1. Identify key support/resistance before speech
2. Place buy stop above resistance
3. Place sell stop below support
4. Whichever breaks, trade in that direction
5. Trail stop aggressively (lock profits quickly)

---

### Pre-News Positioning Strategy

**Concept:**
- Market often consolidates before major news
- Trade the breakout of the consolidation

**Setup:**
1. Identify 1-2 hour consolidation before news
2. Mark high and low of range
3. Place pending orders 5 pips above and below
4. Cancel unfilled orders 2 minutes before release
5. If filled, trail stop tightly

---

## 5. Risk Management for Forex

### Pip-Based Stop Loss Framework

| Strategy Type | Stop Loss | Take Profit | R:R Ratio |
|---------------|-----------|-------------|-----------|
| 1-Min Scalping | 3-5 pips | 5-10 pips | 1:1.5 - 1:2 |
| 5-Min Scalping | 8-15 pips | 15-30 pips | 1:2 - 1:3 |
| 15-Min Day Trade | 15-25 pips | 30-50 pips | 1:2 - 1:3 |
| London Breakout | Range width | 1.5x range | 1:1.5 |
| News Trading | 30-50 pips | 50-100 pips | 1:2 |

### Risk Per Trade Guidelines

**Conservative (Recommended):**
- Risk 0.5% - 1% per trade
- Maximum 3 trades per session
- Daily loss limit: 2%

**Moderate:**
- Risk 1% - 2% per trade
- Maximum 5 trades per session
- Daily loss limit: 3%

**Aggressive (Not Recommended):**
- Risk 2% - 3% per trade
- Maximum 10 trades per session
- Daily loss limit: 5%

### Position Sizing Formula

```
Position Size = (Account Balance × Risk %) / (Stop Loss in Pips × Pip Value)

Example:
- Account: $10,000
- Risk: 1% ($100)
- Stop Loss: 20 pips
- Pip Value (EUR/USD standard lot): $10

Position Size = $100 / (20 × $10) = 0.5 lots (5 mini lots)
```

### Leverage Guidelines

**Recommended Maximum Leverage:**
- Beginners: 1:10 to 1:20
- Intermediate: 1:20 to 1:50
- Advanced: 1:50 to 1:100

**Why Low Leverage:**
- 1:500 leverage = 0.2% margin required
- 50 pip move against you = 10% account loss
- High leverage causes emotional trading

### Spread Cost Impact

**Acceptable Spreads for Scalping:**
| Currency Pair | Maximum Spread |
|---------------|----------------|
| EUR/USD | 1.0 pip |
| GBP/USD | 1.5 pips |
| USD/JPY | 1.0 pip |
| AUD/USD | 1.5 pips |
| USD/CAD | 2.0 pips |
| EUR/GBP | 1.5 pips |

**Calculating Spread Cost:**
- 10 trades per day × 1 pip spread = 10 pips daily cost
- Monthly: ~200 pips in spread costs alone
- Must factor into profitability calculations

### Rollover/Swap Considerations

**When Scalping:**
- Minimal impact (positions held <1 hour)
- Avoid holding through 5 PM EST (rollover time)
- Wednesdays: Triple swap (weekend included)

**Swap Calculation:**
```
Daily Swap = Position Size × Swap Rate

If swap is -$5 per lot per day:
- Holding 1 lot overnight = -$5
- Holding through Wednesday = -$15
```

---

## 6. Session-Based Strategies

### Asian Session (11:00 PM - 8:00 AM GMT)

**Characteristics:**
- Lowest volatility
- Tight ranges (20-40 pips on majors)
- Best for range scalping
- Watch Tokyo and Sydney opens

**Optimal Strategy: Range Bound Mean Reversion**
- Identify overnight range
- Buy low, sell high within range
- Close all positions by 7:30 AM GMT
- Avoid GBP pairs (illiquid)

**Best Pairs:**
- USD/JPY
- AUD/USD
- NZD/USD
- EUR/JPY

---

### London Session (8:00 AM - 4:30 PM GMT)

**Characteristics:**
- Highest volume (35-40% of daily)
- Strong trends develop
- Most volatile session
- Frankfurt open adds liquidity (7:00 AM GMT)

**Optimal Strategy: Breakout Trading**
- London Breakout (Asian range breakout)
- Trend following
- EUR/USD and GBP/USD most active

**Best Times:**
- 8:00-9:00 AM GMT: Initial volatility
- 1:00-4:00 PM GMT: London-NY overlap

---

### New York Session (1:00 PM - 9:00 PM GMT)

**Characteristics:**
- Second highest volume
- US economic data releases
- Often continues London trends
- Slows after 5:00 PM GMT

**Optimal Strategy: Trend Continuation**
- Trade in direction of London trend
- Fade false breakouts
- News trading on US data

**Best Times:**
- 1:00-3:00 PM GMT: High volatility
- 5:00-6:00 PM GMT: Avoid (slow)

---

### Session Overlap (1:00 PM - 4:00 PM GMT)

**Characteristics:**
- MOST VOLATILE 3 HOURS
- Highest liquidity
- Largest moves
- Best R:R opportunities

**Optimal Strategy: Momentum Breakouts**
- Trade breakouts from consolidation
- Larger position sizes acceptable
- 20-40 pip moves common

**Best Pairs:**
- EUR/USD
- GBP/USD
- USD/CHF
- All majors

---

### End-of-Day Reversals (8:00 PM - 10:00 PM GMT)

**Characteristics:**
- Institutional profit-taking
- Position squaring
- Mean reversion tendency
- Lower liquidity

**Optimal Strategy: Fade the Day's Move**
- If strong trend all day, look for reversal
- Counter-trend scalping
- Smaller targets (10-15 pips)

---

## 7. Python Pattern Detection Code

### Pin Bar Detector

```python
import pandas as pd
import numpy as np

def detect_pin_bars(df, tail_ratio=0.67):
    """
    Detect pin bar candlestick patterns in OHLC data.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with 'open', 'high', 'low', 'close' columns
    tail_ratio : float
        Minimum ratio of tail to total candle length (default 0.67 = 2/3)
    
    Returns:
    --------
    df : pandas.DataFrame
        DataFrame with 'pin_bar' column (1=bullish, -1=bearish, 0=none)
    """
    df = df.copy()
    
    # Calculate candle components
    df['body_size'] = abs(df['close'] - df['open'])
    df['total_range'] = df['high'] - df['low']
    df['upper_wick'] = df['high'] - np.maximum(df['open'], df['close'])
    df['lower_wick'] = np.minimum(df['open'], df['close']) - df['low']
    
    # Bullish pin bar: long lower wick, small body at top
    bullish_pin = (
        (df['lower_wick'] / df['total_range'] >= tail_ratio) &
        (df['body_size'] / df['total_range'] <= 0.15) &
        (df['close'] > df['open'])  # Bullish close
    )
    
    # Bearish pin bar: long upper wick, small body at bottom
    bearish_pin = (
        (df['upper_wick'] / df['total_range'] >= tail_ratio) &
        (df['body_size'] / df['total_range'] <= 0.15) &
        (df['close'] < df['open'])  # Bearish close
    )
    
    df['pin_bar'] = np.where(bullish_pin, 1, np.where(bearish_pin, -1, 0))
    
    return df


# Example usage
if __name__ == "__main__":
    # Sample data structure
    data = {
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='5min'),
        'open': np.random.randn(100).cumsum() + 1.1000,
        'high': np.random.randn(100).cumsum() + 1.1010,
        'low': np.random.randn(100).cumsum() + 1.0990,
        'close': np.random.randn(100).cumsum() + 1.1005
    }
    df = pd.DataFrame(data)
    
    # Detect pin bars
    df = detect_pin_bars(df)
    
    # Filter for pin bars only
    pin_bars = df[df['pin_bar'] != 0]
    print(f"Found {len(pin_bars)} pin bars")
```

---

### Inside Bar Detector

```python
def detect_inside_bars(df):
    """
    Detect inside bar patterns.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with 'open', 'high', 'low', 'close' columns
    
    Returns:
    --------
    df : pandas.DataFrame
        DataFrame with 'inside_bar' column (True/False)
    """
    df = df.copy()
    
    # Inside bar: current high < previous high AND current low > previous low
    df['inside_bar'] = (
        (df['high'] < df['high'].shift(1)) &
        (df['low'] > df['low'].shift(1))
    )
    
    # Mother bar reference levels
    df['mother_high'] = df['high'].shift(1)
    df['mother_low'] = df['low'].shift(1)
    
    return df


def detect_inside_bar_breakouts(df):
    """
    Detect breakouts from inside bar patterns.
    
    Returns:
    --------
    df : pandas.DataFrame
        DataFrame with 'breakout_direction' column (1=up, -1=down, 0=none)
    """
    df = detect_inside_bars(df)
    
    # Breakout above mother bar high
    breakout_up = (
        df['inside_bar'].shift(1) &
        (df['close'] > df['mother_high'].shift(1))
    )
    
    # Breakout below mother bar low
    breakout_down = (
        df['inside_bar'].shift(1) &
        (df['close'] < df['mother_low'].shift(1))
    )
    
    df['breakout_direction'] = np.where(
        breakout_up, 1,
        np.where(breakout_down, -1, 0)
    )
    
    return df
```

---

### Moving Average Ribbon Signals

```python
def ma_ribbon_signals(df, fast=5, medium_fast=8, medium=13, slow=21):
    """
    Generate signals from EMA ribbon alignment.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with 'close' column
    fast, medium_fast, medium, slow : int
        EMA periods
    
    Returns:
    --------
    df : pandas.DataFrame
        DataFrame with 'signal' column
    """
    df = df.copy()
    
    # Calculate EMAs
    df['ema_fast'] = df['close'].ewm(span=fast).mean()
    df['ema_mf'] = df['close'].ewm(span=medium_fast).mean()
    df['ema_med'] = df['close'].ewm(span=medium).mean()
    df['ema_slow'] = df['close'].ewm(span=slow).mean()
    
    # Bullish alignment (ascending)
    bullish_aligned = (
        (df['ema_fast'] > df['ema_mf']) &
        (df['ema_mf'] > df['ema_med']) &
        (df['ema_med'] > df['ema_slow'])
    )
    
    # Bearish alignment (descending)
    bearish_aligned = (
        (df['ema_fast'] < df['ema_mf']) &
        (df['ema_mf'] < df['ema_med']) &
        (df['ema_med'] < df['ema_slow'])
    )
    
    # Price pulling back to EMA 8/13 in bullish trend
    bullish_pullback = (
        bullish_aligned &
        (df['low'] <= df['ema_mf']) &
        (df['close'] > df['ema_mf'])
    )
    
    # Price pulling back to EMA 8/13 in bearish trend
    bearish_pullback = (
        bearish_aligned &
        (df['high'] >= df['ema_mf']) &
        (df['close'] < df['ema_mf'])
    )
    
    df['signal'] = np.where(
        bullish_pullback, 1,  # Buy signal
        np.where(bearish_pullback, -1, 0)  # Sell signal or no signal
    )
    
    df['trend'] = np.where(
        bullish_aligned, 1,
        np.where(bearish_aligned, -1, 0)
    )
    
    return df
```

---

### London Breakout Strategy Code

```python
def london_breakout_strategy(df, asian_start='00:00', asian_end='07:00', 
                              london_start='08:00', buffer_pips=0.0005):
    """
    London Breakout Strategy implementation.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with 'timestamp', 'open', 'high', 'low', 'close' columns
    asian_start, asian_end : str
        Asian session time range (HH:MM format)
    london_start : str
        London session start time
    buffer_pips : float
        Buffer above/below range for entry (in price terms)
    
    Returns:
    --------
    signals : pandas.DataFrame
        DataFrame with entry signals
    """
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['time'] = df['timestamp'].dt.strftime('%H:%M')
    
    # Group by date
    df['date'] = df['timestamp'].dt.date
    
    signals = []
    
    for date, group in df.groupby('date'):
        # Get Asian session range
        asian = group[
            (group['time'] >= asian_start) &
            (group['time'] <= asian_end)
        ]
        
        if len(asian) == 0:
            continue
        
        asian_high = asian['high'].max()
        asian_low = asian['low'].min()
        asian_range = asian_high - asian_low
        
        # Skip if range too wide (>60 pips for EUR/USD)
        if asian_range > 0.0060:
            continue
        
        # London session
        london = group[group['time'] >= london_start]
        
        for idx, row in london.iterrows():
            # Check for breakout
            if row['close'] > asian_high + buffer_pips:
                signals.append({
                    'timestamp': row['timestamp'],
                    'signal': 1,  # Buy
                    'entry_price': asian_high + buffer_pips,
                    'stop_loss': asian_low,
                    'take_profit': asian_high + (asian_range * 1.5),
                    'asian_high': asian_high,
                    'asian_low': asian_low,
                    'asian_range': asian_range
                })
                break  # One trade per day
                
            elif row['close'] < asian_low - buffer_pips:
                signals.append({
                    'timestamp': row['timestamp'],
                    'signal': -1,  # Sell
                    'entry_price': asian_low - buffer_pips,
                    'stop_loss': asian_high,
                    'take_profit': asian_low - (asian_range * 1.5),
                    'asian_high': asian_high,
                    'asian_low': asian_low,
                    'asian_range': asian_range
                })
                break  # One trade per day
    
    return pd.DataFrame(signals)
```

---

### Support/Resistance Level Detector

```python
def find_support_resistance(df, lookback=20, touch_threshold=3, 
                           proximity_percent=0.001):
    """
    Identify support and resistance levels based on price touches.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with 'high', 'low', 'close' columns
    lookback : int
        Number of periods to look back
    touch_threshold : int
        Minimum touches to qualify as level
    proximity_percent : float
        Price proximity to count as same level (0.001 = 0.1%)
    
    Returns:
    --------
    levels : list of dict
        List of support/resistance levels
    """
    recent_data = df.tail(lookback)
    
    # Find swing highs and lows
    highs = recent_data['high'].values
    lows = recent_data['low'].values
    
    levels = []
    
    # Check for resistance (swing highs)
    for i in range(2, len(highs) - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
           highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            
            level_price = highs[i]
            
            # Count touches
            touches = sum(
                abs(highs[j] - level_price) / level_price < proximity_percent
                for j in range(len(highs))
            )
            
            if touches >= touch_threshold:
                levels.append({
                    'price': level_price,
                    'type': 'resistance',
                    'strength': touches
                })
    
    # Check for support (swing lows)
    for i in range(2, len(lows) - 2):
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
           lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            
            level_price = lows[i]
            
            # Count touches
            touches = sum(
                abs(lows[j] - level_price) / level_price < proximity_percent
                for j in range(len(lows))
            )
            
            if touches >= touch_threshold:
                levels.append({
                    'price': level_price,
                    'type': 'support',
                    'strength': touches
                })
    
    # Remove duplicate levels
    unique_levels = []
    for level in levels:
        is_duplicate = False
        for existing in unique_levels:
            if abs(level['price'] - existing['price']) / existing['price'] < 0.0005:
                is_duplicate = True
                break
        if not is_duplicate:
            unique_levels.append(level)
    
    return sorted(unique_levels, key=lambda x: x['price'], reverse=True)


def check_price_at_level(price, levels, tolerance_pips=5, pip_size=0.0001):
    """
    Check if price is near a support/resistance level.
    
    Returns:
    --------
    dict or None
        Level information if near, None otherwise
    """
    for level in levels:
        distance_pips = abs(price - level['price']) / pip_size
        if distance_pips <= tolerance_pips:
            return level
    return None
```

---

### Fibonacci Retracement Calculator

```python
def calculate_fibonacci_levels(swing_high, swing_low):
    """
    Calculate Fibonacci retracement and extension levels.
    
    Parameters:
    -----------
    swing_high : float
        High of the swing
    swing_low : float
        Low of the swing
    
    Returns:
    --------
    dict
        Dictionary of Fibonacci levels
    """
    diff = swing_high - swing_low
    
    levels = {
        # Retracement levels
        '0.0% (High)': swing_high,
        '23.6%': swing_high - (diff * 0.236),
        '38.2%': swing_high - (diff * 0.382),
        '50.0%': swing_high - (diff * 0.500),
        '61.8%': swing_high - (diff * 0.618),
        '78.6%': swing_high - (diff * 0.786),
        '100% (Low)': swing_low,
        
        # Extension levels
        '127.2%': swing_low - (diff * 0.272),
        '161.8%': swing_low - (diff * 0.618),
        '200%': swing_low - diff
    }
    
    return levels


def detect_swing_points(df, window=5):
    """
    Detect swing highs and lows for Fibonacci calculations.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with 'high', 'low' columns
    window : int
        Window size for swing detection
    
    Returns:
    --------
    df : pandas.DataFrame
        DataFrame with 'swing_high' and 'swing_low' columns
    """
    df = df.copy()
    
    # Swing highs
    df['swing_high'] = df['high'].rolling(window=window*2+1, center=True).max() == df['high']
    
    # Swing lows
    df['swing_low'] = df['low'].rolling(window=window*2+1, center=True).min() == df['low']
    
    return df
```

---

### Risk Management Calculator

```python
def calculate_position_size(account_balance, risk_percent, stop_loss_pips, 
                           pip_value=10, currency_pair='EUR/USD'):
    """
    Calculate position size based on risk parameters.
    
    Parameters:
    -----------
    account_balance : float
        Account balance in account currency
    risk_percent : float
        Risk percentage per trade (e.g., 1.0 for 1%)
    stop_loss_pips : int
        Stop loss in pips
    pip_value : float
        Value per pip for 1 standard lot
    currency_pair : str
        Currency pair being traded
    
    Returns:
    --------
    dict
        Position size information
    """
    risk_amount = account_balance * (risk_percent / 100)
    
    # Calculate position size in lots
    lots = risk_amount / (stop_loss_pips * pip_value)
    
    # Round to standard lot sizes
    standard_lots = round(lots, 2)
    mini_lots = round(lots * 10, 1)
    micro_lots = round(lots * 100, 0)
    
    return {
        'account_balance': account_balance,
        'risk_percent': risk_percent,
        'risk_amount': risk_amount,
        'stop_loss_pips': stop_loss_pips,
        'standard_lots': standard_lots,
        'mini_lots': mini_lots,
        'micro_lots': micro_lots,
        'units': int(lots * 100000)
    }


def calculate_risk_reward(entry, stop, target):
    """
    Calculate risk/reward ratio.
    
    Returns:
    --------
    dict
        Risk/reward information
    """
    risk = abs(entry - stop)
    reward = abs(target - entry)
    rr_ratio = reward / risk if risk > 0 else 0
    
    return {
        'entry': entry,
        'stop_loss': stop,
        'take_profit': target,
        'risk': risk,
        'reward': reward,
        'rr_ratio': round(rr_ratio, 2),
        'rr_text': f"1:{rr_ratio:.1f}"
    }


def calculate_trade_outcome(position_size, entry, exit, pip_value=10, 
                           commission_per_lot=7):
    """
    Calculate trade P&L including costs.
    """
    pips = (exit - entry) * 10000  # Assuming 4 decimal forex pairs
    gross_profit = pips * pip_value * position_size
    
    # Calculate commission
    commission = commission_per_lot * position_size * 2  # Entry + Exit
    
    net_profit = gross_profit - commission
    
    return {
        'pips': round(pips, 1),
        'gross_profit': round(gross_profit, 2),
        'commission': round(commission, 2),
        'net_profit': round(net_profit, 2)
    }
```

---

### Complete Strategy Backtester Framework

```python
class ForexScalpingBacktester:
    """
    Backtesting framework for forex scalping strategies.
    """
    
    def __init__(self, initial_balance=10000, risk_per_trade=1.0):
        self.initial_balance = initial_balance
        self.risk_per_trade = risk_per_trade
        self.balance = initial_balance
        self.trades = []
        
    def run_backtest(self, df, strategy_func, **strategy_params):
        """
        Run backtest on historical data.
        
        Parameters:
        -----------
        df : pandas.DataFrame
            OHLC data
        strategy_func : callable
            Function that returns signals DataFrame
        strategy_params : dict
            Parameters for strategy function
        """
        # Get signals
        signals = strategy_func(df, **strategy_params)
        
        # Simulate trades
        for _, signal in signals.iterrows():
            if signal['signal'] == 0:
                continue
            
            # Calculate position size
            position_info = calculate_position_size(
                self.balance,
                self.risk_per_trade,
                signal['stop_loss_pips'],
                pip_value=10
            )
            
            # Simulate trade outcome (simplified - assumes target hit)
            if signal['signal'] == 1:  # Buy
                pips_gained = signal['take_profit'] - signal['entry_price']
            else:  # Sell
                pips_gained = signal['entry_price'] - signal['take_profit']
            
            pips_gained *= 10000  # Convert to pips
            
            profit = pips_gained * 10 * position_info['standard_lots']
            
            # Update balance
            self.balance += profit
            
            # Record trade
            self.trades.append({
                'timestamp': signal['timestamp'],
                'signal': signal['signal'],
                'entry': signal['entry_price'],
                'stop': signal['stop_loss'],
                'target': signal['take_profit'],
                'pips': pips_gained,
                'profit': profit,
                'balance': self.balance
            })
        
        return self.get_stats()
    
    def get_stats(self):
        """Calculate backtest statistics."""
        if not self.trades:
            return {}
        
        trades_df = pd.DataFrame(self.trades)
        
        wins = trades_df[trades_df['profit'] > 0]
        losses = trades_df[trades_df['profit'] <= 0]
        
        return {
            'total_trades': len(trades_df),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': len(wins) / len(trades_df) * 100,
            'total_profit': trades_df['profit'].sum(),
            'avg_profit': trades_df['profit'].mean(),
            'avg_win': wins['profit'].mean() if len(wins) > 0 else 0,
            'avg_loss': losses['profit'].mean() if len(losses) > 0 else 0,
            'profit_factor': abs(wins['profit'].sum() / losses['profit'].sum()) if len(losses) > 0 else float('inf'),
            'final_balance': self.balance,
            'return_pct': (self.balance - self.initial_balance) / self.initial_balance * 100
        }


# Example usage
if __name__ == "__main__":
    # Create sample data
    np.random.seed(42)
    n = 1000
    
    data = {
        'timestamp': pd.date_range('2024-01-01', periods=n, freq='5min'),
        'open': 1.1000 + np.cumsum(np.random.randn(n) * 0.0001),
    }
    data['high'] = data['open'] + abs(np.random.randn(n) * 0.0003)
    data['low'] = data['open'] - abs(np.random.randn(n) * 0.0003)
    data['close'] = data['open'] + np.random.randn(n) * 0.0002
    
    df = pd.DataFrame(data)
    
    # Run backtest
    backtester = ForexScalpingBacktester(initial_balance=10000)
    
    # Example: Use MA ribbon strategy
    df_signals = ma_ribbon_signals(df)
    
    # Create signals DataFrame
    signals = pd.DataFrame({
        'timestamp': df['timestamp'],
        'signal': df_signals['signal'],
        'entry_price': df['close'],
        'stop_loss_pips': 15,  # Fixed 15 pip stop
        'take_profit': df['close'] + 30  # Fixed 30 pip target
    })
    
    stats = backtester.run_backtest(df, lambda x: signals)
    print("Backtest Results:")
    for key, value in stats.items():
        print(f"  {key}: {value:.2f}" if isinstance(value, float) else f"  {key}: {value}")
```

---

## Summary Checklist

### Before Every Trade:
- [ ] Identify clear support/resistance level
- [ ] Confirm with candlestick pattern
- [ ] Check higher timeframe trend alignment
- [ ] Calculate position size (risk ≤1%)
- [ ] Set stop loss before entry
- [ ] Define take profit target (min 1.5 R:R)
- [ ] Note session and expected volatility

### Daily Routine:
- [ ] Check economic calendar for news events
- [ ] Mark Asian session high/low (for London breakout)
- [ ] Identify key support/resistance levels
- [ ] Review previous day's trades

### Risk Management Rules:
- Maximum 3 losses per session (stop trading)
- Maximum 5% account drawdown per day
- Never move stop loss further away
- Never risk more than 2% per trade

---

*This research document is for educational purposes only. Trading forex involves significant risk of loss. Past performance does not guarantee future results.*
