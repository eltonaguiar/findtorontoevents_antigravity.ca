# Questions Addendum — 12 More, Focused on Benchmarks and Fees

**Date:** 2026-11-15 · **Author:** Buffy
Extends `2026-11-15_1227AM_profitability/buffy/04_questions/ESSENTIAL_QUESTIONS.md` (Q1–Q15).
Those fifteen asked *"is the number real?"*. These twelve ask *"is it better than doing nothing?"*.

The previous set's blind spot was exactly what you flagged: it never forced a comparison against the
S&P 500 or against buy-and-hold. Q16–Q19 fix that.

---

## Benchmark-relative

**Q16. What is your benchmark, and is exposure matched?**
A 60%-invested strategy compared to 100% SPY is measuring cash drag, not skill. Build the benchmark at
`exposure × index + (1−exposure) × cash`.
*Repo state:* ❌ never done for any class.

**Q17. What is your excess return at matched exposure, after costs?**
`EDGE = annualised(Rp) − annualised(Rb_matched) − costs`. This is the only number that answers "should
I just buy the index?"
*Repo state:* ❌ zero of five classes benchmarked.

**Q18. How much of your return is beta?**
Report β and R². If R² > 0.8 against SPY, you are selling index exposure with extra steps.
*Repo state:* ❌ not computed.

**Q19. What is your down-capture?**
A strategy that participates fully in drawdowns while capturing 80% of rallies is a fee, not an edge.
Gate: down-capture < 100, capture ratio > 1.0.
*Repo state:* ❌ never computed.

## Fee and structure

**Q20. Are you a taker or a maker?**
On Kalshi/Polymarket this is decisive: makers pay **0** plus a 15–25% rebate; takers pay
`0.07 × P × (1−P)`, i.e. **3.5% of stake at 50¢** and **6.3% at 10¢**.
*Repo state:* the code treats both venues as generic price sources; side is not recorded.

**Q21. What edge do you need just to break even at your price point?**
Solve the fee curve at your own entry price before claiming a forecasting edge. At 50¢ you need >3.5%
of stake. A 2-point calibration edge does not clear it.
*Repo state:* ❌ fee never enters any P&L.

**Q22. Is your asset class even recorded separately?**
Prediction markets have **no class in the ledger** — their picks are tagged CRYPTO (32 rows). A class
that isn't recorded can never be verdicted.
*Repo state:* ❌ confirmed structural gap.

**Q23. What is your turnover, and does it violate platform limits?**
Mutual funds: 30-day frequent-trading limits. ETFs: spread + ER. FX: rollover/swap. Crypto: funding.
High turnover plus a per-trade fee is a guaranteed negative regardless of signal quality.
*Repo state:* ❌ turnover not modelled.

## Statistical honesty

**Q24. How many trials produced this, and is your DSR computed at that count?**
361 registered strategies. At α=0.05 that is ~18 expected false positives. A DSR at N=38 (the Nov-14
plan's threshold) understates the correction by roughly 10×.
*Repo state:* ❌ DSR absent entirely.

**Q25. What happens when you double the costs?**
If the edge dies at 2× costs, it dies at the first wide spread. This is the cheapest robustness test
available and almost nobody runs it.
*Repo state:* ❌ not done.

**Q26. Does the edge survive a one-bar delay?**
Same-bar fills are a latency claim, not an edge. Shift entry forward one bar; if the edge vanishes, it
was never executable.
*Repo state:* threshold defined in the Nov-14 plan, never applied.

**Q27. Would this survive on a different venue and data vendor?**
Reproduce on a second source. One-vendor edges are often vendor artefacts — the repo already has
CADJPY at 611.23 vs entry 115.77 and USDJPY at 1.358 vs entry 158.58, which are feed errors, not wins.
*Repo state:* ❌ no cross-vendor check.

---

## Scoreboard

| Group | Questions | Repo can answer |
|---|---|---|
| Benchmark-relative (Q16–Q19) | 4 | **0** |
| Fee/structure (Q20–Q23) | 4 | 0 (one confirmed structural gap) |
| Statistical honesty (Q24–Q27) | 4 | 0 |
| **Total new** | **12** | **0** |

Combined with Q1–Q15 (4 answerable), the repo can answer **4 of 27** essential questions.

## The three that would change the most, cheapest

1. **Q17** — compute excess vs matched-exposure benchmark for EQUITY and ETF. Two days of work; it either
   justifies the research or ends it.
2. **Q25** — double the costs on every existing strategy. A single script, no new data.
3. **Q22** — give prediction markets a class. Then at least the failure becomes measurable.
