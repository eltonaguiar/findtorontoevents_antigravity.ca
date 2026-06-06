# Money-Ready Screen — Clean Cohort (all artifact filters applied)

**Date:** 2026-06-06  
**Question (operator):** "Do we REALLY have picks that would perform reliably — mutual-fund-worthy, no coin flips?"  
**Answer: NO — not confirmed today.** With every artifact filter applied, only one borderline candidate clears the bar, and it fails scrutiny.

## Method
Read-only screen of `at_pick_outcomes` applying ALL corrections simultaneously:
- exclude `resolver_version LIKE 'backfill%'` (68–100% of rows were retroactive backfill)
- exclude `resolved_at IS NULL`
- exclude BANNED_SOURCES + myfxbook/ig contrarian
- per-class sane-pnl guard (FX ≤20%, COMMODITY ≤30%, BOND ≤25%, CRYPTO ≤95%, EQUITY/ETF ≤50%) — drops reverse-split + feed-bug artifacts (CADJPY=X +428%, NZDUSD=X ±100%)
- EXPIRED counted as non-win (honest denominator)
- bar: n≥50, ≥3 months, PF>1.5, WR>52%

## Result — one screen-survivor, and it does not hold up
| strategy | class | n | WR% | expiry% | months | PF |
|---|---|---|---|---|---|---|
| luxalgo_confluence | crypto | 73 | 63.0 | 16.4 | 3 | 5.35 |
| hs_lb_None | crypto | 261 | 50.6 | 22.6 | 2 | 3.26 |
| MeanReversionBB | equity | 214 | 44.9 | 18.2 | 2 | 1.88 |
| unknown | crypto | 305 | 40.0 | 9.8 | 2 | 1.31 |
| (all others) | — | — | <50% or PF<1 | — | — | — |

**luxalgo_confluence is NOT confirmed money-ready:** the same strategy measured n=2040 / WR 45.5% / PF 1.20 over its full resolved history (per the per-class edge audit). The 63%/PF 5.35 here rests on just 73 of 2040 rows (3.6% clean subset) and has NOT passed intrabar TP-vs-SL-first-touch validation. It is a small-clean-sample candidate, not a proven edge.

## Honest verdict
The system has **no confirmed mutual-fund-worthy edge in any asset class today.** This is a measurement-and-data-quality state, not a final alpha judgment — the clean cohort is too small (artifacts removed ~78% of resolved rows) to confirm OR deny most strategies.

## Bridge to money-ready (fastest path)
1. **Deepen `crypto_ohlcv` / add `stock_ohlcv` history** so intrabar re-resolution can cover the full pick history (currently 1,422/3,000 picks are out-of-window → no_data). This is the gating data dependency.
2. **Run `reresolve_intrabar.py --apply`** (backup-first) to replace artifact labels with true first-touch outcomes across the book.
3. **Re-screen** on the now-large clean+intrabar cohort; only strategies clearing n≥100, ≥3 months, PF>1.5, WR>52% with intrabar validation advance to a **paper-pilot** (not real money).
4. **Wire the dormant academic sleeves** (TSMOM / residual-momentum / carry) which use trailing-stop/signal-flip exits and structurally avoid the expiry trap.
5. Real money only after a sleeve holds the bar on FORWARD (post-fix) data for ≥4 weeks.
