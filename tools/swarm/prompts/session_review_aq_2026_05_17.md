# Session AQ — Swarm Review Request
# Date: 2026-05-17
# Session: AQ (following AP — APPROVE)

## Context

Session AQ: deep dive into QUALITY_GATE shadow tracker kills. Investigated why three
technical pattern strategies (cyclic_momentum_stack, stochrsi_oversold_bounce, sr_breakout_retest)
have poor QUALITY_GATE save rates. No code changes this session — diagnostic only.

## Session AQ Findings

### 1. QUALITY_GATE Root Cause: Negative elite_scores

All QUALITY_GATE blocks for these strategies share a common root cause:
**elite_score is systematically negative** (ranging -22.2 to +1.8), far below the
QUALITY_GATE threshold of 30.

| Strategy | n_blocked | killed | saved | save_rate | avg_pnl_killed | elite_score range |
|----------|-----------|--------|-------|-----------|----------------|-------------------|
| cyclic_momentum_stack | 12 | 7 | 4 | 33.3% | +15.03% | always -8.2 |
| stochrsi_oversold_bounce | 19 | 12 | 5 | 26.3% | +5.54% | -22.2 to -5.2 |
| sr_breakout_retest | 16 | 9 | 7 | 43.8% | +1.39% | -11.2 to +1.8 |
| fractal_sr_bounce | 10 | 7 | 3 | 30.0% | +3.46% | -11.2 to +1.8 |

**Key observations:**

1. `cyclic_momentum_stack` ALWAYS gets elite_score=-8.2 regardless of symbol or confidence.
   This strongly suggests a fixed/sentinel value — elite_scorer may not compute a real score
   for this strategy. avg_killed PnL=+15.03% (APEUSDT +91.24% outlier).

2. `stochrsi_oversold_bounce` has **high ml_scores (0.44-0.71)** but negative elite_scores.
   The ML model sees value; elite_scorer penalizes via source/strategy score.

3. `fractal_sr_bounce` has **VERY high ml_scores (0.83-0.98)** but negative elite_scores.
   This is the strongest disconnect: ML near-certainty (>0.95) blocked by elite_score=-5 to -11.

4. `sr_breakout_retest` has the most balanced save rate (43.8%) and lowest avg_killed_pnl (+1.39%)
   — weakest case for intervention.

5. For comparison: WINNER_FILTER / cross_sectional_reversal had save_rate=0%, avg_killed=+5.88%
   (n=5), which justified M-082. These strategies have save rates 26-44% with n=10-19 — the gate
   IS blocking some real losers here (unlike M-082).

### 2. elite_score vs ml_score Structural Disconnect

The elite_scorer appears to apply heavy source-system penalties to these technical pattern strategies,
suppressing scores into negative territory despite ML signals being positive.

`fractal_sr_bounce` is the clearest case: ml_score 0.825-0.977 (near-certain ML signal) combined
with elite_score -5 to -11 (rejected by QUALITY_GATE at threshold 30).

This suggests the elite_scorer source-score component may be miscalibrated for these strategies.
However, BECAUSE the gate IS saving some losers (not 0% save rate), this is not an emergency.

### 3. Additional Shadow Findings

`super_channel_trend_rider`: blocked by RR_GATE (not QUALITY_GATE). ml_scores 0.71-0.80.
6 KILLED_ALPHA, 2 SAVED, save_rate=25%. This is a separate RR_GATE calibration question.

### 4. What We Did NOT Do (Correct Restraint)

- Did NOT add per-strategy QUALITY_GATE overrides (save rates too mixed — not a clear 0% case)
- Did NOT modify elite_scorer or source system scores (pending investigation, not diagnostic)
- Pending user approvals from Sessions AO/AP still awaiting:
  1. Block `cta_cross_asset_tsmom` for COMMODITY (WR=12.7%, n=71)
  2. Add `CONCENTRATION_CAP_BY_CLASS = {"COMMODITY": 0.85}`

### 5. Recommended Next Steps

1. **Investigate cyclic_momentum_stack elite_score sentinel** — why is it always -8.2?
   Check elite_scorer.py for strategy name lookup + source system score assignment.

2. **fractal_sr_bounce investigation** — ml_score 0.83-0.98 vs elite_score -5 to -11
   is the strongest elite_score/ml_score disconnect seen. Worth a targeted fix if the
   elite_scorer is applying an incorrect penalty.

3. **Monitor forward**: no action until n≥20 per strategy in shadow tracker.

4. **cross_sectional_reversal M-082**: now at n=5 with override. Review at n=20.

## Questions for Swarm

1. **QUALITY_GATE elite_score pattern**: cyclic_momentum_stack always getting -8.2 — is this
   a sentinel ("not computed") or a legitimate floor score? If sentinel, should we block the pick
   rather than apply the default-rejected sentinel?

2. **fractal_sr_bounce ml vs elite disconnect**: With ml_scores 0.83-0.98 but elite_score
   negative, should we add `ml_score >= 0.85` as an elite_score override condition in QUALITY_GATE?
   Or investigate elite_scorer source penalties first?

3. **sr_breakout_retest**: 43.8% save rate, avg_killed=+1.39%. No intervention needed —
   gate is performing close to 50/50, which is acceptable. Agree?

4. **super_channel_trend_rider RR_GATE**: n=8 total, save_rate=25%, ml_scores 0.71-0.80.
   Too small to act on — monitor at n=20?

5. **Overall verdict**: Is Session AQ APPROVE? No code changes made — diagnostic only.

## Verification

- CI: 0 failures
- Shadow tracker: 500 entries analyzed
- Commits: none this session (diagnostic only)
- Prior commits: M-082 (Session AP, commit 197151b881)
