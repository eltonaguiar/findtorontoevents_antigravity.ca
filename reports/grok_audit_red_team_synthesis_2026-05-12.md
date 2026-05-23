# Red-Team of Grok's 2026-05-12 Audit — Synthesis

Two parallel agents cross-checked Grok's specific numerical claims
against the in-repo `reports/kimi_edge_audit_2026-05-11/` corpus.

- Agent `abebbd8fdd9ae165b` (fabrication-red-team) — 8 claims tabled, evidence-cited.
- Agent `aa0ebfe1283afe2c3` (cavecrew-investigator) — independent verification of same headline numbers.

## Verdict matrix

| # | Grok claim | Red-team verdict |
|---|---|---|
| 1 | n=55,510 resolved trades | **CONFIRMED** — metrics_by_asset_class.csv row ALL n_picks=55510; SQL in db_analysis.py:79-87 matches verbatim |
| 2 | Overall WR 11.13% / avg -3.5577% / Sharpe -2.3437 / PF 0.4574 | **CONFIRMED** — exact match metrics_by_asset_class.csv row 10 |
| 3 | Per-class table (CRYPTO/MEMECOIN/EQUITY/FOREX/FUTURES/PENNY_STOCK/ETF) | **CONFIRMED** — all 7 rows exact match within ±0.2% |
| 4 | Backtest WR ~42.4% vs Live 11.13% | **CONFIRMED with caveat** — backtest_vs_live.csv row ALL: BT 42.42 / live 11.13. BUT backtest n=943 is CRYPTO-only; EQUITY/MEMECOIN/FOREX have zero BT trades. Gap is essentially CRYPTO gap relabeled "ALL". |
| 5 | ML accuracy 32.6% / Brier 0.374 | **CONFIRMED with caveat** — ml_performance.csv accuracy=32.6, brier=0.3743. Note: precision=11.52, recall=84.38 means the model predicts WIN almost always; accuracy<random is a labeling artifact (skewed class), not necessarily "worse than random EDGE". |
| 6 | All 23 algorithms negative avg returns | **CONFIRMED** — algorithm_performance.csv: 23 rows, all avg_return_pct ∈ [-10.00, -0.35] |
| 7 | ~69% zero-PnL on resolved trades | **CONFIRMED** — direct count: 38,359/55,510 = 69.10%. Grok said 38,312; off by 0.12% within tolerance. |
| 8 | DB tables ejaguiar1_stocks + ejaguiar1_backtests schema + creds | **CONFIRMED (schema), UNVERIFIED (live row counts)** — schema_documentation.json matches; can't execute SQL without DB creds in this read. |

## Critical contextualization (do NOT skip)

Red-team agents flagged 2 important caveats Grok did not emphasize:

### Caveat 1 — Stale corpus vs live filtered view

The Kimi audit derives from `at_raw_picks` containing 143,514 historical
rows with **69.1% zero-PnL rows counted as resolved losses**. The live
`audit_dashboard/data/dashboard_data.json::performance.asset_class_health`
applies the post-resolver-v2 noise filter (`PNL_WIN_THRESHOLD_BY_CLASS`,
per CLAUDE.md Goal #1):

| Metric | Kimi audit (raw) | Live dashboard (filtered) |
|---|---|---|
| CRYPTO n | 51,049 | 7,860 (13× smaller scope) |
| CRYPTO WR | 11.3% | 47.1% |
| CRYPTO PF | 0.456 | 1.36 |

**Both reads are valid**; the gap is what the filter excludes. The 11.3%
CRYPTO WR in Grok's table includes 38k zero-PnL rows counted as losses.

This is exactly what the truth-layer banner shipped in commit `dd8e8282537`
explains to /audit users — and the zero-PnL artifact filter shipped in
the same commit excludes the artifact-pattern rows from /audit per-class
aggregates going forward.

### Caveat 2 — Backtest gap is CRYPTO-only

`backtest_vs_live.csv` shows the BT data is n=943 CRYPTO-only. The
"42.4% vs 11.13%" gap is a CRYPTO-specific overfitting signature, NOT
a cross-class indictment. EQUITY/MEMECOIN/FOREX have zero backtest
trades in the file — so for those classes, the "severe overfitting"
narrative is unverifiable from this corpus.

## What this changes about prior session work

Nothing material. The truth-layer banner + zero-PnL artifact filter
shipped in commit `dd8e8282537` already address Caveat 1. The 4
deep-dive reports (FOREX/FUTURES/BOND/ML staleness, commit `26cd0f39d01`)
already cite the post-filter live view per class.

The ML staleness watchdog hard-fail (commit `db5bcfa0f04` / `2b9692d4f3e`)
adds the mtime gate that the prior feature-count-only gate was missing —
directly addresses Grok's "32.6% accuracy / Brier 0.374 / stale" finding.

## Net verdict

**Grok's numbers are accurate** — all match in-repo artifacts within
tolerance. No claim refuted. Two caveats matter for interpretation:
the raw-vs-filtered view distinction (already shipped to /audit) and
the backtest-gap being CRYPTO-scoped (not pan-class).

The system IS currently destroying capital on the unfiltered raw view.
The post-resolver-v2 filtered view shows a more recoverable picture
(CRYPTO PF 1.36, COMMODITY PF 2.08). Real-money sizing remains gated
on the 10-step Lopez de Prado AFML readiness pipeline regardless of
which view one cites.

## Refs

- Investigator `abebbd8fdd9ae165b` (fabrication-red-team)
- Investigator `aa0ebfe1283afe2c3` (cavecrew)
- `reports/kimi_edge_audit_2026-05-11/metrics_by_asset_class.csv`
- `reports/kimi_edge_audit_2026-05-11/backtest_vs_live.csv`
- `reports/kimi_edge_audit_2026-05-11/ml_performance.csv`
- `reports/kimi_edge_audit_2026-05-11/algorithm_performance.csv`
- `reports/kimi_edge_audit_2026-05-11/raw_picks_clean.csv`
- `reports/kimi_edge_audit_2026-05-11/db_analysis.py`
- `audit_dashboard/data/dashboard_data.json::performance.asset_class_health`
- Truth-layer banner commit `dd8e8282537`
- Zero-PnL artifact filter (same commit)
- ML staleness watchdog hard-fail commit `db5bcfa0f04` (rebased from `2b9692d4f3e`)

## NFA

Research surface only. All shipped fixes are forward-only guards or
truth-layer repair. No real-money sizing without explicit greenlight +
10-step readiness gate clear.
