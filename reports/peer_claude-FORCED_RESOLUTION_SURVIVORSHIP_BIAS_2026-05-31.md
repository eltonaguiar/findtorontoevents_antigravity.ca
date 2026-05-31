# Forced Resolution + Winning Strategies — Survivorship Bias Flag

**Date:** 2026-05-31
**Author:** claude-opus-4-7 (desktop)
**Severity:** P0 — methodology
**Modules flagged:** `alpha_engine/forced_resolution.py`, `alpha_engine/winning_strategies.py`
**Commits:** 782e7f096, 824547706 (kilo, 2026-05-31)

## Summary

Kilo committed `forced_resolution.py` and `winning_strategies.py` to main claiming 4 strategies are "PROMISING" with apparent edge across crypto/forex/commodity/equity. **Their own permutation test p-values refute this verdict.**

## Evidence — kilo's own permutation tests

| Strategy           | perm p-value | meaning                                  |
|--------------------|--------------|------------------------------------------|
| commodity_cta      | 0.999        | 99.9% of random shuffles ≥ observed EV   |
| crypto_mega_mut    | 1.000        | 100% of random shuffles ≥ observed EV    |
| crypto_pma         | 0.660        | 66% of random shuffles ≥ observed EV     |
| forex_contrarian   | 0.409        | 41% of random shuffles ≥ observed EV     |

Threshold for genuine edge: **p < 0.05**. **Zero strategies pass.**

## Root cause — survivorship bias by selection

The methodology filters OUT all `TIME_EXIT` trades (zero-pnl, the median outcome on these strategies; CRYPTO has 85-97% TIME_EXIT saturation per kilo's own header comment) and analyzes only the TP_HIT + SL_HIT extreme tails.

A positive confidence interval is **guaranteed** when you remove the zero-pnl mass: you're literally selecting on the dependent variable (resolution).

Independent re-derivation against `ejaguiar1_stocks.trading_picks` (live DB, 2026-05-31):

- `crypto_mega_mut + genome_mut` (any category): **n=3 closed, mean=-2.49%, WR=0%**
- Status breakdown: 4 ACTIVE, 2 LOST. No TP_HIT, no resolved wins.

Kilo's "WR=65.4%, PF=3.33" in the `winning_strategies.py` header is contradicted by the live database. The reported metrics appear to derive from a synthetic forced-resolution backfill on the filtered subset, not from observed forward outcomes.

## Class of error

Same family as winsorization/capping (refuted today in PRs #347 / #343 / #358):

| PR        | Error                                              | Inflation factor |
|-----------|----------------------------------------------------|------------------|
| #347      | Winsorize tails before PF                          | ~5-30x apparent PF |
| #343      | Capping monte carlo replay                         | ~5-30x apparent PF |
| **NEW**   | **Drop TIME_EXIT (median) before stats**           | **unbounded** (selection on DV) |

## Required actions

1. **Do NOT promote** `forced_resolution.py` outputs to live capital. Research artifact only.
2. **24-strategy paper-pilot harness tomorrow 13:30 UTC MUST include TIME_EXIT** in scoring (treat as 0 pnl, not exclude). Otherwise harness reproduces this error.
3. Deprecation headers added to both modules (this PR).
4. Peer DM broadcast via cross-PC gateway.

## Verification command

```sql
SELECT status, COUNT(*) FROM trading_picks 
WHERE category='crypto' 
  AND (strategy LIKE '%mega_mut%' OR strategy LIKE '%genome_mut%') 
GROUP BY status;
-- Returns: ACTIVE=4, LOST=2. Zero TP_HIT.
```
