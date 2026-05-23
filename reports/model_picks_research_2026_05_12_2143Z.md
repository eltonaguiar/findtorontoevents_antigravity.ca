# Multi-Model Picks Research — Per Asset Class

**Generated:** 2026-05-12 21:43 UTC

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

### kimi-k2-thinking:cloud — Moonshot Kimi K2 Thinking (Ollama Cloud)  (elapsed ?s)
- ERROR: HTTP Error 500: Internal Server Error

### qwen3-coder:480b-cloud — Qwen3 Coder 480B (Ollama Cloud)  (elapsed 56.8s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Bitcoin showing accumulation pattern with rising volume and positive funding rates
- **ETHUSDT** LONG (swing) — Ethereum outperforming altcoins with strong smart contract activity metrics
- **SOLUSDT** SHORT (short-term) — Solana approaching key resistance with weakening momentum indicators
**Factors Used:**
- on-chain accumulation metrics
- funding rate differentials
- relative strength vs altcoins
- orderbook depth analysis
- hash rate trends
**Data Points To Fetch:**
- live orderbook imbalance ratios
- wallet accumulation rates across exchanges
- miner selling pressure metrics
- stablecoin issuance flows
- futures basis spreads
**Swing Trade Setup:** Enter long positions when 20-day MA crosses above 50-day MA with increasing volume, exit when RSI exceeds 75 or 10-day MA breaks below 20-day MA
**Short Term Setup:** Take mean reversion trades against extreme RSI levels (above 80 for shorts, below 20 for longs) with tight stops at recent swing highs/lows and target previous consolidation zones

### deepseek-v3.1:671b-cloud — DeepSeek V3.1 671B (Ollama Cloud)  (elapsed 10.0s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Strong bullish divergence on daily RSI suggests a potential reversal from oversold conditions.
- **ETHUSDT** LONG (short-term) — High funding rates have reset, and price is holding key support on high volume, indicating a potential long squeeze is over.
- **SOLUSDT** SHORT (swing) — Failing to break above the 200-day moving average on decreasing volume signals weakness and a likely rejection.
**Factors Used:**
- RSI Divergence
- 200-Day Moving Average Confluence
- Funding Rate Mean Reversion
- Volume-Weighted Average Price (VWAP) Deviation
- On-Balance Volume (OBV)
**Data Points To Fetch:**
- 1h/4h RSI values for divergence check
- Perpetual swap funding rates for major pairs
- Order book depth for key support/resistance levels
- 24h volume profile and VWAP
- Exchange net flows for whale movement insight
**Swing Trade Setup:** Enter on a confirmed bullish/bearish engulfing candle at a key support/resistance level with RSI divergence; exit at the next major resistance/support or on a 4h close against the 20EMA.
**Short Term Setup:** Enter on a break of the 15m Bollinger Band with a spike in volume, targeting the opposite band; exit at the target or on a loss of the 5EMA.

### gpt-oss:120b-cloud — GPT-OSS 120B (Ollama Cloud)  (elapsed 7.5s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Bullish on-chain metrics and price above 20‑day EMA with rising funding rates
- **ETHUSDT** LONG (short-term) — Strong RSI rebound from oversold zone and increasing futures open interest
- **BNBUSDT** SHORT (short-term) — Negative MACD crossover and declining on‑chain activity suggest near‑term weakness
**Factors Used:**
- On‑chain transaction volume
- Relative Strength Index (RSI)
- MACD histogram
- Futures open interest
- Funding rate differential
**Data Points To Fetch:**
- Spot price and 20‑day EMA
- Order‑book depth imbalance
- 24‑hour funding rate
- On‑chain active addresses count
- Futures open interest change
**Swing Trade Setup:** Enter on a pullback to the 20‑day EMA with bullish MACD divergence and funding rate >0; target a 2:1 reward‑to‑risk or the next major resistance level, stop just below the EMA swing low.
**Short Term Setup:** Enter on a breakout of the prior day high with volume >150% of average 1‑hour volume; set a tight stop 1% below entry and exit at 1.5× risk or if price re‑enters the 4‑hour EMA band within 24‑48 hours.

### glm-4.6:cloud — GLM-4.6 (Ollama Cloud)  (elapsed 27.2s)
- PARSE-FAIL
- tail: ``

## EQUITY

### kimi-k2-thinking:cloud — Moonshot Kimi K2 Thinking (Ollama Cloud)  (elapsed 24.2s)
**Top picks:**
- **SPY** LONG (swing) — Stable regime with PF>1.5 favors trend continuation, SPY holding above 50-day EMA with improving breadth
- **QQQ** LONG (swing) — Tech sector relative strength and momentum above 20-day EMA, AI/semiconductor tailwinds
- **IWM** LONG (short-term) — Small-cap potential catch-up trade with risk appetite improving and volume accumulation
**Factors Used:**
- RSI(14) momentum
- ATR(14) volatility sizing
- 20/50-day EMA crossover
- Volume profile POC
- Put/Call ratio sentiment
**Data Points To Fetch:**
- Real-time SIP consolidated tape
- Dark pool ATS prints
- Options order flow (unusual activity)
- Sector ETF flow data
- Short interest change feeds
**Swing Trade Setup:** Enter on pullback to 20-day EMA with RSI(14)>50 and rising volume, exit on daily close below 50-day EMA or 2x ATR profit target
**Short Term Setup:** Enter on intraday VWAP breakout with 1.5x average volume confirmation, exit on opposite signal or 1.5x ATR target within 3-day max hold

### qwen3-coder:480b-cloud — Qwen3 Coder 480B (Ollama Cloud)  (elapsed 31.8s)
**Top picks:**
- **SPY** LONG (swing) — Strong momentum with rising volume confirming breakout above key resistance
- **NVDA** LONG (swing) — AI chip demand surge with strong institutional accumulation and earnings beat guidance
- **TSLA** SHORT (short-term) — Technical breakdown below support with increasing bearish sentiment and valuation concerns
**Factors Used:**
- RSI(14)
- Volume Trend
- MACD Histogram
- Institutional Flow
- Earnings Revision Momentum
**Data Points To Fetch:**
- Real-time order book depth
- Intraday volume profile
- Key technical support/resistance levels
- Pre-market futures movement
- Sector correlation coefficients
**Swing Trade Setup:** Enter on confirmed breakout/reversal pattern with volume confirmation, hold for 3-10 days with trailing stop at recent swing low/high for long/short positions respectively.
**Short Term Setup:** Trade mean reversion in oversold/overbought conditions (RSI < 30 or > 70) with tight stops, exit on momentum exhaustion or opposite signal within 1-3 sessions.

### deepseek-v3.1:671b-cloud — DeepSeek V3.1 671B (Ollama Cloud)  (elapsed 8.4s)
**Top picks:**
- **SPY** LONG (swing) — Strong momentum and trend continuation above key moving averages support a long bias.
- **IWM** LONG (swing) — Small-cap breakout from consolidation suggests catch-up potential to broader market strength.
- **TSLA** SHORT (short-term) — Failed breakout on declining volume indicates weakness and a potential reversal short.
**Factors Used:**
- 20/50-day EMA crossover
- RSI(14) momentum
- Volume-Weighted Average Price (VWAP)
- Bollinger Band squeeze/expansion
- Sector relative strength
**Data Points To Fetch:**
- 1-minute OHLCV for VWAP calculation
- Real-time RSI(14) and MACD(12,26,9)
- Pre-market and opening auction volume data
- Sector ETF flows (XLK, XLF, XLV)
- Key support/resistance level order book depth
**Swing Trade Setup:** Enter on a pullback to the 20-day EMA with strong volume confirmation; exit on a break below the 50-day EMA or RSI(14) exceeding 70.
**Short Term Setup:** Enter on a 1-minute breakout above VWAP with high relative volume for longs; exit at the next significant resistance level or if price reclaims VWAP to the downside.

### gpt-oss:120b-cloud — GPT-OSS 120B (Ollama Cloud)  (elapsed 5.4s)
**Top picks:**
- **SPY** LONG (swing) — Broad market rally supported by strong earnings season and positive CPI surprise.
- **AAPL** SHORT (short-term) — Overbought on daily RSI and weakening relative strength versus the Nasdaq index.
- **TSLA** LONG (short-term) — Momentum breakout above 20‑day EMA with rising institutional buying.
**Factors Used:**
- Relative Strength Index (RSI)
- Moving Average Convergence Divergence (MACD)
- Volume Weighted Average Price (VWAP)
- Earnings surprise vs. consensus
- Short interest ratio
**Data Points To Fetch:**
- Intraday price and volume bars (1‑min)
- Latest earnings release and surprise magnitude
- Analyst consensus rating changes
- Institutional ownership and net flow data
- Short interest and days‑to‑cover
**Swing Trade Setup:** Enter on a pullback to the 20‑day EMA when MACD histogram turns positive and RSI is below 70; target the 50‑day EMA or a 5‑10% upside, stop below the recent swing low.
**Short Term Setup:** Take a 1‑3 day position when price breaks above VWAP with volume > 2× average, confirming with a bullish MACD cross; set a tight stop 1% below entry and exit at a 2‑4% profit or on reversal signal.

### glm-4.6:cloud — GLM-4.6 (Ollama Cloud)  (elapsed 17.5s)
**Top picks:**
- **SPY** LONG (swing) — S&P 500 showing bullish momentum with support at 50-day moving average and positive MACD crossover
- **NVDA** LONG (swing) — Semiconductor leader breaking out of consolidation with increasing volume and relative strength vs. sector
- **TSLA** SHORT (short-term) — Overextended above 200-day moving average with bearish divergence on RSI and declining volume
**Factors Used:**
- Price momentum
- Volume patterns
- Moving average crossovers
- RSI divergence
- Relative strength vs. sector
**Data Points To Fetch:**
- Daily OHLCV data
- Intraday volume profile
- Options flow data
- Institutional ownership changes
- Earnings surprise data
**Swing Trade Setup:** Enter on confirmed breakout above resistance with volume confirmation, exit when price closes below 20-day EMA or when RSI reaches overbought levels above 70.
**Short Term Setup:** Enter on mean reversion signals when price deviates more than 2 standard deviations from 5-day moving average, exit when price returns to mean or after 2-3 trading days.

## FOREX

### kimi-k2-thinking:cloud — Moonshot Kimi K2 Thinking (Ollama Cloud)  (elapsed 26.4s)
- PARSE-FAIL
- tail: ``

### qwen3-coder:480b-cloud — Qwen3 Coder 480B (Ollama Cloud)  (elapsed 70.2s)
**Top picks:**
- **EURUSD** SHORT (swing) — Dollar strength amid Fed rate hike expectations and ECB dovish pivot pressure
- **GBPJPY** LONG (short-term) — Yen weakness against majors with BoJ policy divergence supporting upside
- **AUDUSD** SHORT (swing) — RBA hawkish pause amid China demand concerns weighing on Aussie
**Factors Used:**
- relative central bank policy divergence
- real interest rate differentials
- risk sentiment flows
**Data Points To Fetch:**
- Fed speech calendar and tone analysis
- ECB meeting minutes sentiment scoring
- DXY index momentum and support levels
**Swing Trade Setup:** Enter on multi-day trend continuation after key moving average breaks with RSI confirmation, target 2% move with 1% stop loss based on recent volatility clusters
**Short Term Setup:** Trade intraday breakouts from consolidation patterns with volume confirmation, holding 1-3 days targeting 0.8-1.2% moves with tight stops at previous day's extremes

### deepseek-v3.1:671b-cloud — DeepSeek V3.1 671B (Ollama Cloud)  (elapsed 8.0s)
**Top picks:**
- **USDJPY** LONG (swing) — Persistent interest rate differential favoring the USD over the JPY supports a long bias.
- **AUDUSD** SHORT (swing) — Dovish RBA outlook and weaker commodity demand pressures the Aussie against a strong USD.
- **EURGBP** SHORT (short-term) — Relative monetary policy divergence with the ECB expected to cut rates before the BoE.
**Factors Used:**
- Interest Rate Differentials
- Relative Strength Index (RSI)
- 200-Day Moving Average Confluence
- Commitment of Traders (COT) Report Positioning
- FX Volatility Index (VIX)
**Data Points To Fetch:**
- Real-time Central Bank Rate Expectations (OIS)
- Live Spot Price and RSI(14)
- Daily Closing Price vs. 200D MA
- Weekly CFTC COT Report (Net Spec Positions)
- DXY (US Dollar Index) Spot Price
**Swing Trade Setup:** Enter on a pullback to a key moving average or support/resistance level confirmed by RSI divergence; exit on a reach of the next significant resistance/support level or a fundamental shift in central bank rhetoric.
**Short Term Setup:** Enter on a breakout of the Asian or London session range with high volume; exit with a 1:1.5 risk-reward ratio or at the end of the US session to avoid overnight risk.

### gpt-oss:120b-cloud — GPT-OSS 120B (Ollama Cloud)  (elapsed 13.0s)
**Top picks:**
- **EURUSD** SHORT (swing) — Euro weakness from ECB dovish stance versus strong US data
- **USDJPY** LONG (short-term) — Safe‑haven demand for USD and yen carry‑trade unwind
- **GBPUSD** SHORT (short-term) — UK inflation surprise and weaker pound outlook
**Factors Used:**
- Interest rate differential (Fed vs ECB/BOE)
- MACD histogram
- Relative Strength Index (RSI)
- COT positioning (net long/short)
- Implied volatility (FX options)
**Data Points To Fetch:**
- Real-time 1H and 4H OHLCV for each pair
- Central bank policy rate announcements calendar
- US Non‑Farm Payrolls and PMI releases
- COT reports for major dealers
- FX options implied volatility surface
**Swing Trade Setup:** Enter on a 4‑hour MACD bullish/bearish crossover that aligns with a break of the prevailing trendline and RSI confirming overbought or oversold; target a 2:1 reward‑to‑risk or the next major support/resistance level.
**Short Term Setup:** Enter on a 1‑hour RSI extreme bounce (≤30 for long, ≥70 for short) with price holding above/below the 20‑period EMA; exit at the opposite EMA cross or after 1‑3 days if the pair reverts toward the daily pivot.

### glm-4.6:cloud — GLM-4.6 (Ollama Cloud)  (elapsed 25.7s)
**Top picks:**
- **EURUSD** SHORT (swing) — ECB maintaining dovish stance while Fed remains hawkish creating bearish pressure
- **USDJPY** LONG (short-term) — Bank of Japan intervention concerns limiting yen strength despite risk-off sentiment
- **GBPUSD** SHORT (swing) — UK economic data weakening while BOE signals potential rate cuts
**Factors Used:**
- interest rate differentials
- RSI divergence
- 200-day moving average position
- volatility expansion
- commitment of traders report
**Data Points To Fetch:**
- central bank policy statements
- CPI inflation data
- non-farm payrolls
- commitment of traders report
- overnight index swap rates
**Swing Trade Setup:** Enter on 4-hour timeframe when price closes below 21 EMA with RSI below 50, exit when RSI crosses above 70 or price closes above 50 SMA
**Short Term Setup:** Enter on 15-minute chart during London/NY session overlap when price breaks 20-period Bollinger Band with volume spike, exit at 1:2 risk/reward or session close

## COMMODITY

### kimi-k2-thinking:cloud — Moonshot Kimi K2 Thinking (Ollama Cloud)  (elapsed 31.8s)
**Top picks:**
- **GC=F** LONG (swing) — Strong momentum above 20-week MA with backwardated curve signaling supply tightness
- **CL=F** SHORT (short-term) — Mean reversion signal after 3-week rally into resistance with rising inventory builds
- **NG=F** LONG (swing) — Seasonal pattern alignment with early summer cooling demand and low storage levels
**Factors Used:**
- 12-week price momentum
- Term structure slope (backwardation/contango)
- COT net speculator positioning
- Inventory deviation from seasonal norm
- DXY inverse correlation
**Data Points To Fetch:**
- Real-time futures tick data
- CFTC COT weekly report
- EIA/DOE inventory statistics
- USD index spot price
- CVOL commodity volatility index
**Swing Trade Setup:** Enter on momentum breakout confirmed by term structure backwardation; exit when price closes below 20-period MA or contango develops signaling oversupply.
**Short Term Setup:** Fade extreme intraday moves when inventory data surprises against trend; use 1.5x ATR stop-loss and target 2:1 reward/risk within 3 sessions.

### qwen3-coder:480b-cloud — Qwen3 Coder 480B (Ollama Cloud)  (elapsed 45.8s)
**Top picks:**
- **GC=F** LONG (swing) — Gold breaking above key resistance with strong volume confirmation and positive sentiment amid inflation concerns
- **CL=F** SHORT (short-term) — Crude oil showing bearish divergence with lower highs despite geopolitical tensions, indicating distribution phase
- **SI=F** LONG (swing) — Silver exhibiting strong relative strength against gold with increasing open interest and technical breakout
**Factors Used:**
- price momentum
- volume confirmation
- sentiment indicators
- seasonal patterns
- carry cost analysis
**Data Points To Fetch:**
- COT reports for commercial positioning
- inventory levels from government sources
- volatility term structure
- real interest rate differentials
- geopolitical risk indices
**Swing Trade Setup:** Enter on breakout above 20-day high with volume confirmation, target 2-3% move based on average true range, exit on 5-day low penetration or when momentum diverges
**Short Term Setup:** Trade 1-3 day reversals around key support/resistance levels with intraday momentum filters, exit on opposite signal or when price exceeds daily volatility range

### deepseek-v3.1:671b-cloud — DeepSeek V3.1 671B (Ollama Cloud)  (elapsed 10.4s)
**Top picks:**
- **CL=F** LONG (swing) — Strong uptrend with recent breakout above key resistance on rising open interest.
- **ZC=F** SHORT (short-term) — Breakdown from a bear flag pattern suggests continuation of the primary downtrend.
- **HG=F** LONG (swing) — Oversold RSI bouncing from a major support level amid tightening physical supply.
**Factors Used:**
- RSI (14-period)
- Open Interest change
- 20/50-day EMA confluence
- Commitment of Traders (COT) net positioning
- Inter-commodity spread strength
**Data Points To Fetch:**
- Real-time futures term structure (roll yields)
- 1-hour volume profile
- Current day's high/low for key pivot levels
- Settlement price from previous session
- Macro calendar for today's key events (e.g., CPI, inventory reports)
**Swing Trade Setup:** Enter on a daily close confirming the breakout/breakdown of a key technical level, using the 20-day EMA as a dynamic exit for momentum trades.
**Short Term Setup:** Enter on a 1-hour candle close with high volume exceeding the prior session's ATR, targeting the previous day's high/low for a quick scalp exit.

### gpt-oss:120b-cloud — GPT-OSS 120B (Ollama Cloud)  (elapsed 8.8s)
**Top picks:**
- **CL=F** LONG (swing) — Oil prices are above the 20‑day EMA, inventory draws are accelerating and the USD index is weakening, supporting a multi‑week uptrend.
- **GC=F** SHORT (short-term) — Real yields have risen sharply, gold is below its 50‑day SMA and COT data shows increasing short positioning.
- **ZC=F** LONG (swing) — Corn stocks are at multi‑year lows and planting progress is ahead of schedule, driving bullish fundamentals.
**Factors Used:**
- 20‑day EMA / 50‑day SMA crossover
- Relative Strength Index (RSI) on 14 periods
- Commitments of Traders (COT) net positioning
- Key inventory reports (EIA, USDA)
- USD Index correlation
**Data Points To Fetch:**
- Live futures price and volume for each symbol
- Open interest and net long/short COT data
- Latest EIA crude oil inventory and USDA corn stock reports
- USD Index (DXY) level
- Economic calendar events (GDP, PMI, Fed minutes) affecting risk sentiment
**Swing Trade Setup:** Enter on a break above the 20‑day EMA with RSI > 55 and confirming bullish COT net longs; set a profit target at 8‑10% or the next major resistance and a trailing stop 3% below the entry high.
**Short Term Setup:** Enter on a 4‑hour RSI crossing 70 (overbought) for shorts or 30 (oversold) for longs, with price failing to hold the 20‑day SMA; exit after 1‑3 days or when RSI re‑enters the 40‑60 band.

### glm-4.6:cloud — GLM-4.6 (Ollama Cloud)  (elapsed 19.6s)
**Top picks:**
- **GC=F** LONG (swing) — Safe-haven demand amid geopolitical tensions and inflation concerns
- **CL=F** SHORT (short-term) — Demand slowdown concerns and OPEC+ production increases
- **NG=F** LONG (swing) — Seasonal demand increase and lower-than-average inventory levels
**Factors Used:**
- Seasonal patterns
- Supply/demand fundamentals
- Inventory levels
- Currency correlation (USD strength)
- Weather patterns
**Data Points To Fetch:**
- COT reports
- Weekly inventory data
- Production/consumption statistics
- Weather forecasts
- USD index correlation
**Swing Trade Setup:** Enter on seasonal trend confirmation with inventory support, exit when fundamentals reverse or target seasonal peak
**Short Term Setup:** Enter on technical breakouts with volume confirmation, exit at next key support/resistance level or on momentum divergence

## ETF

### kimi-k2-thinking:cloud — Moonshot Kimi K2 Thinking (Ollama Cloud)  (elapsed 29.7s)
- PARSE-FAIL
- tail: ``

### qwen3-coder:480b-cloud — Qwen3 Coder 480B (Ollama Cloud)  (elapsed 41.2s)
**Top picks:**
- **SPY** LONG (swing) — Strong momentum with improving breadth and above-average volume confirmation
- **QQQ** LONG (short-term) — Tech sector leading with strong relative performance against S&P 500
- **TLT** SHORT (swing) — Rising yield environment pressuring long-duration bonds with bearish moving average crossover
**Factors Used:**
- price momentum
- relative strength vs benchmark
- volume confirmation
- moving average alignment
- volatility regime
**Data Points To Fetch:**
- real-time price/volume
- market breadth indicators
- federal reserve policy signals
- VIX levels
- sector rotation metrics
**Swing Trade Setup:** Enter on confirmed trend continuation with 20-day MA support and exit on 50-day MA rejection or -2% stop loss, target 5-8% gain
**Short Term Setup:** Enter on intraday momentum breakouts with volume confirmation, exit on opposite momentum signal or end of day if held overnight

### deepseek-v3.1:671b-cloud — DeepSeek V3.1 671B (Ollama Cloud)  (elapsed 8.1s)
**Top picks:**
- **SPY** LONG (swing) — Strong win rate and profit factor suggest a stable uptrend favoring long bias on broad market ETFs.
- **QQQ** LONG (swing) — Momentum and risk-on sentiment typically benefit tech-heavy ETFs in a stable bullish regime.
- **TLT** SHORT (short-term) — Anticipating rising yields to pressure long-duration bonds as the stable trend allows for tactical shorts.
**Factors Used:**
- RSI (14-period)
- 20-day Simple Moving Average convergence
- Average Directional Index (ADX)
- Volume profile (VWAP)
- Sector rotation flows
**Data Points To Fetch:**
- Real-time RSI(14) for overbought/oversold levels
- 1-hour and daily candle closes vs 20 SMA
- 14-period ADX for trend strength
- Volume 20-day average comparison
- US 10-Year Treasury Yield (^TNX)
**Swing Trade Setup:** Enter LONG on a pullback to the 20-day SMA with RSI(14) < 45, exit on RSI(14) > 70 or a close below the 20-day SMA.
**Short Term Setup:** Enter on a 1-hour RSI(14) divergence with price, targeting a 2:1 reward/risk ratio, and exit at the previous session's high/low.

### gpt-oss:120b-cloud — GPT-OSS 120B (Ollama Cloud)  (elapsed 6.7s)
**Top picks:**
- **SPY** LONG (swing) — 20‑day EMA just turned up and RSI is in the 45‑55 range, indicating bullish momentum with room to run.
- **QQQ** LONG (swing) — Tech sector strength and a bullish MACD crossover support further upside over the next 2‑4 weeks.
- **IWM** SHORT (short-term) — Break below the 50‑day SMA with deteriorating small‑cap earnings outlook suggests a near‑term pullback.
**Factors Used:**
- 20‑day Exponential Moving Average (EMA)
- Relative Strength Index (RSI)
- MACD histogram
- ETF net inflow/outflow data
- Sector rotation index
**Data Points To Fetch:**
- Live price and volume for each ETF
- EMA and SMA values (20, 50, 200 day)
- RSI and MACD readings
- Daily net inflow/outflow from fund providers
- Sector rotation score from Bloomberg
**Swing Trade Setup:** Enter long when price closes above the 20‑day EMA with RSI between 40‑60 and MACD histogram turning positive; set initial stop 2% below entry and target 8‑12% or exit on EMA cross down.
**Short Term Setup:** Enter short on IWM if price breaks below the 50‑day SMA on >2× average volume and RSI falls below 40; exit after a 1.5‑2% gain or if price rebounds above the SMA with a bullish candle.

### glm-4.6:cloud — GLM-4.6 (Ollama Cloud)  (elapsed 30.2s)
- PARSE-FAIL
- tail: `{
  "top_picks": [
    {"symbol": "SPY", "direction": "LONG", "rationale": "SPY showing bullish momentum with RSI oversold bounce and institutional buying pressure", "timeframe": "swing"},
    {"symbol": "QQQ", "direction": "LONG", "rationale": "Tech sector strength with QQQ breaking above 50-day mo`

## BOND

### kimi-k2-thinking:cloud — Moonshot Kimi K2 Thinking (Ollama Cloud)  (elapsed 30.9s)
- PARSE-FAIL
- tail: ``

### qwen3-coder:480b-cloud — Qwen3 Coder 480B (Ollama Cloud)  (elapsed 34.9s)
**Top picks:**
- **TLT** LONG (swing) — Treasury bonds oversold with rising real yields and inverted yield curve signaling recession protection
- **IEF** LONG (swing) — Intermediate-term Treasuries attractive as Fed pivot expectations build amid economic slowdown signals
- **BND** LONG (short-term) — Broad bond market ETF offers diversification with defensive positioning against equity volatility
**Factors Used:**
- yield_curve_slope
- real_interest_rates
- credit_spread_tightness
- volatility_index_VIX
- fed_funds_rate_expectations
**Data Points To Fetch:**
- 10Y-2Y_yield_spread
- 10Y_TIPS_real_yield
- VIX_index_level
- fed_funds_futures_implied_rates
- investment_grade_credit_spreads
**Swing Trade Setup:** Enter long positions when yield curve inversion deepens beyond -50bps with VIX above 25, exit when 10Y-2Y spread normalizes above 0 or VIX declines below 20 for 3 consecutive days
**Short Term Setup:** Buy dips in bond ETFs when daily RSI falls below 30 and 5-day Treasury auction results show strong demand, exit on RSI crossover above 70 or if Fed speakers signal hawkish tone

### deepseek-v3.1:671b-cloud — DeepSeek V3.1 671B (Ollama Cloud)  (elapsed 8.0s)
**Top picks:**
- **TLT** LONG (swing) — Long-duration Treasuries are oversold and due for a relief rally as the market reassesses the Fed's rate path.
- **HYG** SHORT (swing) — High yield credit spreads are likely to widen in a thin sample, high uncertainty environment, pressuring prices.
- **ZB=F** LONG (short-term) — 30-Year Treasury Bond futures show bullish RSI divergence on short-term charts, suggesting a brief bounce.
**Factors Used:**
- Yield Curve Steepening/Flattening
- Credit Spreads (ICE BofA High Yield Index)
- RSI Divergence on Key Maturities
- Fed Funds Futures Implied Probability
- Aggregate Bond Fund Flows
**Data Points To Fetch:**
- 10-Year vs 2-Year Treasury Yield Spread
- Daily TRACE Data for HYG Constituents
- CFTC 10-Year Treasury Net Speculator Positions
- TLT On-Balance Volume (OBV)
- Next FOMC Meeting Implied Rate Hike Probability
**Swing Trade Setup:** Enter on a close above the 20-day SMA with rising volume for longs, or a close below it for shorts; exit at key resistance/support levels or on a reversal of the yield curve momentum.
**Short Term Setup:** Scalp 1-3 day reversions using 1-hour RSI extremes (<30 for long, >70 for short) against the 50-period EMA, exiting at the mean or on a 5% profit target.

### gpt-oss:120b-cloud — GPT-OSS 120B (Ollama Cloud)  (elapsed 10.4s)
- PARSE-FAIL
- tail: `     "rationale": "Yield curve flattening and falling 10‑yr Treasury yields support higher prices",
      "timeframe": "swing"
    },
    {
      "symbol": "HYG",
      "direction": "SHORT",
      "rationale": "Rising credit spreads and higher inflation expectations pressure high‑yield bonds",
     `

### glm-4.6:cloud — GLM-4.6 (Ollama Cloud)  (elapsed 14.5s)
**Top picks:**
- **TLT** LONG (swing) — Yield curve inversion suggests potential Fed rate cuts, benefiting long-duration bonds
- **ZB** SHORT (short-term) — Rising inflation expectations may pressure long-term yields higher
- **SHY** LONG (swing) — Short-term Treasuries offer safety with Fed likely maintaining higher rates longer
**Factors Used:**
- Yield curve slope (10Y-2Y spread)
- Fed funds rate expectations
- CPI inflation trends
- Real yield differentials
- Duration exposure
**Data Points To Fetch:**
- Treasury yield curve (2Y, 5Y, 10Y, 30Y)
- Fed funds futures implied rates
- CPI and PPI releases
- Non-farm payrolls data
- Treasury auction demand metrics
**Swing Trade Setup:** Enter on yield curve steepening/flattening extremes, exit when spread reverts to 30-day mean or Fed policy pivot confirmed
**Short Term Setup:** Trade around major economic releases using pre-positioning based on consensus vs actual data, with tight stops on unexpected outcomes
