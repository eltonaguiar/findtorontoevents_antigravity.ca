-- Mercury feedback (April 2026) — Tier-1/Tier-2 schema additions.
-- Run on ejaguiar1_sportsbet after backup. All statements are idempotent
-- (CREATE TABLE IF NOT EXISTS) so re-running is safe. MyISAM matches the
-- rest of the schema; switch to InnoDB on hosts that grant it.
--
-- Phase 0 — Foundations (this file)
-- Phase 1 items 1–5 and Phase 2 items 6–10 tables are all created here.
-- Each subsequent PR wires its own population path against these tables.

-- =============================================================
-- Phase 1 item 1 — Rolling odds history for steam/RLM detection
-- =============================================================
-- Mirrors lm_sports_odds row-for-row plus snapshot_at. Populated by
-- sports_odds.php on each successful upcoming-odds refresh. A nightly
-- cron prunes rows older than 30 days.
CREATE TABLE IF NOT EXISTS `lm_sports_odds_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `sport` varchar(50) NOT NULL,
  `event_id` varchar(100) NOT NULL,
  `home_team` varchar(100) NOT NULL,
  `away_team` varchar(100) NOT NULL,
  `commence_time` datetime NOT NULL,
  `bookmaker` varchar(50) NOT NULL,
  `bookmaker_key` varchar(50) NOT NULL DEFAULT '',
  `market` varchar(20) NOT NULL,
  `outcome_name` varchar(100) NOT NULL,
  `outcome_price` decimal(10,4) NOT NULL DEFAULT '0.0000',
  `outcome_point` decimal(6,2) DEFAULT NULL,
  `last_updated` datetime NOT NULL,
  `snapshot_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_event_book_market` (`event_id`, `bookmaker_key`, `market`, `snapshot_at`),
  KEY `idx_snapshot` (`snapshot_at`),
  KEY `idx_sport_snap` (`sport`, `snapshot_at`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;

-- =============================================================
-- Phase 1 item 2 — Steam-move detector
-- =============================================================
-- Each row = one detected coordinated line move. detected_at is wall-clock.
-- magnitude = average price/point shift across moving books (signed; see
-- sports_steam_detector.php for direction semantics).
CREATE TABLE IF NOT EXISTS `lm_sports_steam_moves` (
  `id` int NOT NULL AUTO_INCREMENT,
  `event_id` varchar(100) NOT NULL,
  `sport` varchar(50) NOT NULL DEFAULT '',
  `home_team` varchar(100) NOT NULL DEFAULT '',
  `away_team` varchar(100) NOT NULL DEFAULT '',
  `commence_time` datetime DEFAULT NULL,
  `market` varchar(20) NOT NULL DEFAULT 'h2h',
  `outcome_name` varchar(100) NOT NULL DEFAULT '',
  `direction` varchar(8) NOT NULL DEFAULT 'up',
  `books_moved` int NOT NULL DEFAULT '0',
  `magnitude` decimal(8,4) NOT NULL DEFAULT '0.0000',
  `window_minutes` int NOT NULL DEFAULT '15',
  `books_json` text,
  `detected_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_event` (`event_id`),
  KEY `idx_detected` (`detected_at`),
  KEY `idx_sport` (`sport`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;

-- =============================================================
-- Phase 1 item 3 — Arbitrage scanner
-- =============================================================
-- Two-leg arb opportunities computed from latest lm_sports_odds. Status
-- transitions: 'open' (initial) -> 'closed' (line moved) | 'taken' (manual).
CREATE TABLE IF NOT EXISTS `lm_sports_arbs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `event_id` varchar(100) NOT NULL,
  `sport` varchar(50) NOT NULL DEFAULT '',
  `home_team` varchar(100) NOT NULL DEFAULT '',
  `away_team` varchar(100) NOT NULL DEFAULT '',
  `commence_time` datetime DEFAULT NULL,
  `market` varchar(20) NOT NULL DEFAULT 'h2h',
  `point` decimal(6,2) DEFAULT NULL,
  `leg_a_outcome` varchar(100) NOT NULL DEFAULT '',
  `leg_a_book` varchar(60) NOT NULL DEFAULT '',
  `leg_a_book_key` varchar(60) NOT NULL DEFAULT '',
  `leg_a_odds` decimal(10,4) NOT NULL DEFAULT '0.0000',
  `leg_b_outcome` varchar(100) NOT NULL DEFAULT '',
  `leg_b_book` varchar(60) NOT NULL DEFAULT '',
  `leg_b_book_key` varchar(60) NOT NULL DEFAULT '',
  `leg_b_odds` decimal(10,4) NOT NULL DEFAULT '0.0000',
  `gross_spread` decimal(8,4) NOT NULL DEFAULT '0.0000',
  `fees_pct` decimal(6,4) NOT NULL DEFAULT '0.0000',
  `net_edge_pct` decimal(8,4) NOT NULL DEFAULT '0.0000',
  `source` varchar(40) NOT NULL DEFAULT 'odds_api',
  `status` varchar(20) NOT NULL DEFAULT 'open',
  `detected_at` datetime NOT NULL,
  `closed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_event_market` (`event_id`, `market`),
  KEY `idx_detected` (`detected_at`),
  KEY `idx_status` (`status`),
  KEY `idx_source` (`source`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;

-- =============================================================
-- Phase 1 item 4 / Phase 2 item 6 — Prediction-market quotes
-- =============================================================
-- One row per (platform, market, side) snapshot. Populated by
-- predhunt_fetch.php (free tier) and predhunt_arb/ev.php (Dev tier).
CREATE TABLE IF NOT EXISTS `lm_predmarket_quotes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `platform` varchar(30) NOT NULL DEFAULT '',
  `event_match_key` varchar(160) NOT NULL DEFAULT '',
  `event_id` varchar(100) DEFAULT NULL,
  `sport` varchar(50) NOT NULL DEFAULT '',
  `market` varchar(40) NOT NULL DEFAULT '',
  `side` varchar(8) NOT NULL DEFAULT 'yes',
  `outcome_name` varchar(120) NOT NULL DEFAULT '',
  `price` decimal(10,6) NOT NULL DEFAULT '0.000000',
  `volume` decimal(18,4) DEFAULT NULL,
  `liquidity` decimal(18,4) DEFAULT NULL,
  `external_market_id` varchar(120) DEFAULT NULL,
  `fetched_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_match_key` (`event_match_key`),
  KEY `idx_event_id` (`event_id`),
  KEY `idx_platform_fetch` (`platform`, `fetched_at`),
  KEY `idx_sport_fetch` (`sport`, `fetched_at`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;

-- Optional: persisted predhunt EV signals (Dev tier). Mirrors the /api/v2/ev
-- response. Decoupled from lm_sports_arbs because EV is probabilistic, not
-- guaranteed-profit, so it has its own tab.
CREATE TABLE IF NOT EXISTS `lm_predmarket_ev_signals` (
  `id` int NOT NULL AUTO_INCREMENT,
  `platform` varchar(30) NOT NULL DEFAULT '',
  `event_match_key` varchar(160) NOT NULL DEFAULT '',
  `sport` varchar(50) NOT NULL DEFAULT '',
  `market` varchar(40) NOT NULL DEFAULT '',
  `side` varchar(8) NOT NULL DEFAULT 'yes',
  `price` decimal(10,6) NOT NULL DEFAULT '0.000000',
  `fair_price` decimal(10,6) NOT NULL DEFAULT '0.000000',
  `ev_pct` decimal(8,4) NOT NULL DEFAULT '0.0000',
  `kelly_fraction` decimal(6,4) NOT NULL DEFAULT '0.0000',
  `signal_payload` text,
  `detected_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_match_key` (`event_match_key`),
  KEY `idx_detected` (`detected_at`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;

-- =============================================================
-- Phase 2 item 7 — Weather snapshots
-- =============================================================
-- Keyed off event_id; nullable temp/wind/precip handle indoor venues that
-- have no meaningful weather signal (the situational scorer should ignore
-- rows where all three are NULL).
CREATE TABLE IF NOT EXISTS `lm_event_weather` (
  `id` int NOT NULL AUTO_INCREMENT,
  `event_id` varchar(100) NOT NULL,
  `sport` varchar(50) NOT NULL DEFAULT '',
  `venue_name` varchar(160) DEFAULT NULL,
  `is_indoor` tinyint NOT NULL DEFAULT '0',
  `temp_c` decimal(6,2) DEFAULT NULL,
  `wind_kph` decimal(6,2) DEFAULT NULL,
  `precip_mm` decimal(6,2) DEFAULT NULL,
  `humidity_pct` decimal(5,2) DEFAULT NULL,
  `provider` varchar(40) NOT NULL DEFAULT 'openweather',
  `fetched_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_event` (`event_id`),
  KEY `idx_fetched` (`fetched_at`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;

-- =============================================================
-- Phase 2 item 8 — NHL goalie starts (situational model input)
-- =============================================================
CREATE TABLE IF NOT EXISTS `lm_nhl_goalie_starts` (
  `id` int NOT NULL AUTO_INCREMENT,
  `game_id` varchar(60) NOT NULL,
  `team` varchar(60) NOT NULL,
  `goalie_name` varchar(120) NOT NULL DEFAULT '',
  `sv_pct_l10` decimal(6,4) DEFAULT NULL,
  `gaa_l10` decimal(6,3) DEFAULT NULL,
  `projected_starter` tinyint NOT NULL DEFAULT '0',
  `confirmed` tinyint NOT NULL DEFAULT '0',
  `source` varchar(40) NOT NULL DEFAULT '',
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_game_team` (`game_id`, `team`),
  KEY `idx_updated` (`updated_at`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;

-- =============================================================
-- Phase 2 item 9 — E-sports odds (CS2 / LoL pilots)
-- =============================================================
CREATE TABLE IF NOT EXISTS `lm_esports_odds` (
  `id` int NOT NULL AUTO_INCREMENT,
  `game` varchar(40) NOT NULL DEFAULT '',
  `event_id` varchar(120) NOT NULL,
  `match_name` varchar(200) NOT NULL DEFAULT '',
  `team_a` varchar(120) NOT NULL DEFAULT '',
  `team_b` varchar(120) NOT NULL DEFAULT '',
  `commence_time` datetime DEFAULT NULL,
  `bookmaker` varchar(60) NOT NULL DEFAULT '',
  `bookmaker_key` varchar(60) NOT NULL DEFAULT '',
  `market` varchar(40) NOT NULL DEFAULT 'h2h',
  `outcome_name` varchar(120) NOT NULL DEFAULT '',
  `outcome_price` decimal(10,4) NOT NULL DEFAULT '0.0000',
  `outcome_point` decimal(8,2) DEFAULT NULL,
  `source` varchar(40) NOT NULL DEFAULT '',
  `last_updated` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_event` (`event_id`),
  KEY `idx_game_time` (`game`, `commence_time`),
  KEY `idx_book` (`bookmaker_key`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;

-- =============================================================
-- Phase 2 item 10 — Polymarket whale tracker
-- =============================================================
CREATE TABLE IF NOT EXISTS `lm_polymarket_wallets` (
  `id` int NOT NULL AUTO_INCREMENT,
  `address` varchar(64) NOT NULL,
  `label` varchar(80) NOT NULL DEFAULT '',
  `focus` varchar(120) NOT NULL DEFAULT '',
  `notes` text,
  `active` tinyint NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_address` (`address`),
  KEY `idx_active` (`active`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;

CREATE TABLE IF NOT EXISTS `lm_polymarket_positions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `wallet_address` varchar(64) NOT NULL,
  `wallet_label` varchar(80) NOT NULL DEFAULT '',
  `market_id` varchar(120) NOT NULL DEFAULT '',
  `market_question` varchar(400) NOT NULL DEFAULT '',
  `outcome` varchar(40) NOT NULL DEFAULT '',
  `size` decimal(20,6) NOT NULL DEFAULT '0.000000',
  `avg_price` decimal(10,6) NOT NULL DEFAULT '0.000000',
  `current_price` decimal(10,6) DEFAULT NULL,
  `unrealized_pnl` decimal(20,6) DEFAULT NULL,
  `fetched_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_wallet_fetch` (`wallet_address`, `fetched_at`),
  KEY `idx_market` (`market_id`),
  KEY `idx_fetched` (`fetched_at`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;

-- =============================================================
-- Maintenance — pruning policy
-- =============================================================
-- The history table grows fast; expect ~50k-200k rows/day at 1-min refresh
-- across 12 sports. Prune to 30 days via cron:
--   DELETE FROM lm_sports_odds_history WHERE snapshot_at < NOW() - INTERVAL 30 DAY;
-- Steam moves and arbs are small (~hundreds/day max) — no pruning required.
-- Predmarket quotes: prune to 14 days via cron:
--   DELETE FROM lm_predmarket_quotes WHERE fetched_at < NOW() - INTERVAL 14 DAY;
-- Polymarket positions: prune to 30 days; keep latest snapshot per wallet/market via downstream view.
