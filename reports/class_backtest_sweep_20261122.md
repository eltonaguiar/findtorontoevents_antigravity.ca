# Class backtest sweep — 20261122

Population: `closed_at IS NOT NULL AND pnl_pct IS NOT NULL AND status NOT IN ('OPEN','ABANDONED','FLAT','FORCE_CLOSED_TOXIC') AND closed_at > '2026-01-01' AND DATE(closed_at) != '2026-06-04' AND pnl_pct BETWEEN -100 AND 100`. Folds 5, embargo 2, 2000 seeded resamples. **Backtest rows only: the ceiling is CANDIDATE.**

| class | n | WR | gross PF | net PF | 2x PF | net mean | median | CI-LB | h1 | h2 | WF folds + | worst | top sym | top date | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CRYPTO | 11007 | 0.4391 | 1.0462 | 0.9917 | 0.9404 | -0.0156 | -0.0996 | -0.1334 | -0.0177 | -0.0136 | 2/5 | -100.0996 | ETHUSDT 6% | 4% | **WEAK** |
| FOREX | 8041 | 0.4217 | 1.501 | 1.0629 | 0.8008 | 0.004 | -0.02 | -0.0033 | -0.0181 | 0.026 | 2/5 | -12.15 | USDJPY=X 13% | 41% | **WEAK** |
| COMMODITY | 1506 | 0.2829 | 0.6202 | 0.5219 | 0.4455 | -0.5206 | -0.1582 | -0.6638 | -0.221 | -0.8201 | 0/5 | -30.29 | SI=F 23% | 16% | **KILL** |
| EQUITY | 1224 | 0.3954 | 0.9931 | 0.939 | 0.8885 | -0.0561 | -0.05 | -0.2068 | -0.2518 | 0.1396 | 2/5 | -30.26 | AAPL 13% | 43% | **WEAK** |
| UNCATEGORIZED | 149 | 0.4698 | 0.7414 | 0.6626 | 0.5929 | -0.4414 | -0.2557 | -0.8314 | -0.3163 | -0.5648 | 0/5 | -11.44 | SPY 20% | 10% | **KILL** |
| MEME | 102 | 0.3725 | 0.9237 | 0.8188 | 0.7278 | -0.493 | -0.3 | -2.2517 | 0.2757 | -1.2616 | 3/5 | -75.3 | DOGE 23% | 23% | **WEAK** |
| ETF | 79 | 0.4177 | 1.5737 | 1.4974 | 1.4256 | 0.4436 | -0.0778 | -0.266 | 0.9892 | -0.0885 | 0/0 | -6.14 | QQQ 18% | 11% | **INSUFFICIENT_N** |
| BOND | 77 | 0.2597 | 0.8074 | 0.6959 | 0.605 | -0.1169 | -0.42 | -0.2931 | -0.1488 | -0.0859 | 0/0 | -1.26 | TLT 27% | 14% | **INSUFFICIENT_N** |
| FUTURES | 70 | 0.3 | 1.0627 | 0.9432 | 0.842 | -0.0496 | -0.275 | -0.5608 | 0.178 | -0.2773 | 0/0 | -8.67 | NQ=F 26% | 10% | **INSUFFICIENT_N** |
| INDEX | 25 | 0.28 | 0.3919 | 0.2634 | 0.1846 | -0.3535 | -0.12 | -0.688 | -0.2974 | -0.4054 | 0/0 | -3.03 | NQ=F 40% | 20% | **INSUFFICIENT_N** |
| MUTUAL_FUND | 0 | — | — | — | — | — | — | — | — | — | 0/0 | — | — | —% | **NO_ROWS** |
| PENNY_STOCK | 0 | — | — | — | — | — | — | — | — | — | 0/0 | — | — | —% | **NO_ROWS** |

## Per-class walk-forward folds

- **CRYPTO**: f1 n1832 mean -0.2824 PF 0.8971, f2 n1832 mean 0.2642 PF 1.2931, f3 n1832 mean -0.0109 PF 0.9933, f4 n1832 mean 0.1007 PF 1.0697, f5 n1832 mean -0.1421 PF 0.9164
- **FOREX**: f1 n1338 mean -0.0065 PF 0.8065, f2 n1338 mean -0.019 PF 0.0019, f3 n1338 mean -0.0229 PF 0.2141, f4 n1338 mean 0.0255 PF 1.1893, f5 n1338 mean 0.0761 PF 1.6726
- **COMMODITY**: f1 n249 mean -0.0108 PF 0.9648, f2 n249 mean -0.5282 PF 0.4344, f3 n249 mean -1.6828 PF 0.1814, f4 n249 mean -0.4538 PF 0.6128, f5 n249 mean -0.3238 PF 0.7951
- **EQUITY**: f1 n202 mean -0.0052 PF 0.9964, f2 n202 mean -0.005 PF 0.9863, f3 n202 mean -0.3281 PF 0.2278, f4 n202 mean 0.1274 PF 1.087, f5 n202 mean 0.6427 PF 1.7818
- **UNCATEGORIZED**: f1 n22 mean -0.6704 PF 0.3491, f2 n22 mean -0.3277 PF 0.6157, f3 n22 mean -0.4061 PF 0.582, f4 n22 mean -0.4366 PF 0.6649, f5 n22 mean -1.8681 PF 0.2981
- **MEME**: f1 n15 mean -2.6117 PF 0.0307, f2 n15 mean 4.9378 PF 7.3995, f3 n15 mean 2.1568 PF 7.3561, f4 n15 mean 0.308 PF 1.1045, f5 n15 mean -0.7733 PF 0.7561
- **ETF**: too few rows for walk-forward
- **BOND**: too few rows for walk-forward
- **FUTURES**: too few rows for walk-forward
- **INDEX**: too few rows for walk-forward
- **MUTUAL_FUND**: no rows in trading_picks under this population
- **PENNY_STOCK**: no rows in trading_picks under this population
