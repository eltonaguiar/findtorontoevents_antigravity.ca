<?php
/**
 * Stocks Database Schema Setup
 * 
 * Creates all required tables for ejaguiar1_stocks database
 * Called by GitHub Actions to ensure schema exists
 * 
 * ?action=setup - Create all tables
 * ?action=status - Check current status
 * ?action=reset - Drop and recreate tables (DANGER)
 */

error_reporting(0);
ini_set('display_errors', '0');
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// Database config
$db_host = 'mysql.50webs.com';
$db_user = 'ejaguiar1_stocks';
$db_pass = 'stocks';
$db_name = 'ejaguiar1_stocks';

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
    'lm_signals' => "CREATE TABLE IF NOT EXISTS lm_signals (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        signal_type VARCHAR(50) NOT NULL,
        signal_value DECIMAL(10,4),
        price DECIMAL(15,4),
        volume BIGINT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        source VARCHAR(50) DEFAULT 'live_monitor',
        INDEX idx_symbol (symbol),
        INDEX idx_timestamp (timestamp),
        INDEX idx_signal_type (signal_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'ua_predictions' => "CREATE TABLE IF NOT EXISTS ua_predictions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        prediction_type VARCHAR(50) NOT NULL,
        predicted_value DECIMAL(15,4),
        confidence DECIMAL(5,4),
        actual_value DECIMAL(15,4),
        accuracy DECIMAL(5,4),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        resolved_at DATETIME,
        INDEX idx_symbol (symbol),
        INDEX idx_created (created_at),
        INDEX idx_resolved (resolved_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'ps_scores' => "CREATE TABLE IF NOT EXISTS ps_scores (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        score DECIMAL(5,4) NOT NULL,
        grade VARCHAR(5),
        volatility DECIMAL(10,4),
        trend_direction VARCHAR(20),
        computed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_symbol (symbol),
        INDEX idx_score (score),
        INDEX idx_computed (computed_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'ml_feature_store' => "CREATE TABLE IF NOT EXISTS ml_feature_store (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        feature_name VARCHAR(100) NOT NULL,
        feature_value DECIMAL(20,8),
        feature_type VARCHAR(50),
        computed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_symbol (symbol),
        INDEX idx_feature (feature_name),
        INDEX idx_computed (computed_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'goldmine_tracker' => "CREATE TABLE IF NOT EXISTS goldmine_tracker (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        pick_date DATE NOT NULL,
        entry_price DECIMAL(15,4),
        target_price DECIMAL(15,4),
        stop_loss DECIMAL(15,4),
        status VARCHAR(20) DEFAULT 'active',
        exit_price DECIMAL(15,4),
        pnl DECIMAL(15,4),
        pnl_percent DECIMAL(10,4),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_symbol (symbol),
        INDEX idx_status (status),
        INDEX idx_date (pick_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'performance_probe' => "CREATE TABLE IF NOT EXISTS performance_probe (
        id INT AUTO_INCREMENT PRIMARY KEY,
        metric_name VARCHAR(100) NOT NULL,
        metric_value DECIMAL(20,8),
        symbol VARCHAR(20),
        timeframe VARCHAR(20),
        recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_metric (metric_name),
        INDEX idx_symbol (symbol),
        INDEX idx_recorded (recorded_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'stock_alerts' => "CREATE TABLE IF NOT EXISTS stock_alerts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        alert_type VARCHAR(50) NOT NULL,
        alert_message TEXT,
        price_trigger DECIMAL(15,4),
        is_triggered TINYINT(1) DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        triggered_at DATETIME,
        INDEX idx_symbol (symbol),
        INDEX idx_type (alert_type),
        INDEX idx_triggered (is_triggered)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
    
    'command_center_log' => "CREATE TABLE IF NOT EXISTS command_center_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        command VARCHAR(100) NOT NULL,
        params TEXT,
        result TEXT,
        status VARCHAR(20),
        executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        execution_time_ms INT,
        INDEX idx_command (command),
        INDEX idx_status (status),
        INDEX idx_executed (executed_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
);

// Status check
if ($action === 'status') {
    $existing_tables = array();
    $missing_tables = array();
    
    foreach ($tables as $table_name => $sql) {
        $result = $conn->query("SHOW TABLES LIKE '$table_name'");
        if ($result && $result->num_rows > 0) {
            // Table exists, get row count
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
        // Check if table already exists
        $result = $conn->query("SHOW TABLES LIKE '$table_name'");
        if ($result && $result->num_rows > 0) {
            $existing[] = $table_name;
            continue;
        }
        
        // Create table
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

// Reset (DANGER - drops and recreates)
if ($action === 'reset') {
    $dropped = array();
    $errors = array();
    
    foreach (array_keys($tables) as $table_name) {
        if ($conn->query("DROP TABLE IF EXISTS $table_name")) {
            $dropped[] = $table_name;
        } else {
            $errors[] = array('table' => $table_name, 'error' => $conn->error);
        }
    }
    
    // Now recreate
    $created = array();
    foreach ($tables as $table_name => $sql) {
        if ($conn->query($sql)) {
            $created[] = $table_name;
        } else {
            $errors[] = array('table' => $table_name, 'error' => $conn->error);
        }
    }
    
    echo json_encode(array(
        'ok' => count($errors) === 0,
        'database' => $db_name,
        'dropped' => $dropped,
        'created' => $created,
        'errors' => $errors
    ));
    
    $conn->close();
    exit;
}

// Unknown action
$conn->close();
echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
