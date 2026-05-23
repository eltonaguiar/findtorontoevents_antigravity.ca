-- Sports enhancement plan: optional tables for paper A/B and pre-game features.
-- Run on ejaguiar1_sportsbet after backup. MySQL 5.x compatible (no IF NOT EXISTS for VIEW on older hosts).

-- Paper shadow tickets (main vs fade); stakes are paper-only.
CREATE TABLE IF NOT EXISTS `lm_sports_paper_shadow` (
  `id` int NOT NULL AUTO_INCREMENT,
  `source_bet_id` int DEFAULT NULL,
  `track` varchar(32) NOT NULL DEFAULT 'fade',
  `event_id` varchar(100) NOT NULL,
  `sport` varchar(50) DEFAULT NULL,
  `pick` varchar(100) NOT NULL,
  `market` varchar(20) DEFAULT NULL,
  `odds` decimal(10,4) NOT NULL DEFAULT '0.0000',
  `stake` decimal(10,2) NOT NULL DEFAULT '0.00',
  `result` varchar(20) DEFAULT NULL,
  `pnl` decimal(10,2) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `settled_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_track` (`track`),
  KEY `idx_event` (`event_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;

-- Normalized pre-game features per event (join to lm_sports_bets.event_id).
CREATE TABLE IF NOT EXISTS `lm_sports_pre_game_features` (
  `id` int NOT NULL AUTO_INCREMENT,
  `event_id` varchar(100) NOT NULL,
  `sport` varchar(50) DEFAULT NULL,
  `feature_json` text,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_event` (`event_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;

-- Optional reporting VIEW (MySQL 5.7+). Drop first if re-running.
-- DROP VIEW IF EXISTS `v_sports_odds_bucket_stats`;
-- CREATE VIEW `v_sports_odds_bucket_stats` AS
-- SELECT
--   sport,
--   market,
--   bookmaker AS book,
--   CASE
--     WHEN odds < 2.0 THEN 'lt_2'
--     WHEN odds < 3.0 THEN '2_to_3'
--     WHEN odds < 6.0 THEN '3_to_6'
--     ELSE 'ge_6'
--   END AS odds_bucket,
--   SUM(CASE WHEN result IN ('won','win','lost','loss') THEN 1 ELSE 0 END) AS settled_wl,
--   SUM(CASE WHEN result IN ('won','win') THEN 1 ELSE 0 END) AS wins,
--   SUM(CASE WHEN result IN ('lost','loss') THEN 1 ELSE 0 END) AS losses,
--   ROUND(100.0 * SUM(CASE WHEN result IN ('won','win') THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN result IN ('won','win','lost','loss') THEN 1 ELSE 0 END),0), 2) AS win_rate_pct,
--   SUM(CASE WHEN result IN ('won','win','lost','loss') THEN bet_amount ELSE 0 END) AS staked_wl,
--   SUM(COALESCE(pnl,0)) AS net_pnl
-- FROM lm_sports_bets
-- WHERE result IS NOT NULL AND result != ''
-- GROUP BY sport, market, book, odds_bucket;

-- Optional: extra columns on lm_sports_bets for line history and audit (uncomment and run once per host).
-- ALTER TABLE `lm_sports_bets` ADD COLUMN `initial_odds` decimal(10,4) DEFAULT NULL;
-- ALTER TABLE `lm_sports_bets` ADD COLUMN `final_odds` decimal(10,4) DEFAULT NULL;
-- ALTER TABLE `lm_sports_bets` ADD COLUMN `odds_change_pct` decimal(8,4) DEFAULT NULL;
-- ALTER TABLE `lm_sports_bets` ADD COLUMN `placed_at_utc` datetime DEFAULT NULL;
-- ALTER TABLE `lm_sports_bets` ADD COLUMN `raw_events_json` mediumtext;
-- ALTER TABLE `lm_sports_bets` ADD COLUMN `book_jurisdiction` varchar(16) DEFAULT NULL;
-- Post–Apr 2026 policy cohort for headline metrics (see ensure_sports_bets_cohort.php).
-- ALTER TABLE `lm_sports_bets` ADD COLUMN `cohort` varchar(64) DEFAULT NULL;
