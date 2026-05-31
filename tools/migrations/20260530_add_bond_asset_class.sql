-- Migration: Add BOND to asset_class ENUM in all affected tables
-- Date: 2026-05-30
-- Reason: Bond strategies (bond_yield_momentum, bond_mean_reversion, etc.) emit
--         category="bond" but the MySQL ENUM doesn't include 'BOND', causing
--         them to fall through to 'CRYPTO' via symbol-based detection.
--
-- Run on: ejaguiar1_stocks (mysql.50webs.com:3306)
-- Tables affected: all tables with asset_class ENUM

ALTER TABLE at_raw_picks
    MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','BOND','UNKNOWN')
    NOT NULL DEFAULT 'UNKNOWN';

ALTER TABLE at_consensus_picks
    MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','BOND','UNKNOWN')
    NOT NULL DEFAULT 'UNKNOWN';

ALTER TABLE at_filter_log
    MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','BOND','UNKNOWN')
    DEFAULT 'UNKNOWN';

ALTER TABLE at_strategy_stats
    MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','BOND','UNKNOWN')
    DEFAULT 'UNKNOWN';

ALTER TABLE at_signal_outcomes
    MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','BOND','UNKNOWN')
    DEFAULT 'UNKNOWN';

-- at_pending_outcomes was in an earlier migration draft but does not exist
-- in the live DB (verified 2026-05-30 SHOW TABLES). Keeping a commented stub
-- so the migration is self-documenting; uncomment if the table is later
-- created with an asset_class ENUM column.
-- ALTER TABLE at_pending_outcomes
--     MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','BOND','UNKNOWN')
--     NOT NULL DEFAULT 'UNKNOWN';

ALTER TABLE bt_backtest_runs
    MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','BOND','UNKNOWN')
    DEFAULT 'UNKNOWN';

ALTER TABLE bt_backtest_trades
    MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','BOND','UNKNOWN')
    DEFAULT 'UNKNOWN';

-- 2026-05-30: added the 3 tables peer's first pass missed (verified against
-- live DB SHOW COLUMNS — all 3 still carry asset_class ENUM without BOND).
-- Without these the migration is incomplete and downstream inserts into
-- these tables would silently fall back to 'UNKNOWN' or error on BOND.

ALTER TABLE at_audit_events
    MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','BOND','UNKNOWN')
    DEFAULT 'UNKNOWN';

ALTER TABLE at_discord_sent
    MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','BOND','UNKNOWN')
    DEFAULT 'UNKNOWN';

ALTER TABLE at_sqlite_imports
    MODIFY COLUMN asset_class ENUM('CRYPTO','FOREX','EQUITY','PENNY_STOCK','MEMECOIN','SPORTS','FUTURES','ETF','COMMODITY','BOND','UNKNOWN')
    DEFAULT 'UNKNOWN';

-- Also update consensus_tracked which uses varchar but should be consistent
-- (no change needed for varchar columns, they accept any value)
