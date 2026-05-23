# Swarm review: NS-D ml_crypto_pred LONG-reject diff

## Context

Following prior swarm consult: 4/4 engines voted Option A (hard REJECT LONG in passes_active_gate), expected PF lift 0.22 (0.25/0.25/0.25/0.14).

Branch `fix/ns-d-ml-crypto-pred-long-reject-2026-05-13` implements Option A.

## Diff

`audit_trail/quality_gates.py` (inserted after NS-C, before NS-E):

```python
# NS-D: ml_crypto_pred LONG-side reject. Per AA-1 autopsy 2026-05-13:
# LONG sub-strategy = 3W/22L = 12.0% WR; SHORT sub-strategy = 6W/1L =
# 85.7% WR (n=7, thin). 4/4-engine swarm consensus 2026-05-13: Option A
# (hard REJECT LONG) preserves the working SHORT side and is one-line
# reversible. Expected PF lift: ~0.22 (system 1.25 -> ~1.55 projected).
if _truthy(os.environ.get("ML_CRYPTO_PRED_LONG_REJECT"), "1"):
    _src_lower = str(pick.get("source_system", "") or "").lower()
    if _src_lower in ("ml_crypto_pred", "ml_crypto_predictor"):
        _dir_upper = str(
            pick.get("direction") or pick.get("signal_type") or ""
        ).upper()
        if _dir_upper in ("LONG", "BUY"):
            pick["_hf_quality_gate_reason"] = "ns_d_ml_crypto_pred_long_reject"
            logger.debug(
                "Pick rejected: ml_crypto_pred LONG (NS-D filter — "
                "12%% WR vs 85.7%% SHORT per AA-1 autopsy)"
            )
            return False
```

Plus 10 unit tests in `tests/test_ns_d_ml_crypto_pred_long_reject.py`. **17/17 tests pass** (10 new + 7 regression on NS-C/FX1).

## Properties

- Both source-name variants caught: `ml_crypto_pred` AND `ml_crypto_predictor`
- Both direction variants caught: `LONG` AND `BUY`
- Reads `direction` OR fallback `signal_type` field
- Env-gated `ML_CRYPTO_PRED_LONG_REJECT` (default `1` = ON)
- Sets `_hf_quality_gate_reason` for audit trail
- Placed after NS-C, before NS-E (same hierarchical pattern)
- Preserves SHORT/SELL signals (the 85.7% WR working side)

## Question to engines

Final approval before merge. Return strict JSON ONLY:

```json
{
  "verdict": "APPROVE | APPROVE_WITH_CAVEATS | REQUEST_CHANGES | REJECT",
  "merge_decision": "MERGE | HOLD | REJECT",
  "code_quality_score": <1-10>,
  "concerns": ["<list>"],
  "missing_edge_cases": ["<list>"],
  "default_on_or_off_check": "<correct | should_default_off | needs_shadow_first>"
}
```

## Constraints

- Reversibility: one-line revert (set env to 0 or delete the if block)
- Default ON because reject side has 12% WR — keeping it active is the bleed
- Memory `feedback_gate_at_execution_not_generation`: this lives at exec-time per spec
- AA-1 SHORT data thin (n=7) — but filter REJECTS LONG, doesn't take SHORT signals as truth
