# GHA Workflow Repairs + bt_backtest Resume — 2026-06-05

## Problems

1. **auto-shutdown-monitor.yml** — invalid YAML (inline `python3 -c` broke scanner at line 26). Every push-triggered run failed in 0s without executing.
2. **bt_backtest_trades sync** — first real sync (`27019279488`) synced ~500k rows then died with `Lost connection to MySQL server during query` (long-lived `SSDictCursor` on 50webs).
3. **Feed Health Check** — failing on `ueps.unrealized_pnl_pct: null` (fixed prior commit in `dashboard_payload_health.py`).

## Fixes

| Workflow | Fix |
|----------|-----|
| `auto-shutdown-monitor.yml` | Heredoc `PYEOF` block; hardcoded `ejaguiar1_stocks` user |
| `bt-backtest-trades-sync.yml` | Id-windowed `LIMIT 2000` batches; reconnect src/tgt every 100k rows; resume from `MAX(id)` on target; timeout 90→180 min |
| `money_ready_verdict.json` | Refreshed via `tools/money_ready_snapshot.py`; FTP-deployed |

## Retry

```bash
gh workflow run bt-backtest-trades-sync.yml --field dry_run=false
gh workflow run feed-health.yml
gh workflow run auto-shutdown-monitor.yml
```

Prior sync left ~500k rows on backtests side — retry resumes from `cutoff_id` automatically.

## Verification

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/auto-shutdown-monitor.yml'))"
python3 tools/money_ready_snapshot.py
python3 tools/deploy_audit_files.py --only audit_data
```
