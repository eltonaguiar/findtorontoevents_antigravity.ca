---
name: db-schema
description: Look up database schema, table structure, or connection details for any of the 9 MySQL databases (ejaguiar1_stocks, ejaguiar1_backtests, ejaguiar1_sportsbet, ejaguiar1_favcreators, ejaguiar1_events, ejaguiar1_memecoin, ejaguiar1_tvmoviestrailers, ejaguiar1_news, ejaguiar1_deals). Triggers — `/db-schema`, "what tables are in X db", "schema for table Y", "how is the DB structured", "where is the schema", "DB connection details", "regenerate schema doc". Aliases — dbschema, db-schema, schema-lookup, db-lookup.
---

# DB Schema Skill

## Quick Reference — Where Schema Lives

| Resource | Path | What it contains |
|---|---|---|
| **Full introspected schema** | `docs/DB_SCHEMA_stocks_backtests_2026-05-15.md` | 322+6 tables: full `DESCRIBE` per table with types, nullability, keys, row counts |
| **DB catalog / topology** | `docs/DATABASE_SPECIFICATION_2026-05-06.md` | All 9 databases, their purpose, representative tables, runtime surfaces |
| **Audit trail SQLite schema** | `audit_trail/schema.sql` | `at_*` / `bt_*` table DDL (SQLite version) |
| **Audit trail MySQL schema** | `audit_trail/mysql_schema.sql` | Same tables, MySQL DDL for `ejaguiar1_stocks` |
| **Live trading schema** | `trading_system/database/schema.sql` | TimescaleDB hypertables: orders, fills, positions, OHLCV aggregates |
| **Strategy health schema** | `strategy_health/schema.sql` | Strategy health monitoring tables |
| **Baseline snapshot** | `schema-baseline.sql` | 93 KB baseline reference (may be stale) |
| **Regenerate script** | `tools/_db_schema_doc.py` | Re-introspects live DBs → overwrites `docs/DB_SCHEMA_stocks_backtests_2026-05-15.md` |
| **Kimi edge audit JSON** | `reports/kimi_edge_audit_2026-05-11/schema_documentation.json` | Row-count statistics snapshot |

## Database Catalog (9 MySQL databases on mysql.50webs.com:3306)

### `ejaguiar1_stocks` — 322 tables (as of 2026-05-15)
- **Role:** primary audit + trading pipeline operational store
- **Key table families:**
  - `at_*` — audit trail: `at_raw_picks`, `at_consensus_picks`, `at_aggregation_runs`, `at_signal_outcomes`, `at_strategy_stats`, `at_discord_gate_log`, `at_filter_log`
  - `alpha_*` — alpha engine staging: `alpha_picks`, `alpha_factor_scores`, `alpha_fundamentals`, `alpha_macro`, `alpha_earnings`
  - `algorithm_*` — algo performance: `algorithms`, `algorithm_performance`, `algorithm_rolling_perf`
  - `bt_*` / `backtest_*` — backtest tables (partially migrated to `ejaguiar1_backtests`): `bt_backtest_runs`, `bt_backtest_trades`, `backtest_results`, `backtest_trades`, `at_large_backtest_results`, `at_incubator_backtest_results`
- **Runtime surfaces:** `audit_trail/mysql_client.py`, `live-monitor/api/*`, `sync_all_picks_to_mysql.py`

### `ejaguiar1_backtests` — 6 tables (live-verified 2026-05-16)
- **Role:** dedicated backtest archive
- **Tables (confirmed live):** `at_incubator_backtest_results`, `at_large_backtest_results`, `backtest_results`, `backtest_trades`, `bt_backtest_runs`, `bt_backtest_trades`

### `ejaguiar1_sportsbet`
- **Role:** sports-betting operational DB
- **Key table families:** `lm_sports_*`, `lm_arena_*`, `lm_nba_*`, `lm_nfl_*`, `lm_nhl_*`, `lm_mlb_*`
- **Runtime surfaces:** `live-monitor/api/sports_*.php`

### `ejaguiar1_favcreators`
- **Role:** FavCreators app (users, creators, accountability)
- **Key tables:** `users`, `creators`, `creator_status_updates`, `streamer_*`, `accountability_*`, `user_*`
- **Runtime surfaces:** `favcreators/docs/api/*`

### `ejaguiar1_events`
- **Role:** events ingestion and analytics
- **Key tables:** `events_log`, `event_pulls`, `event_sources`, `event_title_index`, `stats_summary`

### `ejaguiar1_memecoin`
- **Role:** memecoin/pump analytics
- **Key tables:** `mc_winners`, `pump_forensics_*`, `meme_ml_*`, `psi_*`, `he_*`, `sf_*`, `tv_signals`

### `ejaguiar1_tvmoviestrailers`
- **Role:** movies/trailers/watchlist/playlists
- **Key tables:** `movies`, `trailers`, `thumbnails`, `streaming_providers`, `playlist_items`, `shared_playlists`, `user_preferences`, `user_queues`
- **Runtime surfaces:** `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS*` APIs

### `ejaguiar1_news`
- **Role:** news articles + source catalog
- **Key tables:** `news_articles`, `news_sources`

### `ejaguiar1_deals`
- **Role:** reserved/deals vertical (minimal usage, likely empty)

## Connection Details

**ALWAYS connect via `tools/db_env.py` — never hardcode a password.** It resolves creds from env vars, then `/home/eaguiar2015/dbpasses.txt` (gitignored — never commit/echo its contents):

```python
import sys; sys.path.insert(0, '<repo root>')
from tools.db_env import get_stocks_creds, get_backtests_creds, get_backups_creds
import pymysql
KEEP = ('host','user','password','database','port','connect_timeout')
conn = pymysql.connect(**{k:v for k,v in get_stocks_creds().items() if k in KEEP})
```

| DB | resolver | user | purpose |
|---|---|---|---|
| `ejaguiar1_stocks` | `get_stocks_creds()` | `ejaguiar1_stocks` | live picks/outcomes (`trading_picks`, `at_signal_outcomes`, INCIDENT_*/ENHANCEMENT_*/FINDING_*) |
| `ejaguiar1_backtests` | `get_backtests_creds()` | `ejaguiar1_backtests` | `bt_backtest_trades`, backtest runs |
| `ejaguiar1_backups` | `get_backups_creds()` | `ejaguiar1_backups` | **backup target for ALL table-mutating ops** |

Pass envs (`DB_PASS_STOCKS` / `DB_PASS_BACKTESTS` / `DB_PASS_BACKUPS`) live in `.env` / `dbpasses.txt` — the actual values are NOT documented here (history exposure → operator rotation pending). 50webs pw convention: `<name>1234560`.

> **BACKUP RULE (MANDATORY, operator directive):** before any UPDATE/DELETE/DROP/schema change on a live table, snapshot the affected rows to `ejaguiar1_backups` first. Use `tools/db_backup_to_backups.py` or an inline copy — **backup-table names must stay ≤64 chars** (MySQL identifier limit; long source-table names + a timestamp suffix overflow — use a short hashed/consolidated name). Then mutate in a txn with a row-count sanity assert.

> **Note:** `ejaguiar1_stocks` is **only connectable from the 50webs server IP** — external connections (dev machine, CI) get `Access denied`. Use the PHP API endpoints or run queries from within 50webs shell. `ejaguiar1_backtests` is accessible externally. (Local agents on this desktop reach all three via `db_env` — creds in `dbpasses.txt`.)

## How to Regenerate the Schema Doc

```bash
# Set env vars first (already in .env)
set DB_PASS_STOCKS=stock123
set DB_PASS_BACKTESTS=backtests123

# Run from repo root (generates docs/DB_SCHEMA_stocks_backtests_<date>.md)
python tools/_db_schema_doc.py
```

> Must be run **from the 50webs server** or a whitelisted IP for `ejaguiar1_stocks`. `ejaguiar1_backtests` regenerates fine from anywhere.

## Live Verification (2026-05-16)

| Database | Expected tables | Live result | Status |
|---|---|---|---|
| `ejaguiar1_backtests` | 6 | 6 ✓ | **MATCHES** |
| `ejaguiar1_stocks` | 322 | Access denied from dev IP | **UNVERIFIABLE externally** — last introspected 2026-05-15 |

The `ejaguiar1_backtests` 6 tables confirmed live: `at_incubator_backtest_results`, `at_large_backtest_results`, `backtest_results`, `backtest_trades`, `bt_backtest_runs`, `bt_backtest_trades`.
