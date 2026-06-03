# Stale resolver pagination fix — full OPEN+ACTIVE scan

**Date:** 2026-06-03  
**Severity:** P0 data hygiene  
**Goal #1:** `/audit` health `past_hold_window` must match what the resolver actually closes

## What was broken

`tools/resolve_stale_open_picks.py` fetched only the **oldest 500** live rows (`ORDER BY created_at ASC LIMIT 500`) and stopped after **10 consecutive empty batches** without advancing offset.

When the oldest cohort was still inside the hold window but **newer** live rows were past max hold, the tool reported **0 stale** while `check_resolver_health.py` showed **192** `past_hold_window` (YELLOW).

## Fix

- `find_live_picks_batch(..., offset=N)` uses SQL `LIMIT/OFFSET` pagination.
- On a batch with **no** stale picks: `offset += len(batch)` until the full live set is scanned.
- On resolve: reset `offset = 0` and re-scan from oldest (rows removed from live set).

## Verification (2026-06-03T03:12Z)

```bash
python3 -m pytest tests/test_resolve_stale_scan.py -q   # 1 passed
python3 tools/resolve_stale_open_picks.py --execute --batch-size 500
# stale found: 192 (CRYPTO 176, UNKNOWN 16) — matches health metric
python3 tools/check_resolver_health.py
# stale_by_category → GREEN (0 past_hold_window)
```

## Ops

- GHA `outcome-resolver.yml` uses the same script hourly — fix applies on next deploy (already in repo).
- On-prem: `./tools/install_resolver_hygiene_cron.sh` for 06:15 UTC daily bundle.

## Capital policy

Unchanged — no production sizing; empty `PROMOTED_STRATEGIES`.
