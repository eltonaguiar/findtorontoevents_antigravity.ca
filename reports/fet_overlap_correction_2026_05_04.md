# FETUSDT Elite Claim — RETRACTED After Overlap Analysis

## TL;DR

The previous claim that `ml_enhanced_FETUSDT_1d_B_lightgbm` is a buried elite (PF 9.43, n=44, +$15,181) is **largely an artifact of overlapping positions, not independent edge**. After deduplication by exit_date, the strategy's metrics collapse to **WR 35%, PF 1.79, +$908 across 20 distinct trade events**. Still mildly positive but FAR from elite.

This **supersedes** the FETUSDT verification in `reports/fetusdt_buried_elite_2026_05_04.md` and the related entries in `reports/comet_strategy_verification_2026_05_04.md`, `reports/verified_audit_findings_summary_2026_05_04.md` finding #1, and `reports/strategy_inversion_findings_2026_05_04.md` D4. **Withdraws the FETUSDT promotion recommendation entirely.**

## What the data actually shows

44 picks chronologically (`alpha_engine/data/closed_picks.json`, post-Patch-2 backfill):

```
entry_date    hold  pnl_$    pnl_pct  exit_date    reason
2026-02-22    21d   +602    +0.30    2026-03-16   TP_HIT
2026-03-08    7d    +921    +0.46    2026-03-16   TP_HIT
2026-03-09    6d    +906    +0.45    2026-03-16   TP_HIT
2026-03-10    6d    +882    +0.44    2026-03-16   TP_HIT
2026-03-11    4d    +699    +0.35    2026-03-16   TP_HIT
2026-03-12    4d    +738    +0.37    2026-03-16   TP_HIT
2026-03-13    12d   +1163   +0.5813  2026-03-25   TP_HIT  <-- cluster start
2026-03-14    10d   +1163   +0.5813  2026-03-25   TP_HIT
2026-03-15    10d   +1163   +0.5813  2026-03-25   TP_HIT
2026-03-16    9d    +1163   +0.5813  2026-03-25   TP_HIT
2026-03-17    8d    +1163   +0.5813  2026-03-25   TP_HIT
2026-03-19    5d    +1163   +0.5813  2026-03-25   TP_HIT
2026-03-20    5d    +1163   +0.5813  2026-03-25   TP_HIT
2026-03-21    4d    +1163   +0.5813  2026-03-25   TP_HIT
2026-03-23    2d    +1163   +0.5813  2026-03-25   TP_HIT
2026-03-25    0d    +1163   +0.5813  2026-03-25   TP_HIT  <-- cluster end (10 entries)
2026-03-26 .. 2026-04-20: 27 EXPIRED picks, mostly small losses (avg ~-$50)
```

**Pattern**: the strategy fires every day. When price moves through the daily 1d_B_lightgbm signal threshold and a TP is in range, ALL open positions close at the same TP simultaneously. Bookkeeping records this as N independent winning trades; mechanically it's 1 market event.

## Dedup analysis

Three views of the same 44 picks:

| Method | n | WR | PF | sum_$ |
|---|---|---|---|---|
| **Raw (no dedup)** | 44 | 56.8% | 9.43 | +$15,181 |
| Dedup by `(exit_date, pnl_pct)` (clusters with same exit + same return → 1 event) | 35 | 45.7% | 3.62 | +$4,717 |
| **Dedup by `exit_date` only** (1 trade event per market exit) | **20** | **35.0%** | **1.79** | **+$908** |

The middle view (35 picks) is the kindest reading — different pnl_pcts on the same exit_date are kept separate, on the assumption that the pick entered at a different price. The bottom view (20 picks) is the strictest — every distinct exit-date is one market move, period.

Either way, the strategy is FAR weaker than the raw n=44 suggested. **WR 35% is below random for a binary win/loss outcome.**

## Cross-check: do INJ and DYDX have the same problem?

Same dedup-by-exit-date battery on the other "elites":

| Strategy | Raw | Dedup-by-exit |
|---|---|---|
| `ml_enhanced_FETUSDT_1d_B_lightgbm` | n=44 PF 9.43 WR 56.8% +$15K | **n=20 PF 1.79 WR 35%** +$908 |
| `ml_enhanced_INJUSDT_1d_B_lightgbm` | n=28 PF 41.52 WR 96.4% +$8K | n=18 PF 25.88 WR 94.4% +$4,977 |
| `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` | n=31 PF 60.54 WR 96.8% +$1K | n=20 PF 40.20 WR 95.0% +$737 |

INJ and DYDX hold up much better than FET — WR stays >94%, PF stays >25. The 28→18 and 31→20 reductions are smaller proportionally (35-36% reduction vs FET's 55% reduction in n).

So:
- **FET — RETRACTED**. PF 9.43 was inflated by a single 10-day cluster around 2026-03-25.
- **INJ — STILL CANDIDATE** (PF 25.88 post-dedup is still >T1 floor of 2.0).
- **DYDX — STILL CANDIDATE** but n=20 is below T2 floor of 100.

## Implication for promotion

`reports/strategy_inversion_findings_2026_05_04.md` D4 recommended promoting FET to candidate tier. **WITHDRAW that recommendation.** The honest verdict: FET 1d_B_lightgbm is unremarkable — n=20 effective trades, mildly positive, well below T2 charter floor.

INJ and DYDX still warrant attention but neither has reached n>=100 distinct events. Hold for n growth + run a third sanity check (per-symbol survivorship in the training data — were these the only profitable symbols across the 1d_B_lightgbm sweep, or were they cherry-picked?).

## Implication for the audit dashboard

The **dedup-by-exit-date** is a basic sample-size correction that should be a feature of the audit dashboard's per-strategy rollup, not just an ad-hoc analysis. Recommend a follow-up PR to `audit_trail/dashboard_generator.py` that emits both `n_raw` and `n_distinct_events` per strategy, with PF/WR computed against the latter for any "promote" / "block" decision.

This generalizes: every daily-firing strategy (which is most ml_enhanced 1d_B variants) will have inflated n. Without dedup, the dashboard surfaces fictitious confidence.

## What this means for the broader prior-claim verification scoreboard

Updating `reports/verified_audit_findings_summary_2026_05_04.md`:

- **OLD finding #1**: "LONG conf [0.80, 0.85): n=120 WR 62.5% PF 5.83" — this finding is from a different cohort (cross-asset, cross-strategy) and is unaffected by per-strategy dedup. Still valid.
- **OLD finding #3**: `ml_enhanced_FETUSDT_1d_B_lightgbm` PF 9.43 — **RETRACTED post-dedup**. PF 1.79.
- INJ and DYDX upgraded from "buried elites" to "still candidates pending dedup-aware analysis".

Net: of 11 prior numeric claims, **0 fully verified** at face value, **1 partially holds** (LONG conf band), **3 collapse under stricter sample analysis** (FET, parts of INJ, parts of DYDX), **7 fully rejected**.

## Provenance

- Source: `alpha_engine/data/closed_picks.json` post-Patch-2
- Compute: 2026-05-04 dedup-by-(exit_date, pnl_pct) and dedup-by-exit_date
- Cross-references: this supersedes the FETUSDT-positive findings in:
  - `reports/fetusdt_buried_elite_2026_05_04.md`
  - `reports/comet_strategy_verification_2026_05_04.md`
  - `reports/verified_audit_findings_summary_2026_05_04.md` finding #1
  - `reports/strategy_inversion_findings_2026_05_04.md` D4
  - `reports/unknown_asset_class_deep_investigation_2026_05_04.md` (the "buried elites" table needs annotation)
