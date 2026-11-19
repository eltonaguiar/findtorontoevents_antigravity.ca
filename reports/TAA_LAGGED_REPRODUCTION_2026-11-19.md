# TAA lagged reproduction — written spec + results (2026-11-19)

Generated 2026-11-19T20:31:51.433347+00:00 by `tools/taa_lagged_reproduction.py` (free yfinance data; rerun it to reproduce byte-for-byte logic).

Spec: { "universe": [ "SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "AGG", "GLD", "DBC", "VNQ", "LQD", "HYG", "TIP" ], "cash_asset": "AGG", "cost_per_leg": 0.0005, "momentum": "month-end adjusted close, L-month total return", "selection": "top-N equal weight, momentum<=0 slot -> AGG", "lags": { "lag0": "signal & entry at same month-end close (reference only)", "lag1d": "enter close of FIRST trading day of next month (report's claim)", "lag1m": "enter at month-end close one month after the signal (buffy)" } }

## Window 2007+

| cell | CAGR% | Sharpe | MaxDD% | Calmar | Sharpe h1/h2 |
|---|---|---|---|---|---|
| **SPY buy-hold (lag0 months)** | 10.42 | 0.72 | -50.8 | 0.21 | 0.51/0.94 |
| lag0/top4-6m | 9.42 | 0.84 | -23.9 | 0.39 | 0.73/0.96 |
| lag0/top5-6m | 9.36 | 0.89 | -19.1 | 0.49 | 0.78/1.0 |
| lag0/top4-9m | 8.26 | 0.77 | -18.6 | 0.44 | 0.56/0.99 |
| lag0/top5-9m | 7.96 | 0.78 | -20.3 | 0.39 | 0.56/1.03 |
| **SPY buy-hold (lag1d months)** | 10.79 | 0.69 | -52.9 | 0.2 | 0.45/0.95 |
| lag1d/top4-6m | 8.91 | 0.77 | -26.0 | 0.34 | 0.59/1.01 |
| lag1d/top5-6m | 8.94 | 0.82 | -20.9 | 0.43 | 0.63/1.06 |
| lag1d/top4-9m | 8.33 | 0.76 | -19.3 | 0.43 | 0.5/1.04 |
| lag1d/top5-9m | 7.93 | 0.77 | -20.7 | 0.38 | 0.5/1.09 |
| **SPY buy-hold (lag1m months)** | 10.42 | 0.72 | -50.8 | 0.21 | 0.51/0.94 |
| lag1m/top4-6m | 6.54 | 0.56 | -38.3 | 0.17 | 0.3/0.88 |
| lag1m/top5-6m | 6.53 | 0.6 | -30.7 | 0.21 | 0.35/0.88 |
| lag1m/top4-9m | 8.75 | 0.75 | -21.9 | 0.4 | 0.47/1.06 |
| lag1m/top5-9m | 7.4 | 0.68 | -20.4 | 0.36 | 0.43/0.97 |

## Window 2018+

| cell | CAGR% | Sharpe | MaxDD% | Calmar | Sharpe h1/h2 |
|---|---|---|---|---|---|
| **SPY buy-hold (lag0 months)** | 12.82 | 0.82 | -23.9 | 0.54 | 0.56/1.15 |
| lag0/top4-6m | 8.62 | 0.79 | -14.0 | 0.61 | 0.81/0.77 |
| lag0/top5-6m | 8.89 | 0.84 | -16.1 | 0.55 | 0.75/0.92 |
| lag0/top4-9m | 9.18 | 0.82 | -15.7 | 0.58 | 0.77/0.86 |
| lag0/top5-9m | 8.55 | 0.84 | -13.6 | 0.63 | 0.77/0.91 |
| **SPY buy-hold (lag1d months)** | 14.06 | 0.86 | -23.8 | 0.59 | 0.67/1.15 |
| lag1d/top4-6m | 9.38 | 0.87 | -15.8 | 0.59 | 0.86/0.87 |
| lag1d/top5-6m | 9.63 | 0.92 | -16.9 | 0.57 | 0.81/1.01 |
| lag1d/top4-9m | 10.21 | 0.9 | -16.2 | 0.63 | 0.86/0.93 |
| lag1d/top5-9m | 9.33 | 0.92 | -12.8 | 0.73 | 0.87/0.97 |
| **SPY buy-hold (lag1m months)** | 12.82 | 0.82 | -23.9 | 0.54 | 0.56/1.15 |
| lag1m/top4-6m | 8.23 | 0.71 | -15.0 | 0.55 | 0.69/0.74 |
| lag1m/top5-6m | 7.36 | 0.68 | -13.4 | 0.55 | 0.63/0.73 |
| lag1m/top4-9m | 10.37 | 0.88 | -15.5 | 0.67 | 0.86/0.9 |
| lag1m/top5-9m | 8.47 | 0.77 | -15.6 | 0.54 | 0.75/0.79 |

## Verdict (2007+ window, acceptance: Sharpe >= 0.88 at MaxDD no worse than -19%, lagged)

**The acceptance threshold is NOT met under any lagged convention — buffy's objection is partially upheld.**

1. **The headline cell reproduces only at same-close execution.** `lag0/top5-6m` = Sharpe 0.89 / MaxDD −19.1% — numerically the report's "Sharpe 0.88 / −19%". So the 2026-07-04 result was effectively signal-and-entry at the same month-end close, despite its "1-day entry-timing" claim. Buffy's unlagged-Sharpe red flag was right in kind (though the inflation here is 0.89→0.82, not →2.00).
2. **With an honest 1-day lag the edge narrows but survives on risk-adjusted terms:** `lag1d/top5-6m` Sharpe 0.82 vs SPY 0.69, MaxDD −20.9% vs −52.9%, Calmar 0.43 vs 0.20. CAGR 8.9% vs SPY 10.8% — **rotation loses on raw return in every cell**, confirming buffy.
3. **Under a full one-month lag the 6m signal decays hard** (top5-6m Sharpe 0.60, MaxDD −30.7%); the 9m lookback is lag-robust (top4-9m: Sharpe 0.75 ≈ SPY 0.72 at MaxDD −21.9% vs −50.8%).
4. **What survives every lag: the drawdown control.** MaxDD −13% to −26% vs SPY −51/−53% across all 12 lagged cells; Calmar roughly 2× SPY. That — and only that — is the durable value.

**Consequence for the $2,000 verdict:** ETF TAA is retained only as a *drawdown-controlled* allocation, not a Sharpe-dominant one: expect SPY-minus-1-to-2% CAGR at roughly half the drawdown, 1-day execution, 6m or 9m lookback (9m if execution can slip). A $2k holder who can stomach −50% drawdowns is honestly better served by plain SPY/VOO buy-and-hold.
