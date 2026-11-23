# 2026-11-23 — σ adjudication, and a retraction of a number I published

## What was asked

`proceed` — continue the open work after the DSR/cost/ETF round.

## What this round did

Wrote `reports/dsr_sigma_adjudication_2026-11-23.md`, answering the question
`reports/TRIAL_N_RECONCILIATION_2026-11-23.md` §7 left open (SR\* 1.259 vs 1.6176 at the same N).

## The retraction first

I published a COMS note stating the SE-of-SR basis for H-242 was **0.07195**. That is **wrong**. The
correct value, recomputed from the same inputs, is **0.020089**:

```
SE(SR_daily) = sqrt((1 − skew·SR + (kurt−1)/4·SR²)/T) = sqrt(1.00723/2514) = 0.020089
```

It was a mis-transcription, not a different estimator, and it matters because it changes the finding:
the two bases are **0.022798 vs 0.020089 — 13% apart, not 3.6×**. The HTML/JS panel carried no SE
figure, so no published page was wrong; only the COMS note was, and it is corrected on the bus.

## The adjudication

- **Cross-trial σ (canonical `Var(SR)`) = 0.022798. SE of one estimate = 0.020089. Ratio 0.88.**
- Independent zero-skill trials would make that ratio ≈ 1. It is 0.88 — consistent with
  near-independent trials of mildly differing lengths, and 5× away from what heavy cross-trial
  correlation would produce.
- **Therefore the "~25 effective independent trials" estimate is not supported by the trial scatter.**
  For 25 effective out of ~120 declared, the cross-sectional SD would need to be ≈0.0092; the observed
  0.0228 is 2.5× larger. If you want N_eff = 25, the shrunk dispersion has to be shown, and it isn't.
- Do not feed SE into `E[max]` (which is what `alpha_engine.deflated_sharpe` does through
  `sharpe_variance()`): that asks "how surprising is this SR given the noise in one measurement"
  instead of "how surprising is it given the best of N draws". It happens to be more permissive here
  only because 0.0201 < 0.0228 — a coincidence of this cell, not a property of the convention.

## The number that survives every σ choice

Breakeven: to clear 0.95 the hurdle must satisfy `SR0* ≤ 0.03596`, i.e. **N_eff ≈ 12**. The book would
have to be the best of ~11 or fewer effectively-independent trials. DSR at N_eff = 25 is 0.879, at 120
it is 0.688, at 362 it is 0.533 — **every candidate denominator fails**, including the most generous
one. H-242 is unaffected by the σ dispute.

## Limits, stated in the memo

The 0.022798 is a **recovered** scale, back-solved from a published `expected_max_sharpe_daily` rather
than computed from the trial matrix. The matrix (`reports/per_class_edge_series_2026-11-22.csv`) and
`reports/per_class_edge_2026-11-22.json` are **not in this clone**, so the recovery cannot be re-derived
here. If that published figure was itself produced with the SE convention, then 0.022798 is not a
cross-trial σ and the independence conclusion collapses. Two artefacts agreeing to 4 decimals proves
the number is stable, not that it measures what it claims.

## Deploy path — checked, no gap

`audit_dashboard/audit2.html` and `audit2.js` are both in `tools/deploy_audit_files.py` (lines 213-214)
and in the `audit-dashboard.yml` per-site page lists, so yesterday's Graveyard/prereg panel does ship.
No deploy-list change was needed.

## One failing test, flagged not fixed

`tests/test_audit2_per_class_panel.py::test_panel_matches_golden_snapshot` fails with
`CRYPTO.flat: panel 0 != golden 1`. The suite is otherwise **18 passed**.

**Correction to my first draft of this paragraph.** I wrote that the test "reads neither `audit2.html`
nor `audit2.js`". That is false and I checked it: the file reads `audit2.js` **twice** — once slicing
`function renderPerClass` to assert no statistic is computed in the renderer, once asserting the two
empty-state strings. The corrected evidence is narrower but still decisive for this failure:

- the failing assertion is the **golden-snapshot** one, which calls `build_per_class_verdicts(...)` and
  compares to `tests/golden/audit2_per_class_verdicts.json`; it never touches the JS;
- my edits to `audit2.js` were confined to `renderStatic()` and the static arrays above `BENCHMARKS`,
  so the `renderPerClass` slice the test does read is byte-identical;
- the two JS-reading tests are among the **18 that passed**.

So: not caused by this change, and **not diagnosed** — the cause sits in `build_per_class_verdicts`,
`alpha_engine.resolved_closed_view`, or the golden file, all of which belong to another owner. I am not
asserting which. "A human must decide which is right" is literally the assertion's own text.
