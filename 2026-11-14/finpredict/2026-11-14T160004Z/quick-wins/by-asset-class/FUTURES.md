# FUTURES — quick wins

## 1. Emit full ISO timestamps (never date-only) (S / H)
- **Problem:** `_make_pick()` emits `entry_date` as `strftime("%Y-%m-%d")`, and two importers map `entry_date` → `entry_time`, so persisted `entry_time`/`signal_time` is bare `"2026-11-14"` → UI "no date".
- **Fix:** In `_make_pick()` emit full ISO (add explicit `entry_time`/`signal_time`); make importers prefer a full timestamp over `entry_date`.
- **Targets:** `copy_trader_intel/multi_asset_copytrader_scraper.py:409` (`_make_pick`, bad emit :452); `audit_trail/import_to_local_sqlite.py:73`; `audit_trail/import_backtest_trades.py:285`. (`alpha_engine/futures_strategies.py` already emits ISO via `_now_iso()` :32.)
- **Verify:** re-emit one `ES=F` pick → `entry_time`/`signal_time` parse as ISO; UI shows a time.

## 2. Hide gated/placeholder futures rows (see OVERALL QW-7)
- FUTURES "3 OPEN, 0 closed ever" is a visibility-floor artifact, not real live positions. Exclude `_gate_passed=False` rows from the headline active list (or mark `placeholder=True`).
