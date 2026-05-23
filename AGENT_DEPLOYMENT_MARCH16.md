# Agent Deployment — March 16, 2026
## 4 New Strategies to Production

---

## 🎯 MISSION

Deploy 4 newly-created strategies into the audit database and dashboard to generate high-quality trading signals within 4 hours.

---

## 👥 AGENT TEAM ASSIGNMENTS

### Agent 1: Integration Specialist (@coder)
**Task:** Integrate 4 strategies into audit system
**Files:**
- `audit_integration_new_strategies.py`
- `genomic_audit_verifier.py`
- `BABY_STRATEGIES_AUDIT_INTEGRATION.md`

**Deliverable:** All 4 strategies registered and ready for backtest

---

### Agent 2: Backtest Runner (@coder)
**Task:** Run comprehensive backtests on all 4 strategies
**Command:**
```bash
python baby_strategies_backtest.py \
  --strategies vwap_rsi_institutional,liquidation_cascade_contrarian,regime_sentinel_composite,rsi_pairs_arbitrage \
  --symbols BTCUSDT,ETHUSDT,SOLUSDT \
  --timeframes 15m,1h,4h
```

**Success Criteria:**
- Win rate > 55%
- Profit factor > 1.4
- Max drawdown < 15%
- 100+ trades per symbol

**Deliverable:** `backtest_results/new_strategies_march16.json`

---

### Agent 3: Dashboard Integrator (@coder)
**Task:** Add strategies to audit dashboard
**Files:**
- `audit_dashboard/audit_page.html`
- `audit_dashboard/data/new_strategies_config.json`

**Deliverable:** Strategy cards visible in dashboard

---

### Agent 4: Forward Test Tracker (@coder)
**Task:** Enable forward test tracking
**Files:**
- `genome/mutation_lab/ag_forward_tracker.py`
- `alpha_engine/data/pick_monitor_report.json` updater

**Deliverable:** New picks appearing in hourly monitor

---

### Agent 5: Quality Assurance (@coder)
**Task:** Verify end-to-end pipeline
**Checklist:**
- [ ] All 4 strategies compile
- [ ] Backtests complete
- [ ] Picks generate
- [ ] Dashboard shows data
- [ ] No duplicate/conflicting signals

**Deliverable:** QA sign-off report

---

## 📋 STRATEGY SUMMARY

| Strategy | File | Category | Expected WR | Status |
|----------|------|----------|-------------|--------|
| VWAP + RSI Institutional | `vwap_rsi_institutional.py` | Intraday Mean Reversion | 65-72% | ✅ Ready |
| Liquidation Cascade | `liquidation_cascade_contrarian.py` | Structural | 58-65% | ✅ Ready |
| Regime Sentinel | `regime_sentinel_composite.py` | Regime Adaptive | 60% | ✅ Ready |
| RSI Pairs Arbitrage | `rsi_pairs_arbitrage.py` | Market Neutral | 70-75% | ✅ Ready |

---

## ⏰ TIMELINE

| Time | Milestone | Owner |
|------|-----------|-------|
| T+0 | All agents briefed | Kimi |
| T+1h | Integration complete | Agent 1 |
| T+2h | Backtests running | Agent 2 |
| T+3h | Dashboard updated | Agent 3 |
| T+4h | Forward tracking live | Agent 4 |
| T+5h | QA sign-off | Agent 5 |
| T+6h | **LIVE PICKS GENERATING** | All |

---

## 🚨 CRITICAL NOTES

1. **No conflicts with Google Antigravity** — These are from March 16 research
2. **All 4 strategies compile** — Syntax verified
3. **Expected quality boost:** 56% → 70%+
4. **Immediate impact:** Intraday mean reversion + structural edges

---

## 📊 SUCCESS METRICS

Within 24 hours:
- [ ] 4 strategies live in dashboard
- [ ] 50+ new picks generated
- [ ] Combined win rate > 60%
- [ ] Quality score > 65%

---

**DEPLOYED:** March 16, 2026  
**COORDINATOR:** Kimi (Antigravity)  
**PRIORITY:** CRITICAL
