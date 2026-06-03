# 2026-06-03 — Outcome resolver: bounded stale-pick batches

## Problem
`tools/resolve_stale_open_picks.py` without `--max-batches` scanned 3k+ live rows and could run until the harness 10h kill. Local operator runs from non-whitelisted IPs also hit MySQL `1045`.

## Fix
- `.github/workflows/outcome-resolver.yml`: `--max-batches 30` on stale OPEN+ACTIVE step (~15k row cap per hourly run).
- `tools/run_daily_resolver_hygiene.sh`: same bound for cron.

## Verify
```bash
gh workflow run outcome-resolver.yml
gh run list --workflow=outcome-resolver.yml --limit 1
python3 tools/check_resolver_health.py   # from host with valid DB_PASS_STOCKS
```