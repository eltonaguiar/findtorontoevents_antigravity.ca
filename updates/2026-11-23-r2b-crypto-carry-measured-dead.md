# R2b — crypto funding/carry measured: 3.07% net vs a 4.32% hurdle. DEAD.

**Date:** 2026-11-23
**Tool:** `tools/crypto_funding_carry_measure.py`
**Artifact:** `reports/crypto_funding_carry.json`
**Plan row:** R2b of `notes/per-asset-class-plan-copilot-2026-11-23`

---

## The claim this replaces

`alpha_engine/funding_rate_arb.py` opens with:

> *"Research: Funding rate arbitrage yields 5-15% monthly with very low risk."*

5–15% **monthly** is **60–180% annualised**. That is an imported magnitude of exactly the
kind this programme has banned. The archive we already held was enough to measure it.

## The measurement

`data/funding_rate_archive/*.jsonl` — 8-hourly funding from OKX, **5 symbols**, **4,235
intervals**, **218 days** (≈7 months).

| Symbol | n | Gross ann. yield | % intervals positive | p05 | cum. funding | cum. worst DD |
|---|---|---|---|---|---|---|
| BNBUSDT | 847 | 4.53% | 71% | −7.15e−05 | 3.50% | −0.12% |
| BTCUSDT | 847 | 4.39% | 82% | −3.83e−05 | 3.40% | −0.11% |
| ETHUSDT | 847 | 3.32% | 77% | −4.84e−05 | 2.57% | −0.15% |
| SOLUSDT | 847 | 2.26% | 65% | −8.96e−05 | 1.75% | −0.40% |
| XRPUSDT | 847 | 3.36% | 71% | −8.50e−05 | 2.60% | −0.34% |

**Pooled (equal weight):**

| | |
|---|---|
| Gross annual yield | **3.57%** |
| Round-trip cost (2 legs × 2 sides × 12.6 bp) | 0.50% |
| **Net annual yield** | **3.07%** |
| Hurdle | **4.32%** |
| Intervals positive | 73.3% |
| Worst cumulative funding drawdown | −0.40% |

## Verdict: DEAD, and not because of cost

Net **3.07%** against a **4.32%** hurdle — fails by **1.25 percentage points**, and it
fails **gross-minus-nothing** too once you account for the fact that gross is only 3.57%.
Cost (0.50%) is not the deciding term here; the funding stream itself is too thin.

Against the asserted claim: measured gross is **~17× to ~50× below** the 5–15%
*monthly* range. The number in that docstring was never a measurement of anything we hold.

## Why this is the right metric, and what it deliberately omits

Funding carry is a **short-volatility** trade: it pays steadily and loses sharply when
funding flips negative during a deleveraging. So the deciding statistics are
**percentage of intervals positive (73.3%)** and **worst cumulative drawdown**, not
Sharpe. Both are reported.

**Not modelled, and stated rather than assumed away:**
- basis drift between spot and perp,
- liquidation/venue risk in a deleveraging event,
- leverage, which scales the yield *and* the drawdown.

The −0.40% drawdown is reassuring **only because 218 days is a benign window**. A single
deleveraging week would dwarf it. Do not read a small MaxDD here as "low risk" — that is
the same error as reading a high Sharpe on a strategy that sells tail risk.

## What would reopen it

- A **multi-year** archive including at least one deleveraging period (2021-05, 2022-05,
  2022-11). 218 days cannot distinguish "carry pays 3.6%" from "carry pays 3.6% in a
  quiet stretch".
- Basis/spread history so the *realised* delta-neutral return can be computed instead of
  the funding yield.

## Effect on the plan

R2b moves from **CANDIDATE** to **DEAD**. The 02:05Z plan called it "the only crypto track
whose ledger we do NOT already know to be broken" — that is now tested, and it fails on
its own numbers. Crypto therefore has **no live candidate** in any sub-row.

Zero capital sanctioned. Not investment advice.
