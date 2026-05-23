# 100+ Original Trading Strategy Concepts

A comprehensive collection of creative trading strategies across multiple dimensions of market analysis.

---

## Category 1: Unconventional Indicator Combinations (Strategies 1-15)

### 1. Volume-Weighted RSI Divergence (VWRD)
**Core Concept:** Traditional RSI divergence weighted by volume profile to filter false signals.
**Edge/Rationale:** Standard RSI divergences fail because they don't account for conviction. High-volume divergences indicate genuine exhaustion; low-volume divergences are noise.
**Indicators/Data:** RSI(14), Volume Profile (VPVR), On-Balance Volume (OBV)
**Asset Class:** Equities, Crypto, Forex
**Implementation Difficulty:** Medium

### 2. Bollinger Band %B with Keltner Channel Confluence
**Core Concept:** Trade when price touches Bollinger extremes while Keltner Channel confirms trend direction.
**Edge/Rationale:** Bollinger Bands capture volatility; Keltner Channels capture trend. The combination filters mean-reversion trades against the prevailing trend.
**Indicators/Data:** Bollinger Bands (20,2), Keltner Channel (20,1.5), ADX for trend strength
**Asset Class:** All liquid markets
**Implementation Difficulty:** Easy

### 3. MACD Histogram Slope + Ichimoku Cloud Position
**Core Concept:** MACD histogram slope changes combined with price position relative to Ichimoku Cloud.
**Edge/Rationale:** MACD slope indicates momentum acceleration/deceleration; Ichimoku provides multi-timeframe support/resistance context.
**Indicators/Data:** MACD(12,26,9), Ichimoku Cloud (9,26,52,26), Chikou Span confirmation
**Asset Class:** Forex, Commodities, Indices
**Implementation Difficulty:** Medium

### 4. Stochastic RSI with Williams %R Overlay
**Core Concept:** Double-oscillator confirmation using StochRSI for momentum and Williams %R for overbought/oversold extremes.
**Edge/Rationale:** StochRSI is sensitive; Williams %R is robust. Together they reduce whipsaws while capturing early reversals.
**Indicators/Data:** StochRSI(14,14,3,3), Williams %R(14), Volume confirmation
**Asset Class:** Crypto, Tech Stocks
**Implementation Difficulty:** Easy

### 5. Parabolic SAR with ATR Trailing Stop Hybrid
**Core Concept:** Use Parabolic SAR for entry signals, ATR-based trailing stops for exits.
**Edge/Rationale:** Parabolic SAR catches trends early but gives false signals in chop. ATR stops adapt to volatility, protecting profits better than fixed SAR reversals.
**Indicators/Data:** Parabolic SAR(0.02,0.2), ATR(14), ATR multiplier (2x-3x)
**Asset Class:** Trending markets (Commodities, Crypto)
**Implementation Difficulty:** Easy

### 6. CCI with Donchian Channel Breakout Filter
**Core Concept:** CCI momentum signals only taken when price breaks Donchian Channel extremes.
**Edge/Rationale:** CCI identifies momentum; Donchian Channels ensure breakout confirmation. Filters range-bound false signals.
**Indicators/Data:** CCI(20), Donchian Channels(20), Volume spike filter
**Asset Class:** Commodities, Forex
**Implementation Difficulty:** Medium

### 7. Momentum Divergence with VWAP Anchoring
**Core Concept:** Identify momentum divergences only when price is extended from VWAP.
**Edge/Rationale:** VWAP represents fair value; extreme deviations with momentum divergence indicate mean-reversion opportunities with statistical edge.
**Indicators/Data:** VWAP (session or rolling), RSI or MACD, Standard deviation bands from VWAP
**Asset Class:** Intraday Equities, Futures
**Implementation Difficulty:** Medium

### 8. Fibonacci Retracement with Volume at Price (VAP)
**Core Concept:** Trade Fibonacci levels only where significant volume has traded historically.
**Edge/Rationale:** Fibonacci levels work because traders watch them. Volume at Price confirms where actual supply/demand exists, validating which Fib levels matter.
**Indicators/Data:** Fibonacci retracements, Volume Profile/Fixed Range Volume Profile, POC (Point of Control)
**Asset Class:** All markets
**Implementation Difficulty:** Medium

### 9. Aroon Oscillator with ADX Trend Filter
**Core Concept:** Aroon signals (trend strength/direction) filtered by ADX threshold.
**Edge/Rationale:** Aroon identifies trend changes early; ADX filters out weak trends. Prevents entries during consolidation.
**Indicators/Data:** Aroon(14), ADX(14) with threshold (typically 25), +DI/-DI
**Asset Class:** Forex, Indices
**Implementation Difficulty:** Easy

### 10. Chaikin Money Flow with Price Action Patterns
**Core Concept:** CMF accumulation/distribution signals confirmed by candlestick patterns.
**Edge/Rationale:** CMF shows institutional money flow; candlestick patterns show immediate sentiment. Together they confirm genuine buying/selling pressure.
**Indicators/Data:** CMF(20), Engulfing patterns, Pin bars, Doji at extremes
**Asset Class:** Equities, ETFs
**Implementation Difficulty:** Medium

### 11. Rate of Change (ROC) with Moving Average Envelope
**Core Concept:** ROC momentum signals when price touches moving average envelope extremes.
**Edge/Rationale:** ROC measures speed of price change; envelopes define statistical extremes. Captures momentum exhaustion at overextended levels.
**Indicators/Data:** ROC(12 or 25), Moving Average Envelope (20-period SMA ± 3-5%), Volume
**Asset Class:** All markets
**Implementation Difficulty:** Easy

### 12. Ultimate Oscillator with Support/Resistance Zones
**Core Concept:** Ultimate Oscillator signals (multi-timeframe momentum) at key S/R levels.
**Edge/Rationale:** Ultimate Oscillator reduces false signals by weighting three timeframes. Combined with S/R, it identifies high-probability reversal zones.
**Indicators/Data:** Ultimate Oscillator(7,14,28), Horizontal S/R levels, Swing highs/lows
**Asset Class:** Swing trading all markets
**Implementation Difficulty:** Medium

### 13. TRIX with Price Momentum Divergence
**Core Concept:** TRIX (triple-smoothed EMA rate of change) with price divergence analysis.
**Edge/Rationale:** TRIX filters noise better than standard momentum oscillators. Divergences indicate sustainable trend changes, not just pullbacks.
**Indicators/Data:** TRIX(15,9), Price, Volume trend
**Asset Class:** Equities, Indices
**Implementation Difficulty:** Medium

### 14. Commodity Channel Index with Historical Volatility Percentile
**Core Concept:** CCI signals filtered by current volatility regime (high vs low percentiles).
**Edge/Rationale:** CCI behaves differently in high vs low volatility. Filtering by HV percentile adapts strategy to current market conditions.
**Indicators/Data:** CCI(20), Historical Volatility(20), HV percentile ranking
**Asset Class:** Commodities, Crypto
**Implementation Difficulty:** Medium

### 15. Detrended Price Oscillator with Cycle Analysis
****Core Concept:** DPO (removes trend to show cycles) combined with Hurst cycle analysis.
**Edge/Rationale:** Markets exhibit cyclical behavior. DPO reveals cycles; Hurst analysis identifies dominant cycle lengths for timing.
**Indicators/Data:** DPO(20), Hurst Exponent, Dominant cycle detection
**Asset Class:** All cyclical markets
**Implementation Difficulty:** Hard

---

## Category 2: Multi-Timeframe Confluence Ideas (Strategies 16-30)

### 16. Triple Screen Trading System (Modernized)
**Core Concept:** Trend on weekly, momentum on daily, entry on 4H/1H using different indicator types per timeframe.
**Edge/Rationale:** Each timeframe answers a different question: direction, timing, execution. Reduces counter-trend trades.
**Indicators/Data:** Weekly: 13 EMA slope; Daily: MACD histogram; 4H: RSI or Stochastic
**Asset Class:** All markets
**Implementation Difficulty:** Medium

### 17. Higher Timeframe Order Block with Lower Timeframe Entry
**Core Concept:** Identify institutional order blocks on daily/4H, enter on 15M/5M confirmation.
**Edge/Rationale:** Order blocks represent where smart money transacted. Lower timeframe entries provide tight risk management.
**Indicators/Data:** Order Block detection (fair value gaps, imbalance), 15M breaker blocks
**Asset Class:** Forex, Crypto, Futures
**Implementation Difficulty:** Hard

### 18. Weekly VWAP with Daily Deviation Trades
**Core Concept:** Trade mean reversion when daily price extends beyond standard deviations from weekly VWAP.
**Edge/Rationale:** Weekly VWAP represents longer-term fair value. Extreme deviations tend to revert, especially in range-bound markets.
**Indicators/Data:** Weekly VWAP, Daily closes, 2-3 standard deviation bands
**Asset Class:** Equities, ETFs
**Implementation Difficulty:** Medium

### 19. Monthly Pivot Points with Weekly Trend Filter
**Core Concept:** Trade bounces off monthly pivot levels (S1, R1, etc.) in direction of weekly trend.
**Edge/Rationale:** Monthly pivots are widely watched. Weekly trend ensures alignment with larger money flow.
**Indicators/Data:** Monthly Pivot Points (classic or Fibonacci), Weekly EMA slope, ADX
**Asset Class:** Forex, Indices
**Implementation Difficulty:** Easy

### 20. 4H Structure Break with 1M Order Flow Confirmation
**Core Concept:** Wait for 4H structural break (higher high/low), confirm with 1-minute order flow (delta, volume imbalance).
**Edge/Rationale:** Structure breaks indicate trend changes; order flow confirms genuine buying/selling pressure vs stop runs.
**Indicators/Data:** 4H swing analysis, 1M Volume Delta, Cumulative Delta, Footprint charts
**Asset Class:** Futures, Crypto
**Implementation Difficulty:** Hard

### 21. Daily ATR with Hourly Volatility Compression
**Core Concept:** When daily ATR is below average (compression), trade hourly Bollinger Band squeezes.
**Edge/Rationale:** Volatility is mean-reverting. Compression periods often precede expansion. Hourly squeezes time entries.
**Indicators/Data:** Daily ATR(14), ATR percentile, Hourly Bollinger Band Width, BandWidth < 6%
**Asset Class:** All markets
**Implementation Difficulty:** Medium

### 22. Weekly RSI with Daily Hidden Divergence
**Core Concept:** Weekly RSI in trend zone (>50 bullish, <50 bearish), trade daily hidden divergences in that direction.
**Edge/Rationale:** Hidden divergences indicate trend continuation. Weekly context ensures trading with the larger trend.
**Indicators/Data:** Weekly RSI(14), Daily RSI hidden divergence detection, Trend line analysis
**Asset Class:** Swing trading all markets
**Implementation Difficulty:** Medium

### 23. Monthly MACD with Weekly Zero Line Reject
**Core Concept:** Monthly MACD above zero (bullish), trade weekly pullbacks to zero line that hold.
**Edge/Rationale:** Monthly MACD defines major trend. Weekly zero line rejects are high-probability continuation entries.
**Indicators/Data:** Monthly MACD(12,26,9), Weekly MACD zero line, Histogram confirmation
**Asset Class:** Equities, Indices, ETFs
**Implementation Difficulty:** Easy

### 24. Quarterly Seasonality with Monthly Technical Setup
**Core Concept:** Combine historical seasonal patterns (quarterly) with monthly technical confirmations.
**Edge/Rationale:** Seasonality provides statistical edge; technicals provide timing. Together they create high-confluence setups.
**Indicators/Data:** Seasonal charts (15-20 year average), Monthly candlestick patterns, Monthly momentum
**Asset Class:** Commodities, Seasonal equities
**Implementation Difficulty:** Medium

### 25. Yearly Opening Range with Quarterly Re-tests
**Core Concept:** Trade re-tests of yearly opening range breakout levels on quarterly timeframe.
**Edge/Rationale:** Yearly opening range breakouts are significant. Quarterly re-tests offer lower-risk entry points.
**Indicators/Data:** Yearly OHLC, Quarterly closes relative to yearly range, Volume on re-test
**Asset Class:** All markets
**Implementation Difficulty:** Medium

### 26. 3-Day Rolling VWAP with 1-Hour Deviation Scalps
**Core Concept:** Short-term mean reversion when 1H price extends from 3-day VWAP with momentum divergence.
**Edge/Rationale:** 3-day VWAP captures recent fair value. Scalping deviations works in range-bound, high-liquidity environments.
**Indicators/Data:** 3-Day VWAP, 1H RSI or MACD, Standard deviation bands
**Asset Class:** Liquid futures, Major forex pairs
**Implementation Difficulty:** Medium

### 27. Weekly Fibonacci Extension with Daily Confluence Zone
**Core Concept:** Weekly Fibonacci extension targets (161.8%, 261.8%) where daily structure also aligns.
**Edge/Rationale:** Multiple timeframe confluence at extension levels creates strong reaction zones for profit-taking or reversal.
**Indicators/Data:** Weekly Fibonacci extensions, Daily support/resistance, Daily trend lines
**Asset Class:** Trending markets
**Implementation Difficulty:** Easy

### 28. Monthly Bollinger Band Walk with Weekly Pullback Entries
**Core Concept:** Price walking monthly Bollinger Bands (strong trend), enter on weekly pullbacks to middle band.
**Edge/Rationale:** Band walks indicate strong trends. Weekly pullbacks offer better entries than chasing.
**Indicators/Data:** Monthly Bollinger Bands(20,2), Weekly closes, Weekly volume
**Asset Class:** Strong trending markets (Crypto, Tech stocks)
**Implementation Difficulty:** Medium

### 29. 8H (Custom) Session Analysis with 30M Execution
**Core Concept:** Define custom 8-hour sessions (Asian, London, NY), trade session highs/lows on 30M confirmation.
**Edge/Rationale:** Different sessions have different characteristics. Session levels are defended by algos and day traders.
**Indicators/Data:** 8H session OHLC, 30M breakout/breakdown confirmation, Session volume profile
**Asset Class:** Forex, Crypto (24H markets)
**Implementation Difficulty:** Medium

### 30. Decade Chart Structure with Yearly Execution
**Core Concept:** Identify major decade-long patterns (cup and handle, triangles), execute on yearly confirmations.
**Edge/Rationale:** Ultra-long-term patterns have massive implications. Yearly entries manage risk while capturing major moves.
**Indicators/Data:** Decade log-scale charts, Yearly candlestick patterns, Yearly moving averages
**Asset Class:** Indices, Commodities, Long-term holdings
**Implementation Difficulty:** Easy (patience required)

---

## Category 3: Market Microstructure Exploitation (Strategies 31-45)

### 31. Bid-Ask Bounce Scalping
**Core Concept:** Scalp the natural oscillation between bid and ask in high-liquidity, low-spread markets.
**Edge/Rationale:** Market makers earn the spread; nimble traders can capture micro-moves within the spread during active periods.
**Indicators/Data:** Level II data, Time & Sales, Bid-Ask spread monitoring, Order book depth
**Asset Class:** Liquid futures, Major forex pairs, Large-cap equities
**Implementation Difficulty:** Hard

### 32. Stop Hunt Reversal
**Core Concept:** Identify likely stop-loss clusters (swing highs/lows, round numbers), fade the breakout.
**Edge/Rationale:** Smart money hunts stops before reversing. Breakouts that quickly reverse with volume indicate stop runs.
**Indicators/Data:** Swing point analysis, Round number levels, Volume profile, Reversal candlestick patterns
**Asset Class:** Forex, Crypto, Retail-heavy markets
**Implementation Difficulty:** Hard

### 33. Iceberg Order Detection
**Core Concept:** Detect hidden large orders (icebergs) by analyzing volume at price and order book refresh patterns.
**Edge/Rationale:** Icebergs indicate institutional intent. Trading with detected icebergs aligns with large player direction.
**Indicators/Data:** Level II refresh analysis, Volume at price anomalies, Tape reading
**Asset Class:** Futures, Large-cap equities
**Implementation Difficulty:** Very Hard

### 34. Opening Auction Imbalance Trading
**Core Concept:** Trade pre-market auction imbalances (indicated by exchange data) at market open.
**Edge/Rationale:** Auction imbalances predict opening direction. The edge is in execution speed and post-open management.
**Indicators/Data:** Exchange auction imbalance data, Pre-market volume, Opening print analysis
**Asset Class:** Equities (NYSE, NASDAQ)
**Implementation Difficulty:** Hard

### 35. Closing Cross Momentum
**Core Concept:** Capture momentum into the closing auction based on late-day order flow and imbalance.
**Edge/Rationale:** MOC (Market on Close) orders create predictable flows. Index rebalancing days offer enhanced opportunities.
**Indicators/Data:** NYSE imbalance data (3:50 PM), MOC order flow estimates, Last 30-minute trend
**Asset Class:** Equities, ETFs
**Implementation Difficulty:** Hard

### 36. Dark Pool Print Analysis
**Core Concept:** Analyze delayed dark pool prints to identify institutional accumulation/distribution.
**Edge/Rationale:** Dark pools hide intent but eventually print. Analyzing print size, price, and timing reveals institutional activity.
**Indicators/Data:** Dark pool print feed, Print size analysis, Price relative to lit markets
**Asset Class:** Equities
**Implementation Difficulty:** Hard

### 37. HFT Microstructure Alpha
**Core Concept:** Exploit predictable HFT behaviors: quote stuffing detection, latency arbitrage signals.
**Edge/Rationale:** HFTs create micro-patterns. Detecting their activity provides short-term predictive signals.
**Indicators/Data:** Sub-second order book analysis, Quote cancellation rates, Trade-to-order ratios
**Asset Class:** Highly liquid futures, equities
**Implementation Difficulty:** Very Hard

### 38. Liquidity Void Fill Trading
**Core Concept:** Identify liquidity voids (gaps in volume profile) and trade the fill when price enters the void.
**Edge/Rationale:** Markets dislike voids. Price often accelerates through voids then reverses when filled.
**Indicators/Data:** Volume Profile analysis, Single prints, Low volume nodes
**Asset Class:** Futures, Crypto
**Implementation Difficulty:** Medium

### 39. Tick Chart Divergence
**Core Concept:** Use tick-based charts (not time-based) to identify divergences invisible on standard charts.
**Edge/Rationale:** Tick charts filter time-based noise. Divergences on tick charts indicate genuine exhaustion.
**Indicators/Data:** Tick charts (1000, 2000 ticks), Tick-based RSI/MACD, Volume delta
**Asset Class:** All liquid markets
**Implementation Difficulty:** Medium

### 40. Range Extension Failure
**Core Concept:** Trade when initial balance range extension fails (Market Profile concept).
**Edge/Rationale:** Failed range extensions often lead to range days or reversals. Captures the failed breakout.
**Indicators/Data:** Initial Balance (first hour range), Range extension attempts, TPO (Time Price Opportunity) analysis
**Asset Class:** Futures (especially index futures)
**Implementation Difficulty:** Hard

### 41. Volume Delta Divergence at Extremes
**Core Concept:** Price makes new extreme but volume delta (buy vs sell volume) disagrees.
**Edge/Rationale:** Delta divergence at highs/lows indicates absorption. Smart money is taking the other side.
**Indicators/Data:** Volume Delta (per bar), Cumulative Volume Delta, Footprint charts
**Asset Class:** Futures, Crypto
**Implementation Difficulty:** Hard

### 42. Order Book Imbalance Scalping
**Core Concept:** Scalp based on real-time order book imbalances (bid/ask ratio > threshold).
**Edge/Rationale:** Short-term order flow predicts immediate price direction. Requires fast execution.
**Indicators/Data:** Level II data, Bid/Ask ratio, Order book depth analysis
**Asset Class:** Liquid futures, Major forex
**Implementation Difficulty:** Very Hard

### 43. Trade-Through Rejection
**Core Concept:** Trade when price briefly trades through a level then immediately rejects (false breakout).
**Edge/Rationale:** Trade-throughs trigger stops and attract breakout traders. Quick rejection traps them.
**Indicators/Data:** Tick data, Rejection candles, Volume on rejection
**Asset Class:** All markets
**Implementation Difficulty:** Medium

### 44. Time-Weighted Average Price (TWAP) Detection
**Core Concept:** Detect TWAP algorithms and trade alongside them for free ride.
**Edge/Rationale:** TWAPs create predictable volume patterns. Identifying them allows alignment with large flow.
**Indicators/Data:** Volume pattern analysis, Regular interval detection, Price impact analysis
**Asset Class:** Equities, Futures
**Implementation Difficulty:** Hard

### 45. Exchange Dislocation Arbitrage
**Core Concept:** Exploit temporary price dislocations between related exchanges or instruments.
**Edge/Rationale:** Brief dislocations occur due to latency, order flow differences. Fast capture yields risk-free profit.
**Indicators/Data:** Multi-exchange price feeds, Latency monitoring, Correlation analysis
**Asset Class:** Crypto (multi-exchange), ADR/ORD pairs
**Implementation Difficulty:** Very Hard

---

## Category 4: Behavioral Finance Edges (Strategies 46-60)

### 46. Fear-Greed Mean Reversion
**Core Concept:** Trade extreme readings on CNN Fear & Greed Index with technical confirmation.
**Edge/Rationale:** Extreme sentiment indicates crowded positioning. Mean reversion follows extreme emotions.
**Indicators/Data:** Fear & Greed Index, VIX, Put/Call ratio, RSI confirmation
**Asset Class:** Indices, ETFs (SPY, QQQ)
**Implementation Difficulty:** Easy

### 47. Retail FOMO Fade
**Core Concept:** Fade parabolic moves with high retail participation (measured by social media, small-lot trades).
**Edge/Rationale:** Retail FOMO marks tops; retail panic marks bottoms. Contrarian edge against emotional traders.
**Indicators/Data:** Social sentiment (Twitter, Reddit), Small lot trade percentage, Unusual volume
**Asset Class:** Meme stocks, Crypto, Hot sectors
**Implementation Difficulty:** Medium

### 48. Analyst Upgrade/Downgrade Momentum
**Core Concept:** Trade the momentum following earnings estimate revisions, not the initial rating change.
**Edge/Rationale:** Estimate revisions have more persistence than ratings. The trend of revisions matters most.
**Indicators/Data:** EPS estimate revision trend, Surprise history, Consensus changes
**Asset Class:** Individual equities
**Implementation Difficulty:** Medium

### 49. Earnings Announcement Premium Decay
**Core Concept:** Sell volatility before earnings when implied volatility is excessively high, buy after crush.
**Edge/Rationale:** IV typically overstates actual move. Capturing the volatility risk premium.
**Indicators/Data:** Implied volatility percentile, Historical earnings moves, Straddle pricing
**Asset Class:** Options on individual equities
**Implementation Difficulty:** Medium

### 50. Post-Earnings Announcement Drift (PEAD)
**Core Concept:** Buy stocks with positive earnings surprises, sell negative surprises; hold for weeks.
**Edge/Rationale:** Markets underreact to earnings news. Drift persists due to gradual information diffusion.
**Indicators/Data:** Earnings surprise %, SUE (Standardized Unexpected Earnings), Revenue surprise
**Asset Class:** Equities
**Implementation Difficulty:** Easy

### 51. Weekend Effect Exploitation
**Core Concept:** Capture the Monday effect (often negative) and Friday effect (often positive) systematically.
**Edge/Rationale:** Weekend risk premium, rebalancing flows, and sentiment shifts create predictable patterns.
**Indicators/Data:** Day-of-week analysis, Friday/Monday returns, Pre-holiday patterns
**Asset Class:** Indices, broad equities
**Implementation Difficulty:** Easy

### 52. Turn-of-Month Effect
**Core Concept:** Trade the turn-of-month effect (last day of month to first few days of next month).
**Edge/Rationale:** Pension fund flows, window dressing, and rebalancing create predictable patterns.
**Indicators/Data:** Calendar day analysis, Pension fund flow estimates, Month-end positioning
**Asset Class:** Indices, ETFs
**Implementation Difficulty:** Easy

### 53. January Effect (Small Cap)
**Core Concept:** Buy small caps in late December, sell in January; tax loss selling reversal.
**Edge/Rationale:** Tax loss selling depresses small caps in December; rebound in January as selling stops.
**Indicators/Data:** Small cap index, Tax loss selling indicators, December performance
**Asset Class:** Small cap equities, Russell 2000
**Implementation Difficulty:** Easy

### 54. Momentum Crashes (Momentum Reversal)
**Core Concept:** Identify when momentum strategies are crowded and likely to crash; fade momentum.
**Edge/Rationale:** Momentum crashes occur during market stress and recoveries. Contarian to momentum.
**Indicators/Data:** Momentum factor performance, Market stress indicators, Correlation spikes
**Asset Class:** Factor ETFs, momentum stocks
**Implementation Difficulty:** Hard

### 55. Disposition Effect Exploitation
**Core Concept:** Identify stocks near round numbers where retail is likely to sell winners (resistance) or hold losers (support).
**Edge/Rationale:** Disposition effect creates predictable support/resistance at psychological levels.
**Indicators/Data:** Round number proximity, Volume profile, Price history analysis
**Asset Class:** Retail-heavy stocks, Crypto
**Implementation Difficulty:** Medium

### 56. Herding Detection and Fade
**Core Concept:** Detect herding behavior through correlation spikes and sector uniformity, then fade.
**Edge/Rationale:** Herding leads to inefficiencies. Extreme correlation indicates crowded trades ready to unwind.
**Indicators/Data:** Cross-correlation matrix, Sector dispersion, Herding indices
**Asset Class:** Sectors, thematic ETFs
**Implementation Difficulty:** Hard

### 57. Overconfidence in Trends (Trend Exhaustion)
**Core Concept:** Identify when trend followers are overconfident (steep slopes, high volume) for reversal trades.
**Edge/Rationale:** Overconfidence leads to trend extensions that exhaust themselves. Fade parabolic moves.
**Indicators/Data:** Trend slope angle, Volume trend, Sentiment extremes, Positioning data
**Asset Class:** All trending markets
**Implementation Difficulty:** Medium

### 58. Anchoring Bias at Round Numbers
**Core Concept:** Trade bounces and breaks of round numbers where anchoring creates order clusters.
**Edge/Rationale:** Traders anchor to round numbers, creating self-fulfilling support/resistance.
**Indicators/Data:** Round number levels, Volume at round numbers, Options open interest at strikes
**Asset Class:** All markets, especially Forex and Crypto
**Implementation Difficulty:** Easy

### 59. Loss Aversion Reversal Patterns
**Core Concept:** Identify capitulation patterns where loss aversion causes panic selling (V-shaped bottoms).
**Edge/Rationale:** Loss aversion causes exaggerated downside. Panic selling creates buying opportunities.
**Indicators/Data:** Downside volume spikes, VIX spikes, Put/Call extremes, RSI < 20
**Asset Class:** All markets during stress
**Implementation Difficulty:** Medium

### 60. Confirmation Bias Breakout Failure
**Core Concept:** Fade breakouts that occur on weak volume after prolonged consolidation (confirmation bias traps).
**Edge/Rationale:** Traders seeking confirmation enter late on weak breakouts, providing liquidity for smart money exit.
**Indicators/Data:** Consolidation duration, Breakout volume vs average, False breakout pattern recognition
**Asset Class:** All markets
**Implementation Difficulty:** Medium

---

## Category 5: Alternative Data Signals (Strategies 61-75)

### 61. Satellite Imagery (Retail Parking Lots)
**Core Concept:** Use satellite parking lot data to predict retail earnings before announcements.
**Edge/Rationale:** Parking lot traffic precedes reported sales. Alternative data edge before market knows.
**Indicators/Data:** Satellite parking lot counts (RS Metrics, Orbital Insight), YoY change, Quarterly trends
**Asset Class:** Retail equities, REITs
**Implementation Difficulty:** Hard (data access)

### 62. Credit Card Transaction Aggregation
**Core Concept:** Aggregate anonymized credit card data to predict company revenue trends.
**Edge/Rationale:** Real-time spending data precedes quarterly reports. Early indicator of performance.
**Indicators/Data:** Credit card panel data (Second Measure, Earnest), Spending velocity, Category trends
**Asset Class:** Consumer discretionary, restaurants, retail
**Implementation Difficulty:** Hard (expensive data)

### 63. Web Traffic Momentum
**Core Concept:** Track website traffic trends (SimilarWeb, Alexa) to predict digital business performance.
**Edge/Rationale:** Web traffic correlates with digital revenue. Changes precede earnings announcements.
**Indicators/Data:** Website traffic estimates, App download data, Engagement metrics
**Asset Class:** E-commerce, SaaS, digital businesses
**Implementation Difficulty:** Medium

### 64. Job Posting Velocity
**Core Concept:** Analyze job posting growth/decline as leading indicator of company expansion/contraction.
**Edge/Rationale:** Hiring precedes revenue growth; layoffs precede decline. Real-time labor market signal.
**Indicators/Data:** Job posting data (LinkUp, Burning Glass), Posting velocity, Role types
**Asset Class:** Growth equities, staffing companies
**Implementation Difficulty:** Medium

### 65. Social Media Sentiment Alpha
**Core Concept:** Analyze Twitter, Reddit, StockTwits sentiment for predictive stock signals.
**Edge/Rationale:** Crowd sentiment contains information. Processing at scale extracts alpha.
**Indicators/Data:** NLP sentiment scores, Mention volume, Influencer tracking, Emotion analysis
**Asset Class:** Retail-heavy stocks, crypto, meme stocks
**Implementation Difficulty:** Hard (NLP infrastructure)

### 66. Supply Chain Data (Bill of Materials)
**Core Concept:** Track component orders and shipping data to predict manufacturing output.
**Edge/Rationale:** Supply chain data is upstream from reported revenue. Predicts demand changes early.
**Indicators/Data:** Import/export data, Shipping manifests, Component order trends (Panjiva, ImportGenius)
**Asset Class:** Manufacturing, semiconductors, industrials
**Implementation Difficulty:** Hard

### 67. Google Trends Arbitrage
**Core Concept:** Use Google search trends to predict consumer interest and stock performance.
**Edge/Rationale:** Search interest precedes purchase intent. Correlates with revenue for consumer-facing companies.
**Indicators/Data:** Google Trends API, Search volume indices, Related queries analysis
**Asset Class:** Consumer brands, pharmaceuticals (symptom searches), entertainment
**Implementation Difficulty:** Easy

### 68. Patent Filing Momentum
**Core Concept:** Track patent filings and citations as leading indicator of innovation and future growth.
**Edge/Rationale:** R&D investment precedes product launches. Patent activity indicates innovation cycles.
**Indicators/Data:** USPTO patent data, Citation analysis, Patent quality scores
**Asset Class:** Tech, biotech, innovation-driven sectors
**Implementation Difficulty:** Medium

### 69. ESG Score Changes
**Core Concept:** Trade ESG rating upgrades/downgrades before they become widely priced.
**Edge/Rationale:** ESG flows are massive and growing. Rating changes drive institutional rebalancing.
**Indicators/Data:** ESG rating changes (MSCI, Sustainalytics), ESG fund flows, Exclusion list changes
**Asset Class:** Large caps, ESG ETFs
**Implementation Difficulty:** Medium

### 70. Options Flow Unusual Activity
**Core Concept:** Detect unusual options activity as signal of informed trading.
**Edge/Rationale:** Informed traders use options for leverage. Unusual flow can predict moves.
**Indicators/Data:** Options volume vs OI, Unusual volume alerts, Sweep detection, Block trades
**Asset Class:** Individual equities, ETFs
**Implementation Difficulty:** Medium

### 71. Insider Cluster Buying
**Core Concept:** Multiple insiders buying within short window indicates strong conviction.
**Edge/Rationale:** Insiders have information advantage. Cluster buying is high-confidence signal.
**Indicators/Data:** Form 4 filings, Cluster detection (3+ insiders, 30-day window), Purchase size analysis
**Asset Class:** Individual equities
**Implementation Difficulty:** Easy

### 72. Weather Derivatives Correlation
**Core Concept:** Use weather forecasts to trade correlated commodities and equities.
**Edge/Rationale:** Weather affects agriculture, energy, insurance. Forecasts predict demand changes.
**Indicators/Data:** Weather forecasts (NOAA), Degree days, Precipitation forecasts, Storm tracking
**Asset Class:** Agriculture, energy, insurance, utilities
**Implementation Difficulty:** Medium

### 73. Shipping Container Tracking
**Core Concept:** Track container shipping volumes and rates as global trade indicator.
**Edge/Rationale:** Container volumes are real-time trade indicators. Precedes reported economic data.
**Indicators/Data:** Container throughput (port data), Freight rates (Drewry, Freightos), Container availability
**Asset Class:** Shipping stocks, trade-sensitive equities, commodities
**Implementation Difficulty:** Medium

### 74. App Store Ranking Momentum
**Core Concept:** Track app store rankings to predict mobile-first company performance.
**Edge/Rationale:** App rankings correlate with user acquisition and revenue. Changes precede earnings.
**Indicators/Data:** App Annie/Sensor Tower data, Ranking changes, Download velocity, Revenue estimates
**Asset Class:** Mobile gaming, consumer apps, platform companies
**Implementation Difficulty:** Medium

### 75. Cryptocurrency On-Chain Analysis
**Core Concept:** Use blockchain data (exchange flows, whale movements, network activity) to predict price.
**Edge/Rationale:** On-chain data is unique to crypto. Reveals holder behavior and supply dynamics.
**Indicators/Data:** Exchange inflows/outflows, Whale wallet tracking, Network hash rate, Active addresses
**Asset Class:** Cryptocurrencies
**Implementation Difficulty:** Medium

---

## Category 6: Cross-Asset Arbitrage Concepts (Strategies 76-85)

### 76. Gold/Real Rates Divergence Trade
**Core Concept:** Trade the relationship between gold and real interest rates (TIPS yields).
**Edge/Rationale:** Gold is inversely correlated with real rates. Divergences create mean-reversion opportunities.
**Indicators/Data:** Gold price, 10Y TIPS yield, Real rate percentile, Z-score of relationship
**Asset Class:** Gold, TIPS, gold miners
**Implementation Difficulty:** Easy

### 77. USD/CNY vs Copper Correlation Break
**Core Concept:** Trade when copper and USD/CNY decouple from their typical inverse correlation.
**Edge/Rationale:** China is dominant copper consumer. Currency and commodity should correlate. Breaks indicate opportunities.
**Indicators/Data:** Copper price, USD/CNY rate, 90-day correlation, Deviation from mean correlation
**Asset Class:** Copper futures, FX pairs, mining stocks
**Implementation Difficulty:** Medium

### 78. VIX Contango/Backwardation Roll
**Core Concept:** Capture roll yield in VIX futures term structure.
**Edge/Rationale:** VIX futures are usually in contango. Rolling down the curve generates yield in stable markets.
**Indicators/Data:** VIX futures term structure, M1/M2 spread, Roll yield calculation
**Asset Class:** VIX futures, VIX ETFs/ETNs
**Implementation Difficulty:** Medium

### 79. Crack Spread Reversion
**Core Concept:** Trade the refining margin (crack spread) between crude oil and refined products.
**Edge/Rationale:** Crack spreads mean-revert around refinery operating costs. Extreme spreads indicate opportunities.
**Indicators/Data:** Crude oil (WTI/Brent), Gasoline, Heating oil, 3:2:1 crack spread
**Asset Class:** Energy futures, refinery stocks
**Implementation Difficulty:** Medium

### 80. Yield Curve Steepener/Flattener
**Core Concept:** Trade changes in yield curve slope using futures or options.
**Edge/Rationale:** Yield curve shape reflects economic expectations. Systematic moves create opportunities.
**Indicators/Data:** 2Y/10Y spread, 5Y/30Y spread, Fed policy expectations, Economic surprise index
**Asset Class:** Treasury futures, interest rate options
**Implementation Difficulty:** Medium

### 81. Sector Pairs Trading (Relative Value)
**Core Concept:** Trade mean reversion between correlated sectors (e.g., XLY vs XLP).
**Edge/Rationale:** Sector relationships are stable long-term. Short-term divergences create pairs opportunities.
**Indicators/Data:** Sector ETF prices, Cointegration analysis, Z-score of spread, Ratio bands
**Asset Class:** Sector ETFs
**Implementation Difficulty:** Medium

### 82. ADR vs Local Share Arbitrage
**Core Concept:** Trade price discrepancies between ADRs and their underlying local shares.
**Edge/Rationale:** ADRs and local shares represent same asset. Temporary dislocations create arbitrage.
**Indicators/Data:** ADR price, Local share price (converted), FX rate, Borrow costs
**Asset Class:** ADRs, international equities
**Implementation Difficulty:** Hard

### 83. ETF vs NAV Arbitrage
**Core Concept:** Trade when ETFs deviate significantly from their net asset value.
**Edge/Rationale:** Authorized participants arbitrage ETF/NAV gaps. Temporary dislocations offer opportunities.
**Indicators/Data:** ETF price, Real-time NAV estimate, Premium/discount history, Creation/redemption data
**Asset Class:** ETFs (especially international, fixed income, less liquid)
**Implementation Difficulty:** Hard

### 84. Commodity Calendar Spread
**Core Concept:** Trade spreads between different expiration months of the same commodity.
**Edge/Rationale:** Calendar spreads reflect storage costs, seasonality, and supply/demand timing.
**Indicators/Data:** Front month vs back month prices, Storage cost estimates, Inventory data, Seasonality
**Asset Class:** Commodity futures (especially energy, agriculture)
**Implementation Difficulty:** Medium

### 85. Credit-Equity Divergence
**Core Concept:** Trade when credit spreads and equity prices send conflicting signals.
**Edge/Rationale:** Credit and equity should correlate. Divergences often resolve with equity following credit.
**Indicators/Data:** CDS spreads, Corporate bond spreads, Equity price, Credit-equity correlation
**Asset Class:** Individual equities, corporate bonds, CDS
**Implementation Difficulty:** Hard

---

## Category 7: Volatility Regime Strategies (Strategies 86-93)

### 86. Volatility Targeting (Constant Vol)
**Core Concept:** Adjust position size dynamically to maintain constant portfolio volatility.
**Edge/Rationale:** Volatility is predictable (clustering). Targeting constant vol improves risk-adjusted returns.
**Indicators/Data:** Realized volatility (20-day), Target volatility level, Position sizing algorithm
**Asset Class:** All markets
**Implementation Difficulty:** Easy

### 87. GARCH Volatility Forecasting
**Core Concept:** Use GARCH models to predict future volatility and adjust positions accordingly.
**Edge/Rationale:** GARCH captures volatility clustering and mean reversion. Better than simple historical vol.
**Indicators/Data:** GARCH(1,1) or EGARCH model, Residual analysis, Forecast confidence bands
**Asset Class:** All markets
**Implementation Difficulty:** Hard

### 88. VIX Spike Mean Reversion
**Core Concept:** Buy volatility after VIX spikes > 50% above moving average, sell when normalized.
**Edge/Rationale:** Volatility is mean-reverting. Spikes typically overstate actual risk and revert.
**Indicators/Data:** VIX level, VIX 20-day moving average, VIX percentile, Realized volatility
**Asset Class:** VIX futures, options, volatility ETPs
**Implementation Difficulty:** Medium

### 89. Volatility Regime Switching
**Core Concept:** Use different strategies in high vs low volatility regimes (regime detection).
**Edge/Rationale:** Strategy performance varies by regime. Detecting regimes allows strategy selection.
**Indicators/Data:** Volatility regime detection (Markov switching, percentiles), Strategy performance by regime
**Asset Class:** All markets
**Implementation Difficulty:** Hard

### 90. Straddle Strangle Swaps (Volatility Skew)
**Core Concept:** Trade volatility skew by selling expensive wings and buying cheap ATM options.
**Edge/Rationale:** Skew reflects crash risk premium. Systematically harvesting skew premium.
**Indicators/Data:** Volatility skew (25 delta put vs call), Skew percentile, Term structure
**Asset Class:** Options on indices, ETFs
**Implementation Difficulty:** Hard

### 91. Realized vs Implied Volatility Arbitrage
**Core Concept:** Trade when implied volatility significantly diverges from realized volatility.
**Edge/Rationale:** Implied vol typically overstates realized vol. Selling overpriced vol captures risk premium.
**Indicators/Data:** Implied volatility, Realized volatility (trailing), IV-RV spread, Percentile ranking
**Asset Class:** Options markets
**Implementation Difficulty:** Medium

### 92. Volatility Convexity Harvesting
**Core Concept:** Capture volatility of volatility (vol of vol) through VIX options or variance swaps.
**Edge/Rationale:** Vol of vol is persistent and tradeable. Convexity provides tail risk protection.
**Indicators/Data:** VIX of VIX (VVIX), VIX options term structure, Variance swap rates
**Asset Class:** VIX options, volatility derivatives
**Implementation Difficulty:** Very Hard

### 93. Jump Diffusion Detection
**Core Concept:** Detect elevated jump risk through options skew and trade protective structures.
**Edge/Rationale:** Options market prices jump risk. Detecting elevated jump probability allows positioning.
**Indicators/Data:** Options skew steepness, Jump risk estimators, Tail risk indicators
**Asset Class:** Options, tail risk hedges
**Implementation Difficulty:** Hard

---

## Category 8: Liquidity-Based Approaches (Strategies 94-100)

### 94. Liquidity Momentum (Amihud Illiquidity)
**Core Concept:** Trade stocks with improving liquidity (decreasing Amihud ratio) as liquidity begets liquidity.
**Edge/Rationale:** Liquidity improvements attract more participants, creating momentum. Illiquidity premiums reverse.
**Indicators/Data:** Amihud illiquidity ratio, Bid-ask spread trends, Volume trends, Price impact
**Asset Class:** Small-mid cap equities, less liquid ETFs
**Implementation Difficulty:** Medium

### 95. Closing Auction Volume Participation
**Core Concept:** Participate in closing auctions where volume concentrates (MOC, index rebalancing).
**Edge/Rationale:** Closing auctions have price discovery and liquidity. Predictable flows create opportunities.
**Indicators/Data:** MOC imbalance data, Index rebalancing calendar, Closing volume patterns
**Asset Class:** Equities, ETFs
**Implementation Difficulty:** Hard

### 96. Liquidity Black Hole Detection
**Core Concept:** Avoid or fade markets entering liquidity black holes (positive feedback illiquidity).
**Edge/Rationale:** Liquidity can evaporate suddenly. Detecting early signs prevents adverse execution.
**Indicators/Data:** Order book depth trends, Kyle's lambda (price impact), Correlation breakdown
**Asset Class:** All markets during stress
**Implementation Difficulty:** Hard

### 97. High-Frequency Liquidity Provision
**Core Concept:** Provide liquidity through limit orders in high-volume, mean-reverting instruments.
**Edge/Rationale:** Capturing spread while managing adverse selection. Requires fast cancellation.
**Indicators/Data:** Tick data, Queue position, Fill rates, Adverse selection metrics
**Asset Class:** Liquid futures, major forex pairs
**Implementation Difficulty:** Very Hard

### 98. Market Impact Minimization (Optimal Execution)
**Core Concept:** Use optimal execution algorithms (TWAP, VWAP, Implementation Shortfall) to minimize trading costs.
**Edge/Rationale:** Execution quality directly impacts returns. Systematic approaches beat ad-hoc trading.
**Indicators/Data:** Market impact models, Liquidity forecasts, Order book resilience
**Asset Class:** All markets for large orders
**Implementation Difficulty:** Hard

### 99. Liquidity Risk Premium Capture
**Core Concept:** Hold less liquid assets that compensate with higher expected returns (liquidity premium).
**Edge/Rationale:** Investors demand premium for illiquidity. Systematically capturing this premium.
**Indicators/Data:** Liquidity metrics, Turnover, Float, Amihud ratio, Off-exchange volume
**Asset Class:** Small caps, corporate bonds, private markets (if accessible)
**Implementation Difficulty:** Medium

### 100. Flash Crash Detection and Protection
**Core Concept:** Detect microstructure signs of impending flash crashes and flatten exposure.
**Edge/Rationale:** Flash crashes have precursors (order book anomalies, quote stuffing). Detection enables protection.
**Indicators/Data:** Order book anomaly detection, Quote-to-trade ratios, Cancellation rates, Cross-market correlation breakdown
**Asset Class:** All electronic markets
**Implementation Difficulty:** Very Hard

---

## Bonus Strategies (101-110)

### 101. Overnight Gap Fade
**Core Concept:** Fade large overnight gaps based on historical gap fill statistics.
**Edge/Rationale:** Overnight gaps often overreact to news. Mean reversion fills gaps frequently.
**Indicators/Data:** Gap size, Historical fill rate by gap size, Pre-market volume
**Asset Class:** Equities, equity indices
**Implementation Difficulty:** Easy

### 102. Options Gamma Exposure (GEX) Levels
**Core Concept:** Trade around key gamma exposure levels where dealer hedging creates pinning or acceleration.
**Edge/Rationale:** Dealer gamma hedging creates predictable price behavior around strikes.
**Indicators/Data:** Gamma exposure by strike, Put-call wall levels, Zero gamma level
**Asset Class:** Heavily optioned stocks, indices
**Implementation Difficulty:** Hard

### 103. Delta Neutral Volatility Scalping
**Core Concept:** Maintain delta-neutral options portfolio to scalp gamma while hedging directional risk.
**Edge/Rationale:** Captures volatility risk premium while managing directional exposure.
**Indicators/Data:** Portfolio delta, Gamma, Theta, Vega, Rebalancing thresholds
**Asset Class:** Options markets
**Implementation Difficulty:** Hard

### 104. Cross-Sectional Momentum (Relative Strength)
**Core Concept:** Buy strongest assets, sell weakest within a universe (relative momentum).
**Edge/Rationale:** Momentum works cross-sectionally. Winners keep winning relative to losers.
**Indicators/Data:** 12-month returns, 6-month returns, Risk-adjusted momentum, Sector momentum
**Asset Class:** Equity universe, sector ETFs, country ETFs
**Implementation Difficulty:** Easy

### 105. Time-Series Momentum (Trend Following)
**Core Concept:** Go long assets with positive 12-month returns, short negative (absolute momentum).
**Edge/Rationale:** Trends persist across asset classes. Diversified trend following captures crisis alpha.
**Indicators/Data:** 12-month return sign, Risk-adjusted position sizing, Portfolio construction
**Asset Class:** Diversified futures, ETFs across all asset classes
**Implementation Difficulty:** Medium

### 106. Carry Trade (FX)
**Core Concept:** Borrow in low-yield currencies, lend in high-yield currencies.
**Edge/Rationale:** Interest rate differential provides carry. Works until sudden unwinds (peso problem).
**Indicators/Data:** Interest rate differentials, Real rates, Volatility, Risk sentiment
**Asset Class:** G10 and EM FX pairs
**Implementation Difficulty:** Medium

### 107. Term Structure Carry (Commodities)
**Core Concept:** Buy backwardated commodities, sell contangoed commodities (roll yield).
**Edge/Rationale:** Term structure reflects storage costs and convenience yield. Capturing roll yield.
**Indicators/Data:** Futures curve shape, Roll yield calculation, Inventory data
**Asset Class:** Commodity futures
**Implementation Difficulty:** Medium

### 108. Quality Minus Junk (QMJ)
**Core Concept:** Buy high-quality stocks (profitable, stable, low leverage), sell low-quality.
**Edge/Rationale:** Quality factor has persistent premium. Quality outperforms in drawdowns.
**Indicators/Data:** Profitability metrics, Earnings stability, Leverage, Growth measures
**Asset Class:** Equities
**Implementation Difficulty:** Easy

### 109. Betting Against Beta (BAB)
**Core Concept:** Buy low-beta stocks, sell high-beta stocks (leverage-constrained investors).
**Edge/Rationale:** Leverage constraints cause high-beta to be overpriced. Low-beta outperforms.
**Indicators/Data:** 1-year beta, Volatility, Residual returns
**Asset Class:** Equities
**Implementation Difficulty:** Easy

### 110. Multi-Strategy Ensemble
**Core Concept:** Combine multiple uncorrelated strategies with dynamic risk allocation.
**Edge/Rationale:** No single strategy works all the time. Ensembles reduce drawdowns, improve Sharpe.
**Indicators/Data:** Strategy correlations, Performance metrics, Regime detection, Risk budgeting
**Asset Class:** All markets
**Implementation Difficulty:** Hard

---

## Summary Table

| Category | Count | Difficulty Distribution |
|----------|-------|------------------------|
| Unconventional Indicators | 15 | Easy: 5, Medium: 8, Hard: 2 |
| Multi-Timeframe | 15 | Easy: 4, Medium: 9, Hard: 2 |
| Microstructure | 15 | Medium: 3, Hard: 9, Very Hard: 3 |
| Behavioral Finance | 15 | Easy: 5, Medium: 8, Hard: 2 |
| Alternative Data | 15 | Easy: 1, Medium: 6, Hard: 8 |
| Cross-Asset Arbitrage | 10 | Easy: 1, Medium: 6, Hard: 3 |
| Volatility Regimes | 8 | Easy: 1, Medium: 3, Hard: 3, Very Hard: 1 |
| Liquidity-Based | 7 | Medium: 3, Hard: 3, Very Hard: 1 |
| Bonus | 10 | Easy: 5, Medium: 4, Hard: 1 |
| **Total** | **110** | **Easy: 21, Medium: 56, Hard: 27, Very Hard: 8** |

---

## Implementation Notes

1. **Start with Easy strategies** (21 total) for quick wins and learning
2. **Medium difficulty strategies** (56 total) form the core of a robust trading system
3. **Hard/Very Hard strategies** require significant infrastructure, data access, or expertise
4. **Combine strategies** across categories for diversification
5. **Paper trade first** - all strategies require validation before risking capital
6. **Risk management** is more important than strategy selection

---

*Generated for implementation by trading strategy development agents.*
