# Block 2, Round 21 — FOREX cross-sectional momentum (carry + trend mechanism test)

**Date:** 2026-11-22 · **Class:** FOREX · **Harness:** [`tools/forex_carry_trend_research.py`](../../tools/forex_carry_trend_research.py:1) · **Machine output:** [`reports/forex_carry_trend_20261122.json`](../../reports/forex_carry_trend_20261122.json)

**Verdict: `KILL`** — the mechanism loses money gross, before any cost, and sits at the 0th percentile of a random-signal null.

---

## Hypothesis (pre-registered, verbatim)

> A daily cross-sectional FX strategy that goes long the top-quintile and short the bottom-quintile of pairs ranked by 63-day momentum, held 21 days, earns a positive net return after 2x realistic costs.

Pre-registered parameters, unchanged after seeing results: lookback **63** trading days, hold **21**, rebalance every **21** (non-overlapping), quintile **20%**, equal weight within each leg, seed **42**.

## What carry means here, and why it is not tested

The round is labelled "carry + trend". **Carry cannot be priced from this data.** Carry needs interest-rate differentials; the only thing on disk is FX spot (ECB fix). No yield curve exists (`data/rate_curve_cache` is absent), which is exactly the gap that keeps BOND `BLOCKED_DATA` after the Part A fix. Spot alone cannot separate the carry component from the spot move. So this round tests the **trend/momentum leg only**, and the verdict is scoped to that. Any "carry" claim for FOREX would need rate-curve data first.

## Panel

| Item | Value |
|---|---|
| Pairs | **110** (all CSVs; every pair has an identical 2,022-date calendar) |
| Dates | **2,022** business days, 2018-12-31 .. 2026-11-20 |
| Source | `data/forex_rate_cache/*.csv`, `date,close` (ECB fix via Frankfurter) |
| Values filled / interpolated | **0** — only rows present in the files |

**Breadth caveat:** 110 *ordered* pairs over 11 currencies means every currency appears in both directions (`EURUSD` and `USDEUR` are exact inverses). Independent breadth is **55 crosses, not 110**. The pre-registered test uses all 110 as instructed; the leg breakdown below shows the effect of that duplication.

## Method

- At rebalance date `D`: signal = `close(D)/close(D-63) - 1`, known at the close of `D`.
- Rank the cross-section, go long the top 20% and short the bottom 20%, equal weight.
- Position established at `close(D)`, realised over `close(D) → close(D+21)`, signed `+1` long / `-1` short.
- Windows are adjacent and non-overlapping (93 windows). Each pair-rebalance is one full round trip, so exactly one round-trip cost is charged per record.

## Cost assumption

**10 bp per position round trip (1x); 20 bp for the 2x case.**

Justification: the panel is ECB *fix* (mid) rates, so no spread is embedded and the cost line is the only place a spread enters. G10 spot round trip is ~2–5 bp institutional and ~10–20 bp retail. The universe includes thin DKK/SEK/NOK crosses priced at a daily fix with no tick data to estimate a real spread, so 10 bp (retail midpoint) is the conservative choice for a non-institutional participant, and 20 bp covers the retail upper bound. Because every position is held a full window and closed at the next rebalance, one round trip per record is exact.

## Statistics (n = 4,092 pair-rebalances, 93 windows)

| Statistic | Value |
|---|---|
| n (pair-rebalances / windows) | **4,092 / 93** (windows positive: 40) |
| Mean **gross** return | **−26.88 bp** |
| Mean **net** return (1x cost) | **−36.88 bp** |
| Median net return | **−35.93 bp** |
| 95% bootstrap CI on mean net | **[−44.13, −29.59] bp** (10,000 resamples, seed 42) |
| 95% CI, window-clustered | [−63.16, −11.26] bp |
| Mean net at **2x** cost | **−46.88 bp** |
| Win rate (gross → net) | 45.50% → **44.23%** |
| First-half mean net | **−43.59 bp** |
| Second-half mean net | **−30.31 bp** |
| Worst / best window (mean net) | **−438.80 / +242.07 bp** |
| Worst / best single pair-rebalance | −1,145.59 / +1,592.95 bp |
| Long leg / short leg mean net | **−33.97 / −39.79 bp** |
| Cost haircut (total) | 40,920 bp over 4,092 round trips |
| Best pair | CHFAUD, +1,007.84 bp net |
| Best-pair share of total net | **null** — total net is negative, a share is not interpretable |
| Top-pair share of windows | 1.15% |

Both legs lose money (−34.0 bp long, −39.8 bp short). That matters: the failure is not a directional artifact of the long/short construction, it is that FX 63-day momentum reverses over the following 21 days rather than continuing.

## Null distribution (random cross-sectional ranks, 1,000 shuffles, seed 42)

| Item | Value |
|---|---|
| Null mean, **gross** | **+0.07 bp** |
| Null mean net (at 10 bp) | −9.93 bp |
| Null SD net | 3.49 bp |
| Null 5th / 95th percentile net | −15.74 / **−4.22 bp** |
| Null max net | +1.21 bp |
| **Observed percentile (net)** | **0.0** |
| Empirical p (net) | 1.0 |

The null is centred on ~0 gross, which validates the harness (a random ranking earns nothing before cost). The observed mean is **below every one of the 1,000 shuffles** — the 0th percentile. This is the most important number in the round: the observed result is not merely "not significant", it is worse than random selection, which is the signature of a *reversing* signal.

## Gate-by-gate

| Gate | Requirement | Result | Pass |
|---|---|---|---|
| G1 | 95% CI lower bound > 0 at 1x cost | CI lower = −44.13 bp | **FAIL** |
| G2 | Mean net > 0 at 2x cost | −46.88 bp | **FAIL** |
| G3 | Both halves positive | −43.59 / −30.31 bp | **FAIL** |
| G4 | Observed mean > null 95th percentile | −36.88 bp vs −4.22 bp (0th pct) | **FAIL** |
| G5 | No single pair > 30% of total return | **Not evaluable** (total net negative → share undefined) | n/a |

## Verdict and reasoning

**`KILL`.** The mapping rule is: G1 or G4 fails → KILL. Both fail, and so does G2 and G3. `n = 4,092` is far above the 200-window floor, so this is not `INSUFFICIENT_N`; it is a well-powered, decisively negative result.

The hypothesis is falsified as stated: the strategy does not earn a positive net return after 2x costs, and it does not earn a positive *gross* return either (−26.88 bp before any cost). The random-signal null places the observed result at the 0th percentile, so it is worse than noise, not indistinguishable from it. `PROVEN` is not reachable from a backtest, and nothing here approaches `CANDIDATE` or `WEAK`.

Per the pre-registered stop condition, no parameters were changed after seeing this. The 63-day lookback and 21-day hold are reported exactly as registered. No variant was run and none is reported.

## What this establishes for the program

FOREX momentum at a monthly horizon on G10+ crosses, at a daily fix, is a **reversal** signal, not a continuation signal. Combined with the earlier finding that the FOREX picks sweep was single-pair concentrated and failed at 2x cost, FOREX has now failed on the two mechanisms the program can test with available data. The remaining untested FOREX mechanism is genuinely **carry**, which is blocked until a yield curve exists on disk.
