# P1 Safety Fixes: Position Sizing Cut + Confidence Calibration Enable

**Date:** 2026-06-12  
**Author:** Kilo  
**Status:** Ready for review

## Summary

Two safety fixes to reduce risk and fix the scoring inversion:

1. **Position sizes cut 50%** — Reduces risk-per-trade from 2% to 1%, max allocation from 15% to 8%
2. **Confidence calibration enabled** — Remaps raw confidence to realized P(win), fixing the inversion

## Fix 1: Position Sizes Cut 50%

**Files:**
- `alpha_engine/config.py:70-73` — Primary risk knobs
- `alpha_engine/config.py:85` — Kelly cap
- `alpha_engine/per_class_position_caps.py:51` — Universal fallback
- `alpha_engine/per_class_position_caps.py:66-75` — Per-class caps

**Changes:**

| Parameter | Old | New | Impact |
|-----------|-----|-----|--------|
| MAX_RISK_PER_TRADE | 0.02 (2%) | 0.01 (1%) | $100 risk per trade on $10K |
| MAX_ALLOCATION_PER_PICK | 0.15 (15%) | 0.08 (8%) | Max $800 in single pick |
| MAX_TOTAL_EXPOSURE | 0.80 (80%) | 0.50 (50%) | Max $5K deployed |
| MAX_CORRELATED_EXPOSURE | 0.40 (40%) | 0.20 (20%) | Max $2K in same sector |
| KELLY_CAP | 0.05 (5%) | 0.025 (2.5%) | Kelly-sized positions capped |
| UNIVERSAL_POSITION_PCT | 0.05 (5%) | 0.025 (2.5%) | Universal fallback |
| Per-class caps | 2-8% | 1-4% | All halved |

**Rationale:** System has 32.3% WR (worse than coin flip). Cutting position sizes by 50% reduces maximum loss by 50% while preserving edge on winning strategies.

## Fix 2: Confidence Calibration Enabled

**File:** `alpha_engine/confidence_calibrator.py:81`

**Problem:** Confidence measures signal extremity, not probability of success. High confidence (≥0.90) has 14.4% WR while moderate confidence (0.50-0.60) has 60.3% WR.

**Fix:** Changed default from `"0"` to `"1"` in `_enabled()` function. The isotonic regression calibrator remaps raw confidence to realized P(win), inherently correcting the inversion.

**How it works:**
1. Fit phase: Maps raw confidence → realized win rate using isotonic regression
2. Apply phase: Replaces raw confidence with calibrated P(win)
3. Result: High confidence now means high probability of success

**Known limitations:**
- Training data may have resolver noise (63-67% of FOREX/COMMODITY "wins" are 1bp resolver flicker)
- Calibrators are stale the moment they're fit (need daily re-fit)
- CRYPTO inversion is plausibly real; FOREX/COMMODITY/EQUITY calibrators partially regressing on resolver noise

## Verification

- All three modified Python files pass syntax check
- Position sizing changes are config-only (no logic changes)
- Confidence calibration was already wired but disabled (default-off)

## Rollback

1. Revert position sizes to original values in config.py and per_class_position_caps.py
2. Change confidence_calibrator.py default back to `"0"`
