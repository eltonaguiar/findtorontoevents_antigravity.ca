<?php
/**
 * sports_schema.php — Centralized schema for Sports Betting system.
 * 7 tables: odds, credit_usage, clv, value_bets, daily_picks, bets, bankroll.
 * PHP 5.2 compatible.
 *
 * Usage: require_once 'sports_schema.php'; _sb_ensure_schema($conn);
 */

function _sb_ensure_schema($conn) {

    // ── 1. Sports Odds Cache ──
    $conn->query("CREATE TABLE IF NOT EXISTS lm_sports_odds (
        id INT AUTO_INCREMENT PRIMARY KEY,
        sport VARCHAR(50) NOT NULL,
        event_id VARCHAR(100) NOT NULL,
        home_team VARCHAR(100) NOT NULL,
        away_team VARCHAR(100) NOT NULL,
        commence_time DATETIME NOT NULL,
        bookmaker VARCHAR(50) NOT NULL,
        bookmaker_key VARCHAR(50) NOT NULL DEFAULT '',
        market VARCHAR(20) NOT NULL,
        outcome_name VARCHAR(100) NOT NULL,
        outcome_price DECIMAL(10,4) NOT NULL DEFAULT 0,
        outcome_point DECIMAL(6,2) DEFAULT NULL,
        last_updated DATETIME NOT NULL,
        KEY idx_sport (sport),
        KEY idx_event (event_id),
        KEY idx_bookmaker (bookmaker),
        KEY idx_commence (commence_time),
        UNIQUE KEY idx_unique_odds (event_id, bookmaker_key, market, outcome_name)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 2. API Credit Usage Tracking ──
    $conn->query("CREATE TABLE IF NOT EXISTS lm_sports_credit_usage (
        id INT AUTO_INCREMENT PRIMARY KEY,
        request_time DATETIME NOT NULL,
        sport VARCHAR(50) NOT NULL DEFAULT 'all',
        credits_used INT NOT NULL DEFAULT 0,
        credits_remaining INT DEFAULT NULL,
        KEY idx_time (request_time)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 3. CLV (Closing Line Value) Tracking ──
    $conn->query("CREATE TABLE IF NOT EXISTS lm_sports_clv (
        id INT AUTO_INCREMENT PRIMARY KEY,
        event_id VARCHAR(100) NOT NULL,
        sport VARCHAR(50) NOT NULL DEFAULT '',
        home_team VARCHAR(100) NOT NULL DEFAULT '',
        away_team VARCHAR(100) NOT NULL DEFAULT '',
        commence_time DATETIME NOT NULL,
        bookmaker_key VARCHAR(50) NOT NULL DEFAULT '',
        market VARCHAR(20) NOT NULL DEFAULT 'h2h',
        outcome_name VARCHAR(100) NOT NULL DEFAULT '',
        opening_price DECIMAL(10,4) NOT NULL DEFAULT 0,
        closing_price DECIMAL(10,4) DEFAULT NULL,
        opening_implied_prob DECIMAL(8,6) DEFAULT NULL,
        closing_implied_prob DECIMAL(8,6) DEFAULT NULL,
        clv_pct DECIMAL(8,4) DEFAULT NULL,
        first_seen DATETIME NOT NULL,
        last_updated DATETIME NOT NULL,
        UNIQUE KEY idx_clv_unique (event_id, bookmaker_key, market, outcome_name),
        KEY idx_clv_sport (sport),
        KEY idx_clv_commence (commence_time)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 4. Value Bets ──
    $conn->query("CREATE TABLE IF NOT EXISTS lm_sports_value_bets (
        id INT AUTO_INCREMENT PRIMARY KEY,
        event_id VARCHAR(100) NOT NULL,
        sport VARCHAR(50) NOT NULL,
        home_team VARCHAR(100) NOT NULL,
        away_team VARCHAR(100) NOT NULL,
        commence_time DATETIME NOT NULL,
        market VARCHAR(20) NOT NULL,
        bet_type VARCHAR(50) NOT NULL,
        outcome_name VARCHAR(100) NOT NULL DEFAULT '',
        best_book VARCHAR(50) NOT NULL,
        best_book_key VARCHAR(50) NOT NULL DEFAULT '',
        best_odds DECIMAL(10,4) NOT NULL DEFAULT 0,
        consensus_implied_prob DECIMAL(6,4) NOT NULL DEFAULT 0,
        true_prob DECIMAL(6,4) NOT NULL DEFAULT 0,
        edge_pct DECIMAL(6,2) NOT NULL DEFAULT 0,
        ev_pct DECIMAL(6,2) NOT NULL DEFAULT 0,
        kelly_fraction DECIMAL(6,4) NOT NULL DEFAULT 0,
        kelly_bet DECIMAL(10,2) NOT NULL DEFAULT 0,
        all_odds TEXT,
        detected_at DATETIME NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'active',
        KEY idx_sport (sport),
        KEY idx_status (status),
        KEY idx_ev (ev_pct),
        KEY idx_event (event_id),
        KEY idx_commence (commence_time)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 5. Daily Picks (timestamped historical picks) ──
    $conn->query("CREATE TABLE IF NOT EXISTS lm_sports_daily_picks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pick_date DATE NOT NULL,
        generated_at DATETIME NOT NULL,
        sport VARCHAR(50) NOT NULL,
        event_id VARCHAR(100) NOT NULL,
        home_team VARCHAR(100) NOT NULL,
        away_team VARCHAR(100) NOT NULL,
        commence_time DATETIME NOT NULL,
        market VARCHAR(20) NOT NULL,
        pick_type VARCHAR(50) NOT NULL DEFAULT '',
        outcome_name VARCHAR(100) NOT NULL DEFAULT '',
        best_book VARCHAR(50) NOT NULL DEFAULT '',
        best_book_key VARCHAR(50) NOT NULL DEFAULT '',
        best_odds DECIMAL(10,4) NOT NULL DEFAULT 0,
        ev_pct DECIMAL(6,2) NOT NULL DEFAULT 0,
        kelly_bet DECIMAL(10,2) NOT NULL DEFAULT 0,
        algorithm VARCHAR(50) NOT NULL DEFAULT 'value_bet',
        confidence VARCHAR(20) NOT NULL DEFAULT 'medium',
        result VARCHAR(20) DEFAULT NULL,
        pnl DECIMAL(10,2) DEFAULT NULL,
        all_odds TEXT,
        KEY idx_date (pick_date),
        KEY idx_sport (sport),
        KEY idx_event (event_id),
        KEY idx_result (result)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 6. Paper Bets ──
    $conn->query("CREATE TABLE IF NOT EXISTS lm_sports_bets (
        id INT AUTO_INCREMENT PRIMARY KEY,
        event_id VARCHAR(100) NOT NULL,
        sport VARCHAR(50) NOT NULL,
        home_team VARCHAR(100) NOT NULL,
        away_team VARCHAR(100) NOT NULL,
        commence_time DATETIME NOT NULL,
        game_date DATE DEFAULT NULL,
        bet_type VARCHAR(30) NOT NULL DEFAULT 'moneyline',
        market VARCHAR(20) NOT NULL DEFAULT 'h2h',
        pick VARCHAR(100) NOT NULL,
        pick_point DECIMAL(6,2) DEFAULT NULL,
        bookmaker VARCHAR(50) NOT NULL,
        bookmaker_key VARCHAR(50) NOT NULL DEFAULT '',
        odds DECIMAL(10,4) NOT NULL DEFAULT 0,
        implied_prob DECIMAL(6,4) NOT NULL DEFAULT 0,
        bet_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
        potential_payout DECIMAL(10,2) NOT NULL DEFAULT 0,
        algorithm VARCHAR(50) NOT NULL DEFAULT 'value_bet',
        ev_pct DECIMAL(6,2) NOT NULL DEFAULT 0,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        result VARCHAR(20) DEFAULT NULL,
        pnl DECIMAL(10,2) DEFAULT NULL,
        settled_at DATETIME DEFAULT NULL,
        actual_home_score INT DEFAULT NULL,
        actual_away_score INT DEFAULT NULL,
        placed_at DATETIME NOT NULL,
        KEY idx_status (status),
        KEY idx_sport (sport),
        KEY idx_algorithm (algorithm),
        KEY idx_placed (placed_at),
        KEY idx_event (event_id),
        KEY idx_game_date (game_date)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 7. Bankroll Snapshots ──
    $conn->query("CREATE TABLE IF NOT EXISTS lm_sports_bankroll (
        id INT AUTO_INCREMENT PRIMARY KEY,
        snapshot_date DATE NOT NULL,
        bankroll DECIMAL(10,2) NOT NULL DEFAULT 1000,
        total_bets INT NOT NULL DEFAULT 0,
        total_wins INT NOT NULL DEFAULT 0,
        total_losses INT NOT NULL DEFAULT 0,
        total_pushes INT NOT NULL DEFAULT 0,
        win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
        total_wagered DECIMAL(10,2) NOT NULL DEFAULT 0,
        total_pnl DECIMAL(10,2) NOT NULL DEFAULT 0,
        roi_pct DECIMAL(6,2) NOT NULL DEFAULT 0,
        UNIQUE KEY idx_date (snapshot_date)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
}
?>
