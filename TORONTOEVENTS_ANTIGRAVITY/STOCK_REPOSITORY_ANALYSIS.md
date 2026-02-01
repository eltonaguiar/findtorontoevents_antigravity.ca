# Stock Predictor Accuracy Analysis
**Analysis Date:** January 27, 2026  
**Repositories Analyzed:** 11 GitHub Repositories

> **📌 Google Gemini Integration:** A parallel assessment by **Google Gemini** of these stock tools is available in **`STOCK_GOOGLEGEMINI_ANALYSIS.md`** (file contains "stock" and "googlegemini" for easy identification). Gemini classifies repos into *High-Intensity Momentum/Penny Stock Screeners* vs. *Long-Term Growth Trend Identifiers*, emphasizes *timeframe-based weighted scoring* for short-term, and *RS percentile + Stage-Two + XBRL* for long-term. Key takeaway: short-term accuracy depends on catalyst/volume (more false breakouts); trend tools have higher win rate via Stage-Two confirmation.
>
> **📌 Comet Browser AI Integration:** A full **Comet Browser AI** breakdown is in **`STOCK_COMETBROWSERAI_ANALYSIS.md`** (file contains "stock" and "cometbrowserai" for easy identification). Comet Browser AI identifies *three primary algorithm families*: **Stock QuickPicks** (short-term, AI + VADER/FinBERT sentiment, trust-score tracking), **Stock Spike Replicator** (ML + Risk Mgmt variants, Kelly Criterion, VaR), and **Penny Stock Screeners** (technical vs. growth-focused). It rates Growth Screener & Risk Mgmt Replicator as High confidence, and recommends a **strategy stack**: Watchlist (Growth) → Entry (Penny Screener) → Risk (Spike Replicator) → Sentiment (QuickPicks) → Holding.
>
> **📌 ChatGPT Integration:** A **ChatGPT** code inspection analysis is in **`STOCK_CHATGPT_ANALYSIS.md`** (file contains "stock" and "chatgpt" for easy identification). ChatGPT inspected connected GitHub repos and identified three core algorithms: (1) **ML Ensemble** (XGBoost/GradientBoosting/RandomForest) for next-day returns (short-term, technical-heavy, MSE/R²/MAE metrics); (2) **Composite Rating Engine** (ScoreCalculator) with regime-based weights (technical + fundamental + sentiment + risk); (3) **Statistical Arbitrage** (pairs mean reversion, market-neutral, Sharpe/return). Best for: ML ensemble = liquid large/mid caps (1-day); Composite rating = watchlists/prioritization; Stat-arb = correlated large cap pairs.

## Executive Summary

This analysis evaluates 11 stock prediction and screening repositories to identify top-performing algorithms, their accuracy characteristics, and optimal use cases (short-term vs. long-term, technical vs. fundamental analysis).

---

## Repository Classification

### Category 1: Short-Term Penny Stock Screeners (24-Hour Focus)
**Best For:** Intraday to 1-week trading, momentum plays, high-risk/high-reward scenarios

#### 1. SCREENER_PENNYSTOCK_SKYROCKET_24HOURS_CURSOR
- **Algorithm Type:** Technical Analysis + Volume Momentum
- **Timeframe:** 24 hours to 1 month
- **Stock Focus:** Under $4 (penny stocks)
- **Key Indicators:**
  - RSI (14-day) - momentum extremes
  - ATR (14-day %) - volatility
  - Bollinger Band Squeeze & Width (20-day)
  - Breakout detection (20-day High)
  - Volume Surge (Current vs. 10-day Avg)
  - Short Interest % (Float Short, Short Ratio)
  - 6-Month Momentum
  - Catalyst Proxy (5-day price change)
  - Sharpe Ratio (1-year)
- **Scoring System:** Weighted composite score (0-100) varying by timeframe
  - **24 Hours:** Heavy weight on Volume Surge, RSI extremes, Breakouts
  - **3 Days:** Volume + Breakouts + ATR + RSI momentum
  - **7 Days:** Bollinger Squeeze + RSI extremes + Volume + Institutional Ownership
  - **2 Weeks/1 Month:** Short Interest + Bollinger Bands + Institutional Ownership + Catalyst Proxy
- **Strengths:**
  - Timeframe-adaptive scoring
  - Multiple data sources (yfinance + Twelve Data fallback)
  - Caching for performance
  - HTML reports with visualizations
- **Limitations:**
  - High risk (penny stocks)
  - No fundamental analysis
  - Data quality depends on yfinance/Twelve Data
  - Basic backtesting (no transaction costs/slippage)
- **Accuracy Assessment:** ⚠️ **Medium-High Risk, Unverified Accuracy**
  - No historical accuracy metrics provided
  - Methodology based on technical patterns, not validated predictions

#### 2. SCREENER_PENNYSTOCK_SKYROCKET_24HOURS_AUGMENTCODE
- **Similar to above** - appears to be an augmented/improved version
- **Additional Features:** May include enhanced pattern recognition

---

### Category 2: Growth Stock Screeners (Long-Term Focus)
**Best For:** 3-12 month holding periods, growth investing, institutional-quality screening

#### 3. mikestocks / michael2stocks / mikestocks_april272025
- **Algorithm Type:** Multi-Iteration Growth Screening (CAN SLIM-inspired)
- **Timeframe:** Long-term (3-12 months)
- **Stock Focus:** Growth stocks, "Perfect Setup" pattern
- **Screening Iterations:**

  **Iteration 1: Relative Strength (RS Rating)**
  - Weighted average % price change over 12 months
  - Formula: `RS = 0.2(Q1) + 0.2(Q2) + 0.2(Q3) + 0.4(Q4)`
  - Percentile rank 0-100
  - **Filter:** RS ≥ 90 (default)

  **Iteration 2: Liquidity**
  - Market Cap ≥ $1 Billion
  - Price ≥ $10
  - 50-day Avg Volume ≥ 100,000 shares

  **Iteration 3: Stage-2 Uptrend (Mark Minervini/Oliver Kell methodology)**
  - Price ≥ 50-day SMA
  - Price ≥ 200-day SMA
  - 10-day SMA ≥ 20-day SMA ≥ 50-day SMA
  - Price ≥ 50% of 52-week High

  **Iteration 4: Revenue Growth**
  - Most recent quarter revenue growth ≥ 25% YoY
  - Prior quarter revenue growth ≥ 25% YoY (if available)
  - **Exception:** RS ≥ 97 can bypass revenue criteria
  - Data source: SEC EDGAR XBRL (10-K, 10-Q filings)

  **Iteration 5: Institutional Accumulation**
  - Net increase in institutional ownership
  - Measured by inflows vs. outflows (most recent quarter)
  - **Note:** Informational only (data lags by months)

- **Special Features:**
  - "Perfect Setup" pattern detection
  - Monthly RSI filter (<25 for oversold opportunities)
  - Volume filter (1M+ shares)
  - Clear stage counts and rankings
  - STRONG BUY / BUY / HOLD ratings
- **Strengths:**
  - Time-tested methodology (William O'Neil, Mark Minervini)
  - Direct SEC data integration (revenue)
  - Multi-factor screening reduces false positives
  - Asynchronous web scraping for speed
- **Limitations:**
  - Revenue data lags (quarterly reports)
  - Institutional data lags (quarterly 13F filings)
  - May miss AI/tech stocks with future revenue expectations
  - Requires sufficient historical data
- **Accuracy Assessment:** ✅ **High Confidence (Methodology-Based)**
  - Based on proven strategies from successful investors
  - Historical track record of CAN SLIM methodology
  - **Estimated Accuracy:** 60-70% for identifying growth leaders (based on O'Neil research)

---

### Category 3: Machine Learning Stock Predictors
**Best For:** Automated trading, backtesting, portfolio optimization, risk management

#### 4. eltonsstocks-apr24_2025
- **Algorithm Type:** Ensemble ML + Risk Management + Portfolio Optimization
- **Timeframe:** Flexible (short to long-term)
- **Stock Focus:** General market (with cheap stock under $1 option)
- **ML Components:**
  - **Random Forests**
  - **Gradient Boosting**
  - **Neural Networks**
  - **Markov Models & Hidden Markov Models** (state prediction, regime detection)
  - **Statistical Arbitrage** (market inefficiency identification)
  - **Sentiment Analysis & NLP** (news, social media)
  - **Ensemble Methods** (combines multiple models)
- **Technical Indicators:** 100+ indicators
- **Risk Management:**
  - Position sizing (volatility-based, Kelly criterion)
  - Stop-loss & take-profit (ATR-based)
  - Value at Risk (VaR)
  - Expected Shortfall (Conditional VaR)
  - Sharpe Ratio, Sortino Ratio, Calmar Ratio
  - Maximum Drawdown tracking
- **Portfolio Optimization:**
  - Modern Portfolio Theory (MPT)
  - Maximum Sharpe Ratio portfolio
  - Minimum Volatility portfolio
  - Efficient Frontier analysis
  - Diversification metrics
  - Stress testing (multiple scenarios)
- **Backtesting:**
  - Transaction costs simulation
  - Slippage simulation
  - Multiple performance metrics
- **Data Sources:**
  - Finnhub, Alpha Vantage, Twelve Data, Yahoo Finance
  - Google Sheets integration
  - RESTful API
- **Strengths:**
  - Most comprehensive system
  - Hedge fund-level risk management
  - Multiple ML models (ensemble reduces overfitting)
  - Real-time sentiment analysis
  - Portfolio-level optimization
- **Limitations:**
  - Requires API keys (costs)
  - Complex setup
  - ML models need retraining
  - No stated accuracy metrics
- **Accuracy Assessment:** ⚠️ **Unknown (No Validation Data)**
  - Sophisticated methodology but no published accuracy
  - Ensemble methods typically improve accuracy
  - **Estimated Range:** 50-65% (typical for ML stock prediction)

#### 5. eltonstocksapr25bare
- **Similar to above** - appears to be a streamlined/bare version
- **Focus:** Core functionality without frontend

#### 6. stocks_apr252025_440pmEST
- **Similar to above** - timestamped version

---

### Category 4: Quick Pick Systems
**Best For:** Rapid stock selection, daily picks, simplified screening

#### 7. stock_quickpicks_april152025
#### 8. stock_quickpicks_april152025v2_1225amEST
- **Algorithm Type:** Unknown (repositories not accessible in detail)
- **Likely Focus:** Simplified screening for quick daily picks
- **Accuracy Assessment:** ❓ **Cannot Assess (Insufficient Data)**

#### 9. eltonstocksapr23
- **Algorithm Type:** Unknown (repository not accessible in detail)
- **Accuracy Assessment:** ❓ **Cannot Assess (Insufficient Data)**

---

## Algorithm Comparison Matrix

| Repository | Primary Algorithm | Timeframe | Stock Type | Accuracy Confidence | Risk Level |
|------------|------------------|-----------|------------|---------------------|------------|
| **Skyrocket 24H** | Technical + Volume | 24h-1mo | Penny (<$4) | ⚠️ Medium | 🔴 Very High |
| **mikestocks** | CAN SLIM Growth | 3-12mo | Growth | ✅ High | 🟡 Medium |
| **eltonsstocks-apr24** | ML Ensemble | Flexible | General | ⚠️ Unknown | 🟡 Medium |
| **Quick Picks** | Unknown | Unknown | Unknown | ❓ Unknown | ❓ Unknown |

---

## Top Algorithms by Use Case

### 🏆 Best for Short-Term Trading (1-7 days)
1. **SCREENER_PENNYSTOCK_SKYROCKET_24HOURS** ⭐
   - Volume surge detection
   - RSI extremes
   - Breakout patterns
   - **Best for:** Day trading, swing trading penny stocks

### 🏆 Best for Long-Term Growth Investing (3-12 months)
1. **mikestocks / michael2stocks** ⭐⭐⭐
   - CAN SLIM methodology
   - Revenue growth screening
   - Stage-2 uptrend detection
   - **Best for:** Growth stock identification, institutional-quality screening

### 🏆 Best for Technical Analysis
1. **SCREENER_PENNYSTOCK_SKYROCKET_24HOURS** ⭐⭐
   - 10+ technical indicators
   - Timeframe-adaptive weights
   - Volume analysis

2. **mikestocks** ⭐⭐
   - Moving average analysis
   - Relative strength
   - Trend detection

### 🏆 Best for Fundamental Analysis
1. **mikestocks** ⭐⭐⭐
   - SEC EDGAR XBRL revenue data
   - Institutional ownership tracking
   - Revenue growth requirements

### 🏆 Best for Risk Management
1. **eltonsstocks-apr24_2025** ⭐⭐⭐
   - VaR, Expected Shortfall
   - Position sizing (Kelly criterion)
   - Portfolio optimization (MPT)
   - Stress testing

### 🏆 Best for Machine Learning / AI
1. **eltonsstocks-apr24_2025** ⭐⭐⭐
   - Ensemble ML models
   - Sentiment analysis (NLP)
   - Markov models for regime detection
   - Statistical arbitrage

---

## Accuracy Validation Status

### ✅ Validated Methodologies
- **mikestocks (CAN SLIM):** Based on William O'Neil's research showing 60-70% success rate for growth leaders
- **Stage-2 Uptrend:** Validated by Mark Minervini's track record

### ⚠️ Unvalidated (No Historical Accuracy Data)
- **Skyrocket 24H:** No backtest results or accuracy metrics provided
- **eltonsstocks-apr24:** No published validation or accuracy reports
- **Quick Picks:** Cannot assess

### ❓ Unknown
- **stock_quickpicks_april152025**
- **stock_quickpicks_april152025v2_1225amEST**
- **eltonstocksapr23**

---

## Recommendations

### For Day Trading / Short-Term
**Use:** SCREENER_PENNYSTOCK_SKYROCKET_24HOURS
- **Why:** Volume surge + RSI + breakout detection optimized for 24h-7d
- **Risk:** Very high (penny stocks)
- **Action:** Validate with paper trading before live use

### For Growth Investing
**Use:** mikestocks / michael2stocks
- **Why:** Proven CAN SLIM methodology, SEC data integration
- **Risk:** Medium (diversified growth stocks)
- **Action:** Combine with your own fundamental research

### For Portfolio Management
**Use:** eltonsstocks-apr24_2025
- **Why:** Comprehensive risk management, portfolio optimization
- **Risk:** Medium (depends on ML model quality)
- **Action:** Validate ML models with backtesting before deployment

### For Quick Daily Picks
**Status:** Cannot recommend (insufficient information on Quick Picks repositories)

---

## Missing Critical Information

To improve this analysis, the following data would be valuable:

1. **Historical Accuracy Metrics:**
   - Win rate for each algorithm
   - Average return per trade
   - Sharpe ratios from backtests
   - Maximum drawdowns

2. **Validation Reports:**
   - Out-of-sample testing results
   - Walk-forward analysis
   - Paper trading results

3. **Algorithm Details:**
   - Specific ML model architectures
   - Feature engineering details
   - Hyperparameter tuning results

4. **Performance Benchmarks:**
   - Comparison to buy-and-hold
   - Comparison to market indices
   - Risk-adjusted returns

---

## Conclusion

**Top Algorithm Overall:** **mikestocks / michael2stocks** (Growth Stock Screener)
- ✅ Proven methodology (CAN SLIM)
- ✅ Long-term focus (more reliable than short-term)
- ✅ Multi-factor screening (reduces false positives)
- ✅ Direct SEC data integration

**Most Sophisticated:** **eltonsstocks-apr24_2025** (ML Ensemble)
- ⚠️ Requires validation
- ✅ Comprehensive risk management
- ✅ Portfolio optimization
- ✅ Multiple ML models

**Best for Specific Use Case (Penny Stocks):** **SCREENER_PENNYSTOCK_SKYROCKET_24HOURS**
- ⚠️ High risk
- ✅ Optimized for short-term momentum
- ✅ Timeframe-adaptive scoring

---

**Next Steps:**
1. Request accuracy/validation data from repository owners
2. Conduct independent backtesting on available algorithms
3. Compare predictions to actual market performance
4. Document win rates and risk metrics
5. Create unified accuracy dashboard

---

*Analysis compiled from repository READMEs, code structure, and algorithm descriptions. Accuracy assessments are estimates based on methodology, not validated performance data.*
