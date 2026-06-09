# Pillar Migration Safety Net (2026-06-09)

## What this turn did

Added a **rollback path** for the schema migration + backfill that was applied earlier today:

1. **Snapshot backup tables** (created `2026-06-09`):
   - `at_pick_outcomes_pre_pillar_migration_2026_06_09` — 39,908 rows / 16 cols
   - `trading_picks_pre_pillar_migration_2026_06_09` — 47,279 rows / 29 cols
   - Verified row + column counts match the live tables exactly.

2. **Reverse tool** (`tools/reverse_pillar_migration.py`):
   - Idempotent `DROP COLUMN` for the 4 pillar columns on both tables.
   - Safe-by-default: dry-run mode prints the exact `ALTER TABLE ... DROP COLUMN` statements it would execute. Must pass `--apply` to actually drop.
   - Race-safe: handles MySQL 1091 (column already gone) gracefully.

## ⚠️ Critical timing note

**The user originally asked for the backup to be done BEFORE the migration**, so the migration would be reversible within a single transaction.

**Reality**: the migration (`bad1214f71`) and the backfill (`tools/backfill_pillar_columns.py --apply`) were both already applied before this safety-net turn ran. The backup tables created in this turn therefore capture the **post-migration, post-backfill state**, not the pristine pre-migration state.

**Consequence**: the 4 new columns (`market_regime_id`, `sector`, `volatility_atr`, `execution_slippage_pct`) ARE present in the backup tables. If you run `tools/reverse_pillar_migration.py --apply` to drop them from the live tables, the columns are gone from the live tables BUT the backfilled data is preserved in the backup tables (under the same column names).

**To fully recover the pristine pre-migration state**, the only path is:
1. `RENAME TABLE at_pick_outcomes TO at_pick_outcomes_post_pillar;` + `RENAME TABLE at_pick_outcomes_pre_pillar_migration_2026_06_09 TO at_pick_outcomes;` (and same for trading_picks)
2. This swaps the backup into the live position. The backup has 16/29 columns (post-migration schema), not 12/25 (pre-migration schema), so the schema is not truly pristine — but the row data + all backfilled values are preserved.

**To truly get a 12/25-column pristine pre-migration snapshot**, the only path is a database restore from a pre-2026-06-09 backup, which is outside this safety-net's scope.

## What the safety-net IS good for

- **Snapshot recovery**: if a future session discovers the backfilled data is wrong and wants to start over, the backup has the exact row state to restore from.
- **Schema rollforward**: re-running `tools/migrate_add_pillar_columns.py --apply` on the backup tables would be a no-op (idempotent).
- **Schema rollback**: running `tools/reverse_pillar_migration.py --apply` removes the 4 columns from the live tables; the backup tables still have them for reference.

## How to actually use it

### Roll forward (re-add the columns — currently a no-op)
```bash
python3 tools/migrate_add_pillar_columns.py --apply
```

### Roll back (drop the columns — destructive!)
```bash
# Dry-run first to see what would be dropped:
python3 tools/reverse_pillar_migration.py
# Then actually drop:
python3 tools/reverse_pillar_migration.py --apply
```

### Restore from snapshot (full row+column state, schema is post-migration)
```bash
# After running reverse, the backup tables still have the columns.
# To swap the snapshot into the live position:
mysql ejaguiar1_stocks -e "
  RENAME TABLE at_pick_outcomes TO at_pick_outcomes_post_pillar_2026_06_09;
  RENAME TABLE at_pick_outcomes_pre_pillar_migration_2026_06_09 TO at_pick_outcomes;
  RENAME TABLE trading_picks TO trading_picks_post_pillar_2026_06_09;
  RENAME TABLE trading_picks_pre_pillar_migration_2026_06_09 TO trading_picks;
"
```

## Files

- Created: `tools/reverse_pillar_migration.py` (113 lines, idempotent, dry-run-by-default, warning banner in --apply mode)
- Created (in DB): `at_pick_outcomes_pre_pillar_migration_2026_06_09`, `trading_picks_pre_pillar_migration_2026_06_09`
- Created: `updates/2026-06-09-pillar-migration-safety-net.md` (this file)
