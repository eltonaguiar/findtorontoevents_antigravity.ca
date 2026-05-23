# Feed health monitoring

Validates `audit_trail/data/dashboard_payload.json` against the live registry **`JSON_PICK_SOURCES`** in `audit_trail/dashboard_generator.py` (via import, not a duplicate config file).

## What gets checked

| Check | Detail |
|-------|--------|
| Payload freshness | `generated_at` vs `MAX_AGE_SECONDS` (default 4h), or file mtime if missing |
| Registry coverage | Each `JSON_PICK_SOURCES` system name has a row in `payload.systems[].name` (except `_HIDDEN_SYSTEMS`) |
| Numeric sanity | `unrealized_pnl_pct` coercible to float; `active_picks` integer ≥ 0 |

**Not** validated: individual upstream JSON files on disk or GitHub raw URLs (use `hub/data/systems_manifest.json` ping script in `ROOT_ORIGIN_CURSOR.MD` §I for that).

## Scripts

| Path | Purpose |
|------|---------|
| `audit_trail/collect_sources.py` | Prints registered source names; uses `dashboard_generator` import |
| `audit_trail/dashboard_payload_health.py` | Shared `check_dashboard_payload()` |
| `audit_trail/feed_health_check.py` | CLI: `--once`, optional Prometheus `--metrics-port` + daemon `--interval` |
| `tools/audit_payload_health.py` | Thin wrapper (same checks, no Prometheus) |

## One-shot (local or CI)

```bash
python tools/audit_payload_health.py
# or
python audit_trail/feed_health_check.py --once
```

## Prometheus + Slack

```bash
pip install prometheus_client
export SLACK_WEBHOOK="https://hooks.slack.com/services/..."
export MAX_AGE_SECONDS=14400
python audit_trail/feed_health_check.py --metrics-port 8000 --interval 300
```

Scrape `http://<host>:8000/metrics`. Metrics:

- `crypto_feed_payload_stale` — 1 if payload older than max age  
- `crypto_feed_payload_age_seconds`  
- `crypto_feed_up_to_date{system="..."}` — 1 if that registered source is healthy for this run  

## systemd (example)

```ini
[Unit]
Description=Crypto audit feed health exporter
After=network.target

[Service]
WorkingDirectory=/opt/crypto/findtorontoevents_antigravity.ca
ExecStart=/usr/bin/python3 audit_trail/feed_health_check.py --metrics-port 8000 --interval 300
Restart=always
User=crypto
Environment=SLACK_WEBHOOK=https://hooks.slack.com/services/XXX/YYY/ZZZ
Environment=MAX_AGE_SECONDS=14400

[Install]
WantedBy=multi-user.target
```

Use **`--once`** from **cron** if you only want alerts without a long-lived metrics port:

```cron
*/15 * * * * cd /opt/crypto/findtorontoevents_antigravity.ca && /usr/bin/python3 audit_trail/feed_health_check.py --once
```

## GitHub Actions

`.github/workflows/feed-health.yml` runs `feed_health_check.py --once` on the **committed** `dashboard_payload.json`. If the repo snapshot is stale, the job fails until the next data commit.

Optional: add repository secret **`SLACK_WEBHOOK`** for Slack notifications.

## Grafana panel (import snippet)

Use Prometheus data source; query `crypto_feed_up_to_date` with legend `{{system}}`. Thresholds: 0 = red, 1 = green.

See also `ROOT_ORIGIN_CURSOR.MD` §I / §I2 / §L5 for context.
