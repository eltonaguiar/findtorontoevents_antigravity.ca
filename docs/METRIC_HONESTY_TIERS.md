# Metric Honesty Tiers — honest reporting on every WR/PF/Sharpe

**Status:** Proposed 2026-05-29 — **peer-reviewed** (3 models via `/PeerReviewSwarmOptions`, see bottom). Definitions below incorporate the consensus.
**Canonical thresholds:** inherited from [`docs/PERFORMANCE_CHARTER.md`](PERFORMANCE_CHARTER.md) §2. This doc adds the **validity gates** that decide whether a number may be trusted *at all*.
**Machine-readable source (tooltips render from this):** [`audit_dashboard/data/metric_honesty_tiers.json`](../audit_dashboard/data/metric_honesty_tiers.json).

## Why this exists

Every performance cell on `/audit` and the Investment Hub should answer, in one glance, the question a hedge-fund manager actually asks:

> *"Is this institutional-grade? Promising but not statistically valid yet? Or should I not trust the number at all?"*

A bare "WR 74%" is dishonest without context — it could be 200 OOS-confirmed multi-source trades (trust it) or 4 soft-resolved picks on one symbol (ignore it). These tiers attach that context as a tooltip + colored label so no metric is ever shown naked.

## The decisive-outcome rule (load-bearing definition)

A pick counts toward WR/PF **only if it is DECISIVE**:
- **Hard-resolved** = TP hit (`WIN`) or SL hit (`LOSS`). These are the only outcomes a strategy actually earned.
- **Soft-resolved** = closed by max-hold / expiry, scored by the sign of raw PnL. Counted **separately**; if > 25% of a cohort's "wins" are soft-resolved, the cohort is capped at *Promising — not valid yet* (soft resolution silently inflates WR — see the `miracle_picks2` example below).
- **OPEN / active** picks are **never** counted. ~50% of tournament + Investment Hub picks are OPEN; including them is the single most common inflation.

## The six tiers

| Tier | Label | Bar (all must hold) | Honest meaning |
|------|-------|---------------------|----------------|
| 🟢 | **Institutional-grade** | PF≥2.0, WR≥55%, MaxDD≤10%, **n≥200 hard-resolved**, OOS walk-forward PF≥1.5, no source/symbol ≥60%, **ZERO soft**, **staleness≤30d (hard)**, R:R-asymmetry OK, Sharpe≥1.2 | A quant fund would size this up. (= Charter Tier 1) |
| 🔵 | **Production-viable** | PF≥1.5, WR≥50%, MaxDD≤20%, **n≥100 hard-resolved**, no source/symbol ≥60%, ≤25% soft (of attempted), staleness warning | Real edge, conservative live size OK. (= Charter Tier 2) |
| 🟡 | **Promising — not statistically valid yet** | PF≥1.2 on hard-resolved, but **fails ≥1 validity gate** (n<100, single-source≥60%, stale>30d, no OOS, or >25% soft) | Interesting; **paper-only**. "Maybe — not enough evidence yet." |
| 🟠 | **Unverified — no outcome resolution** | Picks exist but **zero** resolved outcomes (no status/exit/pnl), or only synthetic summary values | **WR/PF cannot be stated.** Do not display a number — show the label. |
| 🔴 | **No edge / negative** | n≥30 hard-resolved, but PF<1.2 OR WR<45% OR MaxDD>25% | Honestly measured and losing. Mutation-before-kill candidate. |
| ⛔ | **Disputed / contaminated** | Headline contradicts the canonical policy-clean view via a leakage pattern | Number is **false until re-derived**. Show DISPUTED banner. |

Leakage patterns that trigger ⛔: duplicate signal-timestamp groups, `EXPIRED→WON` relabels, >60% single-source concentration, a PF>10 (almost always a few corrupt PnL rows), soft-resolution inflation, and literal fabricated/sentinel values (e.g. a `decimal(10,4)` column maxing out at `999,999.9999%`).

## Worked examples (all from the 2026-05-29 Investment Hub audit — real DB queries)

- 🟡 **Promising:** `gm_unified_picks / ADX Trend Strength` — WR 74.3% / PF 3.29 on n=70. Fails on n<100, crypto-concentration, STALE (Feb 2026), and ~40% soft-resolved wins. Worth a fresh forward-test, **not** a wire-up.
- 🟠 **Unverified:** `alpha_picks` (5,043) + `stock_picks` (7,239) + `cr_pair_picks` (1,008) + `fxp_pair_picks` (1,248) + `mf2_fund_picks` (600) — picks emitted with a score but **never resolved to a win/loss**. The bulk of the Investment Hub lives here. No honest WR/PF is possible.
- 🔴 **No edge:** `penny_picks` — WR 16.3% / PF 0.39 on n=331 (stop-loss-dominated micro-caps). Measurement is sound; the strategy loses.
- ⛔ **Disputed:** `fxp_algo_performance` shows FX Carry Trade `avg_return = +999,999.9999%` — a sentinel overflow, not a result. `FUTURES` pick_funnel 65.09% WR / PF 4.11 vs policy-clean 9.1% / PF 0.48. `miracle_picks2 / Mean Reversion Sniper` shows 62.5% WR but has **zero actual winners** (8 losers + 40 expired scored by sign).

## How tooltips consume this

1. On hover over any WR/PF/Sharpe cell, render `tooltip_short` for the cell's tier.
2. Color the cell border per the tier `color`; prefix the metric with the tier `emoji`.
3. Link a glossary modal showing `tooltip_full` + the decisive-outcome rule.
4. **For an `unverified_unresolved` cohort, never print a number — print the 🟠 label instead.**

## Anti-gaming gates (necessary because thresholds alone are gameable)

Peer review surfaced that the threshold gates above can be satisfied by a dishonest reporter without real edge. These gates close the loopholes:

- **Expectancy gate (R:R-asymmetry)** — *the single biggest hole.* Tight TP + wide SL manufactures a high WR via random-walk TP hits; PF>2 is trivial with a 10:1 payoff skew on coin-flip signals. **The principled, un-gameable fix (round-2 derivation):** for any cohort, the break-even WR of a *no-edge* strategy is `BE = 1/(1 + R:R)` where `R:R = |TP−entry|/|SL−entry|` (R:R 0.5→BE 66.7%, 0.6→62.5%, 1.0→50%, 2.0→33.3%). Bar from 🔵/🟢 unless the **Wilson lower bound** of observed WR **exceeds BE** with statistical significance (i.e. positive expectancy on the CI lower bound, not the point estimate). Moving TP/SL shifts BE with you, so this can't be gamed. Also require conditional WR by holding-period bucket.
- **Loss-tail / PF-binding** — many small (often soft-resolved) wins + a few large hard losses can show high WR while bleeding money. **PF, not WR, is the binding metric** for 🔵/🟢; also report largest single loss + max consecutive loss so a fat loss tail is visible.
- **OOS must be walk-forward, declared up front** — "OOS holdout PF≥1.5" is itself gameable via cherry-picked holdout periods, future-data leakage, or mislabeling in-sample as OOS. The split (anchored/rolling) must be fixed *before* the run, with no tuning on the holdout, and the split spec recorded alongside the metric so it is independently reproducible.
- **Soft-resolution clustering watch** — with a 25% soft cap on 🔵, cohorts can pile up just under 25% to maximize WR inflation. Apply the soft-share to *attempted* resolutions, monitor for pile-up at 24–25%, and tighten over time.

## Peer review (2026-05-29) — resolved

Reviewed via `/PeerReviewSwarmOptions` → `consult_multi --fanout reasoning4`: **nvidia/kimi-k2.6, nous/Hermes-4-405B, fireworks/kimi** (aimlapi/gpt-4o-mini returned HTTP 403).

| Q | Question | Consensus | Resolution applied |
|---|----------|-----------|--------------------|
| Q1 | n≥200 Tier-1 floor vs n≥100+stricter-OOS | 3/3 keep **n≥200** (hard count harder to game) | kept |
| Q2 | 25% soft cap vs zero-soft for 🔵/🟢 | 3/3 **zero soft for 🟢**, 25% only for 🔵 | tightened 🟢 to zero-soft |
| Q3 | 🟠 Unverified vs ⛔ Disputed — one tier or two | 3/3 **two** (omission ≠ commission) | kept as two |
| Q4 | staleness hard gate vs soft warning | 3/3 **hard for 🟢**, soft warning for 🔵 | applied |
| — | biggest loophole | **TP/SL payoff-asymmetry gaming** + non-verifiable OOS | added anti-gaming gates above |
