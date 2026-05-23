# Social Media Prediction Farming - Research Summary

## 🔥 COMPREHENSIVE SOURCE COVERAGE

### Active Scrapers (8 Sources)

| # | Source | Type | Method | Frequency | Status |
|---|--------|------|--------|-----------|--------|
| 1 | **Reddit** | Social | JSON API + Pushshift | Every 2h | ✅ Active |
| 2 | **TradingView** | Trading Platform | Playwright + Scrapling | Every 2h | ✅ Active |
| 3 | **Twitter/X** | Social | RSS + Nitter | Every 2h | ✅ Active |
| 4 | **Polymarket** | Prediction Market | Public API | Every 2h | ✅ Active |
| 5 | **CoinCodex** | Aggregator | RSS + API | Every 2h | ✅ Active |
| 6 | **4chan /biz/** | Forum | 4chan API | Every 2h | ✅ Active |
| 7 | **StockTwits** | Social Trading | Public API | Every 2h | ✅ Active |
| 8 | **CryptoPanic** | News | RSS | Every 2h | ✅ Active |

### Reddit Subreddits (25+)

**Major Trading Communities:**
- r/BitcoinMarkets - BTC trading discussion
- r/CryptoMarkets - General crypto trading
- r/CryptoCurrency - Largest crypto community
- r/ethtrader - Ethereum focused
- r/binance - Exchange-specific
- r/CryptoTrading - Trading strategies
- r/SatoshiStreetBets - WSB-style crypto
- r/CryptoMoonShots - Altcoin picks

**Coin-Specific:**
- r/altcoin, r/defi, r/NFTs
- r/solana, r/cardano, r/ethereum, r/BTC
- r/Ripple, r/Chainlink, r/Polkadot
- r/Avalanche, r/Polygon

**Investment & Trading:**
- r/wallstreetbets, r/stocks, r/investing
- r/Daytrading, r/Forex, r/algotrading, r/options
- r/SecurityAnalysis

**Regional:**
- r/CryptoIndia, r/CryptoUK, r/CryptoAus, r/CryptoCanada

### Top Analysts Tracked (20+)

**On-Chain Analysts:**
- Willy Woo (@woonomic)
- Ki Young Ju
- Will Clemente (@WClementeIII)
- Plan B (@100trillionUSD)
- Benjamin Cowen (@intocryptoverse)
- Dylan LeClair (@DylanLeClair_)

**Macro Analysts:**
- Raoul Pal (@RaoulGMI)
- Arthur Hayes (@CryptoHayes)
- Alex Kruger (@krugermacro)

**TA Daily Analysts:**
- Michael van de Poppe (@CryptoMichNL)
- DonAlt (@CryptoDonAlt)
- Credible Crypto (@CredibleCrypto)
- Dave the Wave (@davthewave)
- Hsaka (@HsakaTrades)
- Pentoshi (@Pentosh1)
- Josh Rager (@Josh_Rager)
- Scott Melker (@scottmelker)

**Narrative Analysts:**
- Miles Deutscher (@milesdeutscher)
- Coin Bureau
- Lark Davis (@TheCryptoLark)

### Prediction Markets Tracked

**Via Polymarket API:**
- Bitcoin Up/Down (hourly)
- Ethereum price predictions
- Crypto market cap predictions
- ETF approval predictions
- Regulatory event predictions

**Other Prediction Markets to Consider:**
- Kalshi (regulated US prediction market)
- Augur (decentralized)
- Omen/Gnosis
- Limitless (on Base)
- Overtime (sports + crypto)

### Additional Free Sources Researched

**Price Prediction Sites:**
| Site | Type | Free API/RSS |
|------|------|--------------|
| WalletInvestor | AI Forecasts | Limited |
| DigitalCoinPrice | Long-term forecasts | No |
| CryptoPredictions | 12,000+ coins | No |
| TradingBeasts | Monthly forecasts | No |
| CoinPriceForecast | Yearly predictions | No |
| LongForecast | Economy forecasts | No |

**Social Sentiment:**
- LunarCrush (social analytics)
- Santiment (on-chain + social)
- CoinMarketCap Fear & Greed Index

**Crypto Communities:**
- Discord: Axion, Jacob Crypto Bury, Elite Crypto Signals
- Telegram: Binance Killers, 4C Trading, Evening Trader
- YouTube: Coin Bureau, Lark Davis, Benjamin Cowen

**Other Platforms:**
- Seeking Alpha (analysis)
- FxStreet (forex + crypto)
- Investing.com (forecasts)

## 🎯 Honesty Verification System

### How It Works:

1. **Scrape** - Capture prediction + timestamp + source URL
2. **Track** - Monitor price via Binance API
3. **Validate**:
   - TP Hit → WIN (+PnL)
   - SL Hit → LOSS (-PnL)
   - 7 days expiry → Final PnL
4. **Score** - Update predictor stats and tier

### Tier System:

| Tier | Requirements | Description |
|------|--------------|-------------|
| UNRANKED | < 5 picks | Not enough data |
| QUALIFYING | 5-24 picks | Building track record |
| MIXED | 25+ picks, 45-55% WR | Average performance |
| PROVEN | 25+ picks, 55%+ WR | Consistent winner |
| ELITE | 50+ picks, 65%+ WR, Sharpe > 1.5 | Top performer |
| LOSING | 25+ picks, < 45% WR | Consistent loser |

## 📊 Dashboard Features

- **Live Leaderboard** - Ranked by win rate
- **Source Filtering** - Filter by platform
- **Audit Trail** - Click any predictor to see all picks
- **Source Links** - Every prediction links to original post
- **Real-time Validation** - Prices checked against Binance
- **Auto-refresh** - Updates every 60 seconds

## 🚀 GitHub Actions Workflow

**Schedule:**
- Every 2 hours: Standard scrape
- Daily at 6 AM: Deep farm (all sources)

**Runtime:** ~25 minutes (45 min for deep farm)

**Outputs:**
- `predictions/data/leaderboard.json`
- `predictions/data/active_predictions.json`
- Automatic commits with results

## 💡 Future Expansion Ideas

### High Priority:
1. **YouTube Transcripts** - Farm predictions from video content
2. **Discord Webhooks** - Capture signals from alpha groups
3. **Telegram Bots** - Scrape public signal channels
4. **LunarCrush API** - Social sentiment scoring

### Medium Priority:
5. **DeFi Llama** - TVL predictions
6. **Coingecko** - Trending coins
7. **CryptoQuant** - On-chain signals
8. **Glassnode** - Analytics (paid)

### Low Priority:
9. **TikTok** - Viral crypto content
10. **Instagram** - Influencer calls
11. **Twitch** - Live trading streams

## 🔗 Useful Links

- **Awesome Prediction Markets:** https://github.com/buddies2705/awesome-prediction-market
- **Polymarket:** https://polymarket.com
- **LunarCrush API:** https://lunarcrush.com/developers
- **4chan API:** https://github.com/4chan/4chan-API
- **Reddit JSON:** https://www.reddit.com/r/CryptoMarkets/.json

## 📈 Stats Tracking

Current system tracks:
- Total predictions per source
- Win rate by predictor
- Average PnL
- Best/worst picks
- Sharpe ratio
- Time to resolution

All data is **publicly auditable** via:
- GitHub repository (full history)
- Dashboard (live view)
- Source URLs (original posts)
- Binance prices (objective data)

---

**System Status:** ✅ FULLY OPERATIONAL
**Last Updated:** 2026-02-27
**Sources Active:** 8 platforms, 25+ subreddits, 20+ analysts
