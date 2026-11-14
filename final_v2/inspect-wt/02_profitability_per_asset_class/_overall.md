# Cross-cutting: order of operations + certification gates (read before the class files)

## Why this file comes first
Every class file in this folder assumes four upstream fixes. Without them, *no* PF, WR or
Sharpe on this system's data can be certified — that is the merged finding of quant-audit
(`resolution_method=None` ×3,500 — **since retracted by quant-audit**: the field is
`exit_reason`, populated; I re-verified), finpredict-v3 (PnL-unit mix bug — **scoped**: real in
`multi_asset_closed.json`, NOT the dashboard ledger, which I re-verified reproduces 3,500/3,500),
and me (zombies, garbage ingest, ledger disagreement, **stop-fill overshoot**).

## Order of operations (strict sequence — UPDATED after quant-audit's final_v2 corrections)
1. **Fix fill fidelity** (the #1 verified blocker: crypto realizes 2.970% on 1.932% planned
   risk; 98.8% of the class loss is overshoot — fills-at-stop → PF 0.768 ≈ 1.00) **+ scope the
   PnL-unit fix where it is real** (`multi_asset_closed.json`, active-pick garbage ingest).
   `exit_reason` is already populated (SL_HIT/TP_HIT/FORCE_CLOSED/TIME_EXIT) — no backfill
   needed; the nice-to-have is a field recording intrabar-vs-nominal *resolution*.
2. **One canonical ledger** (my `fixspec_single_canonical_ledger`) + **zombie purge**
   (`fixspec_zombie_purge_and_reemission_guard`): kill the 3,272 EXPIRED pnl=0 rows,
   stop inverse re-emissions (2,262 mutations), make `recent_closed` the single truth.
3. **Re-certify the two surviving claims on the cleaned ledger**: variant C (walk-forward)
   and mega_mutation (price-truth verified) → one number each, no ledger disagreement.
4. **Forward-only from then on.** No more backfill-discovery; selection trials are spent.

## Certification gates (merge T2 with finpredict-v3's stricter CI tests)
A class/strategy is **MONEY-READY** only when ALL hold **on the forward record alone**:
- **n ≥ 100** (T2; v3 says 60 — take the stricter 100 for certification, report n≥30/60 as provisional)
- **WR ≥ 50%** with **95% Wilson CI excluding 50%** on the profitable side (v3's addition — mine lacked it)
- **PF ≥ 1.5** (T2) *and* PF > 1.05 + positive mean per-trade PnL at every interim read (v3)
- **Max drawdown < 20%** at stated sizing (T2), reported bankroll-based not trade-weighted
- **Win-majority in ≥66% of walk-forward windows** (v3)
- **Multiple-testing disclosure**: # tested vs # passed, Bonferroni or pre-registration (my V1–V6 lesson)
- **Capital-adjusted**: excess-of-benchmark with paired bootstrap (finpredict's rule — absolute Sharpe in a bull window is beta)
- **Single-source check**: `is_single_source_artifact=False` on every contributing cell (quant-audit's gate — eliminates all 166 current cells)

**Kill criteria (any class):** two consecutive months PF<0.5, or 3-month rolling PF<1.0 → stop, re-audit.

## Sizing (while provisional)
¼ Kelly: at variant-C parameters (WR 47.3%, win/loss 1.41) full Kelly ≈10%/trade →
**2.5%/trade**; worst observed month (−64pp trade-weighted) ≈ **−1.6% bankroll**.

## The multiple-testing ledger (my own negative results — do not re-run these)
- V1: 46 cells (8 source, 12 source×class, 26 strategy) — **none** pass uncorrected z>1.96.
- V2: split-sample survival — plain selection p=0.006–0.038; **alive-filter refinement FAILED** (PF 0.80).
- V5: 4 pre-specified variants — only variant C survives Bonferroni-for-4 (and v2 correctly notes effective search was larger).
- Anti-overfit live: 69/80 OVERFIT_LIKELY; surface truth 0/9 money-ready.
**Lesson:** the selection well is dry; further mining on this data = burning false-positive
budget. Effort goes to (a) data-layer fixes, (b) the forward pilot, (c) *external* documented
premia (the class files), never back to signal discovery here.
