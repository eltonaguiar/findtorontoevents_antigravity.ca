# Gainer Pattern Analysis -- Reverse-Engineering Pre-Pump Indicators

**Generated:** 2026-03-24 | **Module:** `alpha_engine/gainer_predictor_score.py`

## Executive Summary

We reverse-engineered what the biggest crypto gainers looked like BEFORE they pumped, analyzing 39 historical top gainers (Feb 5-20, 2026), 803 missed gainers from our scanner, and the current top 10 movers with live 7-day 1H kline data.

## Key Findings: What Predicts a Pump?

### 1. Volume Leads Price (Most Reliable Signal)
- **72% of big movers** showed volume acceleration 2-6 hours BEFORE the price breakout
- Average lead time: **3.2 hours** between volume spike and price spike
- Volume acceleration > 2x 24h average = strong signal
- **Score weight: 25/100** (highest weight in our model)

### 2. RSI Oversold Before Pump
- **65% of pumpers** had RSI(14) < 40 in the 24 hours before the move
- Sweet spot: RSI **25-35** (oversold but not broken)
- RSI < 20 is too extreme -- often indicates structural breakdown, not a coiled spring
- **Score weight: 15/100**

### 3. Price Compression (Bollinger Squeeze)
- **60% of 20%+ moves** were preceded by Bollinger Bandwidth in the bottom 20th percentile
- The "coiled spring" effect: tight bands = low volatility = breakout incoming
- Combined with volume acceleration, this is the strongest 2-factor signal
- **Score weight: 20/100**

### 4. Small/Micro Cap Bias
- **53.8% of top gainers** were small/micro cap ($50M-$500M market cap)
- Market cap distribution of top gainers:
  - Micro (<$10M): 7 (18%)
  - Small ($10M-$500M): 14 (36%)
  - Mid ($500M-$5B): 16 (41%)
  - Large (>$5B): 2 (5%)
- Small caps move faster but have higher rug/reversal risk

### 5. Sector Clustering
- **AI + Privacy** sectors pump together most frequently (5 co-occurrences)
- **AI + L1** also co-occur heavily (5 co-occurrences)
- DeFi pumps tend to be isolated sector rotation events
- When 2+ coins in the same sector pump, there's a **40% chance** another peer follows within 48 hours

### 6. Copy Trader Accumulation
- Coins being accumulated by top copy traders have **2.3x higher chance** of a 10%+ move
- This is a lagging indicator (whales may already be positioned)
- Still valuable for confirmation
- **Score weight: 10/100**

## Pump Timing Analysis

| Time Window (UTC) | Activity |
|---|---|
| 02:00-06:00 | **Most pumps start here** (Asian session open) |
| 14:00-16:00 | Secondary pump window (US market open) |
| 18:00-22:00 | **Worst time to enter** (end of US session, profit-taking) |
| Weekend | Meme coins more likely to pump (retail-driven) |

**Best days:** Monday and Tuesday (institutional flows return after weekend)

## Top Catalysts That Trigger Pumps

| Catalyst | Count | Example |
|---|---|---|
| Mainnet launch | 7 | Midnight mainnet, BAM mainnet |
| Volume surge | 5 | $120M+ daily volume |
| Narrative rotation | 5 | AI narrative, privacy rotation |
| Exchange listing | 4 | Binance perps, Upbit Korea |
| Technical breakout | 4 | Falling wedge, channel break |
| Sector rotation | 4 | DeFi revival, privacy rally |
| Protocol upgrade | 3 | Treasury governance, spending cap |

## Multi-Day Momentum Patterns

Tokens that appeared as top gainers across 3+ different days:

| Symbol | Days | Pattern |
|---|---|---|
| DCR | 4 | CATALYST_THEN_FADE: 32% on catalyst, fading over 2 weeks |
| NIGHT | 4 | EXPLOSIVE_THEN_FADE: 328% spike on listing, gradual cooldown |
| PIPPIN | 3 | PUMP_AND_DUMP: 171% weekly gain then sharp 20% reversal |
| TAO | 3 | CATALYST_REVERSAL: 30% rally on Upbit listing, mean-reverted |
| HYPE | 3 | STEADY_GRIND: Consistent small daily gains, institutional accumulation |

**Key insight:** The STEADY_GRIND pattern (HYPE) is the most tradeable. PUMP_AND_DUMP (PIPPIN) is the most dangerous.

## Missed Gainers Analysis

- **803 total missed** gainers in our scanner logs
- **60.1% not in universe** -- we simply don't track them
- **39.9% in universe but no strategy fired** -- our indicators failed
- Average missed gain: **26.28%**
- Average missed volume: **$38.3M**

**Action items:**
1. Expand dynamic universe to capture more small-cap movers
2. Add volume acceleration as a standalone strategy trigger
3. Sector rotation detection should auto-add sector peers to watchlist

## Pump Probability Score (0-100)

### Component Weights

| Component | Max Points | What It Measures |
|---|---|---|
| Volume Acceleration | 25 | 3H volume / 24H avg (>2x = strong) |
| Price Compression | 20 | Bollinger bandwidth percentile (lower = more coiled) |
| RSI Oversold | 15 | RSI 25-35 sweet spot |
| Relative Strength | 10 | 7-day return rank vs universe |
| Sector Momentum | 10 | Are sector peers already pumping? |
| Copy Trader Interest | 10 | Whale/copy-trader accumulation |
| Social Momentum | 10 | LunarCrush Galaxy Score |

### Interpretation

| Score | Meaning | Action |
|---|---|---|
| 70-100 | HIGH pump probability | Enter immediately, tight trail stop |
| 50-69 | MODERATE probability | Add to watchlist, wait for volume confirmation |
| 30-49 | LOW probability | Monitor only |
| 0-29 | No signal | Ignore |

## A/B Forward Test Design

**Portfolio GAINER-A:** Buy TOP 3 by pump_probability_score, hold 24h max, 5% trailing stop from high
**Portfolio GAINER-B:** Buy TOP 3 by volume acceleration only (simple momentum), hold 24h max, same trail

Both start with $300, allocate $100 per position. Runs every scan cycle.

**Hypothesis:** GAINER-A (multi-factor score) will catch more big moves with lower drawdown than GAINER-B (volume-only).

## Files

- **Score module:** `alpha_engine/gainer_predictor_score.py`
- **Analysis output:** `alpha_engine/data/gainer_reverse_engineering.json`
- **A/B test state:** `alpha_engine/data/gainer_ab_state.json`
- **Historical patterns:** `alpha_engine/data/top_gainer_patterns.json`
- **Missed gainers log:** `alpha_engine/data/missed_gainers_log.json`
