# Crypto Prediction & Forecast Data Sources Research

**Date:** 2026-03-01
**Purpose:** Comprehensive catalog of FREE/low-cost crypto prediction, forecast, and sentiment data sources for integration into our trading system (Alpha Engine + KIMI Rise of the Claw).
**Goal:** Build a multi-source prediction aggregator that combines forecasts into consensus signals.

---

## Table of Contents

1. [Weekly/Daily Crypto Forecasts](#1-weeklydaily-crypto-forecasts)
2. [Sentiment/Social Data APIs](#2-sentimentsocial-data-apis)
3. [On-Chain Prediction Metrics](#3-on-chain-prediction-metrics)
4. [Macro/Cross-Asset Predictors](#4-macrocross-asset-predictors)
5. [AI/ML Prediction Aggregators](#5-aiml-prediction-aggregators)
6. [Prediction Market Data](#6-prediction-market-data)
7. [Bonus: Additional Low-Cost Sources](#7-bonus-additional-low-cost-sources)
8. [Prediction Aggregator Architecture](#8-prediction-aggregator-architecture)
9. [Academic Research on Consensus Forecasting](#9-academic-research-on-consensus-forecasting)
10. [Implementation Priority Matrix](#10-implementation-priority-matrix)

---

## 1. Weekly/Daily Crypto Forecasts

### 1.1 CoinCodex Price Predictions API

| Field | Details |
|---|---|
| **URL** | https://coincodex.com/page/api/ |
| **Free Tier** | Yes - CC BY-NC 3.0 license (free for non-commercial, attribution required) |
| **Data Freshness** | Daily predictions updated; historical data available |
| **API Key Required** | No (public beta API) |
| **Data Format** | JSON |
| **Rate Limit** | Not explicitly documented (beta) |
| **Relevance** | **HIGH** - Provides price predictions for 2000+ coins using technical indicators (MA, RSI, MACD) and halving cycle analysis |
| **Integration Difficulty** | **EASY** |

**Key Endpoints:**
```
GET https://coincodex.com/api/coincodex/get_firstpage_history
  ?days=30&samples=30&coins_limit=10

GET https://coincodex.com/api/coincodex/get_coin_history
  ?symbol=BTC&start_date=2026-01-01&end_date=2026-03-01&samples=60

GET https://coincodex.com/api/coincodex/get_coin_ranges
  ?coins=BTC,ETH,SOL
```

**Prediction Data (Web Scraping Required):**
- Price predictions page: `https://coincodex.com/crypto/bitcoin/price-prediction/`
- Provides 14-day, 1-month, 3-month, 6-month, 1-year forecasts
- Bullish/Bearish sentiment percentages
- Technical indicator consensus (buy/sell/neutral counts)
- Scraping approach: BeautifulSoup + requests on prediction pages

**Notes:** The API itself provides market data (prices, history, ranges) but the prediction data (price targets, forecasts) is on the web pages. A hybrid approach (API for market data + scraping for predictions) would be optimal.

---

### 1.2 WalletInvestor ML Predictions

| Field | Details |
|---|---|
| **URL** | https://walletinvestor.com/forecast |
| **Free Tier** | Yes - website predictions are free to view |
| **Data Freshness** | Updated every 3 minutes with latest prices |
| **API Key Required** | No public API; web scraping required |
| **Data Format** | HTML (scraping needed) |
| **Rate Limit** | Standard web scraping etiquette applies |
| **Relevance** | **HIGH** - ML-based predictions for 8000+ cryptos with short/long term forecasts |
| **Integration Difficulty** | **MEDIUM** (requires scraping) |

**Prediction Data Available:**
- 14-day forecast with daily price targets
- 3-month, 6-month, 1-year, 5-year predictions
- Revenue potential calculator
- "Good/Bad investment" classification
- Predicted min/max/average prices

**Scraping Approach:**
```python
# URL pattern: https://walletinvestor.com/forecast/bitcoin-prediction
# Key data points in HTML tables:
# - 14-day forecast table
# - "Is it a good investment?" verdict
# - Min/Max/Average price predictions
import requests
from bs4 import BeautifulSoup

url = "https://walletinvestor.com/forecast/bitcoin-prediction"
# Parse forecast tables for price targets
```

---

### 1.3 DigitalCoinPrice Forecasts

| Field | Details |
|---|---|
| **URL** | https://digitalcoinprice.com/forecast |
| **Free Tier** | Yes - all forecast pages are publicly accessible |
| **Data Freshness** | Daily updates |
| **API Key Required** | No public API; scraping required |
| **Data Format** | HTML (scraping needed) |
| **Rate Limit** | Standard web scraping |
| **Relevance** | **MEDIUM** - Monthly and yearly forecasts for 20,000+ coins |
| **Integration Difficulty** | **MEDIUM** (requires scraping) |

**Prediction Data Available:**
- Monthly price forecasts (min, average, max) for current year
- Yearly forecasts out to 2035
- Percentage change predictions
- "Profitable investment?" verdict

**URL Pattern:**
```
https://digitalcoinprice.com/forecast/bitcoin
https://digitalcoinprice.com/forecast/ethereum
https://digitalcoinprice.com/forecast/solana
```

---

### 1.4 TradingView Consensus Signals

| Field | Details |
|---|---|
| **URL** | https://pypi.org/project/tradingview-ta/ |
| **Free Tier** | Yes - unofficial Python library, completely free |
| **Data Freshness** | Real-time (live indicator calculations) |
| **API Key Required** | No |
| **Data Format** | Python objects (JSON-serializable) |
| **Rate Limit** | Reasonable use (no hard limit documented) |
| **Relevance** | **HIGH** - Technical analysis consensus from 26+ indicators |
| **Integration Difficulty** | **EASY** |

**Python Library: `tradingview-ta`**
```python
from tradingview_ta import TA_Handler, Interval

handler = TA_Handler(
    symbol="BTCUSDT",
    screener="crypto",
    exchange="BINANCE",
    interval=Interval.INTERVAL_1_DAY
)
analysis = handler.get_analysis()

# Returns:
# analysis.summary
# {"RECOMMENDATION": "BUY", "BUY": 15, "SELL": 3, "NEUTRAL": 8}
# analysis.oscillators  -> RSI, Stoch, CCI, ADX, MACD, etc.
# analysis.moving_averages -> EMA/SMA 10/20/30/50/100/200
```

**Also Available: `tradingview-screener`**
```python
# pip install tradingview-screener
# Scan entire crypto market with custom filters
from tradingview_screener import Scanner
scanner = Scanner.crypto_scanner()
```

**Notes:** This is one of the most valuable sources. It provides the same technical analysis consensus that millions of TradingView users see, with buy/sell/neutral counts from 26 indicators. The `tradingview-ta` library works without any API key or authentication.

---

### 1.5 CryptoPredictions.com

| Field | Details |
|---|---|
| **URL** | https://cryptopredictions.com/ |
| **Free Tier** | Yes - public forecasts |
| **Data Freshness** | Monthly updates |
| **API Key Required** | No API; scraping required |
| **Data Format** | HTML |
| **Relevance** | **MEDIUM** - Monthly/yearly price predictions |
| **Integration Difficulty** | **MEDIUM** (scraping) |

**Data Available:**
- Monthly price predictions (open, min, max, close)
- Yearly forecasts through 2030
- Multiple crypto assets covered

---

### 1.6 Gov.Capital Crypto Forecasts

| Field | Details |
|---|---|
| **URL** | https://gov.capital/crypto/ |
| **Free Tier** | Yes - public forecast pages |
| **Data Freshness** | Daily/Weekly updates |
| **API Key Required** | No API; scraping required |
| **Data Format** | HTML |
| **Relevance** | **MEDIUM** - ML-based forecasts with 14d, 3m, 6m, 1y, 5y horizons |
| **Integration Difficulty** | **MEDIUM** (scraping) |

**Data Available:**
- Short-term (14-day) daily forecasts
- Medium-term (3-month, 6-month) predictions
- Long-term (1-year, 5-year) predictions
- Min/Max/Average price targets

---

## 2. Sentiment/Social Data APIs

### 2.1 LunarCrush (Social Intelligence)

| Field | Details |
|---|---|
| **URL** | https://lunarcrush.com/about/api |
| **Free Tier** | Discover Plan (free) - limited features; Individual $24/mo |
| **Data Freshness** | Real-time social data |
| **API Key Required** | Yes (free account required) |
| **Data Format** | JSON |
| **Rate Limit** | Free: very limited; Individual: 10 req/min |
| **Relevance** | **HIGH** - Industry-leading crypto social sentiment |
| **Integration Difficulty** | **EASY** |

**Key Metrics:**
- **Galaxy Score** (0-100): Combined social + market performance
- **AltRank**: Relative performance vs other cryptos
- **Social Volume**: Total social media mentions
- **Social Sentiment**: Bullish/bearish ratio
- **Social Contributors**: Unique accounts discussing asset

**Example Endpoint:**
```
GET https://lunarcrush.com/api4/public/coins/BTC/time-series/v2
Headers: Authorization: Bearer <API_KEY>
```

**MCP Server Available:** LunarCrush offers an MCP server for AI agent integration - could be useful for automated analysis.

**Notes:** Free tier is very limited. The $24/mo Individual plan provides good value for the quality of social sentiment data. Consider this as a paid integration if free tier proves insufficient.

---

### 2.2 Santiment (On-Chain + Social)

| Field | Details |
|---|---|
| **URL** | https://api.santiment.net/ |
| **Free Tier** | Yes - limited metrics and historical depth |
| **Data Freshness** | Varies: some real-time, some daily |
| **API Key Required** | No for basic queries; Yes for real-time/extended |
| **Data Format** | JSON (GraphQL API) |
| **Rate Limit** | Free: limited; Pro from $49/mo |
| **Relevance** | **HIGH** - Unique combination of on-chain + social + developer data |
| **Integration Difficulty** | **MEDIUM** (GraphQL) |

**Python Client:**
```python
# pip install sanpy
import san

# Free query example:
df = san.get(
    "daily_active_addresses/bitcoin",
    from_date="2026-01-01",
    to_date="2026-03-01"
)
```

**Key Free Metrics:**
- Daily active addresses
- Transaction volume
- Social volume (limited history)
- Development activity (GitHub commits)
- Network growth

**Paid Metrics (Pro $49/mo):**
- Real-time social sentiment
- Whale transaction alerts
- Exchange inflow/outflow
- MVRV ratio
- NVT ratio
- Holder distribution changes

---

### 2.3 The TIE (Institutional Crypto Sentiment)

| Field | Details |
|---|---|
| **URL** | https://www.thetie.io/solutions/sentiment-api/ |
| **Free Tier** | No - institutional product, custom pricing |
| **Data Freshness** | Real-time (minute-level granularity) |
| **API Key Required** | Yes (paid) |
| **Data Format** | JSON |
| **Relevance** | **HIGH** quality but **LOW** accessibility (expensive) |
| **Integration Difficulty** | **EASY** (well-documented) but **expensive** |

**Key Features:**
- Twitter firehose data (billions of tweets/week)
- Patented noise-filtering (eliminates 90%+ of spam)
- Point-in-time data back to 2017
- 1000+ cryptocurrencies covered
- Used by top quant hedge funds

**Notes:** Too expensive for our use case. Consider alternatives like StockGeist or LunarCrush instead.

---

### 2.4 CryptoMood (AI Sentiment)

| Field | Details |
|---|---|
| **URL** | https://github.com/cryptomood/api |
| **Free Tier** | Limited free tier available |
| **Data Freshness** | Real-time |
| **API Key Required** | Yes |
| **Data Format** | JSON |
| **Relevance** | **MEDIUM** |
| **Integration Difficulty** | **EASY** |

**Data Sources:**
- 50,000+ news sources
- Twitter, Facebook, LinkedIn, Reddit
- Whale movement tracking
- Tether emission monitoring

**Key Output:**
- Market sentiment score (bullish/bearish/neutral)
- Sentiment trends over time
- News impact analysis

---

### 2.5 StockGeist Crypto Sentiment

| Field | Details |
|---|---|
| **URL** | https://www.stockgeist.ai/crypto-sentiment-api/ |
| **Free Tier** | Yes - 10,000 monthly API credits + 1 free crypto stream |
| **Data Freshness** | Real-time (SSE streams available) |
| **API Key Required** | Yes (free account) |
| **Data Format** | JSON (REST API + SSE streams) |
| **Rate Limit** | 10k monthly credits on free tier |
| **Relevance** | **HIGH** - Free tier is generous for crypto sentiment |
| **Integration Difficulty** | **EASY** |

**Key Features:**
- 400+ cryptocurrencies tracked
- Real-time sentiment from social media
- REST API + Server-Sent Events (SSE) for streaming
- Sentiment score, volume, and trend data

**Notes:** Best free-tier sentiment API for our use case. 10k monthly credits is enough for periodic polling of top assets.

---

### 2.6 Reddit Sentiment

| Field | Details |
|---|---|
| **URL** | Reddit API / PullPush (Pushshift successor) |
| **Free Tier** | Reddit API: free for non-commercial; PullPush: free |
| **Data Freshness** | Near real-time (Reddit API); Historical (PullPush) |
| **API Key Required** | Reddit: Yes (OAuth); PullPush: No |
| **Data Format** | JSON |
| **Rate Limit** | Reddit: 100 req/min; PullPush: varies |
| **Relevance** | **HIGH** - r/CryptoCurrency has 7M+ members |
| **Integration Difficulty** | **MEDIUM** |

**Reddit API Approach:**
```python
import praw

reddit = praw.Reddit(
    client_id="...",
    client_secret="...",
    user_agent="crypto_sentiment_bot"
)

# Monitor r/CryptoCurrency for sentiment
subreddit = reddit.subreddit("CryptoCurrency")
for post in subreddit.hot(limit=50):
    # NLP sentiment analysis on title + comments
    pass
```

**PullPush (Pushshift Successor):**
```
GET https://api.pullpush.io/reddit/search/submission/
  ?subreddit=CryptoCurrency&size=100&sort=desc
```

**Key Subreddits:**
- r/CryptoCurrency (7M+ members)
- r/Bitcoin (5M+ members)
- r/ethereum (2M+ members)
- r/solana, r/cardano, r/dogecoin

**Sentiment Analysis Pipeline:**
1. Fetch posts/comments from target subreddits
2. Run through VADER or TextBlob sentiment analyzer
3. Aggregate bullish/bearish/neutral counts
4. Weight by upvotes and comment engagement

---

### 2.7 Fear & Greed Index (alternative.me) [ALREADY INTEGRATED]

| Field | Details |
|---|---|
| **URL** | https://api.alternative.me/fng/ |
| **Free Tier** | **Completely free forever** (per their commitment) |
| **Data Freshness** | Daily updates |
| **API Key Required** | **No** |
| **Data Format** | JSON |
| **Rate Limit** | 60 requests/min (enforced over 10-min window) |
| **Relevance** | **HIGH** - Already integrated in our system |
| **Integration Difficulty** | **EASY** (already done) |

**Endpoints:**
```bash
# Current index
curl https://api.alternative.me/fng/

# Historical (all data)
curl "https://api.alternative.me/fng/?limit=0&format=json"

# Last 30 days
curl "https://api.alternative.me/fng/?limit=30"
```

**Response Format:**
```json
{
  "data": [{
    "value": "25",
    "value_classification": "Extreme Fear",
    "timestamp": "1709251200"
  }]
}
```

**Status:** Already integrated in `alpha_engine/vix_spike_reversal.py` and `KIMI_RISEOFTHECLAW/proven_crypto_forex_strategies.py`. Verified working.

---

## 3. On-Chain Prediction Metrics

### 3.1 CryptoQuant Alerts & Indicators

| Field | Details |
|---|---|
| **URL** | https://cryptoquant.com/docs |
| **Free Tier** | Basic plan: free but very limited (Bitcoin only, 1 alert, 24h charts, 3yr history) |
| **Data Freshness** | Real-time for paid; delayed for free |
| **API Key Required** | Yes for API (paid plans only: $39-$1999/mo) |
| **Data Format** | JSON |
| **Relevance** | **HIGH** quality but **LOW** free-tier access |
| **Integration Difficulty** | **MEDIUM** |

**Free Tier Limitations:**
- Bitcoin-only advanced indicators
- 24-hour chart data (up to 3 years history)
- 1 custom alert only
- No API access on free plan

**Telegram Alerts (Free):**
- CryptoQuant publishes alerts on Telegram: https://t.me/s/cryptoquant_alert
- Can be monitored/scraped for whale movements, exchange flows, etc.

**Alternative:** Scrape CryptoQuant's public Telegram channel for alerts as a free workaround.

---

### 3.2 Glassnode Free Tier

| Field | Details |
|---|---|
| **URL** | https://docs.glassnode.com/basic-api/api |
| **Free Tier** | Yes - limited metrics, 100 req/day, daily resolution |
| **Data Freshness** | Daily (free); hourly/real-time (paid) |
| **API Key Required** | Yes (free account) |
| **Data Format** | JSON |
| **Rate Limit** | Free: ~100 req/day |
| **Relevance** | **HIGH** - Industry standard for on-chain analytics |
| **Integration Difficulty** | **EASY** |

**Free Tier Metrics Available:**
```bash
# Active addresses
GET https://api.glassnode.com/v1/metrics/addresses/active_count
  ?a=BTC&api_key=YOUR_KEY

# Exchange balance
GET https://api.glassnode.com/v1/metrics/distribution/balance_exchanges
  ?a=BTC&api_key=YOUR_KEY

# SOPR (Spent Output Profit Ratio)
GET https://api.glassnode.com/v1/metrics/indicators/sopr
  ?a=BTC&api_key=YOUR_KEY
```

**Key Free Metrics for Prediction:**
- Active addresses (network activity proxy)
- Exchange balance (buying/selling pressure)
- SOPR (profit-taking indicator)
- Hash rate (miner health)
- Transaction count
- NUPL (Net Unrealized Profit/Loss) - limited

**Notes:** 100 req/day is enough if we poll daily for key metrics on BTC and ETH. We already reference Glassnode concepts in our on-chain strategies.

---

### 3.3 IntoTheBlock / Sentora Research

| Field | Details |
|---|---|
| **URL** | https://www.intotheblock.com/ (now https://sentora.com/analytics-research) |
| **Free Tier** | Yes - Sentora Research is free (no paywall) |
| **Data Freshness** | Daily updates |
| **API Key Required** | Legacy API sunset; Sentora Research is web-based |
| **Data Format** | HTML (research articles); legacy API was JSON |
| **Relevance** | **MEDIUM** - Good research insights but no longer has programmatic API |
| **Integration Difficulty** | **HARD** (API sunset, now research-only) |

**Key Signals (from research):**
- In/Out of the Money distribution (cost basis clustering)
- Large transaction volume (whale activity)
- Net network growth
- Concentration by large holders
- Correlation matrix between assets

**Notes:** IntoTheBlock has pivoted to "Sentora Research" - a free research platform without API access. Less useful for programmatic integration but good for manual signal validation.

---

### 3.4 Whale Alert API

| Field | Details |
|---|---|
| **URL** | https://developer.whale-alert.io/ |
| **Free Tier** | Yes - 10 req/min, free API key |
| **Data Freshness** | Near real-time (transactions appear within seconds) |
| **API Key Required** | Yes (free registration) |
| **Data Format** | JSON |
| **Rate Limit** | Free: 10 req/min |
| **Relevance** | **HIGH** - Whale movements are strong predictive signals |
| **Integration Difficulty** | **EASY** |

**Endpoints:**
```bash
# Get recent large transactions
GET https://api.whale-alert.io/v1/transactions
  ?api_key=YOUR_KEY&min_value=1000000&start=UNIX_TIMESTAMP

# Get specific transaction
GET https://api.whale-alert.io/v1/transaction/BLOCKCHAIN/TX_HASH
  ?api_key=YOUR_KEY
```

**Response Example:**
```json
{
  "transactions": [{
    "blockchain": "bitcoin",
    "symbol": "BTC",
    "transaction_type": "transfer",
    "hash": "...",
    "from": {"owner": "binance", "owner_type": "exchange"},
    "to": {"owner": "unknown", "owner_type": "unknown"},
    "amount": 500,
    "amount_usd": 45000000,
    "timestamp": 1709251200
  }]
}
```

**Supported Blockchains:** Bitcoin, Ethereum, Algorand, Bitcoin Cash, Dogecoin, Litecoin, Polygon, Solana, Ripple, Cardano, Tron

**Predictive Use Cases:**
- Exchange -> Unknown wallet = accumulation (bullish)
- Unknown -> Exchange = potential selling (bearish)
- Large stablecoin movements to exchanges = buying pressure incoming
- Whale accumulation patterns during fear = contrarian buy signal

---

### 3.5 Blockchain.com Charts API (Hash Rate + Network Data)

| Field | Details |
|---|---|
| **URL** | https://www.blockchain.com/api/charts_api |
| **Free Tier** | **Completely free** |
| **Data Freshness** | Daily updates |
| **API Key Required** | **No** |
| **Data Format** | JSON |
| **Rate Limit** | Reasonable use |
| **Relevance** | **HIGH** - Hash rate, difficulty, transaction data |
| **Integration Difficulty** | **EASY** |

**Endpoints:**
```bash
# Hash rate
GET https://api.blockchain.info/charts/hash-rate?timespan=30days&format=json

# Difficulty
GET https://api.blockchain.info/charts/difficulty?timespan=1year&format=json

# Transaction volume (USD)
GET https://api.blockchain.info/charts/estimated-transaction-volume-usd?timespan=30days&format=json

# Mempool size
GET https://api.blockchain.info/charts/mempool-size?timespan=7days&format=json

# Miners revenue
GET https://api.blockchain.info/charts/miners-revenue?timespan=1year&format=json
```

**Already Referenced:** We use blockchain.info data in `alpha_engine/onchain_strategies.py` for hash ribbon calculations. This is a confirmed working source.

---

## 4. Macro/Cross-Asset Predictors

### 4.1 FRED API (Federal Reserve Economic Data) [PARTIALLY INTEGRATED]

| Field | Details |
|---|---|
| **URL** | https://fred.stlouisfed.org/docs/api/fred/ |
| **Free Tier** | **Completely free** (840,000+ time series) |
| **Data Freshness** | Varies by series (daily to monthly) |
| **API Key Required** | Yes (free registration at https://fred.stlouisfed.org/docs/api/api_key.html) |
| **Data Format** | JSON, XML |
| **Rate Limit** | 120 req/min |
| **Relevance** | **HIGH** - Critical macro indicators for crypto correlation |
| **Integration Difficulty** | **EASY** |

**Key Series for Crypto Trading:**
```bash
# DXY (US Dollar Index) - inverse correlation with BTC
GET https://api.stlouisfed.org/fred/series/observations
  ?series_id=DTWEXBGS&api_key=YOUR_KEY&file_type=json

# Federal Funds Rate
GET ...?series_id=FEDFUNDS&api_key=YOUR_KEY&file_type=json

# 10-Year Treasury Yield
GET ...?series_id=DGS10&api_key=YOUR_KEY&file_type=json

# 2-Year Treasury Yield (for yield curve)
GET ...?series_id=DGS2&api_key=YOUR_KEY&file_type=json

# Fed Balance Sheet (Total Assets)
GET ...?series_id=WALCL&api_key=YOUR_KEY&file_type=json

# Reverse Repo (RRP)
GET ...?series_id=RRPONTSYD&api_key=YOUR_KEY&file_type=json

# Treasury General Account (TGA)
GET ...?series_id=WTREGEN&api_key=YOUR_KEY&file_type=json

# M2 Money Supply
GET ...?series_id=M2SL&api_key=YOUR_KEY&file_type=json

# CPI (Consumer Price Index)
GET ...?series_id=CPIAUCSL&api_key=YOUR_KEY&file_type=json

# VIX
GET ...?series_id=VIXCLS&api_key=YOUR_KEY&file_type=json
```

**Hayes Liquidity Index Formula (already in our system):**
```
Net Liquidity = Fed Balance Sheet (WALCL) - RRP (RRPONTSYD) - TGA (WTREGEN)
```

**Status:** Already partially integrated in `alpha_engine/onchain_strategies.py` (`hayes_liquidity_index` strategy). Expand to include DXY, yield curve, and VIX.

---

### 4.2 DXY Forecasts

| Field | Details |
|---|---|
| **Primary Source** | FRED API (series: DTWEXBGS for broad trade-weighted dollar) |
| **Alternative** | TradingView TA on DXY for technical consensus |
| **Free Tier** | Yes (both FRED and TradingView TA) |
| **Relevance** | **HIGH** - Strong inverse correlation with BTC |
| **Integration Difficulty** | **EASY** |

**Implementation:**
```python
from tradingview_ta import TA_Handler, Interval

# Get DXY technical analysis consensus
dxy = TA_Handler(symbol="DXY", screener="cfd", exchange="TVC", interval=Interval.INTERVAL_1_DAY)
analysis = dxy.get_analysis()
# If DXY is "STRONG_SELL" -> bullish for crypto
# If DXY is "STRONG_BUY" -> bearish for crypto
```

---

### 4.3 VIX Term Structure

| Field | Details |
|---|---|
| **URL** | FRED: VIXCLS; CBOE: vixcentral.com |
| **Free Tier** | Yes (FRED for VIX close; CBOE website for term structure) |
| **Data Freshness** | Daily (FRED); real-time during market hours (CBOE) |
| **API Key Required** | FRED: Yes (free); CBOE: No (scraping) |
| **Relevance** | **HIGH** - VIX spikes correlate with crypto buying opportunities |
| **Integration Difficulty** | **EASY** (FRED) / **MEDIUM** (term structure scraping) |

**Status:** Already integrated in `alpha_engine/vix_spike_reversal.py`. VIX > 30 triggers our crypto buy signals.

**Enhancement:** Add VIX term structure (contango/backwardation) as an additional signal. Contango = complacency (caution), backwardation = fear (opportunity).

---

### 4.4 CME FedWatch Probabilities

| Field | Details |
|---|---|
| **URL** | https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html |
| **Free Tier** | Web tool is free; API is $25/month |
| **Data Freshness** | Real-time during market hours |
| **API Key Required** | API: Yes ($25/mo); Web: No |
| **Data Format** | JSON (API); HTML (web) |
| **Relevance** | **HIGH** - Rate cut expectations drive crypto rallies |
| **Integration Difficulty** | **MEDIUM** |

**Free Alternative: pyfedwatch (Python)**
```python
# pip install pyfedwatch
# Open-source Python implementation of CME FedWatch
# Calculates probabilities from Fed Funds futures prices
# GitHub: https://github.com/ARahimiQuant/pyfedwatch
```

**Web Scraping Approach:**
- Parse probabilities from CME's public FedWatch page
- Track changes in rate cut/hike probabilities
- Signal: Increasing rate cut probability = bullish for crypto

---

### 4.5 Treasury Yield Curve Data

| Field | Details |
|---|---|
| **URL** | FRED API (DGS2, DGS5, DGS10, DGS30) |
| **Free Tier** | **Completely free** |
| **Data Freshness** | Daily |
| **API Key Required** | Yes (free FRED key) |
| **Relevance** | **HIGH** - Yield curve inversion/steepening signals |
| **Integration Difficulty** | **EASY** |

**Key Signals:**
```python
# Yield curve spread (10Y - 2Y)
spread = yield_10y - yield_2y

# Inversion (spread < 0) historically precedes recessions
# Steepening after inversion = risk-on, bullish for crypto
# Flattening = risk-off, bearish for crypto
```

---

## 5. AI/ML Prediction Aggregators

### 5.1 CoinPriceForecast.com

| Field | Details |
|---|---|
| **URL** | https://coinpriceforecast.com/ |
| **Free Tier** | Yes - public forecasts |
| **Data Freshness** | Monthly updates |
| **API Key Required** | No API; scraping required |
| **Data Format** | HTML |
| **Relevance** | **MEDIUM** - Mid/end-of-year price predictions |
| **Integration Difficulty** | **MEDIUM** (scraping) |

**Methodology:** Uses time series data, media news, regulator activities, coin events (forks), and exchange volumes. Combines statistical methods with ML models.

**Data Available:**
- Mid-year and end-of-year price targets
- Monthly forecast tables
- Year-over-year growth projections (through 2036)

---

### 5.2 PricePrediction.net

| Field | Details |
|---|---|
| **URL** | https://priceprediction.net/ |
| **Free Tier** | Yes - public forecasts |
| **Data Freshness** | Monthly updates |
| **API Key Required** | No API; scraping required |
| **Data Format** | HTML |
| **Relevance** | **MEDIUM** - Aggregates multiple prediction models |
| **Integration Difficulty** | **MEDIUM** (scraping) |

**Data Available:**
- Monthly price predictions (min, average, max)
- Yearly forecasts through 2030+
- Technical analysis summary
- Multiple coins covered

---

### 5.3 RapidAPI Cryptocurrency Price Prediction API

| Field | Details |
|---|---|
| **URL** | https://rapidapi.com/ovinokurov/api/cryptocurrency-price-prediction-api |
| **Free Tier** | Basic plan (limited requests) |
| **Data Freshness** | On-demand predictions |
| **API Key Required** | Yes (RapidAPI key) |
| **Data Format** | JSON |
| **Relevance** | **MEDIUM** - ML-based price predictions via simple API |
| **Integration Difficulty** | **EASY** |

**Features:**
- Predict future prices using ML algorithms
- Customizable prediction frequency and period
- Multiple cryptocurrencies supported

---

### 5.4 Token Metrics (AI Crypto Signals)

| Field | Details |
|---|---|
| **URL** | https://www.tokenmetrics.com/ |
| **Free Tier** | Limited free tier |
| **Data Freshness** | Daily |
| **API Key Required** | Yes |
| **Data Format** | JSON |
| **Relevance** | **MEDIUM** - AI-generated buy/sell ratings |
| **Integration Difficulty** | **EASY** |

---

## 6. Prediction Market Data

### 6.1 Polymarket API

| Field | Details |
|---|---|
| **URL** | https://docs.polymarket.com/ |
| **Free Tier** | Yes - read-only market data is free |
| **Data Freshness** | Real-time (WebSocket < 50ms latency) |
| **API Key Required** | No for market data reads; HMAC for trading |
| **Data Format** | JSON (REST + WebSocket) |
| **Rate Limit** | Generous for read operations |
| **Relevance** | **HIGH** - 94%+ accuracy on predictions |
| **Integration Difficulty** | **EASY** |

**Key Endpoints:**
```bash
# List all crypto markets
GET https://clob.polymarket.com/markets?tag=crypto

# Get specific market odds
GET https://clob.polymarket.com/markets/{market_id}

# Get orderbook
GET https://clob.polymarket.com/book?token_id={token_id}
```

**Crypto-Specific Markets:**
- "Will BTC reach $X by [date]?"
- "Will ETH reach $X by [date]?"
- "Will [event] happen in crypto?"

**Trading Signal Use Cases:**
- High probability (>70%) of BTC reaching price target = bullish confirmation
- Rapid probability changes = momentum signal
- Divergence between Polymarket odds and our technical signals = opportunity

**Python/TypeScript SDKs:** Official libraries available from Polymarket.

**Notes:** Polymarket is exceptionally valuable because prediction markets aggregate collective intelligence. Their 94%+ accuracy rate is better than most individual forecasters. FREE for read-only data.

---

### 6.2 Kalshi API

| Field | Details |
|---|---|
| **URL** | https://docs.kalshi.com/ |
| **Free Tier** | Yes - API access is free (pay only trading fees: 0.7-3.5%) |
| **Data Freshness** | Real-time |
| **API Key Required** | Yes (free account) |
| **Data Format** | JSON (REST + WebSocket + FIX) |
| **Relevance** | **HIGH** - CFTC-regulated prediction market |
| **Integration Difficulty** | **EASY** |

**Key Features:**
- Crypto price prediction markets
- Fed rate decision markets (complement to FedWatch)
- Economic event markets
- Official Python and TypeScript SDKs

**Crypto Markets Available:**
```
https://kalshi.com/category/crypto
```

**Signal Use Cases:**
- Fed rate decision probabilities (alternative to FedWatch)
- Crypto milestone price targets
- Macro event probabilities

---

## 7. Bonus: Additional Low-Cost Sources

### 7.1 CoinGecko API (Market Data Foundation)

| Field | Details |
|---|---|
| **URL** | https://www.coingecko.com/en/api |
| **Free Tier** | Demo: 30 calls/min, 10k/month; Public: 5-15 calls/min |
| **API Key Required** | Demo: Yes (free); Public: No |
| **Data Format** | JSON |
| **Relevance** | **HIGH** - Foundation for all market data |
| **Integration Difficulty** | **EASY** |

**Key Endpoints for Prediction:**
```bash
# Market cap rankings (for rotation signals)
GET https://api.coingecko.com/api/v3/coins/markets
  ?vs_currency=usd&order=market_cap_desc&per_page=100

# OHLCV data (for technical analysis)
GET https://api.coingecko.com/api/v3/coins/bitcoin/ohlc?vs_currency=usd&days=30

# Trending coins (momentum signal)
GET https://api.coingecko.com/api/v3/search/trending

# Global market data (dominance, total market cap)
GET https://api.coingecko.com/api/v3/global
```

**Status:** Already used in several Alpha Engine strategies. Expand usage for trend/momentum signals.

---

### 7.2 Messari API (Research-Grade Data)

| Field | Details |
|---|---|
| **URL** | https://data.messari.io/docs/ |
| **Free Tier** | Yes - prices, market metrics, on-chain data, asset profiles |
| **API Key Required** | Optional (improves rate limits) |
| **Data Format** | JSON |
| **Rate Limit** | Free: 20 req/min |
| **Relevance** | **MEDIUM** - Good supplementary data |
| **Integration Difficulty** | **EASY** |

**Endpoints:**
```bash
# Asset metrics
GET https://data.messari.io/api/v1/assets/bitcoin/metrics

# Market data
GET https://data.messari.io/api/v1/assets/bitcoin/metrics/market-data

# Asset profile (qualitative)
GET https://data.messari.io/api/v2/assets/bitcoin/profile
```

---

### 7.3 Coindive (Social Tracker)

| Field | Details |
|---|---|
| **URL** | https://coindive.app/ |
| **Free Tier** | Yes - basic social tracking |
| **Data Freshness** | Real-time |
| **Relevance** | **MEDIUM** - Multi-platform social aggregation |
| **Integration Difficulty** | **MEDIUM** |

---

## 8. Prediction Aggregator Architecture

### Overview

The goal is to combine multiple prediction sources into a single consensus signal that is more reliable than any individual source.

### Architecture Diagram

```
                    ┌─────────────────────────┐
                    │  PREDICTION AGGREGATOR   │
                    │   consensus_engine.py    │
                    └──────────┬──────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   ┌────▼────┐           ┌────▼────┐           ┌────▼────┐
   │ LAYER 1 │           │ LAYER 2 │           │ LAYER 3 │
   │ Price   │           │Sentiment│           │ Macro   │
   │Forecasts│           │ Social  │           │Cross-Ast│
   └────┬────┘           └────┬────┘           └────┬────┘
        │                     │                     │
   ┌────┼────┐           ┌────┼────┐           ┌────┼────┐
   │CoinCodex│           │F&G Index│           │FRED DXY │
   │WalletInv│           │LunarCrsh│           │VIX      │
   │DigCoin  │           │StockGeis│           │FedWatch │
   │TV Consns│           │Reddit   │           │Yield Crv│
   │GovCapitl│           │CryptoMod│           │Liquidity│
   │CoinPrice│           │WhaleAlrt│           │Polymarkt│
   └─────────┘           └─────────┘           └─────────┘
```

### Consensus Algorithm

```python
class PredictionAggregator:
    """
    Multi-source prediction consensus engine.

    Methodology:
    1. Normalize all predictions to a -1 (strong sell) to +1 (strong buy) scale
    2. Weight sources by historical accuracy (tracked over time)
    3. Require minimum source agreement threshold (e.g., 60%+)
    4. Apply confidence decay for stale predictions
    5. Output: consensus_score, confidence, direction, agreement_pct
    """

    WEIGHTS = {
        # Layer 1: Price Forecasts (weight by historical accuracy)
        'tradingview_ta': 0.20,      # High signal quality, real-time
        'coincodex': 0.10,            # ML-based, daily
        'walletinvestor': 0.08,       # ML-based, frequent updates
        'digitalcoinprice': 0.05,     # Monthly, lower weight
        'gov_capital': 0.05,          # Monthly, lower weight
        'coinpriceforecast': 0.02,    # Infrequent, lowest weight

        # Layer 2: Sentiment/Social (contrarian + trend)
        'fear_greed': 0.12,           # Proven contrarian indicator
        'stockgeist': 0.08,           # Real-time social sentiment
        'reddit_sentiment': 0.05,     # Community pulse
        'whale_alert': 0.10,          # Whale movements (high signal)

        # Layer 3: Macro/Cross-Asset
        'dxy_trend': 0.05,            # Dollar strength inverse
        'vix_level': 0.04,            # Fear gauge
        'yield_curve': 0.03,          # Recession/expansion signal
        'fed_liquidity': 0.05,        # Hayes liquidity formula

        # Layer 4: Prediction Markets
        'polymarket': 0.08,           # Collective intelligence
    }

    def normalize_signal(self, source, raw_value):
        """Convert source-specific values to -1 to +1 scale."""
        normalizers = {
            'tradingview_ta': lambda v: {
                'STRONG_BUY': 1.0, 'BUY': 0.5,
                'NEUTRAL': 0.0,
                'SELL': -0.5, 'STRONG_SELL': -1.0
            }.get(v, 0.0),

            'fear_greed': lambda v: (50 - v) / 50,  # Contrarian: fear=buy
            # ... more normalizers
        }
        return normalizers[source](raw_value)

    def calculate_consensus(self, signals: dict) -> dict:
        """
        Calculate weighted consensus from all available signals.

        Returns:
            {
                'consensus_score': float,  # -1 to +1
                'direction': str,          # 'BUY', 'SELL', 'NEUTRAL'
                'confidence': float,       # 0-100%
                'agreement_pct': float,    # % of sources agreeing
                'sources_used': int,
                'strongest_signal': str,
                'weakest_signal': str,
            }
        """
        weighted_sum = 0
        total_weight = 0
        directions = {'buy': 0, 'sell': 0, 'neutral': 0}

        for source, raw_value in signals.items():
            if source not in self.WEIGHTS:
                continue

            normalized = self.normalize_signal(source, raw_value)
            weight = self.WEIGHTS[source]

            weighted_sum += normalized * weight
            total_weight += weight

            if normalized > 0.2:
                directions['buy'] += weight
            elif normalized < -0.2:
                directions['sell'] += weight
            else:
                directions['neutral'] += weight

        consensus_score = weighted_sum / total_weight if total_weight > 0 else 0

        # Determine direction
        if consensus_score > 0.3:
            direction = 'BUY'
        elif consensus_score < -0.3:
            direction = 'SELL'
        else:
            direction = 'NEUTRAL'

        # Calculate agreement
        max_direction = max(directions, key=directions.get)
        agreement_pct = directions[max_direction] / total_weight * 100

        return {
            'consensus_score': round(consensus_score, 4),
            'direction': direction,
            'confidence': round(abs(consensus_score) * 100, 1),
            'agreement_pct': round(agreement_pct, 1),
            'sources_used': len(signals),
        }
```

### Data Collection Schedule

```
Every 15 minutes:
  - TradingView TA consensus (real-time)
  - Fear & Greed Index (cached daily but check)
  - Whale Alert transactions (near real-time)

Every 1 hour:
  - StockGeist sentiment (conserve API credits)
  - CoinGecko trending/market data
  - Polymarket crypto odds

Every 6 hours:
  - Reddit sentiment aggregation
  - CryptoMood sentiment

Every 24 hours:
  - FRED macro data (DXY, VIX, yields, liquidity)
  - Glassnode on-chain metrics
  - Blockchain.com hash rate/difficulty
  - Web scraping: CoinCodex, WalletInvestor, DigitalCoinPrice predictions
  - Messari asset metrics
```

### Confidence Decay

```python
def apply_staleness_decay(signal_age_hours, base_weight):
    """
    Reduce weight of stale signals.
    - Real-time signals: no decay for 1 hour
    - Daily signals: no decay for 24 hours
    - Weekly signals: no decay for 168 hours
    """
    half_life = {
        'realtime': 2,   # 50% weight after 2 hours
        'daily': 24,     # 50% weight after 24 hours
        'weekly': 168,   # 50% weight after 1 week
    }
    decay = 0.5 ** (signal_age_hours / half_life)
    return base_weight * decay
```

---

## 9. Academic Research on Consensus Forecasting

### Key Papers

1. **"CryptoPulse: Short-Term Cryptocurrency Forecasting with Dual-Prediction and Cross-Correlated Market Indicators"** (arXiv 2502.19349, 2025)
   - Dual-prediction: macro conditions forecast + crypto dynamics forecast, fused by market sentiment
   - Key finding: Combining macro and crypto-specific signals significantly improves accuracy
   - **Directly applicable** to our aggregator architecture

2. **"Cryptocurrency Price Prediction Algorithms: A Survey and Future Directions"** (MDPI, 2024)
   - Comprehensive survey of prediction methods
   - Ensemble methods (GBR + RFR + SVR + MLP) outperform individual models
   - LSTM consistently best for time-series crypto prediction

3. **"Deep Learning and NLP in Cryptocurrency Forecasting: Integrating Financial, Blockchain, and Social Media Data"** (ScienceDirect, 2025)
   - BART MNLI zero-shot classification for sentiment (bullish/bearish detection)
   - Multi-modal integration of news, social media, on-chain, and price data
   - **Applicable:** Our Reddit/Twitter sentiment pipeline should use modern NLP models

4. **"Prediction of Cryptocurrency's Price Using Ensemble Machine Learning Algorithms"** (Emerald Publishing, 2024)
   - Dynamic forecasting using ensemble of GBR, RFR, SVR, MLP
   - Tested on top 15 cryptocurrencies
   - **Key insight:** Ensemble of diverse models beats any single model

5. **"Practical Forecasting of Cryptocoins Time Series using Correlation Patterns"** (arXiv, 2024)
   - Cross-correlation between coins improves forecasting
   - **Applicable:** Our multi-asset strategy can benefit from cross-coin correlation signals

### Key Findings for Our Aggregator

1. **Ensemble beats individual:** Combining 5+ prediction sources significantly outperforms any single source
2. **Multi-modal is critical:** Price + sentiment + on-chain + macro yields best results
3. **Recency matters:** More recent data should have higher weight
4. **Cross-asset signals:** BTC movements predict altcoin movements with lag
5. **Prediction markets are remarkably accurate:** Polymarket > individual analyst forecasts

---

## 10. Implementation Priority Matrix

### Tier 1: Implement Immediately (Free, Easy, High Value)

| Source | Status | Action |
|---|---|---|
| TradingView TA (`tradingview-ta`) | Not integrated | `pip install tradingview-ta` - 1 hour to integrate |
| Fear & Greed Index | Already integrated | Verify and expand usage |
| Blockchain.com Charts API | Partially integrated | Add more endpoints |
| FRED API | Partially integrated | Add DXY, yield curve, M2 |
| Whale Alert API | Not integrated | Register for free key - 2 hours |
| Polymarket API | Not integrated | Free read-only - 3 hours |

### Tier 2: Implement This Week (Free/Cheap, Medium Effort)

| Source | Status | Action |
|---|---|---|
| CoinCodex API + scraping | Not integrated | API endpoints + BS4 scraping - 4 hours |
| StockGeist sentiment | Not integrated | Free 10k credits/month - 2 hours |
| Glassnode free tier | Not integrated | Register + integrate key metrics - 3 hours |
| Reddit sentiment (PRAW) | Not integrated | NLP pipeline needed - 6 hours |
| Messari free tier | Not integrated | Simple REST calls - 2 hours |
| Kalshi API | Not integrated | Free read-only - 2 hours |

### Tier 3: Implement Later (Requires Scraping or Paid)

| Source | Status | Action |
|---|---|---|
| WalletInvestor (scraping) | Not integrated | BS4/Playwright scraping - 4 hours |
| DigitalCoinPrice (scraping) | Not integrated | BS4 scraping - 3 hours |
| Gov.Capital (scraping) | Not integrated | BS4 scraping - 3 hours |
| CoinPriceForecast (scraping) | Not integrated | BS4 scraping - 2 hours |
| CME FedWatch (pyfedwatch) | Not integrated | Open-source Python lib - 3 hours |
| CryptoMood | Not integrated | Register for API key - 2 hours |

### Tier 4: Evaluate Later (Paid Services)

| Source | Cost | Decision |
|---|---|---|
| LunarCrush Individual | $24/mo | Evaluate after free alternatives |
| Santiment Pro | $49/mo | Only if free metrics insufficient |
| CryptoQuant Advanced | $39/mo | Only for professional deployment |
| The TIE | Custom (expensive) | Skip - institutional only |

---

## Summary: Quick Start Integration Plan

### Phase 1 (Day 1): Free API Sources
```bash
pip install tradingview-ta praw
```
1. TradingView TA consensus for all tracked assets
2. Expand FRED API usage (DXY, yields, M2)
3. Expand blockchain.com usage (hash rate, difficulty)

### Phase 2 (Day 2-3): Free API Keys
1. Register Whale Alert API key
2. Register StockGeist free account
3. Register Glassnode free account
4. Set up Polymarket read-only access

### Phase 3 (Week 1): Build Aggregator
1. Create `prediction_aggregator.py` module
2. Implement signal normalization (-1 to +1)
3. Build weighted consensus calculation
4. Create data collection scheduler
5. Store predictions in SQLite for backtesting

### Phase 4 (Week 2): Scraping Sources
1. Build scrapers for CoinCodex, WalletInvestor, DigitalCoinPrice
2. Add Reddit sentiment pipeline with NLP
3. Integrate prediction market data (Polymarket + Kalshi)

### Phase 5 (Week 3): Validation
1. Backtest aggregated predictions vs actual prices
2. Calibrate source weights based on accuracy
3. A/B test aggregator vs individual signals
4. Deploy to production pipeline

---

## Estimated Cost Summary

| Category | Monthly Cost |
|---|---|
| Completely Free Sources | $0 |
| Optional Paid Enhancements | $25-73/mo |
| Full Premium Stack | $200+/mo |

**Recommended budget: $0-25/month** — All Tier 1 and Tier 2 sources are free. Only CME FedWatch API ($25/mo) is worth paying for among the first two tiers, and even that has a free alternative (pyfedwatch library + web scraping).
