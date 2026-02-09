<?php
/**
 * Schema setup for dividend and earnings data tables.
 * Creates 3 tables: stock_dividends, stock_earnings, stock_fundamentals.
 * PHP 5.2 compatible.
 *
 * Usage: GET .../dividend_earnings_schema.php
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'actions' => array());

$tables = array(

// 1. Dividend history
"CREATE TABLE IF NOT EXISTS stock_dividends (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    ex_date DATE NOT NULL,
    payment_date DATE DEFAULT NULL,
    amount DECIMAL(10,6) NOT NULL DEFAULT 0,
    frequency VARCHAR(20) NOT NULL DEFAULT 'quarterly',
    source VARCHAR(20) NOT NULL DEFAULT 'yahoo_v8',
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_ticker_exdate (ticker, ex_date),
    KEY idx_exdate (ex_date),
    KEY idx_ticker (ticker)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 2. Quarterly earnings history
"CREATE TABLE IF NOT EXISTS stock_earnings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    quarter_end DATE NOT NULL,
    earnings_date DATE DEFAULT NULL,
    eps_actual DECIMAL(10,4) DEFAULT NULL,
    eps_estimate DECIMAL(10,4) DEFAULT NULL,
    eps_surprise DECIMAL(10,4) DEFAULT NULL,
    surprise_pct DECIMAL(10,4) DEFAULT NULL,
    revenue_actual BIGINT DEFAULT NULL,
    revenue_estimate BIGINT DEFAULT NULL,
    source VARCHAR(20) NOT NULL DEFAULT 'yahoo_v10',
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_ticker_quarter (ticker, quarter_end),
    KEY idx_earnings_date (earnings_date),
    KEY idx_ticker (ticker)
) ENGINE=MyISAM DEFAULT CHARSET=utf8",

// 3. Current fundamentals snapshot (one row per ticker)
"CREATE TABLE IF NOT EXISTS stock_fundamentals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    trailing_eps DECIMAL(10,4) DEFAULT NULL,
    forward_eps DECIMAL(10,4) DEFAULT NULL,
    trailing_pe DECIMAL(10,4) DEFAULT NULL,
    forward_pe DECIMAL(10,4) DEFAULT NULL,
    peg_ratio DECIMAL(10,4) DEFAULT NULL,
    dividend_rate DECIMAL(10,4) DEFAULT NULL,
    dividend_yield DECIMAL(10,6) DEFAULT NULL,
    trailing_annual_div_rate DECIMAL(10,4) DEFAULT NULL,
    trailing_annual_div_yield DECIMAL(10,6) DEFAULT NULL,
    five_yr_avg_div_yield DECIMAL(10,6) DEFAULT NULL,
    payout_ratio DECIMAL(10,4) DEFAULT NULL,
    ex_dividend_date DATE DEFAULT NULL,
    next_earnings_date DATE DEFAULT NULL,
    price_to_book DECIMAL(10,4) DEFAULT NULL,
    enterprise_to_revenue DECIMAL(10,4) DEFAULT NULL,
    total_revenue BIGINT DEFAULT NULL,
    ebitda BIGINT DEFAULT NULL,
    total_debt BIGINT DEFAULT NULL,
    current_ratio DECIMAL(10,4) DEFAULT NULL,
    roe DECIMAL(10,4) DEFAULT NULL,
    gross_margins DECIMAL(10,4) DEFAULT NULL,
    operating_margins DECIMAL(10,4) DEFAULT NULL,
    recommendation_key VARCHAR(20) DEFAULT NULL,
    target_mean_price DECIMAL(10,4) DEFAULT NULL,
    source VARCHAR(20) NOT NULL DEFAULT 'yahoo_v10',
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_ticker (ticker)
) ENGINE=MyISAM DEFAULT CHARSET=utf8"

);

foreach ($tables as $sql) {
    if ($conn->query($sql)) {
        // Extract table name for status message
        $matches = array();
        if (preg_match('/CREATE TABLE IF NOT EXISTS (\w+)/', $sql, $matches)) {
            $results['actions'][] = 'OK: ' . $matches[1];
        } else {
            $results['actions'][] = 'OK';
        }
    } else {
        $results['ok'] = false;
        $results['actions'][] = 'FAIL: ' . $conn->error;
    }
}

echo json_encode($results);
$conn->close();
?>
