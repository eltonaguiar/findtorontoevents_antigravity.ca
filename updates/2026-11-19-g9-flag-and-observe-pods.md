# G9 flagged every cell, and observe pods could never appear

**Date:** 2026-11-19
**Files:** `alpha_engine/audit3_tribunal.py`, `tests/test_audit3_selection_alpha.py`,
`tests/test_audit3_forward_gate.py`

## What was broken

Merging the rescued COMS handoff (PR #934) put the G9 selection-alpha gate on main for the
first time, and the first full regeneration exposed two defects.

1. **`beta_dominant` fired on 179 of 179 cells.** The gate looked up a class's
   direction-adjusted selection alpha and treated "not measured" as "measured and
   non-positive", so every untested / `INSUFFICIENT_N` cell was branded beta-dominant. A
   flag that is always on carries no information and would have told a reader that every
   cell had been shown to be beta-driven, which is false.
2. **`POD-CRYPTO-POSITION` could never appear on /audit3.** `forward_gate_block()` skipped
   every pod whose status was not `pre_registered`, and that pod is deliberately
   `observe`. Its forward clock — the whole point of registering it — was invisible.

## What changed

- `apply_selection_alpha_gate()` now distinguishes three states: alpha proven positive
  (`passed: true`), alpha measured and non-positive (`beta_dominant: true`, PROVEN_T2
  demoted to CANDIDATE), and alpha **unmeasured** (`alpha_gate.status == "unmeasured"`,
  no brand). A PROVEN_T2 with unmeasured alpha still drops to CANDIDATE, with a reason
  that says "unmeasured" rather than claiming beta dominance.
- `forward_gate_block()` now includes `observe` pods with `status`, `eligible: false` and
  `promotion_blocked_by_status`, so the clock renders while promotion stays impossible.
  `declined` / `post_hoc` / `retired` pods remain hidden.

## Verification

```
python3 -m pytest tests/test_audit3_selection_alpha.py tests/test_audit3_forward_gate.py \
                  tests/test_audit3_tribunal.py -q
python3 -m alpha_engine.audit3_tribunal --picks ... --alpha /tmp/sa.json --out /tmp/l.json
# beta_dominant count drops from 179/179 to only the measured-and-negative classes;
# forward_gate.pods now contains POD-CRYPTO-POSITION with eligible=false
```

The ledger committed on main is **not** overwritten from a local run: a local run on the
dashboard payload scored 3,500 rows while the canonical CI run scores 8,605, so replacing
it would shrink coverage. The hourly `audit3-ledger` workflow regenerates and deploys from
the canonical view.
