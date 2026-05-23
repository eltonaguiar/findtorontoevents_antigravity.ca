# 🎯 DAILY_IDEAS_OPENMONOAGENT.MD - Statistical Edge Analysis

> **Generated:** 2026-05-17 03:56:53
> **Total Picks Analyzed:** 8421
> **Overall Mean PnL:** 0.1258%

---
## 🎯 KEY STATISTICAL EDGES DISCOVERED
---

### 🥇 EDGE #1: COMMODITY MOMENTUM STRATEGY

**Current Performance:**
- Win Rate: **60.2%** (213/354 trades)
- Avg PnL: **++0.02%** per trade
- Total Trades: 354

**Statistical Significance:**
- Sharpe Proxy: 0.403
- Z-Score: 7.57 (Significant at p<0.05)

**Action Items:**
1. **REDUCE FILTERS:** Commodity picks are currently over-filtered
2. **Increase Allocation:** This is our strongest edge with 60%+ WR
3. **Relax Confidence Threshold:** Lower from 0.75 to 0.65 for COMMODITY

### 🥈 EDGE #2: HIGH-PERFORMING CRYPTO STRATEGIES

**Top Crypto Strategies by Win Rate:**

| Strategy | Trades | WR%  | Avg PnL% | Recommendation |
|----------|-------:|------|---------:|----------------|
| ml_enhanced_ZKUSDT_4h_D_ensemble_stack   |      9 | 100.0% |     0.03% | Keep & Scale |
| ml_enhanced_DYDXUSDT_15m_D_ensemble_stac |     31 | 96.8% |     0.02% | Keep & Scale |
| ml_enhanced_INJUSDT_1d_B_lightgbm        |     28 | 96.4% |     0.14% | Keep & Scale |
| ml_enhanced_STRKUSDT_15m_D_ensemble_stac |     29 | 89.7% |     0.01% | Keep & Scale |
| ml_enhanced_BNBUSDT_15m_B_lightgbm       |     19 | 89.5% |     0.05% | Keep & Scale |
| cot_positioning                          |    134 | 78.4% |     0.03% | Keep & Scale |
| cftc_cot_commercial_signal               |    131 | 74.8% |     0.03% | Keep & Scale |
| macd_crossover                           |     16 | 68.8% |     0.02% | Monitor Closely |

**Action Items:**
1. These strategies show strong edges - consider reducing sample requirements
2. ML ensemble stacks (DYDX, INJ, STRK) showing 89-96% WR - investigate patterns

### 🥉 EDGE #3: SHORT/SELL BIAS OPPORTUNITY

- **SHORT/SELL:** 52.8% WR, **+-0.01%** avg PnL (916 trades)
- **LONG/BUY:**  28.7% WR,  **+-0.03%** avg PnL (1609 trades)

**Finding:** Short/Sell strategies outperform Long/Buy by ~24% WR
**Action:** Consider biasing toward short-side opportunities when signals are equal

---
## 🚨 CRITICAL SAFETY GATE ISSUES REQUIRING FIXES
---

### 🚨 ISSUE #1: FOREX TP/SL BUG (CRITICAL)

**Impact:** 567 total picks, but only 9 forex closed
**Win Rate:** 33.3% (3W / 6L)

1. PROBLEM 1: 7/9 picks closed at 0.0% PnL (expired without hitting TP or SL). TP targets too far for hold period.
2. PROBLEM 2: Heavy LONG bias (6/9). Strategies generating mostly BUY regardless of trend direction.
3. PROBLEM 3: Only 9 forex closed picks out of 567 total (1.6%). Severely underrepresented.
4. PROBLEM 4: session_momentum_continuation STILL has tp_mult=2.5 (UNFIXED BUG on lines 610 and 636 of forex_strategies.py). This is the old crypto-scale TP that was supposed to be fixed to 1.2x.
5. PROBLEM 5: REZ-USD pick was misclassified as forex (it is a crypto token). Category assignment bug.
6. PROBLEM 6: 2 of 12 forex strategies hard-disabled (forex_logistic_direction + community_london_breakout_v2_forex).

**FIX REQUIRED:**
```diff
+ File: alpha_engine/forex_strategies.py
+ Lines: 610, 636
+ Change: tp_mult = 2.5 → tp_mult = 1.2
+ Reason: Using crypto-scale TP for forex pairs causes premature expirations
```

---
## 💡 IMMEDIATE ACTION ITEMS
---

### Priority 1: Fix Forex TP/SL Bug 🔧
- **File:** `alpha_engine/forex_strategies.py`
- **Lines:** 610, 636
- **Change:** `tp_mult = 2.5` → `tp_mult = 1.2`
- **Impact:** Recover ~7 expired picks with proper TP hits

### Priority 2: Enable Commodity Edge 📈
- **Current WR:** 60.2% (354 trades)
- **Action:** Reduce confidence filter from 0.75 to 0.65 for COMMODITY
- **Expected Impact:** Could increase commodity picks by 2-3x while maintaining edge

### Priority 3: Review Hard-Killed Strategies 🔍
- Check `crypto_risk_gates.py` HARD_KILL_STRATEGIES set
- Some may be underperforming due to recent market conditions
- Consider re-evaluating after 20+ trades minimum

### Priority 4: Crypto Confidence Optimization 🪙
- **Best Confidence Bucket:** 0.75-0.84 (58.3% WR)
- **Current Minimum:** 0.75
- **Recommendation:** Consider lowering to 0.65 with tighter SL for more signals

---
## 📊 DETAILED METRICS BY ASSET CLASS
---

| Asset Class | Trades | WR%  | Avg PnL% | Sharpe Proxy | Status        |
|-------------|-------:|------|---------:|--------------|---------------|
| COMMODITY    |    354 | 60.2% |     0.02% |  +0.403 | ✅ STRONG EDGE |
| CRYPTO       |   6884 | 32.8% |    -0.15% |  -0.327 | ⚠️ NEEDS OPT |
| FOREX        |    932 | 25.6% |    -0.00% |  -0.519 | ⚠️ NEEDS OPT |
| FUTURES      |    203 |  3.0% |    -0.03% |  -1.681 | ⚠️ NEEDS OPT |

---
## 📈 TOP 10 PERFORMING STRATEGIES
---

| Rank | Strategy | Trades | WR%  | Avg PnL% | Profit Factor |
|------|----------|-------:|------|---------:|--------------:|
| 1   | ml_enhanced_LINKUSDT_15m_D_ensemble_stac |      1 | 100.0% |     0.01% | 999.00       |
| 2   | ml_enhanced_SEIUSDT_15m_D_ensemble_stack |      1 | 100.0% |     0.01% | 999.00       |
| 3   | ml_enhanced_ATOMUSDT_15m_B_lightgbm      |      1 | 100.0% |     0.01% | 999.00       |
| 4   | ml_enhanced_POLUSDT_15m_D_ensemble_stack |      1 | 100.0% |     0.01% | 999.00       |
| 5   | ml_enhanced_BTCUSDT_1h_B_lightgbm        |      1 | 100.0% |     0.09% | 999.00       |
| 6   | ml_enhanced_TRXUSDT_1h_D_ensemble_stack  |      1 | 100.0% |     0.01% | 999.00       |
| 7   | ml_enhanced_TRXUSDT_4h_D_ensemble_stack  |      1 | 100.0% |     0.01% | 999.00       |
| 8   | ml_enhanced_SUIUSDT_1h_A_xgboost         |      1 | 100.0% |     0.15% | 999.00       |
| 9   | ml_enhanced_ARBUSDT_1h_D_ensemble_stack  |      1 | 100.0% |     0.16% | 999.00       |
| 10   | ml_enhanced_OPUSDT_1h_B_lightgbm         |      1 | 100.0% |     0.07% | 999.00       |

---
## 🎓 CONCLUSION
---

### Summary of Findings:

1. **COMMODITY (60.2% WR)** - Our strongest statistical edge, currently over-filtered
2. **SHORT/SELL bias (52.8% WR vs 28.7% LONG)** - Clear directional preference
3. **Forex TP/SL bug** - Critical fix needed to recover expired picks
4. **Crypto strategies showing ML ensemble edge** - DYDX, INJ, STRK stacks performing exceptionally

### Next Steps:

1. ✅ Fix forex_strategies.py TP/SL bug (lines 610, 636)
2. ✅ Reduce commodity confidence filter from 0.75 to 0.65
3. 🔄 Review high performers - investigate ML ensemble patterns
4. ⏳ Re-evaluate hard-killed strategies after more data
5. ⏳ Consider score threshold reduction from 50 to 45 for crypto/forex
