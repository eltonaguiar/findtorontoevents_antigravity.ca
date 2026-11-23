# What a human should actually buy — CORRECTED

**Date:** 2026-11-23 · **Supersedes:** `FUNDS_WHAT_TO_BUY_2026-11-23.md` (Kilo's original)
**Tool:** `tools/fund_deep_dive.py` (schema v2) · **Data:** adjusted closes 2021-11-15 → 2026-11-13, 1,254 daily returns
**Branch:** `feat/fund-deep-dive-fixes-2026-11-23`

> **Paper only. Not investment advice.** Beta/buying analysis, not an edge claim.
> Past five years, bull-heavy, taxes not modelled. Reproduce: `python3 tools/fund_deep_dive.py --anchors`

---

## Errata — what the first review got wrong

The peer review (subq) was **directionally right but 4 of 12 claims were false**. Each was
checked against the code or the data, not taken on assertion.

| Review claim | Verdict | Evidence |
|---|---|---|
| Code is markdown-mangled, cannot run | **REFUTED** | `py_compile` clean; reproduces every number. The garbling was transcript rendering. |
| "Fee gap over-predicts the FXAIX−SPY gap" | **REFUTED — unit error** | Compared **5-year** fee drag (0.40pp) to the **per-year** gap (0.17pp). Same units: 0.17pp/yr ≈ 0.85pp over 5y **>** 0.40pp. The gap *exceeds* the fee, not the reverse. |
| "No tax drag modelled" | **REFUTED** | The original had a dedicated §"The mutual-fund catch": capital-gains distributions, taxable vs registered. |
| "No minimums / practicality" | **REFUTED** | Original covered $0 / $3,000 / fractional shares. |

The review also **missed four real defects**, fixed here: the Sortino denominator, the additive
net-CAGR, the population stdev, and the Python ≥3.11 dependency.

## Errata — what the original document got wrong

| # | Original claim | Correction |
|---|---|---|
| 1 | "Sharpe 0.728" for FXAIX, "0.714" SPY | Those were `(μ−MER)/σ`, **not Sharpe**. True excess-of-cash: **0.457** and **0.443**. |
| 2 | SGOV Sharpe 15.886 | Undefined. Emitted as `null` now. |
| 3 | 60/40 at 7.05%, "monthly rebalance" | The code rebalanced **daily**; `rebal` was ignored. True monthly: **6.91%**. |
| 4 | "FXAIX net CAGR +0.17pp higher — durable" | The **gross** advantage **flips sign** between halves (+0.099 → −0.021). Only the **fee** is durable. |
| 5 | "60/40 gives up return for a shallower hole" | True **trailing**, but BND's forward **YTM is 4.11%**, not −0.29%. On current yields bonds are expected to *contribute*, which changes the forward case. |

---

## The measured table (corrected)

Cash hurdle **R_f = 3.81%/yr** (SGOV trailing net CAGR).

| instrument | MER | net CAGR | vol | Sharpe | Sortino | max DD |
|---|---:|---:|---:|---:|---:|---:|
| **Fidelity 500 Index (FXAIX)** MF | 0.015% | 11.66% | 17.2% | **0.457** | 0.652 | **−24.5%** |
| **SPDR S&P 500 (SPY)** ETF | 0.0945% | 11.48% | 17.3% | **0.443** | 0.634 | **−24.5%** |
| Fidelity ZERO Total Mkt (FZROX) MF | 0.00% | 10.74% | 17.6% | 0.393 | 0.560 | −25.12% |
| Vanguard Total Mkt (VTI) ETF | 0.03% | 10.49% | 17.7% | 0.379 | 0.539 | −25.36% |
| Vanguard Total Stock (VTSAX) MF | 0.04% | 10.48% | 17.6% | 0.379 | 0.539 | −25.36% |
| **Vanguard Total Bond (BND)** ETF | 0.03% | -0.32% | 6.1% | **−0.680** | −0.932 | **−17.31%** |
| **iShares 0-3mo T-bill (SGOV)** ETF | 0.09% | 3.81% | 0.2% | **n/a (cash)** | n/a | **−0.03%** |

Note how the correction bites: BND's Sharpe goes from a harmless −0.02 to **−0.68** — over the
window it destroyed value *against cash*, which the original table hid.

## Precision — the point estimates are far less certain than they look

Moving-block bootstrap (21-day blocks, 1,000 draws, fixed seed), 90% intervals on CAGR:

| fund | CAGR | 90% CI |
|---|---:|---|
| SPY | 11.59% | **[−0.10, 24.92]** |
| FXAIX | 11.67% | **[0.01, 25.02]** |
| FZROX | 10.74% | [−1.07, 24.39] |
| VTI | 10.53% | [−1.34, 24.09] |
| VTSAX | 10.52% | [−1.36, 24.03] |
| BND | −0.29% | [−4.75, 4.17] |
| SGOV | 3.90% | [3.57, 4.27] |

Equity CAGR intervals span ~25 percentage points. **Ranking equity funds on 5-year CAGR is not
supported by this data.** Only the cash series is tight.

## Does a mutual fund beat the ETF? — the honest answer

Paired bootstrap on the *difference* series (the correct test; separate intervals prove nothing
for two near-identical series):

| pair | gross | fee advantage | **net** | distinguishable from zero? |
|---|---:|---:|---:|---|
| FXAIX − SPY | +0.051 | +0.0795 | **+0.131** | **No** |
| FZROX − VTI | +0.192 | +0.0300 | +0.222 | No |
| VTI − VTSAX | +0.013 | +0.0100 | +0.023 | No |

Split in half:

| FXAIX − SPY | gross | net | distinguishable? |
|---|---:|---:|---|
| H1 (2021-11 → 2024-11) | +0.099 | **+0.178** | No |
| H2 (2024-11 → 2026-11) | **−0.021** | **+0.059** | No |

**The defensible claim:** the fee edge (0.0795pp/yr) is contractual and keeps the *net* gap
positive in both halves. The *realised* outperformance is noise and changed sign mid-window. You
cannot demonstrate FXAIX "beat" SPY from this data — you can only show it is cheaper.

## Risk — rebalancing matters, and not in the direction expected

60/40 SPY/BND, 5bp spread on the traded fraction:

| schedule | CAGR | vol | Sharpe | max DD | turnover |
|---|---:|---:|---:|---:|---:|
| **buy & hold** | **7.45%** | 11.66% | **0.306** | −20.92% | 0.00 |
| daily (1d) | 7.03% | 11.17% | 0.282 | −20.59% | 2.28 |
| monthly (21d) | 6.91% | 11.09% | 0.273 | −20.73% | 0.45 |
| quarterly (63d) | 6.78% | 11.04% | 0.262 | −20.87% | 0.17 |

The review predicted daily rebalancing would *overstate* a 60/40 via volatility harvesting. In
this window the **opposite** held: more frequent rebalancing **lowered** return, because it kept
buying a falling bond sleeve. The harvesting effect is real but its **sign depends on the relative
performance of the sleeves** — it is not a free lunch.

The reviewer's arithmetic concern is fair and worth stating explicitly: the measured table shows
**geometric** net CAGRs (FXAIX 11.66% − SPY 11.48% = 0.18pp), while the paired table shows the
**arithmetic** annualised mean of the daily difference series (0.131pp). These are different
estimands and are not expected to match:

- geometric CAGRs: $(V_T/V_0)^{1/T} - 1$, compounded
- paired figure: $\overline{r_A - r_B} \times 252$, an arithmetic average

The paired figure is the right one for "is the difference distinguishable from zero", because it
bootstraps the *difference* series and the two legs are near-perfectly correlated — resampling each
fund separately would badly overstate the uncertainty. The geometric table is the right one for "what
would I have earned". Neither is wrong; quoting one against the other is.

## Forward anchors (current, not trailing)

Fetched 2026-11-23 via `--anchors`:

- **Cash (13-week T-bill, ^IRX): 4.12%** as of 2026-11-20 — vs 3.81% trailing SGOV
- **BND yield-to-maturity: 4.11%** — vs −0.29% trailing CAGR

**This is the single largest correction.** BND's forward expectation is ≈ +4.1%/yr. The original
"60/40 gives up return" conclusion rests on a trailing window dominated by a rate-hike bond bear
market. On current yields a bond sleeve is expected to *add* return, so the forward case for 60/40
is materially stronger than the trailing numbers imply.

## Futures — explicitly out of scope

The request mentioned futures. They are **not** analysed, and adjusted closes are the wrong input
for them: a continuous futures series embeds roll assumptions that a share-price series does not,
and the relevant economics (roll yield, contango/backwardation, margin, financing) are absent from
this dataset. Doing this properly needs front-month settlements and roll dates. **Out of scope —
requires contract-level data.** Treat any futures conclusion from this dataset as invalid.

## Decision table

| vehicle | type | MER | minimum | tax efficiency (taxable) | fractional | best fit |
|---|---|---:|---|---|---|---|
| FZROX | index MF | 0.00% | $0 (US Fidelity only) | low (can distribute gains) | n/a (MF) | max-cost-efficiency, registered |
| FXAIX | index MF | 0.015% | $0 | low | n/a (MF) | core S&P 500 holding |
| VTSAX | index MF | 0.04% | $3,000 | low | n/a (MF) | total market, Vanguard |
| VTI | ETF | 0.03% | 1 share | **high** (in-kind) | usually | total market, taxable |
| SPY | ETF | 0.0945% | 1 share | high | usually | liquidity/trading, not buy-and-hold |
| BND | ETF | 0.03% | 1 share | high | usually | bond sleeve |
| SGOV | ETF | 0.09% | 1 share | high | usually | cash parking |

## Bottom line

1. **Order of decision:** account wrapper (taxable vs registered) → then vehicle. Not the reverse.
2. **Core holding:** broad low-cost index. Same beta everywhere; choose the lowest total cost you can actually access.
3. **MF vs ETF is a tax-and-minimum question, not a return question.** The fee edge is real (~0.08pp/yr); the return edge is unmeasurable here.
4. **Risk:** 100% equity returned ~11.5%/yr with a −24.5% drawdown. If you cannot hold through that, a 60/40 is defensible — and on *current* yields more defensible than the trailing numbers suggest.
5. **Do not rank funds on 5-year CAGR.** The intervals overlap almost completely.

## What would change this answer

- Cash falling well below ~2% (raises the equity hurdle back to favourable)
- A sustained drop in the net gap making the fee advantage negative
- Dividend reinvestment turning out to be *not* reflected in the adjusted closes (would invalidate every CAGR here — plan item L1, still open)
- A tax regime where MF capital-gains distributions exceed the fee edge (plan items E2–E6, needs jurisdiction)

## Still open

Plan: `docs/edge_research/FUND_DEEP_DIVE_TODO_2026-11-23.md` (173 items, 15 sections).
Blocked on operator input: **E3/E4/E5/E6** (jurisdiction — Canadian vs US account wrapper) and
**G3–G7** (futures contract-level data). Peer review of *these* corrected numbers (J1–J5, M1–M5) has
not yet been run.
