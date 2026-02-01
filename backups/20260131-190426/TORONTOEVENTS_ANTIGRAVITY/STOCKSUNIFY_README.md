# STOCKSUNIFY 📈

**Unified Stock Analysis & Daily Picks**

This repository consolidates stock analysis data, algorithms, and daily picks from multiple AI-validated sources.

## 🌐 Live Site

**GitHub Pages:** [View Live Site](https://eltonaguiar.github.io/STOCKSUNIFY/)  
**Find Stocks Page:** [findtorontoevents.ca/findstocks](https://findtorontoevents.ca/findstocks/)

## 📊 Daily Stock Picks

**Last Updated:** 2026-01-27, 6:16:49 p.m.  
**Total Picks:** 30  
**Data Source:** [data/daily-stocks.json](./data/daily-stocks.json)

### Summary by Rating
- **STRONG BUY:** 7
- **BUY:** 23
- **HOLD:** 0

### Technical Momentum

**Total Picks:** 24

#### 3D Timeframe (14 picks)

**Last updated:** 2026-01-27, 6:16:49 p.m.

| Symbol | Name | Score | Rating | Risk | Key Indicators |
|--------|------|-------|--------|------|----------------|
| GM | General Motors Company | 100/100 | STRONG BUY | High | RSI: 59, Vol: 2.34x, Breakout, Bollinger Squeeze |
| PFE | Pfizer Inc. | 90/100 | STRONG BUY | High | RSI: 65, Vol: 1.42x, Breakout, Bollinger Squeeze |
| MSFT | Microsoft Corporation | 70/100 | BUY | High | RSI: 51, Vol: 1.17x, Breakout |
| GOOGL | Alphabet Inc. | 70/100 | BUY | High | RSI: 69, Vol: 0.54x, Breakout, Bollinger Squeeze |
| META | Meta Platforms, Inc. | 70/100 | BUY | High | RSI: 54, Vol: 0.81x, Breakout |
| SBUX | Starbucks Corporation | 70/100 | BUY | High | RSI: 68, Vol: 1.7x |
| F | Ford Motor Company | 70/100 | BUY | High | RSI: 52, Vol: 1.81x, Bollinger Squeeze |
| XOM | Exxon Mobil Corporation | 60/100 | BUY | High | RSI: 82, Vol: 0.71x, Breakout |
| CVX | Chevron Corporation | 60/100 | BUY | High | RSI: 82, Vol: 0.99x, Breakout |
| SLB | SLB N.V. | 60/100 | BUY | High | RSI: 81, Vol: 1.01x, Breakout |

#### 24H Timeframe (7 picks)

**Last updated:** 2026-01-27, 6:16:49 p.m.

| Symbol | Name | Score | Rating | Risk | Key Indicators |
|--------|------|-------|--------|------|----------------|
| GM | General Motors Company | 85/100 | STRONG BUY | High | RSI: 59, Vol: 2.34x, Breakout, Bollinger Squeeze |
| UNH | UnitedHealth Group Incorporate | 70/100 | BUY | High | RSI: 26, Vol: 8.16x |
| GME | GameStop Corp. | 60/100 | BUY | High | RSI: 84, Vol: 2.25x |
| XOM | Exxon Mobil Corporation | 50/100 | BUY | High | RSI: 82, Vol: 0.71x, Breakout |
| CVX | Chevron Corporation | 50/100 | BUY | High | RSI: 82, Vol: 0.99x, Breakout |
| SLB | SLB N.V. | 50/100 | BUY | High | RSI: 81, Vol: 1.01x, Breakout |
| JNJ | Johnson & Johnson | 50/100 | BUY | High | RSI: 84, Vol: 0.77x, Breakout |

#### 7D Timeframe (3 picks)

**Last updated:** 2026-01-27, 6:16:49 p.m.

| Symbol | Name | Score | Rating | Risk | Key Indicators |
|--------|------|-------|--------|------|----------------|
| PFE | Pfizer Inc. | 70/100 | BUY | High | RSI: 65, Vol: 1.42x, Breakout, Bollinger Squeeze |
| F | Ford Motor Company | 70/100 | BUY | High | RSI: 52, Vol: 1.81x, Bollinger Squeeze |
| GM | General Motors Company | 70/100 | BUY | High | RSI: 59, Vol: 2.34x, Breakout, Bollinger Squeeze |

### Composite Rating

**Total Picks:** 6

#### 1M Timeframe (6 picks)

**Last updated:** 2026-01-27, 6:16:49 p.m.

| Symbol | Name | Score | Rating | Risk | Key Indicators |
|--------|------|-------|--------|------|----------------|
| PFE | Pfizer Inc. | 75/100 | STRONG BUY | Medium | RSI: 65, Vol: 1.42x |
| SBUX | Starbucks Corporation | 70/100 | STRONG BUY | Medium | RSI: 68, Vol: 1.7x |
| F | Ford Motor Company | 70/100 | STRONG BUY | Medium | RSI: 52, Vol: 1.81x |
| GM | General Motors Company | 70/100 | STRONG BUY | Medium | RSI: 59, Vol: 2.34x |
| INTC | Intel Corporation | 60/100 | BUY | Medium | RSI: 55, Vol: 1.15x |
| GME | GameStop Corp. | 60/100 | BUY | Medium | RSI: 84, Vol: 2.25x |



## 📚 Analysis Documents

All links point to this repository ([STOCKSUNIFY](https://github.com/eltonaguiar/STOCKSUNIFY)):

### Comprehensive Analysis
- [Stock Repository Analysis](https://github.com/eltonaguiar/STOCKSUNIFY/blob/main/STOCK_REPOSITORY_ANALYSIS.md) - Analysis of 11 stock repositories
- [Algorithm Summary](https://github.com/eltonaguiar/STOCKSUNIFY/blob/main/STOCK_ALGORITHM_SUMMARY.md) - Quick reference guide
- [Decision Matrix](https://github.com/eltonaguiar/STOCKSUNIFY/blob/main/STOCK_ALGORITHM_DECISION_MATRIX.md) - Visual algorithm selector

### AI Assessments
- [Google Gemini Analysis](https://github.com/eltonaguiar/STOCKSUNIFY/blob/main/STOCK_GOOGLEGEMINI_ANALYSIS.md) - Gemini's assessment
- [Comet Browser AI Analysis](https://github.com/eltonaguiar/STOCKSUNIFY/blob/main/STOCK_COMETBROWSERAI_ANALYSIS.md) - Comet Browser AI breakdown
- [ChatGPT Analysis](https://github.com/eltonaguiar/STOCKSUNIFY/blob/main/STOCK_CHATGPT_ANALYSIS.md) - ChatGPT code inspection

## ⚠️ Methodologies Not Yet Automated

The following algorithms from the 11 stock repositories have been **identified but not yet integrated** into the automated daily pick generation:

### 1. ML Ensemble (XGBoost/Gradient Boosting)
- **Source:** Stock Spike Replicator (ML variant)
- **Status:** ❌ Not Automated
- **Features:**
  - RandomForest, GradientBoosting, XGBoost models
  - Next-day return prediction
  - Feature engineering (returns, gaps, MAs, volatility, RSI, MACD, Bollinger)
  - MSE, R², MAE metrics
- **Why Not Automated:** Requires ML model training infrastructure

### 2. Statistical Arbitrage / Pairs Trading
- **Source:** Stock Spike Replicator
- **Status:** ❌ Not Automated
- **Features:**
  - Correlated pairs detection
  - Z-score mean reversion
  - Market-neutral strategy
  - Sharpe ratio optimization
- **Why Not Automated:** Requires pairs analysis and correlation matrix

### 3. Revenue Growth (SEC XBRL Scraping)
- **Source:** mikestocks variants
- **Status:** ⚠️ Partially Automated (CAN SLIM uses RS but not XBRL)
- **Features:**
  - SEC EDGAR XBRL data extraction
  - 25%+ quarterly revenue growth filter
  - Real-time filing monitoring
- **Why Not Fully Automated:** Requires SEC EDGAR API/scraping

### 4. Institutional Accumulation Tracking
- **Source:** mikestocks variants
- **Status:** ❌ Not Automated
- **Features:**
  - Net institutional inflows/outflows
  - Quarterly ownership changes
  - Institutional flow tracking
- **Why Not Automated:** Requires institutional ownership data API

### 5. Sentiment Analysis (NLP)
- **Source:** Stock QuickPicks
- **Status:** ❌ Not Automated
- **Features:**
  - VADER sentiment analysis
  - FinBERT financial sentiment
  - News/article sentiment scoring
- **Why Not Automated:** Requires NLP libraries and news data sources

### 6. Website Prediction Tracking
- **Source:** Stock QuickPicks
- **Status:** ❌ Not Automated
- **Features:**
  - Trust score system
  - Prediction source reliability tracking
  - Accuracy tracking per source
- **Why Not Automated:** Requires web scraping infrastructure

### 7. Portfolio Optimization (Modern Portfolio Theory)
- **Source:** Stock Spike Replicator (Risk Management variant)
- **Status:** ❌ Not Automated
- **Features:**
  - Efficient Frontier calculation
  - Portfolio diversification
  - Risk-adjusted returns (Sharpe, Sortino, Calmar)
  - Position sizing (Kelly Criterion)
- **Why Not Automated:** Requires portfolio-level calculations

### 8. Market Regime Detection
- **Source:** Stock Spike Replicator (ML variant)
- **Status:** ⚠️ Partially Automated (Composite Rating has basic regime detection)
- **Features:**
  - Hidden Markov Models (HMM)
  - Regime classification (bull/bear/sideways)
  - Regime-based weight adjustments
- **Why Not Fully Automated:** Requires HMM implementation

### 9. Advanced Risk Metrics
- **Source:** Stock Spike Replicator (Risk Management variant)
- **Status:** ❌ Not Automated
- **Features:**
  - Value at Risk (VaR)
  - Expected Shortfall
  - ATR-based stop-loss/take-profit
  - Dynamic position sizing
- **Why Not Automated:** Requires risk calculation infrastructure

### 10. Backtesting with Transaction Costs
- **Source:** Multiple repositories
- **Status:** ❌ Not Automated
- **Features:**
  - Realistic backtesting
  - Slippage modeling
  - Transaction cost inclusion
  - Walk-forward analysis
- **Why Not Automated:** Requires backtesting framework

## 📋 Integration Priority

**High Priority (Most Impact):**
1. ✅ CAN SLIM Growth Screener - **DONE**
2. ✅ Technical Momentum (24h, 3d, 7d) - **DONE**
3. ✅ Composite Rating Engine - **DONE**
4. 🔄 ML Ensemble - **NEXT** (would add predictive power)
5. 🔄 Statistical Arbitrage - **NEXT** (market-neutral strategy)

**Medium Priority:**
6. Revenue Growth (SEC XBRL) - Would improve CAN SLIM accuracy
7. Sentiment Analysis - Would add catalyst detection
8. Portfolio Optimization - Would enable portfolio-level recommendations

**Low Priority (Nice to Have):**
9. Institutional Accumulation - Data lags by months
10. Website Prediction Tracking - Requires web scraping
11. Advanced Risk Metrics - More for portfolio management
12. Backtesting Framework - Validation tool, not pick generation



## 🔧 Scripts

- [generate-daily-stocks.ts](./scripts/generate-daily-stocks.ts) - Daily stock picks generator

## 🚀 Usage

### Generate Daily Stock Picks

```bash
npm install
npx tsx scripts/generate-daily-stocks.ts
```

### View Data

The daily stock picks are available as JSON:
- **Local:** `data/daily-stocks.json`
- **Web:** `https://eltonaguiar.github.io/STOCKSUNIFY/data/daily-stocks.json`

## 📈 Algorithms Currently Integrated

### ✅ 1. CAN SLIM Growth Screener (Long-term: 3-12 months)
**Status:** ✅ **AUTOMATED**  
**Accuracy:** 60-70% (based on O'Neil research)  
**Source:** mikestocks repository

**Criteria:**
- RS Rating ≥ 90 (weighted 12-month momentum)
- Stage-2 Uptrend (Minervini methodology)
- Price vs 52-week high
- RSI momentum (50-70 ideal)
- Volume surge detection

**Timeframes:** 3m, 6m, 1y

### ✅ 2. Technical Momentum Screener (Short-term: 24h-1 week)
**Status:** ✅ **AUTOMATED**  
**Source:** SCREENER_PENNYSTOCK_SKYROCKET_24HOURS repositories

**Timeframes:**
- **24h:** Volume surge (40 pts), RSI extremes (30 pts), Breakout (30 pts)
- **3d:** Volume (30 pts), Breakout (30 pts), RSI momentum (25 pts), Volatility (15 pts)
- **7d:** Bollinger squeeze (30 pts), RSI extremes (25 pts), Volume (25 pts), Institutional (20 pts)

**Indicators:**
- RSI (14-day)
- Volume Surge (current vs 10-day avg)
- Breakout detection (20-day high)
- Bollinger Band Squeeze

### ✅ 3. Composite Rating Engine (Medium-term: 1-3 months)
**Status:** ✅ **AUTOMATED**  
**Source:** Stock Spike Replicator (Composite Rating variant)

**Components:**
- Technical (40 pts): Price vs SMAs, RSI
- Volume (20 pts): Volume surge analysis
- Fundamental (20 pts): PE ratio, Market cap
- Regime Adjustment (20 pts): Normal/low-vol/high-vol market conditions

## 🔗 Source Repositories

This data is synced from:
- [TORONTOEVENTS_ANTIGRAVITY](https://github.com/eltonaguiar/TORONTOEVENTS_ANTIGRAVITY) - Main repository
- [mikestocks](https://github.com/eltonaguiar/mikestocks) - CAN SLIM Growth Screener
- [Stock Spike Replicator](https://github.com/eltonaguiar/eltonsstocks-apr24_2025) - ML + Risk Management
- [Penny Stock Screener](https://github.com/eltonaguiar/SCREENER_PENNYSTOCK_SKYROCKET_24HOURS_CURSOR) - Technical Momentum

## ⚠️ Disclaimer

Stock predictions are for informational purposes only and do not constitute financial advice. Always conduct your own research and consult with a licensed financial advisor before making investment decisions.

## 📅 Auto-Update

This README is automatically updated when `npm run stocks:sync` is run. The daily picks section reflects the latest data from `data/daily-stocks.json`.

---

*Powered by 11+ AI-validated stock analysis algorithms*  
*Last README Update: 2026-01-28T00:05:11.334Z*
