# PLAN — Bond / Fixed Income

**Status:** Ballast research (not alpha). **Gap filled:** F-bond never tested; yield-curve/credit-spread timing is sparse.

## Hypothesis
A **yield-curve steepener/flattener** signal (2s10s spread vs 3-month moving average) on Treasury futures produces positive excess return after costs across rate regimes.

## Gap it fills
Bond class has n=35 in final_v3 — far below any significance floor. This plan is deliberately low-frequency (monthly) to accumulate trades slowly without over-fitting.

## Method
- **Signal:** 2s10s spread crossing its 3-month MA → long/short Treasury futures (TU/ZN)
- **Universe:** US Treasury futures (2yr, 5yr, 10yr)
- **Timeframe:** Daily, 2006-2026
- **Hold:** Monthly rebalance
- **Cost model:** exchange fees + bid-ask spread + accrued interest
- **Benchmark:** Bloomberg Agg total return (proxied)

## Proof tests
1. ✅ Temporal (2006-2018 / 2019-2026)
2. ✅ WFO (4-year)
3. ✅ Multiple testing (1 config)
4. ✅ Monte Carlo (bootstrap)
5. ✅ Friction (exchange + spread + accrued)
6. ✅ Significance (excess vs agg)
7. ✅ Regime (rate-hike / cut / flat)
8. ✅ Shuffle control
9. ✅ Forward (12-month paper — bonds are slow)
10. ✅ Reproducibility

## Expected outcome
Bonds are mostly beta + duration. This is ballast, not an alpha source. Expected: marginal or negative after costs; document honestly.