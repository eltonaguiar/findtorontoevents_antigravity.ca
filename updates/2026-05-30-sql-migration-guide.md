# SQL Migration: Add BOND to asset_class ENUM

**Date:** 2026-05-30
**Branch:** `fix/bond-asset-class-mapping`
**Reason:** Bond strategies (bond_yield_momentum, bond_mean_reversion, etc.) emit `category="bond"` but the MySQL ENUM doesn't include 'BOND', causing them to fall through to 'CRYPTO' via symbol-based detection.

## 1. Run BOND Asset Class Migration

**Migration file:** `tools/migrations/20260530_add_bond_asset_class.sql`

**Tables affected:** at_raw_picks, at_consensus_picks, at_filter_log, at_strategy_stats, at_signal_outcomes

**What it does:** Adds 'BOND' to the `asset_class` ENUM in all audit trail tables, and also adds 'COMMODITY' to at_filter_log, at_strategy_stats, and at_signal_outcomes (which were missing it).

**Run on:** `ejaguiar1_stocks` (mysql.50webs.com:3306)

```bash
mysql -h mysql.50webs.com -u ejaguiar1_stocks -p ejaguiar1_stocks < tools/migrations/20260530_add_bond_asset_class.sql
```

**Verification:**
```sql
SHOW COLUMNS FROM at_raw_picks LIKE 'asset_class';
-- Should show ENUM with BOND included
```

## 2. Verify Sync Script Mapping

The `sync_all_picks_to_mysql.py` now maps `category="bond"` → `asset_class="BOND"` and `category="commodity"` → `asset_class="COMMODITY"` in the `_CATEGORY_TO_ASSET_CLASS` dict.

After the migration is applied, re-run the sync to pick up any previously misclassified bond picks:
```bash
python3 sync_all_picks_to_mysql.py
```

## 3. Strategy Stats Refresh

`audit_trail.mysql_client.refresh_strategy_stats_mysql()` was added to rebuild `at_strategy_stats` from `at_consensus_picks`. This runs automatically at the end of each sync cycle.
