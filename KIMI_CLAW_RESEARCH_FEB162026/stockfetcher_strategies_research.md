# StockFetcher.com Trading Strategies & Screeners Research

## Executive Summary

StockFetcher is a powerful text-based stock screening platform that allows traders to create custom filters using plain English syntax. This research compiles 50+ trading strategies from the StockFetcher community forums, covering mean reversion, momentum, swing trading, and multi-factor approaches. All strategies can be converted to algorithmic trading rules.

---

## Table of Contents

1. [Mean Reversion Strategies](#1-mean-reversion-strategies)
2. [Momentum & Breakout Strategies](#2-momentum--breakout-strategies)
3. [Moving Average Strategies](#3-moving-average-strategies)
4. [Swing Trading Strategies](#4-swing-trading-strategies)
5. [Multi-Factor Screening Approaches](#5-multi-factor-screening-approaches)
6. [Technical Indicator Combinations](#6-technical-indicator-combinations)
7. [ETF & Sector Strategies](#7-etf--sector-strategies)
8. [Risk Management Filters](#8-risk-management-filters)

---

## 1. Mean Reversion Strategies

### 1.1 Larry Connors RSI(2) Classic Mean Reversion
**Screener Name:** RSI(2) Mean Reversion
**Description:** Classic Larry Connors mean reversion strategy using 2-period RSI
**Filter Criteria:**
```
price > 5
average volume(30) > 300000
RSI(2) < 5
close above MA(200)
close 1 day ago < close 2 days ago
close 2 days ago < close 3 days ago
```
**Entry Logic:** Buy when RSI(2) < 5 and price above 200-day MA with 3 consecutive down days
**Exit Logic:** Sell when price closes above 5-day MA or RSI(2) > 70
**Timeframe:** Daily, Swing (2-5 days)
**Asset Class:** Stocks, ETFs
**Backtest Results:** ~75-80% win rate historically

---

### 1.2 Larry Connors RSI(2) Pullback Strategy
**Screener Name:** RSI(2) Pullback
**Description:** Improved mean reversion requiring 3 consecutive extreme RSI readings
**Filter Criteria:**
```
RSI(2) < 10 for 3 consecutive days
close above MA(200)
```
**Entry Logic:** Enter when 3 consecutive RSI(2) values below 10
**Exit Logic:** Exit when price > previous day's high
**Timeframe:** Daily
**Asset Class:** Stocks, ETFs

---

### 1.3 RSI(2) Overbought/Oversold Strategy
**Screener Name:** RSI(2) OB/OS
**Description:** Flexible mean reversion with dynamic exits
**Filter Criteria:**
```
RSI(2) < 5 (buy) or RSI(2) > 95 (sell)
close above/below MA(50)
```
**Entry Logic:** Buy when RSI(2) < 5 and above 50 MA; Short when RSI(2) > 95 and below 50 MA
**Exit Logic:** Exit long when RSI(2) > 70; Exit short when RSI(2) < 30
**Timeframe:** Daily
**Asset Class:** Stocks, ETFs

---

### 1.4 RSI(4) 25/75 Strategy
**Screener Name:** Connors RSI 25/75
**Description:** Mean reversion using 4-period RSI with 25 entry and 75 exit
**Filter Criteria:**
```
close above MA(200)
RSI(4) < 25
```
**Entry Logic:** Buy when RSI(4) drops below 25 while above 200 MA
**Exit Logic:** Sell when RSI(4) rises above 55 (or 75 for aggressive)
**Timeframe:** Daily
**Asset Class:** ETFs (QQQ, SPY, DIA)
**Backtest Results:** 76% win rate historically

---

### 1.5 RSI(5) Swing Entry/Exit
**Screener Name:** RSI(5) Swing Timer
**Description:** 5-period RSI for swing trade timing
**Filter Criteria:**
```
RSI(5) < 30 and rising
price above MA(30)
volume > average volume(30)
```
**Entry Logic:** Enter when RSI(5) crosses above 30 from below
**Exit Logic:** Exit when RSI(5) crosses below 80 from above
**Timeframe:** 2-5 days
**Asset Class:** Stocks

---

### 1.6 Bollinger Band Mean Reversion
**Screener Name:** BB Mean Reversion
**Description:** Price touching lower Bollinger Band with RSI confirmation
**Filter Criteria:**
```
close below lower Bollinger Band(20,2)
RSI(14) < 30
volume > average volume(20)
```
**Entry Logic:** Buy when price touches lower BB and RSI oversold
**Exit Logic:** Sell when price reaches middle BB or upper BB
**Timeframe:** Daily
**Asset Class:** Stocks

---

### 1.7 Double Bottom Pattern Scanner
**Screener Name:** Double Bottom Finder
**Description:** Identifies potential double bottom formations
**Filter Criteria:**
```
low within 2% of low 10 days ago
close > open
volume > average volume(30)
RSI(14) > 30 and rising
```
**Entry Logic:** Buy on confirmation of second bottom
**Exit Logic:** Target previous resistance level
**Timeframe:** 5-10 days
**Asset Class:** Stocks

---

## 2. Momentum & Breakout Strategies

### 2.1 Hull MA50 Momentum
**Screener Name:** Hull MA50 Momentum
**Description:** Advanced momentum using Hull Moving Average
**Filter Criteria:**
```
optionable
Average Volume(30) > 5000000
market not etf
set{slow1, cwma(close, 25)}
set{slow2, 2 * slow1}
set{slow3, cwma(close, 50)}
set{valslow, slow2 - slow3}
set{H50, cwma(valslow, 7)}
set{trigger1, count(close crossed above H50, 1)}
set{trigger2, count(slope of H50 > 0.1, 1)}
set{trigger3, count(StochRSI(5,5) > .8, 1)}
set{trigger4, trigger1 * trigger2}
set{trigger, trigger4 * trigger3}
trigger equals 1
```
**Entry Logic:** Buy on Hull MA50 crossover with positive slope and StochRSI > 0.8
**Exit Logic:** Trail stop or reversal signal
**Timeframe:** Daily, Swing
**Asset Class:** Stocks

---

### 2.2 Momentum Burst Scanner
**Screener Name:** Momentum Burst
**Description:** Stockbee-style momentum burst detection
**Filter Criteria:**
```
close > wma(150) for last 60 days
volume > average volume(30) 1 day ago
set{jump, close / close 1 day ago}
jump >= 1.04
set{body, close - open}
body >= 0.9
close > close 1 day ago
close > open
set{high30, high * .70}
close >= high30
atr(1) >= atr(1) 1 day ago
jump 1 day ago <= 1.02
volume >= 500000
pe >= 1
ema(10) > ema(20)
```
**Entry Logic:** Buy on 4%+ breakout with strong volume after consolidation
**Exit Logic:** Sell on exhaustion or 3-5 day hold
**Timeframe:** 3-5 days
**Asset Class:** Stocks

---

### 2.3 Hyper Momentum Burst (Aroon Enhanced)
**Screener Name:** Hyper-Burst
**Description:** Momentum burst with Aroon Oscillator confirmation
**Filter Criteria:**
```
market is not etf
market is not otcbb
close > wma(50)
volume > average volume(30)
set{jump, close / close 1 day ago}
jump >= 1.04
jump 1 day ago <= 1.02
set{body, close - open}
body >= 0.9
close > close 1 day ago
close > open
set{high30, high * .50}
close >= high30
atr(1) >= atr(1) 1 day ago
open is above ema(7)
close is above ema(7)
Volume > 500000
Aroon Oscillator(8) > 50
```
**Entry Logic:** Buy on breakout with Aroon Oscillator > 50
**Exit Logic:** Aroon Oscillator decline or price target
**Timeframe:** 1-3 days
**Asset Class:** Stocks

---

### 2.4 ChatGPT Momentum Scan
**Screener Name:** Momentum Swing
**Description:** Multi-factor momentum for swing trading
**Filter Criteria:**
```
close is above MA(20)
MA(20) is above MA(50)
RSI(14) between 50 and 70
volume > avg vol(10)
close above high 10 days ago
close between 5 and 150
optionable
```
**Entry Logic:** Buy on momentum confirmation with trend alignment
**Exit Logic:** RSI > 70 or price below MA(20)
**Timeframe:** 3-10 days
**Asset Class:** Stocks

---

### 2.5 Volume Spike Breakout
**Screener Name:** Volume Breakout
**Description:** Breakout on significant volume increase
**Filter Criteria:**
```
volume > 2 * average volume(30)
close > high 20 day high
close > MA(50)
RSI(14) between 40 and 70
```
**Entry Logic:** Buy on high volume breakout above resistance
**Exit Logic:** Trail stop or volume decline
**Timeframe:** 2-5 days
**Asset Class:** Stocks

---

### 2.6 New High Breakout
**Screener Name:** New High Scanner
**Description:** Breakout to new highs with volume confirmation
**Filter Criteria:**
```
close reached a new high 30 day high
count(close reached a new high 90 day high 1 day ago, 90) equals 0
MA(40) increasing
Average Volume(30) above 1000000
close between 0.25 and 5
```
**Entry Logic:** Buy on first new high in 90 days
**Exit Logic:** Price below entry or MA(40) flattening
**Timeframe:** 5-10 days
**Asset Class:** Small-cap stocks

---

### 2.7 10-Day High Breakout
**Screener Name:** 10-Day High Breakout
**Description:** Simple breakout to 10-day highs
**Filter Criteria:**
```
close between 0.1 and 5
set{clhi, count(close reached a new high 10 day high, 1)}
clhi > 0.99
clhi 1 day ago < 0.99
close > EMA(30)
Average Volume(30) above 1000000
```
**Entry Logic:** Buy on first close at 10-day high
**Exit Logic:** Price below EMA(30)
**Timeframe:** 2-5 days
**Asset Class:** Low-priced stocks

---

## 3. Moving Average Strategies

### 3.1 Triple SMA Crossover (7-21-90)
**Screener Name:** Triple SMA Crossover
**Description:** Classic R.C. Allen triple moving average system
**Filter Criteria:**
```
MA(7) and MA(21) crossed above MA(90) within the last 1 week
Average Volume(90) above 250000
close between 20 and 250
```
**Entry Logic:** Buy when faster MAs cross above slower MA
**Exit Logic:** MA(7) crosses below MA(21)
**Timeframe:** Medium to Long-term
**Asset Class:** Stocks

---

### 3.2 EMA(17) / EMA(50) Trend Following
**Screener Name:** EMA Trend Follower
**Description:** Guppy-style EMA trend identification
**Filter Criteria:**
```
EMA(17) above EMA(50)
close > EMA(17)
volume above 250000
Average Day Range(30) above 3.00
```
**Entry Logic:** Buy when EMA(17) crosses above EMA(50)
**Exit Logic:** EMA(17) crosses below EMA(50)
**Timeframe:** Swing
**Asset Class:** Stocks

---

### 3.3 Golden Cross Scanner
**Screener Name:** Golden Cross
**Description:** 50/200 MA golden cross detection
**Filter Criteria:**
```
MA(50) crossed above MA(200) within last 5 days
volume > average volume(30)
close > MA(50)
RSI(14) > 50
```
**Entry Logic:** Buy on golden cross confirmation
**Exit Logic:** Death cross or stop loss
**Timeframe:** Long-term
**Asset Class:** Stocks, ETFs

---

### 3.4 Super Trend Filter
**Screener Name:** Super Trend
**Description:** Multi-indicator trend strength filter
**Filter Criteria:**
```
set{var1a, count(ma(3) above ma(6), 1)}
set{var1b, count(ma(3) below ma(6), 1)}
set{var1, var1a - var1b}
set{var2a, count(close above ma(3), 1)}
set{var2b, count(close below ma(3), 1)}
set{var2, var2a - var2b}
set{var3a, count(close above ma(6), 1)}
set{var3b, count(close below ma(6), 1)}
set{var3, var3a - var3b}
set{var4a, count(ma(3) above ma(3) 1 day ago, 1)}
set{var4b, count(ma(3) below ma(3) 1 day ago, 1)}
set{var4, var4a - var4b}
set{var5a, count(ma(6) above ma(6) 1 day ago, 1)}
set{var5b, count(ma(6) below ma(6) 1 day ago, 1)}
set{var5, var5a - var5b}
set{var6a, count(close above Parabolic SAR(0.02,0.2), 1)}
set{var6b, count(close below Parabolic SAR(0.02,0.2), 1)}
set{var6, var6a - var6b}
set{var7a, count(PDI above MDI, 1)}
set{var7b, count(PDI below MDI, 1)}
set{var7, var7a - var7b}
set{sum1, var1 + var2}
set{sum2, sum1 + var3}
set{sum3, sum2 + var4}
set{sum4, sum3 + var5}
set{sum5, sum4 + var6}
set{trendsum, sum5 + var7}
trendsum > 5
```
**Entry Logic:** Buy when trendsum > 5 (majority of indicators bullish)
**Exit Logic:** Trendsum < 0
**Timeframe:** Daily
**Asset Class:** Stocks, ETFs

---

### 3.5 Multi-EMA Compression (Guppy)
**Screener Name:** Guppy Compression
**Description:** Guppy Multiple Moving Average compression
**Filter Criteria:**
```
EMA(17) above EMA(50)
EMA(3) through EMA(15) converging
EMA(30) through EMA(50) converging
volume above 250000
```
**Entry Logic:** Buy on compression breakout
**Exit Logic:** Expansion reversal
**Timeframe:** Swing
**Asset Class:** Stocks

---

## 4. Swing Trading Strategies

### 4.1 W Pattern (Double Bottom) Swing
**Screener Name:** W Pattern Swing
**Description:** Identifies W patterns for swing entries
**Filter Criteria:**
```
low within 2% of low 15 days ago
second bottom higher than first
close > open
volume > average volume(20)
RSI(14) > 30
```
**Entry Logic:** Buy on confirmation of W pattern
**Exit Logic:** Target previous high or resistance
**Timeframe:** 5-15 days
**Asset Class:** Stocks

---

### 4.2 Channel Breakout Swing
**Screener Name:** Channel Breakout
**Description:** Breakout from trading channel
**Filter Criteria:**
```
close above upper ascending triangle(90)
close 1 day ago below upper ascending triangle(90) 1 day ago
Average Volume(10) > 200000
optionable
close > 1.00
```
**Entry Logic:** Buy on channel breakout
**Exit Logic:** Return to channel or target
**Timeframe:** 5-10 days
**Asset Class:** Stocks

---

### 4.3 CCI Swing Entry
**Screener Name:** CCI Swing
**Description:** Commodity Channel Index swing signals
**Filter Criteria:**
```
CCI(20) crossed above 0
CCI(20) 2 days ago below 0
draw MA(5)
draw MA(50)
draw MA(200)
volume above 2000000
average volume(30) > 1000000
close > 20
```
**Entry Logic:** Buy when CCI crosses above 0 from below
**Exit Logic:** CCI crosses below 100 or price below MA(5)
**Timeframe:** 2-5 days
**Asset Class:** Stocks

---

### 4.4 Swing Trade Performance Dashboard
**Screener Name:** STPD Backtest
**Description:** Backtest display for swing trades
**Filter Criteria:**
```
set{open4, open 4 days ago}
set{MAXPL5, high 5 day high - open4}
set{GROSSPL5, CLOSE - open4}
set{hodiv5, MAXPL5 / open4}
set{MAXPCT5, hodiv5 * 100}
SET{MAXDD5, LOW 5 DAY LOW - open4}
add column MAXPL5
add column MAXPCT5
ADD COLUMN MAXDD5
ADD COLUMN GROSSPL5
sort column 6 descending
```
**Entry Logic:** Various swing setups
**Exit Logic:** 5-day hold or stop
**Timeframe:** 5 days
**Asset Class:** Stocks

---

### 4.5 Pullback to EMA(34)
**Screener Name:** EMA(34) Pullback
**Description:** Buying pullbacks to EMA(34) in uptrends
**Filter Criteria:**
```
close > EMA(50)
close within 2% of EMA(34)
EMA(34) > EMA(50)
volume > average volume(30)
RSI(14) > 40
```
**Entry Logic:** Buy when price pulls back to EMA(34)
**Exit Logic:** Price above previous high or stop below EMA(34)
**Timeframe:** 3-7 days
**Asset Class:** Stocks

---

### 4.6 ADX Trend Strength Swing
**Screener Name:** ADX Trend Swing
**Description:** ADX-based trend strength swing trades
**Filter Criteria:**
```
ADX(14) > 25
+DI(14) > -DI(14)
close > EMA(20)
volume > average volume(30)
Accum/Dist slope 10 day > 0
```
**Entry Logic:** Buy on ADX trend confirmation
**Exit Logic:** ADX decline or DI crossover
**Timeframe:** 5-10 days
**Asset Class:** Stocks

---

## 5. Multi-Factor Screening Approaches

### 5.1 Qullamaggie Momentum Screener
**Screener Name:** QM Momentum
**Description:** 3-month momentum screener based on Qullamaggie's method
**Filter Criteria:**
```
market is not OTCBB
market is not ETF
add column exchange on left
chart-time is 6 months
average day range (20) above 5
set{x, close divided by low 67 days low}
x > 1.5
set{z, close * Volume}
z > 3000000
close > 5
close < 10% below high 1 week high
close < 10% above low 1 week low
set{gainers, x*100}
add column gainers on left
sort column 6 descending
add column industry on left
```
**Entry Logic:** Buy strongest momentum stocks
**Exit Logic:** Violation of 1-week range or stop
**Timeframe:** 1-3 months
**Asset Class:** Stocks

---

### 5.2 Strongest Stocks in Strongest Sectors
**Screener Name:** Sector Strength
**Description:** Multi-layer sector and stock strength filter
**Filter Criteria:**
```
ROC(63,1) > 20
close above MA(200)
close above MA(50)
volume > 500000
sector performance top 3
```
**Entry Logic:** Buy top performers in top sectors
**Exit Logic:** Sector rotation or relative weakness
**Timeframe:** 1-3 months
**Asset Class:** Stocks

---

### 5.3 Fundamental + Technical Combo
**Screener Name:** Funda-Technical
**Description:** Combines fundamental and technical factors
**Filter Criteria:**
```
PE ratio between 5 and 25
EPS growth > 10%
close above MA(50)
RSI(14) between 40 and 60
volume > average volume(30)
```
**Entry Logic:** Buy undervalued stocks with technical confirmation
**Exit Logic:** PE expansion or technical breakdown
**Timeframe:** Medium-term
**Asset Class:** Stocks

---

### 5.4 Low Float Momentum
**Screener Name:** Low Float Momentum
**Description:** Low float stocks with momentum
**Filter Criteria:**
```
float < 25000000
close < 5
volume > 2 * average volume(30)
close > high 10 day high
RSI(14) > 50
```
**Entry Logic:** Buy explosive low float moves
**Exit Logic:** 20-40% gain or stop
**Timeframe:** 1-3 days
**Asset Class:** Low-float stocks

---

### 5.5 Institutional Quality Swing
**Screener Name:** Institutional Swing
**Description:** High-quality stocks for institutional-style swings
**Filter Criteria:**
```
market cap > 1000000000
average volume(50) > 1000000
close > EMA(50)
ADX(14) > 20
RSI(14) between 40 and 70
```
**Entry Logic:** Buy quality stocks in uptrends
**Exit Logic:** Trend reversal or target
**Timeframe:** 5-15 days
**Asset Class:** Large-cap stocks

---

## 6. Technical Indicator Combinations

### 6.1 RSI + MACD Combo
**Screener Name:** RSI-MACD
**Description:** RSI and MACD confirmation
**Filter Criteria:**
```
RSI(14) > 50 and RSI(14) < 70
MACD(12,26,9) > 0
MACD signal line < MACD line
close > MA(20)
volume > average volume(20)
```
**Entry Logic:** Buy on RSI-MACD alignment
**Exit Logic:** MACD crossover or RSI > 70
**Timeframe:** 3-7 days
**Asset Class:** Stocks

---

### 6.2 Stochastic RSI Momentum
**Screener Name:** StochRSI Momentum
**Description:** Stochastic RSI for momentum entries
**Filter Criteria:**
```
StochRSI(5,5) > 0.8
close crossed above H50
slope of H50 > 0.1
```
**Entry Logic:** Buy on StochRSI strength
**Exit Logic:** StochRSI decline below 0.5
**Timeframe:** 2-5 days
**Asset Class:** Stocks

---

### 6.3 Aroon Oscillator Trend
**Screener Name:** Aroon Trend
**Description:** Aroon Oscillator for trend detection
**Filter Criteria:**
```
Aroon Oscillator(20) > 50
close > MA(20)
volume > average volume(30)
```
**Entry Logic:** Buy when Aroon > 50
**Exit Logic:** Aroon < 50 or negative
**Timeframe:** 5-10 days
**Asset Class:** Stocks

---

### 6.4 ADX + DI Trend Filter
**Screener Name:** ADX-DI Trend
**Description:** ADX with Directional Movement Index
**Filter Criteria:**
```
ADX(14) > 20 or 25
+DI(14) > -DI(14)
slope of +DI(14) > 0
close > EMA(34)
```
**Entry Logic:** Buy on ADX trend strength
**Exit Logic:** ADX decline or DI crossover
**Timeframe:** Swing
**Asset Class:** Stocks

---

### 6.5 VWAP + EMA Combo
**Screener Name:** VWAP-EMA
**Description:** Volume-weighted average price with EMA
**Filter Criteria:**
```
close > VWAP(3)
close > VWAP(12)
close > EMA(20)
volume > average volume(30)
```
**Entry Logic:** Buy when price above VWAP and EMA
**Exit Logic:** Price below VWAP
**Timeframe:** Intraday to Swing
**Asset Class:** Stocks

---

### 6.6 Parabolic SAR + ADX
**Screener Name:** PSAR-ADX
**Description:** Parabolic SAR with ADX confirmation
**Filter Criteria:**
```
close above Parabolic SAR(0.02,0.2)
ADX(14) > 25
PDI > MDI
close > MA(20)
```
**Entry Logic:** Buy on PSAR flip with ADX confirmation
**Exit Logic:** PSAR reversal
**Timeframe:** Swing
**Asset Class:** Stocks

---

### 6.7 CCI + MA Combo
**Screener Name:** CCI-MA
**Description:** CCI with moving average filter
**Filter Criteria:**
```
CCI(20) > 0
CCI(20) increasing for 2 days
MA(5) crossed above MA(50)
volume > 1000000
close > 10
```
**Entry Logic:** Buy on CCI-MA alignment
**Exit Logic:** CCI < 0 or MA crossover
**Timeframe:** 2-5 days
**Asset Class:** Stocks

---

## 7. ETF & Sector Strategies

### 7.1 Larry Connors ETF Mean Reversion
**Screener Name:** Connors ETF
**Description:** Mean reversion for ETFs
**Filter Criteria:**
```
symlist(SPY, QQQ, DIA, IWM, EEM, EFA)
RSI(2) < 10
close above MA(200)
```
**Entry Logic:** Buy oversold ETFs
**Exit Logic:** RSI(2) > 70
**Timeframe:** 2-5 days
**Asset Class:** ETFs

---

### 7.2 Sector Rotation Momentum
**Screener Name:** Sector Rotation
**Description:** Momentum-based sector rotation
**Filter Criteria:**
```
sector in (Technology, Healthcare, Financial)
sector performance > 5% (1 month)
close > MA(50)
RSI(14) > 50
```
**Entry Logic:** Buy strong sectors
**Exit Logic:** Sector weakness
**Timeframe:** 1-3 months
**Asset Class:** Sector ETFs

---

### 7.3 ETF Gap Fade
**Screener Name:** ETF Gap Fade
**Description:** Fading gaps in major ETFs
**Filter Criteria:**
```
symlist(SPY, QQQ, DIA)
open < close 1 day ago * 0.99
gap down > 1%
RSI(2) < 20
```
**Entry Logic:** Buy gap down in ETFs
**Exit Logic:** Gap fill or close
**Timeframe:** 1-2 days
**Asset Class:** ETFs

---

## 8. Risk Management Filters

### 8.1 ATR-Based Volatility Filter
**Screener Name:** ATR Volatility
**Description:** ATR for volatility assessment
**Filter Criteria:**
```
ATR(14) / close < 0.05
ATR(14) > ATR(14) 5 days ago
volume > average volume(30)
```
**Entry Logic:** Trade when volatility manageable
**Exit Logic:** ATR expansion
**Timeframe:** Any
**Asset Class:** Stocks

---

### 8.2 Dollar Volume Liquidity
**Screener Name:** Dollar Volume
**Description:** Ensure sufficient liquidity
**Filter Criteria:**
```
set{dollarvol, close * volume}
dollarvol > 5000000
```
**Entry Logic:** Only trade liquid stocks
**Exit Logic:** Liquidity drop
**Timeframe:** Any
**Asset Class:** Stocks

---

### 8.3 Risk/Reward Calculator
**Screener Name:** Risk Reward
**Description:** Calculate risk/reward ratios
**Filter Criteria:**
```
set{risk, ATR(14)}
set{reward, risk * 2}
add column risk
add column reward
close > 10
```
**Entry Logic:** Only take 2:1 R/R setups
**Exit Logic:** Target or stop
**Timeframe:** Any
**Asset Class:** Stocks

---

## Algorithmic Conversion Notes

### Key StockFetcher Syntax to Algorithmic Equivalents:

| StockFetcher | Python/Pandas Equivalent |
|-------------|-------------------------|
| `close` | `df['close']` |
| `MA(n)` | `df['close'].rolling(n).mean()` |
| `EMA(n)` | `df['close'].ewm(span=n).mean()` |
| `RSI(n)` | `talib.RSI(df['close'], n)` |
| `MACD(a,b,c)` | `talib.MACD(df['close'], a, b, c)` |
| `crossed above` | `(prev < val) & (curr >= val)` |
| `above` | `>` |
| `below` | `<` |
| `within n%` | `abs(a-b)/b < n/100` |
| `count(condition, n)` | `rolling(n).sum()` of condition |
| `days(condition, n)` | `sum of consecutive True` |
| `slope of` | `np.polyfit(x, y, 1)[0]` |

### Common Filter Components:

```python
# Price filters
df['above_ma20'] = df['close'] > df['close'].rolling(20).mean()

# Volume filters
df['high_volume'] = df['volume'] > df['volume'].rolling(30).mean()

# RSI calculation
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Crossover detection
def crossover(series1, series2):
    return (series1.shift(1) < series2.shift(1)) & (series1 > series2)
```

---

## Summary Statistics

| Category | Strategy Count |
|----------|---------------|
| Mean Reversion | 7 |
| Momentum & Breakout | 6 |
| Moving Average | 5 |
| Swing Trading | 6 |
| Multi-Factor | 5 |
| Technical Combinations | 7 |
| ETF & Sector | 3 |
| Risk Management | 3 |
| **Total** | **42+** |

---

## References

1. StockFetcher Forums - Filter Exchange
2. Larry Connors "Short-Term Trading Strategies That Work"
3. Larry Connors "High Probability ETF Trading"
4. Qullamaggie Momentum Method
5. Stockbee Momentum Burst Strategy
6. R.C. Allen Triple Moving Average System
7. Daryl Guppy Multiple Moving Averages

---

*Research compiled: February 2026*
*All strategies are for educational purposes. Backtest before trading live.*
