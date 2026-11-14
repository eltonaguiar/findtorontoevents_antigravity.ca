# Per-Asset-Class Profitability — Index

| Class | Priority | One-line idea | File |
|---|---|---|---|
| FUTURES | **HIGH** | 12m vol-targeted TSMOM + separately gated carry on continuous contracts | `FUTURES.md` |
| CRYPTO | **HIGH feasibility / LOW return** | Cross-venue funding+basis carry, measured on capital vs T-bill | `CRYPTO.md` |
| BOND | **HIGH** | UST curve carry + roll-down, DV01-neutral, no forecast | `BOND.md` |
| EQUITY | **MEDIUM** | PEAD/SUE event study from SEC XBRL; value/quality composite | `EQUITY.md` |
| FOREX | **MEDIUM** | G10 carry via CIP forwards/currency ETFs; 12m TSMOM | `FOREX.md` |
| ETF | **LOW** | Covered-call/vol-risk-premium overlay; low-vol/risk parity | `ETF.md` |
| COMMODITY | **LOW** | Roll-yield carry on real curves after purging crypto proxies | `COMMODITY.md` |
| MUTUAL FUNDS | **LOW / NOT_BUILT** | Fee arithmetic + allocation; de-advertise the signal class | `MUTUAL_FUNDS.md` |

**Common gates for every experiment:** clean OOS (train ≤2023-12-31, OOS ≥2024-01-01), realistic
costs, intrabar stops, concurrent capital/ROC, true DSR at all trials, CSCV PBO, SPA, n≥30
(preferably ≥100), 2× cost, one-period execution lag, independent replication.
