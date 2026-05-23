# Multi-Model Picks per Asset Class — Consolidated

**Generated:** 2026-05-12 22:06 UTC

Combines all `reports/model_picks_research_*.md` runs (REST cloud + Ollama Cloud + local).
Each model: top picks + factors used + data points + swing/short setups.

## Asset classes covered

- **BOND** — 11 model verdicts
- **COMMODITY** — 13 model verdicts
- **CRYPTO** — 13 model verdicts
- **EQUITY** — 13 model verdicts
- **ETF** — 13 model verdicts
- **FOREX** — 11 model verdicts

## CRYPTO

### deepseek-r1:14b — _reasoning (DeepSeek)_
**Top picks:**
- **BTCUSDT** LONG (swing) — Strong upward momentum with RSI divergence.
- **ETHUSDT** SHORT (short-term) — Overbought conditions on the ETH-BTC pair.
- **SOLBUSD** LONG (swing) — Positive network growth indicators and upcoming updates.
**Factors:** RSI (Momentum); VWAP (Volume Weighted Average Price); MACD (Trend Strength); Bollinger Bands (Volatility); Network Hash Rate (Security)
**Data points:** BTCUSDT RSI; ETH-BTC Volume; SOL Network Transaction Count; Market VIX Index; Binance BTC Funding Rate
**Swing:** Enter on divergence in RSI or pullback to key support levels, exit at resistance or 20% gain.
**Short-term:** Entry on VWAP cross above with tight stop loss based on recent volatility.

### deepseek-v3.1:671b-cloud — _DeepSeek V3.1 671B (Ollama Cloud)_
**Top picks:**
- **BTCUSDT** LONG (swing) — Strong bullish divergence on daily RSI suggests a potential reversal from oversold conditions.
- **ETHUSDT** LONG (short-term) — High funding rates have reset, and price is holding key support on high volume, indicating a potential long squeeze is over.
- **SOLUSDT** SHORT (swing) — Failing to break above the 200-day moving average on decreasing volume signals weakness and a likely rejection.
**Factors:** RSI Divergence; 200-Day Moving Average Confluence; Funding Rate Mean Reversion; Volume-Weighted Average Price (VWAP) Deviation; On-Balance Volume (OBV)
**Data points:** 1h/4h RSI values for divergence check; Perpetual swap funding rates for major pairs; Order book depth for key support/resistance levels; 24h volume profile and VWAP; Exchange net flows for whale movement insight
**Swing:** Enter on a confirmed bullish/bearish engulfing candle at a key support/resistance level with RSI divergence; exit at the next major resistance/support or on a 4h close against the 20EMA.
**Short-term:** Enter on a break of the 15m Bollinger Band with a spike in volume, targeting the opposite band; exit at the target or on a loss of the 5EMA.

### devstral-small-2 — _code-patches (Mistral)_
**Top picks:**
- **BTCUSDT** LONG (swing) — Strong on-chain accumulation and positive macro sentiment
- **ETHUSDT** LONG (swing) — Outperformance in DeFi sector and ETF approval catalyst
- **SOLUSDT** SHORT (short-term) — Overbought RSI and weak on-chain activity
**Factors:** on-chain volume; RSI (14); macro sentiment; ETF approval catalysts; DeFi sector performance
**Data points:** BTC daily active addresses; ETH gas fees; SOL open interest; Crypto fear & greed index; BTC dominance
**Swing:** Enter on breakout above 20-day EMA with volume confirmation; exit on RSI >70 or macro sentiment shift.
**Short-term:** Trade mean reversion within Bollinger Bands; enter on touch of upper/lower band, exit at middle band.

### ernie-coder — _thinking (Baidu)_
**Top picks:**
- **BTCUSDT** LONG (swing) — Bullish RSI crossover above 50 with increasing volume
- **ETHUSDT** SHORT (short-term) — Bearish MACD cross below signal line with volume contraction
- **SOLUSDT** LONG (swing) — Price break above 200-day MA with momentum from higher lows
**Factors:** RSI; MACD; Volume; Moving Averages; ATR
**Data points:** price(BTCUSDT); volume(BTCUSDT); rsi(BTCUSDT); macd(BTCUSDT); feedly_crypto_sentiment
**Swing:** Enter long BTCUSDT on RSI >50 and volume >20% above 5-day avg, stop at 1.5% below entry. Exit if RSI >70 or volume <10% avg.
**Short-term:** Enter short ETHUSDT on price break of recent lower high with volume >1.2x 5-day avg, target 3% downside. Exit if price >0.5% above entry high or volume <8x avg.

### gemma3:4b — _compact (Google)_
**Top picks:**
- **BTCUSDT** LONG (swing) — Recent price action suggests a potential breakout above the 70k resistance, indicating further upside momentum.
- **ETHUSDT** LONG (short-term) — Ethereum's strong fundamentals and upcoming upgrades continue to drive bullish sentiment.
- **BNBBTC** LONG (swing) — BNB's utility within the Binance ecosystem provides a strong foundation for continued growth.
**Factors:** RSI (14-period) - To identify overbought/oversold conditions.; MACD - To assess momentum shifts.; Volume - To confirm price movements.; Fibonacci Retracement Levels - To identify potential support and resistance zones.; Moving Average Convergence Divergence (MACD) - To gauge trend strength and potential reversals.
**Data points:** 4-hour RSI (14 period); 1-hour MACD Histogram; Hourly Volume; BTCUSDT 50-day Moving Average; ETHUSDT Open Interest (Derivatives)
**Swing:** We'll enter long positions on BTCUSDT when the RSI dips below 30 and the MACD histogram shows a bullish divergence, targeting a 1:2 risk-reward ratio. Exit signals will be triggered by a break of the established resistance level or a significant RSI overbought condition.
**Short-term:** For 1-3 day trades on ETHUSDT, we'll focus on short-term momentum using the hourly MACD and volume. Entry will be long when the MACD crosses above the signal line with increasing volume, aiming for a 1:1 risk-reward ratio and exiting on a pullback to the entry level or a bearish divergence.

### gpt-oss:120b-cloud — _GPT-OSS 120B (Ollama Cloud)_
**Top picks:**
- **BTCUSDT** LONG (swing) — Bullish on-chain metrics and price above 20‑day EMA with rising funding rates
- **ETHUSDT** LONG (short-term) — Strong RSI rebound from oversold zone and increasing futures open interest
- **BNBUSDT** SHORT (short-term) — Negative MACD crossover and declining on‑chain activity suggest near‑term weakness
**Factors:** On‑chain transaction volume; Relative Strength Index (RSI); MACD histogram; Futures open interest; Funding rate differential
**Data points:** Spot price and 20‑day EMA; Order‑book depth imbalance; 24‑hour funding rate; On‑chain active addresses count; Futures open interest change
**Swing:** Enter on a pullback to the 20‑day EMA with bullish MACD divergence and funding rate >0; target a 2:1 reward‑to‑risk or the next major resistance level, stop just below the EMA swing low.
**Short-term:** Enter on a breakout of the prior day high with volume >150% of average 1‑hour volume; set a tight stop 1% below entry and exit at 1.5× risk or if price re‑enters the 4‑hour EMA band within 24‑48 hours.

### grok-4-latest — _Grok-4 (X_AI)_
**Top picks:**
- **BTCUSDT** LONG (swing) — Bitcoin shows strong upward momentum with breakout above $60,000 resistance and positive on-chain metrics amid stable market conditions.
- **ETHUSDT** SHORT (short-term) — Ethereum is overbought with RSI above 70 and potential for correction given recent whale selling activity.
- **SOLUSDT** LONG (short-term) — Solana exhibits bullish divergence on MACD and increasing network activity supporting a short-term rebound.
**Factors:** RSI momentum indicator; MACD trend convergence; On-chain transaction volume; Funding rate analysis; Market sentiment index
**Data points:** Real-time OHLCV price data; Order book depth from exchanges; Perpetual funding rates; Social media sentiment scores; Whale wallet transaction alerts
**Swing:** For swing trades in crypto, enter on confirmed breakouts above key moving average crossovers with supporting volume, and exit when price reaches Fibonacci extension levels or upon reversal signals like bearish candlestick patterns.
**Short-term:** Enter short-term crypto trades on intraday momentum bursts confirmed by RSI breakouts and high trading volume, exiting within 1-3 days on profit targets or when momentum fades as indicated by MACD histogram contraction.

### mercury-2 — _Mercury 2 (Inception)_
**Top picks:**
- **BTCUSDT** LONG (swing) — Strong on-chain activity and bullish EMA cross suggest upside
- **ETHUSDT** LONG (short-term) — Positive funding rates and RSI divergence indicate short-term strength
- **SOLUSDT** SHORT (short-term) — Overbought RSI and falling volume suggest a pullback
**Factors:** 20/50 EMA cross; RSI; On-chain transaction volume; Futures funding rate; Order book imbalance
**Data points:** Current price; 24h volume; On-chain transaction count; Funding rate; Order book depth
**Swing:** Enter long when price breaks above the 20‑day EMA while the 20‑day EMA is above the 50‑day EMA and RSI is above 40; set stop below the 50‑day EMA and target 8‑12% profit.
**Short-term:** Take long/short on 1‑3 day horizons when price touches Bollinger band extremes with confirming MACD divergence; exit at opposite band or when RSI reverts to neutral.

### moonshot-v1-32k — _Kimi K2 (Moonshot REST)_
**Top picks:**
- **BTCUSDT** LONG (swing) — Bitcoin's dominance in the crypto market and its recent price stability suggest a potential upward trend.
- **ETHUSDT** LONG (short-term) — Ethereum's strong fundamentals and upcoming network upgrades make it a promising investment.
**Factors:** Moving Average Convergence Divergence (MACD); Relative Strength Index (RSI); Volume Weighted Average Price (VWAP)
**Data points:** Historical price data; Order book depth; Social sentiment analysis; Market capitalization; 24-hour trading volume
**Swing:** For swing trades, enter long positions when the MACD signals a bullish crossover and RSI is below 70, indicating a potential overbought condition. Exit when the MACD shows a bearish crossover or RSI reaches 70 or above.
**Short-term:** For short-term trades, look for entry opportunities when price breaks above VWAP and RSI is below 50, suggesting a potential bounce. Exit positions when price falls below VWAP or RSI exceeds 50, indicating a possible reversal.

### phi3.5:latest — _compact reasoning (Microsoft)_
**Top picks:**
- **BTCZC** LONG (swing) — Bitcoin shows a stable price with high weekly return potential given current market sentiment.
- **ETHUSDT** LONG (short-term) — Ethereum'thy performance is robust and poised for growth in the near term due to increasing institutional interest.
**Factors:** Price momentum indicators (e.g., Stochastic, MACD); Volume analysis; Market sentiment from social media and news sources
**Data points:** 24-hour price chart with candlestick patterns; Hourly trading volume data for the past week; Twitter hashtags related to cryptocurrency sentiment analysis tool (e.g., ToneTweet); Institutional investment reports and announcements
**Swing:** Enter when a strong bullish candlestick pattern forms on the price chart, exit at resistance level or after holding for two days to secure profits.
**Short-term:** Buy upon positive sentiment spikes and sell if volume drops below average levels within three trading sessions.

### qwen2.5-coder:14b — _code-specialist (Alibaba)_
**Top picks:**
- **BTCUSDT** LONG (swing) — BTC is showing strong upward momentum and has a positive sentiment.
- **ETHUSDT** SHORT (short-term) — ETH has been overbought and is experiencing a potential price correction.
- **ADAUSDT** LONG (swing) — ADA is in an uptrend with low volatility, making it a stable long-term investment.
**Factors:** Relative Strength Index (RSI); Moving Average Convergence Divergence (MACD); Bollinger Bands; On-Balance Volume (OBV); Sentiment Analysis
**Data points:** Price Action; Volume; Open Interest; Market Capitalization; Social Sentiment
**Swing:** Enter a long position when the price crosses above the 20-period moving average and RSI is below 70. Exit when the price touches the upper Bollinger Band or RSI reaches 80.
**Short-term:** Buy on a breakout above resistance with high volume, exit on a close below the opening price or if RSI hits 90.

### qwen3-coder:480b-cloud — _Qwen3 Coder 480B (Ollama Cloud)_
**Top picks:**
- **BTCUSDT** LONG (swing) — Bitcoin showing accumulation pattern with rising volume and positive funding rates
- **ETHUSDT** LONG (swing) — Ethereum outperforming altcoins with strong smart contract activity metrics
- **SOLUSDT** SHORT (short-term) — Solana approaching key resistance with weakening momentum indicators
**Factors:** on-chain accumulation metrics; funding rate differentials; relative strength vs altcoins; orderbook depth analysis; hash rate trends
**Data points:** live orderbook imbalance ratios; wallet accumulation rates across exchanges; miner selling pressure metrics; stablecoin issuance flows; futures basis spreads
**Swing:** Enter long positions when 20-day MA crosses above 50-day MA with increasing volume, exit when RSI exceeds 75 or 10-day MA breaks below 20-day MA
**Short-term:** Take mean reversion trades against extreme RSI levels (above 80 for shorts, below 20 for longs) with tight stops at recent swing highs/lows and target previous consolidation zones

### qwen3:14b — _Qwen3 general (Alibaba)_
**Top picks:**
- **BTCUSDT** LONG (swing) — Strong institutional inflows and stable volatility suggest continuation of upward trend
- **ETHUSDT** LONG (swing) — DeFi adoption metrics improving alongside positive macro sentiment
- **XRPUSDT** SHORT (short-term) — Regulatory uncertainty weighs on short-term momentum despite strong fundamentals
**Factors:** ATR volatility; RSI divergence; on-chain active addresses; 50/200 EMA crossover; social media sentiment score
**Data points:** real-time order book depth; CBOE Bitcoin Volatility Index (BVOL); on-chain transaction volume; news sentiment analysis; perpetual funding rates
**Swing:** Enter long when price breaks above 50 EMA with positive volume surge, exit if RSI exceeds 70 or price rejects at key resistance levels
**Short-term:** Scalp entries on sharp news-driven moves with 1.5% stop-loss, exit on 5-period RSI overbought or reversal candlestick patterns

## EQUITY

### deepseek-r1:14b — _reasoning (DeepSeek)_
**Top picks:**
- **SPY** LONG (swing) — Strong momentum in tech sector.
- **TSLA** SHORT (short-term) — Overbought conditions on RSI.
- **QQQ** LONG (swing) — Breakout above resistance level.
**Factors:** RSI; MACD; VWAP; Bollinger Bands; 20-day Moving Average
**Data points:** Most recent trade data; Options implied volatility; VWAP data; S&P 500 futures; Earnings announcements
**Swing:** Enter on a break above resistance with RSI confirming strength; exit on failure to hold support or hitting profit target.
**Short-term:** Entry on intraday momentum divergence with high volume; exit on reversal signal or predefined price level.

### deepseek-v3.1:671b-cloud — _DeepSeek V3.1 671B (Ollama Cloud)_
**Top picks:**
- **SPY** LONG (swing) — Strong momentum and trend continuation above key moving averages support a long bias.
- **IWM** LONG (swing) — Small-cap breakout from consolidation suggests catch-up potential to broader market strength.
- **TSLA** SHORT (short-term) — Failed breakout on declining volume indicates weakness and a potential reversal short.
**Factors:** 20/50-day EMA crossover; RSI(14) momentum; Volume-Weighted Average Price (VWAP); Bollinger Band squeeze/expansion; Sector relative strength
**Data points:** 1-minute OHLCV for VWAP calculation; Real-time RSI(14) and MACD(12,26,9); Pre-market and opening auction volume data; Sector ETF flows (XLK, XLF, XLV); Key support/resistance level order book depth
**Swing:** Enter on a pullback to the 20-day EMA with strong volume confirmation; exit on a break below the 50-day EMA or RSI(14) exceeding 70.
**Short-term:** Enter on a 1-minute breakout above VWAP with high relative volume for longs; exit at the next significant resistance level or if price reclaims VWAP to the downside.

### devstral-small-2 — _code-patches (Mistral)_
**Top picks:**
- **SPY** LONG (swing) — Strong momentum with WR above 50% and PF > 1.5
- **QQQ** LONG (swing) — Tech sector resilience and positive sector rotation
- **IWM** SHORT (short-term) — Weak relative performance and high volatility
**Factors:** momentum; relative strength; volatility; sector rotation; price action
**Data points:** SPY 20-day moving average; QQQ sector performance; IWM volume spikes; VIX index; market breadth indicators
**Swing:** Enter on breakout above 20-day MA with volume confirmation; exit on reversal below 5-day MA or when WR drops below 50%.
**Short-term:** Trade pullbacks to 5-day MA with tight stops; exit on VIX spikes or negative news flow.

### ernie-coder — _thinking (Baidu)_
**Top picks:**
- **AAPL** LONG (swing) — RSI <30 with bullish price structure above 20-day MA
- **MSFT** LONG (short-term) — MACD crossover with volume spike >1.5x avg
- **TSLA** SHORT (swing) — Price near 52-week low with negative RSI <30
**Factors:** RSI; MACD; Volume Spike; Moving Average Cross; ATR Volatility
**Data points:** Price (1m); Volume (5m); RSI (14); MA(20/50); ATR (14)
**Swing:** Enter long when price crosses above RSI 40 and volume spikes >1.2x avg daily, exit if RSI >65 or MA(20) < MA(50)
**Short-term:** Enter short when price breaks below RSI 35 with bearish MACD crossover, exit if price >2% above entry or RSI >70

### gemma3:4b — _compact (Google)_
**Top picks:**
- **SPY** LONG (swing) — SPY's historical performance and current relative strength suggest a continuation of the upward trend.
- **QQQ** LONG (short-term) — Technology sector (QQQ) is exhibiting strong momentum and is expected to outperform.
- **NVDA** LONG (swing) — Nvidia's leadership in AI and strong earnings potential justify a long position.
**Factors:** Relative Strength Index (RSI); Moving Average Convergence Divergence (MACD); 50-day Simple Moving Average (SMA); Advance-Decline Line; Volatility Index (VIX)
**Data points:** SPY 50-day SMA; QQQ 50-day SMA; NVDA Trading Volume; SPY Beta; VIX 30-day
**Swing:** We'll initiate long positions on SPY and QQQ when the 50-day SMA crosses above the 200-day SMA, coupled with positive MACD signals, indicating a sustained trend. Exits will be triggered by a break below the 50-day SMA or a significant increase in the VIX.
**Short-term:** For 1-3 day trades, we'll focus on high-probability breakout setups around key support and resistance levels, utilizing RSI and volume confirmation. Entries will be taken on a 3:1 risk-reward ratio, and exits will be set based on stop-loss orders placed just below recent swing lows or above recent swing highs.

### glm-4.6:cloud — _GLM-4.6 (Ollama Cloud)_
**Top picks:**
- **SPY** LONG (swing) — S&P 500 showing bullish momentum with support at 50-day moving average and positive MACD crossover
- **NVDA** LONG (swing) — Semiconductor leader breaking out of consolidation with increasing volume and relative strength vs. sector
- **TSLA** SHORT (short-term) — Overextended above 200-day moving average with bearish divergence on RSI and declining volume
**Factors:** Price momentum; Volume patterns; Moving average crossovers; RSI divergence; Relative strength vs. sector
**Data points:** Daily OHLCV data; Intraday volume profile; Options flow data; Institutional ownership changes; Earnings surprise data
**Swing:** Enter on confirmed breakout above resistance with volume confirmation, exit when price closes below 20-day EMA or when RSI reaches overbought levels above 70.
**Short-term:** Enter on mean reversion signals when price deviates more than 2 standard deviations from 5-day moving average, exit when price returns to mean or after 2-3 trading days.

### gpt-oss:120b-cloud — _GPT-OSS 120B (Ollama Cloud)_
**Top picks:**
- **SPY** LONG (swing) — Broad market rally supported by strong earnings season and positive CPI surprise.
- **AAPL** SHORT (short-term) — Overbought on daily RSI and weakening relative strength versus the Nasdaq index.
- **TSLA** LONG (short-term) — Momentum breakout above 20‑day EMA with rising institutional buying.
**Factors:** Relative Strength Index (RSI); Moving Average Convergence Divergence (MACD); Volume Weighted Average Price (VWAP); Earnings surprise vs. consensus; Short interest ratio
**Data points:** Intraday price and volume bars (1‑min); Latest earnings release and surprise magnitude; Analyst consensus rating changes; Institutional ownership and net flow data; Short interest and days‑to‑cover
**Swing:** Enter on a pullback to the 20‑day EMA when MACD histogram turns positive and RSI is below 70; target the 50‑day EMA or a 5‑10% upside, stop below the recent swing low.
**Short-term:** Take a 1‑3 day position when price breaks above VWAP with volume > 2× average, confirming with a bullish MACD cross; set a tight stop 1% below entry and exit at a 2‑4% profit or on reversal signal.

### grok-4-latest — _Grok-4 (X_AI)_
**Top picks:**
- **AAPL** LONG (swing) — Strong quarterly earnings and positive RSI momentum indicate potential for upward trend continuation.
- **TSLA** SHORT (short-term) — Overbought conditions and weakening EV sector sentiment suggest a near-term pullback.
- **SPY** LONG (swing) — Broad market recovery supported by favorable economic data and low volatility points to sustained gains.
**Factors:** Moving Average Convergence Divergence (MACD); Relative Strength Index (RSI); Trading Volume; Earnings Per Share (EPS) Growth; Market Sentiment Index
**Data points:** Real-time intraday price feeds; Historical volatility metrics; Options implied volatility; Economic calendar events; Sector performance indices
**Swing:** For swing trades in equities, enter on confirmed breakouts above key resistance levels with supporting volume and MACD crossover, then exit on hitting a predefined profit target or trailing stop-loss based on ATR multiples.
**Short-term:** For 1-3 day trades, enter on intraday momentum signals like RSI divergences or candlestick patterns during high-volume sessions, and exit at the end of the day or upon reaching a tight stop-loss to capture quick gains.

### kimi-k2-thinking:cloud — _Moonshot Kimi K2 Thinking (Ollama Cloud)_
**Top picks:**
- **SPY** LONG (swing) — Stable regime with PF>1.5 favors trend continuation, SPY holding above 50-day EMA with improving breadth
- **QQQ** LONG (swing) — Tech sector relative strength and momentum above 20-day EMA, AI/semiconductor tailwinds
- **IWM** LONG (short-term) — Small-cap potential catch-up trade with risk appetite improving and volume accumulation
**Factors:** RSI(14) momentum; ATR(14) volatility sizing; 20/50-day EMA crossover; Volume profile POC; Put/Call ratio sentiment
**Data points:** Real-time SIP consolidated tape; Dark pool ATS prints; Options order flow (unusual activity); Sector ETF flow data; Short interest change feeds
**Swing:** Enter on pullback to 20-day EMA with RSI(14)>50 and rising volume, exit on daily close below 50-day EMA or 2x ATR profit target
**Short-term:** Enter on intraday VWAP breakout with 1.5x average volume confirmation, exit on opposite signal or 1.5x ATR target within 3-day max hold

### mercury-2 — _Mercury 2 (Inception)_
**Top picks:**
- **SPY** LONG (swing) — Strong earnings growth and bullish momentum on the S&P 500
- **QQQ** SHORT (short-term) — Tech valuation compression and weakening MACD divergence
- **AAPL** LONG (swing) — Robust product pipeline and positive earnings surprise
**Factors:** Relative Strength Index (RSI); Moving Average Convergence Divergence (MACD); Earnings Surprise; Analyst Sentiment; Volatility (ATR)
**Data points:** Real-time price and volume; Earnings calendar; Analyst rating changes; Economic calendar (GDP, CPI); Option implied volatility
**Swing:** Enter long on SPY when price closes above the 50‑day EMA with RSI >55 and MACD bullish crossover; exit near 10‑day EMA or when RSI exceeds 70.
**Short-term:** Short QQQ on a pull‑back below the 20‑day EMA with MACD negative divergence and RSI <45; cover within 1‑3 days if price re‑claims the EMA.

### moonshot-v1-32k — _Kimi K2 (Moonshot REST)_
**Top picks:**
- **SPY** LONG (swing) — S&P 500 ETF, expected to benefit from the current economic recovery.
- **AAPL** LONG (swing) — Strong Q1 earnings and increasing demand for tech products.
- **ZC=F** SHORT (short-term) — Corn futures may face selling pressure due to increased supply.
**Factors:** Relative Strength Index (RSI); Moving Average Convergence Divergence (MACD); Volume Weighted Average Price (VWAP)
**Data points:** Historical price data; Economic indicators; Company earnings reports; Volume and liquidity metrics; Market sentiment analysis
**Swing:** Enter on a breakout above the 50-day moving average with a stop loss below the 200-day moving average. Exit on a close below the 50-day moving average or when a target profit level is reached.
**Short-term:** Enter on a strong bullish candlestick pattern with a tight stop loss. Exit on the next day if the price fails to move in the anticipated direction or if a profit target is met.

### qwen2.5-coder:14b — _code-specialist (Alibaba)_
**Top picks:**
- **SPY** LONG (swing) — Strong upward momentum and positive MACD crossover.
- **AAPL** SHORT (short-term) — Overbought conditions on RSI and potential resistance break.
- **GOOGL** LONG (swing) — Positive earnings estimates and rising stock price.
**Factors:** MACD; RSI; Moving Averages; Earnings Estimates; Sentiment Analysis
**Data points:** Price History; Volume; Technical Indicators; News Sentiment; Earnings Calendar
**Swing:** Enter long positions on MACD crossovers above zero and exit when the price hits a moving average. For short positions, enter when RSI exceeds 70 and exit on a crossover below zero.
**Short-term:** Buy dips where RSI falls below 30 and sell when it spikes above 80. Use volume as a confirmation tool for entry and exit points.

### qwen3-coder:480b-cloud — _Qwen3 Coder 480B (Ollama Cloud)_
**Top picks:**
- **SPY** LONG (swing) — Strong momentum with rising volume confirming breakout above key resistance
- **NVDA** LONG (swing) — AI chip demand surge with strong institutional accumulation and earnings beat guidance
- **TSLA** SHORT (short-term) — Technical breakdown below support with increasing bearish sentiment and valuation concerns
**Factors:** RSI(14); Volume Trend; MACD Histogram; Institutional Flow; Earnings Revision Momentum
**Data points:** Real-time order book depth; Intraday volume profile; Key technical support/resistance levels; Pre-market futures movement; Sector correlation coefficients
**Swing:** Enter on confirmed breakout/reversal pattern with volume confirmation, hold for 3-10 days with trailing stop at recent swing low/high for long/short positions respectively.
**Short-term:** Trade mean reversion in oversold/overbought conditions (RSI < 30 or > 70) with tight stops, exit on momentum exhaustion or opposite signal within 1-3 sessions.

## FOREX

### deepseek-r1:14b — _reasoning (DeepSeek)_
**Top picks:**
- **EURUSD** SHORT (swing) — Weak euro due to ECB policy divergence.
- **GBPUSD** LONG (short-term) — Potential BOE rate hike expectations.
- **USDJPY** SHORT (swing) — Strong yen due to safe-haven demand.
**Factors:** volatility; momentum; trend strength; economic indicators; risk sentiment
**Data points:** CCI (Commodity Channel Index); ADX (Average Directional Index); central bank interest rates; VIX index; economic news calendar
**Swing:** Enter on support/resistance levels with stop losses, exit at key trend reversals or target price levels.
**Short-term:** Entry based on intraday volatility and momentum indicators like RSI or MACD, exit on reversal patterns or time-based stops.

### deepseek-v3.1:671b-cloud — _DeepSeek V3.1 671B (Ollama Cloud)_
**Top picks:**
- **USDJPY** LONG (swing) — Persistent interest rate differential favoring the USD over the JPY supports a long bias.
- **AUDUSD** SHORT (swing) — Dovish RBA outlook and weaker commodity demand pressures the Aussie against a strong USD.
- **EURGBP** SHORT (short-term) — Relative monetary policy divergence with the ECB expected to cut rates before the BoE.
**Factors:** Interest Rate Differentials; Relative Strength Index (RSI); 200-Day Moving Average Confluence; Commitment of Traders (COT) Report Positioning; FX Volatility Index (VIX)
**Data points:** Real-time Central Bank Rate Expectations (OIS); Live Spot Price and RSI(14); Daily Closing Price vs. 200D MA; Weekly CFTC COT Report (Net Spec Positions); DXY (US Dollar Index) Spot Price
**Swing:** Enter on a pullback to a key moving average or support/resistance level confirmed by RSI divergence; exit on a reach of the next significant resistance/support level or a fundamental shift in central bank rhetoric.
**Short-term:** Enter on a breakout of the Asian or London session range with high volume; exit with a 1:1.5 risk-reward ratio or at the end of the US session to avoid overnight risk.

### devstral-small-2 — _code-patches (Mistral)_
**Top picks:**
- **EURUSD** SHORT (swing) — Stressed market conditions favor safe-haven USD strength against EUR.
- **GBPUSD** SHORT (short-term) — UK economic uncertainty supports USD outperformance.
- **USDJPY** LONG (swing) — Risk-off sentiment drives yen weakness despite carry trade unwind.
**Factors:** VIX (volatility index); USD index strength; carry trade positions; central bank policy divergence; commodity currency correlations
**Data points:** 10-day RSI for EURUSD/GBPUSD; COT report for USDJPY; 5-day moving average convergence; VIX futures term structure; ECB/Fed policy meeting minutes
**Swing:** Enter on RSI <30 for EURUSD/GBPUSD shorts, exit on RSI >50 or USD index reversal. For USDJPY long, enter on carry trade unwind signals, exit on VIX spike >30.
**Short-term:** Trade GBPUSD short on 1-3 day timeframe using 5-day MA crossovers, exit on MACD bearish divergence. Avoid trades during high-impact news events.

### gemma3:4b — _compact (Google)_
**Top picks:**
- **EURUSD** SHORT (swing) — Current stressed status and high WR suggest a potential bearish trend continuation.
- **GBPUSD** SHORT (short-term) — GBPUSD exhibiting strong negative momentum and high volatility, presenting a short opportunity.
- **USDJPY** SHORT (swing) — USDJPY's recent performance and high WR indicate a potential for further downside movement.
**Factors:** Average Directional Index (ADX); Moving Average Convergence Divergence (MACD); Relative Strength Index (RSI); Fractals; Commitment of Traders (COT) Report
**Data points:** EURUSD 1-hour candlestick data (Open, High, Low, Close); GBPUSD 4-hour candlestick data (Open, High, Low, Close); USDJPY 15-minute candlestick data (Open, High, Low, Close); US Dollar Index (DXY) 1-hour data; German ZEW Economic Sentiment Index
**Swing:** Swing trades would be initiated upon confirmation of a breach of the 20-period moving average with a stop-loss placed just below the recent swing low. Exit would occur upon a retest of the moving average as support or a significant price increase.
**Short-term:** Short-term trades (1-3 days) would focus on breakout patterns following high-volume candle formations, utilizing a tight stop-loss just below the entry point. Exit would be triggered by a reversal candlestick pattern or a target reached based on Fibonacci extensions.

### glm-4.6:cloud — _GLM-4.6 (Ollama Cloud)_
**Top picks:**
- **EURUSD** SHORT (swing) — ECB maintaining dovish stance while Fed remains hawkish creating bearish pressure
- **USDJPY** LONG (short-term) — Bank of Japan intervention concerns limiting yen strength despite risk-off sentiment
- **GBPUSD** SHORT (swing) — UK economic data weakening while BOE signals potential rate cuts
**Factors:** interest rate differentials; RSI divergence; 200-day moving average position; volatility expansion; commitment of traders report
**Data points:** central bank policy statements; CPI inflation data; non-farm payrolls; commitment of traders report; overnight index swap rates
**Swing:** Enter on 4-hour timeframe when price closes below 21 EMA with RSI below 50, exit when RSI crosses above 70 or price closes above 50 SMA
**Short-term:** Enter on 15-minute chart during London/NY session overlap when price breaks 20-period Bollinger Band with volume spike, exit at 1:2 risk/reward or session close

### gpt-oss:120b-cloud — _GPT-OSS 120B (Ollama Cloud)_
**Top picks:**
- **EURUSD** SHORT (swing) — Euro weakness from ECB dovish stance versus strong US data
- **USDJPY** LONG (short-term) — Safe‑haven demand for USD and yen carry‑trade unwind
- **GBPUSD** SHORT (short-term) — UK inflation surprise and weaker pound outlook
**Factors:** Interest rate differential (Fed vs ECB/BOE); MACD histogram; Relative Strength Index (RSI); COT positioning (net long/short); Implied volatility (FX options)
**Data points:** Real-time 1H and 4H OHLCV for each pair; Central bank policy rate announcements calendar; US Non‑Farm Payrolls and PMI releases; COT reports for major dealers; FX options implied volatility surface
**Swing:** Enter on a 4‑hour MACD bullish/bearish crossover that aligns with a break of the prevailing trendline and RSI confirming overbought or oversold; target a 2:1 reward‑to‑risk or the next major support/resistance level.
**Short-term:** Enter on a 1‑hour RSI extreme bounce (≤30 for long, ≥70 for short) with price holding above/below the 20‑period EMA; exit at the opposite EMA cross or after 1‑3 days if the pair reverts toward the daily pivot.

### grok-4-latest — _Grok-4 (X_AI)_
**Top picks:**
- **EURUSD** LONG (swing) — EURUSD shows bullish momentum due to recent ECB policy hints and weakening USD index.
- **GBPUSD** SHORT (short-term) — GBPUSD is overbought on RSI with upcoming UK economic data likely to pressure the pound.
- **USDJPY** LONG (swing) — USDJPY benefits from safe-haven flows amid global uncertainty and positive US yield differentials.
**Factors:** RSI oscillator for overbought/oversold conditions; Moving average crossovers for trend confirmation; Economic calendar events like GDP releases; Interest rate differentials between currencies
**Data points:** Real-time bid/ask prices from forex API; Historical OHLC data for the past 30 days; Upcoming economic indicators from calendars like Forex Factory; Currency correlation matrix
**Swing:** For swing trades in FOREX, enter on confirmed trend reversals using moving average crossovers with RSI above 50 for longs or below for shorts, and exit at predefined profit targets based on Fibonacci extensions or trailing stops after 5-10 days.
**Short-term:** For 1-3 day trades, enter on intraday breakouts supported by volume spikes and MACD signals, exiting at the end of the session or upon hitting a 1:2 risk-reward ratio stop/target.

### mercury-2 — _Mercury 2 (Inception)_
**Top picks:**
- **EURUSD** LONG (swing) — Eurozone CPI easing and positive rate differential support upside
- **USDJPY** SHORT (short-term) — Bank of Japan's ultra-loose stance vs rising US yields creates downward pressure
- **GBPUSD** LONG (swing) — UK wage growth outpacing inflation fuels expectations of rate hikes
**Factors:** Interest rate differential (CIRP); Relative Strength Index (RSI); Moving Average Convergence Divergence (MACD); CPI inflation releases; Central bank policy expectations
**Data points:** Real-time spot price feed; Overnight interest rate spreads (EUR/USD, GBP/USD, USD/JPY); Upcoming macro calendar (CPI, employment); Order flow imbalance data; Implied volatility index (e.g., JP Morgan G7 FX Vol)
**Swing:** Enter on a 20‑day EMA crossover with RSI below 30 for longs or above 70 for shorts, and hold 2‑4 weeks targeting 1‑2% move; exit on opposite EMA cross or RSI reversal.
**Short-term:** Use 4‑hour chart; enter on break of Bollinger Band with MACD histogram turning positive for longs or negative for shorts, hold 1‑3 days and exit at 0.5% profit or when price re‑enters the band.

### moonshot-v1-32k — _Kimi K2 (Moonshot REST)_
**Top picks:**
- **EURUSD** LONG (swing) — Euro is expected to strengthen against the US dollar due to the European Central Bank's hawkish stance and strong economic data.
- **GBPUSD** SHORT (short-term) — GBP is likely to weaken against USD due to Brexit uncertainties and the Bank of England's cautious approach to rate hikes.
- **USDJPY** SHORT (swing) — Japanese yen may appreciate against the US dollar as the Bank of Japan maintains its ultra-accommodative monetary policy, leading to a safe-haven demand for JPY.
**Factors:** Interest rate differentials; Economic indicators (GDP, inflation, employment data); Central bank policy statements; Technical indicators (RSI, MACD, Bollinger Bands); Geopolitical events
**Data points:** Central bank interest rate decisions and meeting minutes; Economic calendar releases (ISM, NFP, GDP, CPI); Currencies' implied volatility (VIX for forex pairs); FX swap rates and carry trades; Technical chart patterns and moving averages
**Swing:** For swing trades, look for entry points near key support/resistance levels and strong economic data releases. Exit positions when the trade reaches the next significant technical level or when economic data suggests a trend reversal.
**Short-term:** For 1-3 day trades, focus on intraday price action and short-term technical indicators. Enter trades on breakouts or pullbacks to key levels, and exit when profit targets are met or if the trade moves against you by a predetermined stop-loss amount.

### qwen2.5-coder:14b — _code-specialist (Alibaba)_
**Top picks:**
- **EURUSD** LONG (swing) — Strong bullish momentum on the EURUSD pair.
- **GBPJPY** SHORT (short-term) — Overbought conditions and potential for a reversal.
- **AUDNZD** LONG (swing) — Support level holding strong, indicating a bullish setup.
**Factors:** Relative Strength Index (RSI); Moving Average Convergence Divergence (MACD); Bollinger Bands; Stochastic Oscillator; Volume
**Data points:** 1-hour candlestick data; 4-hour candlestick data; Daily candlestick data; Weekly candlestick data; Intraday volume data
**Swing:** Enter long positions when the price closes above a rising trendline and RSI is below 70. Exit on a close below the trendline or when RSI reaches overbought levels.
**Short-term:** Look for breakouts above resistance levels with high volume to enter short-term trades. Exit on a close below the breakout level or after 1-3 days.

### qwen3-coder:480b-cloud — _Qwen3 Coder 480B (Ollama Cloud)_
**Top picks:**
- **EURUSD** SHORT (swing) — Dollar strength amid Fed rate hike expectations and ECB dovish pivot pressure
- **GBPJPY** LONG (short-term) — Yen weakness against majors with BoJ policy divergence supporting upside
- **AUDUSD** SHORT (swing) — RBA hawkish pause amid China demand concerns weighing on Aussie
**Factors:** relative central bank policy divergence; real interest rate differentials; risk sentiment flows
**Data points:** Fed speech calendar and tone analysis; ECB meeting minutes sentiment scoring; DXY index momentum and support levels
**Swing:** Enter on multi-day trend continuation after key moving average breaks with RSI confirmation, target 2% move with 1% stop loss based on recent volatility clusters
**Short-term:** Trade intraday breakouts from consolidation patterns with volume confirmation, holding 1-3 days targeting 0.8-1.2% moves with tight stops at previous day's extremes

## COMMODITY

### deepseek-r1:14b — _reasoning (DeepSeek)_
**Top picks:**
- **ZC=F** LONG (swing) — Geopolitical tensions in energy markets may drive prices higher.
- **GC=F** LONG (swing) — Safe-haven demand amid central bank policy uncertainty.
- **BTCUSDT** SHORT (short-term) — Potential mean-reversion after recent rally; high volatility expected.
**Factors:** RSI (Momentum); MACD (Trend Strength); Volume Confirmation; Support/Resistance Levels; News Sentiment Impact
**Data points:** Brent Crude Futures Prices; Gold Spot Price; Bitcoin Index; Energy Market News Feeds; Macroeconomic Indicators (CPI, GDP)
**Swing:** Enter on a confirmed break of resistance with RSI <70 and MACD bullish; exit on failure to hold support or bearish divergence.
**Short-term:** Intraday entries based on EMA crossovers and high volume; exit on stop loss or reversal signals within the day.

### deepseek-v3.1:671b-cloud — _DeepSeek V3.1 671B (Ollama Cloud)_
**Top picks:**
- **CL=F** LONG (swing) — Strong uptrend with recent breakout above key resistance on rising open interest.
- **ZC=F** SHORT (short-term) — Breakdown from a bear flag pattern suggests continuation of the primary downtrend.
- **HG=F** LONG (swing) — Oversold RSI bouncing from a major support level amid tightening physical supply.
**Factors:** RSI (14-period); Open Interest change; 20/50-day EMA confluence; Commitment of Traders (COT) net positioning; Inter-commodity spread strength
**Data points:** Real-time futures term structure (roll yields); 1-hour volume profile; Current day's high/low for key pivot levels; Settlement price from previous session; Macro calendar for today's key events (e.g., CPI, inventory reports)
**Swing:** Enter on a daily close confirming the breakout/breakdown of a key technical level, using the 20-day EMA as a dynamic exit for momentum trades.
**Short-term:** Enter on a 1-hour candle close with high volume exceeding the prior session's ATR, targeting the previous day's high/low for a quick scalp exit.

### devstral-small-2 — _code-patches (Mistral)_
**Top picks:**
- **BTCUSDT** LONG (swing) — Strong momentum with WR above 60% and positive PF in crypto markets.
- **ZC=F** SHORT (short-term) — Weak relative performance in grains sector with declining WR.
- **EURUSD** LONG (swing) — Carry trade opportunity with positive interest rate differentials.
**Factors:** momentum (WR); performance (PF); sector relative strength; volatility; liquidity
**Data points:** 20-day moving average convergence; order book depth; open interest changes; macro economic indicators; technical indicators (RSI, MACD)
**Swing:** Enter on breakout above 20-day MA with volume confirmation, exit on RSI >70 or trend reversal signal.
**Short-term:** Trade mean reversion around key moving averages, exit within 3 days on profit target or stop-loss.

### gemma3:4b — _compact (Google)_
**Top picks:**
- **ZCL=F** LONG (swing) — Recent price action suggests a potential breakout above key resistance levels.
- **GC=F** SHORT (short-term) — Elevated gold prices coupled with rising interest rates present a bearish outlook.
- **CL=F** LONG (swing) — Crude oil inventories are expected to decline, supporting upward price momentum.
**Factors:** Commitment of Traders (COT) Report; Weather Patterns (US Drought Index); Interest Rate Expectations (Federal Funds Rate); Geopolitical Risk Index; Inventory Levels (DOE Weekly Report)
**Data points:** CFTC Commitments of Traders Report (1-week and 1-month); US Drought Monitor Index; Federal Reserve Economic Data (FRED) - Federal Funds Rate; Reuters Geopolitical Risk Index; US Energy Information Administration (EIA) Weekly Short-Term Energy Outlook
**Swing:** We'll initiate long positions on commodities exhibiting bullish signals from the COT report and EIA outlook, targeting entry around key resistance levels identified through technical analysis. Exits will be triggered by a break below support levels or a significant reversal in momentum.
**Short-term:** For 1-3 day trades, we'll focus on short-term momentum trades based on daily price action and short-term indicators like RSI and MACD. Entries will be taken on breakouts above moving averages, while exits will be set at predetermined stop-loss levels or during trend reversals.

### glm-4.6:cloud — _GLM-4.6 (Ollama Cloud)_
**Top picks:**
- **GC=F** LONG (swing) — Safe-haven demand amid geopolitical tensions and inflation concerns
- **CL=F** SHORT (short-term) — Demand slowdown concerns and OPEC+ production increases
- **NG=F** LONG (swing) — Seasonal demand increase and lower-than-average inventory levels
**Factors:** Seasonal patterns; Supply/demand fundamentals; Inventory levels; Currency correlation (USD strength); Weather patterns
**Data points:** COT reports; Weekly inventory data; Production/consumption statistics; Weather forecasts; USD index correlation
**Swing:** Enter on seasonal trend confirmation with inventory support, exit when fundamentals reverse or target seasonal peak
**Short-term:** Enter on technical breakouts with volume confirmation, exit at next key support/resistance level or on momentum divergence

### gpt-oss:120b-cloud — _GPT-OSS 120B (Ollama Cloud)_
**Top picks:**
- **CL=F** LONG (swing) — Oil prices are above the 20‑day EMA, inventory draws are accelerating and the USD index is weakening, supporting a multi‑week uptrend.
- **GC=F** SHORT (short-term) — Real yields have risen sharply, gold is below its 50‑day SMA and COT data shows increasing short positioning.
- **ZC=F** LONG (swing) — Corn stocks are at multi‑year lows and planting progress is ahead of schedule, driving bullish fundamentals.
**Factors:** 20‑day EMA / 50‑day SMA crossover; Relative Strength Index (RSI) on 14 periods; Commitments of Traders (COT) net positioning; Key inventory reports (EIA, USDA); USD Index correlation
**Data points:** Live futures price and volume for each symbol; Open interest and net long/short COT data; Latest EIA crude oil inventory and USDA corn stock reports; USD Index (DXY) level; Economic calendar events (GDP, PMI, Fed minutes) affecting risk sentiment
**Swing:** Enter on a break above the 20‑day EMA with RSI > 55 and confirming bullish COT net longs; set a profit target at 8‑10% or the next major resistance and a trailing stop 3% below the entry high.
**Short-term:** Enter on a 4‑hour RSI crossing 70 (overbought) for shorts or 30 (oversold) for longs, with price failing to hold the 20‑day SMA; exit after 1‑3 days or when RSI re‑enters the 40‑60 band.

### grok-4-latest — _Grok-4 (X_AI)_
**Top picks:**
- **GC=F** LONG (swing) — Geopolitical tensions and inflation concerns are boosting demand for gold as a safe-haven asset.
- **CL=F** SHORT (short-term) — Oversupply from increased production and weakening global demand signals a downward price pressure.
- **ZC=F** LONG (swing) — Favorable weather forecasts and rising export demand are supporting higher corn prices.
**Factors:** Moving Average Crossovers; RSI Momentum; Volume Trends; Supply/Demand Fundamentals; USD Strength Correlation
**Data points:** CFTC Commitment of Traders Report; EIA Weekly Inventory Data; USD Index Live Feed; Geopolitical News Alerts; Weather Pattern Forecasts
**Swing:** For swing trades in commodities, enter on confirmed trend reversals using moving average crossovers and positive divergence in RSI, with exits triggered by trailing stops or when prices hit predefined Fibonacci retracement levels over 1-4 weeks.
**Short-term:** In short-term commodity trades, enter on intraday breakouts supported by high volume and momentum indicators like MACD, exiting at the end of the session or upon reaching a 1-2% profit target within 1-3 days to capture quick volatility swings.

### kimi-k2-thinking:cloud — _Moonshot Kimi K2 Thinking (Ollama Cloud)_
**Top picks:**
- **GC=F** LONG (swing) — Strong momentum above 20-week MA with backwardated curve signaling supply tightness
- **CL=F** SHORT (short-term) — Mean reversion signal after 3-week rally into resistance with rising inventory builds
- **NG=F** LONG (swing) — Seasonal pattern alignment with early summer cooling demand and low storage levels
**Factors:** 12-week price momentum; Term structure slope (backwardation/contango); COT net speculator positioning; Inventory deviation from seasonal norm; DXY inverse correlation
**Data points:** Real-time futures tick data; CFTC COT weekly report; EIA/DOE inventory statistics; USD index spot price; CVOL commodity volatility index
**Swing:** Enter on momentum breakout confirmed by term structure backwardation; exit when price closes below 20-period MA or contango develops signaling oversupply.
**Short-term:** Fade extreme intraday moves when inventory data surprises against trend; use 1.5x ATR stop-loss and target 2:1 reward/risk within 3 sessions.

### mercury-2 — _Mercury 2 (Inception)_
**Top picks:**
- **GC=F** LONG (swing) — Gold is gaining as real‑interest‑rate expectations rise and inflation remains sticky.
- **CL=F** SHORT (short-term) — Crude oil inventories are at multi‑year highs, signaling oversupply.
- **HG=F** LONG (swing) — Copper demand from China is accelerating while supply constraints tighten.
**Factors:** COT Commitment of Traders; Relative Strength Index (RSI); MACD; US CPI YoY; EIA Inventory Reports
**Data points:** EIA Weekly Petroleum Status Report; COT Futures Positions; US CPI YoY; Gold Spot Price; Copper Industrial Production Index
**Swing:** Enter on a breakout above the 50‑day SMA with RSI > 55 and MACD bullish crossover; exit near the 20‑day SMA or on a bearish divergence.
**Short-term:** Use intraday 15‑min charts; go short CL=F when price falls below the 1‑hour VWAP with RSI < 40, and cover at the next resistance level or if inventory data shows a drawdown.

### moonshot-v1-32k — _Kimi K2 (Moonshot REST)_
**Top picks:**
- **GC=F** LONG (swing) — Gold is historically seen as a safe-haven asset during economic uncertainty.
- **CL=F** SHORT (short-term) — Oil prices are expected to decrease due to global economic slowdown affecting demand.
- **ZC=F** LONG (swing) — Corn futures may benefit from increased demand for biofuels and food security concerns.
**Factors:** Commodity Futures Trading Commission Commitments of Traders Report; Moving Average Convergence Divergence (MACD); Relative Strength Index (RSI); Commodity Channel Index (CCI); Volume Weighted Average Price (VWAP)
**Data points:** Global economic indicators; Supply and demand reports; Weather forecasts; Geopolitical news; Technical indicators
**Swing:** For swing trades, look for a breakout above the 50-day moving average or a bounce off the 200-day moving average as entry points, with exits on a close below the 50-day moving average or upon reaching a predefined profit target.
**Short-term:** For short-term trades, use intraday momentum indicators to enter on strength or weakness, with exits set at key technical levels or at the end of the trading day to limit risk.

### qwen2.5-coder:14b — _code-specialist (Alibaba)_
**Top picks:**
- **ZC=F** LONG (swing) — Strong bullish momentum in corn futures.
- **CL=F** SHORT (short-term) — Overbought conditions and potential supply concerns.
- **GC=F** LONG (swing) — Gold prices supported by inflation expectations.
**Factors:** Relative Strength Index (RSI); Moving Average Convergence Divergence (MACD); Bullish/Bearish Spread; Volatility Index; Sentiment Analysis
**Data points:** Price Action; Volume; Open Interest; Technical Indicators; Economic News
**Swing:** Enter long positions when the price crosses above a rising trendline and RSI is below 70. Exit on a pullback to the trendline or when RSI reaches overbought levels.
**Short-term:** Go short when MACD line crosses below the signal line and price action shows a bearish candlestick pattern. Close positions on a bullish reversal or after a small profit is secured.

### qwen3-coder:480b-cloud — _Qwen3 Coder 480B (Ollama Cloud)_
**Top picks:**
- **GC=F** LONG (swing) — Gold breaking above key resistance with strong volume confirmation and positive sentiment amid inflation concerns
- **CL=F** SHORT (short-term) — Crude oil showing bearish divergence with lower highs despite geopolitical tensions, indicating distribution phase
- **SI=F** LONG (swing) — Silver exhibiting strong relative strength against gold with increasing open interest and technical breakout
**Factors:** price momentum; volume confirmation; sentiment indicators; seasonal patterns; carry cost analysis
**Data points:** COT reports for commercial positioning; inventory levels from government sources; volatility term structure; real interest rate differentials; geopolitical risk indices
**Swing:** Enter on breakout above 20-day high with volume confirmation, target 2-3% move based on average true range, exit on 5-day low penetration or when momentum diverges
**Short-term:** Trade 1-3 day reversals around key support/resistance levels with intraday momentum filters, exit on opposite signal or when price exceeds daily volatility range

### qwen3:14b — _Qwen3 general (Alibaba)_
**Top picks:**
- **CL=F** LONG (swing) — Bullish momentum from supply disruptions and rising inflation expectations
- **GC=F** LONG (swing) — Safe-haven demand amid geopolitical tensions and weak USD
- **HG=F** LONG (short-term) — Industrial demand recovery and tight global copper inventories
**Factors:** Supply-demand imbalance; Geopolitical risk index; Inflation rate; USD strength; Seasonal trends
**Data points:** EIA crude oil inventory report; World Bank commodity price index; CPI data; USD index (DXY); Copper mine production data
**Swing:** Enter long on breakout above 50-day EMA with confirmation from positive sentiment and strong USD; exit on stop-loss below key support or take profit at projected resistance levels.
**Short-term:** Use RSI divergence and MACD crossover for entry; exit after 1-3 days on stop-loss or take profit near immediate resistance with closing below 200-day EMA.

## ETF

### deepseek-r1:14b — _reasoning (DeepSeek)_
**Top picks:**
- **SPY** LONG (swing) — Strong momentum in US equities
- **QQQ** LONG (swing) — Tech sector outperformance expected
- **XLF** SHORT (short-term) — Potential rotation from financials
**Factors:** MACD; RSI; Bollinger Bands; 50-day MA; 200-day MA
**Data points:** S&P 500 index (SPX); Nasdaq-100 (NDX); VIX volatility index; Fed Fund rate; Sector performance indicators
**Swing:** Enter on confirmed bullish MACD crossover with RSI below 70 for oversell signal; exit on bearish MACD or resistance at upper Bollinger Band.
**Short-term:** Enter on Bollinger Band squeeze with volume spike; exit on break of trend line support or resistance.

### deepseek-v3.1:671b-cloud — _DeepSeek V3.1 671B (Ollama Cloud)_
**Top picks:**
- **SPY** LONG (swing) — Strong win rate and profit factor suggest a stable uptrend favoring long bias on broad market ETFs.
- **QQQ** LONG (swing) — Momentum and risk-on sentiment typically benefit tech-heavy ETFs in a stable bullish regime.
- **TLT** SHORT (short-term) — Anticipating rising yields to pressure long-duration bonds as the stable trend allows for tactical shorts.
**Factors:** RSI (14-period); 20-day Simple Moving Average convergence; Average Directional Index (ADX); Volume profile (VWAP); Sector rotation flows
**Data points:** Real-time RSI(14) for overbought/oversold levels; 1-hour and daily candle closes vs 20 SMA; 14-period ADX for trend strength; Volume 20-day average comparison; US 10-Year Treasury Yield (^TNX)
**Swing:** Enter LONG on a pullback to the 20-day SMA with RSI(14) < 45, exit on RSI(14) > 70 or a close below the 20-day SMA.
**Short-term:** Enter on a 1-hour RSI(14) divergence with price, targeting a 2:1 reward/risk ratio, and exit at the previous session's high/low.

### devstral-small-2 — _code-patches (Mistral)_
**Top picks:**
- **SPY** LONG (swing) — Strong momentum and positive trend in US equities
- **GLD** SHORT (short-term) — Overbought conditions and potential pullback in gold
- **QQQ** LONG (swing) — Tech sector resilience and positive earnings outlook
**Factors:** momentum; trend strength; relative strength; volatility; volume
**Data points:** ETF price data; volume trends; moving averages; RSI; MACD
**Swing:** Enter on breakout above resistance with volume confirmation, exit on RSI divergence or moving average crossover.
**Short-term:** Enter on RSI oversold conditions with positive MACD crossover, exit on profit target or stop-loss.

### ernie-coder — _thinking (Baidu)_
**Top picks:**
- **XLF** LONG (swing) — Financial ETF with low PE and high ROE, outperforming sector
- **TLT** SHORT (swing) — Bond ETF with rising rates and declining yields, overbought signal
- **JPM** LONG (short-term) — Bank stock with strong earnings growth, low volatility
**Factors:** PE_ratio; ROE; MACD_histogram; RSI; ATR
**Data points:** last_price; volume; rsi; macd; atr
**Swing:** Enter LONG on MACD crossover with RSI<70; exit if RSI>75 or price < 20-day MA
**Short-term:** Enter SHORT on break of 50-day MA with volume >1.5x avg; exit if price < 20-day MA

### gemma3:4b — _compact (Google)_
**Top picks:**
- **SPY** LONG (swing) — SPY's high win rate suggests a continuation of recent market trends.
- **GLD** LONG (short-term) — Gold's PF indicates potential upside as a safe-haven asset.
- **USAG** LONG (swing) — USAG's strong performance aligns with expectations of continued economic growth.
**Factors:** Relative Strength Index (RSI) on SPY; Moving Average Convergence Divergence (MACD) crossover for GLD; Treasury Yield Curve Slope; VIX (Volatility Index); Commitment of Traders (COT) Report
**Data points:** SPY 30-day moving average; Gold spot price (ZC=F); 10-year Treasury yield; VIX futures contract prices; Weekly CFTC COT report
**Swing:** Enter long positions on SPY when the RSI dips below 30 and the MACD crosses above its signal line, confirming a bullish divergence. Exit long positions when the RSI exceeds 70 or the MACD crosses below its signal line, signaling a potential trend reversal.
**Short-term:** Utilize 1-3 day trades focusing on breakout patterns around key moving averages on SPY and GLD. Entry triggers are based on short-term momentum indicators like stochastic oscillators, with exits set at pre-defined risk-reward ratios (e.g., 1:2).

### gpt-oss:120b-cloud — _GPT-OSS 120B (Ollama Cloud)_
**Top picks:**
- **SPY** LONG (swing) — 20‑day EMA just turned up and RSI is in the 45‑55 range, indicating bullish momentum with room to run.
- **QQQ** LONG (swing) — Tech sector strength and a bullish MACD crossover support further upside over the next 2‑4 weeks.
- **IWM** SHORT (short-term) — Break below the 50‑day SMA with deteriorating small‑cap earnings outlook suggests a near‑term pullback.
**Factors:** 20‑day Exponential Moving Average (EMA); Relative Strength Index (RSI); MACD histogram; ETF net inflow/outflow data; Sector rotation index
**Data points:** Live price and volume for each ETF; EMA and SMA values (20, 50, 200 day); RSI and MACD readings; Daily net inflow/outflow from fund providers; Sector rotation score from Bloomberg
**Swing:** Enter long when price closes above the 20‑day EMA with RSI between 40‑60 and MACD histogram turning positive; set initial stop 2% below entry and target 8‑12% or exit on EMA cross down.
**Short-term:** Enter short on IWM if price breaks below the 50‑day SMA on >2× average volume and RSI falls below 40; exit after a 1.5‑2% gain or if price rebounds above the SMA with a bullish candle.

### grok-4-latest — _Grok-4 (X_AI)_
**Top picks:**
- **SPY** LONG (swing) — SPY shows strong upward momentum with positive economic indicators supporting broad market gains.
- **QQQ** SHORT (short-term) — QQQ is overbought in the tech sector with RSI above 70 indicating potential pullback.
- **GLD** LONG (swing) — GLD benefits from inflation hedges and geopolitical tensions driving gold prices higher.
**Factors:** Moving average crossovers; Relative Strength Index (RSI); Volume trends; Economic indicators like GDP growth; Volatility measures (VIX)
**Data points:** Historical price and volume data from Yahoo Finance; Real-time RSI and MACD indicators from TradingView API; Economic calendar events from Forex Factory; VIX index levels from CBOE; Sector performance metrics from Bloomberg
**Swing:** For swing trades on ETFs, enter long on a breakout above key resistance levels confirmed by increasing volume, and exit on a trailing stop-loss or when price hits a predefined profit target based on Fibonacci extensions.
**Short-term:** For 1-3 day trades, enter based on intraday candlestick patterns like bullish engulfing with momentum confirmation, and exit at the end of the day or on a fixed risk-reward ratio stop to capture quick volatility spikes.

### mercury-2 — _Mercury 2 (Inception)_
**Top picks:**
- **SPY** LONG (swing) — Broad market exposure with strong momentum and positive macro outlook
- **QQQ** LONG (short-term) — Tech sector strength and high relative strength index
- **IWM** SHORT (swing) — Small‑cap momentum weakening and underperformance versus large caps
**Factors:** 20‑day EMA; RSI (14); MACD; Volume Oscillator; VIX
**Data points:** ETF price and volume; Underlying index futures price; Sector rotation index; Economic calendar (CPI, Fed funds); Open interest on ETF options
**Swing:** Enter on a pullback to the 20‑day EMA when RSI is above 50 and MACD shows a bullish crossover; target 5‑8% upside and exit if price falls below the EMA or RSI drops below 45.
**Short-term:** Trade breakouts above the prior day high with volume >1.5× the 10‑day average; set a tight stop 0.5% below entry and a profit target of 1‑2% for a 1‑3 day horizon.

### moonshot-v1-32k — _Kimi K2 (Moonshot REST)_
**Top picks:**
- **SPY** LONG (swing) — Stable market conditions and positive price momentum.
- **QQQ** LONG (swing) — High growth potential in technology sector with strong earnings.
- **XLF** SHORT (short-term) — Sector underperforming due to economic uncertainties.
**Factors:** Relative Strength Index (RSI); Moving Average Convergence Divergence (MACD); Volume Weighted Average Price (VWAP)
**Data points:** Daily trading volume; Recent earnings reports; Sector performance data; Economic indicators; Market sentiment analysis
**Swing:** Enter on a breakout above the 50-day moving average with a stop-loss below the 200-day moving average. Exit on a close below the 50-day moving average or when the MACD shows a bearish crossover.
**Short-term:** Enter on a strong bullish candlestick pattern with a tight stop-loss. Exit on the next day if the price fails to move in the expected direction or if the RSI indicates overbought conditions.

### phi3.5:latest — _compact reasoning (Microsoft)_
**Top picks:**
- **SPY** LONG (swing) — High WR and stable status indicate strong momentum with room for growth.
- **QQQ** LONG (swing) — PF suggests undervaluation relative to historical performance, suitable for swing trading in a bullish market.
- **?** ? (short-term) — ?
**Factors:** Weighted Average Price (WAP); Price/Earnings Ratio (PER); Volume Trend; Market Sentiment Indices; Volatility Measures
**Data points:** Historical WARP vs. current period performance; Current PER compared to historical average and industry benchmarks; Volume trend over the past week/month; Recent changes in investor sentiment as measured by surveys or social media analysis tools; Beta volatility relative to market index
**Swing:** Buy at a WAP that indicates undervaluation and hold until the asset reaches an overbought condition based on PER, then take profits.
**Short-term:** Short sell when sentiment indicators suggest market exhaustion or negative news impacts prices within hours.

### qwen2.5-coder:14b — _code-specialist (Alibaba)_
**Top picks:**
- **SPY** LONG (swing) — Strong upward momentum and positive MACD crossover.
- **BTCUSDT** SHORT (short-term) — Overbought conditions and recent price action suggesting a pullback.
- **EURUSD** LONG (swing) — Support level breakout with increasing volume.
**Factors:** MACD; Relative Strength Index (RSI); Moving Average Convergence Divergence (MACD) Crossover; Bullish/Bearish Spread; Volume
**Data points:** Price; Volume; MACD Line; Signal Line; RSI Value
**Swing:** Enter long positions on SPY and EURUSD when the price breaks above a key resistance level with strong volume. Exit when there is a clear pullback below the moving average or MACD line crosses below the signal line.
**Short-term:** Enter short position on BTCUSDT when RSI reaches overbought levels (above 70) and price action shows signs of weakening momentum. Exit when price dips below the support level or RSI drops significantly.

### qwen3-coder:480b-cloud — _Qwen3 Coder 480B (Ollama Cloud)_
**Top picks:**
- **SPY** LONG (swing) — Strong momentum with improving breadth and above-average volume confirmation
- **QQQ** LONG (short-term) — Tech sector leading with strong relative performance against S&P 500
- **TLT** SHORT (swing) — Rising yield environment pressuring long-duration bonds with bearish moving average crossover
**Factors:** price momentum; relative strength vs benchmark; volume confirmation; moving average alignment; volatility regime
**Data points:** real-time price/volume; market breadth indicators; federal reserve policy signals; VIX levels; sector rotation metrics
**Swing:** Enter on confirmed trend continuation with 20-day MA support and exit on 50-day MA rejection or -2% stop loss, target 5-8% gain
**Short-term:** Enter on intraday momentum breakouts with volume confirmation, exit on opposite momentum signal or end of day if held overnight

### qwen3:14b — _Qwen3 general (Alibaba)_
**Top picks:**
- **SPY** LONG (swing) — Strong positive momentum and low volatility in a stable market environment
- **XLK** LONG (swing) — Technology sector ETF showing relative strength against broader markets
- **EEM** SHORT (short-term) — Emerging markets ETF exhibiting overbought conditions on short-term charts
**Factors:** 50-day moving average crossover; ATR volatility compression; sector rotation momentum; liquidity ratio (volume/position size); macroeconomic surprise index
**Data points:** real-time ETF price and volume; VIX volatility index; sector ETF performance rankings; central bank policy statements; equity risk premium data
**Swing:** Enter long positions when ETF breaks above 50-day SMA with confirmation on RSI(14) < 50 and ATR < 1.5x 20-day average; exit when RSI(14) > 70 or 10% profit target reached.
**Short-term:** Initiate short trades on EEM when 15-minute RSI(9) > 80 and volume spikes 50% above 20-day average; exit on 5% stop loss or 30-period MACD crossover below signal line.

## BOND

### deepseek-r1:14b — _reasoning (DeepSeek)_
**Top picks:**
- **ZN=F** LONG (swing) — Expecting flattening of yield curve due to Fed policy shifts.
- **BZ=** SHORT (short-term) — Potential spread compression in credit markets post-FOMC meeting.
- **HYG** LONG (swing) — Diversified corporate bond exposure for risk-adjusted returns.
**Factors:** yield_curve_slope; credit_spread_levels; volatility_implied; macroeconomic_data_delayed; technical_indicator_macd
**Data points:** 10Y-2Y Treasury yield spread; CDX.NA IG credit spreads; Treasury futures implied volatility; CPI headline month-over-month; unemployment claims weekly report
**Swing:** Enter long on ZN=F when yield curve flattens below -5bp, exit at profit target of +2% or stop loss at -1%. For HYG, enter long during periods of risk-off with RSI <30 and exit at resistance level.
**Short-term:** Trade BZ= intraday using mean reversion strategy; enter short when credit spreads widen above historical median, exit when spread reverts to mean or stop loss triggered.

### deepseek-v3.1:671b-cloud — _DeepSeek V3.1 671B (Ollama Cloud)_
**Top picks:**
- **TLT** LONG (swing) — Long-duration Treasuries are oversold and due for a relief rally as the market reassesses the Fed's rate path.
- **HYG** SHORT (swing) — High yield credit spreads are likely to widen in a thin sample, high uncertainty environment, pressuring prices.
- **ZB=F** LONG (short-term) — 30-Year Treasury Bond futures show bullish RSI divergence on short-term charts, suggesting a brief bounce.
**Factors:** Yield Curve Steepening/Flattening; Credit Spreads (ICE BofA High Yield Index); RSI Divergence on Key Maturities; Fed Funds Futures Implied Probability; Aggregate Bond Fund Flows
**Data points:** 10-Year vs 2-Year Treasury Yield Spread; Daily TRACE Data for HYG Constituents; CFTC 10-Year Treasury Net Speculator Positions; TLT On-Balance Volume (OBV); Next FOMC Meeting Implied Rate Hike Probability
**Swing:** Enter on a close above the 20-day SMA with rising volume for longs, or a close below it for shorts; exit at key resistance/support levels or on a reversal of the yield curve momentum.
**Short-term:** Scalp 1-3 day reversions using 1-hour RSI extremes (<30 for long, >70 for short) against the 50-period EMA, exiting at the mean or on a 5% profit target.

### devstral-small-2 — _code-patches (Mistral)_
**Top picks:**
- **TLT** SHORT (swing) — Rising yields and thinning liquidity in long-duration Treasuries signal downside risk.
- **HYG** SHORT (short-term) — High-yield credit spreads widening amid macro uncertainty.
- **IEF** LONG (swing) — Intermediate Treasuries offer relative stability in volatile market conditions.
**Factors:** yield_curve_slope; credit_spreads; liquidity_metrics; volatility_index; macro_sentiment
**Data points:** 10-year Treasury yield; ICE BofA High Yield Index spread; VIX futures curve; Treasury ETF option implied volatility; Fed Funds Futures
**Swing:** Enter short on TLT when 10-year yield breaks above 4.25% with credit spreads widening; exit on yield retracement below 4.0%.
**Short-term:** Trade HYG short when credit spreads rise 20bps in a day; cover if VIX drops below 18 within 48 hours.

### gemma3:4b — _compact (Google)_
**Top picks:**
- **USG10Y** LONG (swing) — Long exposure to the 10-year Treasury yield, anticipating continued Fed rate hikes and subsequent upward pressure.
- **TLT** LONG (short-term) — Long exposure to the iShares 20+ Year Treasury Bond ETF, capitalizing on the potential for a flight to safety during economic uncertainty.
- **IEI** LONG (swing) — Long exposure to the iShares iBoxx Investment Grade Corporate Bond ETF, leveraging the relative strength of investment-grade bonds.
**Factors:** 10-Year Treasury Yield; Credit Spreads (IG vs. HY); MOVE Index (Volatility); Inflation Expectations (5yr TIPS); GDP Growth Rate
**Data points:** 10-Year Treasury Yield (FRED); Investment Grade Corporate Bond Yields (ICE BofA Index); MOVE Index (Bloomberg); 5-Year Treasury Inflation-Protected Securities (TIPS) Real Yield (FRED); Advance GDP Release (Bureau of Economic Analysis)
**Swing:** Enter long positions when the 10-year Treasury yield demonstrates a sustained upward trend, confirmed by positive GDP growth and decreasing credit spreads. Exit long positions when the yield declines significantly or when credit spreads widen, signaling increased risk aversion.
**Short-term:** Utilize a 1-3 day trading strategy, entering long positions on pullbacks within established uptrends, validated by a decrease in MOVE index volatility and positive GDP data. Exit short-term trades based on a break of key support levels or a reversal in the MOVE index.

### glm-4.6:cloud — _GLM-4.6 (Ollama Cloud)_
**Top picks:**
- **TLT** LONG (swing) — Yield curve inversion suggests potential Fed rate cuts, benefiting long-duration bonds
- **ZB** SHORT (short-term) — Rising inflation expectations may pressure long-term yields higher
- **SHY** LONG (swing) — Short-term Treasuries offer safety with Fed likely maintaining higher rates longer
**Factors:** Yield curve slope (10Y-2Y spread); Fed funds rate expectations; CPI inflation trends; Real yield differentials; Duration exposure
**Data points:** Treasury yield curve (2Y, 5Y, 10Y, 30Y); Fed funds futures implied rates; CPI and PPI releases; Non-farm payrolls data; Treasury auction demand metrics
**Swing:** Enter on yield curve steepening/flattening extremes, exit when spread reverts to 30-day mean or Fed policy pivot confirmed
**Short-term:** Trade around major economic releases using pre-positioning based on consensus vs actual data, with tight stops on unexpected outcomes

### grok-4-latest — _Grok-4 (X_AI)_
**Top picks:**
- **TLT** SHORT (swing) — Anticipating higher yields from persistent inflation pressures weakening long-term bond prices.
- **BND** LONG (short-term) — Bonds as a safe haven amid equity market volatility with expected Fed rate pause.
- **ZN=F** SHORT (swing) — 10-Year Treasury yields likely to rise on strong economic data signaling no imminent recession.
**Factors:** Yield curve slope; CPI inflation readings; Fed funds rate expectations; Unemployment rate trends; GDP growth forecasts
**Data points:** Real-time Treasury yield data from Bloomberg; Economic calendar events from Investing.com; Bond ETF price feeds from Yahoo Finance; Fed meeting minutes from Federal Reserve website; CPI reports from Bureau of Labor Statistics
**Swing:** Enter long on bonds when yields break below a 50-day moving average indicating falling rates, and exit on a trailing stop or when yields revert above the average; for shorts, reverse the logic on yield breakouts upward.
**Short-term:** For 1-3 day trades, enter based on intraday momentum crossovers like RSI above 70 for shorts or below 30 for longs, exiting on predefined profit targets or end-of-day to avoid overnight risk.

### mercury-2 — _Mercury 2 (Inception)_
**Top picks:**
- **ZN=F** LONG (swing) — Yield curve flattening and lower inflation expectations support a rally in 10‑year Treasury futures.
- **ZB=F** SHORT (short-term) — Rising real‑yields and tighter monetary policy pressure long‑dated bonds, making 30‑year futures vulnerable.
- **ZT=F** LONG (short-term) — Short‑duration Treasury futures benefit from flight‑to‑quality amid near‑term market volatility.
**Factors:** Yield curve spread (10Y‑2Y); Real‑yield inflation; Credit spread (Baa‑AAA); Relative Strength Index (RSI) on Treasury ETFs; Fed funds rate outlook
**Data points:** Daily Treasury yield curve rates; CPI inflation data; Federal Reserve policy statements; Credit default swap spreads for sovereign debt; Price and volume for TLT ETF
**Swing:** Enter on a bounce off the 10‑year yield support level with RSI below 30, target a 2‑3% upside or a break of the 2‑year yield resistance; exit if the yield curve steepens beyond 50 bps.
**Short-term:** Trade on intraday breakouts of the 5‑year futures when the 5‑minute RSI crosses above 70 (short) or below 30 (long), with a tight 0.5% stop and a 1% profit target within 1‑3 days.

### moonshot-v1-32k — _Kimi K2 (Moonshot REST)_
**Top picks:**
- **TLT** LONG (swing) — Expecting a decline in interest rates due to economic slowdown.
- **IEF** SHORT (short-term) — Expecting an increase in short-term interest rates due to inflation concerns.
**Factors:** Yield Curve; Inflation Rate; Central Bank Policy
**Data points:** U.S. Treasury Yields; CPI Data; Fed Funds Rate
**Swing:** Enter long positions in bond ETFs like TLT when yields are expected to decrease, and exit when yields rise. Enter short positions in bond ETFs like IEF when yields are expected to increase, and exit when yields fall.
**Short-term:** For short-term trades, look for intraday price movements in bond ETFs in response to economic data releases or central bank announcements, and close positions within 1-3 days based on profit targets or stop-loss levels.

### qwen2.5-coder:14b — _code-specialist (Alibaba)_
**Top picks:**
- **BND** LONG (swing) — High demand for safe-haven assets
- **TLT** LONG (short-term) — Long-term bond ETF with low volatility
- **SHY** SHORT (swing) — Overvalued short-term bond ETF
**Factors:** yield curve slope; credit spread; inflation expectations; economic growth indicators; monetary policy signals
**Data points:** 10-year Treasury yield; 2-year Treasury yield; CPI inflation rate; GDP growth forecast; Fed funds rate
**Swing:** Enter long positions in BND and TLT when the yield curve flattens or inverts, exit on a rising yield curve. Short SHY when it outperforms other short-term bonds.
**Short-term:** Buy TLT on pullbacks to support levels, sell on breakouts above resistance. Use SHY as a hedge against rising rates.

### qwen3-coder:480b-cloud — _Qwen3 Coder 480B (Ollama Cloud)_
**Top picks:**
- **TLT** LONG (swing) — Treasury bonds oversold with rising real yields and inverted yield curve signaling recession protection
- **IEF** LONG (swing) — Intermediate-term Treasuries attractive as Fed pivot expectations build amid economic slowdown signals
- **BND** LONG (short-term) — Broad bond market ETF offers diversification with defensive positioning against equity volatility
**Factors:** yield_curve_slope; real_interest_rates; credit_spread_tightness; volatility_index_VIX; fed_funds_rate_expectations
**Data points:** 10Y-2Y_yield_spread; 10Y_TIPS_real_yield; VIX_index_level; fed_funds_futures_implied_rates; investment_grade_credit_spreads
**Swing:** Enter long positions when yield curve inversion deepens beyond -50bps with VIX above 25, exit when 10Y-2Y spread normalizes above 0 or VIX declines below 20 for 3 consecutive days
**Short-term:** Buy dips in bond ETFs when daily RSI falls below 30 and 5-day Treasury auction results show strong demand, exit on RSI crossover above 70 or if Fed speakers signal hawkish tone

### qwen3:14b — _Qwen3 general (Alibaba)_
**Top picks:**
- **ZN=F** LONG (swing) — Steepening yield curve suggests higher long-term growth expectations, favoring longer-duration bonds
- **HYG** SHORT (short-term) — Credit spreads widening due to inflation fears reduce corporate bond appeal
- **TIP** LONG (swing) — Inflation-linked bonds benefit from rising CPI expectations
**Factors:** yield curve steepness; inflation expectations (TIPS breakeven); credit spreads (BBB vs. Treasury); central bank policy stance; GDP growth forecasts
**Data points:** 10Y-2Y yield spread; CPI YoY data; FED Funds rate projections; Corporate bond default rates; M2 money supply growth
**Swing:** Enter long ZN=F when 10Y yield breaks above 50-day EMA with RSI <30; exit on 200-day EMA crossover. Short HYG if credit spread >200 bps and CPI >3% YoY
**Short-term:** Buy TIP on 2-day close above 5-day EMA with MACD histogram rising; exit on 3% profit target or 2-day close below 5-day EMA
