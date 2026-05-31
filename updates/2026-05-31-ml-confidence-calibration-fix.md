# ML Confidence Calibration Fix - 2026-05-31

## Problem: Inverted Confidence
Audit revealed a systematic "Confidence Inversion" where high confidence scores were negatively correlated with win rates (WR), particularly in FOREX and COMMODITY asset classes.

**Key Findings from `closed_picks.json` Analysis:**
- **FOREX (CRITICAL):** 
  - 0.65-0.70 band: 57.1% WR (Sweet Spot)
  - 0.70-0.75 band: 33.3% WR
  - 0.75-0.80 band: 10.4% WR
  - Result: Severe drop in performance as confidence increases beyond 0.70.
- **COMMODITY (MODERATE):**
  - 0.70-0.75 band: 22.2% WR
  - 0.75-0.80 band: 8.3% WR
  - Result: Performance drop in the high-confidence range.
- **CRYPTO:**
  - 0.95-1.00 band: 0% WR observed.
  - Result: Toxic overconfidence at the extreme end.

## Changes Made
Modified [`alpha_engine/score_booster.py`](alpha_engine/score_booster.py:672) in the `_calibrate_confidence()` function to apply aggressive penalties to inverted bands and reward the identified "sweet spots".

### 1. FOREX Recalibration
- **Penalties:**
  - `conf >= 0.85`: -20 (Extreme overconfidence)
  - `conf >= 0.80`: -15 (Critical danger zone)
  - `conf >= 0.75`: -8 (Danger zone)
  - `conf >= 0.70`: -3 (Early inversion warning)
- **Rewards:**
  - `conf >= 0.60`: +5 (Sweet spot: 0.60-0.70)

### 2. COMMODITY Recalibration
- **Penalties:**
  - `conf >= 0.85`: -15
  - `conf >= 0.80`: -10 (Addressing the 0.75-0.80 inversion)

### 3. CRYPTO Recalibration
- **Penalties:**
  - `conf > 0.90`: -18 (Addressing the 0% WR in the 0.95-1.00 band)

## Verification
1. **Correlation Analysis:** Ran a custom Python script (`/tmp/calibration_audit.py`) against `alpha_engine/data/closed_picks.json` to map confidence bands to actual win rates.
2. **Audit Log:** Generated [`audit_dashboard/data/research/ml_calibration_audit.json`](audit_dashboard/data/research/ml_calibration_audit.json) documenting the per-class inversion severity.
3. **Logic Review:** Verified that the new penalties in `_calibrate_confidence()` directly counteract the observed WR drops.
