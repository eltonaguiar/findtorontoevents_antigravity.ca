# Multi-Model Picks Research — Per Asset Class

**Generated:** 2026-05-12 21:25 UTC

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

### grok-4-latest — Grok-4 (X_AI)  (elapsed 16.7s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Bitcoin shows strong upward momentum with breakout above $60,000 resistance and positive on-chain metrics amid stable market conditions.
- **ETHUSDT** SHORT (short-term) — Ethereum is overbought with RSI above 70 and potential for correction given recent whale selling activity.
- **SOLUSDT** LONG (short-term) — Solana exhibits bullish divergence on MACD and increasing network activity supporting a short-term rebound.
**Factors Used:**
- RSI momentum indicator
- MACD trend convergence
- On-chain transaction volume
- Funding rate analysis
- Market sentiment index
**Data Points To Fetch:**
- Real-time OHLCV price data
- Order book depth from exchanges
- Perpetual funding rates
- Social media sentiment scores
- Whale wallet transaction alerts
**Swing Trade Setup:** For swing trades in crypto, enter on confirmed breakouts above key moving average crossovers with supporting volume, and exit when price reaches Fibonacci extension levels or upon reversal signals like bearish candlestick patterns.
**Short Term Setup:** Enter short-term crypto trades on intraday momentum bursts confirmed by RSI breakouts and high trading volume, exiting within 1-3 days on profit targets or when momentum fades as indicated by MACD histogram contraction.

### mercury-2 — Mercury 2 (Inception)  (elapsed 1.4s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Strong on-chain activity and bullish EMA cross suggest upside
- **ETHUSDT** LONG (short-term) — Positive funding rates and RSI divergence indicate short-term strength
- **SOLUSDT** SHORT (short-term) — Overbought RSI and falling volume suggest a pullback
**Factors Used:**
- 20/50 EMA cross
- RSI
- On-chain transaction volume
- Futures funding rate
- Order book imbalance
**Data Points To Fetch:**
- Current price
- 24h volume
- On-chain transaction count
- Funding rate
- Order book depth
**Swing Trade Setup:** Enter long when price breaks above the 20‑day EMA while the 20‑day EMA is above the 50‑day EMA and RSI is above 40; set stop below the 50‑day EMA and target 8‑12% profit.
**Short Term Setup:** Take long/short on 1‑3 day horizons when price touches Bollinger band extremes with confirming MACD divergence; exit at opposite band or when RSI reverts to neutral.

### moonshot-v1-32k — Kimi K2 (Moonshot REST)  (elapsed 5.0s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Bitcoin's dominance in the crypto market and its recent price stability suggest a potential upward trend.
- **ETHUSDT** LONG (short-term) — Ethereum's strong fundamentals and upcoming network upgrades make it a promising investment.
**Factors Used:**
- Moving Average Convergence Divergence (MACD)
- Relative Strength Index (RSI)
- Volume Weighted Average Price (VWAP)
**Data Points To Fetch:**
- Historical price data
- Order book depth
- Social sentiment analysis
- Market capitalization
- 24-hour trading volume
**Swing Trade Setup:** For swing trades, enter long positions when the MACD signals a bullish crossover and RSI is below 70, indicating a potential overbought condition. Exit when the MACD shows a bearish crossover or RSI reaches 70 or above.
**Short Term Setup:** For short-term trades, look for entry opportunities when price breaks above VWAP and RSI is below 50, suggesting a potential bounce. Exit positions when price falls below VWAP or RSI exceeds 50, indicating a possible reversal.

## EQUITY

### grok-4-latest — Grok-4 (X_AI)  (elapsed 14.4s)
**Top picks:**
- **AAPL** LONG (swing) — Strong quarterly earnings and positive RSI momentum indicate potential for upward trend continuation.
- **TSLA** SHORT (short-term) — Overbought conditions and weakening EV sector sentiment suggest a near-term pullback.
- **SPY** LONG (swing) — Broad market recovery supported by favorable economic data and low volatility points to sustained gains.
**Factors Used:**
- Moving Average Convergence Divergence (MACD)
- Relative Strength Index (RSI)
- Trading Volume
- Earnings Per Share (EPS) Growth
- Market Sentiment Index
**Data Points To Fetch:**
- Real-time intraday price feeds
- Historical volatility metrics
- Options implied volatility
- Economic calendar events
- Sector performance indices
**Swing Trade Setup:** For swing trades in equities, enter on confirmed breakouts above key resistance levels with supporting volume and MACD crossover, then exit on hitting a predefined profit target or trailing stop-loss based on ATR multiples.
**Short Term Setup:** For 1-3 day trades, enter on intraday momentum signals like RSI divergences or candlestick patterns during high-volume sessions, and exit at the end of the day or upon reaching a tight stop-loss to capture quick gains.

### mercury-2 — Mercury 2 (Inception)  (elapsed 0.9s)
**Top picks:**
- **SPY** LONG (swing) — Strong earnings growth and bullish momentum on the S&P 500
- **QQQ** SHORT (short-term) — Tech valuation compression and weakening MACD divergence
- **AAPL** LONG (swing) — Robust product pipeline and positive earnings surprise
**Factors Used:**
- Relative Strength Index (RSI)
- Moving Average Convergence Divergence (MACD)
- Earnings Surprise
- Analyst Sentiment
- Volatility (ATR)
**Data Points To Fetch:**
- Real-time price and volume
- Earnings calendar
- Analyst rating changes
- Economic calendar (GDP, CPI)
- Option implied volatility
**Swing Trade Setup:** Enter long on SPY when price closes above the 50‑day EMA with RSI >55 and MACD bullish crossover; exit near 10‑day EMA or when RSI exceeds 70.
**Short Term Setup:** Short QQQ on a pull‑back below the 20‑day EMA with MACD negative divergence and RSI <45; cover within 1‑3 days if price re‑claims the EMA.

### moonshot-v1-32k — Kimi K2 (Moonshot REST)  (elapsed 5.2s)
**Top picks:**
- **SPY** LONG (swing) — S&P 500 ETF, expected to benefit from the current economic recovery.
- **AAPL** LONG (swing) — Strong Q1 earnings and increasing demand for tech products.
- **ZC=F** SHORT (short-term) — Corn futures may face selling pressure due to increased supply.
**Factors Used:**
- Relative Strength Index (RSI)
- Moving Average Convergence Divergence (MACD)
- Volume Weighted Average Price (VWAP)
**Data Points To Fetch:**
- Historical price data
- Economic indicators
- Company earnings reports
- Volume and liquidity metrics
- Market sentiment analysis
**Swing Trade Setup:** Enter on a breakout above the 50-day moving average with a stop loss below the 200-day moving average. Exit on a close below the 50-day moving average or when a target profit level is reached.
**Short Term Setup:** Enter on a strong bullish candlestick pattern with a tight stop loss. Exit on the next day if the price fails to move in the anticipated direction or if a profit target is met.

## FOREX

### grok-4-latest — Grok-4 (X_AI)  (elapsed 15.1s)
**Top picks:**
- **EURUSD** LONG (swing) — EURUSD shows bullish momentum due to recent ECB policy hints and weakening USD index.
- **GBPUSD** SHORT (short-term) — GBPUSD is overbought on RSI with upcoming UK economic data likely to pressure the pound.
- **USDJPY** LONG (swing) — USDJPY benefits from safe-haven flows amid global uncertainty and positive US yield differentials.
**Factors Used:**
- RSI oscillator for overbought/oversold conditions
- Moving average crossovers for trend confirmation
- Economic calendar events like GDP releases
- Interest rate differentials between currencies
**Data Points To Fetch:**
- Real-time bid/ask prices from forex API
- Historical OHLC data for the past 30 days
- Upcoming economic indicators from calendars like Forex Factory
- Currency correlation matrix
**Swing Trade Setup:** For swing trades in FOREX, enter on confirmed trend reversals using moving average crossovers with RSI above 50 for longs or below for shorts, and exit at predefined profit targets based on Fibonacci extensions or trailing stops after 5-10 days.
**Short Term Setup:** For 1-3 day trades, enter on intraday breakouts supported by volume spikes and MACD signals, exiting at the end of the session or upon hitting a 1:2 risk-reward ratio stop/target.

### mercury-2 — Mercury 2 (Inception)  (elapsed 1.6s)
**Top picks:**
- **EURUSD** LONG (swing) — Eurozone CPI easing and positive rate differential support upside
- **USDJPY** SHORT (short-term) — Bank of Japan's ultra-loose stance vs rising US yields creates downward pressure
- **GBPUSD** LONG (swing) — UK wage growth outpacing inflation fuels expectations of rate hikes
**Factors Used:**
- Interest rate differential (CIRP)
- Relative Strength Index (RSI)
- Moving Average Convergence Divergence (MACD)
- CPI inflation releases
- Central bank policy expectations
**Data Points To Fetch:**
- Real-time spot price feed
- Overnight interest rate spreads (EUR/USD, GBP/USD, USD/JPY)
- Upcoming macro calendar (CPI, employment)
- Order flow imbalance data
- Implied volatility index (e.g., JP Morgan G7 FX Vol)
**Swing Trade Setup:** Enter on a 20‑day EMA crossover with RSI below 30 for longs or above 70 for shorts, and hold 2‑4 weeks targeting 1‑2% move; exit on opposite EMA cross or RSI reversal.
**Short Term Setup:** Use 4‑hour chart; enter on break of Bollinger Band with MACD histogram turning positive for longs or negative for shorts, hold 1‑3 days and exit at 0.5% profit or when price re‑enters the band.

### moonshot-v1-32k — Kimi K2 (Moonshot REST)  (elapsed 6.7s)
**Top picks:**
- **EURUSD** LONG (swing) — Euro is expected to strengthen against the US dollar due to the European Central Bank's hawkish stance and strong economic data.
- **GBPUSD** SHORT (short-term) — GBP is likely to weaken against USD due to Brexit uncertainties and the Bank of England's cautious approach to rate hikes.
- **USDJPY** SHORT (swing) — Japanese yen may appreciate against the US dollar as the Bank of Japan maintains its ultra-accommodative monetary policy, leading to a safe-haven demand for JPY.
**Factors Used:**
- Interest rate differentials
- Economic indicators (GDP, inflation, employment data)
- Central bank policy statements
- Technical indicators (RSI, MACD, Bollinger Bands)
- Geopolitical events
**Data Points To Fetch:**
- Central bank interest rate decisions and meeting minutes
- Economic calendar releases (ISM, NFP, GDP, CPI)
- Currencies' implied volatility (VIX for forex pairs)
- FX swap rates and carry trades
- Technical chart patterns and moving averages
**Swing Trade Setup:** For swing trades, look for entry points near key support/resistance levels and strong economic data releases. Exit positions when the trade reaches the next significant technical level or when economic data suggests a trend reversal.
**Short Term Setup:** For 1-3 day trades, focus on intraday price action and short-term technical indicators. Enter trades on breakouts or pullbacks to key levels, and exit when profit targets are met or if the trade moves against you by a predetermined stop-loss amount.

## COMMODITY

### grok-4-latest — Grok-4 (X_AI)  (elapsed 18.4s)
**Top picks:**
- **GC=F** LONG (swing) — Geopolitical tensions and inflation concerns are boosting demand for gold as a safe-haven asset.
- **CL=F** SHORT (short-term) — Oversupply from increased production and weakening global demand signals a downward price pressure.
- **ZC=F** LONG (swing) — Favorable weather forecasts and rising export demand are supporting higher corn prices.
**Factors Used:**
- Moving Average Crossovers
- RSI Momentum
- Volume Trends
- Supply/Demand Fundamentals
- USD Strength Correlation
**Data Points To Fetch:**
- CFTC Commitment of Traders Report
- EIA Weekly Inventory Data
- USD Index Live Feed
- Geopolitical News Alerts
- Weather Pattern Forecasts
**Swing Trade Setup:** For swing trades in commodities, enter on confirmed trend reversals using moving average crossovers and positive divergence in RSI, with exits triggered by trailing stops or when prices hit predefined Fibonacci retracement levels over 1-4 weeks.
**Short Term Setup:** In short-term commodity trades, enter on intraday breakouts supported by high volume and momentum indicators like MACD, exiting at the end of the session or upon reaching a 1-2% profit target within 1-3 days to capture quick volatility swings.

### mercury-2 — Mercury 2 (Inception)  (elapsed 1.1s)
**Top picks:**
- **GC=F** LONG (swing) — Gold is gaining as real‑interest‑rate expectations rise and inflation remains sticky.
- **CL=F** SHORT (short-term) — Crude oil inventories are at multi‑year highs, signaling oversupply.
- **HG=F** LONG (swing) — Copper demand from China is accelerating while supply constraints tighten.
**Factors Used:**
- COT Commitment of Traders
- Relative Strength Index (RSI)
- MACD
- US CPI YoY
- EIA Inventory Reports
**Data Points To Fetch:**
- EIA Weekly Petroleum Status Report
- COT Futures Positions
- US CPI YoY
- Gold Spot Price
- Copper Industrial Production Index
**Swing Trade Setup:** Enter on a breakout above the 50‑day SMA with RSI > 55 and MACD bullish crossover; exit near the 20‑day SMA or on a bearish divergence.
**Short Term Setup:** Use intraday 15‑min charts; go short CL=F when price falls below the 1‑hour VWAP with RSI < 40, and cover at the next resistance level or if inventory data shows a drawdown.

### moonshot-v1-32k — Kimi K2 (Moonshot REST)  (elapsed 5.6s)
**Top picks:**
- **GC=F** LONG (swing) — Gold is historically seen as a safe-haven asset during economic uncertainty.
- **CL=F** SHORT (short-term) — Oil prices are expected to decrease due to global economic slowdown affecting demand.
- **ZC=F** LONG (swing) — Corn futures may benefit from increased demand for biofuels and food security concerns.
**Factors Used:**
- Commodity Futures Trading Commission Commitments of Traders Report
- Moving Average Convergence Divergence (MACD)
- Relative Strength Index (RSI)
- Commodity Channel Index (CCI)
- Volume Weighted Average Price (VWAP)
**Data Points To Fetch:**
- Global economic indicators
- Supply and demand reports
- Weather forecasts
- Geopolitical news
- Technical indicators
**Swing Trade Setup:** For swing trades, look for a breakout above the 50-day moving average or a bounce off the 200-day moving average as entry points, with exits on a close below the 50-day moving average or upon reaching a predefined profit target.
**Short Term Setup:** For short-term trades, use intraday momentum indicators to enter on strength or weakness, with exits set at key technical levels or at the end of the trading day to limit risk.

## ETF

### grok-4-latest — Grok-4 (X_AI)  (elapsed 17.0s)
**Top picks:**
- **SPY** LONG (swing) — SPY shows strong upward momentum with positive economic indicators supporting broad market gains.
- **QQQ** SHORT (short-term) — QQQ is overbought in the tech sector with RSI above 70 indicating potential pullback.
- **GLD** LONG (swing) — GLD benefits from inflation hedges and geopolitical tensions driving gold prices higher.
**Factors Used:**
- Moving average crossovers
- Relative Strength Index (RSI)
- Volume trends
- Economic indicators like GDP growth
- Volatility measures (VIX)
**Data Points To Fetch:**
- Historical price and volume data from Yahoo Finance
- Real-time RSI and MACD indicators from TradingView API
- Economic calendar events from Forex Factory
- VIX index levels from CBOE
- Sector performance metrics from Bloomberg
**Swing Trade Setup:** For swing trades on ETFs, enter long on a breakout above key resistance levels confirmed by increasing volume, and exit on a trailing stop-loss or when price hits a predefined profit target based on Fibonacci extensions.
**Short Term Setup:** For 1-3 day trades, enter based on intraday candlestick patterns like bullish engulfing with momentum confirmation, and exit at the end of the day or on a fixed risk-reward ratio stop to capture quick volatility spikes.

### mercury-2 — Mercury 2 (Inception)  (elapsed 5.3s)
**Top picks:**
- **SPY** LONG (swing) — Broad market exposure with strong momentum and positive macro outlook
- **QQQ** LONG (short-term) — Tech sector strength and high relative strength index
- **IWM** SHORT (swing) — Small‑cap momentum weakening and underperformance versus large caps
**Factors Used:**
- 20‑day EMA
- RSI (14)
- MACD
- Volume Oscillator
- VIX
**Data Points To Fetch:**
- ETF price and volume
- Underlying index futures price
- Sector rotation index
- Economic calendar (CPI, Fed funds)
- Open interest on ETF options
**Swing Trade Setup:** Enter on a pullback to the 20‑day EMA when RSI is above 50 and MACD shows a bullish crossover; target 5‑8% upside and exit if price falls below the EMA or RSI drops below 45.
**Short Term Setup:** Trade breakouts above the prior day high with volume >1.5× the 10‑day average; set a tight stop 0.5% below entry and a profit target of 1‑2% for a 1‑3 day horizon.

### moonshot-v1-32k — Kimi K2 (Moonshot REST)  (elapsed 5.1s)
**Top picks:**
- **SPY** LONG (swing) — Stable market conditions and positive price momentum.
- **QQQ** LONG (swing) — High growth potential in technology sector with strong earnings.
- **XLF** SHORT (short-term) — Sector underperforming due to economic uncertainties.
**Factors Used:**
- Relative Strength Index (RSI)
- Moving Average Convergence Divergence (MACD)
- Volume Weighted Average Price (VWAP)
**Data Points To Fetch:**
- Daily trading volume
- Recent earnings reports
- Sector performance data
- Economic indicators
- Market sentiment analysis
**Swing Trade Setup:** Enter on a breakout above the 50-day moving average with a stop-loss below the 200-day moving average. Exit on a close below the 50-day moving average or when the MACD shows a bearish crossover.
**Short Term Setup:** Enter on a strong bullish candlestick pattern with a tight stop-loss. Exit on the next day if the price fails to move in the expected direction or if the RSI indicates overbought conditions.

## BOND

### grok-4-latest — Grok-4 (X_AI)  (elapsed 17.8s)
**Top picks:**
- **TLT** SHORT (swing) — Anticipating higher yields from persistent inflation pressures weakening long-term bond prices.
- **BND** LONG (short-term) — Bonds as a safe haven amid equity market volatility with expected Fed rate pause.
- **ZN=F** SHORT (swing) — 10-Year Treasury yields likely to rise on strong economic data signaling no imminent recession.
**Factors Used:**
- Yield curve slope
- CPI inflation readings
- Fed funds rate expectations
- Unemployment rate trends
- GDP growth forecasts
**Data Points To Fetch:**
- Real-time Treasury yield data from Bloomberg
- Economic calendar events from Investing.com
- Bond ETF price feeds from Yahoo Finance
- Fed meeting minutes from Federal Reserve website
- CPI reports from Bureau of Labor Statistics
**Swing Trade Setup:** Enter long on bonds when yields break below a 50-day moving average indicating falling rates, and exit on a trailing stop or when yields revert above the average; for shorts, reverse the logic on yield breakouts upward.
**Short Term Setup:** For 1-3 day trades, enter based on intraday momentum crossovers like RSI above 70 for shorts or below 30 for longs, exiting on predefined profit targets or end-of-day to avoid overnight risk.

### mercury-2 — Mercury 2 (Inception)  (elapsed 1.3s)
**Top picks:**
- **ZN=F** LONG (swing) — Yield curve flattening and lower inflation expectations support a rally in 10‑year Treasury futures.
- **ZB=F** SHORT (short-term) — Rising real‑yields and tighter monetary policy pressure long‑dated bonds, making 30‑year futures vulnerable.
- **ZT=F** LONG (short-term) — Short‑duration Treasury futures benefit from flight‑to‑quality amid near‑term market volatility.
**Factors Used:**
- Yield curve spread (10Y‑2Y)
- Real‑yield inflation
- Credit spread (Baa‑AAA)
- Relative Strength Index (RSI) on Treasury ETFs
- Fed funds rate outlook
**Data Points To Fetch:**
- Daily Treasury yield curve rates
- CPI inflation data
- Federal Reserve policy statements
- Credit default swap spreads for sovereign debt
- Price and volume for TLT ETF
**Swing Trade Setup:** Enter on a bounce off the 10‑year yield support level with RSI below 30, target a 2‑3% upside or a break of the 2‑year yield resistance; exit if the yield curve steepens beyond 50 bps.
**Short Term Setup:** Trade on intraday breakouts of the 5‑year futures when the 5‑minute RSI crosses above 70 (short) or below 30 (long), with a tight 0.5% stop and a 1% profit target within 1‑3 days.

### moonshot-v1-32k — Kimi K2 (Moonshot REST)  (elapsed 4.4s)
**Top picks:**
- **TLT** LONG (swing) — Expecting a decline in interest rates due to economic slowdown.
- **IEF** SHORT (short-term) — Expecting an increase in short-term interest rates due to inflation concerns.
**Factors Used:**
- Yield Curve
- Inflation Rate
- Central Bank Policy
**Data Points To Fetch:**
- U.S. Treasury Yields
- CPI Data
- Fed Funds Rate
**Swing Trade Setup:** Enter long positions in bond ETFs like TLT when yields are expected to decrease, and exit when yields rise. Enter short positions in bond ETFs like IEF when yields are expected to increase, and exit when yields fall.
**Short Term Setup:** For short-term trades, look for intraday price movements in bond ETFs in response to economic data releases or central bank announcements, and close positions within 1-3 days based on profit targets or stop-loss levels.
