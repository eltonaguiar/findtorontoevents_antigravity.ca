# v2 Results

Run: 2026-11-14T18:36:05.092879+00:00 | OOS ≥2024-01-01 | v2 N=5 | cumulative N=12

**0 candidates passed all gates — NOT PROVED.**

| Candidate | OOS Sharpe | OOS CAGR | Bench Sharpe | Bench CAGR | changes | DSR | p | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| H8_SECTOR_RSI2_CASH | 1.16 | 17.2% | 1.09 | 13.5% | 409 | 0.603 | 0.0495 | NOT_PROVED |
| H9_INTL_RSI2_CASH | 0.31 | 4.1% | 0.90 | 15.1% | 346 | 0.128 | 0.595 | NOT_PROVED |
| H10_CORE_RSI2_CASH | 1.83 | 22.0% | 1.02 | 18.6% | 111 | 0.978 | 0.00194 | PASSED_GATES |
| H11_SECTOR_RSI2_TREND_CASH | 1.04 | 11.5% | 1.09 | 13.5% | 361 | 0.529 | 0.078 | NOT_PROVED |
| H12_SECTOR_MOM12_TOP3_CASH | 1.14 | 16.7% | 1.09 | 13.5% | 22 | 0.589 | 0.0549 | NOT_PROVED |

## Detail

### H8_SECTOR_RSI2_CASH — NOT_PROVED

- Train: Sharpe -0.14 | CAGR -5.0% | maxDD -54.5% | PF 0.96 | changes 701 | exposure 0.49
- OOS: Sharpe 1.16 | CAGR 17.2% | maxDD -10.4% | PF 1.31 | changes 409 | exposure 0.60
- Benchmark OOS: Sharpe 1.09 | CAGR 13.5% | maxDD -16.5% | PF 1.22 | changes 0 | exposure 0.00
- Bootstrap OOS: p05 0.54, p95 2.07
- 2x cost OOS Sharpe: 0.66
- DSR (cumulative N=12): 0.603
- Failures: not_0.3_above_benchmark, dsr<0.95, 2x_cost_fail

### H9_INTL_RSI2_CASH — NOT_PROVED

- Train: Sharpe 0.19 | CAGR 1.9% | maxDD -47.3% | PF 1.05 | changes 698 | exposure 0.48
- OOS: Sharpe 0.31 | CAGR 4.1% | maxDD -23.9% | PF 1.08 | changes 346 | exposure 0.51
- Benchmark OOS: Sharpe 0.90 | CAGR 15.1% | maxDD -16.6% | PF 1.17 | changes 0 | exposure 0.00
- Bootstrap OOS: p05 -0.36, p95 1.42
- 2x cost OOS Sharpe: -0.02
- DSR (cumulative N=12): 0.128
- Failures: oos_sharpe<1.0, not_0.3_above_benchmark, below_benchmark_return, dsr<0.95, bootstrap_p05<=0, 2x_cost_fail

### H10_CORE_RSI2_CASH — PASSED_GATES

- Train: Sharpe 0.60 | CAGR 6.4% | maxDD -15.8% | PF 1.29 | changes 204 | exposure 0.16
- OOS: Sharpe 1.83 | CAGR 22.0% | maxDD -7.7% | PF 2.24 | changes 111 | exposure 0.17
- Benchmark OOS: Sharpe 1.02 | CAGR 18.6% | maxDD -21.0% | PF 1.21 | changes 0 | exposure 0.00
- Bootstrap OOS: p05 1.27, p95 2.59
- 2x cost OOS Sharpe: 1.66
- DSR (cumulative N=12): 0.978
- Failures: none

### H11_SECTOR_RSI2_TREND_CASH — NOT_PROVED

- Train: Sharpe -0.31 | CAGR -3.2% | maxDD -34.0% | PF 0.91 | changes 534 | exposure 0.25
- OOS: Sharpe 1.04 | CAGR 11.5% | maxDD -9.6% | PF 1.30 | changes 361 | exposure 0.41
- Benchmark OOS: Sharpe 1.09 | CAGR 13.5% | maxDD -16.5% | PF 1.22 | changes 0 | exposure 0.00
- Bootstrap OOS: p05 0.36, p95 2.05
- 2x cost OOS Sharpe: 0.57
- DSR (cumulative N=12): 0.529
- Failures: not_0.3_above_benchmark, below_benchmark_return, dsr<0.95, 2x_cost_fail

### H12_SECTOR_MOM12_TOP3_CASH — NOT_PROVED

- Train: Sharpe 0.67 | CAGR 12.4% | maxDD -30.7% | PF 1.13 | changes 35 | exposure 1.00
- OOS: Sharpe 1.14 | CAGR 16.7% | maxDD -18.1% | PF 1.22 | changes 22 | exposure 1.00
- Benchmark OOS: Sharpe 1.09 | CAGR 13.5% | maxDD -16.5% | PF 1.22 | changes 0 | exposure 0.00
- Bootstrap OOS: p05 0.40, p95 2.03
- 2x cost OOS Sharpe: 1.11
- DSR (cumulative N=12): 0.589
- Failures: not_0.3_above_benchmark, n_trades<30, dsr<0.95

## Validation

- PBO (v2 ETF candidates): 0.23885003885003886
- PBO (all 12 candidates, common calendar): 0.10637140637140637
- Cumulative multiple testing: `{"n": 12, "bonferroni_alpha": 0.004166666666666667, "bonferroni_reject": ["H10_CORE_RSI2_CASH"], "bh_reject": ["H10_CORE_RSI2_CASH"], "pvalues": {"H8_SECTOR_RSI2_CASH": 0.04951568710994603, "H9_INTL_RSI2_CASH": 0.5950736683275601, "H10_CORE_RSI2_CASH": 0.0019409326181145659, "H11_SECTOR_RSI2_TREND_CASH": 0.07802968751784545, "H12_SECTOR_MOM12_TOP3_CASH": 0.05487882076260009, "H1_BTC_TSMOM200": 0.307287410369383, "H2_ETH_TSMOM200": 0.43030338499624143, "H3_XS_CRYPTO_MOM28_TOP3": 0.9956003007390406, "H4_CRYPTO_RSI2": 0.9222104735183108, "H5_ETF_DUAL_MOM": 0.09246876394356529, "H6_BTC_VOLSCALED_TSMOM": 0.3482928625449102, "H7_EQUITY_RSI2": 0.010961556000469663}}`