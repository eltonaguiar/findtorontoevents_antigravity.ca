# Swarm consult: ml_crypto_pred LONG-inversion implementation approach

## Context

Per CRYPTO swarm round 2026-05-13 (deepseek breakthrough finding):
> "ml_crypto_pred has 85.7% SHORT WR vs 12% LONG WR — inverting LONG signals alone could lift PF from 1.25 to ~1.55, making it the single highest-impact change."

AA-1 autopsy data (n=40 resolved sub-strategy):
- LONG: 3W/22L → 12.0% WR
- SHORT: 6W/1L → 85.7% WR

Existing handling in `alpha_engine/elite_scorer.py:2362-2367`:
```python
elif _source == "ml_crypto_pred" and _direction_for_source in ("BUY", "LONG"):
    _source_adj = -5  # 31.3% WR LONG (n=112), -0.44% avg PnL
    # BEAR regime: total -11
```

This is a SCORE penalty, not a reject. The strategy still emits LONG picks that may pass the score threshold.

## Three candidate implementations

**Option A — Hard REJECT LONG in passes_active_gate**
```python
# audit_trail/quality_gates.py
if str(source_system).lower() == "ml_crypto_pred" and str(direction).upper() in ("LONG","BUY"):
    pick["_hf_quality_gate_reason"] = "ns_d_ml_crypto_pred_long_reject"
    return False
```
- Simple, reversible
- Loses 25-30% of strategy's volume (LONG side)
- Aligned with existing NS-C/FX1 surgical reject pattern

**Option B — Strengthen score penalty to effective-reject (-30)**
```python
elif _source == "ml_crypto_pred" and _direction_for_source in ("BUY", "LONG"):
    _source_adj = -30  # was -5; effectively un-score
```
- Less invasive (no new gate)
- Soft floor — extremely high-score LONG picks could still surface
- Existing code lives in elite_scorer, not exec gate (memory `feedback_gate_at_execution_not_generation` warns about this)

**Option C — Direction INVERT (transform LONG → SHORT)**
- Most aggressive, claimed by deepseek as "highest-impact"
- Architecturally complex: needs to flip direction + recompute TP/SL + recompute entry strategy
- Risk: if SHORT-WR 85.7% reflects regime luck (n=7), inverting amplifies tail risk
- NOT recommended for first iteration

## Question to engines

Pick the safest path that captures most of the projected PF 1.25→1.55 lift. Return strict JSON ONLY:

```json
{
  "recommended_option": "A | B | C",
  "rationale": "<1-2 sentences>",
  "expected_pf_lift": <0-0.3 range>,
  "rollback_complexity": "<one_line | multi_step | hard>",
  "production_safety": "<safe | risky | needs_shadow_mode_first>",
  "additional_safeguards": ["<list>"],
  "ship_now_or_shadow_first": "SHIP_NOW | SHADOW_MODE_7D_FIRST"
}
```

## Constraints

- Reversibility matters: prefer easy revert
- Memory `feedback_gate_at_execution_not_generation`: gates must fire at exec, not just generation
- Memory `aa1_ml_crypto_pred_autopsy_20260513`: SHORT WR 85.7% is on n=7 — small sample, may not generalize
- Hard reject (Option A) preserves SHORT signals (the working side) which is critical
