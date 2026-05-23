# Multi-Model Picks Research — Per Asset Class

**Generated:** 2026-05-12 22:06 UTC

Each model was given the live `asset_class_health` snapshot and asked: top 3 picks,
factors used, data points to fetch, swing-trade setup, short-term setup.

## Live state (asset_class_health input)

| Class | Snapshot |
|---|---|
| CRYPTO | n=7795, WR=46.5%, PF=1.36, status=stable, sizing_allowed=True |
| EQUITY | n=447, WR=53.2%, PF=1.55, status=stable, sizing_allowed=True |
| FOREX | n=1356, WR=46.2%, PF=0.29, status=stressed, sizing_allowed=False |
| COMMODITY | n=424, WR=67.7%, PF=3.91, status=stable, sizing_allowed=True |
| ETF | n=107, WR=56.1%, PF=1.34, status=stable, sizing_allowed=True |
| BOND | n=11, WR=54.5%, PF=0.66, status=thin_sample, sizing_allowed=False |

## CRYPTO

### qwen2.5-coder:14b — code-specialist (Alibaba)  (elapsed 11.1s)
**Top picks:**
- **BTCUSDT** LONG (swing) — BTC is showing strong upward momentum and has a positive sentiment.
- **ETHUSDT** SHORT (short-term) — ETH has been overbought and is experiencing a potential price correction.
- **ADAUSDT** LONG (swing) — ADA is in an uptrend with low volatility, making it a stable long-term investment.
**Factors Used:**
- Relative Strength Index (RSI)
- Moving Average Convergence Divergence (MACD)
- Bollinger Bands
- On-Balance Volume (OBV)
- Sentiment Analysis
**Data Points To Fetch:**
- Price Action
- Volume
- Open Interest
- Market Capitalization
- Social Sentiment
**Swing Trade Setup:** Enter a long position when the price crosses above the 20-period moving average and RSI is below 70. Exit when the price touches the upper Bollinger Band or RSI reaches 80.
**Short Term Setup:** Buy on a breakout above resistance with high volume, exit on a close below the opening price or if RSI hits 90.

### qwen3:14b — Qwen3 general (Alibaba)  (elapsed 15.5s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Strong institutional inflows and stable volatility suggest continuation of upward trend
- **ETHUSDT** LONG (swing) — DeFi adoption metrics improving alongside positive macro sentiment
- **XRPUSDT** SHORT (short-term) — Regulatory uncertainty weighs on short-term momentum despite strong fundamentals
**Factors Used:**
- ATR volatility
- RSI divergence
- on-chain active addresses
- 50/200 EMA crossover
- social media sentiment score
**Data Points To Fetch:**
- real-time order book depth
- CBOE Bitcoin Volatility Index (BVOL)
- on-chain transaction volume
- news sentiment analysis
- perpetual funding rates
**Swing Trade Setup:** Enter long when price breaks above 50 EMA with positive volume surge, exit if RSI exceeds 70 or price rejects at key resistance levels
**Short Term Setup:** Scalp entries on sharp news-driven moves with 1.5% stop-loss, exit on 5-period RSI overbought or reversal candlestick patterns

### deepseek-r1:14b — reasoning (DeepSeek)  (elapsed 19.0s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Strong upward momentum with RSI divergence.
- **ETHUSDT** SHORT (short-term) — Overbought conditions on the ETH-BTC pair.
- **SOLBUSD** LONG (swing) — Positive network growth indicators and upcoming updates.
**Factors Used:**
- RSI (Momentum)
- VWAP (Volume Weighted Average Price)
- MACD (Trend Strength)
- Bollinger Bands (Volatility)
- Network Hash Rate (Security)
**Data Points To Fetch:**
- BTCUSDT RSI
- ETH-BTC Volume
- SOL Network Transaction Count
- Market VIX Index
- Binance BTC Funding Rate
**Swing Trade Setup:** Enter on divergence in RSI or pullback to key support levels, exit at resistance or 20% gain.
**Short Term Setup:** Entry on VWAP cross above with tight stop loss based on recent volatility.

### devstral-small-2 — code-patches (Mistral)  (elapsed 39.1s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Strong on-chain accumulation and positive macro sentiment
- **ETHUSDT** LONG (swing) — Outperformance in DeFi sector and ETF approval catalyst
- **SOLUSDT** SHORT (short-term) — Overbought RSI and weak on-chain activity
**Factors Used:**
- on-chain volume
- RSI (14)
- macro sentiment
- ETF approval catalysts
- DeFi sector performance
**Data Points To Fetch:**
- BTC daily active addresses
- ETH gas fees
- SOL open interest
- Crypto fear & greed index
- BTC dominance
**Swing Trade Setup:** Enter on breakout above 20-day EMA with volume confirmation; exit on RSI >70 or macro sentiment shift.
**Short Term Setup:** Trade mean reversion within Bollinger Bands; enter on touch of upper/lower band, exit at middle band.

### ernie-coder — thinking (Baidu)  (elapsed 65.8s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Bullish RSI crossover above 50 with increasing volume
- **ETHUSDT** SHORT (short-term) — Bearish MACD cross below signal line with volume contraction
- **SOLUSDT** LONG (swing) — Price break above 200-day MA with momentum from higher lows
**Factors Used:**
- RSI
- MACD
- Volume
- Moving Averages
- ATR
**Data Points To Fetch:**
- price(BTCUSDT)
- volume(BTCUSDT)
- rsi(BTCUSDT)
- macd(BTCUSDT)
- feedly_crypto_sentiment
**Swing Trade Setup:** Enter long BTCUSDT on RSI >50 and volume >20% above 5-day avg, stop at 1.5% below entry. Exit if RSI >70 or volume <10% avg.
**Short Term Setup:** Enter short ETHUSDT on price break of recent lower high with volume >1.2x 5-day avg, target 3% downside. Exit if price >0.5% above entry high or volume <8x avg.

### glm-4.7-flash — alt-lineage (Zhipu)  (elapsed 49.6s)
- PARSE-FAIL
- tail: ``

### phi3.5:latest — compact reasoning (Microsoft)  (elapsed 4.9s)
- PARSE-FAIL
- tail: `  "symbol": "...",
          "direction": "LONG|SHORT",
          "rationale": "1-sentence why based on specific data points or factors considered relevant for the asset class.",
          "timeframe": "swing/short-term"
    },
  {
      "factor_name": "Price momentum indicators (e.g., Stochastic Os`

### gemma3:4b — compact (Google)  (elapsed 6.6s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Recent price action suggests a potential breakout above the 70k resistance, indicating further upside momentum.
- **ETHUSDT** LONG (short-term) — Ethereum's strong fundamentals and upcoming upgrades continue to drive bullish sentiment.
- **BNBBTC** LONG (swing) — BNB's utility within the Binance ecosystem provides a strong foundation for continued growth.
**Factors Used:**
- RSI (14-period) - To identify overbought/oversold conditions.
- MACD - To assess momentum shifts.
- Volume - To confirm price movements.
- Fibonacci Retracement Levels - To identify potential support and resistance zones.
- Moving Average Convergence Divergence (MACD) - To gauge trend strength and potential reversals.
**Data Points To Fetch:**
- 4-hour RSI (14 period)
- 1-hour MACD Histogram
- Hourly Volume
- BTCUSDT 50-day Moving Average
- ETHUSDT Open Interest (Derivatives)
**Swing Trade Setup:** We'll enter long positions on BTCUSDT when the RSI dips below 30 and the MACD histogram shows a bullish divergence, targeting a 1:2 risk-reward ratio. Exit signals will be triggered by a break of the established resistance level or a significant RSI overbought condition.
**Short Term Setup:** For 1-3 day trades on ETHUSDT, we'll focus on short-term momentum using the hourly MACD and volume. Entry will be long when the MACD crosses above the signal line with increasing volume, aiming for a 1:1 risk-reward ratio and exiting on a pullback to the entry level or a bearish divergence.

## EQUITY

### qwen2.5-coder:14b — code-specialist (Alibaba)  (elapsed 10.4s)
**Top picks:**
- **SPY** LONG (swing) — Strong upward momentum and positive MACD crossover.
- **AAPL** SHORT (short-term) — Overbought conditions on RSI and potential resistance break.
- **GOOGL** LONG (swing) — Positive earnings estimates and rising stock price.
**Factors Used:**
- MACD
- RSI
- Moving Averages
- Earnings Estimates
- Sentiment Analysis
**Data Points To Fetch:**
- Price History
- Volume
- Technical Indicators
- News Sentiment
- Earnings Calendar
**Swing Trade Setup:** Enter long positions on MACD crossovers above zero and exit when the price hits a moving average. For short positions, enter when RSI exceeds 70 and exit on a crossover below zero.
**Short Term Setup:** Buy dips where RSI falls below 30 and sell when it spikes above 80. Use volume as a confirmation tool for entry and exit points.

### qwen3:14b — Qwen3 general (Alibaba)  (elapsed 21.3s)
- PARSE-FAIL
- tail: `{
  "top_picks": [
    {"symbol": "SPY", "direction": "LONG", "rationale": "Broad market momentum aligned with stable system performance", "timeframe": "swing"},
    {"symbol": "TSLA", "direction": "LONG", "rationale": "Strong earnings growth and sector leadership in EVs", "timeframe": "swing"},
   `

### deepseek-r1:14b — reasoning (DeepSeek)  (elapsed 21.2s)
**Top picks:**
- **SPY** LONG (swing) — Strong momentum in tech sector.
- **TSLA** SHORT (short-term) — Overbought conditions on RSI.
- **QQQ** LONG (swing) — Breakout above resistance level.
**Factors Used:**
- RSI
- MACD
- VWAP
- Bollinger Bands
- 20-day Moving Average
**Data Points To Fetch:**
- Most recent trade data
- Options implied volatility
- VWAP data
- S&P 500 futures
- Earnings announcements
**Swing Trade Setup:** Enter on a break above resistance with RSI confirming strength; exit on failure to hold support or hitting profit target.
**Short Term Setup:** Entry on intraday momentum divergence with high volume; exit on reversal signal or predefined price level.

### devstral-small-2 — code-patches (Mistral)  (elapsed 37.4s)
**Top picks:**
- **SPY** LONG (swing) — Strong momentum with WR above 50% and PF > 1.5
- **QQQ** LONG (swing) — Tech sector resilience and positive sector rotation
- **IWM** SHORT (short-term) — Weak relative performance and high volatility
**Factors Used:**
- momentum
- relative strength
- volatility
- sector rotation
- price action
**Data Points To Fetch:**
- SPY 20-day moving average
- QQQ sector performance
- IWM volume spikes
- VIX index
- market breadth indicators
**Swing Trade Setup:** Enter on breakout above 20-day MA with volume confirmation; exit on reversal below 5-day MA or when WR drops below 50%.
**Short Term Setup:** Trade pullbacks to 5-day MA with tight stops; exit on VIX spikes or negative news flow.

### ernie-coder — thinking (Baidu)  (elapsed 56.3s)
**Top picks:**
- **AAPL** LONG (swing) — RSI <30 with bullish price structure above 20-day MA
- **MSFT** LONG (short-term) — MACD crossover with volume spike >1.5x avg
- **TSLA** SHORT (swing) — Price near 52-week low with negative RSI <30
**Factors Used:**
- RSI
- MACD
- Volume Spike
- Moving Average Cross
- ATR Volatility
**Data Points To Fetch:**
- Price (1m)
- Volume (5m)
- RSI (14)
- MA(20/50)
- ATR (14)
**Swing Trade Setup:** Enter long when price crosses above RSI 40 and volume spikes >1.2x avg daily, exit if RSI >65 or MA(20) < MA(50)
**Short Term Setup:** Enter short when price breaks below RSI 35 with bearish MACD crossover, exit if price >2% above entry or RSI >70

### glm-4.7-flash — alt-lineage (Zhipu)  (elapsed 50.4s)
- PARSE-FAIL
- tail: ``

### phi3.5:latest — compact reasoning (Microsoft)  (elapsed 3.6s)
- PARSE-FAIL
- tail: `{
  "top_picks": [
    {"symbol": "SPY", "direction": "LONG", "rationale": "Strong PF and stable status indicate solid fundamentals.", "timeframe": "swing"},
    {"symbol": "AMZN", "direction": "SHORT", "rationale": "High WR suggests overvaluation in a growth-oriented market.", "timeframe": "short-t`

### gemma3:4b — compact (Google)  (elapsed 5.9s)
**Top picks:**
- **SPY** LONG (swing) — SPY's historical performance and current relative strength suggest a continuation of the upward trend.
- **QQQ** LONG (short-term) — Technology sector (QQQ) is exhibiting strong momentum and is expected to outperform.
- **NVDA** LONG (swing) — Nvidia's leadership in AI and strong earnings potential justify a long position.
**Factors Used:**
- Relative Strength Index (RSI)
- Moving Average Convergence Divergence (MACD)
- 50-day Simple Moving Average (SMA)
- Advance-Decline Line
- Volatility Index (VIX)
**Data Points To Fetch:**
- SPY 50-day SMA
- QQQ 50-day SMA
- NVDA Trading Volume
- SPY Beta
- VIX 30-day
**Swing Trade Setup:** We'll initiate long positions on SPY and QQQ when the 50-day SMA crosses above the 200-day SMA, coupled with positive MACD signals, indicating a sustained trend. Exits will be triggered by a break below the 50-day SMA or a significant increase in the VIX.
**Short Term Setup:** For 1-3 day trades, we'll focus on high-probability breakout setups around key support and resistance levels, utilizing RSI and volume confirmation. Entries will be taken on a 3:1 risk-reward ratio, and exits will be set based on stop-loss orders placed just below recent swing lows or above recent swing highs.

## FOREX

### qwen2.5-coder:14b — code-specialist (Alibaba)  (elapsed 14.9s)
**Top picks:**
- **EURUSD** LONG (swing) — Strong bullish momentum on the EURUSD pair.
- **GBPJPY** SHORT (short-term) — Overbought conditions and potential for a reversal.
- **AUDNZD** LONG (swing) — Support level holding strong, indicating a bullish setup.
**Factors Used:**
- Relative Strength Index (RSI)
- Moving Average Convergence Divergence (MACD)
- Bollinger Bands
- Stochastic Oscillator
- Volume
**Data Points To Fetch:**
- 1-hour candlestick data
- 4-hour candlestick data
- Daily candlestick data
- Weekly candlestick data
- Intraday volume data
**Swing Trade Setup:** Enter long positions when the price closes above a rising trendline and RSI is below 70. Exit on a close below the trendline or when RSI reaches overbought levels.
**Short Term Setup:** Look for breakouts above resistance levels with high volume to enter short-term trades. Exit on a close below the breakout level or after 1-3 days.

### qwen3:14b — Qwen3 general (Alibaba)  (elapsed 21.5s)
- PARSE-FAIL
- tail: `{
  "top_picks": [
    {"symbol": "EURUSD", "direction": "LONG", "rationale": "EURUSD shows oversold conditions on RSI with strong support near 1.05, suggesting potential reversal in a stressed market.", "timeframe": "swing"},
    {"symbol": "GBPUSD", "direction": "SHORT", "rationale": "GBPUSD is ov`

### deepseek-r1:14b — reasoning (DeepSeek)  (elapsed 24.0s)
**Top picks:**
- **EURUSD** SHORT (swing) — Weak euro due to ECB policy divergence.
- **GBPUSD** LONG (short-term) — Potential BOE rate hike expectations.
- **USDJPY** SHORT (swing) — Strong yen due to safe-haven demand.
**Factors Used:**
- volatility
- momentum
- trend strength
- economic indicators
- risk sentiment
**Data Points To Fetch:**
- CCI (Commodity Channel Index)
- ADX (Average Directional Index)
- central bank interest rates
- VIX index
- economic news calendar
**Swing Trade Setup:** Enter on support/resistance levels with stop losses, exit at key trend reversals or target price levels.
**Short Term Setup:** Entry based on intraday volatility and momentum indicators like RSI or MACD, exit on reversal patterns or time-based stops.

### devstral-small-2 — code-patches (Mistral)  (elapsed 47.1s)
**Top picks:**
- **EURUSD** SHORT (swing) — Stressed market conditions favor safe-haven USD strength against EUR.
- **GBPUSD** SHORT (short-term) — UK economic uncertainty supports USD outperformance.
- **USDJPY** LONG (swing) — Risk-off sentiment drives yen weakness despite carry trade unwind.
**Factors Used:**
- VIX (volatility index)
- USD index strength
- carry trade positions
- central bank policy divergence
- commodity currency correlations
**Data Points To Fetch:**
- 10-day RSI for EURUSD/GBPUSD
- COT report for USDJPY
- 5-day moving average convergence
- VIX futures term structure
- ECB/Fed policy meeting minutes
**Swing Trade Setup:** Enter on RSI <30 for EURUSD/GBPUSD shorts, exit on RSI >50 or USD index reversal. For USDJPY long, enter on carry trade unwind signals, exit on VIX spike >30.
**Short Term Setup:** Trade GBPUSD short on 1-3 day timeframe using 5-day MA crossovers, exit on MACD bearish divergence. Avoid trades during high-impact news events.

### ernie-coder — thinking (Baidu)  (elapsed 69.6s)

### glm-4.7-flash — alt-lineage (Zhipu)  (elapsed 52.6s)
- PARSE-FAIL
- tail: ``

### phi3.5:latest — compact reasoning (Microsoft)  (elapsed 5.8s)
- PARSE-FAIL
- tail: `{
  "top_picks": [
    {"symbol": "AUDUSD", "direction": "LONG", "rationale": "Stressed status indicates potential undervaluation due to recent market volatility.", "timeframe": "swing"},
    {"symbol": "EURJPY", "direction": "SHORT", "rationale": "High WR suggests overbought conditions, favoring a `

### gemma3:4b — compact (Google)  (elapsed 6.5s)
**Top picks:**
- **EURUSD** SHORT (swing) — Current stressed status and high WR suggest a potential bearish trend continuation.
- **GBPUSD** SHORT (short-term) — GBPUSD exhibiting strong negative momentum and high volatility, presenting a short opportunity.
- **USDJPY** SHORT (swing) — USDJPY's recent performance and high WR indicate a potential for further downside movement.
**Factors Used:**
- Average Directional Index (ADX)
- Moving Average Convergence Divergence (MACD)
- Relative Strength Index (RSI)
- Fractals
- Commitment of Traders (COT) Report
**Data Points To Fetch:**
- EURUSD 1-hour candlestick data (Open, High, Low, Close)
- GBPUSD 4-hour candlestick data (Open, High, Low, Close)
- USDJPY 15-minute candlestick data (Open, High, Low, Close)
- US Dollar Index (DXY) 1-hour data
- German ZEW Economic Sentiment Index
**Swing Trade Setup:** Swing trades would be initiated upon confirmation of a breach of the 20-period moving average with a stop-loss placed just below the recent swing low. Exit would occur upon a retest of the moving average as support or a significant price increase.
**Short Term Setup:** Short-term trades (1-3 days) would focus on breakout patterns following high-volume candle formations, utilizing a tight stop-loss just below the entry point. Exit would be triggered by a reversal candlestick pattern or a target reached based on Fibonacci extensions.

## COMMODITY

### qwen2.5-coder:14b — code-specialist (Alibaba)  (elapsed 10.9s)
**Top picks:**
- **ZC=F** LONG (swing) — Strong bullish momentum in corn futures.
- **CL=F** SHORT (short-term) — Overbought conditions and potential supply concerns.
- **GC=F** LONG (swing) — Gold prices supported by inflation expectations.
**Factors Used:**
- Relative Strength Index (RSI)
- Moving Average Convergence Divergence (MACD)
- Bullish/Bearish Spread
- Volatility Index
- Sentiment Analysis
**Data Points To Fetch:**
- Price Action
- Volume
- Open Interest
- Technical Indicators
- Economic News
**Swing Trade Setup:** Enter long positions when the price crosses above a rising trendline and RSI is below 70. Exit on a pullback to the trendline or when RSI reaches overbought levels.
**Short Term Setup:** Go short when MACD line crosses below the signal line and price action shows a bearish candlestick pattern. Close positions on a bullish reversal or after a small profit is secured.

### qwen3:14b — Qwen3 general (Alibaba)  (elapsed 15.8s)
**Top picks:**
- **CL=F** LONG (swing) — Bullish momentum from supply disruptions and rising inflation expectations
- **GC=F** LONG (swing) — Safe-haven demand amid geopolitical tensions and weak USD
- **HG=F** LONG (short-term) — Industrial demand recovery and tight global copper inventories
**Factors Used:**
- Supply-demand imbalance
- Geopolitical risk index
- Inflation rate
- USD strength
- Seasonal trends
**Data Points To Fetch:**
- EIA crude oil inventory report
- World Bank commodity price index
- CPI data
- USD index (DXY)
- Copper mine production data
**Swing Trade Setup:** Enter long on breakout above 50-day EMA with confirmation from positive sentiment and strong USD; exit on stop-loss below key support or take profit at projected resistance levels.
**Short Term Setup:** Use RSI divergence and MACD crossover for entry; exit after 1-3 days on stop-loss or take profit near immediate resistance with closing below 200-day EMA.

### deepseek-r1:14b — reasoning (DeepSeek)  (elapsed 17.4s)
**Top picks:**
- **ZC=F** LONG (swing) — Geopolitical tensions in energy markets may drive prices higher.
- **GC=F** LONG (swing) — Safe-haven demand amid central bank policy uncertainty.
- **BTCUSDT** SHORT (short-term) — Potential mean-reversion after recent rally; high volatility expected.
**Factors Used:**
- RSI (Momentum)
- MACD (Trend Strength)
- Volume Confirmation
- Support/Resistance Levels
- News Sentiment Impact
**Data Points To Fetch:**
- Brent Crude Futures Prices
- Gold Spot Price
- Bitcoin Index
- Energy Market News Feeds
- Macroeconomic Indicators (CPI, GDP)
**Swing Trade Setup:** Enter on a confirmed break of resistance with RSI <70 and MACD bullish; exit on failure to hold support or bearish divergence.
**Short Term Setup:** Intraday entries based on EMA crossovers and high volume; exit on stop loss or reversal signals within the day.

### devstral-small-2 — code-patches (Mistral)  (elapsed 39.7s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Strong momentum with WR above 60% and positive PF in crypto markets.
- **ZC=F** SHORT (short-term) — Weak relative performance in grains sector with declining WR.
- **EURUSD** LONG (swing) — Carry trade opportunity with positive interest rate differentials.
**Factors Used:**
- momentum (WR)
- performance (PF)
- sector relative strength
- volatility
- liquidity
**Data Points To Fetch:**
- 20-day moving average convergence
- order book depth
- open interest changes
- macro economic indicators
- technical indicators (RSI, MACD)
**Swing Trade Setup:** Enter on breakout above 20-day MA with volume confirmation, exit on RSI >70 or trend reversal signal.
**Short Term Setup:** Trade mean reversion around key moving averages, exit within 3 days on profit target or stop-loss.

### ernie-coder — thinking (Baidu)  (elapsed 71.2s)
- PARSE-FAIL
- tail: `s_to_fetch: ["CLOSE", "VOLUME", "RSI", "ATR", "MACD"]

Swing_trade_setup: "Enter LONG on Gold when price breaks above 200-day MA with increasing volume. Exit if price drops below 50-day MA or RSI falls below 70."

Short_term_setup: "For short-term trades (1-3 days), enter LONG on Copper when MACD cr`

### glm-4.7-flash — alt-lineage (Zhipu)  (elapsed 50.8s)
- PARSE-FAIL
- tail: ``

### phi3.5:latest — compact reasoning (Microsoft)  (elapsed 4.1s)
- PARSE-FAIL
- tail: `{
  "top_picks": [
    {"symbol": "GOLDZ1", "direction": "LONG", "rationale": "High WR indicates strong buying interest and potential for further price appreciation.", "timeframe": "swing"},
    {"symbol": "PLVX3", "direction": "SHORT", "rationale": "PF suggests overvaluation relative to historical `

### gemma3:4b — compact (Google)  (elapsed 5.9s)
**Top picks:**
- **ZCL=F** LONG (swing) — Recent price action suggests a potential breakout above key resistance levels.
- **GC=F** SHORT (short-term) — Elevated gold prices coupled with rising interest rates present a bearish outlook.
- **CL=F** LONG (swing) — Crude oil inventories are expected to decline, supporting upward price momentum.
**Factors Used:**
- Commitment of Traders (COT) Report
- Weather Patterns (US Drought Index)
- Interest Rate Expectations (Federal Funds Rate)
- Geopolitical Risk Index
- Inventory Levels (DOE Weekly Report)
**Data Points To Fetch:**
- CFTC Commitments of Traders Report (1-week and 1-month)
- US Drought Monitor Index
- Federal Reserve Economic Data (FRED) - Federal Funds Rate
- Reuters Geopolitical Risk Index
- US Energy Information Administration (EIA) Weekly Short-Term Energy Outlook
**Swing Trade Setup:** We'll initiate long positions on commodities exhibiting bullish signals from the COT report and EIA outlook, targeting entry around key resistance levels identified through technical analysis. Exits will be triggered by a break below support levels or a significant reversal in momentum.
**Short Term Setup:** For 1-3 day trades, we'll focus on short-term momentum trades based on daily price action and short-term indicators like RSI and MACD. Entries will be taken on breakouts above moving averages, while exits will be set at predetermined stop-loss levels or during trend reversals.

## ETF

### qwen2.5-coder:14b — code-specialist (Alibaba)  (elapsed 11.2s)
**Top picks:**
- **SPY** LONG (swing) — Strong upward momentum and positive MACD crossover.
- **BTCUSDT** SHORT (short-term) — Overbought conditions and recent price action suggesting a pullback.
- **EURUSD** LONG (swing) — Support level breakout with increasing volume.
**Factors Used:**
- MACD
- Relative Strength Index (RSI)
- Moving Average Convergence Divergence (MACD) Crossover
- Bullish/Bearish Spread
- Volume
**Data Points To Fetch:**
- Price
- Volume
- MACD Line
- Signal Line
- RSI Value
**Swing Trade Setup:** Enter long positions on SPY and EURUSD when the price breaks above a key resistance level with strong volume. Exit when there is a clear pullback below the moving average or MACD line crosses below the signal line.
**Short Term Setup:** Enter short position on BTCUSDT when RSI reaches overbought levels (above 70) and price action shows signs of weakening momentum. Exit when price dips below the support level or RSI drops significantly.

### qwen3:14b — Qwen3 general (Alibaba)  (elapsed 19.8s)
**Top picks:**
- **SPY** LONG (swing) — Strong positive momentum and low volatility in a stable market environment
- **XLK** LONG (swing) — Technology sector ETF showing relative strength against broader markets
- **EEM** SHORT (short-term) — Emerging markets ETF exhibiting overbought conditions on short-term charts
**Factors Used:**
- 50-day moving average crossover
- ATR volatility compression
- sector rotation momentum
- liquidity ratio (volume/position size)
- macroeconomic surprise index
**Data Points To Fetch:**
- real-time ETF price and volume
- VIX volatility index
- sector ETF performance rankings
- central bank policy statements
- equity risk premium data
**Swing Trade Setup:** Enter long positions when ETF breaks above 50-day SMA with confirmation on RSI(14) < 50 and ATR < 1.5x 20-day average; exit when RSI(14) > 70 or 10% profit target reached.
**Short Term Setup:** Initiate short trades on EEM when 15-minute RSI(9) > 80 and volume spikes 50% above 20-day average; exit on 5% stop loss or 30-period MACD crossover below signal line.

### deepseek-r1:14b — reasoning (DeepSeek)  (elapsed 20.6s)
**Top picks:**
- **SPY** LONG (swing) — Strong momentum in US equities
- **QQQ** LONG (swing) — Tech sector outperformance expected
- **XLF** SHORT (short-term) — Potential rotation from financials
**Factors Used:**
- MACD
- RSI
- Bollinger Bands
- 50-day MA
- 200-day MA
**Data Points To Fetch:**
- S&P 500 index (SPX)
- Nasdaq-100 (NDX)
- VIX volatility index
- Fed Fund rate
- Sector performance indicators
**Swing Trade Setup:** Enter on confirmed bullish MACD crossover with RSI below 70 for oversell signal; exit on bearish MACD or resistance at upper Bollinger Band.
**Short Term Setup:** Enter on Bollinger Band squeeze with volume spike; exit on break of trend line support or resistance.

### devstral-small-2 — code-patches (Mistral)  (elapsed 34.8s)
**Top picks:**
- **SPY** LONG (swing) — Strong momentum and positive trend in US equities
- **GLD** SHORT (short-term) — Overbought conditions and potential pullback in gold
- **QQQ** LONG (swing) — Tech sector resilience and positive earnings outlook
**Factors Used:**
- momentum
- trend strength
- relative strength
- volatility
- volume
**Data Points To Fetch:**
- ETF price data
- volume trends
- moving averages
- RSI
- MACD
**Swing Trade Setup:** Enter on breakout above resistance with volume confirmation, exit on RSI divergence or moving average crossover.
**Short Term Setup:** Enter on RSI oversold conditions with positive MACD crossover, exit on profit target or stop-loss.

### ernie-coder — thinking (Baidu)  (elapsed 58.5s)
**Top picks:**
- **XLF** LONG (swing) — Financial ETF with low PE and high ROE, outperforming sector
- **TLT** SHORT (swing) — Bond ETF with rising rates and declining yields, overbought signal
- **JPM** LONG (short-term) — Bank stock with strong earnings growth, low volatility
**Factors Used:**
- PE_ratio
- ROE
- MACD_histogram
- RSI
- ATR
**Data Points To Fetch:**
- last_price
- volume
- rsi
- macd
- atr
**Swing Trade Setup:** Enter LONG on MACD crossover with RSI<70; exit if RSI>75 or price < 20-day MA
**Short Term Setup:** Enter SHORT on break of 50-day MA with volume >1.5x avg; exit if price < 20-day MA

### glm-4.7-flash — alt-lineage (Zhipu)  (elapsed 49.3s)
- PARSE-FAIL
- tail: ``

### phi3.5:latest — compact reasoning (Microsoft)  (elapsed 4.1s)
**Top picks:**
- **SPY** LONG (swing) — High WR and stable status indicate strong momentum with room for growth.
- **QQQ** LONG (swing) — PF suggests undervaluation relative to historical performance, suitable for swing trading in a bullish market.
- **?** ? (short-term) — ?
**Factors Used:**
- Weighted Average Price (WAP)
- Price/Earnings Ratio (PER)
- Volume Trend
- Market Sentiment Indices
- Volatility Measures
**Data Points To Fetch:**
- Historical WARP vs. current period performance
- Current PER compared to historical average and industry benchmarks
- Volume trend over the past week/month
- Recent changes in investor sentiment as measured by surveys or social media analysis tools
- Beta volatility relative to market index
**Swing Trade Setup:** Buy at a WAP that indicates undervaluation and hold until the asset reaches an overbought condition based on PER, then take profits.
**Short Term Setup:** Short sell when sentiment indicators suggest market exhaustion or negative news impacts prices within hours.

### gemma3:4b — compact (Google)  (elapsed 6.3s)
**Top picks:**
- **SPY** LONG (swing) — SPY's high win rate suggests a continuation of recent market trends.
- **GLD** LONG (short-term) — Gold's PF indicates potential upside as a safe-haven asset.
- **USAG** LONG (swing) — USAG's strong performance aligns with expectations of continued economic growth.
**Factors Used:**
- Relative Strength Index (RSI) on SPY
- Moving Average Convergence Divergence (MACD) crossover for GLD
- Treasury Yield Curve Slope
- VIX (Volatility Index)
- Commitment of Traders (COT) Report
**Data Points To Fetch:**
- SPY 30-day moving average
- Gold spot price (ZC=F)
- 10-year Treasury yield
- VIX futures contract prices
- Weekly CFTC COT report
**Swing Trade Setup:** Enter long positions on SPY when the RSI dips below 30 and the MACD crosses above its signal line, confirming a bullish divergence. Exit long positions when the RSI exceeds 70 or the MACD crosses below its signal line, signaling a potential trend reversal.
**Short Term Setup:** Utilize 1-3 day trades focusing on breakout patterns around key moving averages on SPY and GLD. Entry triggers are based on short-term momentum indicators like stochastic oscillators, with exits set at pre-defined risk-reward ratios (e.g., 1:2).

## BOND

### qwen2.5-coder:14b — code-specialist (Alibaba)  (elapsed 10.3s)
**Top picks:**
- **BND** LONG (swing) — High demand for safe-haven assets
- **TLT** LONG (short-term) — Long-term bond ETF with low volatility
- **SHY** SHORT (swing) — Overvalued short-term bond ETF
**Factors Used:**
- yield curve slope
- credit spread
- inflation expectations
- economic growth indicators
- monetary policy signals
**Data Points To Fetch:**
- 10-year Treasury yield
- 2-year Treasury yield
- CPI inflation rate
- GDP growth forecast
- Fed funds rate
**Swing Trade Setup:** Enter long positions in BND and TLT when the yield curve flattens or inverts, exit on a rising yield curve. Short SHY when it outperforms other short-term bonds.
**Short Term Setup:** Buy TLT on pullbacks to support levels, sell on breakouts above resistance. Use SHY as a hedge against rising rates.

### qwen3:14b — Qwen3 general (Alibaba)  (elapsed 19.0s)
**Top picks:**
- **ZN=F** LONG (swing) — Steepening yield curve suggests higher long-term growth expectations, favoring longer-duration bonds
- **HYG** SHORT (short-term) — Credit spreads widening due to inflation fears reduce corporate bond appeal
- **TIP** LONG (swing) — Inflation-linked bonds benefit from rising CPI expectations
**Factors Used:**
- yield curve steepness
- inflation expectations (TIPS breakeven)
- credit spreads (BBB vs. Treasury)
- central bank policy stance
- GDP growth forecasts
**Data Points To Fetch:**
- 10Y-2Y yield spread
- CPI YoY data
- FED Funds rate projections
- Corporate bond default rates
- M2 money supply growth
**Swing Trade Setup:** Enter long ZN=F when 10Y yield breaks above 50-day EMA with RSI <30; exit on 200-day EMA crossover. Short HYG if credit spread >200 bps and CPI >3% YoY
**Short Term Setup:** Buy TIP on 2-day close above 5-day EMA with MACD histogram rising; exit on 3% profit target or 2-day close below 5-day EMA

### deepseek-r1:14b — reasoning (DeepSeek)  (elapsed 20.1s)
**Top picks:**
- **ZN=F** LONG (swing) — Expecting flattening of yield curve due to Fed policy shifts.
- **BZ=** SHORT (short-term) — Potential spread compression in credit markets post-FOMC meeting.
- **HYG** LONG (swing) — Diversified corporate bond exposure for risk-adjusted returns.
**Factors Used:**
- yield_curve_slope
- credit_spread_levels
- volatility_implied
- macroeconomic_data_delayed
- technical_indicator_macd
**Data Points To Fetch:**
- 10Y-2Y Treasury yield spread
- CDX.NA IG credit spreads
- Treasury futures implied volatility
- CPI headline month-over-month
-  unemployment claims weekly report
**Swing Trade Setup:** Enter long on ZN=F when yield curve flattens below -5bp, exit at profit target of +2% or stop loss at -1%. For HYG, enter long during periods of risk-off with RSI <30 and exit at resistance level.
**Short Term Setup:** Trade BZ= intraday using mean reversion strategy; enter short when credit spreads widen above historical median, exit when spread reverts to mean or stop loss triggered.

### devstral-small-2 — code-patches (Mistral)  (elapsed 42.3s)
**Top picks:**
- **TLT** SHORT (swing) — Rising yields and thinning liquidity in long-duration Treasuries signal downside risk.
- **HYG** SHORT (short-term) — High-yield credit spreads widening amid macro uncertainty.
- **IEF** LONG (swing) — Intermediate Treasuries offer relative stability in volatile market conditions.
**Factors Used:**
- yield_curve_slope
- credit_spreads
- liquidity_metrics
- volatility_index
- macro_sentiment
**Data Points To Fetch:**
- 10-year Treasury yield
- ICE BofA High Yield Index spread
- VIX futures curve
- Treasury ETF option implied volatility
- Fed Funds Futures
**Swing Trade Setup:** Enter short on TLT when 10-year yield breaks above 4.25% with credit spreads widening; exit on yield retracement below 4.0%.
**Short Term Setup:** Trade HYG short when credit spreads rise 20bps in a day; cover if VIX drops below 18 within 48 hours.

### ernie-coder — thinking (Baidu)  (elapsed 67.1s)
- PARSE-FAIL
- tail: `lope", "InflationExpectations", "DurationRisk", "LiquidityMetrics", "MomentumIndicators"].

Data_points_to_fetch: 3-5 data feeds. For bonds, maybe yield curves (e.g., 10-year vs 2-year), inflation ETFs (like TIP), treasury yields (ZN=F), bond ETFs (TLT), or macro news (FOMC statements). So ["ZN_F_Ra`

### glm-4.7-flash — alt-lineage (Zhipu)  (elapsed 50.0s)
- PARSE-FAIL
- tail: ``

### phi3.5:latest — compact reasoning (Microsoft)  (elapsed 3.7s)
- PARSE-FAIL
- tail: `{
  "top_picks": [
    {"symbol": "TLT", "direction": "LONG", "rationale": "High yield with potential for recovery due to economic stimulus.", "timeframe": "swing"},
    {"symbol": "SHY", "direction": "LONG", "rationale": "Safe haven status expected during market volatility spike from inflation fear`

### gemma3:4b — compact (Google)  (elapsed 6.4s)
**Top picks:**
- **USG10Y** LONG (swing) — Long exposure to the 10-year Treasury yield, anticipating continued Fed rate hikes and subsequent upward pressure.
- **TLT** LONG (short-term) — Long exposure to the iShares 20+ Year Treasury Bond ETF, capitalizing on the potential for a flight to safety during economic uncertainty.
- **IEI** LONG (swing) — Long exposure to the iShares iBoxx Investment Grade Corporate Bond ETF, leveraging the relative strength of investment-grade bonds.
**Factors Used:**
- 10-Year Treasury Yield
- Credit Spreads (IG vs. HY)
- MOVE Index (Volatility)
- Inflation Expectations (5yr TIPS)
- GDP Growth Rate
**Data Points To Fetch:**
- 10-Year Treasury Yield (FRED)
- Investment Grade Corporate Bond Yields (ICE BofA Index)
- MOVE Index (Bloomberg)
- 5-Year Treasury Inflation-Protected Securities (TIPS) Real Yield (FRED)
- Advance GDP Release (Bureau of Economic Analysis)
**Swing Trade Setup:** Enter long positions when the 10-year Treasury yield demonstrates a sustained upward trend, confirmed by positive GDP growth and decreasing credit spreads. Exit long positions when the yield declines significantly or when credit spreads widen, signaling increased risk aversion.
**Short Term Setup:** Utilize a 1-3 day trading strategy, entering long positions on pullbacks within established uptrends, validated by a decrease in MOVE index volatility and positive GDP data. Exit short-term trades based on a break of key support levels or a reversal in the MOVE index.
