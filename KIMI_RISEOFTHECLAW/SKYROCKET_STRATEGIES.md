# 🚀 SHORT-TERM "SKYROCKET" STRATEGIES

**Target**: 10-50% gains in minutes to hours  
**Max Hold**: 24 hours  
**Stop Loss**: Tight (2-5%)  
**Take Profit**: Aggressive (10-50%)

---

## STRATEGY 1: Volume Spike Detector

**Concept**: Explosive volume = explosive price

**Entry Conditions**:
- Volume spike 300%+ vs 20-period average
- Price up 5%+ in last 15 minutes
- Market cap > $10M (avoid illiquid)
- Not already up 50%+ today (avoid tops)

**Exit Rules**:
- Take Profit: 15% gain
- Stop Loss: -3%
- Time Stop: 2 hours max
- Trailing: 5% below highs after 10% gain

**Timeframe**: 15m, 1h  
**Best Assets**: Mid-cap altcoins, meme coins  
**Best Time**: Any (crypto 24/7)  
**Difficulty**: Easy

**Pseudocode**:
```
if volume > volume_sma20 * 3.0 and
   price_change_15m > 0.05 and
   market_cap > 10000000 and
   daily_change < 0.50:
    ENTER_LONG()
    
if position_return >= 0.15:
    EXIT("TARGET")
elif position_return <= -0.03:
    EXIT("STOP")
elif time_in_trade > 2_hours:
    EXIT("TIME")
```

---

## STRATEGY 2: News Momentum

**Concept**: Major news = immediate price reaction

**Entry Conditions**:
- Major news announcement (partnership, listing, upgrade)
- Price up 3%+ in 5 minutes after news
- Volume spike confirming interest
- Not a "sell the news" pattern

**Exit Rules**:
- Take Profit: 20% gain
- Stop Loss: -5%
- Time Stop: 4 hours max
- Exit if momentum stalls (no new highs for 30 min)

**Timeframe**: 5m, 15m  
**Best Assets**: Any with active news flow  
**Best Time**: News release time  
**Difficulty**: Medium (requires news feed)

---

## STRATEGY 3: Breakout Scalper

**Concept**: Break above resistance = continuation

**Entry Conditions**:
- Price breaks above 24h high
- Volume > 2x average
- Previous resistance becomes support
- No major overhead resistance

**Exit Rules**:
- Take Profit: 10% gain
- Stop Loss: -2%
- Time Stop: 1 hour max
- Exit if price falls back below breakout level

**Timeframe**: 5m, 15m  
**Best Assets**: All liquid cryptos  
**Best Time**: High volume periods  
**Difficulty**: Easy

---

## STRATEGY 4: Social Sentiment Spike

**Concept**: Viral attention = price pump

**Entry Conditions**:
- Twitter mentions up 500%+ in 1 hour
- Social volume spike detected
- Price starting to react (up 2%+)
- Trending on crypto Twitter

**Exit Rules**:
- Take Profit: 25% gain
- Stop Loss: -4%
- Time Stop: 6 hours max
- Exit if sentiment drops below entry level

**Timeframe**: 15m, 1h  
**Best Assets**: Meme coins, trending alts  
**Best Time**: Any  
**Difficulty**: Hard (requires social data)

---

## STRATEGY 5: Whale Buy Detector

**Concept**: Follow the smart money

**Entry Conditions**:
- Large wallet (>$100k) buy detected
- Multiple whale buys in short window
- Price not yet pumped significantly
- On-chain volume spike

**Exit Rules**:
- Take Profit: 15% gain
- Stop Loss: -3%
- Time Stop: 3 hours max
- Exit if whales start selling

**Timeframe**: 5m, 15m  
**Best Assets**: On-chain trackable coins  
**Best Time**: Any  
**Difficulty**: Hard (requires on-chain data)

---

## STRATEGY 6: New Listing Play

**Concept**: Exchange listings = guaranteed pump

**Entry Conditions**:
- New exchange listing announced
- Within 30 minutes of announcement
- Price up < 20% already (avoid late entry)
- Major exchange (Binance, Coinbase, etc.)

**Exit Rules**:
- Take Profit: 30% gain
- Stop Loss: -5%
- Time Stop: 2 hours max
- Exit before actual listing (sell the news)

**Timeframe**: 1m, 5m  
**Best Assets**: Newly listed coins  
**Best Time**: Announcement time  
**Difficulty**: Medium (requires fast execution)

---

## STRATEGY 7: RSI Momentum Burst

**Concept**: Overbought can become more overbought

**Entry Conditions**:
- RSI(14) crosses above 70
- Volume confirming move
- Previous resistance broken
- Not in overbought zone for >3 days

**Exit Rules**:
- Take Profit: 12% gain
- Stop Loss: -3%
- Time Stop: 2 hours max
- Exit if RSI falls below 70

**Timeframe**: 15m, 1h  
**Best Assets**: Momentum cryptos  
**Best Time**: Any  
**Difficulty**: Easy

---

## STRATEGY 8: MACD Cross Momentum

**Concept**: MACD cross = momentum shift

**Entry Conditions**:
- MACD line crosses above signal
- Histogram expanding (green)
- Price above 20 EMA
- Volume above average

**Exit Rules**:
- Take Profit: 10% gain
- Stop Loss: -2%
- Time Stop: 1 hour max
- Exit if MACD crosses back down

**Timeframe**: 5m, 15m  
**Best Assets**: All liquid cryptos  
**Best Time**: Any  
**Difficulty**: Easy

---

## STRATEGY 9: Funding Rate Arbitrage

**Concept**: Negative funding = longs get paid

**Entry Conditions**:
- Funding rate < -0.1% (negative)
- Price stable or slightly up
- High open interest
- Perpetual futures only

**Exit Rules**:
- Take Profit: 8% gain
- Stop Loss: -2%
- Time Stop: 8 hours (next funding)
- Exit if funding turns positive

**Timeframe**: 1h, 4h  
**Best Assets**: Futures markets  
**Best Time**: Before funding payment  
**Difficulty**: Medium

---

## STRATEGY 10: Liquidation Cascade

**Concept**: Forced liquidations = temporary overshoot

**Entry Conditions**:
- Massive long liquidations detected
- Price drops 10%+ in minutes
- Funding highly negative
- RSI oversold (<30)

**Exit Rules**:
- Take Profit: 15% gain (bounce play)
- Stop Loss: -3%
- Time Stop: 1 hour max
- Exit if new liquidations start

**Timeframe**: 1m, 5m  
**Best Assets**: High leverage markets  
**Best Time**: During flash crashes  
**Difficulty**: Hard (requires liquidation data)

---

## STRATEGY 11: Support Bounce

**Concept**: Strong support = high probability bounce

**Entry Conditions**:
- Price at major support level
- Multiple touches of support
- Bullish reversal candle forming
- Volume drying up (seller exhaustion)

**Exit Rules**:
- Take Profit: 8% gain
- Stop Loss: -2% (below support)
- Time Stop: 4 hours max
- Exit if support breaks

**Timeframe**: 15m, 1h  
**Best Assets**: Range-bound cryptos  
**Best Time**: Any  
**Difficulty**: Easy

---

## STRATEGY 12: Gap Fill (Crypto)

**Concept**: CME gaps often fill

**Entry Conditions**:
- CME Bitcoin gap identified
- Price moving toward gap
- Within 24h of gap formation
- Volume supporting move

**Exit Rules**:
- Take Profit: Gap fill complete
- Stop Loss: -3%
- Time Stop: 24 hours max
- Exit if gap not filling

**Timeframe**: 1h, 4h  
**Best Assets**: BTC, ETH (CME listed)  
**Best Time**: Weekends (CME closed)  
**Difficulty**: Medium

---

## STRATEGY 13: Kill Zone Scalping

**Concept**: High volatility during open

**Entry Conditions**:
- London Open (8-10 UTC) OR NY Open (14:30-16:30 UTC)
- First 15 minutes of session
- Clear directional move starting
- Volume spike

**Exit Rules**:
- Take Profit: 5% gain
- Stop Loss: -1.5%
- Time Stop: 30 minutes max
- Exit before session matures

**Timeframe**: 1m, 5m  
**Best Assets**: Major cryptos  
**Best Time**: Market opens only  
**Difficulty**: Medium

---

## STRATEGY 14: Divergence Reversal

**Concept**: Price/indicator divergence = reversal coming

**Entry Conditions**:
- Price makes lower low
- RSI makes higher low (bullish divergence)
- Volume spike on reversal candle
- Support level nearby

**Exit Rules**:
- Take Profit: 10% gain
- Stop Loss: -2%
- Time Stop: 3 hours max
- Exit if divergence invalidates

**Timeframe**: 15m, 1h  
**Best Assets**: Any  
**Best Time**: Any  
**Difficulty**: Medium

---

## STRATEGY 15: Fibonacci Bounce

**Concept**: Fib levels act as support/resistance

**Entry Conditions**:
- Price at 0.618 or 0.786 Fib retracement
- Previous support/resistance at level
- Bullish candle pattern forming
- Volume confirmation

**Exit Rules**:
- Take Profit: 8% gain or 0.382 Fib
- Stop Loss: -2% (below Fib level)
- Time Stop: 6 hours max
- Exit if level breaks

**Timeframe**: 1h, 4h  
**Best Assets**: Trending cryptos  
**Best Time**: After pullback  
**Difficulty**: Medium

---

## STRATEGY 16: VWAP Bounce

**Concept**: VWAP = institutional average price

**Entry Conditions**:
- Price touches VWAP from above
- Previous VWAP support held
- Volume on approach
- Overall trend bullish

**Exit Rules**:
- Take Profit: 6% gain
- Stop Loss: -1.5%
- Time Stop: 2 hours max
- Exit if VWAP breaks

**Timeframe**: 5m, 15m  
**Best Assets**: Institutional favorites  
**Best Time**: Any  
**Difficulty**: Easy

---

## STRATEGY 17: EMA Cross Momentum

**Concept**: EMA cross = trend continuation

**Entry Conditions**:
- 9 EMA crosses above 21 EMA
- Price above both EMAs
- Volume above average
- Previous resistance broken

**Exit Rules**:
- Take Profit: 10% gain
- Stop Loss: -2%
- Time Stop: 2 hours max
- Exit if EMAs cross back

**Timeframe**: 15m, 1h  
**Best Assets**: Trending cryptos  
**Best Time**: Any  
**Difficulty**: Easy

---

## STRATEGY 18: Pattern Breakout

**Concept**: Chart patterns predict moves

**Entry Conditions**:
- Ascending triangle breakout
- Cup and handle breakout
- Bull flag breakout
- Volume on breakout

**Exit Rules**:
- Take Profit: Pattern target or 15%
- Stop Loss: -3%
- Time Stop: 4 hours max
- Exit if pattern fails

**Timeframe**: 1h, 4h  
**Best Assets**: Any  
**Best Time**: Any  
**Difficulty**: Medium

---

## STRATEGY 19: Order Block Rejection

**Concept**: Smart money levels hold

**Entry Conditions**:
- Price at bullish order block
- Previous support at level
- Rejection wick forming
- Volume on rejection

**Exit Rules**:
- Take Profit: 12% gain
- Stop Loss: -2%
- Time Stop: 3 hours max
- Exit if block breaks

**Timeframe**: 15m, 1h  
**Best Assets**: Any  
**Best Time**: Any  
**Difficulty**: Hard (ICT concepts)

---

## STRATEGY 20: Fair Value Gap Fill

**Concept**: Gaps get filled

**Entry Conditions**:
- Fair value gap identified
- Price returning to fill gap
- Imbalance zone
- Volume supporting move

**Exit Rules**:
- Take Profit: Gap fill complete
- Stop Loss: -2%
- Time Stop: 6 hours max
- Exit if gap not filling

**Timeframe**: 15m, 1h  
**Best Assets**: Any  
**Best Time**: Any  
**Difficulty**: Hard (ICT concepts)

---

## PUMP PROTECTION STRATEGIES

### PP1: Volume Profile Check
- Avoid if volume spike is >10x (likely manipulation)
- Avoid if volume drops off quickly after spike

### PP2: Wallet Analysis
- Check if pump is from single wallet (manipulation)
- Avoid if no organic buying

### PP3: Social Authenticity
- Check if mentions are from real accounts
- Avoid if bot-driven

### PP4: Price History
- Avoid if already pumped 100%+ in last week
- Avoid if no consolidation

### PP5: Exit Velocity
- If price drops 50% of gains in 5 minutes, EXIT immediately
- Don't wait for stop loss

---

## SUMMARY TABLE

| # | Strategy | TP | SL | Time | Difficulty |
|---|----------|-----|-----|------|------------|
| 1 | Volume Spike | 15% | -3% | 2h | Easy |
| 2 | News Momentum | 20% | -5% | 4h | Medium |
| 3 | Breakout | 10% | -2% | 1h | Easy |
| 4 | Social Sentiment | 25% | -4% | 6h | Hard |
| 5 | Whale Buy | 15% | -3% | 3h | Hard |
| 6 | New Listing | 30% | -5% | 2h | Medium |
| 7 | RSI Burst | 12% | -3% | 2h | Easy |
| 8 | MACD Cross | 10% | -2% | 1h | Easy |
| 9 | Funding Arb | 8% | -2% | 8h | Medium |
| 10 | Liquidation | 15% | -3% | 1h | Hard |
| 11 | Support Bounce | 8% | -2% | 4h | Easy |
| 12 | Gap Fill | Varies | -3% | 24h | Medium |
| 13 | Kill Zone | 5% | -1.5% | 30m | Medium |
| 14 | Divergence | 10% | -2% | 3h | Medium |
| 15 | Fibonacci | 8% | -2% | 6h | Medium |
| 16 | VWAP | 6% | -1.5% | 2h | Easy |
| 17 | EMA Cross | 10% | -2% | 2h | Easy |
| 18 | Pattern | 15% | -3% | 4h | Medium |
| 19 | Order Block | 12% | -2% | 3h | Hard |
| 20 | FVG Fill | Varies | -2% | 6h | Hard |

---

**Total: 20 Short-Term Skyrocket Strategies**
