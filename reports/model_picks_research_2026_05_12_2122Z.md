# Multi-Model Picks Research — Per Asset Class

**Generated:** 2026-05-12 21:22 UTC

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

### grok-4-latest — Grok-4 (X_AI)  (elapsed 17.6s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Bitcoin is exhibiting bullish momentum with recent breakout above the 50-day moving average and increasing on-chain activity.
- **ETHUSDT** SHORT (short-term) — Ethereum shows overbought conditions on RSI with declining trading volume, suggesting a potential pullback.
- **SOLUSDT** LONG (swing) — Solana is benefiting from positive ecosystem news and rising TVL, indicating upward potential in the near term.
**Factors Used:**
- Relative Strength Index (RSI) for overbought/oversold conditions
- Moving Average Convergence Divergence (MACD) for momentum shifts
- On-chain transaction volume for network activity
- Funding rates from perpetual futures for market sentiment
**Data Points To Fetch:**
- OHLCV data from Binance API for price and volume analysis
- Order book depth from exchange feeds for liquidity assessment
- On-chain metrics like active addresses from Glassnode
- Social sentiment scores from LunarCrush
**Swing Trade Setup:** For swing trades in crypto, enter on confirmed breakouts from key support/resistance levels with MACD crossover confirmation and increasing volume; exit using trailing stops at 20% profit or upon reversal signals like bearish engulfing patterns.
**Short Term Setup:** For 1-3 day trades, enter on short-term EMA crossovers combined with RSI divergences for quick momentum plays; exit on predefined 5-10% profit targets or after 48 hours to limit exposure to volatility.

### mercury-2 — Mercury 2 (Inception)  (elapsed 1.2s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Price is above the 200‑day MA with bullish momentum and positive funding rates.
- **ETHUSDT** LONG (swing) — RSI around 55 and rising on‑balance volume indicate sustained uptrend.
- **SOLUSDT** SHORT (short-term) — Overbought RSI >70 and declining open interest suggest a near‑term pullback.
**Factors Used:**
- 200‑day moving average
- Relative Strength Index (RSI)
- On‑Balance Volume (OBV)
- Funding Rate
- Open Interest
**Data Points To Fetch:**
- Current spot price
- 24‑h trading volume
- Order‑book depth (top 5 levels)
- Perpetual futures funding rate
- Network hash rate (for BTC) / staking metrics (for ETH)
**Swing Trade Setup:** Enter on a pullback to the 200‑day MA with RSI between 45‑55 and positive OBV; set stop‑loss 3‑5% below entry and target 15‑20% upside.
**Short Term Setup:** Take a short position when RSI >70 and open interest contracts; exit within 1‑3 days at a 3‑5% profit or if funding rate turns negative.

### moonshot-v1-32k — Kimi K2 (Moonshot REST)  (elapsed 6.6s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Bitcoin continues to show resilience and has a strong correlation with the overall crypto market sentiment.
- **ETHUSDT** LONG (swing) — Ethereum has a strong developer community and is expected to benefit from the upcoming Ethereum 2.0 upgrade.
- **LINKUSDT** SHORT (short-term) — Chainlink has recently seen significant gains, and a pullback is likely due to profit-taking.
**Factors Used:**
- Moving Averages (50-day and 200-day)
- Relative Strength Index (RSI)
- Volume Weighted Average Price (VWAP)
- On-Balance Volume (OBV)
- Crypto Fear & Greed Index
**Data Points To Fetch:**
- Historical price data for the last 30 days
- Volume data for the last 30 days
- Social media sentiment analysis
- News sentiment analysis
- Technical indicators data (RSI, MACD, etc.)
**Swing Trade Setup:** For swing trades, enter long positions when the price crosses above the 50-day moving average and exit when it crosses below the 200-day moving average. For short positions, enter when the price crosses below the 50-day moving average and exit when it crosses above the 200-day moving average.
**Short Term Setup:** For 1-3 day trades, enter long positions when the RSI is below 30 and exit when it reaches 70. For short positions, enter when the RSI is above 70 and exit when it falls below 30.

## EQUITY

## FOREX

## COMMODITY

## ETF

## BOND
