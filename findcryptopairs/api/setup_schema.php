<?php
/**
 * Memecoin/Crypto Database Schema Setup
 * 
 * Creates all required tables for ejaguiar1_memecoin database
 * 
 * ?action=setup - Create all tables
 * ?action=status - Check current status
 */

error_reporting(0);
ini_set('display_errors', '0');
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// Database config
$db_host = 'mysql.50webs.com';
$db_user = 'ejaguiar1_memecoin';
$db_pass = 'testing123';
$db_name = 'ejaguiar1_memecoin';

$action = isset($_GET['action']) ? $_GET['action'] : 'status';

// Connect to database
$conn = new mysqli($db_host, $db_user, $db_pass, $db_name);
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'Connection failed: ' . $conn->connect_error));
    exit;
}
$conn->set_charset('utf8mb4');

// Table definitions
$tables = array(
    // Hybrid Engine
    'he_signals' => "CREATE TABLE IF NOT EXISTS he_signals (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        signal_type VARCHAR(50) NOT NULL,
        entry_price DECIMAL(20,8),
        target_price DECIMAL(20,8),
        stop_loss DECIMAL(20,8),
        confidence DECIMAL(5,4),
        timeframe VARCHAR(20),
        status VARCHAR(20) DEFAULT 'active',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        resolved_at DATETIME,
        pnl DECIMAL(20,8),
        INDEX idx_symbol (symbol),
        INDEX idx_status (status),
        INDEX idx_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'he_backtest' => "CREATE TABLE IF NOT EXISTS he_backtest (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        test_params TEXT,
        win_rate DECIMAL(5,4),
        total_trades INT,
        profit_factor DECIMAL(10,4),
        max_drawdown DECIMAL(10,4),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol (symbol)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'he_weights' => "CREATE TABLE IF NOT EXISTS he_weights (
        id INT AUTO_INCREMENT PRIMARY KEY,
        strategy VARCHAR(50) NOT NULL,
        weight DECIMAL(5,4) NOT NULL,
        performance DECIMAL(10,4),
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_strategy (strategy)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'he_audit' => "CREATE TABLE IF NOT EXISTS he_audit (
        id INT AUTO_INCREMENT PRIMARY KEY,
        action VARCHAR(100) NOT NULL,
        details TEXT,
        performed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_action (action)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    // TV Technicals
    'tv_signals' => "CREATE TABLE IF NOT EXISTS tv_signals (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        indicator VARCHAR(50) NOT NULL,
        value DECIMAL(20,8),
        signal VARCHAR(20),
        timeframe VARCHAR(20),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol (symbol),
        INDEX idx_indicator (indicator)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    // Kimi Enhanced
    'ke_signals' => "CREATE TABLE IF NOT EXISTS ke_signals (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        prediction DECIMAL(20,8),
        confidence DECIMAL(5,4),
        model_version VARCHAR(20),
        features TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol (symbol)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'ke_backtest' => "CREATE TABLE IF NOT EXISTS ke_backtest (
        id INT AUTO_INCREMENT PRIMARY KEY,
        model_version VARCHAR(20) NOT NULL,
        accuracy DECIMAL(5,4),
        total_predictions INT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'ke_audit' => "CREATE TABLE IF NOT EXISTS ke_audit (
        id INT AUTO_INCREMENT PRIMARY KEY,
        action VARCHAR(100) NOT NULL,
        details TEXT,
        performed_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    // Expert Consensus
    'ec_signals' => "CREATE TABLE IF NOT EXISTS ec_signals (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        consensus_rating VARCHAR(20),
        buy_count INT DEFAULT 0,
        sell_count INT DEFAULT 0,
        hold_count INT DEFAULT 0,
        confidence DECIMAL(5,4),
        sources TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol (symbol)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'ec_audit' => "CREATE TABLE IF NOT EXISTS ec_audit (
        id INT AUTO_INCREMENT PRIMARY KEY,
        action VARCHAR(100) NOT NULL,
        expert_source VARCHAR(100),
        details TEXT,
        performed_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    // Meme Scanner
    'meme_signals' => "CREATE TABLE IF NOT EXISTS meme_signals (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        token_name VARCHAR(100),
        sentiment_score DECIMAL(5,4),
        viral_score DECIMAL(10,4),
        volume_spike DECIMAL(10,4),
        social_mentions INT,
        signal_type VARCHAR(20),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol (symbol),
        INDEX idx_sentiment (sentiment_score)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'meme_ml_models' => "CREATE TABLE IF NOT EXISTS meme_ml_models (
        id INT AUTO_INCREMENT PRIMARY KEY,
        model_name VARCHAR(100) NOT NULL,
        model_version VARCHAR(20),
        accuracy DECIMAL(5,4),
        precision_score DECIMAL(5,4),
        recall DECIMAL(5,4),
        f1_score DECIMAL(5,4),
        training_data_size INT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_active TINYINT(1) DEFAULT 1
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'meme_ml_predictions' => "CREATE TABLE IF NOT EXISTS meme_ml_predictions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        model_id INT,
        prediction DECIMAL(20,8),
        confidence DECIMAL(5,4),
        features TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol (symbol)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    // Algorithm Competition
    'algo_predictions' => "CREATE TABLE IF NOT EXISTS algo_predictions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        algorithm VARCHAR(50) NOT NULL,
        prediction DECIMAL(20,8),
        confidence DECIMAL(5,4),
        features TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol (symbol),
        INDEX idx_algorithm (algorithm)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'algo_battle_preds' => "CREATE TABLE IF NOT EXISTS algo_battle_preds (
        id INT AUTO_INCREMENT PRIMARY KEY,
        battle_id VARCHAR(50) NOT NULL,
        algorithm VARCHAR(50) NOT NULL,
        symbol VARCHAR(20) NOT NULL,
        prediction DECIMAL(20,8),
        actual_result DECIMAL(20,8),
        pnl DECIMAL(20,8),
        is_winner TINYINT(1) DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    // ML Feature Store
    'ml_feature_store' => "CREATE TABLE IF NOT EXISTS ml_feature_store (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        feature_name VARCHAR(100) NOT NULL,
        feature_value DECIMAL(20,8),
        feature_type VARCHAR(50),
        computed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol (symbol),
        INDEX idx_feature (feature_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    // Backtest100
    'bt100_results' => "CREATE TABLE IF NOT EXISTS bt100_results (
        id INT AUTO_INCREMENT PRIMARY KEY,
        strategy_name VARCHAR(100) NOT NULL,
        symbol VARCHAR(20) NOT NULL,
        start_date DATE,
        end_date DATE,
        total_return DECIMAL(10,4),
        win_rate DECIMAL(5,4),
        max_drawdown DECIMAL(10,4),
        sharpe_ratio DECIMAL(10,4),
        total_trades INT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_strategy (strategy_name),
        INDEX idx_symbol (symbol)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'bt100_audit' => "CREATE TABLE IF NOT EXISTS bt100_audit (
        id INT AUTO_INCREMENT PRIMARY KEY,
        action VARCHAR(100) NOT NULL,
        strategy_name VARCHAR(100),
        details TEXT,
        performed_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'bt100_picks' => "CREATE TABLE IF NOT EXISTS bt100_picks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        strategy_name VARCHAR(100),
        entry_price DECIMAL(20,8),
        exit_price DECIMAL(20,8),
        pnl DECIMAL(20,8),
        status VARCHAR(20) DEFAULT 'open',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        closed_at DATETIME
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    // Alpha Hunter
    'ah_signals' => "CREATE TABLE IF NOT EXISTS ah_signals (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        alpha_score DECIMAL(10,4),
        momentum DECIMAL(10,4),
        volume_anomaly DECIMAL(10,4),
        social_sentiment DECIMAL(5,4),
        signal_type VARCHAR(20),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol (symbol)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'ah_pump_analysis' => "CREATE TABLE IF NOT EXISTS ah_pump_analysis (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        pump_probability DECIMAL(5,4),
        volume_surge DECIMAL(10,4),
        price_velocity DECIMAL(10,4),
        detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol (symbol)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    // Academic Edge
    'ae_signals' => "CREATE TABLE IF NOT EXISTS ae_signals (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        edge_type VARCHAR(50),
        edge_value DECIMAL(10,4),
        academic_source VARCHAR(100),
        confidence DECIMAL(5,4),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'ae_results' => "CREATE TABLE IF NOT EXISTS ae_results (
        id INT AUTO_INCREMENT PRIMARY KEY,
        strategy_name VARCHAR(100),
        backtest_period VARCHAR(50),
        annual_return DECIMAL(10,4),
        sharpe DECIMAL(10,4),
        max_dd DECIMAL(10,4),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'ae_audit' => "CREATE TABLE IF NOT EXISTS ae_audit (
        id INT AUTO_INCREMENT PRIMARY KEY,
        action VARCHAR(100),
        details TEXT,
        performed_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    // AI Predictions
    'ai_personal_predictions' => "CREATE TABLE IF NOT EXISTS ai_personal_predictions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        symbol VARCHAR(20) NOT NULL,
        prediction DECIMAL(20,8),
        confidence DECIMAL(5,4),
        model_used VARCHAR(100),
        features TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        resolved_at DATETIME,
        actual_outcome DECIMAL(20,8)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    // Engine Health
    'eh_engine_grades' => "CREATE TABLE IF NOT EXISTS eh_engine_grades (
        id INT AUTO_INCREMENT PRIMARY KEY,
        engine_name VARCHAR(100) NOT NULL,
        grade VARCHAR(5),
        score DECIMAL(10,4),
        win_rate DECIMAL(5,4),
        total_pnl DECIMAL(20,8),
        recommendation VARCHAR(50),
        computed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_engine (engine_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'eh_grade_history' => "CREATE TABLE IF NOT EXISTS eh_grade_history (
        id INT AUTO_INCREMENT PRIMARY KEY,
        engine_name VARCHAR(100),
        grade VARCHAR(5),
        score DECIMAL(10,4),
        recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'eh_alerts' => "CREATE TABLE IF NOT EXISTS eh_alerts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        engine_name VARCHAR(100),
        alert_type VARCHAR(50),
        message TEXT,
        severity VARCHAR(20),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_resolved TINYINT(1) DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
);

// Status check
if ($action === 'status') {
    $existing_tables = array();
    $missing_tables = array();
    
    foreach ($tables as $table_name => $sql) {
        $result = $conn->query("SHOW TABLES LIKE '$table_name'");
        if ($result && $result->num_rows > 0) {
            $count_result = $conn->query("SELECT COUNT(*) as cnt FROM $table_name");
            $row_count = 0;
            if ($count_result) {
                $row = $count_result->fetch_assoc();
                $row_count = (int)$row['cnt'];
            }
            $existing_tables[$table_name] = $row_count;
        } else {
            $missing_tables[] = $table_name;
        }
    }
    
    echo json_encode(array(
        'ok' => true,
        'database' => $db_name,
        'existing_tables' => $existing_tables,
        'missing_tables' => $missing_tables,
        'total_expected' => count($tables),
        'total_existing' => count($existing_tables),
        'needs_setup' => count($missing_tables) > 0
    ));
    
    $conn->close();
    exit;
}

// Setup tables
if ($action === 'setup') {
    $created = array();
    $failed = array();
    $existing = array();
    
    foreach ($tables as $table_name => $sql) {
        $result = $conn->query("SHOW TABLES LIKE '$table_name'");
        if ($result && $result->num_rows > 0) {
            $existing[] = $table_name;
            continue;
        }
        
        if ($conn->query($sql)) {
            $created[] = $table_name;
        } else {
            $failed[] = array('table' => $table_name, 'error' => $conn->error);
        }
    }
    
    echo json_encode(array(
        'ok' => count($failed) === 0,
        'database' => $db_name,
        'created' => $created,
        'existing' => $existing,
        'failed' => $failed,
        'total_tables' => count($tables)
    ));
    
    $conn->close();
    exit;
}

$conn->close();
echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
