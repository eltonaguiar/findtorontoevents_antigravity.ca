<?php
/**
 * smart_money_schema.php — Schema for Smart Money Intelligence system.
 * 9 tables: analyst ratings, price targets, insider sentiment, consensus,
 * WSB sentiment, guru tracker, guru picks, signal performance, challenger showdown.
 * PHP 5.2 compatible.
 */

function _sm_ensure_schema($conn) {

    // ── 1. Analyst Ratings (Finnhub recommendation history) ──
    $conn->query("CREATE TABLE IF NOT EXISTS lm_analyst_ratings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ticker VARCHAR(10) NOT NULL,
        period DATE NOT NULL,
        strong_buy INT NOT NULL DEFAULT 0,
        buy INT NOT NULL DEFAULT 0,
        hold INT NOT NULL DEFAULT 0,
        sell INT NOT NULL DEFAULT 0,
        strong_sell INT NOT NULL DEFAULT 0,
        fetch_date DATE NOT NULL,
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_ticker_period (ticker, period),
        KEY idx_ticker (ticker),
        KEY idx_date (fetch_date)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 2. Price Targets (Finnhub analyst consensus targets) ──
    $conn->query("CREATE TABLE IF NOT EXISTS lm_price_targets (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ticker VARCHAR(10) NOT NULL,
        target_high DECIMAL(12,2) NOT NULL DEFAULT 0,
        target_low DECIMAL(12,2) NOT NULL DEFAULT 0,
        target_mean DECIMAL(12,2) NOT NULL DEFAULT 0,
        target_median DECIMAL(12,2) NOT NULL DEFAULT 0,
        last_updated DATE NOT NULL,
        fetch_date DATE NOT NULL,
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_ticker (ticker),
        KEY idx_date (fetch_date)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 3. Insider Sentiment — Finnhub MSPR (Monthly Share Purchase Ratio) ──
    $conn->query("CREATE TABLE IF NOT EXISTS lm_insider_sentiment (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ticker VARCHAR(10) NOT NULL,
        year INT NOT NULL,
        month INT NOT NULL,
        mspr DECIMAL(10,4) NOT NULL DEFAULT 0,
        change_val DECIMAL(18,2) NOT NULL DEFAULT 0,
        fetch_date DATE NOT NULL,
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_ticker_ym (ticker, year, month),
        KEY idx_ticker (ticker),
        KEY idx_date (fetch_date)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 4. Smart Consensus — computed scores combining all data sources ──
    $conn->query("CREATE TABLE IF NOT EXISTS lm_smart_consensus (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ticker VARCHAR(10) NOT NULL,
        calc_date DATE NOT NULL,
        overall_score INT NOT NULL DEFAULT 0,
        technical_score INT NOT NULL DEFAULT 0,
        smart_money_score INT NOT NULL DEFAULT 0,
        insider_score INT NOT NULL DEFAULT 0,
        analyst_score INT NOT NULL DEFAULT 0,
        momentum_score INT NOT NULL DEFAULT 0,
        social_score INT NOT NULL DEFAULT 0,
        signal_direction VARCHAR(10) NOT NULL DEFAULT '',
        confidence VARCHAR(20) NOT NULL DEFAULT '',
        regime VARCHAR(20) NOT NULL DEFAULT 'neutral',
        explanation TEXT,
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_ticker_date (ticker, calc_date),
        KEY idx_ticker (ticker),
        KEY idx_score (overall_score),
        KEY idx_date (calc_date),
        KEY idx_direction (signal_direction)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 5. WSB Sentiment — Reddit WallStreetBets mentions & sentiment ──
    $conn->query("CREATE TABLE IF NOT EXISTS lm_wsb_sentiment (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ticker VARCHAR(10) NOT NULL,
        scan_date DATE NOT NULL,
        mentions_24h INT NOT NULL DEFAULT 0,
        sentiment DECIMAL(5,3) NOT NULL DEFAULT 0,
        total_upvotes INT NOT NULL DEFAULT 0,
        wsb_score DECIMAL(8,2) NOT NULL DEFAULT 0,
        top_post_title VARCHAR(200) NOT NULL DEFAULT '',
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_ticker_date (ticker, scan_date),
        KEY idx_ticker (ticker),
        KEY idx_date (scan_date),
        KEY idx_score (wsb_score)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 6. Guru Tracker — public stock/sports gurus performance ──
    $conn->query("CREATE TABLE IF NOT EXISTS lm_guru_tracker (
        id INT AUTO_INCREMENT PRIMARY KEY,
        guru_name VARCHAR(100) NOT NULL,
        platform VARCHAR(50) NOT NULL DEFAULT '',
        specialty VARCHAR(50) NOT NULL DEFAULT '',
        tracked_since DATE NOT NULL,
        total_picks INT NOT NULL DEFAULT 0,
        wins INT NOT NULL DEFAULT 0,
        losses INT NOT NULL DEFAULT 0,
        win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
        roi_percent DECIMAL(8,2) NOT NULL DEFAULT 0,
        avg_return DECIMAL(8,2) NOT NULL DEFAULT 0,
        credibility_score INT NOT NULL DEFAULT 0,
        last_updated DATE NOT NULL,
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_name_platform (guru_name, platform),
        KEY idx_credibility (credibility_score),
        KEY idx_winrate (win_rate)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 7. Guru Picks — individual picks from tracked gurus ──
    $conn->query("CREATE TABLE IF NOT EXISTS lm_guru_picks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        guru_id INT NOT NULL DEFAULT 0,
        pick_type VARCHAR(20) NOT NULL DEFAULT '',
        ticker_or_team VARCHAR(50) NOT NULL DEFAULT '',
        pick_description VARCHAR(255) NOT NULL DEFAULT '',
        odds_or_target DECIMAL(10,2) NOT NULL DEFAULT 0,
        source_url VARCHAR(255) NOT NULL DEFAULT '',
        posted_at DATETIME NOT NULL,
        result VARCHAR(20) NOT NULL DEFAULT 'pending',
        profit_loss DECIMAL(8,2) NOT NULL DEFAULT 0,
        resolved_at DATE DEFAULT NULL,
        created_at DATETIME NOT NULL,
        KEY idx_guru (guru_id),
        KEY idx_result (result),
        KEY idx_ticker (ticker_or_team),
        KEY idx_date (posted_at)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 8. Signal Performance — track each signal source accuracy over time ──
    $conn->query("CREATE TABLE IF NOT EXISTS lm_signal_performance (
        id INT AUTO_INCREMENT PRIMARY KEY,
        signal_source VARCHAR(50) NOT NULL,
        ticker VARCHAR(10) NOT NULL,
        signal_date DATE NOT NULL,
        signal_direction VARCHAR(10) NOT NULL DEFAULT '',
        entry_price DECIMAL(12,2) NOT NULL DEFAULT 0,
        price_7d DECIMAL(12,2) NOT NULL DEFAULT 0,
        price_30d DECIMAL(12,2) NOT NULL DEFAULT 0,
        price_90d DECIMAL(12,2) NOT NULL DEFAULT 0,
        return_7d DECIMAL(8,2) NOT NULL DEFAULT 0,
        return_30d DECIMAL(8,2) NOT NULL DEFAULT 0,
        return_90d DECIMAL(8,2) NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_source_ticker_date (signal_source, ticker, signal_date),
        KEY idx_source (signal_source),
        KEY idx_ticker (ticker),
        KEY idx_date (signal_date)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 9. Challenger Showdown — head-to-head Challenger Bot vs existing algos ──
    $conn->query("CREATE TABLE IF NOT EXISTS lm_challenger_showdown (
        id INT AUTO_INCREMENT PRIMARY KEY,
        period_start DATE NOT NULL,
        period_end DATE NOT NULL,
        challenger_trades INT NOT NULL DEFAULT 0,
        challenger_wins INT NOT NULL DEFAULT 0,
        challenger_win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
        challenger_pnl DECIMAL(12,2) NOT NULL DEFAULT 0,
        challenger_sharpe DECIMAL(6,3) NOT NULL DEFAULT 0,
        challenger_max_dd DECIMAL(6,2) NOT NULL DEFAULT 0,
        best_algo_name VARCHAR(100) NOT NULL DEFAULT '',
        best_algo_trades INT NOT NULL DEFAULT 0,
        best_algo_wins INT NOT NULL DEFAULT 0,
        best_algo_win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
        best_algo_pnl DECIMAL(12,2) NOT NULL DEFAULT 0,
        best_algo_sharpe DECIMAL(6,3) NOT NULL DEFAULT 0,
        best_algo_max_dd DECIMAL(6,2) NOT NULL DEFAULT 0,
        challenger_rank INT NOT NULL DEFAULT 0,
        total_algos INT NOT NULL DEFAULT 0,
        snapshot_date DATE NOT NULL,
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_period (period_start, period_end, snapshot_date),
        KEY idx_snapshot (snapshot_date)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
}
?>
