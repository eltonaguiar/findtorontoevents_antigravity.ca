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
  (692 rows). The dominant clean resolver `universal_v2` (1528 WON/LOST rows) is
  **unreachable** → clean-cohort PF/WR is **not** intrabar-validated.
- Intrabar edge-hunt (2026-06-09) found **0 trustworthy T2 leads**; the 2
  survivors (`hs_lb_None` 3d-window null-artifact, `MeanReversionBB` 5d/8-symbol)
  are refuted, both `n_intrabar=0`.
- Hard evidence: **measurement layer is the bottleneck, not alpha.**

## Next step
Run an intrabar pass **directly over `at_pick_outcomes`** (replay OHLC by
symbol+entry+tp+sl+timestamp, write back keyed by its own `pick_id`) — not via
`trading_picks`. `tools/reresolve_intrabar.py` only knows the `trading_picks`
keyspace today.

## Don't
Size up any class on current clean-cohort PF/WR — none are intrabar-validated.

## Related
- [[incidents/resolver-intrabar-blocker]]
- [[incidents/ai-tournament-wr-artifact]]
- [[reference/edge-rescue-roadmap]]
- [[strategies/strategy-catalog-clean-cohort]]
