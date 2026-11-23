# Corrected class verdict — ALL rows vs dated-only (net of COST_OF_RECORD)

**Date:** 2026-11-23T08:30Z · **Author:** Kilo · Paper only.
Source: `alpha_engine/data/closed_picks.json` on **origin/main** (505 rows). Machine: `reports/class_verdict_all_vs_dated.json`.

Following my own filter-bias finding, every class is now reported on **both** populations; **ALL-rows is the honest
class-level number** (dated-only drops the more-negative dateless rows).

| class | cost RT | ALL n | **ALL net/trade** | dated n | dated net/trade |
|---|---:|---:|---:|---:|---:|
| BOND | 0.61 bp | 2 | **+0.014%** | 0 | — |
| ETF | 6.71 bp | 16 | **−0.047%** | 0 | — |
| FOREX | 7.53 bp | 169 | **−0.131%** | 115 | −0.076% |
| EQUITY | 12.07 bp | 8 | **−0.148%** | 1 | −0.130% |
| COMMODITY | 20 bp | 102 | **−0.213%** | 85 | −0.209% |
| STOCKS | 12.07 bp | 14 | **−0.455%** | 0 | — |
| UNKNOWN | 52 bp | 47 | **−0.506%** | 47 | −0.506% |
| CRYPTO | 20–52 bp | 140 | **−0.515%** | 16 | −0.505% |
| FUTURES | 20 bp | 6 | **−0.540%** | 0 | — |
| CHEAP_STOCKS | 12.07 bp | 2 | −0.611% | 0 | — |

## The corrected verdict
**On ALL rows after measured cost, every class is net-negative except BOND at +0.014% on n=2** (a breakeven T-bill,
i.e. noise — the cash hurdle, not a pick). For the classes with real samples (FOREX 169, CRYPTO 140, COMMODITY 102) the
losses are **−0.13%, −0.52%, −0.21% per trade**. ETF/STOCKS have zero dated rows, so their "signal" is unmeasurable.

This is the honest version of the earlier table, and it is **worse, not better**: excluding dateless rows had flattered
FOREX by 5.5 bp and made several classes look closer to breakeven than they are.

**0 investable, now on the conservative population.** A low-cost broad index ETF remains the only defensible action.

*Paper only. Not investment advice.*
