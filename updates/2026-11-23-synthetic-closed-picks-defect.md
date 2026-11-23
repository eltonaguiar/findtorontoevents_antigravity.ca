# DEFECT: 87% of `alpha_engine/data/closed_picks.json` is synthetic placeholder rows

**Date:** 2026-11-23 · **Author:** Kilo · Paper only, zero capital.

## The finding
Of **2,204** rows in `alpha_engine/data/closed_picks.json`:
- only **290** carry an `entry_date` (a real, dated trade);
- **1,914 are dateless** and their `pnl_pct` is quantised to exact barrier values:
  **−2.5 (790), −2.0 (529), 3.75 (187), 3.0 (177)** — i.e. 1,683 of 1,914 sit exactly on a
  take-profit or stop-loss level. These are **"would-hit" placeholders, not realised fills**.

## Why it matters
Any edge, DSR, or hit-rate computed on the full corpus is computed on ~87% synthetic outcomes. I found this
while computing a per-symbol 95% lower bound: the only four "LB-positive" symbols (HOMEUSDT, MEGAUSDT, FFUSDT,
ENJUSDT) were **entirely** these placeholder rows — every "trade" = +3.0% or +3.75% with `entry_date=None`.

## Re-run on real dated trades only
- Real dated trades: **290**.
- Strategies with ≥10 real trades: **3** — `forex_rsi2_mean_reversion` (n=97, DSR 0.9987 at N=61),
  `futures_momentum` (n=98, DSR 0.0), `clone_hl_copy_lb_None` (n=12, DSR 0.07).
- Symbols with ≥10 real trades: **6** — **0 have a positive 95% LB** after class cost
  (best: EURJPY=X LB −0.075%, AUDJPY=X n=39 LB −0.080%).

## Consequence
- `forex_rsi2_mean_reversion`'s DSR 0.9987 **survives the de-contamination** (its 97 trades are dated) but is
  still **net-negative after the 7.533 bp FOREX cost** and fails at the honest N=4,987 (DSR 0.876).
- The earlier "LB-positive altcoins" are **withdrawn** — they were placeholders.
- **No instrument with real data has a positive lower bound.**

## Recommendation
Filter every closed-picks analysis to `entry_date IS NOT NULL` (and treat the exact-barrier values as
`WOULD_HIT`, not realised). Better: fix the writer so TP/SL outcomes are labelled distinctly from fills.
