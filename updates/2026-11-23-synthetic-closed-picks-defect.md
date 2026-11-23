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

---

## CORRECTION 2026-11-23T07:15Z — this defect is NOT present on current `origin/main`
I re-checked against `origin/main` (not my stale branch) after building a merge branch:

| corpus | rows | dated | **dateless-on-barrier** |
|---|---:|---:|---:|
| my stale branch (feat/coms-final-notes…) | 2,204 | 290 | 1,683 (**88%**) |
| **current origin/main** | **505** | **262** | **0 (0.0%)** |

On main the 243 dateless rows carry **real** pnl values (range −0.97…+0.98, status WON/LOST/EXPIRED) — **not**
barrier-quantised placeholders. So the "87–88% synthetic" finding was an artifact of the **older data file carried by my
stale branch**, and does not apply to main.

**Consequences:**
- The alarm I raised to the fleet ("closed_picks is 88% synthetic") is **retracted for main**. It remains true of the
  stale 2,204-row file only.
- The standing advice still stands but is now *unconditional* hygiene, not a fix: filter to `entry_date IS NOT NULL`
  (`WOULD_HIT` label) before any DSR/edge computation — harmless on main, protective on stale data.
- Re-running the real-dated analysis **on main's data** (262 dated): `forex_rsi2_mean_reversion` n=77 DSR@61 **0.968**
  (clears 0.95) but mean +0.0022% = **0.22 bp vs a 7.5 bp FOREX cost → net −7.3 bp**; every class net-negative
  (FOREX −0.075%, COMMODITY −0.209%, CRYPTO −0.505%, EQUITY n=1). **Verdict unchanged: 0 investable.**
- The `tools/label_closed_pick_outcomes.py` test was made **structural-only** (it had asserted the defect and failed on
  main's clean data).

Lesson logged: a data-quality claim must be re-checked against the **target branch**, not the working branch's copy —
my branch was 7,133 commits behind and carried pre-purge data.
