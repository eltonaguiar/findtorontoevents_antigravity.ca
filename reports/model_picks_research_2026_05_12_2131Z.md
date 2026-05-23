# Multi-Model Picks Research — Per Asset Class

**Generated:** 2026-05-12 21:31 UTC

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

### qwen3-coder:480b-cloud — Qwen3 Coder 480B (Ollama Cloud)  (elapsed 58.4s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Bitcoin showing strong support at key moving averages with increasing volume confirming accumulation phase
- **ETHUSDT** LONG (swing) — Ethereum breaking out of consolidation pattern with positive network activity metrics and improving relative strength
- **SOLUSDT** SHORT (short-term) — Solana approaching resistance zone with bearish divergence patterns and elevated leverage longs indicating potential reversal
**Factors Used:**
- price action trends
- volume profile analysis
- network hash rate and transaction metrics
- funding rate differentials
- open interest and liquidation levels
**Data Points To Fetch:**
- on-chain exchange flows and net transfers
- miner/net worth entity positioning data
- perpetual futures funding rates across major exchanges
- order book depth and large trade clusters
- macro risk sentiment indicators and USD strength
**Swing Trade Setup:** Enter on confirmed break of key resistance/support with volume confirmation, target based on previous swing highs/lows with trailing stop at recent swing point; hold 3-14 days
**Short Term Setup:** Trade mean reversion at key support/resistance levels with momentum confirmation, exit on opposite momentum signal or when price action exceeds recent volatility range; hold 1-3 days maximum

### deepseek-v3.1:671b-cloud — DeepSeek V3.1 671B (Ollama Cloud)  (elapsed 9.3s)
**Top picks:**
- **BTCUSDT** LONG (swing) — Strong bounce from key support level with increasing spot buying volume.
- **ETHUSDT** LONG (swing) — Showing relative strength against BTC and holding above critical moving average support.
- **SOLUSDT** SHORT (short-term) — Failed to break key resistance and showing signs of weakness on lower timeframes.
**Factors Used:**
- BTC Dominance (BTC.D)
- 14-Day RSI
- Funding Rates
- 200-period Moving Average
- On-Balance Volume (OBV)
**Data Points To Fetch:**
- Perpetual futures funding rate for each symbol
- Spot exchange order book depth
- 1-hour RSI and OBV
- BTC dominance chart
- Key support/resistance levels from volume profile
**Swing Trade Setup:** Enter on a confirmed breakout/breakdown with volume, using a daily/weekly close; exit on a breach of a key moving average or a 2:1 profit-to-loss ratio.
**Short Term Setup:** Enter on a 1-hour or 4-hour candle close confirming the momentum shift; use a tight stop-loss and exit at the nearest significant support/resistance level.

### gpt-oss:120b-cloud — GPT-OSS 120B (Ollama Cloud)  (elapsed 6.5s)
**Top picks:**
- **BTCUSDT** LONG (swing) — On-chain accumulation, bullish funding rates and price above the 20‑EMA suggest upside over the next 2‑4 weeks.
- **ETHUSDT** LONG (short-term) — Strong DeFi activity, rising active addresses and a 4‑hour EMA crossover signal a short‑term rally that can be extended.
- **SOLUSDT** SHORT (short-term) — Overbought RSI, deteriorating on‑chain metrics and negative funding pressure point to a corrective pullback.
**Factors Used:**
- On‑chain metrics (NUPL, MVRV, active addresses)
- Technical EMA crossovers and RSI levels
- Funding rate differentials across perpetual contracts
- Open interest and futures volume
- Market sentiment indicators (Twitter volume, Google Trends)
**Data Points To Fetch:**
- Real‑time price and 4h/1d OHLCV data
- Current funding rates for perpetual futures
- On‑chain activity: active addresses, NUPL, MVRV
- Open interest and liquidations on major futures exchanges
- Crypto volatility index (e.g., BVOL) and implied volatility
**Swing Trade Setup:** Enter long when price closes above the 20‑EMA on the daily chart, the 20‑EMA is above the 50‑EMA, and RSI is between 40‑60; target 10‑15% profit or the next major resistance, with a stop‑loss just below the 20‑EMA.
**Short Term Setup:** Take a 1‑3 day trade on a 4‑hour break of the previous high (long) or low (short) with funding rate in the trade direction, confirm with RSI <30 (short) or >70 (long), and set a stop‑loss 2‑3% away from entry; exit at a 3‑5% gain or on adverse funding shift.

### glm-4.6:cloud — GLM-4.6 (Ollama Cloud)  (elapsed 28.6s)
- PARSE-FAIL
- tail: ``

## EQUITY

### kimi-k2-thinking:cloud — Moonshot Kimi K2 Thinking (Ollama Cloud)  (elapsed ?s)
- ERROR: HTTP Error 500: Internal Server Error

### qwen3-coder:480b-cloud — Qwen3 Coder 480B (Ollama Cloud)  (elapsed 52.3s)
**Top picks:**
- **SPY** LONG (swing) — Strong momentum with support at recent moving averages and positive earnings season outlook
- **NVDA** LONG (short-term) — AI chip leader showing strong relative strength and institutional accumulation
- **SMCI** SHORT (short-term) — Overextended valuation with profit taking pressure after significant run-up
**Factors Used:**
- price_momentum
- relative_strength_index
- earnings_growth_expectations
- institutional_ownership_changes
- volatility_contraction_patterns
**Data Points To Fetch:**
- price_volume_data
- earnings_calendar_and_guidance
- institutional_flow_data
- options_sentiment_indicators
- sector_rotation_metrics
**Swing Trade Setup:** Enter on pullback to 20-day MA with volume confirmation, exit on 50-day MA resistance or trailing stop below recent swing low
**Short Term Setup:** Enter on morning momentum breakouts with strong volume, exit on intraday RSI divergence or 2% move against position

### deepseek-v3.1:671b-cloud — DeepSeek V3.1 671B (Ollama Cloud)  (elapsed 7.0s)
**Top picks:**
- **SPY** LONG (swing) — Strong bullish momentum confirmed by recent breakout above key moving averages on high volume.
- **IWM** LONG (swing) — Small-cap index showing relative strength and potential for catch-up trade in a risk-on environment.
- **TSLA** SHORT (short-term) — Failed breakout attempt at a major resistance level with increasing selling volume indicating weakness.
**Factors Used:**
- RSI (14-period)
- VWAP deviation
- 20/50 EMA crossover
- Sector relative strength
- ATR for volatility context
**Data Points To Fetch:**
- Real-time 5-min OHLCV
- Pre-market price action & volume
- Sector ETF flows (XLK, XLF)
- Key support/resistance levels
- Most active options chain strikes
**Swing Trade Setup:** Enter on a pullback to a key moving average (e.g., 20 EMA) or breakout above consolidation with above-average volume; exit on a break below the 50 EMA or RSI exceeding 70.
**Short Term Setup:** Enter on a 1-5 minute breakout of the opening range or VWAP rejection; exit with a 1:1.5 risk-reward ratio or at the next significant technical level.

### gpt-oss:120b-cloud — GPT-OSS 120B (Ollama Cloud)  (elapsed 5.4s)
**Top picks:**
- **SPY** LONG (swing) — Broad market breadth and strong Q2 earnings guidance keep the S&P 500 on an upward trajectory.
- **TSLA** LONG (short-term) — Tesla's recent production ramp and positive demand outlook are driving momentum above its 20‑day EMA.
- **NVDA** SHORT (short-term) — Nvidia's valuation is stretched after a steep rally; MACD divergence and weakening volume suggest a pullback.
**Factors Used:**
- Relative Strength Index (RSI)
- Moving Average Convergence Divergence (MACD)
- Earnings surprise & guidance
- Volume-weighted average price (VWAP) trend
- Sector-relative performance
**Data Points To Fetch:**
- Intraday price and volume bars (1‑minute)
- Latest earnings release and guidance numbers
- Analyst consensus revisions and target price changes
- Sector ETF flows (e.g., XLK, XLF)
- Macro indicators: CPI YoY, Fed policy rate expectations
**Swing Trade Setup:** Enter on a pullback to the 20‑day EMA when RSI is between 40‑55 and MACD histogram turns positive; target a 6‑8% upside or exit at the next major resistance level.
**Short Term Setup:** Take a 1‑3 day trade when price breaks above the VWAP with RSI >60 and volume >1.5× average; set a tight stop 1% below entry and aim for a 2‑3% profit target.

### glm-4.6:cloud — GLM-4.6 (Ollama Cloud)  (elapsed 23.8s)
**Top picks:**
- **AAPL** LONG (swing) — Strong earnings momentum with expanding margins and new product cycle driving growth
- **TSLA** SHORT (short-term) — Overextended valuation with increasing competition and production challenges
- **MSFT** LONG (swing) — Cloud dominance and AI integration creating sustainable revenue streams
**Factors Used:**
- Momentum (12-1 month)
- Value (P/E ratio deviation)
- Quality (ROIC and earnings stability)
- Volatility (beta and ATR)
- Volume pattern analysis
**Data Points To Fetch:**
- Intraday price action and volume
- Options flow and unusual activity
- Institutional ownership changes
- Earnings surprise data
- Sector relative strength
**Swing Trade Setup:** Enter on pullbacks to key support levels with confirmation via volume spike, exit at resistance or when momentum diverges
**Short Term Setup:** Enter on breakout patterns with volume confirmation, exit when price closes below 5-period EMA or after 2-3 days

## FOREX

## COMMODITY

## ETF

## BOND
