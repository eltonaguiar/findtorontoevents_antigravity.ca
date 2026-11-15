# PLAN — Commodity / Futures (CTA trend + carry)

**Status:** Research-only. **Gap filled:** F12 (COT+momentum borderline), no pure CTA time-series momentum test.

## Hypothesis
A classic **time-series momentum (TSMOM)** CTA strategy (12-month look-back, long if positive excess return vs cash, short if negative, 1-month hold, vol-targeted at 10% annualized) can produce positive real returns after roll costs across commodity futures, over multiple regimes.

## Gap it fills
- F12 (COT + momentum) failed on significance vs buy-and-hold. TSMOM is the most academically-supported CTA approach (decades of evidence) and has NOT been cleanly tested here.
- Roll cost / contango-backwardation is the specific friction that must be modelled.

## Method
- **Signal:** 12-month excess return vs cash; sign → long/short; vol-target 10% annualized
- **Universe:** 12 liquid commodity futures (energy, metals, ags), continuous contracts
- **Timeframe:** Daily, 2005-01-01 → 2026-11-15
- **Hold:** Monthly rebalance
- **Cost model:** roll cost per contract + 0.02% commission + 0.03% slippage
- **Benchmark:** equal-weight commodity basket (buy-and-hold)

## Proof tests
1. ✅ Temporal (train 2005-2018, test 2019-2026)
2. ✅ WFO 4-year rolling
3. ✅ Multiple testing (1 config)
4. ✅ Monte Carlo (block bootstrap)
5. ✅ Friction (roll + commission + slippage)
6. ✅ Significance (excess return CI vs basket)
7. ✅ Regime (bull/bear commodities, high/low vol)
8. ✅ Shuffle control
9. ✅ Forward (6-month paper)
10. ✅ Reproducibility

## Expected outcome
TSMOM has the strongest academic backing of any active strategy. If it still fails after roll costs, that is a strong negative result — the edge was arbitraged away or the costs are too high.