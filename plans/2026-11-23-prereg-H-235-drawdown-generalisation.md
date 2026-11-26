# PRE-REGISTRATION — H-235: does the drawdown reduction survive outside the US 2005-2026 book?

**Filed:** 2026-11-23, before the run. **Rule:** M-107. **Status at filing:** REGISTERED.

## Why

H-233 refuted the **return** half of vol-targeted 60/40 (certainty-equivalent gain flips sign
between 2005-2015 and 2016-2026) but the **drawdown** half replicated in both windows
(-26.82->-21.60 and -26.39->-19.10). H-233's own limitation note named this test: a book outside
the sample. If the drawdown benefit is US-2005-2026-specific it cannot be sold as a rule.

## Books and windows (fixed now)

- `US_pre2005`: SPY 60 / TLT 40, 2002-07-30 .. 2004-12-31 (TLT's inception bounds this; ~600 bars,
  underpowered and disclosed as such).
- `US_2005_2026_control`: SPY 60 / TLT 40, 2005-01-03 .. 2026-11-20 (H-233's sample).
- `INTL_exUS`: EFA 60 / BWX 40, 2007-05-01 .. 2026-11-20 (developed ex-US equity + intl treasuries).

Rule unchanged: 10% target, yesterday's 60-day realised vol, cap 2x, 5 bp per unit turnover, daily
rebalanced weights.

## Acceptance

`SURVIVES` iff vol targeting produces a smaller max drawdown than plain in BOTH the pre-2005 and
non-US books. `PARTIAL` if exactly one. `FAILS` if neither. dCE is reported as secondary and is
**never** used to rescue a failed drawdown test.

## Kill rule

On `FAILS` or `PARTIAL`, the surviving half of C-026 is narrowed to "US 2005-2026 only" and the
ladder memo's risk-control recommendation is scoped to that sample.

## Disclosures

- The pre-2005 window is short by construction and cannot carry a verdict alone; it is reported as
  `UNDERPOWERED` if it has fewer than 3 years.
- BWX and EFA are US-listed ETFs of non-US assets; this is an instrument-level non-US test, not a
  non-US-listed-fund test.
- Costs are modelled at 5 bp/unit, not measured.
