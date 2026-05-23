# CODEBUFF_HISTORY - High Conviction Filter Root Cause Analysis
**Date:** 2026-04-09 02:40:00 UTC
**Analysis:** Redis Bus + CSV Data Analysis + Code Review

---

## Executive Summary

Analyzed the high-conviction filter on findtorontoevents.ca/audit that was returning picks with coin-toss (~47-52%) win rates instead of picks with actual edge. Root cause identified as **missing forward performance data in CSV exports**.

---

## Key Findings

### 1. Critical Data Flow Bug

- **All 3,429 closed picks** are missing `forward_wr` and `forward_trades` fields
- These metrics exist in `extra_json` but are NOT extracted to top-level fields in CSV exports
- The HC filter relies on these fields for quality gating - when empty, it cannot discriminate

### 2. Actual Edge (from closed picks analysis)

| Strategy | Win Rate | Wins/Total | Total PnL |
|----------|----------|------------|-----------|
| st_fear_greed_contrarian | **83.3%** | 334/401 | +566.6% |
| st_rsi_vol_bounce | **93.8%** | 15/16 | +38.9% |
| st_obv_support_divergence | **65.6%** | 107/163 | +143.8% |
| quality-minus-junk | **63.6%** | 14/22 | +14.9% |

### 3. Trust Tier Performance (from 3,429 closed picks)

| Trust Tier | Win Rate | Count |
|------------|----------|-------|
| PROVEN | **68.6%** | 778 |
| DEVELOPING | 50.0% | 46 |
| WATCH | 47.9% | 119 |
| PROBATION | 41.8% | 2273 |
| SANDBOX | **27.2%** | 213 |

**Critical:** SANDBOX strategies were being included in HC filter - these have only 27.2% WR (coin toss).

---

## Root Cause Analysis

### The Problem
1. Pick data contains `forward_wr` and `forward_trades` inside `extra_json` field
2. CSV export process does NOT extract these to top-level fields
3. HC filter gates check top-level `strat_fwd_wr` / `strat_fwd_trades` fields
4. When these are empty/0, the filter cannot apply proper quality gates
5. Result: Unvalidated SANDBOX/PROBATION strategies leak into HC picks

### Data Flow Path
```
Strategy Performance Tracking (production_scanner.py)
    -> strat_fwd_wr / strat_fwd_trades populated
    -> extra_json (contains forward metrics)
    -> CSV Export (MISSING: not extracting to top-level)
    -> HC Filter (checks top-level fields - EMPTY)
    -> Coin-toss quality picks
```

---

## Redis Bus Message Dropped

```json
{
  "type": "HC_FILTER_ROOT_CAUSE_ANALYSIS",
  "timestamp": "2026-04-09T02:38:45.502519+00:00",
  "findings": {
    "critical_bug": "forward_wr and forward_trades fields are EMPTY in CSV exports despite existing in internal data",
    "data_flow_issue": "extra_json contains forward_wr/forward_trades but export does not extract to top-level fields",
    "actual_edge_from_closed_picks": {
      "st_fear_greed_contrarian": {"wr": 83.3, "wins": 334, "total": 401, "pnl": 566.6},
      "st_rsi_vol_bounce": {"wr": 93.8, "wins": 15, "total": 16, "pnl": 38.9},
      "st_obv_support_divergence": {"wr": 65.6, "wins": 107, "total": 163, "pnl": 143.8}
    },
    "trust_tier_performance": {
      "PROVEN": 68.6,
      "DEVELOPING": 50.0,
      "WATCH": 47.9,
      "PROBATION": 41.8,
      "SANDBOX": 27.2
    },
    "fix_required": "Ensure forward_wr/forward_trades flow from extra_json or strategy performance to CSV export"
  }
}
```

---

## Files Analyzed

### Core Filter Logic
- `alpha_engine/conviction_stack.py` - HF conviction tier classification
- `tools/dashboard_hc_rules.py` - Dashboard HC filter (9-gate v3)
- `config/hc_gate_params.json` - HC filter parameters

### Data Flow
- `alpha_engine/smart_picks_engine.py` - Strategy performance tracking
- `alpha_engine/production_scanner.py` - Forward metrics calculation

### Audit Trail
- `audit_dashboard/index.html` - Dashboard UI
- `audit_dashboard/hc_filter.js` - JS filter implementation (new)

---

## Recommended Fix

1. **Fix CSV Export:** Extract `forward_wr`/`forward_trades` from `extra_json` to top-level fields
2. **Add Validation:** Ensure HC filter requires valid forward_trades > 0 before allowing tier assignment
3. **Audit Strategy Pipeline:** Ensure st_fear_greed_contrarian and other proven strategies properly feed HC filter

---

## Related Documentation

- `docs/HC_FILTER_REWRITE_V2_VALIDATION.md` - HC filter v2 validation docs
- `docs/QUANT_AUDIT_v2.md` - Quant audit v2 documentation
- `tools/backtest_hc_filter.py` - Backtest tooling

---

*Analysis completed via CODEBUFF - Automated Trading System Audit*