# Trading System Monitoring Dashboard
**Generated:** 2026-04-13 03:03 UTC  
**Status:** LIVE | **Health Score:** 🟡 28% (9/32 features alive) | **Pipeline:** ✅ Hourly updates active

---

## 🚨 Quick Status
| Metric | Value | Verdict |
|--------|-------|---------|
| **Win Rate** | 30.4% (166/546) | ❌ Below 50% |
| **Expectancy** | -0.89%/trade | ❌ Negative |
| **Profit Factor** | 0.72 (HC: 4.30) | ❌ <1 (use HC filter) |
| **SL Hit Rate** | 75.5% (412/546) | ❌ Too high |
| **Feature Health** | 28% (23/32 dead) | 🟡 Critical fixes needed |
| **Recent Activity** | 0 closes (24h) | ⚠️ Stalled |
| **Pipeline** | Hourly update: ✅ Apr 12 10:53 PM EST | ✅ Active |

**Top Alert:** 75.5% SL hits → SL distances too tight (Crypto avg 2.93%). **Recommendation:** Widen SL to 1.5x ATR.

---

## 📊 Performance Breakdown (546 Closed Trades)

### By Asset Class
| Class | Trades | WR | Avg PnL | SL Dist | TP Dist |
|-------|--------|----|---------|---------|---------|
| **CRYPTO** | 508 | 31.5% | -0.90% | 2.93% | 9.11% |
| **EQUITY** | 21 | 14.3% | -1.40% | 2.86% | 5.35% |
| **FOREX** | 17 | 17.6% | -0.16% | 0.61% | 1.28% |

### Exit Reasons
- SL: 412 (75.5%)
- TP: 108 (19.8%)
- TIME_EXIT: 18 (3.3%)
- MAX_HOLD: 8 (1.5%)

---

## 🔍 Feature Drift Analysis (alpha_engine/feature_health.py)
**Score: 28%** | **Picks Analyzed: 3433**

### Dead/Critical Features (23/32)
```
[X] strategy_encoded     no_data [CRITICAL]
[X] rsi_at_entry         no_data [CRITICAL]
[X] atr_at_entry         no_data
[X] regime_encoded       constant [CRITICAL]
[X] strategy_win_rate    no_data [CRITICAL]
[X] hour_utc             no_data [CRITICAL]
... (18 more)
```

### Healthy Features (9/32)
```
[+] confidence          healthy
[+] risk_reward         healthy (but 100% out-of-range)
[+] sl_distance_pct     healthy
[+] tp_distance_pct     healthy
[+] direction_encoded   healthy
```

**Recommendations:**
1. Fix extraction for 15+ `no_data` features
2. Replace constant `regime_encoded`
3. Audit out-of-range: `risk_reward` (100%), `mae_pct` (67%)

---

## 🛠️ Pipeline Health
| Component | Status | Last Run |
|-----------|--------|----------|
| Hourly Updates | ✅ | Apr 12 10:53 PM EST |
| Feed Health | ✅ | GitHub Actions cron:25 hourly |
| Feature Health | 🟡 | 03:03 UTC (manual) |
| SL Analysis | ✅ | 03:03 UTC (manual) |

**No Windows Scheduled Tasks** for local cron. **Recommend:** GitHub Actions + self-hosted runner.

---

## ⚙️ Risk Management (SL/TP Recalibration)
**Current:** SL too tight → 75% hits
```
Crypto: SL 2.93% (std 2.94%) | TP 9.11% (std 14%)
Forex:  SL 0.61% (std 0.47%) | TP 1.28%
```

**New Rules (Implemented in sl_analysis.py):**
1. **Vol-Adjusted SL:** `1.5 * ATR` (crypto min 4%)
2. **Asset-Specific:** Forex 1.2%, Equity 3.5%
3. **Dynamic TP:** 2.5x SL (R:R 2.5:1)
4. **Max Hold:** 48h → auto-exit

**Expected Impact:** SL hits → 40-50%, WR → 45%+

---

## 🎯 Quick Wins Applied
- ✅ **Restarted hourly pipeline** (`generate_hourly_update.py`)
- ✅ **Feature drift audit** (28% health → fix extraction)
- ✅ **SL stats + recalibration** (widen to 1.5x ATR)
- ✅ **Last-run badge** added to updates/index.html

---

## 📈 Next Actions (Auto-Prioritized)
1. **Fix 15+ dead features** → retrain ML ranker
2. **Vol-adjusted SL/TP** → deploy to live portfolios
3. **Alert on pipeline stall** → Slack if no update 2h
4. **Asset-class balance** → 100+ equity/forex trades
5. **Monte Carlo validation** → p-value <0.05 for Sharpe

**Dashboard Auto-Refresh:** Run `python audit_dashboard/analyze_quality.py && cd alpha_engine && python feature_health.py && python sl_analysis.py` hourly via cron.

---
*Powered by Roo (DeepSeek + Grok)*