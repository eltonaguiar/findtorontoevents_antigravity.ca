# Evidence Manifest — final_v2 (2026-11-14)

Links to the run/verification artifacts that back the final_v2 findings.

## Key evidence files (in repo)
| Artifact | Path | Supports |
|---|---|---|
| Profitability scorecard | `research/profitability/SCORECARD.md` | NOT_PROVED after 23 candidates; VWAP falsified |
| ITERATION-005 trend | `2026-11-14/finpredict/2026-11-14T160004Z/research/ITERATION-005.md` | trend Sharpe 2.13 claim |
| Horizon harness results | `final_2026_11_14/finpredict-v3/04_research_validation/horizon_validation_n{60,30}.txt` | 0/6, 0/26 pass |
| Data-hygiene audit | `final_2026_11_14/finpredict-v3/01_audit/PREDICTION_DATA_HYGIENE_AUDIT.md` | frozen prices, phantoms, date-only seeds |
| PnL-unit mix defect | `.kilo/worktrees/flaxen-hair/quick_wins/shared/normalize_pnl_units.py` | 93 rows: 47 ratio/32 percent/14 off |
| Adjudication | `final_2026_11_14/quant-audit-2026-11-14/` | refutes VWAP 3.76; corrects trend benchmark |
| ML validation | `final_2026_11_14/finpredict-v3/04_research_validation/ML_VALIDATION_README.md` | leakage/look-ahead/stale models |

## Verification I ran this stage
- `pytest tests/test_pi_data_hygiene.py tests/test_pi_fundamental_ranker.py` → 18 passed.
- Confirmed childlike-airport final folder exists with 8 subfolders (VWAP claim inside).
- Confirmed quant-audit final folder exists (adjudication table).

## Numbers cited
- CRYPTO: WR 35.9%, PF 0.92 (n=4,907 intrabar).
- EQUITY: WR 59.2%, PF 0.94 (headline n=8 / intrabar 250).
- FOREX: WR 32.2%, PF 0.66 (n=82).
- ETF: PF 1.836 (n=15) — fails Bonferroni.
- FUTURES: n=52, PF 1.09 — insufficient.
- BOND: n=3, PF 0.0 — insufficient.
- MUTUAL FUNDS: unbuilt.
- Trend: net Sharpe 2.13, t=5.56, CI [1.25,3.25], OOS 2.06→2.33.
- VWAP (disputed): claim 3.76 → refuted to ~1.18.
