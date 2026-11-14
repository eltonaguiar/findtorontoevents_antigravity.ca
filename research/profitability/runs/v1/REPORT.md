# v1 Results

Run: 2026-11-14T18:34:40.633841+00:00 | train ≤2023-12-31 | OOS ≥2024-01-01 | N=7

## Verdict

**0 candidates passed all gates — NOT PROVED.**

| Candidate | OOS Sharpe | OOS CAGR | Bench Sharpe | OOS changes | DSR | p | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| H1_BTC_TSMOM200 | 0.60 | 16.5% | 0.56 | 29 | 0.360 | 0.307 | NOT_PROVED |
| H2_ETH_TSMOM200 | 0.47 | 11.5% | 0.22 | 21 | 0.277 | 0.43 | NOT_PROVED |
| H3_XS_CRYPTO_MOM28_TOP3 | -0.00 | -19.2% | 0.22 | 125 | 0.082 | 0.996 | NOT_PROVED |
| H4_CRYPTO_RSI2 | 0.06 | -4.6% | 0.34 | 245 | 0.099 | 0.922 | NOT_PROVED |
| H5_ETF_DUAL_MOM | 0.99 | 16.2% | 0.99 | 6 | 0.624 | 0.0925 | NOT_PROVED |
| H6_BTC_VOLSCALED_TSMOM | 0.55 | 14.1% | 0.56 | 613 | 0.329 | 0.348 | NOT_PROVED |
| H7_EQUITY_RSI2 | 1.50 | 17.6% | 1.02 | 111 | 0.948 | 0.011 | NOT_PROVED |

## Per-candidate detail

### H1_BTC_TSMOM200 — NOT_PROVED

- Train: Sharpe 0.93 | CAGR 37.0% | maxDD -64.0% | PF 1.23 | changes 33 | exposure 0.47
- OOS: Sharpe 0.60 | CAGR 16.5% | maxDD -31.7% | PF 1.12 | changes 29 | exposure 0.61
- Benchmark OOS: Sharpe 0.56 | CAGR 16.7% | maxDD -53.0% | PF 1.09 | changes 0 | exposure 0.00
- Bootstrap OOS: p05 -0.36, p95 1.67
- 2x cost OOS Sharpe: 0.57
- Failures: oos_sharpe<1.0, not_0.3_above_benchmark, below_benchmark_return, n_trades<30, dsr<0.95, bootstrap_p05<=0, pbo>=0.5

### H2_ETH_TSMOM200 — NOT_PROVED

- Train: Sharpe 0.97 | CAGR 50.2% | maxDD -73.7% | PF 1.24 | changes 27 | exposure 0.50
- OOS: Sharpe 0.47 | CAGR 11.5% | maxDD -41.8% | PF 1.10 | changes 21 | exposure 0.48
- Benchmark OOS: Sharpe 0.22 | CAGR -7.3% | maxDD -67.6% | PF 1.03 | changes 0 | exposure 0.00
- Bootstrap OOS: p05 -0.59, p95 1.44
- 2x cost OOS Sharpe: 0.45
- Failures: oos_sharpe<1.0, not_0.3_above_benchmark, n_trades<30, dsr<0.95, bootstrap_p05<=0, 2x_cost_fail, pbo>=0.5

### H3_XS_CRYPTO_MOM28_TOP3 — NOT_PROVED

- Train: Sharpe 1.16 | CAGR 106.6% | maxDD -83.6% | PF 1.24 | changes 200 | exposure 0.92
- OOS: Sharpe -0.00 | CAGR -19.2% | maxDD -82.5% | PF 1.00 | changes 125 | exposure 1.00
- Benchmark OOS: Sharpe 0.22 | CAGR -5.9% | maxDD -69.1% | PF 1.03 | changes 0 | exposure 0.00
- Bootstrap OOS: p05 -1.04, p95 1.27
- 2x cost OOS Sharpe: -0.06
- Failures: oos_sharpe<1.0, not_0.3_above_benchmark, oos_cagr<=0, below_benchmark_return, dsr<0.95, bootstrap_p05<=0, 2x_cost_fail, pbo>=0.5

### H4_CRYPTO_RSI2 — NOT_PROVED

- Train: Sharpe -0.38 | CAGR -30.6% | maxDD -91.1% | PF 0.89 | changes 423 | exposure 0.26
- OOS: Sharpe 0.06 | CAGR -4.6% | maxDD -38.2% | PF 1.02 | changes 245 | exposure 0.28
- Benchmark OOS: Sharpe 0.34 | CAGR 2.3% | maxDD -64.3% | PF 1.05 | changes 0 | exposure 0.00
- Bootstrap OOS: p05 -0.65, p95 0.90
- 2x cost OOS Sharpe: -0.17
- Failures: oos_sharpe<1.0, not_0.3_above_benchmark, oos_cagr<=0, below_benchmark_return, dsr<0.95, bootstrap_p05<=0, 2x_cost_fail, pbo>=0.5

### H5_ETF_DUAL_MOM — NOT_PROVED

- Train: Sharpe 0.35 | CAGR 4.0% | maxDD -25.2% | PF 1.07 | changes 18 | exposure 1.00
- OOS: Sharpe 0.99 | CAGR 16.2% | maxDD -19.0% | PF 1.20 | changes 6 | exposure 1.00
- Benchmark OOS: Sharpe 0.99 | CAGR 9.8% | maxDD -11.9% | PF 1.20 | changes 0 | exposure 0.00
- Bootstrap OOS: p05 0.22, p95 1.95
- 2x cost OOS Sharpe: 0.98
- Failures: oos_sharpe<1.0, not_0.3_above_benchmark, n_trades<30, dsr<0.95, 2x_cost_fail

### H6_BTC_VOLSCALED_TSMOM — NOT_PROVED

- Train: Sharpe 0.94 | CAGR 28.5% | maxDD -45.6% | PF 1.24 | changes 1003 | exposure 0.36
- OOS: Sharpe 0.55 | CAGR 14.1% | maxDD -31.2% | PF 1.11 | changes 613 | exposure 0.61
- Benchmark OOS: Sharpe 0.56 | CAGR 16.7% | maxDD -53.0% | PF 1.09 | changes 0 | exposure 0.00
- Bootstrap OOS: p05 -0.46, p95 1.67
- 2x cost OOS Sharpe: 0.51
- Failures: oos_sharpe<1.0, not_0.3_above_benchmark, below_benchmark_return, dsr<0.95, bootstrap_p05<=0, 2x_cost_fail, pbo>=0.5

### H7_EQUITY_RSI2 — NOT_PROVED

- Train: Sharpe 0.46 | CAGR 4.7% | maxDD -17.9% | PF 1.22 | changes 204 | exposure 0.16
- OOS: Sharpe 1.50 | CAGR 17.6% | maxDD -7.7% | PF 2.00 | changes 111 | exposure 0.17
- Benchmark OOS: Sharpe 1.02 | CAGR 18.6% | maxDD -21.0% | PF 1.21 | changes 0 | exposure 0.00
- Bootstrap OOS: p05 0.96, p95 2.13
- 2x cost OOS Sharpe: 1.33
- Failures: below_benchmark_return, dsr<0.95

## Multiple testing

```json
{
  "n": 7,
  "bonferroni_alpha": 0.0071428571428571435,
  "bonferroni_reject": [],
  "bh_reject": [],
  "pvalues": {
    "H1_BTC_TSMOM200": 0.307287410369383,
    "H2_ETH_TSMOM200": 0.43030338499624143,
    "H3_XS_CRYPTO_MOM28_TOP3": 0.9956003007390406,
    "H4_CRYPTO_RSI2": 0.9222104735183108,
    "H5_ETF_DUAL_MOM": 0.09246876394356529,
    "H6_BTC_VOLSCALED_TSMOM": 0.3482928625449102,
    "H7_EQUITY_RSI2": 0.010961556000469663
  }
}
```

PBO (crypto candidates): 0.9045066045066045
PBO (ETF candidates): nan