-- 2026-11-19 — persist volume context at entry on resolved signal outcomes.
--
-- Why: volume_ratio_at_entry exists on 20/23 active rows and 0/3,500 closed rows
-- (buffy's finding, verified: the column does not exist on at_signal_outcomes at
-- all). Every planned volume A/B is therefore retroactively impossible until the
-- resolver records it. This is the schema half; tools/backfill_volume_ratio.py is
-- the writer/backfiller.
--
-- Idempotency: MySQL before 8.0.29 has no ADD COLUMN IF NOT EXISTS, so run the
-- guard below (it no-ops when the column is present).

SET @ddl := (
  SELECT IF(
    EXISTS(SELECT 1 FROM information_schema.columns
           WHERE table_schema = DATABASE()
             AND table_name = 'at_signal_outcomes'
             AND column_name = 'volume_ratio_at_entry'),
    'SELECT 1',
    'ALTER TABLE at_signal_outcomes ADD COLUMN volume_ratio_at_entry DECIMAL(12,4) NULL '
    'COMMENT ''entry-bar volume / median of the prior 20 bars'' AFTER asset_class')
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
