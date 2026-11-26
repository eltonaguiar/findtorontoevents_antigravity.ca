# Turn-of-month seasonality refuted, and a gross-vs-net comparison bug caught in the tool

**Date:** 2026-11-22 · **Type:** new measurement (item B13) + one bug caught on the run
**Files:** `tools/turn_of_month_check.py` (new), `reports/turn_of_month_2026-11-22.json` (new),
`reports/2026-11-22-turn-of-month.md` (new), `plans/2026-11-22-50-action-items.md` (status log)

## What was missing

Item B13 was the cheapest untested family in the programme: a calendar rule trades a few
times a month at ETF cost and needs no forecasting at all. If any seasonality survived cost
and a random-window null it would be a legitimate low-turnover candidate; if none did, the
family closes and the programme stops spending attention on it.

## What the measurement found

SPY, 8,491 days, 1993-01-29 → 2026-11-20, calendar-only signal, 5 bp/unit turnover:

| variant | gross bp/day | cost drag bp/day | net bp/day | null pct (gross) |
|---|---|---|---|---|
| L→+3 | +0.345 | **0.957** | **−0.612** | 23.2 |
| L only | −0.305 | 0.479 | −0.784 | 3.1 |
| +1→+3 | +0.650 | 0.478 | +0.172 | 62.5 |

**0 of 3 variants pass the three-part gate** (CI-LB > 0, both halves positive, null ≥ 95th
percentile). Family **REFUTED**.

The informative part is the decomposition: the classic window earns **+0.87%/yr gross**,
roughly what the literature claims, and costs **2.8× that** to harvest (812 round trips).
And the gross mean sits at only the **23.2nd percentile** of random same-size windows, so
the effect is indistinguishable from chance even before cost — two independent grounds for
the same verdict, both reported.

## Bug caught on the run

The random-window null is costless (it measures the mean of a mask times returns). The first
version compared that **gross** null against the **net** observed mean, which pushed the
classic variant's percentile down to **0.4** and would have let the write-up claim "worse
than 99.6% of random windows" — a far stronger and unjustified statement. Fixed to compare
gross-to-gross (**23.2**), and the tool now prints `gross_excess_bps_day` and
`cost_drag_bps_day` separately so the comparison can be audited rather than trusted.

Both bugs in this round's new tools (this one and the DSR bisection direction) were caught
by running the tool and reading its own output against what the economics requires, not by
reviewing the code.

## Verification

- `python3 tools/turn_of_month_check.py` → `RC=0`; 3 variants, 3 gates each, 0 passing.
- Halves on the classic variant are **[−0.841, −0.382]** — negative in both, so no
  regime-selection story rescues it. At 10 bp/side it is **−3.95%/yr**.
