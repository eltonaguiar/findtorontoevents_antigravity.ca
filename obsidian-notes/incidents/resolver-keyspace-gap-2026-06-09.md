---
tags: [incident, resolver, measurement, P1]
created: 2026-06-09
status: open
---

# Resolver Keyspace Gap — intrabar can't reach the clean cohort

> Full report: `reports/2026-06-09-intrabar-edge-hunt-and-resolver-keyspace-gap.md`

## The finding
The intrabar truth columns live in `trading_picks` (composite-string ids like
`::ATOM-USD::2026-05-27`). The **current production outcome resolver `universal_v2`**
writes `at_pick_outcomes` with **content-hash `pick_id`s** (`03285aa77…`) that join
**0%** to `trading_picks` and only 2% to `at_raw_picks` (UUIDs). Three disjoint
keyspaces.

## Consequence
- The intrabar `COALESCE` in `money_ready_verdict` (commit `acc551cd8f`) is correct
  but in the **clean** (non-backfill) cohort only reaches `signflip_purge` + `v2.2_sync`
  (692 rows). The hourly `trading_picks` intrabar truth **cannot** be COALESCEd onto
  the dominant `universal_v2` cohort (1528 rows, 0% join).

## CORRECTION (deeper trace 07:45Z) — gap is smaller than first stated
`universal_v2` (`outcome_resolver.py:561-611`, `walk_daily_bars`) **already does a
conservative SL-first, gap-aware first-touch replay** at **daily** granularity — NOT
the naive TIME_EXIT-mislabel resolver. So the clean cohort **IS** validly resolved
(conservatively, SL-biased). My first "not intrabar-validated → don't size up" was
too strong.
- Residual gap vs hourly = only **same-day-both-touched** bars, resolved SL-first
  (pessimistic) → hourly could only **raise** borderline WR/PF, never fake an edge.
- So the edge-hunt **0-T2-leads** result is **robust**; no-signal conclusion stands.
- A standalone `reresolve_intrabar_outcomes.py` is **blocked** (`at_pick_outcomes`
  has no entry/tp/sl; `pick_id` is an unjoinable content hash) **and unnecessary**.

## Next step (optional, low priority)
Scoped resolver enhancement: have `walk_daily_bars` use **hourly** bars
(`crypto_ohlcv`/`stock_ohlcv`) for same-day-both-touched disambiguation + set an
`intrabar_ambiguous` flag. NOT a prerequisite for trusting current clean numbers.

## Related
- [[incidents/resolver-intrabar-blocker]]
- [[incidents/ai-tournament-wr-artifact]]
- [[reference/edge-rescue-roadmap]]
- [[strategies/strategy-catalog-clean-cohort]]
