# Trace — the two cells that pass the G8 alpha gate

**Date:** 2026-11-23 · **Author:** buffy · **Branch:** `buffy/alpha-sweep-audjpy-2026-11-23`
**Question:** where did `vol-contraction-scout` and `vwap-reversion-scout` come from, and is their
positive selection alpha a real measurement?
**Answer:** real emitter names on real picks, arithmetic that legitimately passes the gate — and one
field that must not be published as written, plus a confidence interval whose honest version already
exists in the tree and is not being called.
Paper only, zero capital, not investment advice.

## 1. Provenance — new cells, between 2026-11-20 and 2026-11-22

| copy | generated_at | cells | cells passing the gate |
|---|---|---:|---|
| main tree | 2026-11-20T01:57Z | 362 | **0** |
| `_raw` copies | 2026-11-22T06:35Z | 374 | 2 |
| this branch | 2026-11-23T06:48Z | 367 | 2 |

New cells, not newly-weighted ones: the 2026-11-20 ledger had no passing cell at all, and both appear in
the 2026-11-22 regeneration under one provenance id (`45fe8f10b750e6f3`) with unchanged `n` and
`alpha_ci_lo` in both later copies — one measurement rendered twice, not two measurements agreeing.

Real emitters, not phantoms: `alpha_engine/smart_picks_engine.py:546` and `:1253`,
`tools/forward_tracker.py:70` (a 6 bp/side prior written for `vwap-reversion-scout`),
`tools/edge_filter_engine_v3.py:49`, `tools/monte_carlo_equity_inverse.py:27`. Both are pod
`POD-EQUITY-BREAKOUT`, LONG, one source each (`single_source: true`, `top_source_share: 1.0`).

**Join hazard found while writing this:** the strategy name is not unique. `vol-contraction-scout`
appears in **2 cells** and
`vwap-reversion-scout` in **3**,
across pods and states — one sibling of the first has a net CI of [-2.0055, -0.5535] and a small `n`.
Any join on the `strategy` string silently picks whichever cell is last in the list. Join on the cell
key, never the name.

| cell (gate-passing) | n | wr | PF | net exp/trade | net CI | DSR | required_n |
|---|---:|---:|---:|---:|---|---:|---:|
| vol-contraction-scout | 63 | 44.4% | 1.256 | +0.5458% | [-0.8444, 2.0683] | 0.0118 | 922 |
| vwap-reversion-scout | 27 | 51.8% | 1.4764 | +1.3792% | [-2.9562, 6.0074] | 0.0178 | 295 |

## 2. Why the gate passes and the verdict does not

Two functions, two questions, both answered correctly:

- **Gate:** `need_n = max(ALPHA_MIN_N=20, int(0.5 * cell_n))` → **31** rows for a 63-row cell,
  **20** for a 27-row one. Coverage is 61 and 22 rows
  (96.8% / 81.5%), `alpha_ci_lo` +0.1745 / +0.1760.
- **Verdict:** needs `n >= required_n` (922 / 295) *and* a net-expectancy CI
  above zero. Neither holds, and DSR is 0.0118 / 0.0178 against a 0.95 gate.

The gate is not wrong. But look at what the alpha is measured against:

| cell | pick net | benchmark (hold) | alpha | CI |
|---|---:|---:|---:|---|
| vol-contraction-scout | +0.6980% | **-0.6882%** | +1.3862% | [0.1745, 2.7589] |
| vwap-reversion-scout | +3.3127% | +1.7023% | +1.6104% | [0.176, 3.0172] |

`vol-contraction-scout`'s entire positive alpha is **losing less than a falling benchmark**: picks
returned 0.70% while holding the same names returned -0.69% over a
4.6-day average window. That is short-window beta avoidance in a down tape, not
selection skill — the profile the gate exists to demote, passing only because the benchmark is negative
rather than positive. A defensible **defensive filter**; not evidence of stock-picking alpha.

## 3. Three soundness defects

**(a) `alpha_annualized_pct` is not a return.** The field is
`mean(alpha_i / max(hold_days_i, 0.041667)) × 365` — a mean of per-trade *rates* with a one-hour
hold floor, so a sub-day hold has its alpha divided by 0.0417 and then multiplied by 365. Against the
cell's own numbers `alpha_pct / hold_days_mean` = 0.3014%/day, but the
field reports 2.6562%/day — **8.8×** higher (2.6× on the other cell).
Extrapolated: **970%** and **332%** annualised.
Any surface rendering that advertises a ~10× monthly return from 63 trades. Rename it
(`alpha_rate_pct_per_day`), drop the annualised line, or show it only beside `hold_days_median`
(5.04 days).

**(b) The gate calls the iid bootstrap while the honest one sits unused beside it.** Not a missing
feature: `bootstrap_mean_ci` (`alpha_engine/audit3_tribunal.py:259`) accepts `block=True`, and its
docstring calls that "the honest interval for overlapping positions, and the only one that keeps the G2
edge gate honest". `alpha_for` (`alpha_engine/audit3_selection_alpha.py:332`) calls
`bootstrap_mean_ci(a)` — the default, iid. With 4.6-day holds, 61 rows overlap
in calendar time, so the resample understates variance and the +0.1745 lower bound is
optimistic. **The fix is one argument**; until then read the pass as "not yet refuted".

**(c) One source, negative recency, no forward arm.** `single_source: true` on both; `recent_ok` false
(last-quarter net means -0.75% and
-1.32%), so the positive alpha is carried by older rows. Neither name
has a forward measurement and the runbook's n≥200-post-registration clock has not started.

## 4. Verdict

**Arithmetically correct, statistically fragile.** Best forward-measurement candidates in the estate —
and not evidence of edge:

1. Do not promote, size, or surface them as alpha found. Both fail `required_n`, net-CI and DSR at once;
   the gate is the only test they pass.
2. Fix `alpha_annualized_pct` before any surface shows it — the most misleading number in the ledger.
3. Pass `block=True` in `alpha_for`, re-read both lower bounds; if they survive, each name earns **one**
   pre-registered forward trial, kill rule frozen first (`docs/TRIAL_BUDGET_2026-11-23.md`).
4. Require `vol-contraction-scout` to beat a **positive**-benchmark window before calling its alpha skill;
   otherwise classify it as a defensive filter — legitimate, but a different product.

## 5. Reproduce

```bash
python3 -c "print(max(20,int(0.5*63)), max(20,int(0.5*27)))"         # 31 20
python3 -c "print(1.3862/4.5996, 2.6562, 2.6562*365)"               # 0.3014 2.6562 969.5
grep -n 'bootstrap_mean_ci' alpha_engine/audit3_selection_alpha.py   # called without block=True
python3 tools/programme_alpha_sweep_recompute.py                     # both counts, never overwritten
```

Backups of the artefacts this report cites: `reports/_backups/2026-11-23T1017Z/` (branch ledger plus four
report JSONs, copied before any re-run). The 2026-11-20 comparison copy lives in the main tree at
`audit_dashboard/data/audit3_ledger.json`.
