# P0: ACTIVE + OPEN stale resolver + honest health metrics (2026-06-02)

## Problem

`trading_picks` had two live statuses:

| Status | Before | Issue |
|--------|-------:|-------|
| **ACTIVE** | 3726 | Not scanned by `resolve_stale_open_picks.py` (OPEN-only) |
| **OPEN** | ~2465 | Scanned, but health check labeled **all** OPEN as `estimated_stale` |

`check_resolver_health` **YELLOW** was misleading — it counted every OPEN row as stale, not picks past max-hold.

## Fix

1. **`tools/pick_hold_windows.py`** — shared hold windows + `is_past_max_hold()` for OPEN and ACTIVE  
2. **`tools/resolve_stale_open_picks.py`** — queries `status IN ('OPEN','ACTIVE')`; reports `by_status` breakdown  
3. **`tools/check_resolver_health.py`** — `total_past_hold_window` vs `total_live_picks`; `by_status_past_hold`  
4. **`tests/test_pick_hold_windows.py`** — unit tests (5 passed)

## Execute results (2026-06-02 ~23:48 UTC)

```bash
AUDIT_DB_PASS=... python3 tools/resolve_stale_open_picks.py --execute --batch-size 500 --max-batches 30
```

| Metric | Count |
|--------|------:|
| **Resolved (batch 1)** | **3663** (ACTIVE 3479 + OPEN 184) |
| CRYPTO past-hold | 3311 |
| Top strategy | prediction_market_consensus (300) |

**After pass 1:**

| Status | Count |
|--------|------:|
| OPEN | 2432 |
| ACTIVE | 258 |
| TIME_EXIT | 32813 |

Remaining live picks are mostly **within** hold windows (not time-stale).

## Reproduce

```bash
python3 -m pytest tests/test_pick_hold_windows.py -q
AUDIT_DB_PASS=... python3 tools/resolve_stale_open_picks.py          # dry-run
AUDIT_DB_PASS=... python3 tools/resolve_stale_open_picks.py --execute --batch-size 500
python3 tools/check_resolver_health.py --json
```

## Next

- Cron: daily `resolve_stale_open_picks.py --execute` after universal resolver  
- Consider normalizing writer default `ACTIVE` → `OPEN` in `mysql_trading_sync.py` (separate PR)  
- ETF shadow pilot unchanged — `PROMOTED_STRATEGIES` still empty  
