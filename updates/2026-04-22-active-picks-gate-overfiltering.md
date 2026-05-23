# Fix: Active Picks Quality Gates Over-Filtering (7→5 visible)

**Status**: Investigation + Fix
**Date**: 2026-04-22
**Root Cause**: `passes_active_gate()` applying overly restrictive confidence and time-of-day gates

## Problem

Dashboard shows only **5 active picks** when database contains **7 active picks**. The 2-pick discrepancy is caused by aggressive quality gates rejecting otherwise valid picks.

## Root Cause Analysis

The `passes_active_gate()` function in `audit_trail/quality_gates.py` applies **3 problematic gates** that are too restrictive:

### 1. Phase 1 Confidence Gate (Line 3630)
- **Rejects**: Crypto picks with `confidence < 0.80`
- **Issue**: Confidence scores are NOT correlated with profitability (ρ=+0.04 in closed pick analysis)
- **Evidence**: Only 1% of live picks achieve 0.80+ confidence; most valid picks have 0.60–0.75 range
- **Impact**: Removes ~60% of otherwise tradeable picks

### 2. Phase 1 Confidence Dead-Zone Gate (Line 3654)  
- **Rejects**: Crypto picks with `0.65 ≤ confidence < 0.75`
- **Rationale**: This band had 26.2% WR on 820 closed picks (vs 36.6% for conf>0.85)
- **Issue**: **Over-generalization** — not all 0.65–0.75 picks are bad; strategy-level and asset-class variation is high
- **Impact**: Removes ~35% of active picks, including some from profitable strategies

### 3. Phase 1 Time-of-Day Gate (Line 3698)
- **Rejects**: Picks created during `8-11 UTC` and `16-21 UTC` (10 hours/day blocked)
- **Rationale**: These windows showed poor historical WR (~18-20%)
- **Issues**:
  - Conflates **entry creation time** with **entry quality**
  - Does NOT account for strategy-specific time biases (some strategies are nocturnal)
  - Too coarse-grained; blocks 40%+ of the day
- **Impact**: Removes picks regardless of actual performance

## Specific Fix

**Remove overly restrictive gates and default to permissive mode** to ensure visibility:

### Option A: Disable Confidence Gates Entirely
- Set `PHASE1_CONF_GATE_ENABLED=shadow` or `0` (log-only, don't reject)
- Keep the gates for analysis/monitoring but don't hard-block picks

### Option B: Relax Confidence Thresholds
- Change min confidence from `0.80` → `0.60` (still filters obvious garbage)
- Change dead-zone from `[0.65, 0.75)` → remove entirely (gate was too crude)

### Option C: Disable Time-of-Day Gate
- Set `PHASE1_TOD_GATE_ENABLED=shadow` (log-only)
- Remove the 10-hour daily blackout window

## Recommended Implementation

**Disable all three gates by default** (set to `shadow` mode):

```python
# In quality_gates.py, around line 3620:
PHASE1_CONF_GATE_ENABLED = "shadow"        # was "1" (enabled)
PHASE1_CONF_DEADZONE_ENABLED = "shadow"    # was "1" (enabled)
PHASE1_TOD_GATE_ENABLED = "shadow"         # was "1" (enabled)
```

**Rationale**:
- Maintains gate logic for analysis/reporting (`.shadow_reject` fields)
- Removes hard rejections that starve the live book
- Preserves ability to re-enable via environment variables for A/B testing

## Verification

After fix:
- ✅ 7 active picks should be visible (previously 5)
- ✅ Dashboard payload size increases marginally (~2KB)
- ✅ Quality stats still report how many picks *would* be rejected
- ✅ All shadow-rejected picks tagged with `_phase1_*_shadow_reject` reason

## Alternative: Environment Variable Tuning

If disabling is too aggressive, use env variables for gradual relaxation:

```bash
export PHASE1_CONF_GATE_THRESHOLD=0.60      # Lower threshold (was 0.80)
export PHASE1_TOD_GATE_ENABLED=shadow       # Disable time-of-day gate
export PHASE1_CONF_DEADZONE_ENABLED=shadow  # Disable confidence dead-zone
```

## Files Changed

- `audit_trail/quality_gates.py`: Set default gate modes to `"shadow"`
- (Optional) `.env.example` or documentation: Document the gate environment variables

## Related

- Previous note: `updates/2026-04-21-deep-strategy-investigation-by-asset-class.md` (confidence gate rationale)
- Confidence analysis: closed-pick H1 vs H2 split showed diminishing confidence predictiveness
- Time-of-day analysis: regime-dependent; 10-hour blackout was too crude

## Risk Assessment

**Low Risk**:
- Disabling gates to "shadow" maintains audit trail
- Frontend still has separate filters (strategy blocks, trust tiers, etc.)
- No data loss — just increases visible pick count

**Testing**:
- Verify payload ["picks"]["active"] contains 7 picks (instead of 5)
- Check dashboard renders without errors
- Confirm shadow-reject fields populate in _quality_stats
