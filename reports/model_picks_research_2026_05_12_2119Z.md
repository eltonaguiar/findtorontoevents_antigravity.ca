# Multi-Model Picks Research — Per Asset Class

**Generated:** 2026-05-12 21:19 UTC

Each model was given the live `asset_class_health` snapshot and asked: top 3 picks,
factors used, data points to fetch, swing-trade setup, short-term setup.

## Live state (asset_class_health input)

| Class | Snapshot |
|---|---|
| CRYPTO | n=7935, WR=46.5%, PF=1.36, status=stable, sizing_allowed=True |
| EQUITY | n=447, WR=53.2%, PF=1.55, status=stable, sizing_allowed=True |
| FOREX | n=1355, WR=46.1%, PF=0.29, status=stressed, sizing_allowed=False |
| COMMODITY | n=422, WR=67.5%, PF=3.89, status=stable, sizing_allowed=True |
| ETF | n=107, WR=56.1%, PF=1.34, status=stable, sizing_allowed=True |
| BOND | n=11, WR=54.5%, PF=0.66, status=thin_sample, sizing_allowed=False |

## CRYPTO

### grok-4-latest — Grok-4 (X_AI)  (elapsed 14.4s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Bitcoin shows strong bullish momentum with recent breakout above key resistance levels amid positive market sentiment.
- **ETHUSDT** LONG (short-term) — Ethereum is poised for gains due to upcoming network upgrades and increasing DeFi adoption.
- **SOLUSDT** SHORT (short-term) — Solana faces downward pressure from network congestion issues and overbought RSI indicators.
**Factors Used:**
- RSI (Relative Strength Index) for overbought/oversold conditions
- Moving Average Convergence Divergence (MACD) for trend reversals
- On-chain transaction volume for liquidity assessment
- Funding rates on perpetual futures for market sentiment
**Data Points To Fetch:**
- Real-time OHLCV (Open, High, Low, Close, Volume) data from Binance API
- Order book depth for bid-ask spreads
- Funding rate history from exchange feeds
- Social sentiment scores from LunarCrush API
**Swing Trade Setup:** For swing trades in crypto, enter long on confirmed breakouts above 50-day moving averages with RSI above 50, and exit on trailing stops or when price hits 200-day moving average resistance; manage risk with 2% position sizing based on stable status.
**Short Term Setup:** In short-term 1-3 day crypto trades, enter based on intraday candlestick patterns like bullish engulfing with high volume confirmation, and exit on predefined profit targets or if MACD histogram flips negative.

### mercury-2 — Mercury 2 (Inception)  (elapsed ?s)
- ERROR: HTTP Error 503: Service Unavailable

### moonshot-v1-32k — Kimi K2 (Moonshot REST)  (elapsed 6.7s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Bitcoin continues to show resilience and has a strong track record of recovery after dips.
- **ETHUSDT** LONG (swing) — Ethereum has a solid development roadmap and is poised for growth with the upcoming Ethereum 2.0 upgrade.
- **ADAUSDT** LONG (short-term) — Cardano's unique proof-of-stake mechanism and upcoming smart contract capabilities make it a promising investment.
**Factors Used:**
- Moving Averages (MA)
- Relative Strength Index (RSI)
- Volume Weighted Average Price (VWAP)
**Data Points To Fetch:**
- Historical price data
- Order book depth
- Social sentiment analysis
- Fundamental data (e.g., upcoming forks, development updates)
- Market liquidity metrics
**Swing Trade Setup:** For swing trades, enter positions when the price crosses above the 50-day MA and RSI is below 70, indicating a potential overbought condition. Exit when the price crosses below the 50-day MA or RSI exceeds 70, signaling a potential trend reversal.
**Short Term Setup:** For short-term trades, look for entry opportunities during periods of high volume and positive sentiment. Exit positions within 1-3 days if the price moves against the initial direction or if VWAP is breached, indicating a change in momentum.

## EQUITY

## FOREX

## COMMODITY

## ETF

## BOND
