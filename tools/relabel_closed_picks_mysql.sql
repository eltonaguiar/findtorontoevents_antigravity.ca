-- Phase 1.2 — Relabel status='CLOSED' rows in MySQL trading_picks to WON/LOST per pnl_pct sign
--
-- Generated 2026-05-27 alongside tools/relabel_closed_picks_status.py.
-- Local JSON dry-run (closed_picks_enriched.json) flipped 6,093 of 8,421 rows.
-- MySQL trading_picks may have different counts.
--
-- SAFETY:
--   1. ALWAYS run the SELECT preview first.
--   2. Note the COUNT to make sure it matches expectations.
--   3. Run the UPDATE inside a transaction so you can ROLLBACK if needed.
--   4. NEVER bulk-relabel zero-pnl_pct rows — they may be intentionally CLOSED-not-FLAT.

USE ejaguiar1_stocks;

-- ============================================================
-- STEP 1 — Preview row count by intended new status
-- ============================================================

SELECT
  CASE
    WHEN pnl_pct > 0 THEN 'WON'
    WHEN pnl_pct < 0 THEN 'LOST'
    ELSE 'KEEP_CLOSED'
  END AS new_status,
  COUNT(*) AS n
FROM trading_picks
WHERE status = 'CLOSED'
  AND pnl_pct IS NOT NULL
GROUP BY new_status;

-- ============================================================
-- STEP 2 — Sample 20 to eyeball before mass UPDATE
-- ============================================================

SELECT id, symbol, strategy, direction, status, exit_reason, pnl_pct,
       CASE WHEN pnl_pct > 0 THEN 'WON' WHEN pnl_pct < 0 THEN 'LOST' ELSE 'KEEP_CLOSED' END AS would_be
FROM trading_picks
WHERE status = 'CLOSED' AND pnl_pct IS NOT NULL
ORDER BY RAND()
LIMIT 20;

-- ============================================================
-- STEP 3 — Wrap UPDATE in transaction
-- ============================================================

START TRANSACTION;

UPDATE trading_picks
SET status = 'WON',
    updated_at = NOW(),
    notes = CONCAT(IFNULL(notes,''), ' [relabeled-from-CLOSED-2026-05-27]')
WHERE status = 'CLOSED' AND pnl_pct > 0;

UPDATE trading_picks
SET status = 'LOST',
    updated_at = NOW(),
    notes = CONCAT(IFNULL(notes,''), ' [relabeled-from-CLOSED-2026-05-27]')
WHERE status = 'CLOSED' AND pnl_pct < 0;

-- Inspect aggregate impact before committing:
SELECT status, COUNT(*) AS n FROM trading_picks GROUP BY status;

-- ============================================================
-- STEP 4 — COMMIT or ROLLBACK
-- ============================================================
--
-- If numbers look right (overall WON+LOST should increase, CLOSED should drop near zero):
--   COMMIT;
--
-- If anything looks off:
--   ROLLBACK;
