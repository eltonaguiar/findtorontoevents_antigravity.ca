# Excluded-cohort bias measurement (N6) (2026-11-19)

**Scope:** `audit_trail/excluded_cohorts.py` (new),
`tests/test_excluded_cohorts.py` (new).

## Why (N6)

audit3 scores only rows that survive the dashboard's integrity filters. The
dropped cohorts — invalid rows, mirror duplicates, non-performance exits,
resolver breakeven fallbacks, auto-expired — never reach the ledger, so their
PnL is invisible. Nobody can tell whether the retained book is **flattered by
what was dropped**.

The generator already holds those rows at exclusion time (see
`_is_auto_expired_pick`, the auto-expired split, and the integrity counters), so
the missing piece was a small, testable aggregation.

## What

- `summarize_excluded(rows, reason=None)` — per-reason `n`, `n_with_pnl`,
  `win_rate`, `mean_pnl_pct`, `sum_pnl_pct`, long/short split, top symbols,
  first/last closed.
- `bias_report(included, excluded)` — retained vs excluded mean PnL and the gap
  in percentage points, with an explicit note that a positive gap is
  **selection risk, not skill**.
- `split_auto_expired(rows)` / `is_auto_expired(row)` — non-mutating helpers
  matching the generator's existing marker and `STALE (auto-expired …)` reason.

Mean PnL uses only rows with a numeric `pnl_pct`; rows that only carry a `won`
flag contribute to win rate, not to the mean.

## Wiring point (one call, for whoever owns the generator)

In `audit_trail/dashboard_generator.py`, where the build separates
`auto_expired` from real closed picks, after the other integrity filters:

```python
from audit_trail.excluded_cohorts import summarize_excluded
payload["excluded_cohorts"] = summarize_excluded(
    [dict(r, exclude_reason="auto_expired") for r in auto_expired]
    + [dict(r, exclude_reason=why) for r, why in integrity_excluded])
```

Not applied here: the generator is ~800 KB and this change was deliberately kept
testable and blind-safe. The helper is ready and covered.

## Verification

`python3 -m pytest tests/test_excluded_cohorts.py -q` -> **8 passed**
(per-reason stats, pnl-less rows, won-flag fallback, reason override, bias gap,
missing-pnl gap, auto-expired split, empty input).

*Not investment advice.*
