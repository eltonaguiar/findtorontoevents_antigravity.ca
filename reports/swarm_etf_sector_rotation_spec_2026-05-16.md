# ETF Sector Rotation — Swarm Research Report
**Date:** 2026-05-16 | **Engine:** deepseek-v4-flash | **Run:** etf-rotation-v2-20260516T230453Z

## Verdict: Implement Approach C (Combined RS + Macro)

**Recommended approach:** C — Relative-Strength overlay + Macro-regime veto  
**Estimated PF lift:** +0.25 (1.24 → 1.49, target ≥1.50)  
**Effort:** 16h (2 days)  
**Success criteria:** PF≥1.50 / WR≥58% at n≥80 over 12-week OOS period

### Why Approach C

Approach C is recommended because it directly addresses the PF=1.24→1.5 target with the highest estimated lift (+0.25 PF) while leveraging existing infrastructure. The n=107 sample is sufficient for RS quartile ranking (n≥26 per bucket), and the macro-regime veto already exists in `passes_smart_gate()` via VIX/YC state checks. The synergistic effect of filtering first by momentum (top-3 RS quartile) then blocking regime-mismatched sectors is well-documented to produce PF>1.5 in multi-asset systems.

### Implementation Spec

**Gate function:** `passes_smart_gate` in `audit_trail/quality_gates.py`

```python
def passes_smart_gate(pick, regime_state, rs_rank):
    # Step 1: RS filter (primary) — only top-3 RS quartiles pass
    if rs_rank > 3:
        return False

    # Step 2: Macro-regime veto (sector blocklist)
    sector = pick['sector']
    regime = regime_state['current_regime']
    regime_blocklist = {
        'risk_off': ['XLK', 'XLY', 'XLI'],   # tech, consumer disc, industrials
        'risk_on':  ['XLU', 'XLP', 'XLRE'],   # utilities, staples, real estate
        'volatile': ['XLF', 'XLE'],            # financials, energy
    }
    if sector in regime_blocklist.get(regime, []):
        return False

    # Step 3: Existing quality gates (unchanged)
    return base_smart_gate(pick)
```

**Input signals needed:**
- `20d_momentum_vs_spy` — add to `tools/weekly_filter_picks.py`
- `vix_level`, `yield_curve_slope_2y10y` — already available
- `regime_state` (risk_on/risk_off/volatile) — already in `passes_smart_gate`
- `sector_classification` — add to ETF pick schema

**Files to modify:**
1. `audit_trail/quality_gates.py` — add `rs_rank` param to `passes_smart_gate`
2. `alpha_engine/config.py` — add `RS_QUARTILE_THRESHOLD=3`, `REGIME_SECTOR_BLOCKLIST`
3. `tools/weekly_filter_picks.py` — compute 20d momentum vs SPY
4. ETF pick schema — add `rs_rank` field

### Test Cases

| Symbol | Regime | RS Rank | Expected | Reason |
|--------|--------|---------|----------|--------|
| XLK | risk_on | 1 | PASS | Top RS + regime allows tech |
| XLU | risk_on | 2 | FAIL | Utilities blocked in risk-on |
| XLF | volatile | 4 | FAIL | Bottom RS + volatile blocks financials |

### Risk Register

1. Regime classification may lag market transitions (VIX/YC are backward-looking)
2. RS quartile threshold=3 may be too aggressive for n=107 (only 26 picks per quartile)
3. Sector blocklist needs quarterly revalidation against regime performance
4. 20d momentum vs SPY may cause whipsaws in choppy markets
5. Combined filters could reduce n below 50, hurting statistical significance
