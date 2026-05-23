-- Historical backtest tables for retro-running the value-bet algorithm.
-- Apply via: mysql -u <user> -p <db> < live-monitor/sql/historical_backtest.sql
--
-- These tables are STRICTLY isolated from production:
--   - lm_sports_odds_historical mirrors lm_sports_odds shape but only ever
--     receives data from OddsHarvester closing-odds backfills.
--   - lm_sports_synthetic_bets mirrors lm_sports_value_bets shape, plus
--     is_synthetic, actual_outcome, actual_pnl, backtest_run_id columns.
--
-- The production hot path (lm_sports_odds, lm_sports_value_bets, lm_sports_bets)
-- never reads from or writes to these tables. The only consumer outside the
-- backtest runner itself is sports_ml.php's ensemble-activation gate, which
-- counts synthetic bets toward the 20+ "settled" threshold so the stacking
-- ensemble can train on real historical results.
--
-- Honesty banner ("Not yet safe to bet real money") stays gated on REAL
-- settled bets only (lm_sports_bets), regardless of synthetic count.

CREATE TABLE IF NOT EXISTS `lm_sports_odds_historical` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `sport` VARCHAR(64) NOT NULL,
  `event_id` VARCHAR(128) NOT NULL,
  `home_team` VARCHAR(128) NOT NULL,
  `away_team` VARCHAR(128) NOT NULL,
  `commence_time` DATETIME NOT NULL,
  `bookmaker` VARCHAR(64) NOT NULL,
  `bookmaker_key` VARCHAR(64) NOT NULL,
  `market` VARCHAR(32) NOT NULL,
  `outcome_name` VARCHAR(128) NOT NULL,
  `outcome_price` DECIMAL(10,4) NOT NULL,
  `outcome_point` DECIMAL(10,4) NULL,
  `snapshot_kind` ENUM('open','mid','close') NOT NULL DEFAULT 'close',
  `snapshot_at` DATETIME NULL,
  `source` VARCHAR(64) NOT NULL DEFAULT 'oddsharvester',
  `imported_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_event_book_market_outcome_pt_snap` (
    `event_id`, `bookmaker_key`, `market`, `outcome_name`, `outcome_point`, `snapshot_kind`
  ),
  KEY `idx_commence_sport` (`commence_time`, `sport`),
  KEY `idx_event_id` (`event_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `lm_sports_synthetic_bets` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `event_id` VARCHAR(128) NOT NULL,
  `sport` VARCHAR(64) NOT NULL,
  `home_team` VARCHAR(128) NOT NULL,
  `away_team` VARCHAR(128) NOT NULL,
  `commence_time` DATETIME NOT NULL,
  `market` VARCHAR(32) NOT NULL,
  `bet_type` VARCHAR(50) NOT NULL,
  `outcome_name` VARCHAR(128) NOT NULL,
  `best_book` VARCHAR(64) NOT NULL,
  `best_book_key` VARCHAR(64) NOT NULL,
  `best_odds` DECIMAL(10,4) NOT NULL,
  `consensus_implied_prob` DECIMAL(10,6) NOT NULL,
  `true_prob` DECIMAL(10,6) NOT NULL,
  `edge_pct` DECIMAL(8,2) NOT NULL,
  `ev_pct` DECIMAL(8,2) NOT NULL,
  `kelly_fraction` DECIMAL(10,6) NOT NULL,
  `kelly_bet` DECIMAL(10,2) NOT NULL,
  `all_odds` MEDIUMTEXT NULL,
  `detected_at` DATETIME NOT NULL,
  `as_of` DATETIME NOT NULL,
  `is_synthetic` TINYINT(1) NOT NULL DEFAULT 1,
  `backtest_run_id` VARCHAR(64) NOT NULL,
  `actual_outcome` ENUM('win','loss','push','void','pending') NOT NULL DEFAULT 'pending',
  `actual_pnl` DECIMAL(10,2) NULL,
  `graded_at` DATETIME NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_run_event_market_outcome_book` (
    `backtest_run_id`, `event_id`, `market`, `outcome_name`, `best_book_key`
  ),
  KEY `idx_run_outcome` (`backtest_run_id`, `actual_outcome`),
  KEY `idx_commence` (`commence_time`),
  KEY `idx_sport_run` (`sport`, `backtest_run_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `lm_sports_backtest_runs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `run_id` VARCHAR(64) NOT NULL,
  `started_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `finished_at` DATETIME NULL,
  `sports` VARCHAR(255) NOT NULL,
  `start_date` DATE NOT NULL,
  `end_date` DATE NOT NULL,
  `events_processed` INT NOT NULL DEFAULT 0,
  `synthetic_bets_emitted` INT NOT NULL DEFAULT 0,
  `synthetic_bets_graded` INT NOT NULL DEFAULT 0,
  `notes` TEXT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_run_id` (`run_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
