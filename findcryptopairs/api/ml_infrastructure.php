<?php
/**
 * ML Infrastructure Schema v1.0
 * 
 * Creates the database tables needed for a world-class prediction platform:
 *   1. Feature Store — centralized features for all models
 *   2. Model Registry — track every model version and its performance
 *   3. Prediction Pipeline — end-to-end prediction tracking
 *   4. A/B Testing — compare model versions rigorously
 *   5. Regime Detection — market regime tracking for strategy switching
 *   6. Ensemble Optimizer — dynamic weight optimization across engines
 *
 * Run once: ?action=setup
 * Status:   ?action=status
 *
 * PHP 5.2 compatible.
 */

error_reporting(0);
ini_set('display_errors', '0');
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

require_once dirname(__FILE__) . '/db_config.php';
$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'DB connection failed'));
    exit;
}
$conn->set_charset('utf8');

$action = isset($_GET['action']) ? $_GET['action'] : 'status';

if ($action === 'setup') {
    $results = array();

    // ═══ 1. CENTRALIZED FEATURE STORE ═══
    // One row per asset per timestamp with all computed features
    $sql = "CREATE TABLE IF NOT EXISTS ml_feature_store (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        pair VARCHAR(30) NOT NULL,
        asset_class VARCHAR(20) DEFAULT 'CRYPTO',
        timestamp DATETIME NOT NULL,
        timeframe VARCHAR(10) DEFAULT '4H',
        
        -- Price features
        close_price FLOAT DEFAULT 0,
        return_1 FLOAT DEFAULT 0,
        return_5 FLOAT DEFAULT 0,
        return_20 FLOAT DEFAULT 0,
        log_return FLOAT DEFAULT 0,
        
        -- Momentum features
        rsi_14 FLOAT DEFAULT 0,
        macd_value FLOAT DEFAULT 0,
        macd_signal FLOAT DEFAULT 0,
        macd_histogram FLOAT DEFAULT 0,
        stoch_k FLOAT DEFAULT 0,
        stoch_d FLOAT DEFAULT 0,
        williams_r FLOAT DEFAULT 0,
        cci_20 FLOAT DEFAULT 0,
        roc_10 FLOAT DEFAULT 0,
        
        -- Trend features
        sma_20 FLOAT DEFAULT 0,
        sma_50 FLOAT DEFAULT 0,
        ema_9 FLOAT DEFAULT 0,
        ema_21 FLOAT DEFAULT 0,
        adx_14 FLOAT DEFAULT 0,
        plus_di FLOAT DEFAULT 0,
        minus_di FLOAT DEFAULT 0,
        price_vs_sma20 FLOAT DEFAULT 0,
        price_vs_sma50 FLOAT DEFAULT 0,
        
        -- Volatility features
        atr_14 FLOAT DEFAULT 0,
        bollinger_upper FLOAT DEFAULT 0,
        bollinger_lower FLOAT DEFAULT 0,
        bollinger_width FLOAT DEFAULT 0,
        bollinger_pct_b FLOAT DEFAULT 0,
        realized_vol_20 FLOAT DEFAULT 0,
        
        -- Volume features
        volume FLOAT DEFAULT 0,
        volume_sma_20 FLOAT DEFAULT 0,
        volume_ratio FLOAT DEFAULT 0,
        obv FLOAT DEFAULT 0,
        
        -- Predictability features
        hurst_exponent FLOAT DEFAULT 0.5,
        autocorrelation_1 FLOAT DEFAULT 0,
        volatility_stability FLOAT DEFAULT 0,
        signal_noise_ratio FLOAT DEFAULT 0,
        
        -- Pattern detection
        pattern_detected VARCHAR(50) DEFAULT '',
        pattern_strength FLOAT DEFAULT 0,
        
        -- Engine consensus features
        engines_bullish INT DEFAULT 0,
        engines_bearish INT DEFAULT 0,
        engines_total INT DEFAULT 0,
        engine_agreement FLOAT DEFAULT 0,
        
        -- Target label (filled retroactively)
        target_1h FLOAT DEFAULT NULL,
        target_4h FLOAT DEFAULT NULL,
        target_24h FLOAT DEFAULT NULL,
        target_direction VARCHAR(10) DEFAULT NULL,
        
        KEY pair_time (pair, timestamp),
        KEY timeframe_idx (timeframe)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8";
    $ok = $conn->query($sql);
    $results[] = array('table' => 'ml_feature_store', 'ok' => $ok ? true : false, 'error' => $ok ? '' : $conn->error);

    // ═══ 2. MODEL REGISTRY ═══
    $sql = "CREATE TABLE IF NOT EXISTS ml_model_registry (
        id INT AUTO_INCREMENT PRIMARY KEY,
        model_id VARCHAR(50) NOT NULL UNIQUE,
        model_name VARCHAR(100) NOT NULL,
        model_type VARCHAR(50) NOT NULL,
        asset_class VARCHAR(20) DEFAULT 'CRYPTO',
        target_horizon VARCHAR(20) DEFAULT '4H',
        features_used TEXT,
        hyperparameters TEXT,
        training_start DATE,
        training_end DATE,
        training_samples INT DEFAULT 0,
        
        -- Performance metrics
        accuracy FLOAT DEFAULT 0,
        precision_score FLOAT DEFAULT 0,
        recall_score FLOAT DEFAULT 0,
        f1_score FLOAT DEFAULT 0,
        auc_roc FLOAT DEFAULT 0,
        sharpe_ratio FLOAT DEFAULT 0,
        profit_factor FLOAT DEFAULT 0,
        max_drawdown FLOAT DEFAULT 0,
        
        -- Walk-forward validation
        wf_accuracy FLOAT DEFAULT 0,
        wf_sharpe FLOAT DEFAULT 0,
        overfit_score FLOAT DEFAULT 0,
        
        -- Status
        status VARCHAR(20) DEFAULT 'TRAINING',
        is_active TINYINT DEFAULT 0,
        deployed_at DATETIME DEFAULT NULL,
        retired_at DATETIME DEFAULT NULL,
        created_at DATETIME,
        
        KEY active_idx (is_active),
        KEY type_idx (model_type)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8";
    $ok = $conn->query($sql);
    $results[] = array('table' => 'ml_model_registry', 'ok' => $ok ? true : false, 'error' => $ok ? '' : $conn->error);

    // ═══ 3. MODEL A/B TESTING ═══
    $sql = "CREATE TABLE IF NOT EXISTS ml_ab_tests (
        id INT AUTO_INCREMENT PRIMARY KEY,
        test_id VARCHAR(50) NOT NULL UNIQUE,
        model_a_id VARCHAR(50) NOT NULL,
        model_b_id VARCHAR(50) NOT NULL,
        asset_class VARCHAR(20) DEFAULT 'CRYPTO',
        started_at DATETIME,
        ended_at DATETIME DEFAULT NULL,
        
        -- Model A stats
        a_predictions INT DEFAULT 0,
        a_wins INT DEFAULT 0,
        a_total_pnl FLOAT DEFAULT 0,
        a_sharpe FLOAT DEFAULT 0,
        
        -- Model B stats
        b_predictions INT DEFAULT 0,
        b_wins INT DEFAULT 0,
        b_total_pnl FLOAT DEFAULT 0,
        b_sharpe FLOAT DEFAULT 0,
        
        -- Statistical test
        p_value FLOAT DEFAULT 1,
        winner VARCHAR(10) DEFAULT 'NONE',
        confidence_level FLOAT DEFAULT 0,
        status VARCHAR(20) DEFAULT 'RUNNING',
        
        KEY status_idx (status)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8";
    $ok = $conn->query($sql);
    $results[] = array('table' => 'ml_ab_tests', 'ok' => $ok ? true : false, 'error' => $ok ? '' : $conn->error);

    // ═══ 4. ENSEMBLE WEIGHTS (dynamic) ═══
    $sql = "CREATE TABLE IF NOT EXISTS ml_ensemble_weights (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pair VARCHAR(30) DEFAULT 'ALL',
        asset_class VARCHAR(20) DEFAULT 'CRYPTO',
        engine_name VARCHAR(50) NOT NULL,
        weight FLOAT DEFAULT 1.0,
        weight_reason VARCHAR(100) DEFAULT '',
        win_rate FLOAT DEFAULT 0,
        sample_size INT DEFAULT 0,
        computed_at DATETIME,
        UNIQUE KEY eng_pair (engine_name, pair)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8";
    $ok = $conn->query($sql);
    $results[] = array('table' => 'ml_ensemble_weights', 'ok' => $ok ? true : false, 'error' => $ok ? '' : $conn->error);

    // ═══ 5. MARKET REGIME SNAPSHOTS (cross-asset) ═══
    $sql = "CREATE TABLE IF NOT EXISTS ml_regime_snapshots (
        id INT AUTO_INCREMENT PRIMARY KEY,
        snapshot_date DATE NOT NULL,
        asset_class VARCHAR(20) DEFAULT 'CRYPTO',
        
        -- Regime indicators
        btc_trend VARCHAR(10) DEFAULT 'NEUTRAL',
        market_fear_greed INT DEFAULT 50,
        avg_hurst FLOAT DEFAULT 0.5,
        avg_correlation FLOAT DEFAULT 0,
        volatility_percentile FLOAT DEFAULT 50,
        trending_pairs INT DEFAULT 0,
        mean_reverting_pairs INT DEFAULT 0,
        random_pairs INT DEFAULT 0,
        
        -- Best regime strategy
        recommended_strategy VARCHAR(30) DEFAULT 'MULTI_INDICATOR',
        regime_confidence FLOAT DEFAULT 0,
        
        created_at DATETIME,
        UNIQUE KEY date_class (snapshot_date, asset_class)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8";
    $ok = $conn->query($sql);
    $results[] = array('table' => 'ml_regime_snapshots', 'ok' => $ok ? true : false, 'error' => $ok ? '' : $conn->error);

    // ═══ 6. PREDICTION CONFIDENCE CALIBRATION ═══
    // Tracks: when we say "80% confident", is it right 80% of the time?
    $sql = "CREATE TABLE IF NOT EXISTS ml_calibration_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        engine_name VARCHAR(50) NOT NULL,
        confidence_bucket INT NOT NULL,
        total_predictions INT DEFAULT 0,
        correct_predictions INT DEFAULT 0,
        actual_rate FLOAT DEFAULT 0,
        calibration_error FLOAT DEFAULT 0,
        computed_at DATETIME,
        UNIQUE KEY eng_bucket (engine_name, confidence_bucket)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8";
    $ok = $conn->query($sql);
    $results[] = array('table' => 'ml_calibration_log', 'ok' => $ok ? true : false, 'error' => $ok ? '' : $conn->error);

    // ═══ 7. PLATFORM PERFORMANCE DASHBOARD ═══
    // Daily aggregated metrics for the whole platform
    $sql = "CREATE TABLE IF NOT EXISTS ml_platform_daily (
        id INT AUTO_INCREMENT PRIMARY KEY,
        metric_date DATE NOT NULL UNIQUE,
        
        -- Volume
        total_signals_generated INT DEFAULT 0,
        signals_crypto INT DEFAULT 0,
        signals_stocks INT DEFAULT 0,
        signals_forex INT DEFAULT 0,
        signals_sports INT DEFAULT 0,
        
        -- Outcomes
        resolved_today INT DEFAULT 0,
        wins_today INT DEFAULT 0,
        losses_today INT DEFAULT 0,
        
        -- Performance
        daily_win_rate FLOAT DEFAULT 0,
        daily_pnl FLOAT DEFAULT 0,
        cumulative_pnl FLOAT DEFAULT 0,
        
        -- Predictability
        avg_predictability FLOAT DEFAULT 0,
        high_pred_win_rate FLOAT DEFAULT 0,
        low_pred_win_rate FLOAT DEFAULT 0,
        
        -- System health
        engines_active INT DEFAULT 0,
        engines_total INT DEFAULT 0,
        api_uptime_pct FLOAT DEFAULT 100,
        
        created_at DATETIME
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8";
    $ok = $conn->query($sql);
    $results[] = array('table' => 'ml_platform_daily', 'ok' => $ok ? true : false, 'error' => $ok ? '' : $conn->error);

    // ═══ 8. LEARNING CURVES ═══
    // Track model improvement over time as more data comes in
    $sql = "CREATE TABLE IF NOT EXISTS ml_learning_curve (
        id INT AUTO_INCREMENT PRIMARY KEY,
        engine_name VARCHAR(50) NOT NULL,
        data_date DATE NOT NULL,
        sample_count INT DEFAULT 0,
        rolling_win_rate FLOAT DEFAULT 0,
        rolling_sharpe FLOAT DEFAULT 0,
        rolling_profit_factor FLOAT DEFAULT 0,
        improvement_rate FLOAT DEFAULT 0,
        UNIQUE KEY eng_date (engine_name, data_date)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8";
    $ok = $conn->query($sql);
    $results[] = array('table' => 'ml_learning_curve', 'ok' => $ok ? true : false, 'error' => $ok ? '' : $conn->error);

    // Count OK vs failed
    $ok_count = 0;
    $fail_count = 0;
    foreach ($results as $r) {
        if ($r['ok']) $ok_count++;
        else $fail_count++;
    }

    echo json_encode(array(
        'ok' => ($fail_count === 0),
        'tables_created' => $ok_count,
        'tables_failed' => $fail_count,
        'details' => $results
    ));

} elseif ($action === 'status') {
    // Check which tables exist and their row counts
    $tables = array(
        'ml_feature_store', 'ml_model_registry', 'ml_ab_tests',
        'ml_ensemble_weights', 'ml_regime_snapshots', 'ml_calibration_log',
        'ml_platform_daily', 'ml_learning_curve',
        'ps_scores', 'ps_history',
        'ua_predictions', 'ua_engine_stats'
    );
    
    $status = array();
    foreach ($tables as $tbl) {
        $r = $conn->query("SELECT COUNT(*) as cnt FROM " . $tbl);
        if ($r) {
            $row = $r->fetch_assoc();
            $status[] = array('table' => $tbl, 'exists' => true, 'rows' => (int)$row['cnt']);
        } else {
            $status[] = array('table' => $tbl, 'exists' => false, 'rows' => 0);
        }
    }

    echo json_encode(array('ok' => true, 'tables' => $status));
} else {
    echo json_encode(array('ok' => false, 'error' => 'Use ?action=setup or ?action=status'));
}

$conn->close();
