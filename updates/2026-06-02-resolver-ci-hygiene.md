# Resolver CI hygiene — hourly OPEN+ACTIVE stale + MySQL outcomes

**Date:** 2026-06-02  
**Goal #1:** keep `trading_picks` live cohort honest without manual cron on every host

## Changes

### `.github/workflows/outcome-resolver.yml` (hourly `:15`)

1. **New step:** `tools/resolve_stale_open_picks.py --execute` (OPEN+ACTIVE past hold window, max 30×500 batches).
2. **Outcome resolver:** production runs now pass `--mysql` (and `PICK_OUTCOMES_MYSQL_ENABLED=1`) so `at_pick_outcomes` upserts mirror file resolutions.
3. All steps already set `PYTHONPATH=${{ github.workspace }}` — fixes the `No module named 'alpha_engine'` footgun in CI.

### `.github/workflows/quan-engine-live.yml`

- Added `PYTHONPATH: ${{ github.workspace }}` on the TP/SL resolve step.

## Operator mirror (on-prem cron)

Hosts without relying solely on GHA can still run:

```bash
./tools/run_daily_resolver_hygiene.sh
```

That bundle also runs `universal_pick_resolver` + verified pilots (not in the hourly GHA job — see `audit-dashboard.yml` cron).

## Capital policy

Unchanged: empty `PROMOTED_STRATEGIES`, 0/9 money-ready, no `PROMOTION_GATE_ENFORCE=1`.
