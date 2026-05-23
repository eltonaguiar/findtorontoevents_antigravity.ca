# Drift Monitoring Runbook

## Prerequisites
- PowerShell 7+
- Node.js 20+
- Input data files:
  - `audit_dashboard/data/hourly_asset_class_24h_report.json`
  - `tmp/backtest_forward_drift_analysis.json`

## 1) Build canonical backtest-forward drift report

Purpose:
- Generate `tmp/backtest_forward_drift_analysis.json` from the latest dashboard payload.
- Join forward strategy performance with backtest baselines from the strategy leaderboard sources.
- Persist a timestamped snapshot for fallback and audit trail.

Command:

```bash
python tools/drift/build_backtest_forward_drift.py \
  --input audit_dashboard/data/dashboard_data.json \
  --output tmp/backtest_forward_drift_analysis.json \
  --snapshot-dir audit_dashboard/data/drift_snapshots
```

Outputs:
- `tmp/backtest_forward_drift_analysis.json`
- `audit_dashboard/data/drift_snapshots/backtest_forward_drift_*.json`

## 2) Validate backtest integrity

Purpose:
- Assert `bt_n > 0` and `bt_wr` is present and non-zero (strict mode).
- Log missing join keys for investigation.
- Auto-fallback to most recent healthy snapshot if available.

Command:

```powershell
pwsh -File tools/drift/validate_backtest_integrity.ps1 \
  -InputPath tmp/backtest_forward_drift_analysis.json \
  -OutputPath tmp/backtest_forward_drift_analysis.validated.json \
  -SnapshotDir audit_dashboard/data/drift_snapshots \
  -LogPath audit_dashboard/data/backtest_integrity.log \
  -StrictZeroBtWr \
  -FailOnError
```

Outputs:
- `tmp/backtest_forward_drift_analysis.validated.json`
- `audit_dashboard/data/backtest_integrity.log`

## 3) Compute dynamic per-asset drift scores

Purpose:
- Normalize time to `event_ts`.
- Compute per-asset drift score:
  - `drift_score = w*win_rate_gap + b*(1 - pf_ema) + c*expectancy_gap`
- Dynamic thresholding using class history and sigma rule.
- Consecutive high-drift counter and probation flag.

Command:

```bash
node tools/drift/compute_dynamic_drift_score.js \
  --input audit_dashboard/data/hourly_asset_class_24h_report.json \
  --config config/drift_params.json \
  --output audit_dashboard/data/drift_scores_latest.json
```

Output:
- `audit_dashboard/data/drift_scores_latest.json`

## 4) Export Prometheus metrics

Purpose:
- Produce scrape-friendly metrics and optional Pushgateway publish.

Command (file output only):

```powershell
pwsh -File tools/drift/export_drift_metrics.ps1 \
  -DriftScorePath audit_dashboard/data/drift_scores_latest.json \
  -IntegrityPath tmp/backtest_forward_drift_analysis.validated.json \
  -OutputPromPath audit_dashboard/data/drift_metrics.prom
```

Command (with Pushgateway):

```powershell
pwsh -File tools/drift/export_drift_metrics.ps1 \
  -DriftScorePath audit_dashboard/data/drift_scores_latest.json \
  -IntegrityPath tmp/backtest_forward_drift_analysis.validated.json \
  -OutputPromPath audit_dashboard/data/drift_metrics.prom \
  -PushgatewayUrl http://pushgateway:9091 \
  -JobName drift_monitor
```

Output:
- `audit_dashboard/data/drift_metrics.prom`

## Expected schema

### Validated integrity JSON
- `rows_total`
- `rows_valid`
- `rows_invalid`
- `missing_join_keys[]`
- `used_fallback`
- `fallback_path`

### Drift score JSON rows
- `event_ts`
- `asset_class`
- `drift_score`
- `class_score_threshold`
- `high_drift`
- `consecutive_high_drift_hours`
- `probation`

## Common failure modes

1. Missing backtest file
- Symptom: integrity script exits with file-not-found.
- Fix: generate/update `tmp/backtest_forward_drift_analysis.json` first.

2. All backtest baselines invalid
- Symptom: `rows_invalid > 0` and no fallback found.
- Fix: inspect `missing_join_keys` and fix strategy+asset join mapping in upstream aggregation.

3. Empty hourly dataset
- Symptom: drift score output has zero rows.
- Fix: rebuild `audit_dashboard/data/hourly_asset_class_24h_report.json`.

4. Pushgateway publish fails
- Symptom: HTTP error from export script.
- Fix: verify URL/network/auth and retry with local file output first.
