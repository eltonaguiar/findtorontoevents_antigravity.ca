# Looser-Bar Watchlist Sweep: Null Result + the 6-Day-Snapshot Bottleneck — 2026-06-09

**Author:** Claude Opus 4.8 (autonomous edge-research loop)
**Type:** read-only discovery (no production mutation)
**Goal #1** (phenomenal performance across all asset classes on /audit)

## TL;DR

Loosened the edge-hunt bar to **n≥50, PF>1.3, WR>50%** on the intrabar-COALESCE
clean cohort (non-backfill, banned-excluded, sane-pnl-capped), then cross-checked
each survivor against DSR/PBO + concentration HHI. **Result: 0 trustworthy watch
candidates.** The 2 filter-survivors are nominal-TP/SL-pinned 6-day snapshots.

The dominant discovery is structural and quantified: **83% of the entire clean
(non-backfill) outcome cohort resolved inside a single ~6-day window
(2026-05-31 → 06-05), 821 of them on 2026-05-31 alone.** The "clean forward
record" is ~1 week of heavily autocorrelated data — not a multi-month forward
test. No durable edge is *establishable* from it regardless of strategy quality.

## The 2 survivors — both REFUTED

| class | strategy | n | WR | PF | syms | HHI | why refuted |
|-------|----------|--:|---:|---:|-----:|----:|-------------|
| crypto | luxalgo_confluence | 76 | 80% | 6.08 | 16 | 0.063 | 32 wins pinned at exactly +3.5% (ghost-row nominal-TP fill); 6-day window |
| equity | MeanReversionBB | 175 | 55% | 1.82 | 8 | 0.140 | **every** win = exactly +3.0%, **every** loss = exactly −2.0%; 5 days, 8 symbols |

- **MeanReversionBB** is the purest illustration: 96 wins all at +3.0%, 79 losses all
  at −2.0%. PF 1.82 is a *mechanical* consequence of the 1.5:1 reward:risk ratio ×
  54.9% TP-first rate, not a measured P&L distribution. 175 picks across 8 symbols
  over 5 days → effective independent n ≪ 175 (dense autocorrelated sampling of the
  same 8 price paths). Not a fabrication, but not a durable edge — a thin, narrow,
  unvalidated snapshot. DSR/PBO unavailable (strategy absent from closed_picks.json
  returns cache), so it cannot even be overfit-tested.
- **luxalgo_confluence** clean n=76 (the n=2055/41%/PF1.20 figure cited earlier was
  backfill-contaminated; the clean subset is 76). 80% WR is the +3.5% nominal-fill
  pinning over the same 6-day window.

Both pass the HHI<0.25 concentration check but fail on window length (≈1 week vs the
≥3-month money-ready floor) and effective sample size.

## Structural finding — the clean cohort is a 6-day snapshot

Clean (non-backfill) WON/LOST outcomes, by resolved_at:

| date | n |
|------|--:|
| 2026-05-31 | 821 |
| 2026-06-02 | 311 |
| 2026-06-05 | 302 |
| 2026-06-04 | 213 |
| 2026-06-01 | 143 |
| 2026-06-03 | 105 |
| (all other 28 days combined) | ~387 |

- **1895 / 2282 (83%)** fall in 2026-05-31 → 06-05.
- Total clean cohort = 2282 over 34 nominal days, span 2026-04-06 → 06-09, but the
  mass is one ~6-day batch dominated by a single day (5/31).

### Why this is the real bottleneck
Every per-class WR/PF on the clean cohort is effectively a **single-snapshot
measurement** — one market regime, one ~week, dense autocorrelation across a handful
of symbols. This simultaneously explains:
1. Why the strict edge-hunt found 0 T2 leads (2026-06-09, report `…intrabar-edge-hunt-and-resolver-keyspace-gap.md`).
2. Why the looser bar only surfaces nominal-pinned snapshot artifacts.
3. Why DSR/PBO rejects 8/9 strategies with sufficient history (overfit signatures on thin data).

It is **not** purely a no-signal problem and **not** purely a resolver problem — the
clean forward record is too short and too autocorrelated to *measure* a durable edge,
full stop.

## What actually moves the needle (for future iterations)
The only fix is **time + breadth of clean forward resolutions**:
- Keep the daily resolver + the picks-now auto-resolve workflow (commit `21b8e588fe`)
  running so the clean cohort accumulates across regimes/weeks.
- Re-run this exact sweep in ~3–6 weeks; a real edge must persist across multiple
  6-day batches, not within one.
- Until the clean cohort spans ≥3 months with decorrelated samples, treat ALL
  per-class WR/PF as provisional. **No class should be sized up on the current
  6-day snapshot** — consistent with `money_ready_verdict` 0/9.

## APPENDIX — verified against the `at_signal_outcomes` intrabar ledger (later same day)

A money-ready swarm built a **self-contained intrabar ledger `at_signal_outcomes`** (its own
entry/tp/sl/exit columns + `intrabar_pnl_pct`/`intrabar_status`/`intrabar_ambiguous`). Verifying its
claim against the live DB **refines the "6-day snapshot" framing above** (which was specific to
`at_pick_outcomes`):

- **1,553 intrabar-resolved signals spanning 93 distinct closed-days (2026-02-24 → 06-09)** — NOT a
  snapshot. (The intrabar replay was batch-run 2026-06-09 over temporally-distributed signals, so the
  underlying sample is decorrelated.) Top closed-days are spread (151/104/103/79/65/57/51/50…), not
  83%-in-one-window.
- Per-class clean intrabar (non-banned, per-class sane-pnl cap):

  | class | n | WR | PF | verdict |
  |-------|--:|---:|---:|---------|
  | CRYPTO | 1040 | 36.0% | 0.74 | net loser |
  | FOREX | 82 | 35.4% | 0.50 | net loser |
  | MEMECOIN | 73 | 26.0% | 0.59 | net loser |
  | **EQUITY** | **72** | **58.3%** | **2.13** | **T2-shaped, fails only n≥100** |
  | **COMMODITY** | **98** | **40.8%** | **1.73** | close, n<100 |
  | (null class) | 58 | 10.3% | 0.09 | garbage / unlabeled |

**Corrected conclusion:** the "0 classes clear Tier-2" result **holds on a second, broader (93-day)
intrabar dataset** — so it is robust, not a snapshot artifact. BUT the framing "we only have ~1 week of
data" was too pessimistic: EQUITY (58.3%/PF2.13) and COMMODITY (40.8%/PF1.73) are **genuine n→100
watch candidates blocked on sample size, not calendar time**. These match `greedy-mixing-puppy.md`'s
claims exactly. The wiring of `money_ready_verdict` to read this ledger (that plan's Workstream F) is
peer-owned — this appendix independently confirms the data source is sound and the per-class numbers.

## Method (reproducible)
Same filters as `…intrabar-edge-hunt-and-resolver-keyspace-gap.md` (intrabar COALESCE,
non-backfill, 20 banned sources + `prediction_market_consensus`/`hs_lb_None`/`unknown`,
per-class sane-pnl caps), bar loosened to n≥50/PF>1.3/WR>50%. DSR/PBO via
`alpha_engine.anti_overfit_validator.evaluate_strategy` over the closed_picks.json
returns cache; HHI from the symbol distribution.
