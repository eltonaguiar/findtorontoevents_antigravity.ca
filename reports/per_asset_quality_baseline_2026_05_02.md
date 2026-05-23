# Per-Asset Quality Baseline - 2026-05-02

- Generated at: 2026-05-02T06:20:56.672978+00:00
- Source: `audit_dashboard/data/dashboard_data.json`
- Scope: active + smart pick cohorts (asset normalized: COMMODITIES/BONDS/ETFS)

## Observed Distribution

| Asset Class | Active | Smart | Score Min | Score P25 | Score P50 | Score P75 | Score Max | Score Avg | FWR Min | FWR P25 | FWR P50 | FWR P75 | FWR Max | FWR Avg | Corrupted |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CRYPTO | 10 | 0 | 0.000 | 9.750 | 68.000 | 96.500 | 100.000 | 56.100 | 0.000 | 0.628 | 0.642 | 0.708 | 1.000 | 0.627 | 0 |
| EQUITY | 5 | 0 | 20.000 | 40.000 | 40.000 | 40.000 | 57.000 | 39.400 | 0.200 | 0.200 | 0.551 | 0.551 | 0.760 | 0.452 | 0 |
| FOREX | 3 | 0 | 0.000 | 20.000 | 40.000 | 50.000 | 60.000 | 33.333 | 0.459 | 0.459 | 0.459 | 0.502 | 0.545 | 0.488 | 0 |
| COMMODITY | 0 | 0 | NA | NA | NA | NA | NA | NA | NA | NA | NA | NA | NA | NA | 0 |
| FUTURES | 0 | 0 | NA | NA | NA | NA | NA | NA | NA | NA | NA | NA | NA | NA | 0 |
| BOND | 0 | 0 | NA | NA | NA | NA | NA | NA | NA | NA | NA | NA | NA | NA | 0 |
| ETF | 0 | 0 | NA | NA | NA | NA | NA | NA | NA | NA | NA | NA | NA | NA | 0 |

## Initial Threshold Recommendation (Phase-1)

| Asset Class | Smart Min Score | Min Forward WR | CI Mode | Evidence Rule |
|---|---:|---:|---|---|
| CRYPTO | 68.00 | 0.63 | hard | quantile-driven (p50 score, p25 fwr) with floor clamp |
| EQUITY | 40.00 | 0.50 | hard | quantile-driven (p50 score, p25 fwr) with floor clamp |
| FOREX | 40.00 | 0.46 | hard | quantile-driven (p50 score, p25 fwr) with floor clamp |
| COMMODITY | 40.00 | 0.50 | warn | provisional default until active volume >= 10 |
| FUTURES | 45.00 | 0.50 | warn | provisional default until active volume >= 10 |
| BOND | 35.00 | 0.50 | warn | provisional default until active volume >= 10 |
| ETF | 40.00 | 0.50 | warn | provisional default until active volume >= 10 |

## Notes

- Four classes currently have no active rows; they should remain in payload summaries with `warn` CI mode to avoid starvation.
- Corrupted-row count is currently zero in active cohort using known USDCAD/Kimi signature.
- Smart cohort is currently empty in this snapshot; implementation phases should target recoverable smart coverage without relaxing hard safety blocks.
