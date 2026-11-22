# Exclusion bias, bounded instead of hand-waved (2026-11-20)

## What was broken

`payload_coverage` in [`alpha_engine/audit3_tribunal.py`](alpha_engine/audit3_tribunal.py:583)
already states *how much* of the closed book the ledger judges:

> audit3 scores 3,192 of 5,428 closed picks (58.8%). The other 2,236 are not in
> this ledger: the publishing dashboard reports 1,4xx integrity-excluded and
> 9xx auto-expired rows, and no surface scores any of them.

That is a count. It is not an argument. Dropping ~41% of a book is only
defensible if someone can say whether the missing rows could change the
conclusion — and until now nothing did. Every headline number (mean net
return, win rate, per-class alpha) was quoted as if the scored slice were the
book, with "we don't know" standing in for the answer.

## What changed

Added `exclusion_bias_bound(rows, unscored, quantiles=(0.05, 0.5, 0.95))` and
wired it into `payload_coverage` as an `exclusion_bias` block.

The method needs no missing data. For each quantile of the **scored** net
distribution, assume every unscored row landed at that value, then recompute
the pooled mean:

```
combined = (sum(nets) + assumed * unscored) / (n + unscored)
```

Three scenarios (5th, 50th, 95th percentile) give a range, and two booleans
carry the whole reading:

- `sign_stable` — the entire range keeps one sign. Exclusion **cannot** flip the
  conclusion, whatever the missing rows were.
- `straddles_zero` — the range crosses zero. The headline is **not robust** to
  the missing book and must not be quoted alone.

When it straddles zero, the coverage statement now says so in prose rather than
leaving the reader to infer it from a row count.

These are deliberately extreme scenarios — every missing row identical, at a
tail quantile. Real excluded rows are heterogeneous, so the true pooled mean is
normally well inside the range. That makes it a conservative bound, which is
the right direction: it can only understate robustness, never overstate it.

## Why not just estimate the missing rows

Because the two excluded cohorts are not a random sample and we do not have
them:

- **integrity_excluded** — ghost rows, WON-vs-PnL sign contradictions, constant
  or zero pnl. Their returns are meaningless by construction; imputing a mean
  from the scored book would import a number that never existed.
- **auto_expired** — resolved by timeout, not TP/SL. A timeout is neither a win
  nor a loss, and its pnl distribution is genuinely different (it is whatever
  the market did over the holding period).

A point estimate over either cohort would be a fabricated number with a
plausible-looking CI. A bound is honest about what is unknown and still
answers the question that matters: could this change the verdict?

## Verification

- `tests/test_exclusion_bias_bound.py` — 8 deterministic tests, no DB:
  no-unscored returns `None`; an empty scored book returns `None` rather than
  inventing a bound; clearly profitable and clearly losing books are
  `sign_stable`; a thin wide-spread book straddles zero; the range brackets the
  scored mean only when scenarios differ; more missing mass pulls the range
  toward the assumption; non-numeric pnl rows are ignored.
- `python3 -m pytest tests/test_exclusion_bias_bound.py tests/test_audit3_tribunal.py -q`
  → **42 passed**.

## Not done

- The bound is univariate: it assumes the missing rows differ from the scored
  book only in their mean return, not in their composition (e.g. all of them
  being one asset class). A per-class version would be the natural next step if
  the excluded cohorts turn out to be class-skewed.
