<?php
/**
 * KIMI Goldmine Database Schema
 * Central tracking system for all prediction picks across all asset classes
 * 
 * Tables:
 * - KIMI_GOLDMINE_PICKS: Every pick from every source
 * - KIMI_GOLDMINE_PERFORMANCE: Aggregated performance metrics
 * - KIMI_GOLDMINE_WINNERS: High-performing picks that meet criteria
 * - KIMI_GOLDMINE_SOURCES: Metadata for each prediction source
 * - KIMI_GOLDMINE_ALERTS: Notifications for significant events
 */

require_once dirname(__FILE__) . '/../../../findstocks/portfolio2/api/db_connect.php';

$tables = array();

// ─────────────────────────────────────────────────────────────────────────────
// MAIN TABLE: All picks from all sources
// ─────────────────────────────────────────────────────────────────────────────
$tables['KIMI_GOLDMINE_PICKS'] = "CREATE TABLE IF NOT EXISTS KIMI_GOLDMINE_PICKS (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pick_uuid VARCHAR(64) NOT NULL UNIQUE,
    source_type ENUM('stock', 'penny_stock', 'crypto', 'meme_coin', 'forex', 'mutual_fund', 'sports', 'alpha_engine') NOT NULL,
    source_name VARCHAR(100) NOT NULL,
    algorithm_name VARCHAR(100) NOT NULL,
    asset_symbol VARCHAR(50) NOT NULL,
    asset_name VARCHAR(200),
    pick_direction ENUM('long', 'short', 'neutral', 'over', 'under', 'spread') NOT NULL DEFAULT 'long',
    entry_price DECIMAL(15,6),
    entry_price_actual DECIMAL(15,6),
    target_price DECIMAL(15,6),
    stop_loss DECIMAL(15,6),
    target_pct DECIMAL(6,2),
    stop_pct DECIMAL(6,2),
    confidence_score INT(3),
    kelly_fraction DECIMAL(6,4),
    suggested_position DECIMAL(10,2),
    timeframe_days INT,
    pick_date DATETIME NOT NULL,
    pick_timestamp INT(11),
    expected_exit_date DATE,
    
    -- Current tracking
    current_price DECIMAL(15,6),
    current_return_pct DECIMAL(10,4),
    current_pnl DECIMAL(15,4),
    highest_price DECIMAL(15,6),
    lowest_price DECIMAL(15,6),
    peak_return_pct DECIMAL(10,4),
    
    -- Exit tracking
    exit_price DECIMAL(15,6),
    exit_date DATETIME,
    exit_return_pct DECIMAL(10,4),
    exit_pnl DECIMAL(15,4),
    exit_reason ENUM('target_hit', 'stop_hit', 'time_exit', 'manual', 'expired', 'active'),
    
    -- Status
    status ENUM('pending', 'active', 'target_hit', 'stop_hit', 'partial_exit', 'closed', 'expired') DEFAULT 'pending',
    
    -- Raw data storage
    raw_data JSON,
    factors_json JSON,
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resolved_at DATETIME,
    
    -- Indexes
    KEY idx_source_type (source_type),
    KEY idx_source_name (source_name),
    KEY idx_algorithm (algorithm_name),
    KEY idx_symbol (asset_symbol),
    KEY idx_pick_date (pick_date),
    KEY idx_status (status),
    KEY idx_expected_exit (expected_exit_date),
    KEY idx_return (current_return_pct),
    KEY idx_source_symbol_date (source_type, asset_symbol, pick_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";

// ─────────────────────────────────────────────────────────────────────────────
// PERFORMANCE TABLE: Aggregated metrics by source/algorithm
// ─────────────────────────────────────────────────────────────────────────────
$tables['KIMI_GOLDMINE_PERFORMANCE'] = "CREATE TABLE IF NOT EXISTS KIMI_GOLDMINE_PERFORMANCE (
    id INT AUTO_INCREMENT PRIMARY KEY,
    period VARCHAR(20) NOT NULL COMMENT 'daily, weekly, monthly, quarterly, yearly, all_time',
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    
    source_type ENUM('stock', 'penny_stock', 'crypto', 'meme_coin', 'forex', 'mutual_fund', 'sports', 'alpha_engine') NOT NULL,
    source_name VARCHAR(100) NOT NULL,
    algorithm_name VARCHAR(100),
    
    -- Pick counts
    total_picks INT DEFAULT 0,
    active_picks INT DEFAULT 0,
    resolved_picks INT DEFAULT 0,
    winning_picks INT DEFAULT 0,
    losing_picks INT DEFAULT 0,
    
    -- Win rates
    win_rate_pct DECIMAL(6,2),
    win_rate_significance VARCHAR(20) COMMENT 'weak, moderate, strong, very_strong based on sample size',
    
    -- Returns
    avg_return_pct DECIMAL(10,4),
    median_return_pct DECIMAL(10,4),
    best_pick_return DECIMAL(10,4),
    worst_pick_return DECIMAL(10,4),
    total_return_pct DECIMAL(10,4),
    
    -- Risk metrics
    sharpe_ratio DECIMAL(8,4),
    sortino_ratio DECIMAL(8,4),
    max_drawdown_pct DECIMAL(8,4),
    profit_factor DECIMAL(8,4),
    expectancy DECIMAL(10,4),
    
    -- Consistency
    consecutive_wins INT DEFAULT 0,
    consecutive_losses INT DEFAULT 0,
    streak_status ENUM('hot', 'cold', 'neutral') DEFAULT 'neutral',
    
    -- Time in trade
    avg_days_held DECIMAL(6,2),
    avg_days_to_target DECIMAL(6,2),
    avg_days_to_stop DECIMAL(6,2),
    
    -- Ranking
    rank_by_return INT,
    rank_by_sharpe INT,
    rank_by_winrate INT,
    overall_score DECIMAL(6,2) COMMENT 'Composite 0-100 score',
    
    -- Status
    is_goldmine_worthy BOOLEAN DEFAULT FALSE COMMENT 'Meets criteria for goldmine status',
    goldmine_reason VARCHAR(255),
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    KEY idx_period (period, period_start),
    KEY idx_source (source_type, source_name),
    KEY idx_algorithm (algorithm_name),
    KEY idx_overall_score (overall_score),
    KEY idx_goldmine (is_goldmine_worthy),
    UNIQUE KEY idx_unique_period_source (period, source_type, source_name, algorithm_name, period_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";

// ─────────────────────────────────────────────────────────────────────────────
// WINNERS TABLE: Picks that have demonstrated exceptional performance
// ─────────────────────────────────────────────────────────────────────────────
$tables['KIMI_GOLDMINE_WINNERS'] = "CREATE TABLE IF NOT EXISTS KIMI_GOLDMINE_WINNERS (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pick_uuid VARCHAR(64) NOT NULL,
    source_type ENUM('stock', 'penny_stock', 'crypto', 'meme_coin', 'forex', 'mutual_fund', 'sports', 'alpha_engine') NOT NULL,
    source_name VARCHAR(100) NOT NULL,
    algorithm_name VARCHAR(100) NOT NULL,
    asset_symbol VARCHAR(50) NOT NULL,
    asset_name VARCHAR(200),
    
    -- Entry details
    entry_price DECIMAL(15,6),
    pick_date DATETIME,
    
    -- Performance achieved
    exit_price DECIMAL(15,6),
    exit_return_pct DECIMAL(10,4),
    exit_date DATETIME,
    days_held INT,
    
    -- Why it's a winner
    winner_category ENUM('mega_winner', 'consistent_performer', 'quick_hit', 'comeback_kid', 'hidden_gem') NOT NULL,
    winner_reason TEXT,
    
    -- Benchmarks
    outperformed_spy BOOLEAN DEFAULT FALSE,
    spy_return_same_period DECIMAL(10,4),
    alpha_generated DECIMAL(10,4),
    
    -- Recognition
    featured_date DATE,
    featured_in_newsletter BOOLEAN DEFAULT FALSE,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    KEY idx_winner_category (winner_category),
    KEY idx_source (source_type, source_name),
    KEY idx_return (exit_return_pct),
    KEY idx_featured (featured_date),
    FOREIGN KEY (pick_uuid) REFERENCES KIMI_GOLDMINE_PICKS(pick_uuid) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";

// ─────────────────────────────────────────────────────────────────────────────
// SOURCES TABLE: Metadata for each prediction source
// ─────────────────────────────────────────────────────────────────────────────
$tables['KIMI_GOLDMINE_SOURCES'] = "CREATE TABLE IF NOT EXISTS KIMI_GOLDMINE_SOURCES (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_type ENUM('stock', 'penny_stock', 'crypto', 'meme_coin', 'forex', 'mutual_fund', 'sports', 'alpha_engine') NOT NULL,
    source_name VARCHAR(100) NOT NULL,
    source_slug VARCHAR(100) NOT NULL,
    algorithm_name VARCHAR(100),
    algorithm_slug VARCHAR(100),
    
    -- Description
    display_name VARCHAR(200),
    description TEXT,
    strategy_type VARCHAR(100),
    ideal_timeframe VARCHAR(50),
    risk_level ENUM('low', 'medium', 'high', 'very_high') DEFAULT 'medium',
    
    -- Configuration
    is_active BOOLEAN DEFAULT TRUE,
    auto_import BOOLEAN DEFAULT TRUE,
    import_frequency VARCHAR(20) COMMENT 'realtime, hourly, daily',
    
    -- Source API endpoint
    source_api_endpoint VARCHAR(500),
    source_db_table VARCHAR(100),
    
    -- Performance thresholds for goldmine status
    min_win_rate_for_goldmine DECIMAL(5,2) DEFAULT 55.00,
    min_return_for_goldmine DECIMAL(6,2) DEFAULT 10.00,
    min_sharpe_for_goldmine DECIMAL(5,2) DEFAULT 1.00,
    min_samples_for_goldmine INT DEFAULT 10,
    
    -- Current status
    current_goldmine_status BOOLEAN DEFAULT FALSE,
    goldmine_achieved_date DATE,
    goldmine_lost_date DATE,
    total_goldmine_periods INT DEFAULT 0,
    
    -- Stats (denormalized for quick access)
    total_picks_all_time INT DEFAULT 0,
    total_wins_all_time INT DEFAULT 0,
    avg_return_all_time DECIMAL(10,4),
    best_streak INT DEFAULT 0,
    worst_streak INT DEFAULT 0,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY idx_source_slug (source_slug, algorithm_slug),
    KEY idx_source_type (source_type),
    KEY idx_goldmine_status (current_goldmine_status),
    KEY idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";

// ─────────────────────────────────────────────────────────────────────────────
// ALERTS TABLE: Notifications for significant events
// ─────────────────────────────────────────────────────────────────────────────
$tables['KIMI_GOLDMINE_ALERTS'] = "CREATE TABLE IF NOT EXISTS KIMI_GOLDMINE_ALERTS (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alert_type ENUM('new_goldmine', 'goldmine_lost', 'streak_hot', 'streak_cold', 'mega_winner', 'major_drawdown', 'system_error') NOT NULL,
    severity ENUM('info', 'warning', 'critical') DEFAULT 'info',
    
    source_type VARCHAR(50),
    source_name VARCHAR(100),
    algorithm_name VARCHAR(100),
    asset_symbol VARCHAR(50),
    pick_uuid VARCHAR(64),
    
    title VARCHAR(255),
    message TEXT,
    details_json JSON,
    
    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at DATETIME,
    read_by VARCHAR(100),
    
    -- Actions taken
    action_taken VARCHAR(50),
    action_result TEXT,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    KEY idx_alert_type (alert_type),
    KEY idx_severity (severity),
    KEY idx_unread (is_read),
    KEY idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";

// ─────────────────────────────────────────────────────────────────────────────
// DAILY SNAPSHOT TABLE: Historical record of each day's status
// ─────────────────────────────────────────────────────────────────────────────
$tables['KIMI_GOLDMINE_DAILY_SNAPSHOT'] = "CREATE TABLE IF NOT EXISTS KIMI_GOLDMINE_DAILY_SNAPSHOT (
    id INT AUTO_INCREMENT PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    
    -- Overall stats
    total_picks_active INT DEFAULT 0,
    total_sources_active INT DEFAULT 0,
    total_goldmines_active INT DEFAULT 0,
    
    -- Performance summary
    avg_return_all_active DECIMAL(10,4),
    best_performing_source VARCHAR(200),
    best_performing_return DECIMAL(10,4),
    worst_performing_source VARCHAR(200),
    worst_performing_return DECIMAL(10,4),
    
    -- New discoveries
    new_picks_today INT DEFAULT 0,
    new_winners_today INT DEFAULT 0,
    new_goldmines_today INT DEFAULT 0,
    
    -- Alerts
    alerts_generated INT DEFAULT 0,
    critical_alerts INT DEFAULT 0,
    
    snapshot_json JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY idx_snapshot_date (snapshot_date),
    KEY idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";

// Execute table creation
$results = array();
foreach ($tables as $table_name => $sql) {
    if ($conn->query($sql) === TRUE) {
        $results[$table_name] = 'Created or already exists';
    } else {
        $results[$table_name] = 'Error: ' . $conn->error;
    }
}

// Insert default sources
default_sources($conn);

echo json_encode(array(
    'ok' => true,
    'message' => 'KIMI Goldmine schema setup complete',
    'tables' => $results
));

$conn->close();

// ─────────────────────────────────────────────────────────────────────────────
// Helper: Insert default sources
// ─────────────────────────────────────────────────────────────────────────────
function default_sources($conn) {
    $sources = array(
        // Stock sources
        array('stock', 'findstocks_portfolio2', 'findstocks-portfolio2', 'Alpha Forge Ultimate', 'alpha_forge_ultimate', 'Alpha Forge Ultimate', 'Multi-factor ensemble with regime weighting', 'multi_factor', 'medium_term', 'high', 'findstocks/portfolio2/api/consolidated_picks.php', 'stock_picks'),
        array('stock', 'findstocks_portfolio2', 'findstocks-portfolio2', 'God-Mode Standard', 'god_mode_standard', 'God-Mode Standard', 'Meta-learner ensemble: regime-aware, Kelly-sized', 'ensemble', 'medium_term', 'medium', 'findstocks/portfolio2/api/consolidated_picks.php', 'stock_picks'),
        array('stock', 'findstocks_portfolio2', 'findstocks-portfolio2', 'Piotroski F-Score', 'piotroski_fscore', 'Piotroski F-Score', '9-criteria quality scoring, academic-backed', 'value', 'long_term', 'low', 'findstocks/portfolio2/api/data.php', 'stock_picks'),
        array('stock', 'findstocks_portfolio2', 'findstocks-portfolio2', 'Technical Momentum', 'technical_momentum', 'Technical Momentum', 'RSI, Volume, Bollinger-based momentum', 'momentum', 'short_term', 'high', 'findstocks/portfolio2/api/data.php', 'stock_picks'),
        array('stock', 'findstocks_portfolio2', 'findstocks-portfolio2', 'CAN SLIM', 'can_slim', 'CAN SLIM', 'Growth stock selection methodology', 'growth', 'medium_term', 'medium', 'findstocks/portfolio2/api/data.php', 'stock_picks'),
        
        // Penny stocks
        array('penny_stock', 'findstocks_portfolio2', 'findstocks-penny', 'Penny Stock Scanner', 'penny_scanner', 'Penny Stock Scanner', 'Low-priced stock momentum scanner', 'momentum', 'short_term', 'very_high', 'findstocks/portfolio2/api/penny_stocks.php', 'stock_picks'),
        
        // Crypto
        array('crypto', 'findcryptopairs', 'findcryptopairs', 'Crypto Winners', 'crypto_winners', 'Crypto Winners', 'Top-performing crypto pairs', 'momentum', 'short_term', 'high', 'findcryptopairs/api/crypto_winners.php', 'cp_signals'),
        
        // Meme coins
        array('meme_coin', 'findcryptopairs', 'findcryptopairs-meme', 'Meme Coin Scanner', 'meme_scanner', 'Meme Coin Scanner', '7-factor meme coin scoring system', 'momentum', 'very_short', 'very_high', 'findcryptopairs/api/meme_scanner.php', 'mc_winners'),
        
        // Forex
        array('forex', 'findforex2', 'findforex2', 'Forex Signals', 'forex_signals', 'Forex Signals', 'Currency pair trading signals', 'momentum', 'short_term', 'medium', 'findforex2/api/data.php', 'fx_signals'),
        
        // Mutual funds
        array('mutual_fund', 'findmutualfunds2', 'findmutualfunds2', 'Fund Selections', 'fund_selections', 'Fund Selections', 'Top mutual fund picks', 'value', 'long_term', 'low', 'findmutualfunds2/portfolio2/api/data.php', 'mf_selections'),
        
        // Sports
        array('sports', 'live_monitor', 'live-monitor-sports', 'Value Bet Finder', 'value_bet', 'Value Bet Finder', '+EV detection across sportsbooks', 'value', 'short_term', 'medium', 'live-monitor/api/sports_picks.php', 'lm_sports_value_bets'),
        array('sports', 'live_monitor', 'live-monitor-sports', 'Line Shopping', 'line_shop', 'Line Shopping', 'Best odds finder', 'arbitrage', 'short_term', 'low', 'live-monitor/api/sports_odds.php', 'lm_sports_odds'),
        
        // Alpha Engine (when deployed)
        array('alpha_engine', 'alpha_engine', 'alpha-engine', 'ML Ranker', 'ml_ranker', 'ML Ranker', 'Machine learning cross-sectional ranking', 'ml', 'medium_term', 'medium', 'alpha_engine/main.py', NULL),
        array('alpha_engine', 'alpha_engine', 'alpha-engine', 'Quality Compounders', 'quality_compounders', 'Quality Compounders', 'Underpriced boring stocks', 'quality', 'long_term', 'low', 'alpha_engine/main.py', NULL),
    );
    
    $stmt = $conn->prepare("INSERT IGNORE INTO KIMI_GOLDMINE_SOURCES 
        (source_type, source_name, source_slug, algorithm_name, algorithm_slug, display_name, description, strategy_type, ideal_timeframe, risk_level, source_api_endpoint, source_db_table) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
    
    foreach ($sources as $source) {
        $stmt->bind_param('ssssssssssss', 
            $source[0], $source[1], $source[2], $source[3], $source[4], 
            $source[5], $source[6], $source[7], $source[8], $source[9],
            $source[10], $source[11]
        );
        $stmt->execute();
    }
    $stmt->close();
}
