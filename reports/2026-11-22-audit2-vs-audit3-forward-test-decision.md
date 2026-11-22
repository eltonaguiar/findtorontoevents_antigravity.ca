# audit2 vs audit3 — which surface actually proves a backtest in forward testing

**Date:** 2026-11-22
**Question:** if we backtest a strategy with no forward-looking and then paper-trade it, which
of `findtorontoevents.ca/audit2` and `findtorontoevents.ca/audit3` is the right place for that
proof to land?
**Decision: `/audit3`. `/audit2` is a registration manifest and a view, not a decision surface.**

## Why audit3, in code rather than in prose

1. **audit3 owns the only enforced promotion rule.** `alpha_engine/audit3_tribunal.py`
   `forward_gate_block(manifest, ledger)` reads `reports/forward_observations.jsonl` and
   evaluates each pre-registered pod against pre-declared thresholds: rows closed **on or
   after** the pod's `registered_at`, `n >= FO.PROMOTION_MIN_N`, net PF confidence-lower-bound
   `> FO.PROMOTION_PF_CI_LB` **or** `IR >= FO.PROMOTION_IR`, honest intrabar first-touch on
   100%, and benchmark coverage `>= FO.BENCHMARK_COVERAGE_MIN`. That is precisely the
   "repeat the backtest without forward-looking" test: a pod judged on rows that predate its
   registration is rejected by construction.
2. **audit2 cannot promote anything, by its own documentation.** `audit_dashboard/data/audit2_pods.json`
   carries the note *"Not evidence-grade; audit3 is the decision surface."* `audit2.html` states
   *"Every live number on this page comes from `audit3_ledger.json`"* — so audit2 renders
   audit3's ledger. A view cannot be the authority for the thing it displays.
3. **audit2's forward clock is currently non-discriminating.** `audit2_forward.json`
   `by_hypothesis` has exactly one entry, `H-119` with `n=430`, `benchmark_leg=343`,
   `pods: []`. No pod in `audit2_pods.json` has a forward row. The only populated row is
   doubly ineligible in the ledger (`net PF CI-LB 0.9213 <= 1.0`, benchmark coverage
   343/430 = 79.8% < 90%). audit2's table renders that as a clock near "ready".
4. **audit3 carries the plumbing that keeps a proof fresh.** `audit3-ledger.yml`,
   `audit3-health.yml`, `audit3-evidence.yml`, `audit3-denylist-watchdog.yml` regenerate the
   ledger, and `alpha_engine/audit3_denylist.py` blocks re-emission of rules already known
   dead. audit2 has no producer of its own.

## The honest counter-case (and why it does not flip the decision)

audit3's positive side is empty: `summary.n_proven = 0`, `n_candidate = 0` at cell, symbol and
class level. Its KILL/WEAK verdicts are computed on legacy picks whose TP/SL are hardcoded
fixed percentages (`docs/AUDIT_SURFACE_CONSOLIDATION_PLAN_2026-11-20.md`, P0-1: EQUITY 59/59 at
exactly 4.5%, ETF 47/47 at 3.0%), so a KILL there measures stop geometry as much as signal
quality. audit3 is a **good gate reading bad inputs** — which is an argument for feeding it
better rows, not for promoting from audit2 instead.

## Resulting architecture (each stage has one owner)

| Stage | Owner | Artifact |
|---|---|---|
| Hypothesis registration, frozen before any run | `reports/hypothesis_registry.json` (rule M-107) | H-149, H-150 entries |
| Signal validation (does the accounting mean what we think) | `tools/h150_ttm_gpa.py` | `reports/h150_ttm_validation*.json` |
| Backtest verdict (no forward-looking) | `tools/h150_gpa_backtest.py` under **unmodified** `tools/edge_stability_harness.py` + FF4 alpha t | `reports/h150_gpa_backtest_2026-11-22.json` |
| Forward proof (paper book, forward rows only) | `/audit3` `forward_gate_block` | `reports/forward_observations.jsonl` → `audit_dashboard/data/audit3_ledger.json` |
| Display of the clock | `/audit2` | `audit2_forward.json`, `audit2_pods.json` |

The pod record in `audit_dashboard/data/audit2_pods.json` (status `pre_registered`, a
`hypothesis_id`, a `registered_at` timestamp) is an **input** to audit3's gate, not a
substitute for it.

## What must be true before an H-150 forward row can pass

- `hypothesis_id` exactly `H-150` (the gate upper-cases and exact-matches).
- `closed_at >= registered_at` — rows closed before registration are discarded by the gate.
- `benchmark_leg_ret` populated on every row, else coverage falls below 90% and the pod is
  ineligible regardless of P&L (this is what sank H-119).
- `n >= 100` closed forward rows.
- `intrabar_first_touch` honest; a monthly formation has no intrabar ambiguity, so it must be
  derived from the resolver, not asserted.

## Do not do

- Do not promote from `/audit` or `/audit2` dashboards: neither holds a gate.
- Do not tune H-150's book, exit window or cap band after seeing the backtest; the registry
  declares those frozen and a change requires a new hypothesis id.
