# Block 2, Round 22 — FOREX short-horizon mean-reversion

**Date:** 2026-11-22 · **Class:** FOREX · **Harness:** [`tools/fx_meanrev_research.py`](../../tools/fx_meanrev_research.py:1) · **Machine output:** [`reports/fx_meanrev_20261122.json`](../../reports/fx_meanrev_20261122.json)

**Verdict: `KILL`** — the reversal signal beats a random-rank null decisively on gross return, but the gross edge (+4.30 bp per position) is less than half the round-trip cost (10 bp), so net is negative at both cost levels and the CI lower bound is below zero.

---

## Hypothesis (pre-registered, verbatim)

> A daily cross-sectional FX strategy that goes long the worst-performing quintile and short the best-performing quintile by 5-day return, held 5 days, earns a positive net return after 2x realistic costs.

Pre-registered parameters, unchanged after seeing results: formation **5** trading days, hold **5**, rebalance every **5** (non-overlapping), quintile **20%**, equal weight within each leg, seed **42**.

**Why 5d/5d is the natural first test, not a tuned choice:** short-horizon reversal in FX is a documented liquidity-provision effect (market makers absorb order flow imbalance and are paid when price partially reverts). For that effect to be capturable the holding period must be short relative to the formation horizon over which the overreaction decays. 5d formation / 5d hold is the smallest symmetric configuration that expresses the hypothesis with one full round trip per record.

## Panel

| Item | Value |
|---|---|
| Pairs (full) | **110** ordered pairs |
| Pairs (deduplicated) | **55** independent crosses |
| Dates | **2,022** business days, 2018-12-31 .. 2026-11-20 |
| Source | `data/forex_rate_cache/*.csv`, `date,close` (ECB fix via Frankfurter) |
| Values filled / interpolated | **0** — only rows present in the files |

**Deduplication.** 110 ordered pairs over 11 currencies contain every unordered pair twice (`EURUSD` and `USDEUR` are exact inverses). The primary universe keeps the alphabetically canonical orientation of each unordered pair (`AUDCAD` kept, `CADAUD` dropped) → C(11,2) = **55 crosses**. The full-110 universe is reported as the secondary result so the effect of the inverse-pair doubling is visible. In the deduplicated universe 54 of 55 crosses appear in a leg at least once (`DKKEUR` never falls in either quintile across 403 windows; 14 slots per leg out of 55).

## Method

- At rebalance date `D`: signal = `close(D)/close(D-5) - 1`, known at the close of `D`.
- Rank the cross-section ascending; go **long the worst 20%** and **short the best 20%**, equal weight (22 positions per window in the dedup universe, 44 in the full universe).
- Position established at `close(D)`, realised over `close(D) → close(D+5)`, signed `+1` long / `-1` short.
- Windows are adjacent and non-overlapping (**403 windows**). Each pair-rebalance is one full round trip, so exactly one round-trip cost is charged per record.

## Cost assumption

**10 bp per position round trip (1x); 20 bp for the 2x case** — deliberately identical to Round 21.

Justification: the panel is ECB *fix* (mid) rates, so no spread is embedded and the cost line is the only place a spread enters. G10 spot round trip is ~2–5 bp institutional and ~10–20 bp retail. The universe includes thin DKK/SEK/NOK crosses priced at a daily fix with no tick data to estimate a real spread, so 10 bp (retail midpoint) is the conservative choice for a non-institutional participant and 20 bp covers the retail upper bound. One round trip per record is exact because every position is held exactly one window.

## Statistics

### Primary: deduplicated 55-cross universe (n = 8,866 pair-rebalances, 403 windows)

| Statistic | Value |
|---|---|
| n (pair-rebalances / windows) | **8,866 / 403** (windows positive: 184) |
| Mean **gross** return | **+4.30 bp** |
| Mean **net** return (1x cost) | **−5.70 bp** |
| Median net return | **−7.41 bp** |
| 95% bootstrap CI on mean net | **[−8.25, −3.06] bp** (10,000 resamples, seed 42) |
| 95% CI, window-clustered | [−13.32, +2.09] bp |
| Mean net at **2x** cost | **−15.70 bp** |
| Win rate (gross → net) | 51.04% → **47.27%** |
| First-half mean net | **−5.20 bp** |
| Second-half mean net | **−6.19 bp** |
| Worst / best window (mean net) | **−377.55 / +287.48 bp** |
| Worst / best single pair-rebalance | −859.12 / +651.37 bp |
| Long leg / short leg mean net | **−3.74 / −7.65 bp** |
| Concentration (best pair JPYSEK) | share of total net **n/a** (total negative); share of gross absolute P&L **2.48%**; 2.74% of records |
| Cost haircut (total) | 88,660 bp over 8,866 round trips |

### Secondary: full 110-pair universe (n = 17,732 pair-rebalances, 403 windows)

| Statistic | Value |
|---|---|
| Mean gross / net (1x) / net (2x) | **+4.32 / −5.68 / −15.68 bp** |
| 95% bootstrap CI on mean net | **[−7.48, −3.86] bp** |
| 95% CI, window-clustered | [−13.25, +1.90] bp |
| Win rate (gross → net) | 50.97% → **47.29%** |
| First-half / second-half mean net | **−4.94 / −6.42 bp** |
| Long leg / short leg mean net | **−4.92 / −6.45 bp** |

The two universes agree to within 0.02 bp on mean net: removing the inverse-pair doubling changes essentially nothing, because each duplicated pair contributes an exactly offsetting bet.

## Null test (decisive number)

≥1,000 shuffles of random cross-sectional ranks, same rebalance / hold / cost (dedup universe, seed 42):

| | Value |
|---|---|
| Null mean net | **−10.04 bp** |
| Null SD | 1.25 bp |
| Null 95th percentile | **−7.97 bp** |
| Null maximum | −6.36 bp |
| Observed mean net | −5.70 bp |
| **Observed percentile in null** | **100.0th** (empirical p = 0.001) |

Interpretation: the 5-day reversal signal carries *real* information about the next 5 days — a random ranking earns −10.04 bp (pure cost), while the reversal ranking earns −5.70 bp, i.e. **+4.3 bp of genuine gross edge over random** and better than all 1,000 shuffles. The edge is real but too small to pay the toll.

## Gates

| Gate | Test | Result |
|---|---|---|
| **G1** | 95% CI lower bound on mean net > 0 at 1x cost | **FAIL** (−8.25) |
| **G2** | mean net > 0 at 2x cost | **FAIL** (−15.70) |
| **G3** | both halves positive | **FAIL** (−5.20 / −6.19) |
| **G4** | observed mean above null 95th percentile | **PASS** (−5.70 > −7.97, 100th pct) |
| **G5** | no single pair > 30% of total return | **n/a** — total net is negative so a share is not interpretable; gross-absolute concentration of the top pair is 2.48%, far under 30% |
| **G6** | dedup-55 and full-110 agree in sign | **PASS** (both −5.70 / −5.68) |

## Verdict and reasoning

**`KILL`.** G1 and G4 are the decisive pair, and G1 fails: the CI lower bound on net is −8.25 bp. The gross edge is real (G4 passes at the 100th percentile of the null) but it is **4.3 bp against a 10 bp round trip** — the cost is 2.3x the edge. Even at zero cost the mean would be only +4.3 bp, and at the institutional 2–5 bp round trip that FX majors actually charge, the strategy would still be marginal-to-negative (4.3 bp edge vs 2–5 bp cost → −0.7 to +2.3 bp). The 5d/5d FX reversal is therefore not a tradable edge at realistic costs, though it is a measurable effect.

Both legs lose net (−3.74 long, −7.65 short): the long leg (worst performers) recovers more than the short leg, i.e. reversal after *declines* is stronger than reversal after *rallies* — but neither clears cost.

**Anti-fishing clause honoured.** Because G1 failed, no alternative lookback was tried. No 3d, 10d, or 21d variant is reported, and none was run.

## Relationship to Round 21 (why this is a distinct test, not a re-tune)

Round 21 tested FX **momentum** (63d formation, 21d hold, long winners / short losers) and was **KILLED**: n = 4,092, mean net **−36.88 bp**, 95% CI [−44.13, −29.59], 0.0th percentile of a 1,000-shuffle null, both legs negative, gross itself negative (−26.88 bp).

Round 22 tests the **opposite economic claim**: that FX over short horizons **mean-reverts** (liquidity provision / overreaction), not that it trends. The differences are all fixed a priori, not chosen after a result:

- **Sign of the expected edge is inverted** — R21 longs the best performers, R22 longs the worst.
- **Horizon is 12.6x shorter** (5d/5d vs 63d/21d) because the reversal effect decays in days while momentum is a medium-term claim; the holding period must be short relative to the overreaction horizon.
- **Both legs are the opposite side of the cross-section**, so a positive result could not be produced by R21's data in either direction.

Changing 63d→5d alone and keeping the momentum sign would have been parameter fishing. The two rounds instead bracket the mechanism from both sides. **Both fail, for different reasons:** R21 failed because the signal was *worse than random* (momentum direction has no edge in this FX panel); R22 fails because the signal is *better than random but smaller than cost* (reversal edge exists but is ~4 bp). Neither result makes the other redundant, and together they say FX spot cross-section at daily frequency carries at most a few bp of exploitable structure per 5-day bet.

## Reproduction

```bash
python3 tools/fx_meanrev_research.py --out reports/fx_meanrev_20261122.json
# deterministic: identical stats on re-run (seed 42, 1,000 shuffles, 10,000 bootstraps)
```
