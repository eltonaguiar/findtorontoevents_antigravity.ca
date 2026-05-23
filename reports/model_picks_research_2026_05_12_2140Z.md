# Multi-Model Picks Research — Per Asset Class

**Generated:** 2026-05-12 21:40 UTC

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

### qwen2.5-coder:14b — code-specialist (Alibaba)  (elapsed 42.5s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Strong bullish momentum and support from major moving averages.
- **ETHUSDT** SHORT (short-term) — Overbought conditions and potential for a pullback.
- **ADAUSDT** LONG (swing) — Undervalued compared to its peers and strong institutional interest.
**Factors Used:**
- Relative Strength Index (RSI)
- Moving Average Convergence Divergence (MACD)
- Bollinger Bands
- On-Balance Volume (OBV)
- Candlestick Patterns
**Data Points To Fetch:**
- Price action data
- Volume data
- Technical indicators
- Market sentiment analysis
- News and events affecting the crypto market
**Swing Trade Setup:** Enter long positions when a security crosses above its 50-period moving average with bullish candlesticks. Exit when it touches the upper Bollinger Band or reverses below the moving average.
**Short Term Setup:** Buy on a break of a short-term trendline with high volume. Sell when price closes below the trendline for three consecutive days.

### qwen3:14b — Qwen3 general (Alibaba)  (elapsed 26.0s)
- PARSE-FAIL
- tail: `{
  "top_picks": [
    {"symbol": "BTCUSDT", "direction": "LONG", "rationale": "Breakout above 50-period EMA with rising volume suggests bullish momentum", "timeframe": "swing"},
    {"symbol": "ETHUSDT", "direction": "SHORT", "rationale": "Overbought RSI (75) and bearish divergence on daily chart",`

### deepseek-r1:14b — reasoning (DeepSeek)  (elapsed 17.4s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Strong support at $40k after pullback
- **ETHUSDT** SHORT (short-term) — RSI overbought near $2,800 resistance
- **SOLUSDT** LONG (swing) — Bullish engulfing pattern with positive news flow
**Factors Used:**
- RSI
- MACD
- Volume trends
- VWAP
- Market momentum
**Data Points To Fetch:**
- OHLCV data for last 30 days
- RSI(14)
- MACD lines
- Volume profile
- VWAP confirmation
**Swing Trade Setup:** Enter on pullback to resistance, exit at next major resistance level with stop loss below recent swing low.
**Short Term Setup:** Entry on high-volume break of immediate support/resistance, exit at next key level with tight stop.

### devstral-small-2 — code-patches (Mistral)  (elapsed 47.4s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Strong on-chain accumulation and positive funding rate divergence suggest bullish momentum.
- **ETHUSDT** LONG (swing) — ETH/BTC ratio near key support with increasing DeFi activity indicates relative strength.
- **SOLUSDT** SHORT (short-term) — Overbought RSI and declining open interest signal potential correction.
**Factors Used:**
- on-chain accumulation
- funding rate divergence
- ETH/BTC ratio
- RSI
- open interest trends
**Data Points To Fetch:**
- BTC active addresses
- ETH gas fees
- SOL futures open interest
- Crypto fear & greed index
- Stablecoin supply
**Swing Trade Setup:** Enter on confirmation of higher-timeframe trend continuation (e.g., EMA crossover) with stop-loss at recent swing low; exit on RSI divergence or key structure break.
**Short Term Setup:** Trade liquidity voids around key levels (e.g., VWAP) with tight stops; exit on reversal in order flow (e.g., large sell-side imbalances).

### ernie-coder — thinking (Baidu)  (elapsed 67.5s)
- PARSE-FAIL
- tail: `breaks above resistance with bullish MA crossover and increasing volume. Exit when RSI reaches 70 or support (e.g., 50-day MA) breaks."

Short_term_setup: "Enter short on ETHUSDT on breakout below resistance with MACD bearish cross and volume confirmation. Exit if price recovers above resistance or `

### glm-4.7-flash — alt-lineage (Zhipu)  (elapsed 71.3s)
- PARSE-FAIL
- tail: ``

### phi3.5:latest — compact reasoning (Microsoft)  (elapsed 17.0s)
**Top picks:**
- **BTCZC** LONG (swing) — Bitcoin shows a stable price with high weekly return potential given current market sentiment.
- **ETHUSDT** LONG (short-term) — Ethereum'thy performance is robust and poised for growth in the near term due to increasing institutional interest.
**Factors Used:**
- Price momentum indicators (e.g., Stochastic, MACD)
- Volume analysis
- Market sentiment from social media and news sources
**Data Points To Fetch:**
- 24-hour price chart with candlestick patterns
- Hourly trading volume data for the past week
- Twitter hashtags related to cryptocurrency sentiment analysis tool (e.g., ToneTweet)
- Institutional investment reports and announcements
**Swing Trade Setup:** Enter when a strong bullish candlestick pattern forms on the price chart, exit at resistance level or after holding for two days to secure profits.
**Short Term Setup:** Buy upon positive sentiment spikes and sell if volume drops below average levels within three trading sessions.

### gemma3:4b — compact (Google)  (elapsed 11.0s)
**Top picks:**
- **BTCUSDT** LONG (swing) — BTC's recent consolidation suggests a potential breakout driven by institutional adoption.
- **ETHUSDT** LONG (short-term) — Ethereum's upcoming Dencun upgrade could catalyze increased demand and price appreciation.
- **BNBBTC** LONG (swing) — BNB's strong correlation with Bitcoin and potential for increased utility within the Binance ecosystem.
**Factors Used:**
- RSI (14-period)
- MACD (12, 26, 9)
- VWAP (200-period)
- On-Chain Bitcoin Active Address Count
- Market Dominance
**Data Points To Fetch:**
- BTC Spot Price (BinanceUSDT)
- ETH Spot Price (BinanceUSDT)
- BNB Spot Price (BinanceUSDT)
- Bitcoin Hash Rate
- Total Cryptocurrency Market Cap
**Swing Trade Setup:** Enter long positions when the VWAP crosses above the 200-period moving average, confirmed by a bullish RSI divergence, aiming for exits around the next significant resistance level identified by the 200-period VWAP. Short positions would be initiated with a similar setup, reversing the signals.
**Short Term Setup:** For 1-3 day trades, we'll focus on short-term momentum using the MACD and RSI. Long entries are triggered by bullish MACD crossovers and RSI bounces above 50, while short entries are initiated by bearish MACD crossovers and RSI dips below 50.

## EQUITY

## FOREX

## COMMODITY

## ETF

## BOND
