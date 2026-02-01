# Stock Predictor Accuracy Analysis & Algorithm Comparison

**Document ID:** stock · cometbrowserai  
**Source:** Comet Browser AI analysis of eltonaguiar stock repositories  
**Integration Date:** January 27, 2026  

*This file contains the word "stock" and "cometbrowserai" for easy identification.*

---

Based on comprehensive analysis of your 11 stock repositories, here is the detailed breakdown of your algorithms and their specializations.

---

## **PRIMARY ALGORITHM FAMILIES**

### **1. STOCK QUICKPICKS (SHORT-TERM FOCUS)**
**Repository:** `stock_quickpicks_april152025` [github](https://github.com)
- **Type:** Short-term investment analyzer
- **Algorithm Focus:** Technical Analysis + AI Integration
- **Key Features:**
  - Technical indicators (RSI, Moving Averages, multiple indicators)
  - Sentiment analysis (VADER + FinBERT)
  - AI Search integration (You.com, Bing Copilot)
  - Website prediction tracking with trust score system
  - Target prices and stop losses
  - Holding periods based on technical analysis
  - Portfolio optimization
- **Target Timeframe:** Short-term (days to weeks)
- **Specialization:** Quick-pick analysis with AI recommendations and accuracy tracking

***

### **2. STOCK SPIKE REPLICATOR (MULTI-PURPOSE)**
**Repositories:** `eltonsstocks-apr24_2025`, `eltonstocksapr25bare`, `eltonstocksapr23`, `stocks_apr252025_440pmEST`

**Three Variants Identified:**

**Variant A: ML + Algorithmic Trading** (`eltonsstocks-apr24_2025`) [github](https://github.com)
- **Algorithm Focus:** Machine Learning + Advanced Algorithmic Techniques
- **Methods:**
  - Markov Models and Hidden Markov Models for state prediction
  - Statistical Arbitrage for market inefficiencies
  - NLP sentiment analysis
  - Backtesting with transaction costs and slippage
  - Risk management with position sizing
  - Market regime detection
- **Target Timeframe:** Medium to Long-term
- **Specialization:** Algorithmic trading with regime detection

**Variants B & C: Technical + Risk Management** (`eltonstocksapr25bare`, `eltonstocksapr23`, `stocks_apr252025_440pmEST`)
- **Algorithm Focus:** Technical Analysis + Modern Portfolio Theory
- **Methods:**
  - Multiple financial data APIs (Finnhub, Alpha Vantage, Twelve Data, Yahoo)
  - Technical indicators (RSI, Moving Averages, ATR, Bollinger Bands)
  - Advanced risk management:
    - Position sizing via Kelly Criterion (half-Kelly conservative)
    - Dynamic stop-loss/take-profit based on ATR
    - Value at Risk (VaR) and Expected Shortfall
    - Sharpe, Sortino, Calmar ratios
  - Portfolio optimization using Modern Portfolio Theory
  - Ensemble methods
  - Sentiment analysis
- **Target Timeframe:** Short to Medium-term
- **Specialization:** Risk-adjusted returns with hedge fund-level position sizing

***

### **3. PENNY STOCK SCREENERS (SHORT-TERM EXPLOSIVE GROWTH)**

**Short-Term Technical Screener:** `SCREENER_PENNYSTOCK_SKYROCKET_24HOURS_CURSOR` [github](https://github.com)
- **Algorithm Focus:** Technical Indicators for 24-Hour to 1-Month Moves
- **Methods:**
  - RSI (14-day)
  - ATR (Average True Range)
  - Bollinger Band Squeeze & Width
  - Volume Surge detection
  - Short Interest analysis
  - Float Short %
  - Institutional Ownership
  - Price breakouts
  - 6-Month momentum
  - Sharpe Ratio
- **Timeframe Variants:** 24 hours, 3 days, 7 days, 2 weeks, 1 month
- **Target Stocks:** Penny stocks under $4 (customizable)
- **Target Timeframe:** **VERY SHORT-TERM (24 hours to 1 month)**
- **Specialization:** Rapid momentum detection for explosive penny stocks
- **Key Advantage:** Timeframe-adaptive weighting (immediate signals for 24hr, reversal signals for weekly)

**Growth-Focused Screener:** `SCREENER_PENNYSTOCK_SKYROCKET_24HOURS_AUGMENTCODE`, `mikestocks`, `michael2stocks`, `mikestocks_april272025`
- **Algorithm Focus:** Long-Term Growth Fundamentals + Technical
- **Methods (5-Iteration Screen):**
  1. Relative Strength (RS Rating 90+) - weighted 12-month momentum
  2. Liquidity filters (Market cap ≥$1B, Price ≥$10, Volume ≥100K shares)
  3. Stage-2 Uptrend detection (Price relationships with SMAs)
  4. Revenue Growth (25%+ YoY from SEC XBRL filings)
  5. Institutional Accumulation (net inflows/outflows)
- **Target Timeframe:** **LONG-TERM (6 months to years)**
- **Specialization:** Fundamentally strong growth companies
- **Key Advantage:** Uses SEC EDGAR XBRL data for real revenue verification
- **Data Sources:** Selenium web scraping, async requests, institutional flow tracking

***

## **TOP ALGORITHMS BY CATEGORY**

### **BEST FOR SHORT-TERM GAINS (24 hours - 4 weeks):**
1. **🏆 SCREENER_PENNYSTOCK_SKYROCKET_24HOURS** - Technical momentum detection, adaptable timeframes, 0-4 week focus
2. **Stock QuickPicks** - AI-enhanced technical analysis with sentiment, news-based catalysts

### **BEST FOR MEDIUM-TERM SWING TRADING (4 weeks - 6 months):**
1. **🏆 Stock Spike Replicator (Risk Management Version)** - Position sizing with Kelly Criterion, risk-adjusted returns, sentiment + technical
2. **Stock QuickPicks** - Holding period suggestions, ensemble methods

### **BEST FOR LONG-TERM VALUE/GROWTH:**
1. **🏆 Growth Stock Screener** (mikestocks variants) - Revenue growth verification via SEC filings, RS rating, institutional accumulation, 6-month+ horizon
2. **Stock Spike Replicator ML** - Markov models for regime detection over longer periods

### **BEST FOR TECHNICAL ANALYSIS:**
1. **Stock Spike Replicator (All variants)** - 100+ technical indicators, advanced risk metrics
2. **Penny Stock Skyrocket Screener** - Volatility + momentum indicators optimized by timeframe

### **BEST FOR VALUATION/FUNDAMENTALS:**
1. **🏆 Growth Stock Screener** - Revenue growth (25% minimum), market cap filters, SEC XBRL data
2. **Stock QuickPicks** - AI sentiment + website prediction accuracy tracking

***

## **ALGORITHM ACCURACY & CONFIDENCE LEVELS**

| Algorithm | Confidence Level | Accuracy Indicators | Limitations |
|-----------|------------------|---------------------|-------------|
| **Penny Stock Screener (Technical)** | Medium | Historical backtest plots included | Penny stocks high volatility, low liquidity |
| **Stock QuickPicks** | Medium-High | Trust score system tracks prediction source reliability | Relies on web scraping, sentiment can be noisy |
| **Stock Spike Replicator (Risk Mgmt)** | High | Risk metrics validated (Sharpe, Sortino, VaR) | Backtesting limitations, assumes normal distribution |
| **Growth Screener** | High | Revenue data from SEC filings (audited) | Lagged institutional data, doesn't predict future catalysts |
| **Stock Spike Replicator (ML)** | Medium | HMM for regime detection, machine learning proven | Black box decisions, requires significant historical data |

***

## **RECOMMENDED STRATEGY STACK**

For **optimal diversified accuracy**, use them in combination:

1. **Watchlist Generation:** Growth Screener (find fundamentally sound companies)
2. **Entry Timing:** Penny Stock Screener (24-hour to 1-month timeframe based on your horizon)
3. **Risk Management:** Stock Spike Replicator Risk Mgmt version (position sizing, stop-loss)
4. **Sentiment Validation:** Stock QuickPicks (AI sentiment + news catalysts)
5. **Holding Period:** Stock QuickPicks suggestions + Spike Replicator technical analysis

***

## **KEY INSIGHTS**

- **No single algorithm is "best"** - they target different timeframes
- **Stock Spike Replicator Risk Management version** appears most mature (hedge fund-level risk metrics)
- **Growth Screener** has highest fundamental accuracy (SEC XBRL data)
- **Penny Stock Screener** is specialized but high-risk/high-reward for short-term traders
- **Stock QuickPicks** best for capturing catalysts via AI and news sentiment
- Your repositories show strong **technical + fundamental hybrid approach** across different timeframes

The analysis shows you have professional-grade stock tools for multiple strategies - short-term momentum, medium-term swing trading, and long-term growth investing.

---

## **Cross-Reference: stock · cometbrowserai**

- **Comet Browser AI** classifies repos into: **Stock QuickPicks** (short-term, AI + sentiment), **Stock Spike Replicator** (ML + Risk Mgmt variants), **Penny Stock Screeners** (technical vs. growth-focused).
- **Confidence levels:** Growth Screener & Risk Mgmt Replicator = High; QuickPicks = Medium-High; Penny Technical = Medium; ML Replicator = Medium.
- **Strategy stack:** Watchlist (Growth) → Entry (Penny Screener) → Risk (Spike Replicator) → Sentiment (QuickPicks) → Holding (QuickPicks + Replicator).

**Cross-Reference (stock · googlegemini):** For **Google Gemini**'s assessment of the same stock repositories, see **`STOCK_GOOGLEGEMINI_ANALYSIS.md`** (file contains "stock" and "googlegemini"). Gemini uses two categories (High-Intensity Momentum/Penny Stock vs. Long-Term Growth Trend Identifiers), emphasizes timeframe-based weighted scoring for short-term, and RS percentile + Stage-Two + XBRL for long-term.

**Cross-Reference (stock · chatgpt):** For **ChatGPT**'s code inspection analysis of connected GitHub repos, see **`STOCK_CHATGPT_ANALYSIS.md`** (file contains "stock" and "chatgpt"). ChatGPT identified three core algorithms from code inspection: (1) **ML Ensemble** (XGBoost/GradientBoosting/RandomForest) for next-day returns (short-term, MSE/R²/MAE); (2) **Composite Rating Engine** (ScoreCalculator, regime-based); (3) **Statistical Arbitrage** (pairs mean reversion, Sharpe/return). Best for: ML = liquid large/mid caps (1-day); Composite = watchlists; Stat-arb = correlated pairs.

*Document contains "stock" and "cometbrowserai" for search and identification.*
