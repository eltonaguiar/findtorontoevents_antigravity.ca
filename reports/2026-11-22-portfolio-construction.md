# Portfolio construction: risk allocation is second-order, and the error bars say so

**Date:** 2026-11-22 · **Owner:** buffy · **Items:** E31, E33, E34, E35
**Tool:** `tools/risk_parity_vs_6040.py` · **Raw:** `reports/portfolio/risk_parity_2026-11-22.json`
**Tests:** `tests/test_risk_parity_vs_6040.py` (7, passing)
**Window:** 2006-03-31 → 2026-11-30, **249 months**, monthly rebalance, 5 bp/unit turnover
**Risk-free:** `^IRX`/12. Every Sharpe and CE below is excess over that.

## The question this block was built to answer

The per-class sweep found 0 cells clearing every gate, and the vol-matched check found the one
near-pass goes negative when scaled to the benchmark. So selection cannot beat the benchmark.
The last lever that needs no new alpha is **how the same assets are weighted**. Four candidates
were tested against plain 60/40.

## The table (full sample, 249 months)

| strategy | CAGR % | vol % | Sharpe | MDD % (month-end) | CE % |
|---|---|---|---|---|---|
| 60/40 static | 7.91 | 10.28 | 0.630 | −28.45 | **5.95** |
| equal weight 4 | 6.89 | 9.78 | 0.559 | −24.91 | 4.99 |
| risk parity (inverse vol, 12m) | 7.08 | 9.45 | 0.611 | −17.15 | 5.32 |
| **risk parity (ERC, 24m)** | 8.55 | 10.52 | 0.701 | −17.31 | **6.82** |
| **HRP (36m)** | 8.25 | **8.87** | **0.779** | −17.79 | **6.52** |
| ERC @ 10 bp | 8.50 | 10.52 | 0.696 | −17.32 | 6.77 |
| HRP @ 10 bp | 8.22 | 8.87 | 0.775 | −17.80 | 6.48 |
| 60/40 + vol target 10% | 8.71 | 11.18 | 0.655 | **−33.72** | 6.69 |
| ERC + vol target 10% | 9.20 | 10.93 | 0.734 | −20.49 | 7.42 |
| HRP + vol target 10% | **9.33** | 11.16 | 0.729 | −21.27 | **7.51** |

On the point estimates, HRP+VT "beats" 60/40 by **1.56 pp of CE**. That is the number a
careless write-up would publish. It is not supported.

## The paired bootstrap kills every claim in the table

CE is a nonlinear function of two moments, so a point estimate cannot carry a claim about a
*difference*. 5,000 paired month-resamples, both CEs restated on the common window:

| vs 60/40 | common n | CE (strat) | CE (60/40) | diff | 90% CI | verdict |
|---|---|---|---|---|---|---|
| ERC | 225 m | 6.82 | 6.45 | +0.36 | [−2.71, +3.40] | includes 0 |
| HRP | 213 m | 6.52 | 8.44 | **−1.93** | [−4.82, +0.93] | includes 0 |
| HRP + VT | 213 m | 7.51 | 8.44 | **−0.93** | [−4.38, +2.61] | includes 0 |
| ERC + VT | 225 m | 7.42 | 6.45 | +0.97 | [−2.66, +4.56] | includes 0 |
| 60/40 + VT | 249 m | 6.69 | 5.95 | +0.75 | [−0.90, +2.39] | includes 0 |

**Zero of five.** Not one allocation beats 60/40 on certainty equivalent in a way the data can
distinguish from noise. The verdict field in the artifact is gated on this, not on the point
estimate, and a test enforces that gate.

## Three findings that matter more than the ranking

**1. The window moves the answer more than the allocation does.** 60/40's own CE is **5.95** on
the full 249 months, **8.44** on the 213-month common window, and **6.45** on 225 months — a
**2.49 pp swing** from nothing but the choice of end date. That is larger than every
point-estimate difference in the table except HRP's −1.93. Any claim of the form "allocation X
beats 60/40" is therefore smaller than the uncertainty about *which 60/40 you mean*.

**2. HRP's full-sample advantage is one regime, not a property.** HRP shows CE 6.52 against
60/40's 5.95 over 249 months, but **6.52 against 8.44 over the 213 months both series exist** —
it *loses* by 1.93 pp on the common window. The entire apparent advantage comes from the final
~36 months, when 60/40 was hurt by the bond drawdown. What HRP genuinely delivers is robust and
visible in every row: **vol 8.87 vs 10.28** and **MDD −17.79 vs −28.45**. Lower risk, not higher
return — and the difference must be sold as risk, never as alpha.

**3. Cost is irrelevant at this layer, which is itself informative.** Moving 5 bp → 10 bp shifts
ERC's CE from 6.82 to 6.77 and HRP's from 6.52 to 6.48. Portfolio construction trades roughly
monthly, so it is **not where the programme's cost problem lives** — that remains entirely in the
per-class sleeves, where a single round trip costs 12–43 bp.

## E34 — the combined book, and the trap in optimising it

A long-only max-CE solve over all four assets, given the full-sample means (**in-sample, the most
favourable possible setting**) returns:

**SPY 81.44%, GLD 18.56%, TLT 0.00%, DBC 0.00%.**

It zeroes **TLT**, whose correlation to SPY is **−0.079** — the single most valuable correlation
in a 60/40 and the entire reason the portfolio exists. That is **error maximisation in mean
returns**, not a finding about diversification: the optimiser is handed TLT's *realised* excess
return over a rate-hiking era and dutifully discards the hedge. The risk-based allocators never
see expected returns, keep TLT, and deliver lower vol and a drawdown 11 pp shallower.

So the honest combined book is **risk-allocated, not return-optimised**. And the failed per-class
sleeves still get zero under every method — they have neither positive excess return nor a useful
correlation, so no weighting scheme rescues them.

Correlation matrix used (monthly, 249 months): SPY/TLT **−0.079**, SPY/GLD **+0.103**,
SPY/DBC **+0.448**, TLT/DBC **−0.318**, TLT/GLD **+0.241**, GLD/DBC **+0.314**.

## A correction to my own earlier vol-targeting claim

I previously reported vol targeting as real risk control: 60/40 VT gave CE 8.87 vs 7.55 and
**MDD −22.37 vs −31.42** on daily data, 2005-01 → 2026-11. At **monthly** granularity on this
window the CE gain survives (**+0.75 pp**, though CI includes 0) but the **drawdown benefit
reverses: −33.72 vs −28.45**. The cause is legible: 2006-07 realised vol was ~7%, so a 10% target
levers the book **~1.4×** *into* 2008, and a monthly-updating rule de-levers a month at a time.

**Corrected statement: vol targeting's return benefit is granularity-robust; its drawdown
benefit is not.** The earlier daily result stands as measured, but "VT reduces drawdown" is not
a general property of the rule and must not be quoted without its rebalance frequency.

## E35 — what to actually hold, with the error bars attached

Paper only. Zero capital. Not advice.

1. **A diversified, low-cost core.** Nothing in this programme earned a place beside it: 0 of 40
   per-class cells cleared every gate, and 0 of 5 weighting schemes beat plain 60/40 with a CI
   excluding zero.
2. **Prefer risk allocation over return optimisation**, not because it wins on CE (it does not,
   measurably) but because return optimisation deletes the diversifier as an artefact of one
   sample, and that failure is structural rather than statistical.
3. **Expect the differences between sensible cores to be unmeasurable.** The spread between the
   best and worst sensible core here is ~2.5 pp of CE; 60/40's own window sensitivity is 2.49 pp.
   Anyone quoting a ranking finer than that is quoting noise.
4. **Do not size any per-class sleeve** until something has a positive CI on excess return after
   cost. Nothing does.
5. **The vol-target caveat travels with the number:** state the rebalance frequency, every time.

What would change this: a sleeve with a positive CI on excess return after measured cost. That is
the only thing that turns portfolio construction from second-order into first-order.
