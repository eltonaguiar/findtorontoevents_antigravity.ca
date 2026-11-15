# PLAN — Forex (FX)

**Status:** Blocked. **Gap filled:** F13 (FX carry+trend, spread erodes edge).

## Hypothesis
A **carry + momentum combination** on major FX pairs (EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CHF) with strict cost model can produce positive excess return vs cash after 0.1% round-turn spread.

## Gap it fills
F13 died on friction model. This plan explicitly models maker-taker rebates and tests whether the edge survives at *retail* spread (not institutional).

## Method
- **Signal:** rank pairs by interest-rate differential (carry) + 20-day momentum; long top 2, short bottom 2
- **Universe:** 5 major pairs
- **Timeframe:** Daily, 2010-2026
- **Hold:** Weekly rebalance
- **Cost model:** 0.1% spread + 0.02% commission + 0.03% slippage
- **Benchmark:** cash (T-bill rate)

## Proof tests
1. ✅ Temporal (2010-2018 / 2019-2026)
2. ✅ WFO (4-year)
3. ✅ Multiple testing (1 config)
4. ✅ Monte Carlo (bootstrap)
5. ✅ Friction (spread + commission + slippage)
6. ✅ Significance (excess vs cash)
7. ✅ Regime (risk-on / risk-off / high vol)
8. ✅ Shuffle control
9. ✅ Forward (6-month paper)
10. ✅ Reproducibility

## Expected outcome
If F13's pattern holds, this will also fail after costs. That is a legitimate negative result — the honest verdict is "no edge in FX at retail spread".