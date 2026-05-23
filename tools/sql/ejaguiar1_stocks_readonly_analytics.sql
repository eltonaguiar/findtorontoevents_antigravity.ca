-- ejaguiar1_stocks — read-only analytics templates
-- Run against mysql.50webs.com (or local restore) with a read-only user.
-- Table names match dump ejaguiar1_stocks_apr62026_extract.sql; live DB may have extra tables.

-- ---------------------------------------------------------------------------
-- 0) Inventory (detect drift vs repo docs / April 2026 extract)
-- ---------------------------------------------------------------------------
SHOW TABLES;
SELECT TABLE_NAME, ENGINE, TABLE_ROWS, AVG_ROW_LENGTH, DATA_LENGTH
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
ORDER BY DATA_LENGTH DESC;

-- ---------------------------------------------------------------------------
-- 1) Score / confidence vs outcome — at_raw_picks (aggregator)
-- ---------------------------------------------------------------------------
SELECT asset_class,
       COUNT(*) AS n,
       AVG(confidence) AS avg_conf,
       AVG(pnl_pct) AS avg_pnl,
       SUM(CASE WHEN status IN ('WON','LOST','CLOSED') THEN 1 ELSE 0 END) AS n_settled
FROM at_raw_picks
GROUP BY asset_class
ORDER BY n DESC;

-- Quintiles of confidence vs mean pnl (settled only)
SELECT q.conf_quintile,
       COUNT(*) AS n,
       AVG(q.confidence) AS avg_conf,
       AVG(q.pnl_pct) AS avg_pnl_pct
FROM (
  SELECT confidence,
         pnl_pct,
         NTILE(5) OVER (ORDER BY confidence) AS conf_quintile
  FROM at_raw_picks
  WHERE status IN ('WON', 'LOST', 'CLOSED')
    AND pnl_pct IS NOT NULL
    AND confidence IS NOT NULL
) AS q
GROUP BY q.conf_quintile
ORDER BY q.conf_quintile;

-- MySQL 8+ NTILE required. If unavailable, use subquery with percent_rank.

-- ---------------------------------------------------------------------------
-- 2) Consensus tier vs outcome
-- ---------------------------------------------------------------------------
SELECT consensus_tier,
       classification,
       COUNT(*) AS n,
       AVG(pnl_pct) AS avg_pnl,
       SUM(CASE WHEN status IN ('WON','LOST','CLOSED') THEN 1 ELSE 0 END) AS n_settled
FROM at_consensus_picks
GROUP BY consensus_tier, classification
ORDER BY n DESC;

-- ---------------------------------------------------------------------------
-- 3) Top filter reasons (why picks dropped)
-- ---------------------------------------------------------------------------
SELECT filter_reason, COUNT(*) AS n
FROM at_filter_log
GROUP BY filter_reason
ORDER BY n DESC
LIMIT 40;

-- ---------------------------------------------------------------------------
-- 4) alpha_picks — score vs need for outcome join
-- ---------------------------------------------------------------------------
SELECT strategy,
       COUNT(*) AS n,
       AVG(score) AS avg_score,
       MIN(pick_date) AS first_pick,
       MAX(pick_date) AS last_pick
FROM alpha_picks
GROUP BY strategy
ORDER BY n DESC;

-- ---------------------------------------------------------------------------
-- 5) JSON: optional keys in raw_payload (sample — adjust key names)
-- ---------------------------------------------------------------------------
-- SELECT id, JSON_KEYS(raw_payload) AS keys_sample
-- FROM at_raw_picks
-- WHERE raw_payload IS NOT NULL
-- LIMIT 20;

-- ---------------------------------------------------------------------------
-- 6) bt_backtest_trades — scope check (do not mix with at_* without source metadata)
-- ---------------------------------------------------------------------------
SELECT asset_class, COUNT(*) AS n, AVG(pnl_pct) AS avg_pnl
FROM bt_backtest_trades
GROUP BY asset_class
ORDER BY n DESC
LIMIT 20;
