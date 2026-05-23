# Prediction Market Research: Crypto Trading Signals

**Date:** 2026-03-22
**Status:** Research complete, existing module `polymarket_signals.py` already functional

---

## 1. POLYMARKET (Primary Source)

### Overview
- Largest prediction market by volume ($889M+ single event)
- Runs on Polygon blockchain (CTFX ERC-1155 tokens)
- No API key required for read-only access
- Two complementary APIs: Gamma (metadata) and CLOB (order book/prices)

### API Endpoints (Verified Working)

#### Gamma API (Market Metadata)
Base: `https://gamma-api.polymarket.com`

| Endpoint | Use | Example |
|----------|-----|---------|
| `GET /markets?active=true&closed=false&order=volume&ascending=false&limit=100` | List markets | Returns full market objects with prices |
| `GET /markets?slug={slug}` | Single market by slug | e.g., `slug=will-bitcoin-reach-100k-in-march-2026` |
| `GET /events?active=true&closed=false&order=volume&ascending=false&limit=200` | Events (groups of related markets) | Best for crypto price ladder markets |
| `GET /events?slug={slug}` | Single event by slug | e.g., `slug=what-price-will-bitcoin-hit-in-march-2026` |

Key response fields:
- `outcomePrices`: JSON string `["0.035", "0.965"]` (Yes/No probabilities)
- `bestBid` / `bestAsk`: Current order book spread
- `lastTradePrice`: Most recent fill price
- `volumeNum`: Total USD volume traded
- `clobTokenIds`: Token IDs for CLOB API queries
- `conditionId`: Unique market identifier
- `oneDayPriceChange`: 24h price delta (sometimes null)

#### CLOB API (Order Book & Price History)
Base: `https://clob.polymarket.com`

| Endpoint | Use | Example |
|----------|-----|---------|
| `GET /book?token_id={token_id}` | Full order book (bids + asks) | Uses numeric token ID from `clobTokenIds` |
| `GET /prices-history?market={token_id}&interval=all&fidelity=60` | Price time series | Returns `{history: [{t: unix_ts, p: price}, ...]}` |
| `GET /trades?market={token_id}&limit=10` | Recent trades | **Requires API key** |

**Price History is the GOLD MINE:** Returns hundreds of data points. Example:
```
token_id: 97317111333105248444305246935913701855276691680763278938354874121627341343131
Returns 516 data points at ~1hr intervals
Format: {t: 1772344858, p: 0.0205}
```

### Active Crypto Markets (as of 2026-03-22)

#### BTC Price Markets ($68.6M volume, $5.9M liquidity)
Event slug: `what-price-will-bitcoin-hit-in-march-2026`

| Market | Yes Price | Implied Probability | Slug |
|--------|-----------|-------------------|------|
| BTC reach $150K in March | 0.0015 | 0.15% | will-bitcoin-reach-150k-in-march-2026 |
| BTC reach $100K in March | 0.0035 | 0.35% | will-bitcoin-reach-100k-in-march-2026 |
| BTC reach $85K in March | 0.0195 | 1.95% | will-bitcoin-reach-85k-in-march-2026 |
| BTC reach $80K in March | 0.085 | 8.5% | will-bitcoin-reach-80k-in-march-2026 |
| BTC reach $75K in March | 1.00 | 100% (resolved) | will-bitcoin-reach-75k-in-march-2026 |
| **BTC dip to $65K in March** | **0.61** | **61%** | will-bitcoin-dip-to-65k-in-march-2026 |
| BTC dip to $60K in March | 0.205 | 20.5% | will-bitcoin-dip-to-60k-in-march-2026 |
| BTC dip to $55K in March | 0.0865 | 8.65% | will-bitcoin-dip-to-55k-in-march-2026 |
| BTC dip to $50K in March | 0.0225 | 2.25% | will-bitcoin-dip-to-50k-in-march-2026 |

**KEY SIGNAL:** BTC is currently above $75K (resolved YES), market implies 61% chance of dipping to $65K and only 8.5% chance of reaching $80K this month. Strongly bearish near-term.

#### BTC 2026 Annual Targets ($26.2M volume)
Event slug: `what-price-will-bitcoin-hit-before-2027`

| Target | Yes Price | Implied Probability |
|--------|-----------|-------------------|
| $250K by EOY 2026 | 0.0435 | 4.35% |
| $200K by EOY 2026 | 0.0515 | 5.15% |
| $150K by EOY 2026 | 0.105 | 10.5% |
| $120K by EOY 2026 | 0.195 | 19.5% |
| **$100K by EOY 2026** | **0.375** | **37.5%** |
| **$90K by EOY 2026** | **0.505** | **50.5% (coin flip)** |
| $80K by EOY 2026 | 0.735 | 73.5% |
| Dip to $55K by EOY 2026 | 0.73 | 73% |
| Dip to $45K by EOY 2026 | 0.495 | 49.5% |
| Dip to $25K by EOY 2026 | 0.145 | 14.5% |

**KEY SIGNAL:** Market-implied BTC range for 2026 is roughly $45K-$90K with median around $80K. Only 37.5% chance of reclaiming $100K.

#### ETH Price Markets ($15.8M volume)
Event slug: `what-price-will-ethereum-hit-in-march-2026`

| Market | Yes Price |
|--------|-----------|
| ETH reach $2,400 | 0.165 (16.5%) |
| ETH reach $2,200 | 1.00 (resolved) |
| ETH dip to $2,000 | 1.00 (resolved) |
| ETH dip to $1,800 | 0.205 (20.5%) |
| ETH dip to $1,600 | 0.076 (7.6%) |

**KEY SIGNAL:** ETH currently between $2,000-$2,200. Only 16.5% chance of reaching $2,400.

#### SOL Price Markets ($3.5M volume)
Event slug: `what-price-will-solana-hit-in-march-2026`

#### Other Crypto Events
| Event | Volume | Slug |
|-------|--------|------|
| MicroStrategy sells BTC by ___? | $21.5M | microstrategy-sell-any-bitcoin-in-2025 |
| MegaETH FDV at launch | $13.5M | megaeth-market-cap-fdv-one-day-after-launch |
| MetaMask token launch | $8.1M | will-metamask-launch-a-token-in-2025 |
| Base token launch | $5.9M | will-base-launch-a-token-in-2025-341 |
| BTC all-time high by ___? | $5.4M | bitcoin-all-time-high-by |
| Satoshi moves BTC in 2026 | $1.8M | will-satoshi-move-any-bitcoin-in-2026 |
| Pump.fun airdrop | $2.7M | pumpfun-airdop-by |
| Crude Oil price (macro) | $49.8M | will-crude-oil-cl-hit-by-end-of-march |

### Polymarket Leaderboard / Top Traders
- **No public API endpoint for leaderboard** (as of 2026-03-22)
- Leaderboard visible at: https://polymarket.com/leaderboard
- Positions are on-chain (Polygon) and queryable via:
  - Dune Analytics: `SELECT * FROM polymarket_polygon.ctf_positions ORDER BY value DESC`
  - Direct Polygon RPC: Query ERC-1155 balances on CTF contract
  - Known whales tracked by Arkham Intelligence
- **Future integration:** Scrape leaderboard or use Dune API

### How to Use as Trading Signal

**Strategy 1: Implied Probability Curve (PRIMARY)**
- Fetch all markets in a BTC price event (e.g., "What price will BTC hit in March?")
- The prices form an implied probability distribution
- Compare to current spot price for directional bias
- Example: If "BTC reach $85K" is at 2% but BTC is at $83K, market is extremely bearish
- **Edge:** Prediction markets aggregate information from thousands of traders with money at stake

**Strategy 2: Probability Momentum (LEADING INDICATOR)**
- Poll price history every 30min via CLOB API
- Track rate of change in probabilities
- Sharp moves (>5% in <4 hours) often precede spot price moves
- **This is the unique edge** -- nobody else is tracking prediction market momentum

**Strategy 3: Dip Probability Skew**
- Compare "BTC reach $X" vs "BTC dip to $Y" probabilities
- When dip probabilities rise sharply, it's a leading indicator of fear
- When reach probabilities rise, it's a leading indicator of greed

---

## 2. KALSHI (Secondary Source - Regulated US Exchange)

### Overview
- CFTC-regulated US prediction market (legal for US traders)
- Extensive crypto series: BTC, ETH, SOL, DOGE, XRP, AVAX, DOT, LINK, LTC, BCH, XLM, SHIB
- Multiple timeframes: 15-minute, hourly, daily, weekly, monthly, annual
- No API key required for read-only market data

### API Endpoints (Verified Working)
Base: `https://api.elections.kalshi.com/trade-api/v2`

| Endpoint | Use |
|----------|-----|
| `GET /series` | All series (~9000+, ~200+ crypto) |
| `GET /events?status=open&series_ticker=KXBTC` | Active BTC events |
| `GET /events?limit=100&status=open&category=Crypto` | All open crypto events |
| `GET /markets?event_ticker={ticker}` | Markets within an event (price ranges/strikes) |

### Key Crypto Series on Kalshi

#### Price Range Markets (binary options style)
| Series | Asset | Frequency | Description |
|--------|-------|-----------|-------------|
| KXBTC | BTC | Hourly | Bitcoin price range at specific time |
| KXBTCD / BTCD | BTC | Daily/Hourly | Bitcoin above/below specific price |
| KXBTC15M | BTC | 15-min | Ultra-short-term BTC direction |
| KXBTCMAXW | BTC | Weekly | BTC weekly high |
| KXBTCMAXM / BTCMAXM | BTC | Monthly | BTC monthly high |
| KXBTCMAXY / BTCMAXY | BTC | Annual | BTC yearly high |
| KXBTCMINY / BTCMINY | BTC | Annual | BTC yearly low |
| KXETH | ETH | Hourly | Ethereum price range |
| KXETHD / ETHD | ETH | Daily/Hourly | ETH above/below |
| KXETH15M | ETH | 15-min | Ultra-short-term ETH |
| KXSOL / KXSOLD | SOL | Hourly/Daily | Solana price |
| KXSOL15M | SOL | 15-min | Ultra-short-term SOL |
| KXDOGE / KXDOGED | DOGE | Hourly/Daily | Dogecoin price |
| KXDOGE15M | DOGE | 15-min | Ultra-short-term DOGE |
| KXXRP / KXXRPD | XRP | Hourly/Daily | XRP price |
| KXXRP15M | XRP | 15-min | Ultra-short-term XRP |
| KXAVAX / KXAVAXD | AVAX | Daily | Avalanche price |
| KXLINK / KXLINKD | LINK | Daily | Chainlink price |
| KXDOT / KXDOTD | DOT | Daily | Polkadot price |
| KXLTC / KXLTCD | LTC | Daily | Litecoin price |
| KXBCH / KXBCHD | BCH | Daily | Bitcoin Cash price |
| KXXLM / KXXLMD | XLM | Daily | Stellar price |
| KXSHIBA / KXSHIBAD | SHIB | Daily | Shiba Inu price |
| KXRIPPLE / KXRIPPLED | XRP | Hourly/Daily | Ripple price |
| KXBNB15M | BNB | 15-min | BNB price |
| KXADA15M | ADA | 15-min | Cardano price |
| KXHYPE15M | HYPE | 15-min | Hyperliquid price |

#### Event/Narrative Markets
| Series | Description |
|--------|-------------|
| KXBTCATH / BTCATH | Will BTC hit all-time high? |
| KXSOLANAATH | Solana all-time high |
| KXXRPATH | XRP all-time high |
| KXBTCRESERVE | US Bitcoin Strategic Reserve |
| KXBTCRESERVESTATES | US State Bitcoin Reserves |
| KXCOUNTRYBTC | Country buying BTC |
| KXMSTRSELL | MicroStrategy sells BTC |
| KXCRYPTORESERVE | US Crypto Reserve assets |
| KXSTABLECOIN / KXSTABLECOINGENIUS | Stablecoin legislation |
| KXSOLFLIPETH | SOL flips ETH market cap |
| KXBTCETHRETURN | BTC vs ETH relative performance |
| KXDOGEMAX1 | DOGE reaches $1 |
| KXELSALVADORBTC | El Salvador BTC policy |
| KXMAG7BTC | Mag-7 company buys BTC |
| KXSP500BTCPURCHASE | S&P 500 company buys BTC |
| KXHARDFORKBTC | BTC hard fork |
| KXSATOSHIBTCYEAR | Satoshi moves BTC |
| KXTOKENLAUNCH | Who launches a token this year? |
| KXAIRDROPMONAD / KXAIRDROPHYPE / KXAIRDROPPUMPFUN | Airdrop markets |

### How Kalshi Differs from Polymarket for Signals
1. **15-minute markets** -- ultra-short-term directional bets, useful as intraday sentiment
2. **Regulated** -- institutional money more likely to participate
3. **Price range format** -- markets resolve to specific $250 ranges, giving precise implied distribution
4. **Lower volume on crypto** than Polymarket (more liquidity on politics/weather)
5. **No API key needed** for market data reads

---

## 3. OTHER PREDICTION MARKETS

### Drift Protocol (Solana)
- On-chain prediction markets on Solana
- API exploration: Historical trade data in S3 buckets (not well-documented)
- Less liquid than Polymarket for crypto price predictions
- **Status:** Deprioritized -- Drift is primarily a perps DEX, prediction markets are secondary

### Augur (Ethereum)
- Original crypto prediction market (launched 2018)
- Low liquidity, mostly historical
- **Status:** Not worth integrating -- low volume

### Azuro (Multi-chain)
- Primarily sports betting
- Some crypto markets but low volume
- **Status:** Not useful for crypto signals

### Metaculus
- Scientific/forecasting prediction market
- No crypto price markets, but has macro/geopolitical forecasts
- Could be useful for long-term macro signals (Fed rate, regulation)
- API: `https://www.metaculus.com/api2/questions/?search=bitcoin`
- **Status:** Potential for macro overlay signals

---

## 4. SIGNAL STRATEGY RECOMMENDATIONS

### Priority 1: Polymarket Probability Curve (IMPLEMENTED)
Already in `polymarket_signals.py`. Fetches crypto markets, extracts probabilities, generates directional signals.

**Enhancement needed:**
- Add the events endpoint (slug-based) for complete BTC/ETH/SOL price ladders
- Track probability changes over time (store history in JSON/SQLite)
- Calculate implied expected value from the probability distribution

### Priority 2: Polymarket Momentum Detector (NEW)
```
Every 30 min:
1. Fetch price history for top BTC/ETH/SOL markets via CLOB API
2. Calculate 4hr and 24hr rate of change
3. If probability shifts >5% in 4hr => MOMENTUM signal
4. Cross-reference with spot price to detect divergences
```
This is the **unique edge** -- no other system tracks prediction market momentum.

### Priority 3: Kalshi Multi-Timeframe Consensus (NEW)
```
1. Fetch KXBTC 15min, hourly, daily, weekly, monthly markets
2. Build a timeframe consensus: if all timeframes bullish => strong signal
3. Look for timeframe divergences (15min bearish but monthly bullish => mean reversion opportunity)
```

### Priority 4: Implied Distribution Strategy (NEW)
```
From "What price will BTC hit in March?" event:
1. Extract all price level probabilities
2. Build a discrete probability distribution
3. Calculate expected value, skew, kurtosis
4. Compare to options-implied distribution for arbitrage signals
5. If prediction market implies lower prices than options => bearish edge
```

### Priority 5: Cross-Market Arbitrage Detection (ADVANCED)
```
1. Compare Polymarket BTC probability vs Kalshi BTC probability for same event
2. If Polymarket says 20% chance of $85K and Kalshi says 35% => arbitrage exists
3. Generate signal based on which market is "right" historically
```

---

## 5. CURRENT SNAPSHOT (2026-03-22)

### Market-Implied BTC Outlook
- **Current price:** ~$75K-$78K (based on $75K resolved YES, $80K at 8.5%)
- **March downside risk:** 61% chance of touching $65K
- **March upside potential:** Only 1.95% chance of $85K
- **2026 EOY median:** ~$80K (50/50 at $90K)
- **2026 EOY $100K:** Only 37.5% probability
- **Extreme bear:** 14.5% chance of $25K by EOY
- **Extreme bull:** 5.15% chance of $200K by EOY

### Market-Implied ETH Outlook
- **Current price:** ~$2,000-$2,200
- **March upside:** 16.5% chance of $2,400
- **March downside:** 20.5% chance of $1,800

### Overall Sentiment: BEARISH
Prediction markets with $68M+ at stake are pricing in significant downside risk for BTC in March 2026, with the median outcome for the year being well below the 2024 highs.

---

## 6. EXISTING INTEGRATION

File: `alpha_engine/polymarket_signals.py` (563 lines)
- Fetches crypto markets from Gamma API
- Extracts probabilities and generates LONG/SHORT signals
- Maps to trading symbols (BTCUSDT, ETHUSDT, etc.)
- Generates picks in alpha_engine standard format
- Saves to `data/polymarket_signals.json`

### What's Missing (Enhancement Roadmap)
1. **Events endpoint** -- currently only uses `/markets`, should also use `/events?slug=...` for complete price ladders
2. **CLOB price history** -- not fetching time series data (momentum detection)
3. **Kalshi integration** -- not implemented at all
4. **Probability distribution** -- not calculating implied expected values
5. **Historical tracking** -- not storing probability snapshots over time
6. **Momentum signals** -- not detecting rapid probability shifts
7. **Leaderboard/whale tracking** -- attempted but no public API available

---

## 7. API QUICK REFERENCE

### Polymarket - No API Key Needed
```bash
# All active crypto events sorted by volume
curl "https://gamma-api.polymarket.com/events?limit=200&active=true&closed=false&order=volume&ascending=false"

# BTC March price ladder
curl "https://gamma-api.polymarket.com/events?slug=what-price-will-bitcoin-hit-in-march-2026"

# BTC 2026 annual targets
curl "https://gamma-api.polymarket.com/events?slug=what-price-will-bitcoin-hit-before-2027"

# ETH March price ladder
curl "https://gamma-api.polymarket.com/events?slug=what-price-will-ethereum-hit-in-march-2026"

# SOL March price ladder
curl "https://gamma-api.polymarket.com/events?slug=what-price-will-solana-hit-in-march-2026"

# Order book for a specific market (use clobTokenIds from gamma response)
curl "https://clob.polymarket.com/book?token_id={numeric_token_id}"

# Price history (time series)
curl "https://clob.polymarket.com/prices-history?market={numeric_token_id}&interval=all&fidelity=60"
```

### Kalshi - No API Key Needed for Market Data
```bash
# All crypto series
curl "https://api.elections.kalshi.com/trade-api/v2/series" | jq '[.series[] | select(.category=="Crypto")]'

# BTC events
curl "https://api.elections.kalshi.com/trade-api/v2/events?status=open&series_ticker=KXBTC"

# BTC markets with price ranges
curl "https://api.elections.kalshi.com/trade-api/v2/markets?event_ticker=KXBTC-26MAR2317"

# All crypto events
curl "https://api.elections.kalshi.com/trade-api/v2/events?limit=100&status=open&category=Crypto"
```
