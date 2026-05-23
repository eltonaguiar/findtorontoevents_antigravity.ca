# Grafana/Prometheus Alert Pipeline for Drift + Probation

## Goal
Monitor drift in near real-time and trigger probation actions when:
- `drift_score > class_threshold`
- `consecutive_high_drift_hours >= 2`
- `backtest_integrity_failures > 0`

## Pipeline
1. GitHub Action `.github/workflows/audit-drift-telemetry.yml` runs drift pipeline.
2. `tools/drift/export_drift_metrics.ps1` generates `audit_dashboard/data/drift_metrics.prom`.
3. Prometheus scrapes metrics (or receives them via Pushgateway).
4. Alertmanager routes alerts to Slack/Discord/webhook.
5. Probation webhook updates your strategy state store.

## Prometheus scrape example (textfile endpoint)

```yaml
scrape_configs:
  - job_name: audit_drift
    static_configs:
      - targets: ['drift-exporter:9100']
```

If using Pushgateway, add:

```yaml
scrape_configs:
  - job_name: pushgateway
    static_configs:
      - targets: ['pushgateway:9091']
```

## Alert rules example

```yaml
groups:
  - name: drift-alerts
    rules:
      - alert: HighDriftScore
        expr: drift_high == 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High drift detected"
          description: "asset_class={{ $labels.asset_class }} hour={{ $labels.hour_utc }}"

      - alert: ProbationTrigger
        expr: drift_probation == 1
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Probation triggered"
          description: "asset_class={{ $labels.asset_class }} has 2+ consecutive high-drift hours"

      - alert: BacktestIntegrityFailure
        expr: backtest_integrity_failures > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Backtest integrity validation failed"
          description: "rows_invalid={{ $value }}"
```

## Probation action hook
When `ProbationTrigger` fires, route Alertmanager webhook to a lightweight action endpoint that:
1. reads `asset_class`
2. finds impacted strategies in latest drift table
3. sets strategy status to `PROBATION`
4. increments `consecutive-hit` counter
5. writes audit log row

## Fast start checklist
- Enable workflow: `.github/workflows/audit-drift-telemetry.yml`
- Generate metrics: `audit_dashboard/data/drift_metrics.prom`
- Add Prometheus scrape + rules
- Connect Alertmanager webhook
- Validate with one synthetic high-drift row
