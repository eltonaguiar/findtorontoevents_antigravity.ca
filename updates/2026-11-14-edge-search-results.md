# Edge Search v1–v4 — Can a Profitable Approach Be Proven?

**Date:** 2026-11-14
**Question:** given the audit verdict (NOT profitable / NOT statistically sound), does any simple, honest, publicly-testable rule survive out-of-sample, costs, a random-entry null, and multiple-testing correction?

**Answer: no. 0 of 40 trials pass.** The two closest candidates fail the null test.

---

## Method (pre-committed)

| Element | Choice |
|---|---|
| Data | Binance spot daily klines, 10 majors (BTC, ETH, SOL, BNB, XRP, ADA, AVAX, LINK, DOGE, LTC), 2021-01-01 → 2026-11-14 (2,144 bars each) |
| Funding data | Binance USD-M `fundingRate`, 4,794–4,869 points per symbol, 2022-07-01 → 2026-11-14 |
| In-sample | 2021-01-01 → 2024-06-30 |
| Out-of-sample | 2024-07-01 → 2026-11-14 (untouched during design) |
| Costs | 10 bps per side (20 bps round trip) for price strategies; 16 bps round trip for delta-neutral carry |
| Execution | signal from bar `t-1`, return from bar `t` (no look-ahead) |
| Null model | random entries with the **same count and holding-period distribution**; empirical p over 250–1,000 iterations |
| Multiple testing | cumulative trial count across all versions; Bonferroni threshold 0.05/40 = 1.25e-3; DSR with N = cumulative trials |
| Pass criteria | OOS PF > 1.2, n ≥ 30, null p < 0.05, DSR > 0.95 |

**Benchmark:** equal-weight buy-and-hold over the same OOS window returned **−23.2% with a 68.5% max drawdown**. Any long-only strategy in this window looks good simply by avoiding that drawdown — which is exactly what the random-entry null is designed to detect.

---

## v1 — 15 configs, first pass

| Config | IS PF | OOS PF | OOS WR | OOS Sharpe | OOS n | OOS total | null p | DSR | Pass |
|---|---|---|---|---|---|---|---|---|---|
| rsi2 (10/60/10) | 1.26 | 1.49 | 60.7% | 0.43 | 496 | +22.0% | 0.139 | 0.005 | ✗ |
| tsmom 90d long | 1.92 | 1.28 | 37.1% | 0.22 | 167 | +2.5% | 0.474 | 0.000 | ✗ |
| tsmom 30d long | 2.85 | 1.41 | 43.5% | 0.21 | 405 | +2.5% | 0.506 | 0.000 | ✗ |
| xsmom 90d top-2 | 2.34 | 1.04 | 36.5% | 0.12 | 63 | +1.6% | 0.522 | 0.000 | ✗ |
| tsmom 180d long | 2.17 | 0.78 | 30.0% | −0.12 | 140 | −27.9% | 0.841 | 0.000 | ✗ |
| xsmom 90d long/short | 1.35 | 0.88 | 41.3% | −0.38 | 167 | −11.7% | 0.984 | 0.000 | ✗ |

Signal: every in-sample PF above 1.8 decayed to ≤1.4 out-of-sample, and no null p came near 0.05.

## v2 — regime filters, vol targeting, residual momentum (12 configs)

| Config | IS PF | OOS PF | OOS WR | OOS Sharpe | OOS n | OOS total | MDD | null p | DSR |
|---|---|---|---|---|---|---|---|---|---|
| rsi2 + BTC>200d, 5/60/15 | 1.18 | **2.24** | 63.6% | **0.70** | 129 | **+25.3%** | 15.9% | 0.112 | 1.000 |
| rsi2 + BTC>200d, 10/60/10 | 1.22 | 1.67 | 58.9% | 0.49 | 219 | +18.9% | 18.9% | 0.170 | 0.638 |
| rsi2 unfiltered | 1.27 | 1.49 | 60.7% | 0.43 | 496 | +22.0% | 29.6% | 0.135 | 0.040 |
| xsmom + BTC filter 30d | 1.98 | 1.18 | 40.0% | 0.39 | 70 | +12.5% | 20.5% | 0.284 | 0.118 |
| residual momentum 30d | 1.55 | 1.13 | 37.5% | 0.16 | 120 | +2.9% | 28.7% | 0.608 | 0.000 |
| vol-targeted TSMOM 90d | 1.67 | 1.11 | 35.3% | 0.11 | 167 | −0.4% | 32.9% | 0.611 | 0.000 |

The BTC regime filter roughly halved the drawdown and doubled PF — but the null test improved only from p=0.135 to p=0.112. **Most of the gain is drawdown avoidance, not timing skill.**

## v3 — pairs stat-arb (3) and funding carry (6)

Pairs: top-5 IS-correlated pairs (SOL/BNB 0.88, BTC/ETH 0.87, BTC/BNB 0.77, ETH/BNB 0.74, BTC/SOL 0.73), 60-day z-score, exit |z|<0.5, 30-day max hold.

| Entry z | n | WR | PF | Sharpe | Total | MDD |
|---|---|---|---|---|---|---|
| 1.5 | 121 | 57.9% | 0.77 | −0.71 | −26.1% | 39.9% |
| 2.0 | 87 | 54.0% | 0.82 | −0.47 | −16.6% | 32.0% |
| 2.5 | 54 | 37.0% | 0.50 | −1.16 | −28.8% | 35.7% |

**All negative after 20 bps.** Consistent with the peer-replicated finding that crypto cross-sectional/pairs edges do not survive realistic costs.

Carry (delta-neutral, funding income only, 16 bps round trip):

| Config | IS ann | OOS ann | OOS Sharpe | OOS total | MDD | null p (run-preserving) |
|---|---|---|---|---|---|---|
| 7d signal, thr 0 | 7.20% | **1.82%** | 4.56 | +4.4% | 1.8% | **1.000** |
| 3d signal, thr −5e-5 | 5.78% | 0.40% | 0.85 | +1.0% | 3.7% | 1.000 |
| 7d signal, thr 1e-4 | 6.09% | −0.20% | −0.49 | −0.5% | 3.5% | 1.000 |

**Two findings here matter more than the table:**
1. The headline Sharpe of 11.4 (always-on carry) is an artifact of funding having near-zero volatility — the honest number is **annual net return ~3.8%, below T-bills**, matching the 2026 literature that the level carry trade has decayed.
2. My first null (random shuffle of positions) gave a fake p=0.002 because shuffling changes turnover. The corrected **run-length-preserving block null gives p=1.000** — the 7-day signal adds nothing over simply being exposed. The strategy's apparent quality was entirely the funding level, not the filter.

## v4 — 365-day trend, high-resolution null

| Config | IS Sharpe | OOS Sharpe | OOS total | OOS MDD | null p |
|---|---|---|---|---|---|
| TSMOM 365d, vol-target 40%, monthly | 0.57 | **0.57** | +31.7% | 27.4% | **0.200** (600 iters) |
| TSMOM 365d long/short | −0.06 | 0.31 | +11.7% | 36.2% | — |
| TSMOM 365d, vol-target 60% | 0.53 | 0.52 | +33.0% | 35.2% | — |
| RSI2 5/60/15 + regime | 0.04 | 0.70 | +25.3% | 15.9% | **0.080** (1,000 iters) |

TSMOM 365d is the most *stable* result (IS ≈ OOS Sharpe 0.57, average exposure 32%), which is what a real trend premium should look like. But random entries with the same exposure and holding periods matched it 20% of the time. **Stability ≠ significance.**

---

## Cumulative outcome

| Metric | Value |
|---|---|
| Total trials across v1–v4 | **40** |
| Bonferroni threshold | 1.25e-3 |
| Trials passing null p < 0.05 | **0** |
| Trials passing null p < 0.05 **and** DSR > 0.95 | **0** |
| Best null p | 0.080 (RSI2 + regime) |
| Expected false positives at α=0.05 with 40 trials under the null | ~2 |

At 40 trials, seeing a p≈0.08 result is entirely expected under the null. Publishing the RSI2 variant as "an edge" would repeat exactly the error the audit identified in the live system.

---

## What this does and does not prove

**Proves:** these five families — single-asset trend, cross-sectional momentum, residual momentum, RSI(2) mean reversion, correlated-pair reversion, funding-level carry — do not produce a statistically defensible edge on 10 large-cap crypto pairs with daily bars and realistic costs, over a 2.4-year untouched OOS window.

**Does not prove:** that no edge exists anywhere. Specifically untested or weakly tested:
- Cross-sectional **funding** carry (rank funding across venues/contracts rather than trade the level) — published net Sharpe ≈0.4, thin but positive.
- Intrabar resolution (my labels use daily closes; first-touch ordering can move PF materially).
- A survivorship-free universe (my 10 symbols all still trade — a real bias, and it flatters every long-only result).
- Perp-spot basis P/L and liquidation tails in the carry test (funding-only approximation).
- Options volatility risk premium, on-chain/flow signals, cross-venue dislocations.

---

## Recommended next research step (highest expected value)

**Build the cross-sectional funding-carry book on real perp data**, because it is the only family in the literature that survives costs *and* is orthogonal to the price rules that just failed:
1. Universe: all Binance USD-M perps with ≥1 year of funding history, survivorship-inclusive.
2. Signal: funding rank (not level), dollar-neutral long/short perp basket, weekly rebalance.
3. Costs: 16 bps round trip + basis slippage; model liquidation tail explicitly.
4. Gate: the same 40-trial-corrected DSR/PBO/null battery used here.
5. Pre-register the hypothesis (M-107) **before** the first backtest.

Expected honest outcome from the literature: net Sharpe ≈0.4, i.e. tradable only with leverage discipline and a large sample — not a retail edge, but the first defensible candidate.
