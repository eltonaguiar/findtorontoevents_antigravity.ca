# Session AJ — Swarm Review Request
# Date: 2026-05-17
# Session: AJ (following AI v2 — APPROVE)

## Context

Session AJ primary deliverable: fixed 17 CI test failures in the `CI Tests` workflow that have been failing since Session AG lowered `CRYPTO_MAX_CONFIDENCE` from 0.90 to 0.85 (M-035 gate tightening).

## Problem Summary

Root cause: 8 test files used `confidence=0.88` or `confidence=0.87` in their base picks. When M-035 ceiling was 0.90, these picks passed. After Session AG lowered to 0.85, M-035 blocks any CRYPTO pick with confidence > 0.85 — including test fixtures that are testing OTHER gates entirely.

Additional root causes:
1. `test_crypto_gates_p0.py::test_confidence_at_ceiling_passes` — test explicitly checked that 0.90 was "at ceiling" but ceiling is now 0.85
2. `TestM034ConfidenceInversionGate::test_gate_allows_high_conf_super_signals_when_disabled` — M-035 fired before M-034 check
3. `TestForexCopytradeBypas::test_gate_on_still_blocks_other_forex_sources` — FOREX LONG directional gate (M-130) fired before `FOREX_HARD_DISABLE` gate, so `_hf_quality_gate_reason` was never set to `ns_e_forex_hard_disable`
4. `test_ns_d_ml_crypto_pred_long_reject.py::test_ns_d_behavior_long_picks_rejected` — M-035 blocked pick (confidence=0.9) before NS-D gate could set its reason

## Changes Made

### 8 test files updated (8 files, 19 insertions, 15 deletions):

1. **test_crypto_gates_p0.py**: `test_confidence_at_ceiling_passes` — 0.90→0.85; updated docstring
2. **test_wf_verdict_failing_gate.py**: base pick confidence 0.88→0.80
3. **test_wf_verdict_null_block.py**: base pick confidence 0.88→0.80
4. **test_hf_gate_default_on_safety.py**: base pick confidence 0.88→0.80
5. **test_hf_quality_gate_wire.py**: base pick confidence 0.88→0.80
6. **test_stamp_feed_membership.py**: base pick confidence 0.88→0.80
7. **test_quality_gates.py**:
   - base pick 0.88→0.80
   - PM pick (SOLUSDT): 0.87→0.80
   - PM consensus pick: 0.87→0.80
   - TestM034: added `CRYPTO_CONF_OVERFIT_GATE_ENABLED=0` monkeypatch to isolate M-034 from M-035
   - TestForexCopytrade: added `FOREX_DIRECTIONAL_GATE_ENABLED=0` + `FOREX_SESSION_GATE_DISABLED=1` so `FOREX_HARD_DISABLE` fires first and sets reason
8. **test_ns_d_ml_crypto_pred_long_reject.py**: confidence 0.9→0.80

## Verification

Local: `python -m pytest tests/ -q` → **4941 passed, 37 skipped, 1 xfailed** (0 failures)

CI workflow `CI Tests` was failing for the last ~3 runs before this fix (all 3 failing since M-035 tightening in Session AG).

## Questions for swarm

1. **Correctness of base pick changes**: Are 0.80 confidence values appropriate for "a pick that should otherwise pass all gates"? The intent is that the pick shouldn't trigger M-035 so the test can focus on the specific gate under test. Is 0.80 the right reference value?

2. **TestForexCopytrade fix**: Adding `FOREX_DIRECTIONAL_GATE_ENABLED=0` + `FOREX_SESSION_GATE_DISABLED=1` to isolate `FOREX_HARD_DISABLE`. Is there a risk that disabling these gates in the test obscures future gate ordering bugs?

3. **TestM034 fix**: Adding `CRYPTO_CONF_OVERFIT_GATE_ENABLED=0` to allow confidence=0.88 to reach M-034 check. This means the test is using a confidence value that WOULD be blocked in production. Should the test instead lower confidence to 0.80 and remove the M-035 disable?

4. **Completeness**: Any other tests that might break if M-035 ceiling is lowered further (e.g., to 0.80)?

5. **Overall verdict**: Is Session AJ APPROVE?
