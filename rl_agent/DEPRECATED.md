# rl_agent — DEPRECATED

**Date:** 2026-03-16
**Status:** Stale / Abandoned

## Reason
- Last data output: 2026-03-14
- No active GitHub Actions workflow (disabled via `if: false` in `.github/workflows/rl-agent-ppo.yml`)
- Stale picks were polluting the active picks dashboard and cross-aggregation consensus
- System removed from aggregator data pipeline (`cross_aggregation/aggregator.py`)

## What was disabled
1. `cross_aggregation/aggregator.py` — rl_agent entry commented out from SYSTEM_PATHS
2. `.github/workflows/rl-agent-ppo.yml` — job disabled with `if: false`
3. `audit_dashboard/template.html` and `audit_dashboard/index.html` — cosmetic references left in place (no functional impact; dashboard descriptions only)

## Files preserved (not deleted)
- `rl_agent/` — all source code, models, and data remain intact
- Can be re-enabled by reversing the above changes
