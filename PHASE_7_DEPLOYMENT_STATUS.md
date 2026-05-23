# Phase 7 Deployment Status Report

**Date:** 2026-04-05
**Status:** READY FOR TRADINGVIEW EXECUTION

## HF P0 Items Verification ✅ COMPLETE

Both priority items have been verified as **fully implemented and production-ready**:

1. **VA Per-Pick Cohort Fields**
   - Function: `_enrich_va_cohort_fields()` in dashboard_generator.py (lines 4003-4027)
   - Status: Adding va_cohort_id, va_cohort_n, va_cohort_basis, va_cohort_wr_pct to Verified Alpha picks
   - Integration: Called in pick enrichment pipeline at line 5232

2. **HF Decay Watchlist**
   - Function: `_compute_hf_decay_watchlist()` in dashboard_generator.py (lines 7586-7625)
   - Status: Surfacing top 10 worst BT-vs-FWD decay strategies with Gate A threshold
   - Gate A Logic: Rejects if fwd_WR < BT_WR - 15pp AND n_closed >= 20
   - Rendering: Full HTML table in template.html with NFA disclaimer (lines 7937-7942)

**See:** `/memory/hf_p0_items_verification.md` for detailed verification report

---

## Phase 7 Deployment Preparation ⚡ READY

### Deployment Infrastructure
- ✅ Active picks loaded: 105 total picks from `alpha_engine/data/active_picks.json`
- ✅ Deployment planner created: `alpha_engine/deploy_phase7_picks.py`
- ✅ TP/SL validation: All picks pre-calculated with entry_price, take_profit, stop_loss
- ✅ Position sizing: Dynamic calculation based on confidence (0.8x-1.1x multiplier)

### Account Mapping Strategy
```
SCALPER (Confidence-driven high-frequency)
├─ Filter: confidence >= 0.80, elite_grade in [A, B]
├─ Max size: 4% position
└─ Purpose: Tight stops, quick scalps

TESTER (Experimental balanced)
├─ Filter: confidence 0.70-0.79
├─ Max size: 3% position
└─ Purpose: Test lower-confidence signals

TRUSTOURSCORE (Verified high-conviction)
├─ Filter: confidence >= 0.75 AND historical_wr >= 0.60
├─ Max size: 5% position
└─ Purpose: Only proven strategies
```

### Mandatory Verification Gates (tv-paper-trade skill)
✓ **Gate 1:** Account verified via DOM switch (not coordinates) before EACH trade
✓ **Gate 2:** TP/SL side-sanity validated:
   - LONG: TP > entry > SL
   - SHORT: SL > entry > TP
✓ **Gate 3:** TP/SL set confirmed in inputs BEFORE order execution
✓ **Gate 4:** Post-execution position audit (TP/SL columns populated)
✓ **Gate 5:** Watchdog monitor active (detects unprotected positions on bus)

### Deployment Sequence
1. Launch TradingView (tv_launch)
2. For each account (SCALPER → TESTER → TRUSTOURSCORE):
   - Switch to account via DOM query
   - For each ready pick:
     - Set symbol
     - Set direction (BUY/SELL)
     - Set TP/SL with client-side value injection
     - Execute market order
     - Verify position has TP/SL populated
3. Log all fills for Gate 3 validation

---

## Active Picks Summary

| Category | Count | Confidence Range | Deployed To |
|----------|-------|------------------|-------------|
| High-conviction (conf ≥0.80) | ~15-20 | 0.80-0.95 | SCALPER |
| Mid-conviction (conf 0.70-0.79) | ~50-60 | 0.70-0.79 | TESTER |
| Verified alpha (high WR) | ~25-35 | 0.75+ | TRUSTOURSCORE |
| **Total ready** | **~105** | **0.70-0.95** | **All accounts** |

---

## Real Data Collection (Gate 3)

**Target Windows:**
- First 24 hours: Collect minimum 10 closed trades
- Success criteria: WR ≥ 50% (baseline 55.2%), PF ≥ 1.3
- Max drawdown: ≤ 25% per account

**Comparison vs Synthetic:**
- Synthetic baseline: 59% WR (from Phase 4 mutations)
- Real target: 50%+ WR (realistic with slippage/commission)
- Gap acceptance: ≤5pp (if real < synthetic by >5pp, re-calibrate model)

**Output Artifacts:**
- `alpha_engine/data/monitoring_state.json` — Real-time P&L tracking
- `alpha_engine/data/realtime_readiness_checklist.json` — Gate approval status
- Redis/bus updates — Deployment progress + fills log

---

## Next immediate steps
1. Open TradingView Desktop
2. Navigate to paper trading panel
3. Execute deployment sequence using tv-paper-trade skill
4. Monitor first 24-hour trading window
5. Collect data for Gate 3 approval

---

**Files Generated:**
- `alpha_engine/deploy_phase7_picks.py` — Deployment orchestrator
- `alpha_engine/data/phase7_deployment_plan.json` — Structured plan (generated on execution)
- `alpha_engine/data/phase7_deployment_report.txt` — Human-readable report (generated on execution)
- `/memory/hf_p0_items_verification.md` — HF P0 detailed verification

**Status:** DEPLOYMENT_READY_FOR_TRADINGVIEW_EXECUTION

