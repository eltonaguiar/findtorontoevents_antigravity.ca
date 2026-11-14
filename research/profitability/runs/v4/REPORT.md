# v4 Results — Crypto Funding Carry

Run: 2026-11-14T19:02:54.345962+00:00 | train 2020-01-01..2023-12-31 | OOS ≥2024-01-01 | cumulative N=23

**0/3 passed all v4 gates — NOT PROVED.**

| Candidate | OOS Sharpe | OOS CAGR | Cap/1.5 CAGR | Cash CAGR | WF Sharpe | DSR | 2x Sharpe | Lag Sharpe | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| H21_FUNDING_TOP5 | 6.42 | 5.6% | 3.7% | 4.5% | 7.03 | 1.000 | 1.72 | 5.99 | NOT_PROVED |
| H22_FUNDING_BTC | 14.24 | 7.2% | 4.8% | 4.5% | 10.04 | 1.000 | 11.20 | 14.02 | NOT_PROVED |
| H23_FUNDING_TOP10 | 8.34 | 6.2% | 4.1% | 4.5% | 7.59 | 1.000 | 3.93 | 7.83 | NOT_PROVED |

## Detail

### H21_FUNDING_TOP5 — NOT_PROVED

- OOS: Sharpe 6.42, CAGR 5.6%, maxDD -0.8%, changes 134, exposure 1.00
- Cash benchmark OOS: CAGR 4.5%; capital-adjusted CAGR 3.7% (capital x1.5)
- Walk-forward: Sharpe 7.03
- DSR (N=23) 1.000; bootstrap p05 4.55
- 2x cost Sharpe 1.72; 5-day lag Sharpe 5.99
- Failures: capital_adjusted_cagr<=cash

### H22_FUNDING_BTC — NOT_PROVED

- OOS: Sharpe 14.24, CAGR 7.2%, maxDD -0.3%, changes 10, exposure 0.91
- Cash benchmark OOS: CAGR 4.5%; capital-adjusted CAGR 4.8% (capital x1.5)
- Walk-forward: Sharpe 10.04
- DSR (N=23) 1.000; bootstrap p05 11.92
- 2x cost Sharpe 11.20; 5-day lag Sharpe 14.02
- Failures: n_trades<30

### H23_FUNDING_TOP10 — NOT_PROVED

- OOS: Sharpe 8.34, CAGR 6.2%, maxDD -0.5%, changes 142, exposure 1.00
- Cash benchmark OOS: CAGR 4.5%; capital-adjusted CAGR 4.1% (capital x1.5)
- Walk-forward: Sharpe 7.59
- DSR (N=23) 1.000; bootstrap p05 6.84
- 2x cost Sharpe 3.93; 5-day lag Sharpe 7.83
- Failures: capital_adjusted_cagr<=cash
