# Stock Predictor Accuracy Analysis — ChatGPT Assessment

**Document ID:** stock · chatgpt  
**Source:** ChatGPT analysis of eltonaguiar stock repositories (code inspection via GitHub connector)  
**Integration Date:** January 27, 2026  

*This file contains the word "stock" and "chatgpt" for easy identification.*

---

## What ChatGPT Could Actually Inspect (vs. What It Couldn't)

Right now, ChatGPT's GitHub connector access via `file_search` is scoped to a limited set of repos, so it **could only inspect code from the repos currently connected** (not all 11 links provided). Concretely, ChatGPT was able to read code that includes:

* An ML backtesting + feature engineering pipeline (RandomForest / GradientBoosting / XGBoost / LinearRegression) 
* A composite "rating" system (technical + fundamental + sentiment + risk, with regime-based weights) 
* A statistical arbitrage / pairs-trading backtest (z-score mean reversion + Sharpe/return) 
* A Flask "stock analysis web app" that ties modules together and pulls data via yfinance  

If you want ChatGPT to include the other repos listed (e.g., the *pennystock skyrocket* repos, *mikestocks*, etc.), you'll need to add them to the GitHub connector's selected repos for this chat (otherwise ChatGPT can't truthfully claim it reviewed their algorithms).

---

## Top Algorithms You Currently Have (Based on Inspected Code)

### 1) **ML Ensemble for Next-Day Returns (Short-Term / Technical-Heavy)**

**Where it shows up:** `MLBacktesting` initializes and compares multiple models: RandomForestRegressor, GradientBoostingRegressor, XGBoostRegressor, LinearRegression 

**What it's predicting (time horizon):** The engineered target is explicitly **next-day return** (`target_1d = returns.shift(-1)`), so this is a **short-term (1D) predictor** 

**Features used (type):** Heavily **technical/microstructure**: returns/log returns, gaps, multiple moving averages (5/10/20/50/200), volatility windows, RSI, MACD, Bollinger Bands, volume ratios 

**How "accuracy" is measured (in code):** Regression metrics are imported (MSE, R², MAE) indicating model evaluation is intended around **forecast error**, not directional hit-rate 

**Best for:** Liquid large/mid caps or anything where indicators are stable + enough history (it enforces minimum datapoints and volume thresholds) 

**Less ideal for:** Ultra-illiquid penny stocks (gaps/halts can destroy indicator validity, and "next-day return" becomes noise).

**If you ask "what's the top algorithm here?":** In practice, among the listed models, **XGBoost / Gradient Boosting** are usually the strongest for tabular technical features, and your system is explicitly set up to use them. 

---

### 2) **Composite Rating Engine (Multi-Factor: Technical + Fundamental + Sentiment + Risk)**

**Where it shows up:** `ScoreCalculator` computes a **composite score** from multiple components and applies **market regime weights** (normal/high-vol/low-vol) 

**What it's doing (type):** This is a **stock rating / ranking** approach (not strictly a predictor). It:

* Requires technical metrics like RSI/MACD/Bollinger/MA50/MA200 
* Optionally incorporates an ML prediction as an additional score component 

**Time horizon:** Not explicitly defined in this class; it's more of an "overall attractiveness" score. Because it includes MA50/MA200 it naturally fits **swing / medium-term trend context**, but it can be used for short-term screening too. 

**Best for:** "Rate these stocks" workflows, watchlists, prioritization across sectors (especially if you calibrate thresholds to outcomes).

---

### 3) **Statistical Arbitrage / Pairs Mean Reversion (Market-Neutral-ish, Relative Value)**

**Where it shows up:** `StatisticalArbitrage` finds correlated pairs and trades based on z-score thresholds, then reports Sharpe + total return 

**Type:** Not long/short direction on a single ticker; it's **relative value / mean reversion**.

**Time horizon:** Depends on your `lookback_period` and sampling frequency; default lookback 60 suggests a **swing-ish mean reversion** cadence rather than intraday. 

**Best for:** Highly correlated large caps / sector pairs (less so for penny stocks).

---

## "Accuracy Analysis" Summary (What Exists vs. What's Missing)

### What Your Code Already Supports

* **ML regression evaluation** (MSE/R²/MAE) is clearly part of the ML stack 
* The ML pipeline includes realistic guardrails: validation thresholds (min datapoints, min volume, anomaly checks) 
* Pairs strategy directly outputs **Sharpe ratio** and **total return** 

### What ChatGPT Did *Not* Find (In the Inspected Snippets)

* A single consolidated "**predictor accuracy report**" comparing models across tickers (e.g., walk-forward results table, hit-rate, precision/recall for "up tomorrow")—at least not in the parts ChatGPT could access.
* Explicit "short-term vs long-term" labeling in the rating system—except the ML target which is explicitly next-day. 

---

## Quick "Which Tool for Which Stock Type?" Map

* **Short-term / technical prediction (1-day):** ML ensemble (XGB/GB/RF) + next-day target 
* **General rating / blended (technical + fundamental + sentiment + risk):** composite ScoreCalculator 
* **Market-neutral / relative value:** pairs stat-arb 
* **Valuation / fundamentals data availability:** Your web app pulls PE, market cap, target price, etc. via yfinance info (but that's data retrieval, not a "valuation model" by itself).

---

## If You Want ChatGPT to Rank *Across All 11 Repos*

ChatGPT can do a true "top algorithms across all tools" comparison, but it needs access to those repos in the GitHub connector scope (right now ChatGPT can't actually open most of the URLs you posted, so it would be guessing—won't do that). If you add them to the connector, ChatGPT will re-run the same analysis and produce:

* A repo-by-repo inventory of algorithms
* Which ones are predictive vs. scoring-only
* Which are short-term vs. long-term
* What evaluation metrics/backtests each repo actually implements

---

## Cross-Reference: stock · chatgpt

**ChatGPT's Analysis Scope:** Based on **code inspection** of connected GitHub repos (not all 11). Identified three core algorithms: (1) **ML Ensemble** (XGBoost/GradientBoosting/RandomForest) for next-day returns (short-term, technical-heavy); (2) **Composite Rating Engine** (ScoreCalculator) with regime-based weights (technical + fundamental + sentiment + risk); (3) **Statistical Arbitrage** (pairs mean reversion, market-neutral). Accuracy metrics: MSE/R²/MAE for ML; Sharpe/return for pairs. **Best for:** ML ensemble = liquid large/mid caps (1-day); Composite rating = watchlists/prioritization; Stat-arb = correlated large cap pairs.

**Cross-Reference (stock · googlegemini):** For **Google Gemini**'s assessment, see **`STOCK_GOOGLEGEMINI_ANALYSIS.md`** (file contains "stock" and "googlegemini"). Gemini uses two categories (High-Intensity Momentum/Penny Stock vs. Long-Term Growth Trend Identifiers), emphasizes timeframe-based weighted scoring for short-term, and RS percentile + Stage-Two + XBRL for long-term.

**Cross-Reference (stock · cometbrowserai):** For **Comet Browser AI**'s assessment, see **`STOCK_COMETBROWSERAI_ANALYSIS.md`** (file contains "stock" and "cometbrowserai"). Comet Browser AI uses three primary algorithm families (Stock QuickPicks, Stock Spike Replicator variants, Penny Stock Screeners), assigns confidence levels, and recommends a five-step strategy stack (Watchlist → Entry → Risk → Sentiment → Holding).

---

*Document contains "stock" and "chatgpt" for search and identification.*
