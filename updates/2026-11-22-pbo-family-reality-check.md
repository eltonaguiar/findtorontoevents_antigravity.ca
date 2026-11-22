# Code fix: harness discarded the matrices, and my own SPA threshold was anti-conservative

**Date:** 2026-11-22 · **Owner:** buffy · **Items:** 26, 27 of `plans/2026-11-22-50-action-items.md`

Three changes, one of them a bug in code I wrote in this same session. Recorded because the
second one silently produced a *rejecting* p-value that looked like a finding.

## 1. What was broken

**(a) The harness threw away the data its own statistics were computed from.**
`tools/per_class_edge_harness.py` kept every cell's daily return series in memory
(`ret_series`), used it to build the T×N matrix for PBO, then discarded both. The artifact it
wrote contained only scalars (`pbo_cscv: 0.345`, `boot_ci_lb_bps`, …). Consequences:

- **Item 26** (PBO block-length sensitivity) could not be answered — a sweep needs the matrix,
  not one CSCV result.
- **Item 27** (White's Reality Check) could not be answered *at all*. A family-wide max-statistic
  bootstrap cannot be reconstructed from per-cell summaries; nothing short of re-running the
  40-cell fetch would get it back.

This is the same defect class as the earlier "summary statistics stored, source series dropped"
pattern: it converts a cheap re-analysis into a full re-run, and it prevents anyone auditing
whether the stored scalar is right.

**(b) My first SPA implementation thresholded recentring at zero.** Written in the same session as
`tools/pbo_and_reality_check.py`, the Hansen SPA branch used:

```python
g = np.where(stat_cells > 0, mean, 0.0)      # WRONG
```

Hansen (2005) recentres a cell on its own mean unless the cell is *clearly bad*, i.e. unless its
t-statistic falls below `−sqrt(2·log·log T)`. A cell sitting just below zero is statistically
indistinguishable from the null and must still widen it. Thresholding at 0 excluded every
near-zero cell, narrowing the null and making p **anti-conservative**. Measured effect:

| test | with `t > 0` (wrong) | with `−sqrt(2 log log T)` (correct) |
|---|---|---|
| SPA, common window | 0.3158 | **0.5018** |
| SPA, full-history family | 0.0096 | **0.0152** |

The wrong version reported p = 0.0096 — a 1%-level rejection — where the correct rule reports
0.0152. Both reject, but the wrong one overstated the confidence, and with a slightly different
sample it would have crossed the 0.05 line on its own.

## 2. What changed

**`tools/per_class_edge_harness.py`**
- New args `--series-out` (default `reports/per_class_edge_series_2026-11-22.csv`) and
  `--excess-out` (`..._excess_...csv`).
- `record()` now stores `excess_series[cell_id] = pd.Series(x - b, index=net.index[keep])` next to
  the existing `ret_series`. Excess is against the cell's **own** class benchmark, matching what
  `excess_vs_bench_bps` summarises.
- After the cell loop, both matrices are written as CSV (`float_format="%.10g"`) with columns =
  cell ids on the union date index; NaN is left as NaN (not zeroed) so the choice of imputation
  stays with the analysis, where it can be justified.
- New `series_artifacts` block in the JSON records the paths, the net shape, and which cells have
  no shared time axis (H-222), so a future reader knows why the family is 39 and not 40.

**`tools/pbo_and_reality_check.py`** (new)
- Item 26: PBO sweep over `s_blocks ∈ {8,16,24}` under **both** matrix constructions — the
  harness's `fillna(0)` (to reproduce the frozen scalar) and the common window (the admissible
  number). Reproduction is asserted against `pbo_cscv` from the frozen artifact.
- Item 27: stationary block bootstrap (Politis–Romano, mean block `T^(1/3)`) with White's RC,
  a studentised RC, and Hansen SPA with the correct threshold. Run on the all-cells common window
  **and** on a full-history family (cells present from the first week of the sample), because the
  all-cells intersection only starts in 2021.
- Emits a `verdict` block that records the family-p **range** rather than collapsing it to one
  number, plus an explicit note that neither test covers the 200-round programme's wider search.

**`tests/test_pbo_reality_check_invvol.py`** (new, 11 tests)
- Stationary bootstrap must actually produce blocks (≥75% of steps continue a block at q=20) and
  must be near-i.i.d. at q=1 — this is the property that makes the test robust to serial
  correlation, and a broken generator would silently make RC meaningless.
- **Calibration under the null:** over 40 independent noise matrices, the rejection rate at the
  5% level must be ≤ 15%. A single draw landing at p = 0.2 is normal under a uniform null; a
  *rate* is the thing that can be wrong. (First version of this test asserted `p > 0.20` on one
  seed and failed at exactly 0.20 — the assertion was wrong, not the code; it was replaced with
  the rate check, not loosened.)
- Reality Check can never report a smaller p than the uncorrected p of the winning cell, must not
  reject pure noise, must have power against a t≈7.9 dominant cell, and must be seed-deterministic.
- Inverse-vol sizing keeps exposure ≤ 1.0 and sums to 1 when invested, holds ≤ top_k names, never
  equals equal weight (max deviation > 0.02 — otherwise H-232 would silently re-run H-201),
  actually overweights the low-vol name, and turnover stays within `[0, 2]`.

## 3. How it was verified

| check | command | result |
|---|---|---|
| Harness re-runs after the change | `python3 tools/per_class_edge_harness.py --n-trials 29 --out .../seriesrun...` | `RC=0`, 40 cells, **PBO 0.345 reproduced** |
| Matrix written, correct shape | same run | `5157×39` net + `5157×39` excess |
| New tests | `pytest tests/test_pbo_reality_check_invvol.py -q` | **11 passed** |
| Item 26 + 27 tool | `python3 tools/pbo_and_reality_check.py` | `RC=0`, reproduces 0.345 (|diff| 0.0) |
| Item 15 tool | `python3 tools/xsmom_invvol_variant.py` | `RC=0`, equal-weight leg reproduces the frozen CI-LB **7.246 bp** |

The 7.246 reproduction is the strongest check available here: a completely separate tool, written
for a different question, rebuilds H-201 from cached prices and lands on the same lower bound to
three decimals. It means the paired difference in §3 of the report is measured against the same
H-201 the rest of the programme is scored on.

## 4. Reproduction notes

- Items 26/27 no longer need a fetch: `pbo_and_reality_check.py` reads the two CSVs (18 s, no
  network). Only the harness itself fetches, and it caches to `data/research_cache/`.
- Runtime: harness ≈ 3 min cold (90 symbols), item-15 tool ≈ 79 s (2000-draw null dominates).
- Determinism: all bootstrap seeds are fixed (11 by default; the reality check takes `--seed`
  through its function signature), so every number in the report is reproducible bit-for-bit.
