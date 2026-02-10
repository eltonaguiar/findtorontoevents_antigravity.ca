<?php
/**
 * goldmine_schema.php — Schema for the Multi-Page Goldmine Checker.
 * 6 tables: unified picks archive, system health, failure alerts,
 * SEC insider trades, SEC 13F holdings, news sentiment.
 * PHP 5.2 compatible.
 */

function _gm_ensure_schema($conn) {

    // ── 1. Unified Picks Archive ──
    $conn->query("CREATE TABLE IF NOT EXISTS gm_unified_picks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        source_system VARCHAR(30) NOT NULL,
        source_page VARCHAR(100) NOT NULL DEFAULT '',
        source_id INT NOT NULL DEFAULT 0,
        source_table VARCHAR(50) NOT NULL DEFAULT '',
        pick_date DATE NOT NULL,
        pick_time DATETIME NOT NULL,
        asset_type VARCHAR(20) NOT NULL DEFAULT 'stock',
        ticker VARCHAR(30) NOT NULL,
        asset_name VARCHAR(200) NOT NULL DEFAULT '',
        direction VARCHAR(10) NOT NULL DEFAULT 'LONG',
        algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
        algo_count INT NOT NULL DEFAULT 1,
        entry_price DECIMAL(18,8) NOT NULL DEFAULT 0,
        target_price DECIMAL(18,8) NOT NULL DEFAULT 0,
        stop_loss_price DECIMAL(18,8) NOT NULL DEFAULT 0,
        target_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
        stop_loss_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
        confidence_score INT NOT NULL DEFAULT 0,
        hold_period_hours INT NOT NULL DEFAULT 0,
        metadata_json TEXT,
        status VARCHAR(20) NOT NULL DEFAULT 'open',
        current_price DECIMAL(18,8) NOT NULL DEFAULT 0,
        current_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
        peak_price DECIMAL(18,8) NOT NULL DEFAULT 0,
        trough_price DECIMAL(18,8) NOT NULL DEFAULT 0,
        exit_price DECIMAL(18,8) NOT NULL DEFAULT 0,
        exit_date DATETIME DEFAULT NULL,
        exit_reason VARCHAR(50) NOT NULL DEFAULT '',
        final_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
        hold_hours DECIMAL(10,2) NOT NULL DEFAULT 0,
        dividends_earned DECIMAL(10,4) NOT NULL DEFAULT 0,
        earnings_events INT NOT NULL DEFAULT 0,
        total_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        UNIQUE KEY idx_source_dedup (source_system, source_table, source_id, pick_date),
        KEY idx_status (status),
        KEY idx_source (source_system),
        KEY idx_ticker (ticker),
        KEY idx_date (pick_date),
        KEY idx_asset_type (asset_type),
        KEY idx_algorithm (algorithm_name),
        KEY idx_confidence (confidence_score)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 2. System Health — daily performance snapshot per system ──
    $conn->query("CREATE TABLE IF NOT EXISTS gm_system_health (
        id INT AUTO_INCREMENT PRIMARY KEY,
        snap_date DATE NOT NULL,
        source_system VARCHAR(30) NOT NULL,
        total_picks INT NOT NULL DEFAULT 0,
        closed_picks INT NOT NULL DEFAULT 0,
        wins INT NOT NULL DEFAULT 0,
        losses INT NOT NULL DEFAULT 0,
        expired INT NOT NULL DEFAULT 0,
        win_rate DECIMAL(6,2) NOT NULL DEFAULT 0,
        avg_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
        total_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
        avg_hold_hours DECIMAL(10,2) NOT NULL DEFAULT 0,
        best_pick_ticker VARCHAR(30) NOT NULL DEFAULT '',
        best_pick_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
        worst_pick_ticker VARCHAR(30) NOT NULL DEFAULT '',
        worst_pick_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
        accuracy_7d DECIMAL(6,2) NOT NULL DEFAULT 0,
        accuracy_30d DECIMAL(6,2) NOT NULL DEFAULT 0,
        is_failing INT NOT NULL DEFAULT 0,
        failure_reason TEXT,
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_date_system (snap_date, source_system),
        KEY idx_date (snap_date),
        KEY idx_failing (is_failing)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 3. Failure Alerts ──
    $conn->query("CREATE TABLE IF NOT EXISTS gm_failure_alerts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        alert_date DATE NOT NULL,
        source_system VARCHAR(30) NOT NULL,
        alert_type VARCHAR(30) NOT NULL,
        severity VARCHAR(10) NOT NULL DEFAULT 'warning',
        title VARCHAR(200) NOT NULL DEFAULT '',
        description TEXT,
        affected_tickers TEXT,
        metric_value DECIMAL(10,4) NOT NULL DEFAULT 0,
        threshold_value DECIMAL(10,4) NOT NULL DEFAULT 0,
        page_url VARCHAR(200) NOT NULL DEFAULT '',
        is_active INT NOT NULL DEFAULT 1,
        resolved_at DATETIME DEFAULT NULL,
        created_at DATETIME NOT NULL,
        KEY idx_active (is_active),
        KEY idx_date (alert_date),
        KEY idx_system (source_system)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 4. SEC Insider Trades (Form 4) ──
    $conn->query("CREATE TABLE IF NOT EXISTS gm_sec_insider_trades (
        id INT AUTO_INCREMENT PRIMARY KEY,
        cik VARCHAR(20) NOT NULL,
        ticker VARCHAR(10) NOT NULL,
        filer_name VARCHAR(200) NOT NULL DEFAULT '',
        filer_title VARCHAR(100) NOT NULL DEFAULT '',
        transaction_date DATE NOT NULL,
        transaction_type VARCHAR(10) NOT NULL DEFAULT '',
        shares DECIMAL(18,4) NOT NULL DEFAULT 0,
        price_per_share DECIMAL(12,4) NOT NULL DEFAULT 0,
        total_value DECIMAL(18,2) NOT NULL DEFAULT 0,
        shares_owned_after DECIMAL(18,4) NOT NULL DEFAULT 0,
        filing_date DATE NOT NULL,
        accession_number VARCHAR(30) NOT NULL DEFAULT '',
        is_director INT NOT NULL DEFAULT 0,
        is_officer INT NOT NULL DEFAULT 0,
        is_ten_pct_owner INT NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_accession (accession_number, ticker, transaction_type, transaction_date),
        KEY idx_ticker (ticker),
        KEY idx_date (transaction_date),
        KEY idx_filing (filing_date),
        KEY idx_type (transaction_type)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 5. SEC 13F Holdings ──
    $conn->query("CREATE TABLE IF NOT EXISTS gm_sec_13f_holdings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        cik VARCHAR(20) NOT NULL,
        fund_name VARCHAR(200) NOT NULL DEFAULT '',
        ticker VARCHAR(10) NOT NULL DEFAULT '',
        cusip VARCHAR(9) NOT NULL,
        name_of_issuer VARCHAR(200) NOT NULL DEFAULT '',
        value_thousands BIGINT NOT NULL DEFAULT 0,
        shares BIGINT NOT NULL DEFAULT 0,
        filing_quarter VARCHAR(10) NOT NULL,
        filing_date DATE NOT NULL,
        prev_shares BIGINT NOT NULL DEFAULT 0,
        change_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
        change_type VARCHAR(20) NOT NULL DEFAULT '',
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_fund_cusip_q (cik, cusip, filing_quarter),
        KEY idx_ticker (ticker),
        KEY idx_quarter (filing_quarter),
        KEY idx_change (change_type),
        KEY idx_fund (cik)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // ── 6. News Sentiment ──
    $conn->query("CREATE TABLE IF NOT EXISTS gm_news_sentiment (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ticker VARCHAR(10) NOT NULL,
        fetch_date DATE NOT NULL,
        articles_analyzed INT NOT NULL DEFAULT 0,
        sentiment_score DECIMAL(6,4) NOT NULL DEFAULT 0,
        positive_count INT NOT NULL DEFAULT 0,
        negative_count INT NOT NULL DEFAULT 0,
        neutral_count INT NOT NULL DEFAULT 0,
        buzz_score DECIMAL(8,4) NOT NULL DEFAULT 0,
        sector_avg_sentiment DECIMAL(6,4) NOT NULL DEFAULT 0,
        relative_sentiment DECIMAL(6,4) NOT NULL DEFAULT 0,
        source VARCHAR(20) NOT NULL DEFAULT 'finnhub',
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_ticker_date (ticker, fetch_date),
        KEY idx_date (fetch_date),
        KEY idx_sentiment (sentiment_score)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
}
?>
