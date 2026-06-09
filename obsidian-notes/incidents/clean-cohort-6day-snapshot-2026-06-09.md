---
tags: [incident, measurement, edge, P1]
created: 2026-06-09
status: open
---

# The clean cohort is a 6-day snapshot (why no edge is *measurable*)

> Report: `reports/2026-06-09-watchlist-sweep-null-and-snapshot-bottleneck.md`

## Finding
**83% (1895/2282) of the clean non-backfill outcome cohort resolved in 2026-05-31 →
06-05** — 821 on 2026-05-31 alone. The "clean forward record" is ~1 week of
autocorrelated data, not a multi-month forward test.

## Looser-bar watchlist sweep (n≥50, PF>1.3, WR>50%) → 0 trustworthy candidates
- `luxalgo_confluence` crypto n=76, 80% WR, PF 6.08 — but 32 wins pinned at exactly
  +3.5% (ghost-row nominal-TP fill), 6-day window. REFUTED. (The n=2055/41%/1.20
  figure was backfill-contaminated; clean subset is 76.)
- `MeanReversionBB` equity n=175, 55% WR, PF 1.82 — but **every** win = +3.0%,
  **every** loss = −2.0% (mechanical 1.5:1 R:R), 5 days / 8 symbols, effective n ≪ 175.
  DSR/PBO unavailable. REFUTED as a lead; thin snapshot.

## Why this is the bottleneck
It is NOT purely no-signal and NOT purely a resolver bug. The clean record is too
short + autocorrelated to *measure* a durable edge. Explains: strict edge-hunt 0
leads; looser bar only snapshot artifacts; DSR/PBO rejects 8/9 strategies.

## Only fix = time + breadth
Keep the daily resolver + picks-now auto-resolve (commit 21b8e588fe) running so the
clean cohort spans multiple regimes. Re-run the sweep in 3–6 weeks; a real edge must
persist across many 6-day batches. Until ≥3 months of decorrelated clean data, treat
all per-class WR/PF as provisional — size up nothing (consistent with money_ready 0/9).

## Related
- [[incidents/resolver-keyspace-gap-2026-06-09]]
- [[incidents/ai-tournament-wr-artifact]]
- [[reference/edge-rescue-roadmap]]
