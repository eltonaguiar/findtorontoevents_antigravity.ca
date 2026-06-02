# Resolver hygiene wave 3 — MySQL writer OPEN + daily cron bundle

**Date:** 2026-06-02  
**Goal #1:** trustworthy `/audit` pick funnel (no dual live cohort regrowth)

## What changed

1. **`alpha_engine/mysql_trading_sync.pick_to_row`**
   - Missing `status` now defaults to **`OPEN`** (was implicit `ACTIVE` via legacy DDL default).
   - Live picks with `status=ACTIVE` and empty/live `exit_reason` map to **`OPEN`** before upsert.
   - Terminal `ACTIVE` rows (e.g. `exit_reason=TIME_EXIT`) stay **`ACTIVE`** until upstream normalizes.

2. **`tools/run_daily_resolver_hygiene.sh`**
   - Cron-friendly bundle: universal resolver → stale OPEN+ACTIVE execute → `outcome_resolver --mysql` → health JSON tail → verified pilots.
   - Logs under `logs/resolver_hygiene/run_<UTC>.log`.
   - Requires `AUDIT_DB_PASS` or `DB_PASS_STOCKS` and repo `PYTHONPATH`.

3. **Tests:** `tests/test_mysql_sync_live_status_open.py` (3 cases) + existing `test_pick_hold_windows.py`.

## Verification (2026-06-02T23:57Z)

```bash
python3 -m pytest tests/test_mysql_sync_live_status_open.py tests/test_pick_hold_windows.py -q
# 8 passed

python3 tools/resolve_stale_open_picks.py --execute --batch-size 500 --max-batches 10
# total_live_picks 2690, stale_found 0, resolved 0

python3 tools/run_verified_pilots_daily.py
# ok=True, money_ready 0/9, ETF n_closed=0

python3 tools/check_resolver_health.py
# overall YELLOW (estimated_stale label fixed; OPEN volume still high)
```

## Operator cron (example)

```cron
15 6 * * * cd /path/to/repo && AUDIT_DB_PASS=... ./tools/run_daily_resolver_hygiene.sh
```

## Capital policy (unchanged)

- `PROMOTED_STRATEGIES` empty — do **not** set `PROMOTION_GATE_ENFORCE=1`.
- ETF shadow pilot: wait for `n_closed ≥ 30` before allowlist admission.

## Related

- [ACTIVE stale resolver P0](https://findtorontoevents.ca/updates/2026-06-02-active-stale-resolver-p0.md)
- [EAGLE2 PR #465 session findings](https://findtorontoevents.ca/updates/2026-06-02-eagle2-pr465-session-findings.md)
