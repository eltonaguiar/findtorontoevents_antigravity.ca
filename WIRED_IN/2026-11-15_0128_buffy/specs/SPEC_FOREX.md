# Algorithm Specification — FOREX

**Agent:** buffy (Codebuff) · **Date:** 2026-11-15
**Status:** `NOT MEASURED — NO RULE SUBMITTED, NO RULE CLAIMED`

---

## 1. Why there is no measured forex rule

I did not run a forex backtest in this study, and I am not going to present one from memory. The reason
is not lack of interest: it is that the cheapest defensible forex test needs data this repo does not
have wired into a clean series.

| Requirement | Status |
|---|---|
| Spot mid-price history for a G10 basket | Not present in the backtest data cache |
| Interest-rate differentials (for carry) | Not present; `^IRX` is USD-only |
| Rollover/swap cost model | Not present — and this is the entire carry P&L |
| Execution model for 24/5 with weekend gaps | Not present |

Without the rate differentials, a "carry" backtest is really a spot-momentum backtest wearing a carry
label. That mistake is common enough in this repo's category that it is worth refusing to repeat.

---

## 2. What the repo's forex numbers do and do not say

- The ledger has **472 FOREX rows**, PF 1.16 as previously reported.
- PF is not an excess return. It has never been computed against a benchmark for this class
  (`03_benchmark_relative/BENCHMARK_GATES.md` §5).
- **472 rows across an unknown number of currency pairs and an unknown window** is not a sample of
  independent bets; it is a count of records. PF 1.16 on that basis is not evidence of an edge.

So the class status is **unknown, not positive**.

---

## 3. The spec that would be required (design only, not run)

If forex is to be tested, this is the minimum viable specification:

| Element | Value |
|---|---|
| Benchmark | **T-bill cash (risk-free)** — FX has no natural long-only premium |
| Universe | G10 majors, spot only |
| Signal (carry) | 3-month rate differential, ranked; long top 3, short bottom 3, monthly |
| Signal (momentum) | 12-month total return, same ranking |
| Costs | Spread (0.5–2 bps majors) + **rollover** per night, signed by side |
| Sizing | Volatility-scaled so each leg contributes equal risk; otherwise the JPY leg dominates |
| Gate | Excess vs cash > 0 after rollover, IR ≥ 0.5, DSR ≥ 0.95 |

**The critical detail:** for a carry strategy, the rollover *is* the return. A backtest that ignores
swap is not conservative — it is measuring something else entirely.

---

## 4. Elimination

Eliminated at the **data** stage, before any signal was tested: no rule can be honestly evaluated
without rate differentials and a swap model. That is a cheaper elimination than running a
mis-specified backtest and then arguing about it.

Recorded in `ELIMINATION_LOG.md` §3. To re-admit: supply the rate series and swap model, then the design
above can be run as a pre-registered trial with its own DSR correction.
