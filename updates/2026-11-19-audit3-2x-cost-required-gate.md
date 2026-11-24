# audit3 — the 2×-cost stress is now a required gate (2026-11-19)

**Reviewer/author:** Kilo (worktree `universal-pisces`, branch `review-financial-prediction-strategies`)
**Scope:** `alpha_engine/audit3_tribunal.py`, `tests/test_audit3_expectancy_gates.py`
**Source:** audit3 next-gen review (`antigravity_review_Nov192026` §12, E5)

## What was broken

`evaluate_cell` computed the 2×-cost stress CI (`net_ci_pct_2x`, `stress_2x_ok`)
and displayed it, but the docstring and code treated it as **report-only**:

> "Report only — it never changes a verdict, it shows how much of an edge is a cost assumption."

Consequence: a cell whose edge exists only because a single flat per-class
slippage constant is assumed could still reach `PROVEN_T2` or `CANDIDATE`. The
repo's own surface review had already flagged that ETF intraday slippage is
234% of per-trade PnL — i.e. the cost assumption is exactly where edges die.

## What changed

1. `PROVEN_T2` now additionally requires `boot_2x["ci_lo"] > 0` — the net
   expectancy CI must exclude zero at **twice** the class slippage.
2. `CANDIDATE` now carries the same requirement.
3. A cell that is otherwise promotable but fails the 2× stress is demoted to
   `WEAK` with the explicit reason `"fails 2x-cost stress gate (net CI at 2x
   slippage crosses zero)"`, so the demotion is visible rather than silent.
4. The stale "report only" comment was corrected.

## Verification

- `tests/test_audit3_expectancy_gates.py::test_cost_stress_2x_is_a_required_gate`
  (new) pins both directions: a thin edge (3.0/−0.6 payoff, net +0.45%) is
  demoted to `WEAK` with the stress reason, while a cost-robust edge
  (4.0/−0.6) still reaches `PROVEN_T2` in a pre-registered pod.
- The existing expectancy-primary promotion test was re-pointed at the
  cost-robust payoff so it continues to prove the WR→expectancy replacement.
- `pytest tests/test_audit3_tribunal.py tests/test_audit3_expectancy_gates.py
  tests/test_audit3_cost_basis.py` → **27 passed**.
- Full audit3 suite: `2 failed, 72 passed`. The two failures
  (`test_audit3_edge_hunt.py::test_net_pnl_applies_per_class_slippage`,
  `::test_mirror_pairs_need_both_directions_same_day`) are **pre-existing
  test-order pollution** — identical on the unmodified base (`2 failed, 71
  passed`), and both pass in isolation. Not caused by this change.

## Effect on live verdicts

The gate can only **demote**, never promote. On the current ledger the only
positive cells are thin (the single CANDIDATE is a single-source 98% discovery
cell), so the expected live effect is: no new PROVEN, and any cell whose edge
is a cost assumption is visibly demoted to WEAK rather than promoted.

## Live rebuild verification (2026-11-19, payload fetched from the live site)

Rebuilt the ledger from the live `dashboard_data.json` (16,341 closed picks,
3,500 scored) with the new gates and diffed against the committed ledger:

- **0 cell verdicts changed.** The one CANDIDATE (`luxalgo_confluence` SHORT,
  n=476, net +0.688%/trade) **passes** the 2× gate (2× CI [+0.280, +0.896]),
  so it correctly stays CANDIDATE. The gate can only demote; today it demotes
  nothing because no promotable cell is a cost artefact.
- Two verdict differences (a FOREX `rr_gate` segment KILL→WEAK, a FOREX AUDJPY
  symbol WEAK→CANDIDATE) are **data drift** from 11 additional closed rows in
  the newer payload, not gate effects.
- `n_confirmatory_cells` unchanged at 8: the new `observe` pods correctly do
  not confer confirmatory status.
- The new per-cell power fields are populated: the candidate reports
  `required_n=196` and `mde_pct=0.441` — i.e. it needs ~196 trades to confirm
  its observed effect at 80% power, which is the honest number behind "n>=100".

Also landed with this work: the selection-alpha gate (a confirmatory cell whose
class alpha CI includes zero is demoted to CANDIDATE; no effect while the alpha
sidecar is absent) — see `updates/2026-11-19-observe-pods-fx-mapping-stop-fill.md`
and the commit log.
