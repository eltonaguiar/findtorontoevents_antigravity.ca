# H-241 — survivorship envelope for the 44-name book (can H-201 be re-read without the delisting flag?)

**Run:** 2026-11-23 · **Pre-registration:** `plans/2026-11-23-prereg-H-241-survivorship-envelope.md`
(written before the run) · **Artifact:** `reports/h241_survivorship_envelope_2026-11-23.json` ·
**Tool:** `tools/h241_survivorship_envelope.py`

## Answer in one line

The delisting stress costs **1.27 bp/day** at twice the realistic hazard (6%/yr, −50% haircut) — **10% of
the 12.67 bp CI half-width** already in the baseline. Delisting bias is **not** what blocks a verdict for
H-201; **five years of data is.** A delisted-price source would not change the outcome.

## First, the procurement that failed (this is why we bound instead of fix)

A survivorship-free universe needs delisted prices. Both free routes were tested on 2026-11-23:

| source | probe | result |
|---|---|---|
| Yahoo / yfinance, `period="6y"` | 37 known dead tickers (TWTR, ATVI, SGEN, PXD, SIVB, FRC, XLNX, DISH, ANSS, WBA, K, MRO, CTLT, …) | **30 returned no data at all.** The 7 that returned data are *recycled live* tickers (PARA, UNIT, FISV, TMUS, FB, SBNY, BBBY), not delisted histories |
| Stooq CSV (`q/d/l/?s=<sym>.us`) | 7 tickers | HTTP 200 with a **JavaScript proof-of-work challenge** body, not CSV |

So delisted histories are not obtainable free. The flag cannot be removed today; it can only be bounded.

## What was run

H-201's own rule on the 44-name PIT artifact — `xsmom(lookback=126, top_k=3, rebal=21, 10bp/side)`,
SPY benchmark, 2021-11-22 .. 2026-11-19, n=1254 days, 53 rebalances. Synthetic delistings injected at
the rebalance: each **held** name dies with probability `hazard_annual × 21/252`, and earns `haircut`
for that holding period instead of its realised return. 200 seeded paths per cell.

**Baseline reproduction against the published H-236 artifact — not against itself:**

| | n | mean bp/day | CI-LB | CI-UB |
|---|---|---|---|---|
| published H-236 `books.PIT_44` | 1254 | 9.407 | −3.147 | 22.199 |
| this run, hazard 0% | 1254 | **9.407** | **−3.147** | 22.199 |

Exact match on mean and lower bound ⇒ the harness is the same one that produced H-236.

## The envelope

| hazard /yr | haircut | mean bp/day | Δ vs baseline | CI-LB | paths with mean > 0 |
|---|---|---|---|---|---|
| 0% | — | 9.407 | — | **−3.147** | 100% |
| 2% | −30% | 9.133 | −0.274 | −3.437 | 100% |
| 2% | −50% | 8.958 | −0.449 | −3.626 | 100% |
| 2% | −70% | 8.782 | −0.625 | −3.815 | 100% |
| 4% | −50% | 8.503 | −0.904 | −4.006 | 100% |
| **6%** | **−50%** | **8.140** | **−1.267** | −4.469 | 100% |
| 6% | −70% | 7.656 | −1.751 | −4.966 | 100% |
| 10% | −50% | 7.510 | −1.897 | −5.048 | 100% |
| 10% | −70% | 6.763 | −2.644 | −5.794 | 99% |

Realistic US delisting hazard for liquid large caps is ≈1–2%/yr; 6% and 10% are stress corners, not
estimates.

## Verdict — and why the label understates the finding

Per the pre-registered rule: **`NOT_SURVIVES`** — the CI lower bound is ≤ 0 at the 6%/−50% corner.
But **every** cell fails it, including the 0% baseline, whose lower bound is already **−3.147 bp/day**.
The stress is not what breaks the bound; the bound was never above zero.

Read that against the numbers:

- The envelope's **worst** effect (10%/yr, −70%) is −2.644 bp/day. The base rate is 9.407.
- The baseline's own **95% CI half-width is 12.673 bp** — **4.8× the worst-case stress** and 10× the
  pre-registered corner.
- Path means stay positive in 99–100% of the 200 paths in every cell, i.e. the *point estimate* is
  robust to delisting and fragile only to sampling error.

So the honest statement is: **H-201's blocker is a 5-year sample, not the delisting flag.** Buying a
delisted-price source would refine a ±12.7 bp interval by ~1.3 bp. That is the wrong purchase.

Two limits, stated rather than implied:

1. The injection covers names dying **while held**. It does not add dead names to the *selection pool*
   (a name that dies had a chance of being picked before it died). That route needs the delisted prices
   that do not exist here, and it is the larger of the two omissions.
2. The flag stays `BOUNDED` at best. H-241 cannot upgrade anything to `CLEAN`, and 0 of 10 classes are
   investable either way.

## What would actually settle it

Ten years of the 44-name universe would cut the CI half-width roughly in half without touching cost or
survivorship. `reports/pit_equity_universe_20261122.json` is capped at a 5-year window by its own
cached bars, so that is a data-extension job, not a new hypothesis.
