# audit2 shows *why* the forward clock cannot promote (2026-11-20)

**Scope:** `tools/audit2_forward_summary.py`,
`tests/test_audit2_forward_summary.py` (new), `audit_dashboard/audit2.js`.

## Why

The ledger's `forward_gate` already computes the exact blocking clause per
hypothesis and pod — e.g. for H-119:

```
reasons: ["net PF CI-LB 0.9213 <= 1.0 and IR 0.043 < 0.5",
          "benchmark_leg_ret coverage 80% < 90%"]
benchmark_coverage 0.798 · pf_ci_lb 0.9213 · ir 0.0429
```

The audit2 page showed only "accruing", so a reader could not tell whether a pod
was close or nowhere near.

## What

- `merge_gate(payload, ledger)` folds `forward_gate.hypotheses` and
  `forward_gate.pods` into `audit2_forward.json`: `eligible`, `reasons`,
  `benchmark_coverage`, `pf_ci_lb`, `ir`, `n_forward`. Pods with **0 rows** get a
  row of their own, since that is the case the page must name.
- `audit2.js` renders the first gate reason in the status column when a verdict
  is present; otherwise it keeps the previous heuristic.

## Verification

- `pytest tests/test_audit2_forward_summary.py -q` → **3 passed** (hypothesis
  fold, no-ledger no-op, pod-level 0-row row).
- Live build: `rows=430 hypotheses=1`; H-119 carries both reasons and
  `benchmark_coverage 0.798`.
- `node --check audit_dashboard/audit2.js` passes.
