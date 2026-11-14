# v3 Results

Run: 2026-11-14T18:59:09.539745+00:00 | OOS ≥2024-01-01 | v3 N=8 | cumulative N=20

**0/8 passed all v3 gates — NOT PROVED.**

| Candidate | OOS Sharpe | OOS CAGR | Bench | WF Sharpe | CPCV med | PBO | SPA p | DSR | Lag Sharpe | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| H13_CRYPTO_XS_MOM | -0.18 | -31.9% | -0.01 | 0.78 | 0.62 | 0.59 | 0.488 | 0.014 | -0.07 | NOT_PROVED |
| H14_CRYPTO_XS_REV | -0.36 | -44.3% | -0.01 | 0.49 | 0.62 | 0.59 | 0.488 | 0.006 | -0.45 | NOT_PROVED |
| H15_CRYPTO_TSMOM_BREADTH | 0.20 | -2.9% | 0.06 | 0.66 | 0.62 | 0.59 | 0.488 | 0.059 | 0.03 | NOT_PROVED |
| H16_ETF_XS_MOM | 0.98 | 29.6% | 1.18 | 0.84 | 0.52 | 0.36 | 0.488 | 0.386 | 0.83 | NOT_PROVED |
| H17_ETF_XS_REV | 0.76 | 15.2% | 1.18 | 0.60 | 0.52 | 0.36 | 0.488 | 0.268 | 1.04 | NOT_PROVED |
| H18_ETF_TSMOM_BREADTH | 1.00 | 12.0% | 0.99 | 0.37 | 0.52 | 0.36 | 0.488 | 0.408 | 1.11 | NOT_PROVED |
| H19_COUNTRY_MOM | 0.76 | 16.8% | 0.99 | 0.55 | 0.52 | 0.36 | 0.488 | 0.262 | 0.77 | NOT_PROVED |
| H20_CRYPTO_MOM_BTC_TREND | -0.08 | -21.3% | -0.01 | 1.10 | 0.62 | 0.59 | 0.488 | 0.021 | 0.02 | NOT_PROVED |

## Detail

### H13_CRYPTO_XS_MOM — NOT_PROVED

- OOS: Sharpe -0.18, CAGR -31.9%, maxDD -85.3%, changes 147, exposure 1.00
- Benchmark: Sharpe -0.01, CAGR -22.1%
- Walk-forward: Sharpe 0.78 vs bench 0.67
- CPCV median 0.62; PBO 0.59; SPA p 0.488
- DSR (N=20) 0.014; bootstrap p05 -1.10
- 2x cost Sharpe -0.24; lag 5d Sharpe -0.07
- Failures: oos_sharpe<1.0, not_0.3_above_benchmark, oos_cagr<=0, below_benchmark_return, wf_sharpe<0.8, pbo>=0.5, spa_p>=0.05, dsr<0.95, bootstrap_p05<=0, 2x_cost_fail, execution_lag_fail

### H14_CRYPTO_XS_REV — NOT_PROVED

- OOS: Sharpe -0.36, CAGR -44.3%, maxDD -86.8%, changes 151, exposure 1.00
- Benchmark: Sharpe -0.01, CAGR -22.1%
- Walk-forward: Sharpe 0.49 vs bench 0.67
- CPCV median 0.62; PBO 0.59; SPA p 0.488
- DSR (N=20) 0.006; bootstrap p05 -1.14
- 2x cost Sharpe -0.46; lag 5d Sharpe -0.45
- Failures: oos_sharpe<1.0, not_0.3_above_benchmark, oos_cagr<=0, below_benchmark_return, wf_sharpe<0.8, wf_below_benchmark, pbo>=0.5, spa_p>=0.05, dsr<0.95, bootstrap_p05<=0, 2x_cost_fail, execution_lag_fail

### H15_CRYPTO_TSMOM_BREADTH — NOT_PROVED

- OOS: Sharpe 0.20, CAGR -2.9%, maxDD -63.6%, changes 880, exposure 0.95
- Benchmark: Sharpe 0.06, CAGR -15.7%
- Walk-forward: Sharpe 0.66 vs bench 0.52
- CPCV median 0.62; PBO 0.59; SPA p 0.488
- DSR (N=20) 0.059; bootstrap p05 -0.76
- 2x cost Sharpe 0.11; lag 21d Sharpe 0.03
- Failures: oos_sharpe<1.0, not_0.3_above_benchmark, oos_cagr<=0, wf_sharpe<0.8, pbo>=0.5, spa_p>=0.05, dsr<0.95, bootstrap_p05<=0, 2x_cost_fail, execution_lag_fail

### H16_ETF_XS_MOM — NOT_PROVED

- OOS: Sharpe 0.98, CAGR 29.6%, maxDD -33.3%, changes 24, exposure 1.00
- Benchmark: Sharpe 1.18, CAGR 14.8%
- Walk-forward: Sharpe 0.84 vs bench 0.71
- CPCV median 0.52; PBO 0.36; SPA p 0.488
- DSR (N=20) 0.386; bootstrap p05 0.15
- 2x cost Sharpe 0.97; lag 21d Sharpe 0.83
- Failures: oos_sharpe<1.0, not_0.3_above_benchmark, n_trades<30, spa_p>=0.05, dsr<0.95, 2x_cost_fail, execution_lag_fail

### H17_ETF_XS_REV — NOT_PROVED

- OOS: Sharpe 0.76, CAGR 15.2%, maxDD -18.7%, changes 150, exposure 1.00
- Benchmark: Sharpe 1.18, CAGR 14.8%
- Walk-forward: Sharpe 0.60 vs bench 0.71
- CPCV median 0.52; PBO 0.36; SPA p 0.488
- DSR (N=20) 0.268; bootstrap p05 0.01
- 2x cost Sharpe 0.55; lag 5d Sharpe 1.04
- Failures: oos_sharpe<1.0, not_0.3_above_benchmark, wf_sharpe<0.8, wf_below_benchmark, spa_p>=0.05, dsr<0.95, 2x_cost_fail, execution_lag_fail

### H18_ETF_TSMOM_BREADTH — NOT_PROVED

- OOS: Sharpe 1.00, CAGR 12.0%, maxDD -14.1%, changes 555, exposure 1.00
- Benchmark: Sharpe 0.99, CAGR 9.8%
- Walk-forward: Sharpe 0.37 vs bench 0.61
- CPCV median 0.52; PBO 0.36; SPA p 0.488
- DSR (N=20) 0.408; bootstrap p05 0.31
- 2x cost Sharpe 0.90; lag 21d Sharpe 1.11
- Failures: not_0.3_above_benchmark, wf_sharpe<0.8, wf_below_benchmark, spa_p>=0.05, dsr<0.95, 2x_cost_fail

### H19_COUNTRY_MOM — NOT_PROVED

- OOS: Sharpe 0.76, CAGR 16.8%, maxDD -23.4%, changes 25, exposure 1.00
- Benchmark: Sharpe 0.99, CAGR 16.6%
- Walk-forward: Sharpe 0.55 vs bench 0.56
- CPCV median 0.52; PBO 0.36; SPA p 0.488
- DSR (N=20) 0.262; bootstrap p05 0.03
- 2x cost Sharpe 0.74; lag 21d Sharpe 0.77
- Failures: oos_sharpe<1.0, not_0.3_above_benchmark, n_trades<30, wf_sharpe<0.8, wf_below_benchmark, spa_p>=0.05, dsr<0.95, 2x_cost_fail, execution_lag_fail

### H20_CRYPTO_MOM_BTC_TREND — NOT_PROVED

- OOS: Sharpe -0.08, CAGR -21.3%, maxDD -68.7%, changes 98, exposure 0.62
- Benchmark: Sharpe -0.01, CAGR -22.1%
- Walk-forward: Sharpe 1.10 vs bench 0.67
- CPCV median 0.62; PBO 0.59; SPA p 0.488
- DSR (N=20) 0.021; bootstrap p05 -1.02
- 2x cost Sharpe -0.12; lag 5d Sharpe 0.02
- Failures: oos_sharpe<1.0, not_0.3_above_benchmark, oos_cagr<=0, pbo>=0.5, spa_p>=0.05, dsr<0.95, bootstrap_p05<=0, 2x_cost_fail, execution_lag_fail

## Validation

- PBO crypto 0.59; PBO ETF 0.36
- CPCV median crypto 0.62; ETF 0.52
- Reality Check (SPA) p = 0.488
- Cumulative multiple testing N=20