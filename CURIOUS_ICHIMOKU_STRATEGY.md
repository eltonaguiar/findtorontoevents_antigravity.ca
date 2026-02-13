# Curious Ichimoku Cloud Strategy

## Overview

A multi-timeframe trend alignment strategy combining the predictive power of Ichimoku Cloud with precision entry tools on lower timeframes. Designed for traders who want to spend minimal time charting while maximizing setup quality.

**Core Philosophy**: "20-30 minutes on Sunday. Set alerts. Let trades come to you."

---

## Strategy Methodology

### Step 1: Primary Trend Identification (1D Chart) - 25% Weight

Use Ichimoku Cloud on the Daily chart to determine the main trend direction.

**Bullish Signals**:
- Price above the cloud (Kumo)
- Tenkan-sen (Conversion Line) above Kijun-sen (Base Line)
- Future cloud (Senkou Span A > Senkou Span B) is bullish
- Chikou Span (Lagging Span) above price from 26 periods ago

**Bearish Signals**:
- Price below the cloud
- Tenkan-sen below Kijun-sen
- Future cloud is bearish
- Chikou Span below price from 26 periods ago

**Scoring**:
- Price above cloud: +10 pts
- Tenkan > Kijun: +7 pts
- Future cloud bullish: +8 pts

### Step 2: Trend Confirmation (4H/1H Chart) - 20% Weight

Confirm the Daily trend is aligned on lower timeframes using Ichimoku.

**Confirmation Requirements**:
- 4H chart shows same trend direction as Daily
- 1H chart confirms alignment
- Price action respects Ichimoku levels

**Scoring**:
- 4H aligns with Daily: +10 pts
- 1H confirms: +10 pts
- Partial alignment: +3-7 pts

### Step 3: Entry Edge (15m/5m Chart) - 45% Combined Weight

Use multiple confluence factors for precise entry timing.

#### A. Bollinger Bands Position (15%) - 15% Weight
Custom settings: 20 periods, 2 standard deviations (1std and 2std bands)

**Optimal Setup**:
- Price between 1std and 2std upper bands = strong uptrend continuation
- Price between 1std and 2std lower bands = strong downtrend continuation

**Scoring**:
- Between 1-2std (trending): +15 pts
- Between 0-1std (normal): +8 pts
- Outside 2std (overextended): +2 pts

#### B. Stochastics Setup (15%) - 15% Weight
Custom settings: (30, 10, 10) - slower than default for smoother signals

**Bullish Trend**:
- Look for pullback to 20-50 zone then turning up
- K line crossing above D line from below 50

**Bearish Trend**:
- Look for rally to 60-80 zone then turning down
- K line crossing below D line from above 50

**Scoring**:
- Perfect setup (turning from optimal zone): +15 pts
- Good setup (in trend-appropriate zone): +10 pts
- Oversold/overbought extreme: +8 pts
- Neutral: 0-5 pts

#### C. Support/Resistance Confluence (10%) - 10% Weight

Identify key levels where multiple factors align:

- Daily Kijun-sen as major S/R
- Hourly cloud edges (Senkou Span A/B)
- 15m recent swing highs/lows
- Fibonacci retracement levels

**Scoring**:
- At major confluence: +10 pts
- Near single key level: +4-7 pts

#### D. Relative Strength (10%) - 10% Weight

Compare performance vs benchmark:
- Crypto: vs BTC
- Stocks: vs SPY

**Scoring**:
- Strong outperformance (>10%): +10 pts
- Outperforming (>5%): +7 pts
- Slight outperformance (>0%): +5 pts
- Underperforming: 0-3 pts

#### E. Candlestick Patterns (5%) - 5% Weight

Look for reversal/continuation patterns:
- Pinbars
- Engulfing patterns
- Hammers/Shooting stars
- Trendline breaks

**Scoring**:
- Strong pattern at key level: +5 pts
- Moderate pattern: +3-4 pts

---

## Entry Parameters

### For Bullish Setups:
- **Entry**: Current market price or pullback to Kijun
- **Target**: Next major resistance (2std upper Bollinger or previous high)
- **Stop**: Below recent swing low or -1.5% from entry
- **Position Size**: Full if R:R >= 2:1, Half if 1.5:1, Skip if <1.5:1

### For Bearish Setups:
- **Entry**: Current market price or rally to resistance
- **Target**: Next major support (2std lower Bollinger or previous low)
- **Stop**: Above recent swing high or +1.5% from entry
- **Position Size**: Same R:R rules

---

## Scoring Tiers

| Tier | Score | Requirements |
|------|-------|--------------|
| **Strong Buy** | 80+ | Daily 15+, Hourly 12+ |
| **Moderate Buy** | 65+ | Daily 15+ minimum |
| **Lean Buy** | 50+ | Basic alignment |
| **Watch** | 40+ | Early development |
| **Avoid** | <40 | No edge |

---

## Weekly Workflow

### Sunday Analysis (20-30 minutes)

1. **Scan Daily Charts** (15 mins)
   - Open TradingView with Ichimoku Cloud
   - Scan 20-30 symbols
   - Identify those with clear trend (price above/below cloud)

2. **Confirm on 4H/1H** (10 mins)
   - Check trend alignment on lower timeframes
   - Note any divergences

3. **Set Alerts** (5 mins)
   - Set price alerts at key levels:
     - Daily Kijun-sen
     - Cloud edges
     - Recent swing points

### Weekday Execution

1. **Alert Received**
   - Check 15m/5m chart
   - Look for Stochastics setup
   - Confirm Bollinger position

2. **Execute if**:
   - All criteria met
   - R:R >= 1.5:1
   - Position size appropriate

3. **Manage**:
   - Set stops immediately
   - Trail stops using Kijun-sen or ATR
   - Take partial profits at 1:1, 2:1, 3:1

---

## TradingView Setup

### Template 1: Weekly/Daily
- **Indicator**: Ichimoku Cloud (default settings)
- **Background**: Green when bullish, red when bearish
- **Purpose**: Identify primary trend

### Template 2: 4H/1H
- **Indicator**: Ichimoku Cloud
- **Add-on**: Automatic Ichimoku-based support/resistance levels
- **Background**: Green when aligned with daily

### Template 3: 15m/5m
- **Indicator 1**: Bollinger Bands (20, 2) - both 1std and 2std
- **Indicator 2**: Stochastics (30, 10, 10)
- **Indicator 3**: Automatic Ichimoku S/R (red dots)
- **Purpose**: Precision entry timing

---

## Advantages

1. **Time Efficiency**: 20-30 mins/week vs hours daily
2. **Trend Alignment**: Multiple timeframe confirmation reduces false signals
3. **Objective Criteria**: Clear scoring system removes emotion
4. **Risk Management**: Built-in R:R calculation and position sizing
5. **Relaxing**: No screen watching needed - alerts do the work

## Limitations

1. **Whipsaw Risk**: Choppy markets can trigger multiple stops
2. **Lag**: Ichimoku is lagging by design - misses exact tops/bottoms
3. **Requires Discipline**: Must wait for alerts, not chase price
4. **Market Regime**: Works best in trending markets, struggles in ranges

---

## Backtesting Recommendations

To validate this strategy:

1. **Test Period**: Minimum 2 years including bull/bear cycles
2. **Sample Size**: 100+ trades for statistical significance
3. **Metrics to Track**:
   - Win rate by tier
   - Average R:R
   - Max drawdown
   - Expectancy per trade
   - Time in trade

4. **Optimization**:
   - Stochastics period (25-35 range)
   - Bollinger std dev (1.5-2.5 range)
   - Score thresholds (75-85 for Strong Buy)

---

## Implementation

### Files Created
- `findcryptopairs/api/curious_ichimoku.php` - Backend API
- `findcryptopairs/curious-ichimoku.html` - Frontend dashboard

### API Endpoints
- `GET ?action=scan&asset=crypto|stocks&symbol=XXX` - Run scan
- `GET ?action=explain` - Get strategy explanation

### Usage
```bash
# Full scan
curl "https://site.com/findcryptopairs/api/curious_ichimoku.php?action=scan&asset=crypto"

# Single symbol
curl "https://site.com/findcryptopairs/api/curious_ichimoku.php?action=scan&asset=crypto&symbol=BTC/USD"
```

---

## Disclaimer

This strategy is based on technical analysis concepts shared by a community member ("Curious Trader"). It has not been independently verified or backtested. Past performance does not guarantee future results. Always conduct your own due diligence and risk management.

**Not Financial Advice**: This is for educational and research purposes only. Never trade with money you cannot afford to lose.

---

*Strategy Version: 1.0.0*  
*Last Updated: February 2026*
