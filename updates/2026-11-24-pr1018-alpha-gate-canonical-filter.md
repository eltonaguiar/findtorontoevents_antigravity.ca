# 2026-11-24 — PR #1018: alpha-gate scope + canonical row filter

## What was broken (CI job "test (3.11/3.12)")
Eight failures, three root causes:

1. `ALPHA_PASSTHROUGH_KEYS` did not include `by_class`, `by_slice`,
   `bar_coverage`, `missing`, so per-class alpha was computed and then never
   published (`tests/test_selection_alpha_coverage.py`).
2. `apply_selection_alpha_gate` returned `None` (so `summary["demoted"]`
   crashed), ignored strategy-scope alpha, and never recorded `scope`/`status`.
   Consequence: a cell proven only by *class* alpha stayed PROVEN_T2
   (`tests/test_audit3_g8_defaults.py`, `tests/test_audit3_falsifiers.py`).
3. `load_rows` used a 3-value status deny-list and never called the canonical
   `resolved_closed_view.is_performance_scored_row`, so the tribunal admitted
   cancelled/manual/stale/null-exit rows the canonical view drops
   (`tests/test_performance_scored_row.py`).

## What changed
- `ALPHA_PASSTHROUGH_KEYS` += `by_class`, `by_slice`, `bar_coverage`, `missing`.
- `apply_selection_alpha_gate`:
  - uses `by_strategy["<CLASS>/<strategy>/<DIR>"]` as same-scope evidence;
  - class/slice alpha is `scope="class_proxy"` and can NOT prove a strategy
    cell (demote PROVEN_T2 -> CANDIDATE, `beta_dominant=True`);
  - records `alpha_gate = {alpha_ci_lo, passed, scope, status}`
    (`proven` / `unproven` / `unmeasured`);
  - returns `{"demoted": n, "n_cells": m}`.
- `load_rows` now calls `is_performance_scored_row(row)` and counts drops as
  `not_performance_scored`.

## Verified
- `pytest` on the 5 affected files: 42 passed.
- Regression sweep (`-k "audit3 or selection_alpha or performance_scored or
  surface_parity or resolved_closed or g8 or falsifier ..."`): **209 passed,
  6 skipped, 0 failed**.
