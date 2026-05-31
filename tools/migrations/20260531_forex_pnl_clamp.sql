-- Migration: Clamp FOREX pnl_pct to [-100, +inf) on surviving bad rows
-- Date: 2026-05-31
-- Incident: #10 (FOREX pnl_pct clamp)
--
-- Background:
--   The outcome_resolver write-path can produce pnl_pct values below -100%
--   for FOREX picks when a price-unit / direction-sign mismatch slips past
--   the M-111 implausibility cap. A long position can lose at most 100% of
--   capital, so any pnl_pct < -100 on FOREX is corrupt and skews
--   per-class WR/PF aggregates (asset_class_health, pf_registry).
--
--   The write-time clamp landed in alpha_engine/outcome_resolver.py
--   (commit: fix/incident-10). This migration backfills the 5 surviving
--   rows that pre-date the clamp, including the headline -106700% row.
--
-- Targets:
--   Database: ejaguiar1_stocks (mysql.50webs.com:3306)
--   Tables expected to hold pnl_pct for FOREX picks:
--     - trading_picks  (primary live picks table)
--     - signals        (outcome_resolver primary write target)
--     - at_signal_outcomes (audit-trail mirror)
--
-- Safety:
--   * DO NOT execute blindly. Run preview SELECTs first, eyeball the 5 rows,
--     confirm they are FOREX + pnl_pct < -100, then run the UPDATEs inside
--     a transaction with explicit row-count assertions.
--   * Preserve the original raw value in a sidecar column (_pnl_clamped_raw)
--     mirroring the in-memory field the resolver now stamps. If the column
--     doesn't exist, the ALTER below adds it (idempotent via IF NOT EXISTS
--     on MySQL 8.0.29+; on older MySQL, wrap in a stored procedure or run
--     the ALTER manually and ignore "Duplicate column" errors).
--
-- Verification queries (run BEFORE the UPDATEs):
--
--   SELECT id, symbol, strategy, asset_class, pnl_pct, status, resolved_at
--   FROM trading_picks
--   WHERE asset_class = 'FOREX' AND pnl_pct < -100
--   ORDER BY pnl_pct ASC;
--
--   SELECT id, symbol, strategy, asset_class, pnl_pct, status, resolved_at
--   FROM signals
--   WHERE asset_class = 'FOREX' AND pnl_pct < -100
--   ORDER BY pnl_pct ASC;
--
-- Expected: exactly 5 rows total across the two tables, including the
-- pnl_pct = -106700 row flagged in incident #10.

-- ---------------------------------------------------------------------
-- Step 1: Add sidecar columns to preserve raw pre-clamp values.
-- ---------------------------------------------------------------------
ALTER TABLE trading_picks
    ADD COLUMN IF NOT EXISTS _pnl_clamped_raw DOUBLE NULL
        COMMENT 'Original pnl_pct before incident-#10 clamp to [-100, +inf)';

ALTER TABLE trading_picks
    ADD COLUMN IF NOT EXISTS _pnl_clamped_reason VARCHAR(64) NULL
        COMMENT 'Reason tag for clamp (e.g. forex_lower_bound_-100)';

ALTER TABLE signals
    ADD COLUMN IF NOT EXISTS _pnl_clamped_raw DOUBLE NULL
        COMMENT 'Original pnl_pct before incident-#10 clamp to [-100, +inf)';

ALTER TABLE signals
    ADD COLUMN IF NOT EXISTS _pnl_clamped_reason VARCHAR(64) NULL
        COMMENT 'Reason tag for clamp (e.g. forex_lower_bound_-100)';

-- ---------------------------------------------------------------------
-- Step 2: Backfill clamp on the surviving bad rows.
--         Wrap in a transaction so we can ROLLBACK if row counts surprise.
-- ---------------------------------------------------------------------
START TRANSACTION;

-- trading_picks: clamp + preserve raw
UPDATE trading_picks
   SET _pnl_clamped_raw    = pnl_pct,
       _pnl_clamped_reason = 'forex_lower_bound_-100',
       pnl_pct             = -100.0
 WHERE asset_class = 'FOREX'
   AND pnl_pct < -100.0
   AND _pnl_clamped_raw IS NULL;

-- signals: clamp + preserve raw
UPDATE signals
   SET _pnl_clamped_raw    = pnl_pct,
       _pnl_clamped_reason = 'forex_lower_bound_-100',
       pnl_pct             = -100.0
 WHERE asset_class = 'FOREX'
   AND pnl_pct < -100.0
   AND _pnl_clamped_raw IS NULL;

-- at_signal_outcomes: mirror (if the column exists). Comment out if N/A.
-- UPDATE at_signal_outcomes
--    SET pnl_pct = -100.0
--  WHERE asset_class = 'FOREX'
--    AND pnl_pct < -100.0;

-- Manual verification step before COMMIT:
--   SELECT ROW_COUNT();  -- should be small (incident #10: 5 rows total)
--   SELECT COUNT(*) FROM trading_picks WHERE asset_class='FOREX' AND pnl_pct<-100;  -- expect 0
--   SELECT COUNT(*) FROM signals       WHERE asset_class='FOREX' AND pnl_pct<-100;  -- expect 0
--
-- If counts look right:
--   COMMIT;
-- Otherwise:
--   ROLLBACK;

-- NOTE: this file intentionally does NOT auto-COMMIT. A human operator
-- must inspect the row counts and issue COMMIT or ROLLBACK manually.
