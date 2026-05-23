# STRATEGY INVESTIGATION: rapid_fire (C-006)

**Date:** 2026-05-18  
**Analyst:** Claude Code autonomous session  
**Scope:** rapid_fire source system — all CRYPTO closed picks  
**Decision gate:** C-007 — Deploy to 5% shadow if WR>60% AND PF>1.8

---

## Verdict: DO NOT DEPLOY — CRITERIA NOT MET

**rapid_fire overall: WR=29.0%, PF=0.16, n=207, Total PnL=-45.73 (fractional)**

Neither the WR>60% nor PF>1.8 deployment threshold is met. System remains correctly blocked.

---

## Data Summary (all-time, closed_picks.json)

| Metric | Value | Threshold | Pass? |
|--------|-------|-----------|-------|
| Win Rate | 29.0% | >60% | ❌ FAIL |
| Profit Factor | 0.16 | >1.8 | ❌ FAIL |
| Total n | 207 | ≥100 | ✅ |
| Last 90d picks | 0 | — | blocked |
| Max consecutive losses | 14 | — | HIGH RISK |
| Total cumulative PnL | -45.73 (fractional) | positive | ❌ FAIL |

---

## Sub-strategy Breakdown

| Strategy | n | WR | Avg PnL/trade | Assessment |
|----------|---|----|---------------|------------|
| volume_spike_breakout | 78 | 17% | -39.58% | KILL — catastrophic |
| macd_rsi_confluence | 66 | 36% | -16.71% | BLOCK — negative edge |
| rsi_bounce | 25 | 28% | -15.60% | BLOCK — negative edge |
| stochrsi_macd_combo | 17 | 12% | -1.41% | BLOCK — near-zero WR |
| **macd_crossover** | **16** | **69%** | **+1.56%** | **WATCH — only positive edge** |
| rsi_overbought | 5 | 60% | +1.25% | WATCH — n too small |

---

## Root Cause Analysis

### volume_spike_breakout (-39.58% avg/trade)
- WR=17% means 83% of positions hit SL
- Average SL hit rate on CRYPTO = 82-83% (from closed pick exit_reason distribution)
- Signal fires on volume spikes that are mostly fake-outs on low-cap tokens
- Tokens affected: TAOUSDT, HEMIUSDT, ORCAUSDT, SAHARAUSDT (all low liquidity)

### macd_rsi_confluence (-16.71% avg/trade)
- Confluence of two lagging indicators (both MACD and RSI are lagging)
- Double-lagging signal arrives after the move has already occurred
- WR=36% is below random walk baseline for CRYPTO (which is ~45% given the positive drift)

### macd_crossover (WR=69%, n=16) — The One Signal Worth Watching
- Positive edge detected: +1.56% avg/trade, WR=69%
- Sample too small (n=16) for deployment — need n≥50 before shadow allocation
- PBO cannot be computed with n=16 (overfitting risk high)
- **Recommendation:** Monitor only. If n grows to ≥50 with maintained WR≥60%, revisit C-007

---

## Decision: C-007

**Status: NO-GO**

| Criterion | Required | Actual | Result |
|-----------|----------|--------|--------|
| WR | >60% | 29.0% | ❌ |
| PF | >1.8 | 0.16 | ❌ |

rapid_fire remains BLOCKED. The `macd_crossover` sub-strategy is the only positive-edge component but has n=16 which is insufficient for statistical confidence.

**Next review:** 2026-06-01 — only if `macd_crossover` signals resume and reach n≥50

---

## Comparison: rapid_fire vs Deployment Threshold

```
rapid_fire overall:    WR=29%  PF=0.16  [FAR BELOW threshold]
Deployment threshold:  WR>60%  PF>1.8

macd_crossover only:   WR=69%  PF=?     [WR passes, PF unknown, n=16 too small]
```

---

## Files Referenced
- `alpha_engine/data/closed_picks.json` — source of all metrics
- `audit_trail/quality_gates.py` — rapid_fire block status
- `reports/MASTER_ACTION_PLAN_2026-05-18.md` — C-006/C-007 gate specification
