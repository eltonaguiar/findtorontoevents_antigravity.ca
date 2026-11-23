# Block bootstrap wired, and the 969% field removed

**Date:** 2026-11-23 · **Author:** buffy · **Branch:** `buffy/alpha-sweep-audjpy-2026-11-23`
**Scope:** `alpha_engine/audit3_selection_alpha.py`, `tests/test_audit3_selection_alpha.py`
Paper only, zero capital, not investment advice.

## 1. `alpha_for` now asks for the honest interval

`alpha_for` called `bootstrap_mean_ci(a)` — the iid default — even though
`alpha_engine/audit3_tribunal.py:259` implements a circular moving-block bootstrap
(`block=True`, block length ≈ √n) and documents it as "the honest interval for overlapping
positions, and the only one that keeps the G2 edge gate honest". A pick is held for days, so
consecutive rows share calendar time and market moves. Changed to `bootstrap_mean_ci(a,
block=True)`, with the reasoning in a comment at the call site.

## 2. `alpha_annualized_pct` is gone

The field was `mean(alpha_i / max(hold_days_i, 1/24)) × 365`: a mean of per-trade *rates* with a
**one-hour** hold floor, extrapolated as if it were a return. On the two gate-passing cells it
reported **969.5%** and **332.0%** annualised where `alpha_pct / hold_days_mean` is 0.301%/day —
8.8× and 2.6× inflated — and it is not compoundable, ignores capacity, and is dominated by the
shortest holds.

Removed from the emitted dict; the `definition` string now states that `alpha_per_day_pct` is a
rate and that no annualised figure is published. `tests/test_audit3_selection_alpha.py` asserted the
old identity (`alpha_annualized_pct == alpha_per_day_pct * 365`) and now asserts the field is
**absent** and the rate is positive. No Python/JS/HTML consumer read it — the earlier peer review had
already noted the page never displayed it, so nothing breaks; the only remaining mentions in the tree
are dated review documents, which stay as written.

**Deliberately not changed:** `alpha_per_day_pct` itself is still the mean of per-trade ratios with a
one-hour floor, so it retains the 8.8× inflation against `alpha_pct / hold_days_mean`. Fixing that
changes values the gate reads, so it is flagged here rather than silently altered.

## 3. What actually moved (measured, not assumed)

Measured on the row set I could reconstruct — the main-tree dashboard payload's
`picks.recent_closed`, 124 rows of these two cohorts, 117 covered by price bars — computing the same
per-trade alpha as `alpha_for` and bootstrapping the identical values both ways:

| cohort | n | mean alpha | iid 95% CI | block 95% CI | Δ lower bound | passes gate? |
|---|---:|---:|---|---|---:|---|
| vol-contraction-scout | 80 | +0.7308% | [-0.3057, 1.8314] | [-0.1472, 1.6755] | **+0.1585** | no (both) |
| vwap-reversion-scout | 37 | +0.6477% | [-0.4491, 1.7137] | [-0.3804, 1.8779] | **+0.0687** | no (both) |

**This contradicts what I told the fleet an hour ago.** I said the iid interval understated variance
and made the lower bound "optimistic", so the block interval would be *wider*. On this cohort it is
**narrower at the lower end**: the bound rises by +0.1585 and +0.0687 and the upper bound moves
-0.1559 / +0.1642. Block resampling does not mechanically widen a CI — it changes which
clusters of adjacent observations are drawn, and here the low-alpha trades are not adjacent, so the
block interval is tighter. The honest interval is still the right thing to compute; the direction of
the change was an assumption, and it was wrong.

Both cohorts **fail** the gate on this row set under either interval (lower bound below zero), against
means of +0.731% and +0.648%.

## 4. What I could not re-read

The published cell bounds (**+0.1745** and **+0.1760**, n=61 and n=22) are **not reproducible from the
tables available here**:

- `trading_picks` holds **44** closed `vol-contraction-scout` rows and **0** `vwap-reversion-scout`
  rows, and `load_bars` covered **0** of those 44 (their symbols/windows are not in the price tables),
  so no alpha can be computed from that table at all.
- The dashboard payload gives a different cohort: 80 and 37 rows with lower means, not 61
  and 22.

So the two published lower bounds will move when the pipeline regenerates with `block=True`, and I
cannot say in which direction from here. Re-run and compare:

```bash
python3 -m alpha_engine.audit3_selection_alpha --picks <picks payload> \
    --out reports/selection_alpha_block.json --rows-out /tmp/alpha_rows.jsonl
python3 -c "import json;d=json.load(open('reports/selection_alpha_block.json'));print(json.dumps(d['by_strategy'],indent=1))"
```

Check `bootstrap_mode` on the CI or the `alpha_ci` values against the ledger copy at
`audit_dashboard/data/audit3_ledger.json` (generated_at 2026-11-23T06:48Z).

## 5. Verification

- `python3 -m pytest tests/test_audit3_selection_alpha.py tests/test_selection_alpha_coverage.py tests/test_audit3_tribunal.py -q` → **62 passed**.
- `py_compile` on the module.
- `grep -rn alpha_annualized_pct --include=*.py --include=*.js --include=*.html` → matches only in the
  new comment and the new test assertion; no consumer left.
- Backups of the artefacts compared here: `reports/_backups/2026-11-23T1017Z/`.
