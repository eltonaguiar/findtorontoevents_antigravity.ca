# Phase-4 End-to-End Strategy Tracking Pipeline Honesty — Plan (2026-05-31)

Validate 5 layers of: trading_picks -> resolver -> at_strategy_stats -> pf_registry.json -> strategy_tier_tracker.py -> dashboard.

## Layers and checks
1. at_strategy_stats: COUNT/MAX(last_updated); workflow cron lookup; recompute 5 rows.
2. pf_registry.json: generated_utc within 24h; recompute PF for 3 strategies; flag >10% drift.
3. closed_picks honesty (PR #158 SHIBUSDT): last-100 pnl_pct recompute; USDT-suffix non-crypto category audit.
4. anti_overfit_audit.json (PR #156): generated_at within 24h; spot-check 2 high-DSR rows.
5. strategy_tier_tracker.py: read-only run; ImportError / sanity.

Read-only DB access via /home/eaguiar2015/dbpasses.txt. Server-side docs PR if findings ship.
