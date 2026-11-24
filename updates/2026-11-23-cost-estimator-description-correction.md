# 2026-11-23 — Correction: cost headline figures are bar-range upper bounds, not Corwin-Schultz

**Type:** self-correction of the reporting agent's own words. This does not correct any
document authored by someone else. No number changes; no verdict changes.

## What was mis-described

In my status reporting I described the headline new-class cost figures as "derived from
the Corwin-Schultz high-low spread estimator":

- BOND **1.2125 bp**
- COMMODITY_FUTURES **6.3182 bp**
- PENNY_STOCK **21.2974 bp**

That description was wrong.

## The correction

These headline figures are **1-minute bar-RANGE upper bounds**: `statistics.median` of
the per-name median `(high - low) / close × 10000` values.

- The per-bar range is computed at `tools/equity_cost_measure.py:224`
  (`ranges = sorted((h - l) / c * 1e4 ...)`).
- The per-name median over those ranges is at `tools/equity_cost_measure.py:240`
  (`"median": ranges[n // 2]`).
- The cross-name headline median is at `tools/equity_cost_measure.py:602`
  (`"median": statistics.median(vals)`).

Because both the bid and the ask lie inside a bar's `[low, high]` at any instant, the
bar range bounds the round-trip quoted spread from above. It is an upper bound, not a
measured spread, and not the NBBO.

## What Corwin-Schultz actually is in this artifact

Corwin-Schultz is a **separate, less reliable field** in the same artifact:
`corwin_schultz_rt_bp_median`.

- The estimator itself is `def corwin_schultz(...)` at `tools/equity_cost_measure.py:147`,
  with its per-name median at `:172` (`"median_bp": statistics.median(vals)`).
- The aggregate field is emitted at `tools/equity_cost_measure.py:606`
  (`"corwin_schultz_rt_bp_median": statistics.median(css) if css else None`).

It is unusable for BOND (4 of 10 names floor at 0.0, one is negative) and meaningless
for COMMODITY_FUTURES (the median lands on an exact 0.0 from flat nested bars). Its
values are not the headline numbers above.

## What does not change

The numbers themselves do not change, and no verdict changes. Only the description of
how they were computed is corrected.

## Full reconciliation

See the two research documents for the complete reconciliation:

- `updates/2026-11-23-cost-artifact-provenance-reconciliation.md`
- `updates/2026-11-23-nbbo-measurability-probe.md`
