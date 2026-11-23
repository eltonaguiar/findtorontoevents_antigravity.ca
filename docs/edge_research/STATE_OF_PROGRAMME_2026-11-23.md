# STATE OF THE PROGRAMME — 2026-11-23

**One page for a human with real money. Paper only. Zero capital. Not investment advice.**

## The answer
**Put money in a low-cost broad index ETF. Do not fund any signal in this programme.** Across 10 asset classes
and 69 ranked instruments, **0 pass the five gates and 0 have a positive 95% lower bound on real dated data.**

## Why — the three independent reasons
1. **No edge survives deflation.** Best credible DSR is 0.815 (AUDJPY, n=34) and 0.318 (CVX, n=35) against a 0.95 gate;
   everything else < 0.13. Even `forex_rsi2_mean_reversion` (the only DSR pass at N=61) fails at the honest N=4,987.
2. **Cost eats the rest.** At COST_OF_RECORD, **49/69 picks go net ≤ 0**. Real dated data by class (n=290 of 2,204 —
   the rest are synthetic placeholders): COMMODITY −0.208%/trade, CRYPTO −0.511%, FOREX −0.075%, UNKNOWN −0.514%.
   EQUITY/ETF/BOND have **zero real dated trades**.
3. **The data is thinner and more synthetic than advertised.** 88% of `closed_picks.json` is dateless TP/SL
   placeholders; the EQUITY/ETF universe is survivorship-biased (0 delisted names).

## What is actually defensible (measured)
| Vehicle | 10y cost / $100k | ann. return (2021–26) | corr vs SPY |
|---|---:|---:|---:|
| Direct holdings | ~$50 | — | — |
| **Broad index ETF** | **$1,050** | **+11.59%** (SPY) | 1.00 |
| Index mutual fund (FXAIX) | — | +11.67% | **0.998** |
| Index mutual fund (0.45% MER) | $4,520 | — | — |
| Active mutual fund (~1.85%) | $18,520 | — | — |

Index funds and the ETF are **the same beta (corr 0.995–0.998)** — the only difference is fees, so the fee table decides.
Cash hurdle: SGOV +3.90%/yr.

## The one measurable lever left
The operator's cost claim, quantified: **ETF-grade crypto cost (6.71 bp) instead of 20–52 bp takes net-positive crypto
from 3→12 of 40 and G1-pass from 1→10.** Cost is the binding constraint — but those 12 still fail DSR (0.004–0.13), so
cost buys the *right to ask the deflation question*, not an edge.

## What would change the answer (falsifiable)
1. A strategy with **n ≥ 100 and per-trade Sharpe ≥ 0.50** that keeps its paired CI vs buy-and-hold above zero.
2. **Delisting-aware prices** (so EQUITY/ETF backtests are admissible at all).
3. A **measured venue fee tier** at ETF-grade for the 10 G1-passing crypto rows.
4. Any instrument whose **95% lower bound is positive on real dated trades** — none exists today.

*Files: reports/real_dated_class_verdicts.json, reports/crypto_cost_breakthrough_sensitivity.json, docs/edge_research/DISTANCE_TO_INVESTABLE.md.*
