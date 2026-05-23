# Archiving `bt_backtest_trades` to `ejaguiar1_backtests` — impact analysis + migration plan

**Date:** 2026-05-04
**Source DB:** `ejaguiar1_stocks` on `mysql.50webs.com` (~14 GB)
**Target DB:** `ejaguiar1_backtests` (newly created, blank)
**Table:** `bt_backtest_trades` (~282K rows, dominant size contributor)

## Why archive
`bt_backtest_trades` accounts for the bulk of `ejaguiar1_stocks`'s 14 GB footprint per Hermes Agent #3's diff `updates/2026-05-04-database-dependency-analysis.md`. Other tables in the DB (`at_raw_picks`, `algorithm_rolling_perf`, `at_consensus_picks`, `trading_picks`, etc.) are actively read by the production pipeline and cannot be moved without code changes elsewhere. `bt_backtest_trades` is a backtest *log* — write-heavy, read-rare.

## Impact on /audit and live consumers — ZERO

Verified by direct grep. No `SELECT FROM bt_backtest_trades` anywhere in the production read path:

- `audit_trail/dashboard_generator.py` — **does not read** this table. Reads `trading_picks` via `audit_trail/mysql_client.py::mysql_fetch_closed_non_crypto`, which is a different table that stays in `ejaguiar1_stocks`.
- FWD WR%, Track%, Smart Picks, asset_class_health, walkforward.by_class — all derived from `trading_picks` + JSON files (`alpha_engine/data/closed_picks.json`, `audit_trail/data/dashboard_payload.json`), **never** from `bt_backtest_trades`.
- `live-monitor/api/*.php` — zero PHP references.
- `.github/workflows/*.yml` — no workflow reads this table.

## Read sites (4 — all non-blocking)

| File | Line | Use | Action after migration |
|------|------|-----|---|
| `audit_trail/queries.sql` | 360 | Analytical SQL | Update DB context comment |
| `audit_trail/import_to_local_sqlite.py` | 432 | Local SQLite mirror | Switch source DB to `ejaguiar1_backtests` |
| `docs/ASSET_CLASS_ANALYSIS_QUERIES.sql` | 189 | Analyst ad-hoc | Doc-only update |
| `docs/ASSET_CLASS_TOP10_QUERIES.sql` | 112 | Analyst ad-hoc | Doc-only update |
| `tools/sql/ejaguiar1_stocks_readonly_analytics.sql` | 90 | Analytical SQL | Move to a new `ejaguiar1_backtests_readonly_analytics.sql` |

## Write sites (3 — code change required)

| File | Line | Insert | Action |
|------|------|--------|--------|
| `audit_trail/import_backtest_trades.py` | 615, 632 | `INSERT INTO bt_backtest_trades` | Connect to `ejaguiar1_backtests` instead of `ejaguiar1_stocks` |
| `audit_trail/backfill.py` | 292 | `INSERT IGNORE INTO bt_backtest_trades` | Same |
| `alpha_engine/backtest_justin_bravo.py` | 413 | `INSERT INTO bt_backtest_trades` | Same |

These three currently take their DB name from `AUDIT_DB_NAME` env (default `ejaguiar1_stocks`). They share that env var with other tables that are NOT being moved (e.g. `at_raw_picks`, `at_consensus_picks`). Globally switching `AUDIT_DB_NAME` to `ejaguiar1_backtests` would break those inserts.

**Code change recipe (recommended for a follow-up PR):**
- Introduce a new env var `BACKTESTS_DB_NAME` (default `ejaguiar1_backtests`).
- The 3 writers call a small helper `_get_backtests_connection()` that uses `BACKTESTS_DB_NAME` instead of `AUDIT_DB_NAME`. All other DB inserts in those files keep using `AUDIT_DB_NAME`.
- `audit_trail/mysql_client.py` keeps pointing at `ejaguiar1_stocks` for the read path of `trading_picks` etc.

## Out-of-scope: `mega_training_data.py`

`alpha_engine/mega_training_data.py` reads `bt_backtest_trades` from a local SQL **dump file** (variable `STOCKS_SQL`), not the live DB. Migration does not affect this path. Once the dump is regenerated from `ejaguiar1_backtests`, the same script will work pointed at the new dump.

## Migration steps (user-side, MySQL)

Run on `mysql.50webs.com`:

```sql
-- 1. Dump table from source
mysqldump -h mysql.50webs.com -u <user> -p ejaguiar1_stocks bt_backtest_trades > /tmp/bt_backtest_trades.sql
mysqldump -h mysql.50webs.com -u <user> -p ejaguiar1_stocks bt_backtest_runs   > /tmp/bt_backtest_runs.sql

-- 2. Load into ejaguiar1_backtests
mysql -h mysql.50webs.com -u <user> -p ejaguiar1_backtests < /tmp/bt_backtest_trades.sql
mysql -h mysql.50webs.com -u <user> -p ejaguiar1_backtests < /tmp/bt_backtest_runs.sql

-- 3. Verify row counts match
mysql -e "SELECT COUNT(*) FROM bt_backtest_trades" ejaguiar1_stocks
mysql -e "SELECT COUNT(*) FROM bt_backtest_trades" ejaguiar1_backtests
-- Expect both ≈ 282K

-- 4. After follow-up code PR lands and one full backtest cycle writes successfully
--    to ejaguiar1_backtests in production:
DROP TABLE ejaguiar1_stocks.bt_backtest_trades;
DROP TABLE ejaguiar1_stocks.bt_backtest_runs;

-- 5. (Optional) reclaim disk
OPTIMIZE TABLE ejaguiar1_stocks.<other_tables>;
```

## Recommended sequencing

1. **Now (manual, user):** dump + load to `ejaguiar1_backtests`. Source rows stay in `ejaguiar1_stocks` until step 4.
2. **Follow-up PR (code):** introduce `BACKTESTS_DB_NAME` env var + helper in the 3 writer files. Default to `ejaguiar1_backtests` so production picks it up.
3. **Verify:** one full hourly cycle writes new rows to `ejaguiar1_backtests.bt_backtest_trades` AND `/audit` regen still produces normal `dashboard_data.json` (no FWD WR / Track% regression).
4. **Drop:** `DROP TABLE ejaguiar1_stocks.bt_backtest_trades` after green verification window (24h recommended).

## Rollback
- If step 3 verification fails: revert the code PR, writers go back to `ejaguiar1_stocks`. The dumped rows in `ejaguiar1_backtests` are orphaned but harmless. No data loss because step 4 has not happened yet.
- Pre-step-4 dump is the safety net.

## Charter / governance
- Per `CLAUDE.md`: no destructive DB ops without confirmation. Step 4 (DROP TABLE) is destructive and is sequenced **after** code lands and verifies. Documented here so reviewers can see the full chain before authorizing.
