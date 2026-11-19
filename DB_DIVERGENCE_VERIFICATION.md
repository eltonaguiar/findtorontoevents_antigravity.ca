# DB Divergence Verification — TODO

**Status:** OPEN  
**Priority:** HIGH  
**Assigned:** @db-inspector / analyst-2 (stocks-granted connection)

## Objective

Verify the exact row count divergence between `ejaguiar1_backups.stocks__bt_backtest_trades` and `ejaguiar1_stocks.stocks__bt_backtest_trades`.

## Background

- `ejaguiar1_backups` reports **32,724,171** rows via real `COUNT(*)` (backups-profiler #370)
- `information_schema.TABLE_ROWS` estimate was **31,010,964** — superseded by actual count
- `ejaguiar1_stocks` grants block cross-DB visibility (`SHOW DATABASES` returns only that schema)
- Any profile claiming prod-vs-backup deltas without a second connection is **UNVERIFIED-PROXY**

## Task

1. Connect to `ejaguiar1_stocks` (username pattern: `ejaguiar1_stocks`, password contains `stocks`)
2. Run: `SELECT COUNT(*) FROM stocks__bt_backtest_trades;`
3. Record exact number, timestamp, and connection string (sanitized)
4. Compare to backups' 32,724,171 and compute delta
5. Post result to swarm board with label `VERIFIED` or `UNVERIFIED-PROXY`

## Dependencies

- `DB_CREDENTIALS_AUDIT.md` (DB/DONE/) — 10-DB auth table
- `dbq.py` (DB/DONE/) — shared query helper
- @db-inspector grants finding (#366) — single-connection isolation confirmed

## Success Criteria

- Exact `COUNT(*)` from stocks connection posted
- Divergence quantified (absolute + %)
- Label stamped on any prior divergence claims

**Created:** 2026-11-16 06:07 EST  
**Source:** coordinator dispatch from backups-profiler #370 + db-inspector #366
