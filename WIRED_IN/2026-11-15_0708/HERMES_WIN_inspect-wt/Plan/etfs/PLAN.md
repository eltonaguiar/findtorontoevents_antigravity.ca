# PLAN — ETF Tactical

**Status:** Research-only. **Gap filled:** ETF class has sparse coverage; no clean tactical test.

## Hypothesis
A **dual momentum** strategy across major ETFs (SPY, QQQ, IWM, EFA, VTI, BND, GLD) — absolute momentum (10-month SMA filter) + relative momentum (12-1) — produces positive excess return vs SPY total return after costs.

## Gap it fills
ETF class has zero live picks; SPY sometimes miscategorized as equity. This plan is the first clean tactical ETF test.

## Method
- **Signal:** if 10-month SMA > 0, go long top-3 by 12-1 momentum; else go to cash (or short-duration bonds)
- **Universe:** 7 major ETFs
- **Timeframe:** Daily, 2005-2026
- **Hold:** Monthly rebalance
- **Cost model:** 0.03% taker fee + 0.02% slippage
- **Benchmark:** SPY total return

## Proof tests
1. ✅ Temporal (2005-2018 / 2019-2026)
2. ✅ WFO (4-year)
3. ✅ Multiple testing (1 config)
4. ✅ Monte Carlo (bootstrap)
5. ✅ Friction (taker + slippage)
6. ✅ Significance (excess vs SPY)
7. ✅ Regime (bull/bear/sideways)
8. ✅ Shuffle control
9. ✅ Forward (12-month paper)
10. ✅ Reproducibility

## Expected outcome
Dual momentum has a long track record (Antonacci, Faber). If it fails after costs, that is a strong negative result — the edge was arbitraged away.