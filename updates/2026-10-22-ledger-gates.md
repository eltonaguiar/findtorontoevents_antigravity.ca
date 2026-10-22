# Ledger-Level Gate Evaluator — `ledger_gates.compute_ledger_gates`

**Date:** 2026-10-22
**Task:** 4 (Sub-project 1) — Ledger-Level Gate Evaluator
**Module:** [`audit_trail/ledger_gates.py`](../audit_trail/ledger_gates.py)
**Tests:** [`tests/test_ledger_gates.py`](../tests/test_ledger_gates.py)
**Wiring:** [`audit_trail/dashboard_generator.py`](../audit_trail/dashboard_generator.py) → `generate()`

## What this adds

A new standalone module that evaluates the **4 quick-fix ledger gates** per
`(strategy, asset_class)` ledger. It is the authoritative gate evaluator for the
ledger-level quick-fix gates:

| Gate | Code | Threshold |
|------|------|-----------|
| Sample size | `n<100` | `n >= 100` |
| Net profit factor | `pf<1.5` | `PF_net >= 1.5` |
| PF lower CI bound | `pf_ci_lb<1.2` | `pf_ci_lower >= 1.2` |
| Drawdown | `mdd>20` | `MDD <= 20%` |

Verdicts are machine-readable strings: `"OK"` or `"UNVERIFIED"`.

## The two-stage architecture (Stage C before Stage B)

In `generate()`, the measurement-hygiene block (`MEASUREMENT_HYGIENE_V1`) runs a
strictly ordered pipeline:

1. **Stage C — net-of-cost + overlap-aware must run first.**
   `stamp_net_of_cost()` stamps `net_of_cost_pnl_pct` on every resolved row, and
   the overlap-aware compounding (Task 3) builds the equity curve. The ledger
   gates **consume** these quantities.
2. **Stage B — ledger gates.** `compute_ledger_gates(resolved_closed)` groups the
   rows and evaluates the four gates.
3. **Stage D — benchmarks.** `attach_benchmark_column()` merges the Task 10
   sidecar.

The wiring enforces this with a **mandatory ordering assert**:

```python
assert "net_of_cost_pnl_pct" in str(resolved_closed[:5]) or all(
    "net_of_cost_pnl_pct" in (p or {}) for p in resolved_closed[:5]
), "Stage C (net-of-cost) must precede Stage B (ledger gates)"
```

If Stage C is ever reordered after Stage B, the assert raises — the gates would
silently consume gross PnL and produce wrong verdicts.

## Why `n >= 100` cannot live in `_is_valid_resolved_pick`

`_is_valid_resolved_pick(pick)` is a **per-pick predicate**: it inspects a single
row and returns bool. The `n >= 100` gate is a **ledger-level property** — it
requires knowing how many sibling trades share the same `(strategy, asset_class)`
ledger. A per-pick function cannot know sibling-trade counts, so placing the gate
there would either be impossible (no ledger context) or silently skip ledgers.

The ledger gates therefore belong in `compute_ledger_gates()`, which groups rows
first and evaluates the four gates against the whole ledger.

## Key design decisions

- **`_mk` test fixture honors `pf`.** The original spec helper produced a fixed
  PF (~1.28 / ~0.94) regardless of the `pf=` argument, which would have broken
  `test_compute_ledger_gates_all_pass`. The rewritten helper tunes loss amplitude
  to hit the requested PF: `loss_amp = (n_wins * win_amp) / (pf * n_losses)`.
- **MDD uses an *uncapped* overlap-aware curve.** The ±10% cap applies to the
  headline compound-return metric (Task 3), not to risk measurement. A capped
  curve hides deep drawdowns (fixture: 19.7% capped vs 60.7% uncapped). The MDD
  gate therefore computes on the uncapped share-weighted equity curve.
- **Cluster bootstrap CI** uses `tools.pf_ci_lower.pf_ci_lower` with the verified
  key `pf_ci_lower` (not `ci_low`), clusters keyed `symbol|UTC-day`, seed 42,
  `n_boot=2000`, `alpha=0.05`.
- **Fail-soft.** Degenerate inputs (missing symbol/day, non-dict rows, no PnL)
  never raise; gates simply report `UNVERIFIED` with the relevant code.
- **Legacy rename.** The pre-existing module-level `compute_ledger_gates` in
  `dashboard_generator.py` was renamed `_compute_ledger_gates_legacy` to avoid
  collision with the new imported function.

## Verification

- RED: all 7 tests failed with `ModuleNotFoundError` before the module existed.
- GREEN: all 7 tests pass.
- Regression: 29 passed across `test_ledger_gates.py`,
  `test_dashboard_generator_net_pf_wireup.py`,
  `test_compound_overlap_aware.py`,
  `test_dashboard_generator_measurement_hygiene.py`.
- `dashboard_generator.py` compiles and imports; `has_builder=True`,
  `has_legacy=True`, no module-level name collision.
