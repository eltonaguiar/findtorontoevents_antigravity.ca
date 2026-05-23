# Active Picks vs Show All Picks - Filtering Audit Report

**Date:** 2026-04-05  
**Auditor:** antigrav-filter-audit  
**Scope:** `audit_trail/quality_gates.py`, `audit_dashboard/template.html`, `audit_trail/dashboard_generator.py`

---

## Executive Summary

The filtering system for "Active Picks" vs "Show All Picks" has **multiple layers of complexity** that can lead to unexpected behavior. The main findings reveal potential **synchronization issues** between backend filtering (`passes_active_gate()`) and frontend display logic (`_showAllPicks`).

---

## Key Findings

### 1. **Complex Multi-Layer Filtering in `passes_active_gate()`**

**Location:** `audit_trail/quality_gates.py` lines 2302-2528

The active gate applies **10+ filters** in sequence:
- Symbol validation (lines 2321-2350)
- Trust tier blocking (BANNED/AVOID/UNTRUSTED) (line 2334)
- Blocked symbols (MATICUSDT, TRXUSDT, etc.) (line 2348)
- Blocked strategy+symbol pairs (line 2356)
- Mutation filter (lines 2361-2381)
- Asset×strategy/source pair blocks (lines 2403-2408)
- Non-crypto trust score < 4 filter (lines 2426-2435)
- Catastrophic track record filter (lines 2440-2458)
- Blocked source systems (lines 2463-2466)
- Rapid fire noise filter (lines 2469-2474)
- Entry price validation (lines 2477-2483)
- **Staleness filter** (lines 2487-2497) - 72h for crypto, 336h for non-crypto
- Score floor gates (lines 2517-2526)

**Risk:** Multiple filtering layers make it difficult to predict which picks will be displayed.

---

### 2. **Potential Bug: Frontend/Backend Filter Mismatch**

**Location:** `audit_dashboard/template.html` lines 7537-7540

```javascript
window._showAllPicks = !window._showAllPicks;
if (window._showAllPicks) {
    window._hfTrustBook = false;
    window._provenOnlyFilter = false;
}
```

**Issue:** The "Show All Picks" button clears HF-book and proven-only flags, but the backend `passes_active_gate()` has **additional hard-coded filters** (blocked systems, staleness, symbol blocks) that are NOT bypassed by the frontend toggle.

**Expected Behavior:** Show All should show the full raw pool  
**Actual Behavior:** Backend gates still filter out picks even in "Show All" mode

---

### 3. **Critical: Score Modification in `passes_active_gate()`**

**Location:** `audit_trail/quality_gates.py` line 2397

```python
_apply_score_penalties(pick)  # MODIFIES pick scores in-place
```

**Issue:** The function modifies pick scores via `_apply_score_penalties()`. This means:
- Raw scores from upstream systems are transformed
- Displayed scores may not match original scores
- Sorting by score may be inconsistent

**Risk:** Scores shown in "Show All" view (raw) vs "Active" view (penalized) may differ significantly.

---

### 4. **Exempt Sources Discrepancy**

**Location:** Lines 2508-2516 vs 2415-2423

Two different exempt source lists exist:

**Score Floor Exempt (all picks):**
- goldmine_stocks
- stocks_competition
- fast_stocks_competition
- stocks_forex_comp

**Non-Crypto Raw Score Exempt:**
- multi_asset
- multi_asset_institutional
- stocks_competition
- fast_stocks_competition
- stocks_forex_comp
- goldmine_stocks
- multi_asset_copytrader ← Only here
- cta_replicator ← Only here

**Issue:** `multi_asset_copytrader` and `cta_replicator` are only exempt for non-crypto picks, which may cause copytrader picks to be filtered incorrectly.

---

### 5. **Hard-Blocked Source Systems**

**Location:** Lines 553-573, 2463-2466

Blocked systems include:
- mercury2_fast
- kimi_signal_tracking
- ml_bg_system_a/b/c/f
- ml_crypto_pred_v12
- crypto_winners
- ml_bg_ensemble
- signal_validation

**Issue:** These picks are **completely hidden** from Active Picks view, regardless of individual pick quality.

---

### 6. **Staleness Filter May Hide Legitimate Picks**

**Location:** Lines 2487-2497, 586-588

```python
if age_hours > max_age_h and abs(pnl) < STALENESS_PNL_LIMIT:
    return False  # Hidden!
```

- Crypto: >72h old with |PnL|<1% = HIDDEN
- Non-crypto: >336h old with |PnL|<1% = HIDDEN

**Issue:** A pick that's been open for 3 days with small PnL (e.g., 0.5%) will be hidden, even if it's a valid active pick.

---

### 7. **Super Pick Score Cap**

**Location:** Lines 2129-2144

Scores >100 are **capped to 100** unless ALL conditions met:
- trust >= 6
- confidence 0.65-0.85
- strat_fwd_wr >= 55% with 15+ trades

**Issue:** High-scoring picks (e.g., 120) from exceptional edge cases may be suppressed.

---

### 8. **Historical Context: UNTRUSTED Pick Leak**

**From AGENT_BUS.md Section 14:**
> "7 UNTRUSTED picks from kimi_riseoftheclaw were leaking through with score=120 (2026-04-04)"

This was fixed by adding UNTRUSTED to `BLOCKED_ACTIVE_TRUST_TIERS` (line 366).

---

## Recommendations

### Immediate Actions

1. **Clarify "Show All Picks" Intent**
   - If "Show All" means bypass ALL quality gates, implement a true bypass in `passes_active_gate()`
   - If "Show All" only bypasses trust filters, document this clearly

2. **Audit Staleness Filter**
   - Consider extending 72h crypto limit to 96h for low-volatility picks
   - Ensure PnL calculation is accurate before filtering

3. **Review Copytrader Exemptions**
   - Ensure `multi_asset_copytrader` exemption applies correctly
   - Verify copytrader picks are appearing in dashboard

### Code Quality Improvements

4. **Add Debug Logging**
   - Log which specific filter rejected each pick
   - Add counter metrics for rejection reasons

5. **Document Filter Hierarchy**
   - Create visual flowchart of filtering pipeline
   - Document which filters apply in which mode

6. **Separate Score Calculation from Filtering**
   - Consider moving `_apply_score_penalties()` outside of `passes_active_gate()`
   - Make score modification explicit, not side-effect

---

## Dashboard Generation Flow

```
1. dashboard_generator.py collects all picks from 30+ sources
2. passes_active_gate() filters each pick (applies penalties inline)
3. filtered picks go to payload["picks"]["active"]
4. passes_smart_gate() selects from active for smart_picks
5. Frontend displays based on _showAllPicks toggle
   - false: uses active (already filtered by backend)
   - true: uses active_raw (full pool)
```

**Key Insight:** The "Show All Picks" toggle only affects **which data array** the frontend uses, not the backend filtering.

---

## Files Involved

| File | Purpose |
|------|---------|
| `audit_trail/quality_gates.py` | Backend filtering logic (passes_active_gate, passes_smart_gate) |
| `audit_dashboard/template.html` | Frontend display logic, _showAllPicks toggle |
| `audit_trail/dashboard_generator.py` | Payload generation, orchestrates filtering |
| `alpha_engine/data/active_picks.json` | Source of active picks |

---

## Conclusion

The filtering system is **functionally correct but complex**. The main potential issue is the **mismatch between user expectations** ("Show All" means show everything) **and actual behavior** (backend gates still apply). 

The staleness filter (72h crypto) and super-pick cap (>100 scores) are the most likely sources of "missing" picks that users expect to see.

**Status:** No critical bugs found, but UX could be improved by clarifying filter behavior or adding a true "raw view" mode.

---

*Broadcast via Redis Bus: antigrav-filter-audit*
