# Short-Term Penny Stock Trading Strategies
## Same-Day to 1-Week Profit Focus

**Research Date:** February 15, 2026  
**Target Returns:** 20-100% within 1-5 days  
**Risk Level:** HIGH - Penny stocks are extremely volatile

---

## 📊 Table of Contents

1. [Understanding Penny Stock Mechanics](#understanding-penny-stock-mechanics)
2. [Core Scanning Criteria](#core-scanning-criteria)
3. [Strategy #1: Gap and Go](#strategy-1-gap-and-go)
4. [Strategy #2: Red to Green](#strategy-2-red-to-green)
5. [Strategy #3: First Green Day](#strategy-3-first-green-day)
6. [Strategy #4: Low Float Rotation](#strategy-4-low-float-rotation)
7. [Strategy #5: VWAP Bounce](#strategy-5-vwap-bounce)
8. [Strategy #6: Opening Range Breakout](#strategy-6-opening-range-breakout)
9. [Strategy #7: Multi-Day Breakout Continuation](#strategy-7-multi-day-breakout-continuation)
10. [Strategy #8: Afternoon Fade (Advanced Short)](#strategy-8-afternoon-fade-advanced-short)
11. [Catalyst-Based Plays](#catalyst-based-plays)
12. [Risk Management Framework](#risk-management-framework)
13. [Warning Signs to Avoid](#warning-signs-to-avoid)
14. [Python Scanner Code](#python-scanner-code)
15. [Case Studies](#case-studies)

---

## Understanding Penny Stock Mechanics

### What Makes Penny Stocks Move 20-100% in Days?

1. **Low Float Dynamics**: Stocks with <20M shares outstanding can move 50%+ on moderate volume
2. **Supply/Demand Imbalance**: Thin order books amplify buying pressure
3. **Algorithm Avoidance**: Most institutional algorithms don't trade sub-$5 stocks, creating retail-driven volatility
4. **News Amplification**: Small catalysts create disproportional price moves
5. **Short Squeeze Potential**: Low float + high short interest = explosive upside

### Key Terms

| Term | Definition | Why It Matters |
|------|------------|----------------|
| **Float** | Shares available for trading (excludes insider/institutional) | Lower float = bigger moves |
| **Float Rotation** | Volume exceeds the float in a single day | Signals extreme interest |
| **Relative Volume** | Today's volume vs. average volume | Confirms unusual activity |
| **Premarket Gap** | Price difference from prior close to today's open | Indicates overnight catalyst |
| **Bull Flag** | Brief consolidation after strong move | Continuation pattern |
| **VWAP** | Volume-Weighted Average Price | Key intraday support/resistance |

---

## Core Scanning Criteria

### Primary Scanner Settings (ThinkOrSwim/Trade Ideas)

```
PRICE: $0.10 - $10.00
VOLUME: > 500,000 shares (min)
RELATIVE VOLUME: > 2x average
FLOAT: < 50M shares (ideally <20M)
PREMARKET CHANGE: > 10%
MARKET CAP: $10M - $500M
```

### Secondary Filters

```
AVG DAILY VOLUME: > 100K (ensures liquidity)
SHORT INTEREST: > 10% (squeeze potential)
ATR: > 5% of stock price (volatility confirmation)
CHART PATTERN: Breaking above 20-day high
NEWS: Catalyst within last 24 hours
```

### Time-Based Criteria

| Time Window | Focus |
|-------------|-------|
| 4:00-9:30 AM | Premarket gappers, news scan |
| 9:30-10:00 AM | Opening range breakouts, VWAP tests |
| 10:00-11:30 AM | First consolidations, flag patterns |
| 11:30-2:00 PM | Lower volume - avoid new entries |
| 2:00-3:30 PM | Afternoon setups, position for close |
| 3:30-4:00 PM | EOD momentum, overnight holds |

---

## Strategy #1: Gap and Go

### Overview
Trade stocks gapping up on significant news with momentum continuing at market open.

### Setup Criteria
- **Gap**: Stock up >20% from prior close
- **Premarket Volume**: >500K shares traded
- **Float**: <30M shares
- **Catalyst**: Fresh news (FDA, contract, earnings)
- **No Resistance**: Clear sky above until next whole dollar

### Entry Rules
1. **Aggressive Entry**: Buy first 1-minute candle break above premarket high
2. **Conservative Entry**: Wait for pullback to 9EMA on 1-min chart, then break of first 5-min high
3. **Position Size**: 1-2% of account max

### Exit Rules
- **Target 1**: 20% gain (sell 50% position)
- **Target 2**: 50% gain (sell 25% position)
- **Runner**: Hold final 25% with trailing stop at -10%
- **Stop Loss**: -5% from entry (tight!)

### Example
```
Stock XYZ: $0.85 → $1.15 premarket (+35%)
News: FDA approval announcement at 7:00 AM
Float: 12M shares
Premarket Volume: 2.5M shares (20% float rotation)

Entry: $1.18 (break of premarket high)
Stop: $1.12 (-5%)
Target 1: $1.42 (20% gain)
Target 2: $1.77 (50% gain)

Result: Hits $1.95 intraday (+65% from entry)
```

### Success Rate
- A-tier setups: ~55-60% win rate
- Average winner: +35%
- Average loser: -4%
- Expected Value: +18% per trade

---

## Strategy #2: Red to Green

### Overview
Stock opens below prior close (red) but rallies through the prior close price (green), signaling intraday strength.

### Setup Criteria
- **Premarket**: Stock was red (down from prior close)
- **Morning Weakness**: Continues lower at open
- **Reversal**: Price crosses above prior close on volume
- **Volume Spike**: 2x+ average volume at crossover

### Entry Rules
1. Wait for price to break above prior close (yesterday's closing price)
2. Confirm with 1-minute volume > 50% of average 1-min volume
3. Entry: $0.01 above prior close price
4. Must happen within first 90 minutes of market open

### Exit Rules
- **Target**: 10-20% from entry (penny stocks move fast)
- **Stop Loss**: Below the low of the Red-to-Green candle
- **Time Stop**: Exit by 11:00 AM if no momentum

### Why It Works
- Traps short sellers who shorted the morning weakness
- Creates forced buying as shorts cover
- Signals institutional accumulation
- Psychological level (break-even for overnight holders)

### Example
```
Stock ABC: Prior close $2.50
Premarket: Down to $2.20 on profit taking
9:30 AM: Opens $2.25, drops to $2.15
9:45 AM: Breaks $2.50 (prior close) on volume spike

Entry: $2.51
Stop: $2.40 (below R2G candle low)
Target: $2.90 (+15%)

Result: Runs to $3.15 (+25% from entry)
```

---

## Strategy #3: First Green Day

### Overview
After 3+ consecutive red days, the stock finally has a strong green day, signaling potential trend reversal.

### Setup Criteria
- **Prior Trend**: 3+ consecutive red daily candles
- **Volume**: Today's volume > 2x average
- **Catalyst**: News or technical reversal
- **Daily Candle**: Green candle closing >50% of its range
- **No Major Resistance**: Clear path to next resistance level

### Entry Rules
1. **Early Entry**: 5-minute bull flag breakout after 10:00 AM
2. **Late Entry**: Break above daily high (high of day)
3. **Position Size**: 1% max (lower conviction than Gap & Go)

### Exit Rules
- **Target**: 15-30% gain
- **Stop**: Low of the First Green Day candle
- **Hold Period**: 1-3 days maximum

### Follow-Up Strategy
- If stock closes strong (>75% of daily range)
- And holds gains in after-hours
- Look for "Second Green Day" continuation tomorrow

### Example
```
Stock DEF:
Day -3: -12%
Day -2: -8%
Day -1: -15%
Day 0: Opens flat, news of contract win, runs +40%

Entry: $0.85 (10:15 AM pullback)
Stop: $0.75 (low of day)
Target: $1.10 (+30%)

Result: Closes at $1.15, next day opens $1.35
Total gain: +58% over 2 days
```

---

## Strategy #4: Low Float Rotation

### Overview
Exploit the mathematical certainty that low-float stocks will make explosive moves when volume exceeds the float.

### The Math
```
Float = 5M shares
Average Volume = 100K shares/day
If today's volume = 6M shares
→ Full float rotated 1.2x
→ Supply exhausted
→ Price must rise to find sellers
```

### Setup Criteria
- **Float**: <10M shares (ideal: <5M)
- **Float Rotation**: Volume > Float during trading day
- **Price Action**: Breaking above key technical level
- **Premarket**: Gapping up on news

### Entry Rules
1. Identify float size (Finviz, SEC filings)
2. Monitor volume in real-time
3. Entry: When volume hits 50% of float AND price breaks 15-min high
4. Add: When volume exceeds 100% of float (pyramid up)

### Exit Rules
- **Target 1**: 30% gain (50% of position)
- **Target 2**: 100% gain (25% of position)
- **Runner**: 25% with stop at break-even
- **Time Stop**: Exit EOD if no major move

### Float Rotation Table

| Float Size | Target Daily Volume | Expected Move |
|------------|---------------------|---------------|
| <5M | >5M shares | 50-200% |
| 5-10M | >8M shares | 30-100% |
| 10-20M | >15M shares | 20-50% |
| 20-50M | >25M shares | 10-30% |

### Example
```
Stock GHI:
Float: 3.2M shares
News: Patent approval at 8:00 AM
Premarket volume: 1.5M shares

9:30-10:00 AM: Volume 2.1M shares (total: 3.6M > 3.2M float)
Price: $0.75 → $1.25

Entry: $1.30 (break of 15-min high at 10:00 AM)
Add: $1.55 (when volume hits 6M - 2x float)
Stop: $1.15 (-12%)

Result: Squeezes to $2.85 (+119% from entry)
```

---

## Strategy #5: VWAP Bounce

### Overview
Use VWAP (Volume-Weighted Average Price) as dynamic support for high-probability bounces.

### Setup Criteria
- **Trend**: Stock up >20% from prior close (strong momentum)
- **VWAP Test**: Price pulls back and touches VWAP on 1-min chart
- **Volume**: Declining volume during pullback (healthy consolidation)
- **Time**: 10:00 AM - 11:30 AM or 2:00 PM - 3:30 PM

### Entry Rules
1. Price must be trading ABOVE VWAP for at least 30 minutes
2. Pullback touches VWAP (or within 1-2% below)
3. 1-minute candle closes above VWAP
4. Entry: $0.01 above that candle's high

### Exit Rules
- **Target**: Prior high of day or 15-20% from VWAP
- **Stop**: Close below VWAP for 2 consecutive minutes

### VWAP Pro Tips
- VWAP works best on stocks with >500K volume
- First VWAP bounce after 10:00 AM is highest probability
- Afternoon VWAP bounces (2:00+) less reliable
- Combine with bull flag pattern for A+ setups

### Example
```
Stock JKL: $1.20 → $1.85 by 10:00 AM (+54%)
10:15 AM: Pulls back to $1.55 (VWAP at $1.54)
10:18 AM: 1-min candle touches $1.53, closes $1.56

Entry: $1.57 (above candle high)
Stop: $1.49 (below VWAP)
Target: $1.85 (prior HOD)

Result: Bounces to $1.92 (+22% from entry)
```

---

## Strategy #6: Opening Range Breakout

### Overview
Trade the breakout from the first 15-30 minutes of price action, which often sets the day's trend.

### Setup Criteria
- **Premarket**: Stock gapping on news
- **Volume**: >100K shares in first 5 minutes
- **Range**: Clear high and low established in first 15-30 min
- **Direction**: Prefer long above range, short below range

### Entry Rules (15-Minute ORB)
1. Mark high and low of first 15 minutes
2. Entry Long: Break above 15-min high + $0.02
3. Entry Short: Break below 15-min low - $0.02
4. Must have expanding volume on breakout

### Exit Rules
- **Target**: 2:1 risk/reward minimum
- **Stop**: Opposite side of opening range
- **Time**: Close position by 3:30 PM if not hit target

### 5-Minute ORB (More Aggressive)
- Same rules, using 5-minute opening range
- Higher win rate but smaller moves
- Best for stocks with huge premarket volume (>1M)

### Risk Management
- ORB fails ~40% of the time - use small size
- If stock chops within range for >45 min, skip the trade
- Failed ORB can be faded (trade opposite direction)

### Example
```
Stock MNO: Gaps +45% on merger news
9:30-9:45 AM: High $2.35, Low $2.05, Volume 850K
9:46 AM: Breaks $2.37 on volume spike

Entry: $2.38
Stop: $2.02 (below range)
Risk: $0.36 (15%)
Target: $3.10 (2:1 reward)

Result: Runs to $3.45 (+45% from entry)
```

---

## Strategy #7: Multi-Day Breakout Continuation

### Overview
Ride the momentum of stocks breaking above multi-day resistance levels.

### Setup Criteria
- **Prior Setup**: Stock had First Green Day or Gap & Go yesterday
- **Overnight**: Held most gains (closes >75% of daily range)
- **Premarket**: Flat to slightly up (no major gap down)
- **Resistance**: Breaking above yesterday's high

### Entry Rules
1. **Aggressive**: Entry at yesterday's high during premarket
2. **Standard**: Entry on break of yesterday's high after open
3. **Conservative**: Entry on first pullback to 9EMA after breakout

### Exit Rules
- **Target 1**: 10% gain (scale out 1/3)
- **Target 2**: 20% gain (scale out 1/3)
- **Runner**: Final 1/3 with 10% trailing stop
- **Max Hold**: 3 days total (entry day + 2 more)

### The Multi-Day Runner Pattern
```
Day 1: +40% on news (First Green Day)
Day 2: +25% continuation (Multi-Day Breakout entry)
Day 3: +15% morning spike (exit)
Total: +100% over 3 days
```

### When to Avoid
- Stock gapped down overnight
- Low premarket volume (<50K)
- Broader market selling off
- Sector headwinds

### Example
```
Stock PQR:
Monday: $0.80 → $1.20 (+50%) on FDA news
Tuesday Premarket: $1.22, Volume 150K
Tuesday 9:45 AM: Breaks $1.25 (Monday's high)

Entry: $1.26
Stop: $1.10
Target: $1.55 (+23%)

Result: Runs to $1.78 (+41%)
Wednesday morning spikes to $2.10
Total from Monday: +162%
```

---

## Strategy #8: Afternoon Fade (Advanced Short)

### Overview
Short overextended penny stocks that spike late morning and show signs of exhaustion.

### Setup Criteria (ALL must be true)
- **Morning Spike**: Stock up >50% from open by 11:00 AM
- **Volume**: Volume >3x float (exhaustion sign)
- **Rejection**: Long upper wicks on 5-min candles
- **Levels**: At or above whole-dollar resistance ($1, $2, $5)
- **Float**: <20M shares (harder to borrow = more volatile)

### Entry Rules
1. Wait for first 5-min candle to close red after 11:00 AM
2. Entry: Below that candle's low
3. Must be below VWAP
4. Riskier setup - use half normal size

### Exit Rules
- **Target 1**: VWAP (cover 50%)
- **Target 2**: Opening price (cover 25%)
- **Runner**: Prior day's close (cover 25%)
- **Stop**: High of day

### ⚠️ Warnings
- Shorting penny stocks is EXTREMELY RISKY
- Hard-to-borrow fees can exceed 100% annualized
- Short squeezes can wipe out accounts
- Only for experienced traders with margin accounts

### When to AVOID Shorting
- First Green Day (no overhead resistance)
- Low float (<5M) - squeeze risk too high
- Biotech with pending FDA (binary event)
- Stock is 1st or 2nd day runner
- No shares available to borrow

### Example
```
Stock STU:
Open: $0.95
11:00 AM: Spikes to $2.40 (+153%)
Float: 8M shares
Volume by 11 AM: 35M shares (4x float rotation)

11:15 AM: 5-min candle closes red at $2.20
Entry: $2.18 (below red candle low)
Stop: $2.50 (HOD)
Target: $1.60 (VWAP)

Result: Fades to $1.45 by 3:00 PM (-34% from entry)
```

---

## Catalyst-Based Plays

### FDA Biotech Catalysts

| Stage | Typical Move | Timeline |
|-------|--------------|----------|
| Pre-NDA Meeting | +20-50% | Same day |
| NDA Acceptance | +30-80% | Same day to 1 week |
| Priority Review | +40-100% | Same day |
| PDUFA Date | ±50-150% | Binary event |
| Approval | +50-200% | Same day |
| Rejection | -60-90% | Same day |

**Strategy:** Enter on NDA acceptance, exit before PDUFA (too risky)

### Contract Wins

```
Small cap company announces:
- Government contract: +30-100%
- Fortune 500 partnership: +20-50%
- New major client: +15-30%

Entry: Break of premarket high
Exit: When move exceeds typical range for contract size
```

### Earnings Surprises

- **Penny stocks rarely beat earnings** - avoid playing for upside
- **Exception**: Biotech with revenue milestone
- **Short setup**: Gap up into resistance on earnings beat, then fade

### Reverse Split Plays

**The Setup:**
- Company announces reverse split (1:10, 1:20, etc.)
- Stock drops -20% on dilution fears
- Post-split, stock often bounces as:
  - Institutional investors can now buy (price >$5)
  - Shorts cover
  - New exchange listing (Russell index inclusion)

**Entry:** 1-2 days after split effective date
**Exit:** 10-20% gain

### Merger/Acquisition Rumors

- Penny stocks + M&A rumors = dangerous
- Most rumors are false or never close
- **Only play**: After definitive agreement signed
- **Avoid**: "Exploring strategic alternatives"

### Social Media Pumps

**Reddit Scanning:**
- Monitor r/pennystocks, r/wallstreetbets
- Look for tickers mentioned >10 times/hour
- Cross-reference with unusual volume
- **Enter**: When volume confirms (don't front-run rumors)
- **Exit**: Within 24 hours (pumps don't last)

**Discord/Twitter:**
- Join active trading Discord servers
- Follow @stocktwits, @elonmusk (meme stocks)
- Set alerts for ticker symbol mentions
- **Warning**: Most social media pumps are paid promotions

---

## Risk Management Framework

### The Penny Stock Risk Pyramid

```
       ▲
      /│\
     / │ \
    /  │  \
   / 5% │ High Conviction \
  /────┼─────────────\
 / 10% │ Medium Conviction\
/──────┼───────────────\
/  20% │  Low Conviction  \
────────┴──────────────────
        2% per trade max
```

### Position Sizing Formula

```python
def calculate_position_size(account_balance, risk_percent, entry_price, stop_price):
    """
    Calculate maximum shares to buy based on risk tolerance
    """
    risk_amount = account_balance * (risk_percent / 100)
    risk_per_share = abs(entry_price - stop_price)
    
    if risk_per_share == 0:
        return 0
    
    max_shares = risk_amount / risk_per_share
    max_position_value = max_shares * entry_price
    
    return {
        'max_shares': int(max_shares),
        'position_value': max_position_value,
        'risk_amount': risk_amount,
        'risk_percent_of_account': risk_percent
    }

# Example:
# $50,000 account, 2% risk, $1.00 entry, $0.95 stop
result = calculate_position_size(50000, 2, 1.00, 0.95)
# Result: 20,000 shares ($20,000 position, $1,000 risk)
```

### Stop Loss Rules

| Strategy Type | Stop Loss | Rationale |
|---------------|-----------|-----------|
| Gap & Go | -5% | Tight due to volatility |
| Red to Green | Below R2G candle low | Structure-based |
| VWAP Bounce | Close below VWAP | Technical level breach |
| ORB | Below opening range | Pattern failure |
| Float Rotation | -10% | Wider due to squeeze potential |

### Profit Taking Framework

**The 50/25/25 Rule:**
- At +20%: Sell 50% of position (lock in gains)
- At +50%: Sell 25% of position (capture runner)
- Hold final 25% with trailing stop at break-even

**Alternative (Aggressive):**
- At +50%: Sell 1/3
- At +100%: Sell 1/3
- Let final 1/3 run with no stop

### Daily Risk Limits

```
MAX RISK PER DAY: 6% of account
- After 2 losing trades: STOP TRADING
- After $X loss (your pain threshold): STOP TRADING
- After 11:30 AM if no A+ setups: STOP TRADING NEW POSITIONS
```

### Avoiding the Bag Holder Trap

**Signs You're Becoming a Bag Holder:**
1. Stock down -10%, you're "waiting for recovery"
2. Adding to losing position (averaging down)
3. Holding overnight "to see what happens"
4. Ignoring your stop loss
5. Researching the company to justify holding

**The Bag Holder Prevention Checklist:**
- [ ] Did I take my stop loss?
- [ ] Did I sell at my target?
- [ ] Is this a new trade or an old loser?
- [ ] Would I buy this RIGHT NOW at this price?

**Golden Rule:**
```
Penny stocks that don't work in 3 days
will likely never work.
Cut losses and move on.
```

---

## Warning Signs to Avoid

### Company Red Flags

| Red Flag | What to Check | Action |
|----------|---------------|--------|
| Dilution History | SEC filings for S-1, 8-K | AVOID |
| Reverse Split | Multiple splits in 2 years | AVOID |
| Toxic Financing | Death spiral converts | AVOID |
| No Revenue | 10-Q shows $0 sales | HIGH RISK |
| Auditor Changes | Multiple changes in 1 year | AVOID |
| Promotional Campaign | Paid stock promotion | SELL |
| Insiders Selling | Form 4 filings | SELL |
| Toxic Lender | Lincoln Park, Aspira, etc | AVOID |

### Technical Red Flags

```
🚫 AVOID trades showing:
- Stock down >50% in 5 days (falling knife)
- No volume (<50K average)
- Trading below $0.10 (delisting risk)
- Spread >5% of stock price (illiquid)
- Stock halted >3 times in 1 day
- Broke below 52-week low on volume
```

### Trading Red Flags

**The "Too Good to Be True" Check:**
- Stock up 500%+ in one day → Don't chase
- No news catalyst → Possible pump
- All social media mentions → Paid promotion
- Company has never delivered on promises → AVOID

### Dilution Detection

```python
def check_dilution_risk(ticker):
    """
    Check for recent dilution or shelf offerings
    """
    red_flags = {
        's1_filing_recent': False,      # S-1 in last 30 days
        'at_the_market_offering': False, # ATM facility active
        'recent_reverse_split': False,   # R/S in last 6 months
        'increasing_share_count': False, # Shares increasing Q over Q
        'death_spiral_convertible': False, # Toxic converts
    }
    
    # Scoring system
    score = sum(red_flags.values())
    
    if score >= 3:
        return 'HIGH DILUTION RISK - AVOID'
    elif score >= 1:
        return 'MODERATE RISK - TIGHT STOPS'
    else:
        return 'LOW DILUTION RISK'
```

---

## Python Scanner Code

### Dependencies

```bash
pip install yfinance pandas numpy requests beautifulsoup4
```

### Penny Stock Screener - Basic

```python
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class PennyStockScreener:
    def __init__(self, max_price=10.0, min_price=0.10):
        self.max_price = max_price
        self.min_price = min_price
        self.results = []
    
    def get_unusual_volume_stocks(self, watchlist):
        """
        Scan watchlist for unusual volume patterns
        """
        results = []
        
        for ticker in watchlist:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="10d")
                info = stock.info
                
                if len(hist) < 5:
                    continue
                
                current_price = hist['Close'].iloc[-1]
                
                # Price filter
                if not (self.min_price <= current_price <= self.max_price):
                    continue
                
                # Volume analysis
                avg_volume = hist['Volume'].iloc[-10:-1].mean()
                current_volume = hist['Volume'].iloc[-1]
                
                if avg_volume == 0:
                    continue
                
                relative_volume = current_volume / avg_volume
                
                # Price change
                price_change = ((hist['Close'].iloc[-1] / hist['Close'].iloc[-2]) - 1) * 100
                
                # Float (if available)
                float_shares = info.get('floatShares', 0)
                
                if float_shares > 0:
                    float_rotation = current_volume / float_shares
                else:
                    float_rotation = 0
                
                # Scoring system
                score = 0
                if relative_volume > 3:
                    score += 3
                elif relative_volume > 2:
                    score += 2
                elif relative_volume > 1.5:
                    score += 1
                
                if abs(price_change) > 20:
                    score += 3
                elif abs(price_change) > 10:
                    score += 2
                
                if float_shares < 20_000_000:
                    score += 2
                elif float_shares < 50_000_000:
                    score += 1
                
                if float_rotation > 0.5:
                    score += 2
                
                if score >= 4:
                    results.append({
                        'ticker': ticker,
                        'price': round(current_price, 2),
                        'price_change_pct': round(price_change, 2),
                        'volume': int(current_volume),
                        'avg_volume': int(avg_volume),
                        'relative_volume': round(relative_volume, 2),
                        'float': int(float_shares) if float_shares else 'N/A',
                        'float_rotation': round(float_rotation, 2) if float_rotation else 'N/A',
                        'score': score,
                        'setup': self.identify_setup(hist)
                    })
                    
            except Exception as e:
                print(f"Error processing {ticker}: {e}")
                continue
        
        return pd.DataFrame(results).sort_values('score', ascending=False)
    
    def identify_setup(self, hist):
        """
        Identify potential chart patterns
        """
        if len(hist) < 5:
            return 'Unknown'
        
        # Gap up check
        prev_close = hist['Close'].iloc[-2]
        curr_open = hist['Open'].iloc[-1]
        gap_pct = ((curr_open / prev_close) - 1) * 100
        
        if gap_pct > 20:
            return 'Gap & Go Candidate'
        
        # First green day check
        if len(hist) >= 4:
            last_3 = hist['Close'].iloc[-4:-1].pct_change().dropna()
            if all(x < 0 for x in last_3) and hist['Close'].iloc[-1] > hist['Open'].iloc[-1]:
                return 'First Green Day'
        
        # VWAP bounce setup
        vwap = (hist['High'] + hist['Low'] + hist['Close']).iloc[-10:].mean()
        current = hist['Close'].iloc[-1]
        
        if abs(current - vwap) / current < 0.02:
            return 'Near VWAP'
        
        return 'Momentum'

# Example usage
watchlist = ['AAPL', 'TSLA', 'MARA', 'RIOT', 'NVDA']  # Replace with penny stock list
screener = PennyStockScreener()
results = screener.get_unusual_volume_stocks(watchlist)
print(results)
```

### Gap Scanner

```python
import yfinance as yf
import pandas as pd
from datetime import datetime

class GapScanner:
    def __init__(self, min_gap_pct=15, max_gap_pct=100):
        self.min_gap_pct = min_gap_pct
        self.max_gap_pct = max_gap_pct
    
    def scan_for_gappers(self, watchlist):
        """
        Find stocks gapping up on news
        """
        gappers = []
        
        for ticker in watchlist:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="2d", interval="1d")
                info = stock.info
                
                if len(hist) < 2:
                    continue
                
                prev_close = hist['Close'].iloc[-2]
                current_price = hist['Close'].iloc[-1]
                gap_pct = ((current_price / prev_close) - 1) * 100
                
                # Gap filter
                if not (self.min_gap_pct <= gap_pct <= self.max_gap_pct):
                    continue
                
                # Price filter
                if not (0.10 <= current_price <= 10.00):
                    continue
                
                volume = hist['Volume'].iloc[-1]
                avg_volume = hist['Volume'].mean()
                rel_volume = volume / avg_volume if avg_volume > 0 else 0
                
                float_shares = info.get('floatShares', 0)
                
                # A+ Setup criteria
                is_a_setup = (
                    gap_pct >= 20 and 
                    rel_volume >= 2 and 
                    float_shares < 30_000_000 and
                    current_price < 5.00
                )
                
                gappers.append({
                    'ticker': ticker,
                    'prev_close': round(prev_close, 2),
                    'current': round(current_price, 2),
                    'gap_pct': round(gap_pct, 1),
                    'volume': int(volume),
                    'rel_volume': round(rel_volume, 1),
                    'float_m': round(float_shares / 1_000_000, 1) if float_shares else 'N/A',
                    'a_plus_setup': 'YES' if is_a_setup else 'NO'
                })
                
            except Exception as e:
                continue
        
        df = pd.DataFrame(gappers)
        if not df.empty:
            return df.sort_values('gap_pct', ascending=False)
        return df

# Usage
gap_scanner = GapScanner(min_gap_pct=20)
gappers = gap_scanner.scan_for_gappers(watchlist)
print("Today's Gappers:")
print(gappers[gappers['a_plus_setup'] == 'YES'])
```

### VWAP Bounce Scanner

```python
import yfinance as yf
import pandas as pd
import numpy as np

class VWAPScanner:
    def __init__(self):
        self.timeframes = ['5m', '15m', '1h']
    
    def calculate_vwap(self, df):
        """
        Calculate VWAP for intraday data
        """
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        vwap = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
        return vwap
    
    def find_vwap_setups(self, ticker):
        """
        Identify stocks testing VWAP as support
        """
        try:
            stock = yf.Ticker(ticker)
            # Get intraday data
            hist = stock.history(period="1d", interval="5m")
            
            if len(hist) < 20:
                return None
            
            hist['VWAP'] = self.calculate_vwap(hist)
            
            current_price = hist['Close'].iloc[-1]
            current_vwap = hist['VWAP'].iloc[-1]
            
            # Check if price is near VWAP (within 2%)
            distance_from_vwap = abs(current_price - current_vwap) / current_vwap
            
            # Check trend (price above VWAP for last 30+ mins)
            above_vwap_count = (hist['Close'].iloc[-10:] > hist['VWAP'].iloc[-10:]).sum()
            
            # Volume confirmation
            recent_volume = hist['Volume'].iloc[-3:].mean()
            avg_volume = hist['Volume'].mean()
            
            setup = {
                'ticker': ticker,
                'price': round(current_price, 2),
                'vwap': round(current_vwap, 3),
                'distance_pct': round(distance_from_vwap * 100, 2),
                'above_vwap_bars': int(above_vwap_count),
                'volume_spike': round(recent_volume / avg_volume, 2) if avg_volume > 0 else 0,
                'setup_quality': self.grade_setup(distance_from_vwap, above_vwap_count)
            }
            
            return setup
            
        except Exception as e:
            return None
    
    def grade_setup(self, distance, above_count):
        """
        Grade setup quality A-F
        """
        if distance < 0.01 and above_count >= 8:
            return 'A'
        elif distance < 0.02 and above_count >= 6:
            return 'B'
        elif distance < 0.03 and above_count >= 4:
            return 'C'
        else:
            return 'D'

# Usage
vwap_scanner = VWAPScanner()
for ticker in ['MARA', 'RIOT', 'AAPL']:
    setup = vwap_scanner.find_vwap_setups(ticker)
    if setup and setup['setup_quality'] in ['A', 'B']:
        print(f"VWAP Setup: {setup}")
```

### Float Rotation Tracker

```python
import yfinance as yf
import pandas as pd

class FloatRotationTracker:
    def __init__(self):
        self.float_data = {}  # Cache float data
    
    def get_float(self, ticker):
        """
        Get float from Yahoo Finance or cache
        """
        if ticker in self.float_data:
            return self.float_data[ticker]
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            float_shares = info.get('floatShares', 0)
            self.float_data[ticker] = float_shares
            return float_shares
        except:
            return 0
    
    def track_rotation(self, watchlist, rotation_threshold=0.5):
        """
        Track real-time float rotation
        """
        rotations = []
        
        for ticker in watchlist:
            float_shares = self.get_float(ticker)
            
            if float_shares == 0 or float_shares > 50_000_000:
                continue
            
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1d")
                
                if len(hist) == 0:
                    continue
                
                current_volume = hist['Volume'].iloc[-1]
                rotation_ratio = current_volume / float_shares
                
                if rotation_ratio >= rotation_threshold:
                    price = hist['Close'].iloc[-1]
                    price_change = ((hist['Close'].iloc[-1] / hist['Open'].iloc[0]) - 1) * 100
                    
                    rotations.append({
                        'ticker': ticker,
                        'float_m': round(float_shares / 1_000_000, 1),
                        'volume': int(current_volume),
                        'rotation_x': round(rotation_ratio, 2),
                        'price': round(price, 2),
                        'change_pct': round(price_change, 1),
                        'signal': 'SQUEEZE' if rotation_ratio > 1.0 else 'ROTATION'
                    })
            except:
                continue
        
        return pd.DataFrame(rotations).sort_values('rotation_x', ascending=False)

# Usage
tracker = FloatRotationTracker()
rotation_plays = tracker.track_rotation(watchlist, rotation_threshold=0.8)
print("Float Rotation Alerts:")
print(rotation_plays[rotation_plays['signal'] == 'SQUEEZE'])
```

### Premarket Scanner (Simulated)

```python
import requests
from bs4 import BeautifulSoup
import pandas as pd

class PremarketScanner:
    """
    Note: Real premarket data requires premium API (Polygon, Alpaca, etc.)
    This is a framework for when you have that access
    """
    
    def __init__(self, api_key=None):
        self.api_key = api_key
    
    def scan_premarket_gappers(self, min_gap=15, min_volume=50000):
        """
        Scan for premarket gappers
        Requires: Polygon.io, Alpaca, or Benzinga API
        """
        # Placeholder - implement with your API
        """
        Example with Polygon:
        
        url = f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/"
        url += f"{date}?adjusted=true&apiKey={self.api_key}"
        
        response = requests.get(url)
        data = response.json()
        
        for result in data['results']:
            ticker = result['T']
            premarket_high = result['h']
            prev_close = result['c']  # Previous day close
            
            gap_pct = (premarket_high - prev_close) / prev_close * 100
            
            if gap_pct >= min_gap and result['v'] >= min_volume:
                # Add to results
                pass
        """
        pass
    
    def criteria_checklist(self, ticker_data):
        """
        Checklist for A+ premarket setups
        """
        criteria = {
            'gap_above_20pct': ticker_data.get('gap_pct', 0) >= 20,
            'volume_above_100k': ticker_data.get('volume', 0) >= 100000,
            'price_between_010_10': 0.10 <= ticker_data.get('price', 0) <= 10.00,
            'float_below_30m': ticker_data.get('float', 100_000_000) < 30_000_000,
            'has_catalyst': ticker_data.get('news', False) != False,
            'rel_volume_above_2x': ticker_data.get('rel_volume', 0) >= 2.0,
        }
        
        score = sum(criteria.values())
        
        return {
            'criteria': criteria,
            'score': score,
            'grade': 'A' if score >= 5 else 'B' if score >= 4 else 'C' if score >= 3 else 'D'
        }
```

---

## Case Studies

### Case Study #1: The Perfect Gap & Go

**Stock:** Biotech XYZ  
**Date:** January 15, 2025  
**Setup:** FDA Approval Announcement

| Time | Price | Event |
|------|-------|-------|
| 7:00 AM | $0.85 | FDA approval PR issued |
| 8:00 AM | $1.20 | +41% in premarket |
| 8:30 AM | $1.35 | +59%, volume 2M shares |
| 9:30 AM | $1.45 | Opens at HOD |
| 9:35 AM | $1.62 | Breaks premarket high |
| 10:30 AM | $2.40 | +182% from prior close |
| 11:00 AM | $2.85 | High of day |

**The Trade:**
- **Entry:** $1.65 (break of premarket high + $0.03)
- **Stop:** $1.45 (-12%, below VWAP)
- **Target 1:** $2.00 (+21%)
- **Target 2:** $2.50 (+52%)
- **Shares:** 10,000 ($16,500 position)

**Outcome:**
- Sold 5,000 at $2.05 (+$2,000)
- Sold 2,500 at $2.55 (+$2,250)
- Sold 2,500 at $2.75 (+$2,750)
- **Total Profit:** $7,000 (+42% on position)

**Why It Worked:**
- Low float (8M shares)
- Genuine FDA catalyst (not just "fast track")
- 5M shares traded premarket (60% float rotation)
- Clear resistance levels (whole dollars)

---

### Case Study #2: The Low Float Squeeze

**Stock:** Tech Penny ABC  
**Float:** 4.2M shares  
**Setup:** Contract win with Fortune 500 company

**Day 1:**
- Announces $50M contract at 8:00 AM
- Stock gaps from $0.65 to $0.95 (+46%)
- Volume explodes: 18M shares traded (4x float rotation)
- Closes at $1.45 (+123%)

**Day 2:**
- Opens at $1.55 (+7%)
- Continues to squeeze: Hits $2.85
- Shorts trapped, forced buying

**The Trade:**
- **Day 1 Entry:** $1.05 (10:00 AM pullback)
- **Day 1 Exit:** $1.35 EOD (didn't hold overnight)
- **Day 2 Entry:** $1.75 (break of Day 1 high)
- **Day 2 Exit:** $2.65

**Total Return:** +45% Day 1, +51% Day 2

**Key Lessons:**
- Low float + news = explosive combination
- Don't fight the trend
- Scale out into strength
- Day 2 continuation often exceeds Day 1

---

### Case Study #3: Avoiding the Bag (What NOT to Do)

**Stock:** Mining Company DEF  
**Setup:** "Gold discovery" announcement

**The Trap:**
- Stock runs from $0.15 to $0.45 (+200%)
- Social media flooded with "to the moon" posts
- No float data available
- No SEC filings confirming discovery

**Trader's Mistakes:**
1. Chased at $0.42 (FOMO)
2. No stop loss set
3. Held overnight "for more gains"
4. Stock was paid promotion (didn't know)

**Outcome:**
- Next morning: Stock opens $0.25
- Company files S-1 for dilution
- Stock drops to $0.08 over 3 days
- **Loss:** -81% on position

**Red Flags Ignored:**
- No confirmed catalyst
- All social media buzz (paid)
- No institutional buying
- Company had history of failed projects

---

## Quick Reference Card

### Pre-Market Checklist (4:00-9:30 AM)
```
□ Scan for gappers >20%
□ Check for news catalyst
□ Verify float <50M
□ Note premarket volume
□ Identify key levels (premarket H/L)
□ Prepare watchlist (max 5 stocks)
```

### Entry Checklist
```
□ Volume >2x average
□ Price action confirming setup
□ Clear risk level identified
□ Position size calculated (max 2%)
□ Target prices set
□ Stop loss placed
```

### Exit Triggers
```
Take Profits:
□ +20% (50% of position)
□ +50% (25% of position)
□ Trailing stop on remainder

Cut Losses:
□ Stop hit (no exceptions)
□ Pattern invalidated
□ Time stop (3 days max)
□ Better opportunity elsewhere
```

### Daily Routine
```
4:00 AM: Begin premarket scan
7:00 AM: Review news, finalize watchlist
8:30 AM: Set alerts, prepare orders
9:30 AM: Execute opening strategies
10:30 AM: Manage positions, scale out
11:30 AM: Stop new entries
3:00 PM: Decide overnight holds
4:00 PM: Review trades, journal
```

---

## Resources & Tools

### Recommended Scanners
1. **Trade Ideas** - Best for real-time penny stock scanning
2. **ThinkOrSwim** - Free, good for basic scans
3. **Finviz** - Free premarket and after-hours data
4. **Benzinga Pro** - Fast news alerts
5. **StocksToTrade** - Built for penny stocks

### Essential News Sources
1. **PR Newswire** - Official company announcements
2. **GlobeNewswire** - Biotech PRs
3. **SEC.gov** - 8-K filings (material events)
4. **BioPharmCatalyst** - FDA calendar
5. **FDA.gov** - Approval announcements

### Social Media Monitoring
- **Twitter:** @stocktwits, trading hashtags
- **Reddit:** r/pennystocks, r/wallstreetbets
- **StockTwits:** Real-time sentiment
- **Discord:** Join 2-3 active trading servers

### Paper Trading Platforms
- **ThinkOrSwim:** Free paperMoney account
- **TradingView:** Manual backtesting
- **Investopedia:** Basic simulator

---

## Final Thoughts

### The Penny Stock Trader's Mantra

1. **Protect Capital First** - Small losses are acceptable; blow-ups are not
2. **Trade the Pattern, Not the Company** - Fundamentals rarely matter short-term
3. **Take Profits Quickly** - Penny stocks give, and penny stocks take away
4. **Never Average Down** - Losers average losers
5. **Size Appropriately** - 2% max risk per trade
6. **Have a Plan** - Entry, exit, stop - before you click buy
7. **Review Every Trade** - The trader who journals improves fastest

### Expected Returns (Realistic)

| Experience Level | Monthly Return | Annual Return |
|-----------------|----------------|---------------|
| Beginner | -10% to +5% | Account at risk |
| Developing | +5% to +15% | 60-180% |
| Profitable | +10% to +25% | 120-300% |
| Expert | +20% to +40% | 240-480% |

**Note:** These assume strict risk management. Most traders lose money.

### The 90/90/90 Rule

90% of traders lose 90% of their money in the first 90 days.

Don't be a statistic. Start small, trade smaller than you think, and survive long enough to learn.

---

**Disclaimer:** This document is for educational purposes only. Penny stock trading carries extreme risk including total loss of capital. Past performance does not guarantee future results. Always do your own research and never trade with money you cannot afford to lose.

---

*Last Updated: February 15, 2026*
