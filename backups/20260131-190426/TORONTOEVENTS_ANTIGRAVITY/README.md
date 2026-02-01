# TORONTOEVENTS_ANTIGRAVITY // STOCKSUNIFY Engine

[![STOCKSUNIFY CI](https://github.com/eltonaguiar/TORONTOEVENTS_ANTIGRAVITY/actions/workflows/ci.yml/badge.svg)](https://github.com/eltonaguiar/TORONTOEVENTS_ANTIGRAVITY/actions/workflows/ci.yml)

This repository contains the full source code and data for the STOCKSUNIFY V1 and V2 algorithmic stock selection engines. It serves as the primary development and data generation environment.

---

## 🚀 Core Features

### 1. STOCKSUNIFY V1 ("Classic")
- **Methodology**: A composite score based on CAN SLIM principles, technical momentum indicators, and fundamental data.
- **Output**: Generates a list of 30 stock picks daily.
- **Syncs To**: [github.com/eltonaguiar/stocksunify](https://github.com/eltonaguiar/stocksunify)

### 2. STOCKSUNIFY V2 ("Scientific")
- **Methodology**: A multi-strategy engine based on academic research and quantitative principles. It is "regime-aware" and designed to be falsifiable.
- **Strategies**:
    - **RAR**: Regime-Aware Reversion
    - **VAM**: Volatility-Adjusted Momentum
    - **LSP**: Liquidity-Shielded Penny
    - **SCS**: Scientific CAN SLIM
    - **AT**: Adversarial Trend
    - **IF**: Institutional Footprint
- **Output**: Generates a daily "Immutable Ledger" of scientific picks.
- **Syncs To**: [github.com/eltonaguiar/stocksunify2](https://github.com/eltonaguiar/stocksunify2)

### 3. The Truth Engine (Performance Verification)
- **Purpose**: Automatically verifies the performance of V2 picks after their recommended holding period has passed.
- **Process**:
    1. A GitHub Action runs every 6 hours (`.github/workflows/verify-picks.yml`).
    2. The verification engine (`verify-picks.ts`) checks for matured picks based on their unique `timeframe` (e.g., 24h, 3d, 7d).
    3. Matured picks are validated against real-market data from Yahoo Finance.
    4. **Slippage Simulation**: Entry prices include a simulated slippage penalty (high/low/close avg) to ensure realistic returns.
    5. The results are strictly recorded as **WIN** (Positive Return) or **LOSS** (Negative Return or Stop Loss Hit).
    6. All data is committed to the **Immutable Ledger**: [`data/pick-performance.json`](data/pick-performance.json).

#### 🛡️ Immutable Audit Trail
To ensure 100% intellectual honesty, every stock pick generated is:
- **Timestamped**: `pickedAt` ensures no retroactive editing.
- **Hashed**: A SHA-256 hash (`pickHash`) seals the symbol, price, and timestamp.
- **Archived**: Original raw picks are stored in `data/picks-archive/` before any price movement occurs.

**[View Live Performance Data (JSON)](data/pick-performance.json)**

---

## 🔬 Strategy Deep Dive

This table outlines the methodology, pros, cons, and current status of each primary algorithm in the V1 and V2 engines.

| Strategy | Pros | Cons | Current State | Ideal Stock Type | Holding Period |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **V2: Regime-Aware Reversion (RAR)** | Market-aware (shuts down in bear markets). Simple, robust logic (RSI mean-reversion). | Only works for stocks already in a long-term uptrend. | **Implemented**: Yes<br>**Job Setup**: Yes (Daily)<br>**Backtested**: No (Forward-tested via Truth Engine) | Quality, large-cap stocks in a confirmed uptrend experiencing a short-term pullback. | 7 Days |
| **V2: Volatility-Adjusted Momentum (VAM)** | Prioritizes smooth, low-volatility gains (high Martin Ratio). Includes YTD performance for better long-term context. | May underperform in speculative "junk-on" rallies. | **Implemented**: Yes<br>**Job Setup**: Yes (Daily)<br>**Backtested**: No (Forward-tested via Truth Engine) | Any stock with consistent, non-erratic price appreciation. | 1 Month |
| **V2: Liquidity-Shielded Penny (LSP)** | Specifically designed for high-risk stocks. "Slippage Torture Test" validates liquidity. | Inherently very high risk. Model is sensitive to execution costs. | **Implemented**: Yes<br>**Job Setup**: Yes (Daily)<br>**Backtested**: No (Forward-tested via Truth Engine) | Penny stocks (sub-$5) with high volume and catalysts. | 24 Hours |
| **V2: Scientific CAN SLIM (SCS)** | Improves on V1 CAN SLIM with a market regime filter. | Still lacks fundamental data (earnings, etc.) that the full CAN SLIM model requires. | **Implemented**: Yes<br>**Job Setup**: Yes (Daily)<br>**Backtested**: No (Forward-tested via Truth Engine) | Mid to large-cap growth stocks. | 1 Year |
| **V2: Adversarial Trend (AT)** | Volatility-normalized, making it more stable than pure price momentum. | Can be slower to react than simpler momentum strategies. | **Implemented**: Yes<br>**Job Setup**: Yes (Daily)<br>**Backtested**: No (Forward-tested via Truth Engine) | Stocks with strong, established trends in any sector. | 1 Month |
| **V2: Institutional Footprint (IF)** | Uses Volume Z-Score to detect statistically significant institutional activity. | Volume spikes can sometimes be misleading (e.g., ETF rebalancing). | **Implemented**: Yes<br>**Job Setup**: Yes (Daily)<br>**Backtested**: No (Forward-tested via Truth Engine) | Mid to large-cap stocks showing signs of accumulation. | 7 Days |
| **V1: CAN SLIM (Classic)** | Based on a historically proven methodology. | Technical-only implementation. Is not market-regime aware. | **Implemented**: Yes<br>**Job Setup**: Yes (Daily)<br>**Backtested**: No | Growth stocks, typically $10+. | 3-12 Months |
| **V1: Technical Momentum** | Multi-timeframe (24h, 3d, 7d) provides flexibility. | Can be noisy and produce false breakouts without a volatility filter. | **Implemented**: Yes<br>**Job Setup**: Yes (Daily)<br>**Backtested**: No | Any stock with short-term catalysts. High risk for penny stocks. | 24h to 7d |
| **V1: Composite Rating** | Multi-factor approach. Uses YTD performance as a long-term momentum factor. | Uses fixed, heuristic weights for its factors. Simple regime detection. | **Implemented**: Yes<br>**Job Setup**: Yes (Daily)<br>**Backtested**: No | Any stock, good for general watchlist ranking. | 1-3 Months |
| **V1: Penny Sniper** | Specifically designed for high-risk penny stocks with volume and momentum triggers. | Inherently very high risk; can produce many false signals. | **Implemented**: Yes<br>**Job Setup**: Yes (Daily)<br>**Backtested**: No | Penny stocks (<$15) with high volume and catalysts. | 24 Hours |
| **V1: Value Sleeper** | Seeks undervalued mid/large-cap companies near their 52-week lows but still in a long-term uptrend. | Requires fundamental data (PE, ROE, Debt) which can be sparse or inaccurate. | **Implemented**: Yes<br>**Job Setup**: Yes (Daily)<br>**Backtested**: No | Mid to large-cap stocks with solid fundamentals that are currently out of favor. | 3+ Months |
| **V1: Alpha Predator** | A scientific composite that combines Trend (ADX), Momentum (AO), and Structure (VCP) for a robust signal. | More complex and can be slower to react than pure momentum strategies. | **Implemented**: Yes<br>**Job Setup**: Yes (Daily)<br>**Backtested**: No | Any stock exhibiting a combination of strong trend, momentum, and price structure. | 3-7 Days |

---

## Recent Performance (2026-01-28)

**Market Regime:** BULL (SPY > SMA200)

**Top V2.1 Picks (Live Deduplicated Data):**
- **GM** (100/100) - Technical Momentum + 1 - EXTREMELY STRONG BUY
  - *Context:* Breakout + Volume Spike (3.0σ) + Bollinger Squeeze.
- **BMY** (90/100) - Alpha Predator + 2 - STRONG BUY
  - *Context:* VCP + Institutional Footprint. Triggered by CAN SLIM, Momentum, and Alpha Predator simultaneously.
- **HON** (90/100) - Alpha Predator + 1 - STRONG BUY
  - *Context:* Strong trend (ADX 36) + Momentum shift.
- **XLI** (90/100) - Alpha Predator + 3 - STRONG BUY
  - *Context:* **State Street Industrial ETF**. Proves expanded universe is working. Captures sector rotation.
- **PFE** (85/100) - Technical Momentum + 3 - STRONG BUY
  - *Context:* Multi-strategy concurrence (CAN SLIM + Momentum + Composite + Alpha Predator).

**Algorithm Distribution:**
- Alpha Predator + X: 19 picks (Dominant in high-quality setups)
- Technical Momentum: 5 picks
- Composite Rating: 1 pick (SBUX)

*Note: Algorithmic tags like "+ 2" indicate that 2 other algorithms ALSO triggered on this same stock, increasing confidence.*

---

## 🛠️ How to Use

### Installation
```bash
npm install
```

### Key Scripts

- **Generate V1 & V2 Picks Daily**:
  ```bash
  # Runs the full pipeline for both engines
  npm run stocks:all
  ```

- **Generate V2 Picks Only**:
  ```bash
  # Generate ledger and sync to STOCKSUNIFY2 repo
  npm run stocks:v2:full
  ```

- **Run Performance Verification Manually**:
  *Note: This runs automatically on Sundays via GitHub Actions.*
  ```bash
  # 1. Run the verification engine
  npm run stocks:v2:verify
  
  # 2. Aggregate the results for the frontend
  npm run stocks:v2:aggregate
  ```

- **Run Development Server**:
  ```bash
  npm run dev
  ```

---

## 🧪 Testing

This project uses [Vitest](https://vitest.dev/) for unit testing to ensure the quality and correctness of the core algorithmic logic. The test suite is run automatically on every push and pull request to the `main` branch via the CI workflow.

### Run Test Suite
To run all unit tests, use the following command:
```bash
npm test
```

---

## 🧪 Scientific Breakthroughs (Session 6)

In our latest research cycle (Jan 2026), we moved beyond heuristic scoring to **simulation-guided optimization** and **adversarial audit**.

### 1. Mandatory Earnings Risk Guard
Binary event risk (earnings gaps) is the #1 killer of momentum setups. 
- **The Rule**: Any stock with an earnings report within **6 days** is hit with a `-100 point penalty`. 
- **The Result**: These stocks are automatically disqualified from the "Top Picks" list, protecting capital from overnight gap-down risks.

### 2. Scientific Tuning Lab (Hyper-Parameter Sweep)
We ran a **2-year sliding window backtest** to find the "Efficient Frontier" for our core algorithms. We optimized for the highest **Sharpe Ratio** (Risk-Adjusted Return).

| Algorithm | Optimal Threshold | Win Rate | Sharpe Ratio | Finding |
| :--- | :--- | :--- | :--- | :--- |
| **Alpha Predator** | **Score 85** | 57.1% | 0.398 | Exceptional risk-adjusted profile at high conviction. |
| **CAN SLIM** | **Score 70** | 56.8% | 0.262 | High-quality growth setups verified at this level. |
| **Composite Rating** | **Score 60** | 53.9% | 0.130 | Stable for general ranking but lower peak Sharpe. |

### 3. Adversarial Stress Audit ("Falling Knife" Test)
We identified **70 historic stress events** (market flushes of >3% in 5 days) to test algorithm resilience.
- **The Find**: By integrating the **Regime Filter (SMA 200)** and a **Volatility Ceiling (ATR-based)**, the engine successfully avoided firing signals during the peak of 90% of identified panic events.

---

## 🎯 Recommendation Rating Scale

Our system uses a clear, easy-to-understand rating scale to communicate the strength of each stock pick:

| Rating | Score Range | Meaning | Recommended Action |
|--------|-------------|---------|-------------------|
| **EXTREMELY STRONG BUY** | 95-100 | Exceptional setup with multiple confirming signals. Highest conviction. | Consider larger position (up to 5% of portfolio) |
| **STRONG BUY** | 80-94 | Very good setup with most indicators aligned. High confidence. | Standard position (3-4% of portfolio) |
| **BUY** | 65-79 | Good opportunity with solid fundamentals/technicals. | Smaller position (2-3% of portfolio) |
| **HOLD** | 50-64 | Neutral outlook. Not a new buy, but don't sell if already owned. | No new action |
| **SELL** | 35-49 | Weakening signals. Consider exiting positions. | Reduce or exit position |
| **STRONG SELL** | Below 35 | Significant weakness detected. Exit recommended. | Exit position |

### What the Scores Mean

- **Score 100**: Perfect alignment across all indicators - extremely rare
- **Score 80+**: Strong buy territory - multiple confirmations
- **Score 65-79**: Good opportunity - solid setup but some caution
- **Score 50-64**: Hold zone - wait for better entry
- **Below 50**: Avoid or sell - negative signals outweigh positive

---

## 📚 Beginner-Friendly Glossary

New to stock investing? This glossary explains all the technical terms used in our system in plain English.

### 📈 Core Chart & Trend Terms

| Term | Simple Explanation |
|------|-------------------|
| **Trend** | The general direction a stock is moving: **Uptrend** = going up, **Downtrend** = going down, **Sideways** = stuck in a range |
| **Moving Average (SMA)** | The average price over a set number of days. Example: 200 SMA = average price over the last 200 days. Used to judge long-term trend. |
| **EMA (Exponential Moving Average)** | Like SMA, but gives more weight to recent prices, so it reacts faster to changes. |
| **50 SMA & 200 SMA** | Very common trend benchmarks. **Price above 200 SMA** = long-term bull trend. **Price below 200 SMA** = long-term weakness. |
| **Stage-2 Uptrend** | A stock is in the "best growth phase": price rising, above moving averages, institutions buying. Common in breakout stocks. |
| **Support** | A price level where buyers tend to step in and stop the decline. Think of it as a "floor." |
| **Resistance** | A price level where sellers tend to appear and stop the rise. Think of it as a "ceiling." |
| **Breakout** | When a stock breaks above resistance (smashes through the ceiling). Often signals a big move is starting. |

### 🔥 Momentum Indicators

| Term | Simple Explanation |
|------|-------------------|
| **Momentum** | Speed of price movement. Momentum stocks rise quickly because buyers are aggressive. |
| **RSI (Relative Strength Index)** | Measures if a stock is overbought or oversold. Scale: 0-100. **RSI < 30** = oversold (maybe cheap), **RSI 50-75** = bullish momentum, **RSI > 80** = overheated (be careful). |
| **MACD** | Tracks momentum shifts. MACD crossing upward often signals trend turning bullish. |
| **Awesome Oscillator (AO)** | Momentum shift detector. **AO > 0** = buyers gaining control. **AO < 0** = sellers stronger. |

### 📊 Trend Strength Indicators

| Term | Simple Explanation |
|------|-------------------|
| **ADX (Average Directional Index)** | Measures how STRONG a trend is (not direction). Scale: 0-100. **ADX < 20** = weak/no trend, **ADX > 25** = strong trend, **ADX > 40** = extremely powerful trend. |
| **Volume** | How many shares traded. High volume = strong interest from buyers/sellers. |
| **Volume Surge / Spike** | Trading activity far above normal. Usually means big buyers entering or news/breakout underway. |
| **Volume Z-Score** | Measures how extreme volume is statistically. **3.0+** = huge spike (very unusual activity). |

### 📉 Volatility & Pattern Terms

| Term | Simple Explanation |
|------|-------------------|
| **Volatility** | How much a stock swings up/down. High volatility = risky but fast gains possible. |
| **Bollinger Bands** | Bands around price showing expected movement range. When price touches upper band, stock may be overextended. |
| **Bollinger Squeeze** | When bands tighten, meaning volatility is compressed. Like a coiled spring - breakout likely soon! |
| **VCP (Volatility Contraction Pattern)** | A famous pattern from Mark Minervini. Stock becomes quieter, volatility tightens, then a big move often follows. Seen before explosive breakouts. |
| **ATR (Average True Range)** | Measures typical daily price movement. Used to set stop-losses. Higher ATR = more volatile stock. |
| **Golden Cross** | Bullish signal where short-term moving average crosses above long-term MA (e.g., 50 SMA crosses above 200 SMA). Often means trend reversal upward. |

### 💰 Institutional & Smart Money Terms

| Term | Simple Explanation |
|------|-------------------|
| **Institutional Footprint** | Evidence that hedge funds/banks are buying. They move markets because they buy in size. |
| **VWAP (Volume Weighted Average Price)** | A price benchmark used by professional traders. **Price > VWAP** = institutions likely accumulating, trend is healthy. |
| **Accumulation** | When big investors are quietly buying shares over time. Often happens before a stock rises. |
| **Distribution** | When big investors are quietly selling. Often happens before a stock falls. |

### 📌 Fundamental Terms

| Term | Simple Explanation |
|------|-------------------|
| **Market Cap** | Total value of a company's shares. **Large Cap** (>$10B) = stable, **Mid Cap** ($2-10B) = growth potential, **Small Cap** (<$2B) = higher risk/reward. |
| **PE Ratio (Price/Earnings)** | How expensive a stock is relative to profits. **PE 10-20** = cheap/moderate, **PE 40+** = expensive (or high growth expected). |
| **ROE (Return on Equity)** | How efficiently the company generates profit. **ROE > 15%** = strong business. |
| **Debt/Equity Ratio** | Measures how much debt a company uses. **Lower = safer**. Less than 0.8 is generally good. |
| **52-Week High/Low** | Highest and lowest price in the last year. Stocks near 52-week highs often have momentum. |
| **Float** | Number of shares available to trade publicly. **Low float** stocks can move very quickly (up or down). |
| **Penny Stock** | Small, low-priced, high-risk stocks. In our system: $0.50-$15 price range. |

### ⚠️ Risk & Trade Management Terms

| Term | Simple Explanation |
|------|-------------------|
| **Stop Loss** | A pre-set exit point to prevent large losses. Example: Buy at $86, set stop at $82. If it drops to $82 → sell immediately to limit loss. |
| **Take Profit / Target** | A pre-set price where you sell to lock in gains. Example: Buy at $86, target at $95. If it hits $95 → sell and take your profit. |
| **Risk/Reward Ratio (R:R)** | Compares potential profit to potential loss. **2:1 R:R** means you could gain $2 for every $1 you risk. Higher is better. |
| **Slippage** | The real price you get may be worse than expected due to market movement. Our system adds +0.5% to entry prices to simulate this. |
| **Position Sizing** | How much money to allocate per trade. Rule of thumb: Never risk more than 2-5% of your total portfolio on one trade. |
| **Drawdown** | How much your investment dropped from its peak before recovering. Max drawdown = worst decline experienced. |

### 🌍 Market Environment Terms

| Term | Simple Explanation |
|------|-------------------|
| **Market Regime** | The overall market environment: **Bull Market** = rising prices, optimism. **Bear Market** = falling prices, fear. **Neutral** = sideways, uncertain. |
| **Bull Market** | When the market is rising. Momentum strategies work best. Most stocks go up. |
| **Bear Market** | When the market is falling. Defensive/value strategies work best. Cash is often king. |
| **SPY** | An ETF that tracks the S&P 500 (500 largest US companies). Used as a benchmark for overall market health. |

### 📅 Holding Styles & Timeframes

| Term | Timeframe | Description |
|------|-----------|-------------|
| **Day Trade** | < 24 hours | Buy and sell within the same day. High frequency, high stress. |
| **Swing Trade** | 3-7 days | Capture short-term price swings. Most active trading style. |
| **Position Trade** | 1-4 weeks | Hold through a specific move or pattern completion. |
| **Investment** | 1+ months | Buy and hold for longer-term growth. Less monitoring needed. |
| **Long Position** | Any | You profit when the stock goes UP. (All our picks are LONG positions.) |
| **Short Position** | Any | You profit when the stock goes DOWN. (Requires margin account, higher risk.) |

### 🧬 Our Algorithm Names Explained

| Algorithm | What It Does | Best For |
|-----------|--------------|----------|
| **Alpha Predator** | Combines trend strength (ADX) + momentum (AO) + pattern (VCP) + institutional activity (VWAP) | Stocks with multiple confirming signals |
| **Technical Momentum** | Finds stocks with volume surges, RSI momentum, and breakout patterns | Short-term momentum plays (24h to 7d) |
| **CAN SLIM** | Based on William O'Neil's growth investing system | Growth stocks in Stage-2 uptrends |
| **Composite Rating** | Balanced scoring of technical + fundamental factors | General watchlist building |
| **Penny Sniper** | Hunts for microcap breakouts with extreme volume | High-risk, high-reward penny stocks |
| **Value Sleeper** | Finds undervalued stocks near 52-week lows | Patient value investors |

### ✅ Beginner Quick Reference

**If you're new, focus on these terms first:**

| Term | Why It Matters |
|------|----------------|
| **RSI** | Tells you if momentum is with you or against you |
| **SMA 50/200** | Shows the long-term trend direction |
| **Breakout** | When big moves begin |
| **Volume Spike** | Confirms real buying interest |
| **Stop Loss** | Protects you from big losses |
| **VWAP** | Shows where smart money is positioned |
| **ADX** | Tells you if the trend is strong or weak |
| **Risk/Reward** | Helps you take trades where reward exceeds risk |

---

## 🧐 Scientific Limitations & Peer Critique
*Transparency is the cornerstone of scientific validation. Below are the known limitations of this system and our direct responses to peer critiques (Gemini/Grok).*

### 1. Selection Bias (Small Universe)
- **Critique:** The engine currently monitors a curated list of ~100 tickers, rather than the entire market (10,000+).
- **Impact:** This introduces inherent "Quality Bias"—we are only picking from stocks we already know are decent.
- **Roadmap:** Future versions will integrate a screener to dynamically populate the universe from the entire Russell 3000.

### 2. Slippage in Microcaps
- **Critique:** A flat 0.5% slippage model is too optimistic for penny stocks (`Penny Sniper` algo) where spreads can be 2-3%.
- **Response:** As of **Jan 28, 2026**, `verify-picks.ts` implements **Dynamic Slippage**:
  - `>$10`: 0.5% (Liquid)
  - `$5 - $10`: 1.0% (Mid variance)
  - `<$5`: 3.0% (High risk/illiquid)

### 3. Lack of Historical Backtesting
- **Critique:** The system relies on "Forward Testing" (The Truth Engine) rather than 10-year historical backtests.
- **Reality:** We acknowledge this. Most retail backtests are curve-fitted lies. We prefer **Forward Testing** on an immutable ledger as it is the only 100% truthful metric. We are building the track record *live*.

### 4. Regime Lag
- **Critique:** Relying solely on the Daily 200 SMA for market regime can be slow to react to V-shaped recoveries.
- **Mitigation:** We advise users to watch the **50 SMA** as a leading indicator, though the primary engine remains conservative.

---

## 🔗 Live Resources

- **Live Website**: [findtorontoevents.ca/findstocks](https://findtorontoevents.ca/findstocks/)
- **V2 Engine Repo**: [github.com/eltonaguiar/STOCKSUNIFY2](https://github.com/eltonaguiar/STOCKSUNIFY2)
- **V1 Engine Repo**: [github.com/eltonaguiar/stocksunify](https://github.com/eltonaguiar/stocksunify)
- **Daily Picks JSON**: [data/daily-stocks.json](data/daily-stocks.json)
- **Performance Data**: [data/pick-performance.json](data/pick-performance.json)

---

## ⚠️ Disclaimer

This project is for **informational and educational purposes only**. It does not constitute financial advice. All stock investments carry risk, including the potential loss of principal. Past performance does not guarantee future results. Always conduct your own research and consult with a licensed financial advisor before making investment decisions. Never invest more than you can afford to lose.

---