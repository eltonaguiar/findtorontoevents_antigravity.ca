# EXTREME SUMMARY — Multi-Asset Algorithmic Trading & Betting Suite
## Confirmed From Live Production: https://findtorontoevents.ca/live-monitor/
### Feb 11, 2026 — Claude Opus 4.6 (Verified Against Actual Codebase + Live APIs)

> **PURPOSE**: This document is designed to be pasted into ANY AI for critique. It contains
> the full pseudocode, parameters, confirmed live performance, and architecture of our
> 23-algorithm multi-asset system. No codebase access needed — everything is here.

---

## SYSTEM OVERVIEW

| Metric | Value |
|--------|-------|
| **Asset Classes** | Crypto (32 symbols), Forex (8 pairs), Stocks (12 tickers) |
| **Algorithms** | 23 total (19 technical + 4 fundamental/contrarian) |
| **Active Algorithms** | 16 (7 stock-only algos PAUSED for <12% win rate) |
| **Paper Trading Capital** | $10,000 USD |
| **Position Sizing** | 3-7% per trade (volatility-adjusted, half-Kelly) |
| **Max Positions** | 10 total (5 crypto, 5 stock, 3 forex caps) |
| **Data Sources** | FreeCryptoAPI, TwelveData, Finnhub, Yahoo Finance, SEC EDGAR |
| **Timeframe** | 1-hour candles (primary), daily (regime detection) |
| **Automation** | 39 GitHub Actions workflows, 55 Python scripts |
| **Sports Betting** | Separate system, $1,000 bankroll, quarter-Kelly, 8 sports |

### LIVE STATUS (Feb 11, 2026 — confirmed via API)
- **Current Regime**: Crypto=SIDEWAYS, Forex=USD_WEAK, Stocks=PER-INDIVIDUAL
- **Active Signals**: 14 (all from Challenger Bot — smart money consensus algorithm)
- **Signal Symbols**: MSFT(73), NFLX(69), AMZN(69), BAC(68), NVDA(68), AAPL(66), META(65), GOOGL(65), WMT(64)
- **All Signals**: STRONG_BUY direction, 168h max hold, 4% SL, 4-8% TP

---

## 1. CRYPTO ALGORITHMS (Best Performers)

### Confirmed Top Crypto Performers (by verified win rate):
| Algorithm | Win Rate | Trades | Status |
|-----------|----------|--------|--------|
| Momentum Burst | ~100% | Limited | ACTIVE — crypto-preferred |
| Alpha Predator | ~87% | Medium | ACTIVE — crypto-preferred |
| StochRSI Crossover | ~81% | Medium | ACTIVE — crypto-preferred |
| Ichimoku Cloud | ~80% | Medium | ACTIVE — crypto-preferred |
| RSI(2) Scalp | ~75% | Medium | ACTIVE — crypto-preferred |

**IMPORTANT**: Only these 5 algorithms are allowed to open crypto positions. All others
are blocked from crypto due to <70% win rate in that asset class.

### 1a. Momentum Burst (Best Crypto Algo)
```
ALGORITHM: Momentum Burst
ASSET CLASSES: crypto, forex, stocks
SCIENCE: Raw price momentum detection on 1h candles

INPUT: Last 2 hourly candles (close prices)
PARAMETERS:
  entry_threshold = 2.0%        # minimum hourly move
  tp = 3.0%                     # take-profit
  sl = 1.5%                     # stop-loss
  max_hold = 8 hours

PSEUDOCODE:
  hourly_change_pct = (candle[-1].close - candle[-2].close) / candle[-2].close * 100

  IF abs(hourly_change_pct) > 2.0%:
    direction = BUY if hourly_change_pct > 0 else SHORT
    strength = min(100, abs(hourly_change_pct) * 20)

    # Regime gate
    IF regime == "bear" AND direction == "BUY": SUPPRESS
    IF regime == "bull" AND direction == "SHORT": SUPPRESS

    EMIT signal(direction, strength, tp=3%, sl=1.5%, hold=8h)

CRITIQUE POINTS:
  - Very simple logic — just raw momentum
  - No volume confirmation
  - High win rate may be due to crypto's trending nature
  - 2% hourly threshold may miss smaller but valid moves
  - No multi-timeframe confirmation
```

### 1b. Alpha Predator (4-Factor Alignment)
```
ALGORITHM: Alpha Predator
ASSET CLASSES: crypto, forex, stocks
SCIENCE: 4-factor technical confluence (all must align)
SOURCE: STOCKSUNIFY2 repository adaptation

INPUT: 20+ hourly candles with OHLCV data
PARAMETERS:
  adx_threshold = 25           # strong trend required
  rsi_buy_zone = [40, 70]      # healthy momentum, not overbought
  rsi_sell_zone = [30, 60]     # healthy weakness, not oversold
  volume_multiplier = 1.2      # 20% above average volume required
  tp_crypto = 2.0%
  sl_crypto = 1.0%
  max_hold = 12h

PSEUDOCODE:
  adx = ADX(candles, period=14)
  rsi = RSI(candles, period=14)
  ao = AwesomeOscillator(candles, fast=5, slow=34)   # (SMA5 of HL/2) - (SMA34 of HL/2)
  plus_di = +DI(candles, period=14)
  minus_di = -DI(candles, period=14)
  vol_ratio = candle[-1].volume / SMA(volumes, 20)

  # ALL 4 FACTORS MUST ALIGN:
  factor1 = adx > 25                          # Strong trend exists
  factor2_buy = (rsi >= 40 AND rsi <= 70)     # Healthy RSI zone
  factor3_buy = ao > 0                        # Bullish momentum
  factor4 = vol_ratio > 1.2                   # Institutional footprint

  IF factor1 AND factor2_buy AND factor3_buy AND factor4 AND plus_di > minus_di:
    strength = min(100, max(60, (adx - 25) * 1.5 + 40))
    EMIT BUY(strength, tp=2%, sl=1%, hold=12h)

  # Mirror logic for SHORT with rsi_sell_zone + ao < 0 + minus_di > plus_di

CRITIQUE POINTS:
  - Requiring ALL 4 factors = high precision, low recall
  - May miss good trades by being too selective
  - ADX threshold of 25 is conservative (some use 20)
  - No distinction between trend-start vs trend-exhaustion ADX
```

### 1c. StochRSI Crossover
```
ALGORITHM: StochRSI Crossover
ASSET CLASSES: crypto, forex, stocks
SCIENCE: Stochastic oscillator applied to RSI (momentum of momentum)

INPUT: 30+ hourly candles
PARAMETERS:
  rsi_period = 14
  stoch_period = 14
  k_smooth = 3, d_smooth = 3
  oversold_zone = 30
  overbought_zone = 70
  tp_crypto = 2.0%, sl_crypto = 1.0%, hold = 12h

PSEUDOCODE:
  rsi_series = RSI(candles, period=14)        # Standard Wilder RSI

  # Apply Stochastic to RSI values:
  stoch_rsi = (rsi - lowest_rsi_14) / (highest_rsi_14 - lowest_rsi_14) * 100
  K = SMA(stoch_rsi, 3)                       # Fast line
  D = SMA(K, 3)                               # Slow line (signal)

  # Bullish crossover in oversold zone:
  IF prev_K <= prev_D AND K > D AND K < 30:
    strength = min(100, (30 - K) * 3 + abs(K - D) * 5)
    strength = max(strength, 30)               # Floor at 30
    EMIT BUY(strength)

  # Bearish crossover in overbought zone:
  IF prev_K >= prev_D AND K < D AND K > 70:
    strength = min(100, (K - 70) * 3 + abs(K - D) * 5)
    EMIT SHORT(strength)

CRITIQUE POINTS:
  - StochRSI is notoriously noisy on short timeframes
  - Requires being in extreme zone (K<30 or K>70) — may lag
  - No volume or trend confirmation
  - Smoothing (3,3) adds lag to an already lagging indicator
```

### 1d. Ichimoku Cloud
```
ALGORITHM: Ichimoku Cloud
ASSET CLASSES: crypto, forex, stocks
SCIENCE: Ichimoku Kinko Hyo adapted for hourly (originally daily)

INPUT: 52+ hourly candles
PARAMETERS:
  tenkan = 9, kijun = 26, senkou_b = 52
  adx_confirmation = 20         # Demoted — only confirms, doesn't gate
  tp_crypto = 2.0%, sl_crypto = 1.0%, hold = 16h

PSEUDOCODE:
  tenkan_line = (highest_high_9 + lowest_low_9) / 2
  kijun_line = (highest_high_26 + lowest_low_26) / 2
  senkou_b = (highest_high_52 + lowest_low_52) / 2
  cloud_top = max(tenkan_line, kijun_line)    # Shifted 26 bars forward
  cloud_bottom = senkou_b                      # Shifted 26 bars forward

  bullish_factors = 0
  IF tenkan crosses above kijun: bullish_factors += 1
  IF price > cloud_top: bullish_factors += 1
  IF tenkan > kijun AND separation > 0.1%: bullish_factors += 1

  IF bullish_factors >= 2:
    cloud_dist = abs(price - cloud_top) / price * 100
    strength = min(100, max(30, bullish_factors * 25 + cloud_dist * 10))
    EMIT BUY(strength)

  # ADX confirmation: IF ADX(14) > 20, boost strength by +10
  # (Demoted from hard gate because it filtered out 90% of winning trades)

CRITIQUE POINTS:
  - Ichimoku designed for DAILY charts — hourly adaptation questionable
  - Cloud lagging indicator = late entries
  - 52-period lookback on hourly = only ~2 days of data
  - ADX demoted because it was too restrictive — suggests overfitting concern
```

### 1e. RSI(2) Scalp
```
ALGORITHM: RSI(2) Scalp
ASSET CLASSES: crypto, forex, stocks
SCIENCE: Ultra-short RSI mean reversion (Larry Connors strategy)

INPUT: 25+ hourly candles
PARAMETERS:
  rsi_period = 2                # Extremely fast RSI
  rsi_buy_threshold = 10        # Deep oversold
  rsi_sell_threshold = 90       # Deep overbought
  sma_trend_filter = 20         # Only trade with trend
  tp_crypto = 1.2%, sl_crypto = 0.6%, hold = 6h

PSEUDOCODE:
  rsi2 = RSI(candles, period=2)               # 2-period RSI
  sma20 = SMA(closes, 20)                     # Trend filter

  IF rsi2 < 10 AND price > sma20:             # Oversold IN uptrend
    strength = min(100, (10 - rsi2) * 10)
    strength = max(strength, 30)
    EMIT BUY(strength, tp=1.2%, sl=0.6%, hold=6h)

  IF rsi2 > 90 AND price < sma20:             # Overbought IN downtrend
    strength = min(100, (rsi2 - 90) * 10)
    EMIT SHORT(strength)

CRITIQUE POINTS:
  - RSI(2) is EXTREMELY sensitive — whipsaws likely
  - SMA(20) trend filter helps but is also lagging
  - Very tight TP/SL (1.2%/0.6%) — transaction costs matter
  - 6h max hold = true scalp, but hourly candles may be too slow
```

---

## 2. STOCKS ALGORITHMS

### Confirmed Stock Performance:
| Algorithm | Win Rate | Status | Notes |
|-----------|----------|--------|-------|
| Challenger Bot | Active | ACTIVE | Smart money consensus |
| Trend Sniper | Moderate | ACTIVE | 6-indicator composite |
| Dip Recovery | Moderate | ACTIVE | Mean reversion |
| ETF Masters | 3.37% | PAUSED | Catastrophic failure |
| Sector Rotation | 2.19% | PAUSED | Catastrophic failure |
| Sector Momentum | 0% | PAUSED | Zero wins |
| Blue Chip Growth | 5.56% | PAUSED | Near-zero |
| Technical Momentum | 0% | PAUSED | Zero wins |
| Composite Rating | 0% | PAUSED | Zero wins |
| Cursor Genius | 11.54% | PAUSED | Poor |

### 2a. Trend Sniper (Best Active Stock Algo)
```
ALGORITHM: Trend Sniper
ASSET CLASSES: crypto, forex, stocks
SCIENCE: Brock et al. 1992 — multiple indicator confluence

INPUT: 30+ hourly candles with OHLCV
PARAMETERS:
  composite_buy_threshold = +45
  composite_sell_threshold = -45
  min_confirming_indicators = 4 out of 6

INDICATOR WEIGHTS:
  RSI_momentum:     20%    # RSI(14), score = (RSI - 50) * 2, clamped [-100, +100]
  MACD_histogram:   25%    # Bullish xover=+90, bearish=-90, momentum direction
  EMA_stack:        25%    # Price vs EMA(8) vs EMA(21) alignment
  Bollinger_pctB:   15%    # %B = (price-lower)/(upper-lower), score=(B-0.5)*200
  ATR_trend:        10%    # ATR(14) ratio vs 20-avg, directional
  Volume_confirm:    5%    # Volume ratio vs 20-avg, directional

PSEUDOCODE:
  scores = []

  # 1. RSI Momentum (20%)
  rsi = RSI(closes, 14)
  rsi_score = clamp((rsi - 50) * 2, -100, +100)
  scores.append(rsi_score * 0.20)

  # 2. MACD Histogram (25%)
  macd = EMA(closes, 12) - EMA(closes, 26)
  signal = EMA(macd, 9)
  histogram = macd - signal
  IF histogram crosses from <=0 to >0: macd_score = +90
  ELIF histogram crosses from >=0 to <0: macd_score = -90
  ELIF histogram > 0 AND increasing: macd_score = +80
  ELIF histogram > 0 AND flat: macd_score = +30
  ELIF histogram < 0 AND decreasing: macd_score = -80
  ELSE: macd_score = -10
  scores.append(macd_score * 0.25)

  # 3. EMA Stack (25%)
  ema8 = EMA(closes, 8)
  ema21 = EMA(closes, 21)
  IF price > ema8 > ema21: stack_score = +80    # Perfect bullish stack
  ELIF price > ema21: stack_score = +40          # Partial
  ELIF price < ema8 < ema21: stack_score = -80   # Perfect bearish
  ELIF price < ema21: stack_score = -40
  ELSE: stack_score = 0
  scores.append(stack_score * 0.25)

  # 4. Bollinger %B (15%)
  bb_upper, bb_mid, bb_lower = BollingerBands(closes, 20, 2.0)
  pct_b = (price - bb_lower) / (bb_upper - bb_lower)
  bb_score = clamp((pct_b - 0.5) * 200, -100, +100)
  scores.append(bb_score * 0.15)

  # 5. ATR Trend (10%)
  atr = ATR(candles, 14)
  atr_avg = SMA(atr_history, 20)
  atr_ratio = atr / atr_avg
  price_direction = sign(close[-1] - close[-2])
  atr_score = price_direction * (atr_ratio - 1) * 100
  scores.append(atr_score * 0.10)

  # 6. Volume Confirmation (5%)
  vol_ratio = volume / SMA(volumes, 20)
  vol_score = (vol_ratio - 1) * 100 * price_direction
  scores.append(vol_score * 0.05)

  composite = sum(scores)
  positive_count = count(indicator > 0 for indicator in raw_scores)

  IF composite > +45 AND positive_count >= 4 AND regime != "bear":
    strength = min(100, composite)
    EMIT BUY(strength, tp=1.0%, sl=0.5%, hold=8h)  # stock targets
  IF composite < -45 AND negative_count >= 4:
    EMIT SHORT(strength)

CRITIQUE POINTS:
  - 6 indicators = high complexity, but weights are static (not learned)
  - 20% RSI + 25% MACD + 25% EMA = 70% momentum-focused, potentially redundant
  - Requiring 4/6 alignment is aggressive filtering — many valid trades filtered
  - ATR and Volume at 5-10% have minimal impact on final score
  - No price-action patterns (support/resistance, chart patterns)
```

### 2b. Challenger Bot (20th Algorithm — Smart Money Consensus)
```
ALGORITHM: Challenger Bot
ASSET CLASSES: stocks (primary)
SCIENCE: Multi-source consensus (institutional + insider + analyst + sentiment)

INPUT: Pre-computed consensus scores from 5 data pipelines
PARAMETERS:
  buy_threshold = 70 (out of 100)
  short_threshold = 30
  tp = 8%, sl = 4%, max_hold = 168h (7 days)

5-COMPONENT CONSENSUS SCORING (each normalized to 0-100):

  Component 1 — TECHNICAL (25% allocation):
    Count BUY vs SHORT signals from other 19 algorithms (last 7 days)
    tech_score = (buy_count / total_signals) * 100

  Component 2 — SMART MONEY 13F (20% allocation):
    Query SEC 13F filings for latest quarter
    Count: funds_holding, increased, new, decreased, sold_out
    base = min((funds_holding / 5) * 10, 10)    # Max 10 pts for 5+ funds
    net_flow = ((increased + new - decreased - sold) / max_funds) * 10
    sm_score = (base + net_flow) / 20 * 100

  Component 3 — INSIDER TRADES (20% allocation):
    Query SEC Form 4 filings (last 90 days)
    net_ratio = (buy_value - sell_value) / (buy_value + sell_value)  # Range: -1 to +1
    base = ((net_ratio + 1) / 2) * 15           # Maps to 0-15
    cluster_bonus = +5 if >=3 buyers, +3 if >=2 buyers
    insider_score = (base + cluster_bonus) / 20 * 100

    # MSPR (Finnhub Insider Sentiment): supplementary factor
    IF Form4 exists: mspr_bonus = min(mspr * 10, 5)
    IF Form4 absent: use MSPR as primary source

  Component 4 — ANALYST RATINGS (20% allocation):
    From Finnhub: strongBuy, buy, hold, sell, strongSell counts
    weighted = (SB*2 + B*1 + H*0 - S*1 - SS*2)
    ratio = (weighted + max_possible) / (2 * max_possible)    # 0 to 1
    consensus = ratio * 14
    upside_pts = min((target_mean - price) / price * 20, 6)   # Price target
    analyst_score = (consensus + upside_pts) / 20 * 100

  Component 5 — MOMENTUM + SOCIAL (15% allocation):
    price_momentum = 8 pts if 24h_change > 3%, else 5/3/0
    wsb_sentiment = min(wsb_score / 10, 7) if positive, else 0
    momentum_score = (price_momentum + wsb_sentiment) / 15 * 100

  # REGIME-ADAPTIVE WEIGHTING:
  IF regime == "bull":
    weights = [1.2, 1.2, 0.8, 0.8, 0.8]    # Favor tech + smart money
  ELIF regime == "bear":
    weights = [0.5, 0.8, 1.5, 0.8, 1.5]     # Favor insider + momentum
  ELSE:
    weights = [1.0, 1.0, 1.0, 1.0, 1.0]     # Equal

  overall = (tech*25*w[0] + sm*20*w[1] + insider*20*w[2] +
             analyst*20*w[3] + momentum*15*w[4]) / weighted_total * 100

  IF overall >= 70: EMIT BUY(strength=overall, tp=8%, sl=4%, hold=168h)
  IF overall <= 30: EMIT SHORT(strength=100-overall, tp=8%, sl=4%, hold=168h)

CRITIQUE POINTS:
  - Elegant multi-source approach but weights are MANUALLY SET, not optimized
  - 13F data is QUARTERLY — stale by the time you see it (well-known limitation)
  - SEC Form 4 has 2-day reporting lag
  - Analyst ratings are historically wrong at extremes (contrarian indicator?)
  - WSB sentiment is a meme — may inject noise
  - 7-day hold for stocks with 4% SL is aggressive
  - No backtested Sharpe ratio available for this algorithm
```

---

## 3. FOREX ALGORITHMS

Forex uses the SAME 23 algorithms as crypto/stocks, with asset-specific parameters:

### Forex-Specific Targets (tighter due to lower volatility):
| Algorithm | TP | SL | Hold |
|-----------|-----|-----|------|
| Trend Sniper | 0.4% | 0.2% | 8h |
| Dip Recovery | 0.6% | 0.4% | 16h |
| Volume Spike | 0.5% | 0.3% | 12h |
| VAM | 0.4% | 0.2% | 12h |
| Mean Reversion | 0.15-0.8% | 0.3% | 12h |
| RSI(2) Scalp | 0.3% | 0.15% | 6h |

**Forex Pairs Tracked** (8): EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD, EURGBP

### Current Forex Regime (Live):
```
regime = "usd_weak"
benchmark = USDJPY
price = 152.5057
sma20 = 153.1232
pct_from_sma = -0.4%
volatility = 0.154%
```

**CRITIQUE POINTS FOR FOREX:**
- Same algorithms for crypto (2% hourly moves) and forex (0.1% moves) = questionable
- Forex targets are very tight (0.2-0.6% TP) — slippage + spread can eat profits
- No interest rate differential consideration
- No economic calendar integration (NFP, CPI, FOMC)
- No session-awareness (London/NY/Tokyo overlap patterns)
- 8 pairs only — missing key crosses

---

## 4. PENNY STOCKS

### Actual Implementation: Yahoo Finance Screener Proxy
```
ALGORITHM: Penny Stock Screener (NOT a trading algorithm — a stock finder)
PURPOSE: Filter exchange-listed penny stocks, block OTC/Pink Sheets

PSEUDOCODE:
  # Authentication
  cookies = GET("https://fc.yahoo.com")          # Fetch session cookies
  crumb = GET("https://query2.finance.yahoo.com/v1/test/getcrumb", cookies)

  # Screener Query
  filters = {
    price: BETWEEN $0.01 AND $5.00,              # Default penny range
    volume: > 100,000 daily,                      # Liquidity floor
    region: "ca" or "us" or "both",
    quote_type: "EQUITY"
  }

  # OTC Blocking (critical safety filter)
  BLOCKED_EXCHANGES = [PNK, OTC, OBB, OTCQX, OTCQB, OTCBB, PKC, OQX, OQB]
  results = POST(yahoo_screener, filters, crumb, cookies)
  results = results.filter(exchange NOT IN BLOCKED_EXCHANGES)

  # Recognized exchanges with RRSP eligibility
  RRSP_ELIGIBLE = [TSX, TSX-V, CSE, NEO, NYSE, NASDAQ, NYSE American, NYSE Arca]

  # Output per stock: symbol, price, volume, market_cap, 52w_range, exchange, rrsp_eligible

  # Caching: 30 minutes per unique query

CRITIQUE POINTS:
  - This is NOT an algorithm — it's a screener/filter tool
  - No scoring or ranking beyond sort options
  - No technical analysis on the results
  - No momentum or catalyst detection
  - No volume surge detection
  - Yahoo crumb auth can break without warning
  - No fundamental data (earnings, debt ratios)
  - RRSP eligibility is useful for Canadian users
```

---

## 5. MEME COINS

### Actual Implementation: Part of 32-symbol crypto universe
Meme coins (DOGE, SHIB, PEPE, FLOKI, WIF, BONK) are traded by the SAME 5 crypto-preferred
algorithms listed in Section 1. There is NO separate meme coin algorithm.

```
MEME COINS IN UNIVERSE: DOGE, SHIB, PEPE, FLOKI, WIF, BONK
TREATED AS: Regular crypto assets
ALGORITHMS USED: Same 5 crypto-preferred (Momentum Burst, Alpha Predator,
                  StochRSI, Ichimoku, RSI(2) Scalp)
SPECIAL HANDLING: None — same TP/SL/hold as BTC/ETH

SUPPORTING INFRASTRUCTURE:
  - wsb_scraper.py: Scrapes Reddit for WSB-style sentiment
  - Feeds into Challenger Bot's momentum component
  - NOT a standalone meme coin algorithm

CRITIQUE POINTS:
  - Meme coins have WILDLY different volatility than BTC/ETH
  - Same 2% momentum threshold for DOGE (often 10%+ moves) vs BTC is suboptimal
  - No social media velocity detection (Twitter/X trending)
  - No on-chain holder concentration analysis
  - No pump-and-dump detection
  - No exchange listing event detection
  - Should have separate parameters for meme coins (higher thresholds, tighter stops)
```

---

## 6. SPORTS BETTING

### Architecture: 3-File Pipeline
```
sports_odds.php → sports_picks.php → sports_bets.php
   (Fetch)          (Analyze)          (Paper Trade)
```

### 6a. Value Bet Finder (Core Algorithm)
```
ALGORITHM: Vig-Removed Expected Value Detector
SPORTS: NHL, NBA, NFL, MLB, CFL, MLS, NCAAF, NCAAB
DATA SOURCE: The Odds API v4 (free tier — 500 credits/month)
BOOKS TRACKED: bet365, FanDuel, DraftKings, BetMGM, PointsBet, Caesars

PSEUDOCODE:
  FOR each upcoming event:
    FOR each outcome (home_win, away_win, draw):
      # Collect odds from all bookmakers
      implied_probs = [1.0 / decimal_odds for each book]

      # Vig removal (average method)
      avg_ip = mean(implied_probs)                    # Average across books
      total_overround = sum(avg_ip for all outcomes)   # Should be >1.0 (vig)
      true_prob = avg_ip / total_overround             # Remove vig

      # Expected Value
      best_odds = max(decimal_odds across books)
      EV = (true_prob * best_odds) - 1
      EV_pct = EV * 100

      IF EV_pct > 2.0:    # Minimum 2% edge
        # Kelly sizing
        kelly = EV / (best_odds - 1)
        quarter_kelly = kelly / 4.0
        bet_amount = bankroll * min(quarter_kelly, 0.05)   # Cap at 5%
        bet_amount = max(bet_amount, $5)                    # Floor at $5

        EMIT pick(EV_pct, true_prob, best_odds, bet_amount)

PICK RATING SYSTEM (0-100 score → A+ through D):
  ev_points:      0-50 pts  (10%+ EV = 50 pts, <2.5% = 12 pts)
  book_consensus: 0-20 pts  (6+ books agree = 20 pts)
  market_type:    0-15 pts  (H2H = 15, spreads = 12, totals = 8)
  canadian_book:  0-10 pts  (best odds on CA-legal book = 10 pts)
  time_to_game:   0-5 pts   (>6h = 5 pts, <30min = -5 pts)
  kelly_size:     0-5 pts   (>$40 size = 5 pts)

  total_score = sum(all_points)
  IF score >= 90: grade = A+, action = STRONG_TAKE
  IF score >= 80: grade = A,  action = TAKE
  IF score >= 70: grade = B+, action = TAKE
  IF score >= 60: grade = B,  action = LEAN
  IF score >= 50: grade = C+, action = WAIT
  ELSE:           grade = D,  action = SKIP

BANKROLL MANAGEMENT:
  initial_bankroll = $1,000
  max_active_bets = 20
  max_bet_pct = 5% of current bankroll
  sizing = quarter-Kelly (kelly_fraction / 4)

SETTLEMENT:
  Scores from: The Odds API → ESPN (failover)
  Match by: team name fuzzy matching
  Void: auto-void if pending > 7 days
  Snapshot: daily bankroll tracking

CURRENT PERFORMANCE:
  Total bets placed: ~3 (extremely limited sample)
  ROI: +25.34% (STATISTICALLY MEANINGLESS with 3 bets)
  Bankroll: ~$1,025

CRITIQUE POINTS:
  - ONLY 3 BETS — no statistical significance whatsoever
  - Vig removal by AVERAGING implied probs is the simplest method
    (Better: Shin model, power method, or market-implied true probs)
  - No historical team performance features (ELO, head-to-head)
  - No injury/lineup data integration
  - No weather data for outdoor sports
  - No live/in-play betting
  - Quarter-Kelly is conservative but appropriate for this bankroll
  - 500 credits/month severely limits data freshness
  - No sharp vs recreational book distinction (Pinnacle as benchmark)
  - RandomForest ML model exists but needs >50 data points (has 3)
```

### 6b. Sports ML Model (Future — needs data)
```
ALGORITHM: RandomForest Classifier
STATUS: EXISTS but UNUSABLE (needs 50+ data points, has 3)
FILE: scripts/sports_ml.py

PSEUDOCODE:
  features = [ev_pct, confidence_score, odds, win_prob]
  labels = [won/lost]

  model = RandomForestClassifier(
    n_estimators = 100,
    max_depth = 10,
    random_state = 42
  )
  model.fit(features, labels)

CRITIQUE POINTS:
  - 4 features is extremely thin
  - No team-level features, no historical matchups
  - No temporal features (day of week, time, season phase)
  - No market features (line movement, public vs sharp split)
  - RF is reasonable but gradient boosting likely better here
```

---

## 7. RISK MANAGEMENT & POSITION SIZING

### Position Sizing Hierarchy (4 layers, most sophisticated wins)
```
LAYER 1 — Volatility-Adjusted (PHP fallback):
  recent_vol = std_dev(last 20 price changes)
  IF asset == CRYPTO:
    IF vol > 4%: size = 3%    # High vol = small position
    ELIF vol < 1.5%: size = 7% # Low vol = larger position
    ELSE: size = 5%
  IF asset == STOCK:
    IF vol > 2.5%: size = 3%
    ELIF vol < 0.8%: size = 7%
    ELSE: size = 5%
  IF asset == FOREX:
    IF vol > 1.2%: size = 3%
    ELIF vol < 0.4%: size = 7%
    ELSE: size = 5%

LAYER 2 — Half-Kelly (if >= 20 closed trades for this algo):
  p = win_rate
  q = 1 - p
  b = avg_win_pct / avg_loss_pct           # Win/loss ratio
  full_kelly = p - q / b
  half_kelly = full_kelly / 2

  # Confidence ramp: 0% at 20 trades, 100% at 100 trades
  confidence = min(1.0, (sample_size - 20) / 80)
  blended = half_kelly * confidence + vol_size * (1 - confidence)
  size = clamp(blended, 0.5%, 15%)

LAYER 3 — Python Position Sizer (if lm_position_sizing table exists):
  Uses: EWMA volatility, PCA factor budgeting, regime modifier, alpha decay
  Decaying algos capped at 3%
  Bounds: reject if < 0.5% or > 20%

LAYER 4 — Drawdown Scaling (applied on top):
  scale = 1 / (1 + drawdown_pct / 10)
  # 0% DD → 1.0x, 10% DD → 0.5x, 20% DD → 0.25x (floor)
  final_size = size * scale

ADDITIONAL GUARDS:
  - Max 10 total positions (5 crypto, 5 stock, 3 forex)
  - Max 2 positions per sector group (AAPL+MSFT = tech)
  - 6-hour cooldown after stop-loss on same symbol
  - Trailing stop: activates at 50% of TP, trails at 60% of original SL

FEES MODELED:
  CRYPTO: 0.20% per side (NDAX flat rate)
  STOCKS: max($1.99, shares * $0.0099) per side (Moomoo)
  FOREX: 0 explicit (spread-only)

SLIPPAGE MODELED:
  CRYPTO: 15 bps base + 10 bps per $5K above $5K
  STOCKS: 5 bps base + linear above $10K
  FOREX: 3 bps base + linear above $50K
```

---

## 8. REGIME DETECTION (3 Methods)

### 8a. PHP Real-Time Regime (used during signal scan)
```
FOR each asset class:
  price = current price
  sma20 = 20-candle SMA
  pct_from_sma = (price - sma20) / sma20 * 100
  volatility = recent standard deviation

  CRYPTO regime rules:
    IF pct_from_sma > 2%: regime = "bull"
    ELIF pct_from_sma < -2%: regime = "bear"
    ELSE: regime = "sideways"

  FOREX regime rules:
    Based on USD strength (USDJPY as benchmark)
    IF USD strengthening: "usd_strong"
    IF USD weakening: "usd_weak"

  STOCKS: Per-individual SMA analysis
```

### 8b. Python HMM Regime (daily, more sophisticated)
```
ALGORITHM: 3-State Gaussian Hidden Markov Model
LIBRARY: hmmlearn GaussianHMM
LOOKBACK: 252 trading days

PSEUDOCODE:
  returns = daily_log_returns(prices, 252)
  vol = rolling_std(returns, window=21)
  features = stack(returns, vol)             # 2 features per day

  hmm = GaussianHMM(n_components=3, covariance_type="full")
  hmm.fit(features)

  states = hmm.predict(features)
  current_state = states[-1]

  # Auto-label states by mean return (descending):
  state_means = [mean(returns where state==s) for s in 0,1,2]
  labels = sort_descending(state_means)       # Highest mean = "bull"
  regime = labels[current_state]              # "bull", "sideways", or "bear"

  # Confidence = transition matrix diagonal (persistence probability)
  confidence = transition_matrix[current_state][current_state]

  # Fallback: if <100 days of data → regime = "sideways", confidence = 0.5

CRITIQUE POINTS:
  - HMM assumes Gaussian emissions — fat tails not modeled
  - 3 states may be insufficient (what about "crash" vs "correction"?)
  - 252-day lookback may be too long for crypto regime changes
  - No forward-looking features (VIX term structure, yield curve)
  - Covariance type "full" can overfit with limited data
```

### 8c. Macro Overlay (from Python scripts)
```
FEATURES:
  - VIX level + term structure (contango/backwardation)
  - Yield curve: 10Y-2Y spread (recession indicator)
  - DXY: Dollar index strength

OUTPUT: Composite macro score 0-100 (higher = bullish)
USAGE: Adjusts regime confidence, not a standalone signal
```

---

## 9. SUPPORTING INFRASTRUCTURE

### XGBoost Meta-Labeler
```
PURPOSE: Filter signals — predict which will actually profit
FEATURES: Signal strength, algorithm name (one-hot), asset class, regime,
          RSI, MACD, volume, historical win rate
MODEL: XGBClassifier(n_estimators=200, learning_rate=0.02, max_depth=4)
TRAINING DATA: Historical lm_signals joined with lm_trades outcomes
OUTPUT: Probability 0-1 that signal will be profitable
USAGE: Signals with meta_prob < 0.5 can be suppressed
STATUS: Exists but not confirmed integrated into live trading loop
```

### Correlation Pruner
```
PURPOSE: Remove redundant signals on correlated assets
METHOD:
  1. Get top 50 active signals
  2. Fetch 3-month price history via yfinance
  3. Compute pairwise correlation matrix
  4. IF correlation > 0.7: keep higher-ranked signal, discard lower
OUTPUT: Pruned signal list (reduces portfolio correlation risk)
```

### Ensemble Stacker
```
PURPOSE: Combine multiple ML models for better predictions
BASE MODELS: RandomForest, GradientBoosting, Ridge Regression, Linear Regression
METHOD: Stacking with StandardScaler normalization
STATUS: Exists as utility class, not confirmed in live trading loop
```

### Kelly Optimizer (NEW — Feb 11, 2026)
```
PURPOSE: Recalculate optimal position sizes from actual trade history
FEATURES:
  - Per-algorithm + per-asset-class Kelly fractions
  - Quarter-Kelly for safety (25% of optimal)
  - Regime-adjusted: bull=1.2x, sideways=0.85x, bear=0.5x
  - Rolling 30-day vs all-time comparison
  - Decay warning: flag if 30-day WR drops >20% from all-time
OUTPUT: JSON with recommended position sizes per algo
```

### Win Rate Significance Tester (NEW — Feb 11, 2026)
```
PURPOSE: Determine which win rates are statistically real vs luck
METHOD: Binomial test (scipy) against 50% null hypothesis
FEATURES:
  - P-values with significance levels (***/<0.01, **/<0.05, */<0.10)
  - Wilson score 95% confidence intervals
  - Minimum trades needed for significance estimation
  - Power analysis: n = ((z_alpha + z_beta)^2 * p0*(1-p0)) / (p1-p0)^2
```

---

## 10. DATA PIPELINE & AUTOMATION

### GitHub Actions Workflows (39 total):
```
SCHEDULE:
  - Smart Money Tracker: weekdays 6AM + Sunday 9AM EST
  - Daily Picks Snapshot: weekdays 5PM EST
  - Sports Odds Fetch: 5x daily
  - Regime Detection: runs with smart money tracker
  - SEC 13F Ingest: quarterly
  - SEC Form 4 Ingest: daily on weekdays

MASTER ORCHESTRATOR: scripts/run_all.py (28 steps)
  Steps 1-5:   Smart Money (SEC 13F, Insider, WSB, Consensus, Performance)
  Steps 6-11:  World-Class (Regime HMM, Position Sizer, Meta-Labeler, WorldQuant, Bundles)
  Steps 12-15: Sprint 1 (FinBERT, CUSUM, Bayesian, Congressional)
  Steps 16-19: Sprint 2 (Options Flow, On-Chain, Portfolio, Transfer Entropy)
  Steps 20-27: OPUS46 (Commission, Pauser, Pruner, Ensemble, Features, StopLoss, DynSize)
  Step 28:     FRED Macro Overlay
```

### API Dependencies:
| Source | Free Tier | Used For | Cost |
|--------|-----------|----------|------|
| FreeCryptoAPI | Unlimited | Crypto prices | $0 |
| TwelveData | 800 calls/day | Forex prices | $0 |
| Finnhub | 60 calls/min | Stock prices, analyst, insider | $0 |
| Yahoo Finance | Unofficial | Penny stocks, dividends | $0 |
| SEC EDGAR | Public | 13F filings, Form 4 | $0 |
| The Odds API | 500 credits/mo | Sports odds | $0 |
| Alpha Vantage | 500 calls/day | Backup stock data | $0 |

---

## 11. KNOWN WEAKNESSES & OPEN QUESTIONS FOR CRITIQUE

1. **Statistical Significance**: Most algorithms have limited trade counts. Are the win rates real or just luck? (Binomial test now implemented but not yet run against live data)

2. **Regime Detection Lag**: HMM uses 252-day lookback — way too slow for crypto regime changes. PHP SMA(20) is reactive but crude.

3. **No Backtesting Framework**: Algorithms were deployed live without rigorous historical backtests. Win rates are forward (paper trading) only.

4. **Correlation Between Algorithms**: Multiple momentum-based algos may fire simultaneously on same asset, creating concentrated risk despite position limits.

5. **Meme Coin Parameters**: Using same thresholds for BTC and DOGE is clearly wrong. DOGE has 5-10x the volatility.

6. **Sports Betting Sample Size**: 3 bets total. The +25% ROI is meaningless.

7. **7 Paused Stock Algos**: Why did they fail so badly (0-11% WR)? Root cause analysis not done. Were they ever viable?

8. **Stale Data Sources**: 13F filings are quarterly, Form 4 has 2-day lag, analyst ratings update monthly. By the time signals fire, information is priced in.

9. **No Drawdown Limit**: No circuit breaker to stop trading if portfolio drops 20%+.

10. **No Live Money**: This is all paper trading. Real execution introduces slippage, partial fills, and psychological factors not modeled.

11. **Single Timeframe**: All algorithms use 1-hour candles. No multi-timeframe confirmation (daily trend + hourly entry).

12. **No Fundamental Stock Data**: Stock algorithms are purely technical. No P/E, revenue growth, debt ratios, or sector rotation analysis in the core 19 algos.

13. **Indicator Overlap**: RSI appears in 6+ algorithms. MACD in 3+. Bollinger in 3+. Are these truly independent signals or the same signal with different names?

---

## 12. ARCHITECTURE DIAGRAM

```
                    ┌─────────────────────────────────────┐
                    │        GitHub Actions (39 workflows) │
                    │   Scheduled: hourly/daily/weekly     │
                    └──────────┬──────────────────────────┘
                               │
                    ┌──────────▼──────────────────────────┐
                    │     Python Scripts (55 total)        │
                    │  run_all.py orchestrates 28 steps    │
                    │  HMM regime, Kelly, consensus, etc.  │
                    └──────────┬──────────────────────────┘
                               │
              ┌────────────────▼────────────────────┐
              │         MySQL Database               │
              │  lm_signals, lm_trades, lm_regime   │
              │  gm_sec_13f, gm_insider_trades      │
              │  lm_sports_odds, lm_sports_bets     │
              └────────────────┬────────────────────┘
                               │
         ┌─────────────────────▼─────────────────────────┐
         │           PHP Signal Engine                    │
         │   live_signals.php (23 algorithms)             │
         │   1h candle scan → signal generation           │
         │   Regime gating on 22/23 algos                 │
         └─────────────┬─────────────────────────────────┘
                       │
         ┌─────────────▼─────────────────────────────────┐
         │           PHP Paper Trader                     │
         │   live_trade.php                               │
         │   Position sizing → execution → P&L tracking   │
         │   Trailing stops, cooldowns, sector caps       │
         └─────────────┬─────────────────────────────────┘
                       │
         ┌─────────────▼─────────────────────────────────┐
         │         Frontend Dashboards                    │
         │   goldmine-dashboard.html                      │
         │   algo-performance.html                        │
         │   smart-money.html                             │
         │   Daily picks API → Discord bot                │
         └───────────────────────────────────────────────┘

  SPORTS (separate pipeline):
    The Odds API → sports_odds.php → sports_picks.php → sports_bets.php
                   (cache/budget)    (EV detection)     (paper betting)
```

---

*Generated by Claude Opus 4.6 — Feb 11, 2026*
*Verified against: live_signals.php (3,900+ lines), live_trade.php, paper_trader.php,*
*smart_money.php (1,848 lines), 55 Python scripts, 39 GitHub Actions workflows*
*Live API responses confirmed at time of generation*
