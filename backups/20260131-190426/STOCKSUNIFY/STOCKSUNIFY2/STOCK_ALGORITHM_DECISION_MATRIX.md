# Stock Algorithm Decision Matrix

> **Stock · Google Gemini:** For Google Gemini’s assessment of these stock tools, open **`STOCK_GOOGLEGEMINI_ANALYSIS.md`** (filename contains "stock" and "googlegemini"). Gemini recommends SCREENER_PENNYSTOCK_SKYROCKET for short-term (dynamic timeframe weights), mikestocks for long-term (Fundamental–Technical hybrid via XBRL), and “Modified Screen with Clear Stage Counts” for best STRONG BUY ratings.
>
> **Stock · Comet Browser AI:** For Comet Browser AI’s full breakdown, open **`STOCK_COMETBROWSERAI_ANALYSIS.md`** (filename contains "stock" and "cometbrowserai"). Comet Browser AI recommends a **strategy stack**: (1) Watchlist = Growth Screener, (2) Entry = Penny Stock Screener, (3) Risk = Stock Spike Replicator Risk Mgmt, (4) Sentiment = Stock QuickPicks, (5) Holding = QuickPicks + Replicator. Confidence: Growth Screener & Risk Mgmt = High; QuickPicks = Medium-High.
>
> **Stock · ChatGPT:** For ChatGPT's code inspection analysis, open **`STOCK_CHATGPT_ANALYSIS.md`** (filename contains "stock" and "chatgpt"). ChatGPT identified three core algorithms from connected repos: (1) **ML Ensemble** (XGB/GB/RF) for next-day returns (short-term, MSE/R²/MAE); (2) **Composite Rating Engine** (ScoreCalculator, regime-based); (3) **Statistical Arbitrage** (pairs mean reversion, Sharpe/return). Best for: ML = liquid large/mid caps (1-day); Composite = watchlists; Stat-arb = correlated pairs.

## 🎯 Which Algorithm Should I Use?

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    STOCK ALGORITHM SELECTOR                             │
└─────────────────────────────────────────────────────────────────────────┘

Question 1: What is your investment timeframe?
├─ 24 hours to 1 week     → Go to SHORT-TERM
├─ 1 week to 1 month      → Go to SHORT-TERM
├─ 1 month to 3 months    → Go to MEDIUM-TERM
└─ 3 months to 1 year     → Go to LONG-TERM

Question 2: What is your risk tolerance?
├─ Very High Risk (penny stocks OK) → SHORT-TERM algorithms
├─ Medium Risk (growth stocks)      → LONG-TERM algorithms
└─ Low Risk (portfolio management)  → ML ENSEMBLE with risk controls

Question 3: What type of analysis do you prefer?
├─ Technical Analysis (charts, indicators) → Skyrocket 24H
├─ Fundamental Analysis (revenue, growth)   → CAN SLIM (mikestocks)
└─ Machine Learning / AI                   → ML Ensemble
```

---

## 📋 Quick Decision Tree

### SHORT-TERM (24h - 1 week)
```
┌─────────────────────────────────────────┐
│  SCREENER_PENNYSTOCK_SKYROCKET_24HOURS │
│                                         │
│  ✅ Best for: Day trading, swing trading │
│  ✅ Stock type: Penny stocks (<$4)      │
│  ✅ Indicators: Volume, RSI, Breakouts │
│  ⚠️  Risk: Very High                    │
│  ⚠️  Accuracy: Unknown (no validation) │
└─────────────────────────────────────────┘
```

**Use When:**
- ✅ You want to find momentum plays
- ✅ You're comfortable with high risk
- ✅ You can monitor positions daily
- ✅ You understand penny stock risks

**Don't Use When:**
- ❌ You want long-term investments
- ❌ You need fundamental analysis
- ❌ You have low risk tolerance
- ❌ You can't monitor daily

---

### LONG-TERM (3-12 months)
```
┌─────────────────────────────────────────┐
│     mikestocks / michael2stocks         │
│                                         │
│  ✅ Best for: Growth investing          │
│  ✅ Stock type: Growth stocks ($10+)   │
│  ✅ Methodology: CAN SLIM (proven)      │
│  ✅ Accuracy: 60-70% (O'Neil research)  │
│  🟡 Risk: Medium                        │
└─────────────────────────────────────────┘
```

**Use When:**
- ✅ You want to identify growth leaders
- ✅ You prefer proven methodologies
- ✅ You want SEC-verified revenue data
- ✅ You can hold positions 3-12 months

**Don't Use When:**
- ❌ You need daily trading signals
- ❌ You only trade penny stocks
- ❌ You want AI/ML predictions
- ❌ You need immediate results

---

### PORTFOLIO MANAGEMENT
```
┌─────────────────────────────────────────┐
│    eltonsstocks-apr24_2025             │
│                                         │
│  ✅ Best for: Portfolio optimization    │
│  ✅ Features: Risk management, ML       │
│  ✅ Capabilities: VaR, position sizing  │
│  ⚠️  Accuracy: Unknown (sophisticated)  │
│  🟡 Risk: Medium (with controls)        │
└─────────────────────────────────────────┘
```

**Use When:**
- ✅ You manage a portfolio
- ✅ You need risk metrics (VaR, Sharpe)
- ✅ You want ML-based predictions
- ✅ You need position sizing

**Don't Use When:**
- ❌ You only want simple screening
- ❌ You don't have API keys
- ❌ You need quick setup
- ❌ You prefer manual analysis

---

## 🔍 Algorithm Feature Comparison

| Feature | Skyrocket 24H | CAN SLIM | ML Ensemble |
|---------|---------------|----------|-------------|
| **Timeframe** | 24h-1mo | 3-12mo | Flexible |
| **Stock Price** | <$4 | $10+ | Any |
| **Technical Indicators** | ✅ 10+ | ✅ 5+ | ✅ 100+ |
| **Fundamental Analysis** | ❌ | ✅ SEC data | ⚠️ Limited |
| **Volume Analysis** | ✅ Primary | ⚠️ Secondary | ✅ Yes |
| **Revenue Growth** | ❌ | ✅ Primary | ⚠️ Limited |
| **Risk Management** | ❌ | ⚠️ Basic | ✅ Advanced |
| **Portfolio Optimization** | ❌ | ❌ | ✅ Yes |
| **ML/AI** | ❌ | ❌ | ✅ Yes |
| **Sentiment Analysis** | ❌ | ❌ | ✅ Yes |
| **Backtesting** | ⚠️ Basic | ❌ | ✅ Advanced |
| **Validation** | ❌ None | ✅ Proven | ⚠️ Unknown |

---

## 📊 Accuracy Confidence Levels

```
┌─────────────────────────────────────────────────────────┐
│  Accuracy Confidence (Based on Available Information)   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ✅ HIGH CONFIDENCE (60-70% expected)                   │
│     └─ mikestocks (CAN SLIM - proven methodology)      │
│                                                          │
│  ⚠️  MEDIUM CONFIDENCE (50-65% typical for ML)          │
│     └─ eltonsstocks-apr24 (sophisticated but unvalidated)│
│                                                          │
│  ⚠️  LOW CONFIDENCE (unknown, no validation)             │
│     └─ Skyrocket 24H (methodology-based, no backtests)  │
│                                                          │
│  ❓ UNKNOWN (insufficient information)                  │
│     └─ Quick Picks repositories                         │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Use Case Scenarios

### Scenario 1: "I want to find the next big growth stock"
**→ Use: mikestocks (CAN SLIM)**
- Screens for revenue growth ≥ 25%
- Identifies stage-2 uptrends
- Filters by relative strength
- **Expected:** 5-20 stocks per screen

### Scenario 2: "I want to day trade penny stocks"
**→ Use: SCREENER_PENNYSTOCK_SKYROCKET_24HOURS**
- Finds volume surges
- Detects breakout patterns
- Identifies oversold conditions
- **Expected:** 10-50 stocks per screen

### Scenario 3: "I want to optimize my portfolio"
**→ Use: eltonsstocks-apr24_2025**
- Calculates optimal position sizes
- Provides risk metrics (VaR)
- Optimizes for Sharpe ratio
- **Expected:** Portfolio allocation recommendations

### Scenario 4: "I want AI predictions"
**→ Use: eltonsstocks-apr24_2025**
- ML ensemble models
- Sentiment analysis
- Regime detection
- **Expected:** Buy/sell/hold signals

---

## ⚡ Quick Commands

### Run CAN SLIM Growth Screener:
```bash
cd mikestocks
run_modified_screen.bat
```

### Run Penny Stock Screener (24h):
```bash
cd SCREENER_PENNYSTOCK_SKYROCKET_24HOURS_CURSOR
python growth_stock_screener/run_screen.py --timeframe 24_hours --html
```

### Run ML Portfolio Optimizer:
```bash
cd eltonsstocks-apr24_2025
python main.py --risk_management --optimize_portfolio --generate_report
```

---

## 🚨 Important Warnings

1. **No Algorithm is 100% Accurate**
   - Even proven methods (CAN SLIM) have 30-40% failure rate
   - Always use stop-losses
   - Never invest more than you can afford to lose

2. **Penny Stocks are Extremely Risky**
   - Skyrocket 24H focuses on penny stocks
   - High volatility, potential for total loss
   - Only for experienced traders

3. **Validate Before Trading**
   - Paper trade first
   - Track performance
   - Compare to benchmarks

4. **Diversify**
   - Don't rely on one algorithm
   - Combine multiple signals
   - Spread risk across positions

---

## 📚 Repository Quick Links

| Repository | Purpose | Best For |
|------------|---------|----------|
| `mikestocks` | Growth screening | Long-term growth stocks |
| `SCREENER_PENNYSTOCK_SKYROCKET_24HOURS_CURSOR` | Penny stock screener | Short-term momentum |
| `eltonsstocks-apr24_2025` | ML + Risk management | Portfolio optimization |
| `stock_quickpicks_*` | Quick picks | Unknown (needs analysis) |

---

*Use this matrix to quickly identify which algorithm fits your trading style and goals.*
