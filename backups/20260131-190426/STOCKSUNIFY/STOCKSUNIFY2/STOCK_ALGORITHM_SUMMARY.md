# Stock Algorithm Quick Reference Guide

> **Google Gemini stock assessment:** See **`STOCK_GOOGLEGEMINI_ANALYSIS.md`** for Gemini’s own analysis (file contains "stock" and "googlegemini"). Gemini highlights: (1) **Timeframe-Based Weighted Scoring** for short-term (Volume Surge, RSI, Breakouts → Bollinger Squeeze, Short Interest); (2) **Stage-Two + RS Percentile + XBRL** for long-term “super-performance” stocks; (3) **Modified Screen with Clear Stage Counts** as best rating system (STRONG BUY); (4) Short-term = catalyst/volume-driven, more false breakouts; trend tools = higher win rate.
>
> **Comet Browser AI stock assessment:** See **`STOCK_COMETBROWSERAI_ANALYSIS.md`** (file contains "stock" and "cometbrowserai"). Comet Browser AI breaks out **Stock QuickPicks** (VADER + FinBERT, You.com/Bing Copilot, trust scores), **Stock Spike Replicator** (ML vs. Risk Mgmt variants), and **Penny Stock Screeners**. Best-by-category: Short-term = Skyrocket + QuickPicks; Medium-term = Spike Replicator Risk Mgmt; Long-term = Growth Screener; Technical = Spike Replicator (100+ indicators); Valuation = Growth Screener + QuickPicks. **Recommended strategy stack:** Watchlist → Entry → Risk Mgmt → Sentiment → Holding.
>
> **ChatGPT stock assessment:** See **`STOCK_CHATGPT_ANALYSIS.md`** (file contains "stock" and "chatgpt"). ChatGPT inspected connected GitHub repos (code-level analysis) and identified: (1) **ML Ensemble** (XGBoost/GradientBoosting/RandomForest) for next-day returns (short-term, technical-heavy, MSE/R²/MAE); (2) **Composite Rating Engine** (ScoreCalculator) with regime-based weights; (3) **Statistical Arbitrage** (pairs mean reversion, Sharpe/return). Best for: ML ensemble = liquid large/mid caps (1-day); Composite rating = watchlists; Stat-arb = correlated pairs.

## 🎯 Top 3 Algorithms by Use Case

### 1. **Long-Term Growth Investing** (3-12 months)
**🏆 Winner: mikestocks / michael2stocks**

**Algorithm:** CAN SLIM Growth Screener
- **Accuracy Confidence:** ✅ High (60-70% based on O'Neil research)
- **Methodology:**
  - Relative Strength (RS) Rating ≥ 90
  - Stage-2 Uptrend (Minervini methodology)
  - Revenue Growth ≥ 25% YoY (SEC EDGAR data)
  - Institutional Accumulation
- **Best For:** Growth stocks, $10+ price range
- **Risk Level:** 🟡 Medium
- **Repository:** `mikestocks`, `michael2stocks`, `mikestocks_april272025`

---

### 2. **Short-Term Trading** (24 hours - 1 week)
**🏆 Winner: SCREENER_PENNYSTOCK_SKYROCKET_24HOURS**

**Algorithm:** Technical + Volume Momentum
- **Accuracy Confidence:** ⚠️ Medium (no validation data)
- **Methodology:**
  - Volume Surge detection
  - RSI extremes (oversold/overbought)
  - Breakout patterns (20-day high)
  - Bollinger Band Squeeze
  - Short Interest analysis
- **Best For:** Penny stocks under $4, momentum plays
- **Risk Level:** 🔴 Very High
- **Repository:** `SCREENER_PENNYSTOCK_SKYROCKET_24HOURS_CURSOR`

---

### 3. **Portfolio Management & Risk Control**
**🏆 Winner: eltonsstocks-apr24_2025**

**Algorithm:** ML Ensemble + Risk Management
- **Accuracy Confidence:** ⚠️ Unknown (sophisticated but unvalidated)
- **Methodology:**
  - Ensemble ML (Random Forest, Gradient Boosting, Neural Networks)
  - Sentiment Analysis (NLP on news/social media)
  - Markov Models (regime detection)
  - Portfolio Optimization (Modern Portfolio Theory)
  - Risk Metrics (VaR, Expected Shortfall, Sharpe Ratio)
- **Best For:** Automated trading, portfolio optimization
- **Risk Level:** 🟡 Medium (with proper risk controls)
- **Repository:** `eltonsstocks-apr24_2025`, `eltonstocksapr25bare`

---

## 📊 Algorithm Comparison

| Algorithm | Timeframe | Stock Type | Accuracy | Risk | Validation |
|-----------|-----------|------------|----------|------|------------|
| **CAN SLIM Growth** | 3-12mo | Growth ($10+) | ✅ 60-70% | 🟡 Medium | ✅ Proven |
| **Skyrocket 24H** | 24h-1wk | Penny (<$4) | ⚠️ Unknown | 🔴 Very High | ❌ None |
| **ML Ensemble** | Flexible | General | ⚠️ Unknown | 🟡 Medium | ❌ None |

---

## 🚀 Quick Start Recommendations

### If you want to identify growth stocks:
```bash
# Use mikestocks repository
cd mikestocks
python run_modified_screen.bat
```
**Expected:** Stocks with RS ≥ 90, revenue growth ≥ 25%, in stage-2 uptrend

### If you want to find short-term momentum plays:
```bash
# Use Skyrocket screener
cd SCREENER_PENNYSTOCK_SKYROCKET_24HOURS_CURSOR
python growth_stock_screener/run_screen.py --timeframe 24_hours
```
**Expected:** Penny stocks with volume surges and breakout patterns

### If you want portfolio optimization:
```bash
# Use ML ensemble system
cd eltonsstocks-apr24_2025
python main.py --risk_management --optimize_portfolio --generate_report
```
**Expected:** Optimized portfolio with risk metrics and position sizing

---

## ⚠️ Critical Gaps

### Missing Accuracy Data:
- ❌ No historical win rates
- ❌ No backtest validation results
- ❌ No comparison to benchmarks
- ❌ No risk-adjusted return metrics

### Recommended Next Steps:
1. **Backtest Validation:** Run each algorithm on historical data
2. **Paper Trading:** Test predictions in real-time (paper account)
3. **Accuracy Tracking:** Document win rates and returns
4. **Benchmark Comparison:** Compare to S&P 500, buy-and-hold

---

## 📈 Algorithm Strengths & Weaknesses

### CAN SLIM (mikestocks)
**✅ Strengths:**
- Proven methodology (William O'Neil)
- Direct SEC data integration
- Multi-factor screening
- Long-term focus (more reliable)

**❌ Weaknesses:**
- Revenue data lags (quarterly)
- May miss AI/tech stocks with future revenue
- Requires sufficient historical data

### Skyrocket 24H
**✅ Strengths:**
- Timeframe-adaptive scoring
- Multiple technical indicators
- Volume surge detection
- Fast execution

**❌ Weaknesses:**
- High risk (penny stocks)
- No fundamental analysis
- No validation data
- Data quality depends on APIs

### ML Ensemble (eltonsstocks-apr24)
**✅ Strengths:**
- Most comprehensive system
- Hedge fund-level risk management
- Multiple ML models (reduces overfitting)
- Portfolio optimization

**❌ Weaknesses:**
- Complex setup
- Requires API keys (costs)
- No published accuracy
- ML models need retraining

---

## 🎓 Best Practices

1. **Never rely on a single algorithm** - Combine multiple signals
2. **Validate before trading** - Paper trade first
3. **Use risk management** - Always set stop-losses
4. **Diversify** - Don't put all capital in one strategy
5. **Track performance** - Document all trades and outcomes

---

*Last Updated: January 27, 2026*
