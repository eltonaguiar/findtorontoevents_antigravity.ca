# Cost-Adjusted Walk-Forward Backtest — Equity Momentum
Generated: 2026-11-15T00:42:23.027977+00:00
Universe: 30 large-cap US equities
Cost per round-trip trade: 20.0 bps
Parameter combos tested: 27 (Bonferroni correction applied)

## Benchmark: SPY buy-and-hold (total return)
- Total return: 359.03%
- Max drawdown: 23.93%
- Sharpe (annualized): 0.9463
- Periods: 142

## Best variant (ranked by profit factor)

| lookback | skip | n_long | PF | WR% | Sharpe | MDD% | Total% | n | tier |
|---|---|---|---|---|---|---|---|---|---|
| 6 | 2 | 3 | 2.9379 | 61.65 | 1.3029 | 29.49 | 3699.12 | 133 | BELOW_T3 |
| 12 | 2 | 3 | 2.7051 | 64.57 | 1.2081 | 31.16 | 2695.31 | 127 | BELOW_T3 |
| 6 | 0 | 3 | 2.6931 | 65.93 | 1.2515 | 35.87 | 3461.37 | 135 | BELOW_T3 |
| 6 | 0 | 5 | 2.6575 | 64.44 | 1.2806 | 25.57 | 1986.16 | 135 | BELOW_T3 |
| 6 | 1 | 3 | 2.6525 | 62.69 | 1.2513 | 27.61 | 3269.4 | 134 | BELOW_T3 |
| 12 | 0 | 8 | 2.6183 | 62.79 | 1.266 | 17.37 | 1021.41 | 129 | TIER_2 |
| 12 | 1 | 3 | 2.6111 | 60.94 | 1.162 | 31.89 | 2247.62 | 128 | BELOW_T3 |
| 9 | 2 | 3 | 2.5745 | 60.77 | 1.1591 | 30.06 | 2274.61 | 130 | BELOW_T3 |

## Multiple-testing honesty
- Raw T2 passes: 4 of 27
- Expected false T2 passes at alpha=0.05: ~1.4
- Best variant is a HYPOTHESIS until forward-tested on unseen data.

## T2 gate (must clear ALL): PF>=1.5, WR>=50%, MDD<=20%, n>=100 (post-cost)
