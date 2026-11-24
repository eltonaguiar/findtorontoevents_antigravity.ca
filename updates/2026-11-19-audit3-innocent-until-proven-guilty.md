# audit3 — innocent until proven guilty (2026-11-19)

## What was broken

`alpha_engine/audit3_tribunal.py` killed a cell on **either** of two conditions:

```python
if expect_ci_negative or (pf is not None and pf < 0.8 and n >= KILL_PF_N):
```

The second clause is not evidence of harm. With `n = 50` and a low profit factor
you can still have a net-expectancy confidence interval that straddles zero — a
noisy cell, not a losing one. On the first live run this killed **12 strategy
cells and 13 symbol cells**, and the page presented them as a kill list. That is
guilt by failure-to-prove: exactly backwards for a research ledger whose most
valuable finding is usually a small sub-population (one asset class inside a
section that looks bad in aggregate).

## What changed

1. **KILL now requires affirmative evidence.** Verdict is `KILL` only when the
   bootstrap 95% CI of net expectancy is entirely below zero. That negative
   result must then survive Benjamini–Hochberg across all killed cells
   (`apply_harm_gate`, q ≤ 0.10). A negative-but-noisy cell is demoted to `WEAK`
   with an explicit reason.
2. **PF < 0.80 at n ≥ 50 is a watch flag**, never a kill. It adds a reason
   string (`watch only, harm not proven`) and leaves the verdict at `WEAK`.
3. **`WEAK` is redefined in the docs and UI** as "no claim yet — keep observing",
   the default state of every cell. `INSUFFICIENT_N` remains "no claim".
4. **New `segments` matrix** (section gate × value × asset class), reconstructed
   from fields already on each closed row — `trust_tier`, `grade`,
   `elite_grade`, `score ≥ 60`, `rr_ratio ≥ 1.5`, paper flag, `is_ac_survivor`,
   `strat_fwd_trades ≥ 20`. Every segment cell is stamped
   `reconstructed: true` because the generator does not put the live section
   name on closed rows; the matrix is a proxy, and says so.
5. **New sums** in the ledger summary: `n_segment_cells`,
   `n_proven_segments`, `n_harmful_segments`, `n_positive_segments`,
   `n_kill_classes`, plus a `doctrine` block the page renders in Method & Limits.
6. Page: new **Sections × Class** tab, legend explaining the doctrine, KPI
   renamed `Killed` → `Proven harmful`, tribunal subtitle now states the BH harm
   requirement.

Nothing is deleted from the closed-pick ledger. A cell that is merely unproven
stays visible, filterable and re-testable on the next run.

## Verification

- `python3 -m pytest tests/test_audit3_tribunal.py -q` → **16 passed**.
  New tests:
  - `test_low_pf_without_significant_harm_is_not_killed` — PF ≈ 0.70, CI
    contains zero, verdict must be `WEAK`.
  - `test_harm_gate_requires_multiplicity_survival` — q=0.9 demotes, q=0.001
    keeps the kill.
  - `test_report_has_section_by_class_matrix` — `segments` exists, is marked
    reconstructed, and the summary count matches.
- `python3 -c "import py_compile; ..."` → ok.
- Page script extracted and `node --check` → ok.
- Ledger rebuilt from the live 26 MB snapshot and strict-JSON validated
  (`allow_nan=False`), then deployed by `audit3-ledger.yml`.

## Files

- `alpha_engine/audit3_tribunal.py` — doctrine, harm gate, segment matrix.
- `audit_dashboard/audit3.html` — Sections × Class tab, labels, legend.
- `tests/test_audit3_tribunal.py` — three new deterministic tests.
- `audit_dashboard/data/audit3_ledger.json` — regenerated with the new schema.

## Note on scope

This change is deliberately conservative: it makes the tribunal *less* likely to
discard something. It does not add new data sources — those are scheduled in
`docs/plans/2026-11-19-audit3-v2-evidence-and-success-metric-plan.md`.
