# Session AK — Swarm Review Request
# Date: 2026-05-17
# Session: AK (following AJ — APPROVE)

## Context

Session AK primary deliverable: Found and fixed M-037 bug where `ml_score=0` was treated as "below floor" instead of "not populated", causing ALL CRYPTO active picks to be blocked from the dashboard (active=0 for CRYPTO).

## Problem Summary

Root cause: M-037 (`CRYPTO ml_score floor`) was introduced to block low-quality CRYPTO picks
(bottom 30% by ml_score have WR=32.5%). The gate comment said:
"picks without ml_score populated are NOT blocked — fill-rate may be partial."

However, CRYPTO sources emit `ml_score=0` (not `ml_score=None`) as their default fill when
the ML pipeline doesn't score them. The gate checked `if _m037_ml is not None` — which is True
for 0 — then compared `0.0 < 0.65 → True → blocked`.

Result: ALL 46 CRYPTO active_picks had ml_score=0, so all were blocked. Dashboard showed
`active: 0` for CRYPTO. Verified locally: signal_validation/SOLUSDT LONG (confidence=0.75,
score=70, ml_score=None) → passes=True; ml_score=0 → was False, now True.

## Changes Made

### 1. `audit_trail/quality_gates.py` (M-037 fix)
```python
# BEFORE (buggy):
if _m037_ml is not None:

# AFTER (fixed):
# Treat ml_score <= 0 as "not populated" — 0.0 is the default fill
# for sources that don't emit ml_score. A probability model never
# outputs exactly 0.0 for a real pick.
if _m037_ml is not None and _m037_ml > 0:
```

### 2. `tests/test_crypto_gates_p0.py` (2 new regression tests)
- `test_zero_ml_score_not_blocked`: ml_score=0 must pass M-037
- `test_zero_float_ml_score_not_blocked`: ml_score=0.0 must pass M-037

Both guard against the bug where default-filled zero was treated as "very low ML score."

## Verification

- `python -m pytest tests/test_crypto_gates_p0.py::TestM037CryptoMlScoreFloor -v` → 9 passed
- SOLUSDT signal_validation LONG, ml_score=0: True (was False)
- Full suite: 4941 passed, 37 skipped, 1 xfailed (0 failures)

## Additional Findings (Not Fixed — Correct Behavior)

1. **CRYPTO active=0 not fully solved**: After M-037 fix, 46/46 CRYPTO active_picks still block.
   Reasons: 20 ml_crypto_predictor LONG (blocked by NS-D correct), 19 BUY direction (M-036), 7 banned symbols.
   The active_picks.json contains ONLY picks from sources now gated out. New picks from good sources
   (signal_validation, baby_strats_forward) will populate on next scan run.

2. **EQUITY T1 confirmed**: PF=2.04, CB-30d WR=59.5% (n=84). Genuine T1 territory.

3. **CRYPTO CB-30d WR=46.1% drag**: Mostly historical rapid_fire (n=207, WR=29%) picks draining
   out. rapid_fire is currently blocked (score=0 < RAPID_FIRE_MIN_SCORE=50). Historical picks
   drag the 30d metric but new picks don't come in.

4. **Dashboard generated with active=0**: The dashboard at 14:21 UTC showed active=0 because at
   that moment the concentration cap was full AND M-037 was buggy. Next cron run after this fix
   should restore active picks.

## Questions for Swarm

1. **Correctness of fix**: Is treating `ml_score <= 0` as "not populated" the right threshold?
   Could `0.0` ever be a legitimate ML score output for a real CRYPTO pick? The model is a
   random forest classifier outputting probability scores (0-1), so 0.0 exactly seems impossible
   in practice, but should we use a small epsilon (e.g., > 0.001) instead of > 0?

2. **Root cause isolation**: The issue is that sources emit `ml_score=0` instead of `ml_score=None`.
   Should we also fix the upstream (scanner/source) to emit None instead of 0? Or is the gate fix
   (fail-open on zero) sufficient?

3. **Test coverage gap**: The existing `test_null_ml_score_not_blocked` tested `ml_score=None` but
   not `ml_score=0`. Is the 2-test addition sufficient, or should we also add a test for very small
   non-zero scores (e.g., `ml_score=0.001`) to verify the epsilon boundary?

4. **Concentration cap status**: With 46 CRYPTO active picks at 10% cap (4-5 picks per symbol max),
   BTCUSDT at 4 is blocked for the 5th pick. Is 10% (lowered from 15% today due to APEUSDT gap-risk)
   the right cap, or is it too aggressive given the current pick pool size?

5. **Overall verdict**: Is Session AK APPROVE?
