<?php
/**
 * ml_intelligence_schema.php — World-class ML tracking tables
 * Creates tables for ML readiness, walk-forward validation, feature importance,
 * model versioning, ensemble weights, prediction calibration, and cross-correlation.
 */

function _ml_ensure_schema($conn) {
    // 1. ML Status Tracker — bird's eye view of ML readiness per algo per asset
    $conn->query("CREATE TABLE IF NOT EXISTS lm_ml_status (
        id INT AUTO_INCREMENT PRIMARY KEY,
        algorithm_name VARCHAR(100) NOT NULL,
        asset_class VARCHAR(20) NOT NULL,
        closed_trades INT DEFAULT 0,
        min_trades_needed INT DEFAULT 20,
        ml_ready TINYINT DEFAULT 0,
        current_tp DECIMAL(5,2) DEFAULT NULL,
        current_sl DECIMAL(5,2) DEFAULT NULL,
        current_hold INT DEFAULT NULL,
        param_source VARCHAR(20) DEFAULT 'default',
        current_win_rate DECIMAL(5,2) DEFAULT NULL,
        current_sharpe DECIMAL(8,4) DEFAULT NULL,
        current_pf DECIMAL(5,3) DEFAULT NULL,
        total_pnl DECIMAL(10,2) DEFAULT 0,
        last_optimization DATETIME DEFAULT NULL,
        optimization_count INT DEFAULT 0,
        best_sharpe_ever DECIMAL(8,4) DEFAULT NULL,
        backtest_sharpe DECIMAL(8,4) DEFAULT NULL,
        backtest_grade VARCHAR(5) DEFAULT NULL,
        backtest_trades INT DEFAULT 0,
        forward_backtest_overlap TINYINT DEFAULT 0,
        status VARCHAR(30) DEFAULT 'collecting_data',
        status_reason TEXT,
        updated_at DATETIME,
        created_at DATETIME,
        UNIQUE KEY uq_algo_asset (algorithm_name, asset_class)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8");

    // 2. Walk-Forward Validation — out-of-sample testing to detect overfitting
    $conn->query("CREATE TABLE IF NOT EXISTS lm_walk_forward (
        id INT AUTO_INCREMENT PRIMARY KEY,
        algorithm_name VARCHAR(100) NOT NULL,
        asset_class VARCHAR(20) NOT NULL,
        train_start DATE NOT NULL,
        train_end DATE NOT NULL,
        test_start DATE NOT NULL,
        test_end DATE NOT NULL,
        train_sharpe DECIMAL(8,4) DEFAULT NULL,
        train_win_rate DECIMAL(5,2) DEFAULT NULL,
        train_trades INT DEFAULT 0,
        test_sharpe DECIMAL(8,4) DEFAULT NULL,
        test_win_rate DECIMAL(5,2) DEFAULT NULL,
        test_trades INT DEFAULT 0,
        test_pnl DECIMAL(10,2) DEFAULT NULL,
        tp_pct DECIMAL(5,2) DEFAULT NULL,
        sl_pct DECIMAL(5,2) DEFAULT NULL,
        max_hold_hours INT DEFAULT NULL,
        sharpe_decay_pct DECIMAL(5,2) DEFAULT NULL,
        is_overfit TINYINT DEFAULT 0,
        created_at DATETIME,
        INDEX idx_algo (algorithm_name, asset_class),
        INDEX idx_date (test_end)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8");

    // 3. Feature Importance — what drives each algorithm's predictions
    $conn->query("CREATE TABLE IF NOT EXISTS lm_feature_importance (
        id INT AUTO_INCREMENT PRIMARY KEY,
        algorithm_name VARCHAR(100) NOT NULL,
        asset_class VARCHAR(20) NOT NULL,
        feature_name VARCHAR(100) NOT NULL,
        importance_score DECIMAL(8,4) DEFAULT 0,
        importance_rank INT DEFAULT 0,
        calc_date DATE NOT NULL,
        sample_size INT DEFAULT 0,
        created_at DATETIME,
        INDEX idx_algo_date (algorithm_name, asset_class, calc_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8");

    // 4. Model Versions — track parameter versions deployed over time
    $conn->query("CREATE TABLE IF NOT EXISTS lm_model_versions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        algorithm_name VARCHAR(100) NOT NULL,
        asset_class VARCHAR(20) NOT NULL,
        version INT DEFAULT 1,
        tp_pct DECIMAL(5,2) DEFAULT NULL,
        sl_pct DECIMAL(5,2) DEFAULT NULL,
        max_hold_hours INT DEFAULT NULL,
        sharpe_at_deploy DECIMAL(8,4) DEFAULT NULL,
        win_rate_at_deploy DECIMAL(5,2) DEFAULT NULL,
        trades_at_deploy INT DEFAULT 0,
        is_active TINYINT DEFAULT 1,
        deployed_at DATETIME,
        retired_at DATETIME DEFAULT NULL,
        retire_reason VARCHAR(200) DEFAULT NULL,
        created_at DATETIME,
        INDEX idx_active (algorithm_name, asset_class, is_active)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8");

    // 5. Ensemble Weights — optimal combination of algorithms per asset class
    $conn->query("CREATE TABLE IF NOT EXISTS lm_ensemble_weights (
        id INT AUTO_INCREMENT PRIMARY KEY,
        asset_class VARCHAR(20) NOT NULL,
        algorithm_name VARCHAR(100) NOT NULL,
        ensemble_weight DECIMAL(5,4) DEFAULT 0,
        rolling_sharpe_30d DECIMAL(8,4) DEFAULT NULL,
        rolling_win_rate_30d DECIMAL(5,2) DEFAULT NULL,
        correlation_to_portfolio DECIMAL(5,4) DEFAULT NULL,
        information_ratio DECIMAL(8,4) DEFAULT NULL,
        calc_date DATE NOT NULL,
        created_at DATETIME,
        UNIQUE KEY uq_ensemble (asset_class, algorithm_name, calc_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8");

    // 6. Prediction Calibration — are confidence scores well-calibrated?
    $conn->query("CREATE TABLE IF NOT EXISTS lm_prediction_calibration (
        id INT AUTO_INCREMENT PRIMARY KEY,
        algorithm_name VARCHAR(100) NOT NULL,
        asset_class VARCHAR(20) NOT NULL,
        confidence_bucket VARCHAR(20) NOT NULL,
        total_predictions INT DEFAULT 0,
        correct_predictions INT DEFAULT 0,
        actual_accuracy DECIMAL(5,2) DEFAULT NULL,
        calibration_error DECIMAL(5,4) DEFAULT NULL,
        calc_date DATE NOT NULL,
        created_at DATETIME,
        INDEX idx_algo_date (algorithm_name, asset_class, calc_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8");

    // 7. Cross-Asset Correlation — detect correlated algorithms
    $conn->query("CREATE TABLE IF NOT EXISTS lm_cross_correlation (
        id INT AUTO_INCREMENT PRIMARY KEY,
        algo_a VARCHAR(100) NOT NULL,
        asset_a VARCHAR(20) NOT NULL,
        algo_b VARCHAR(100) NOT NULL,
        asset_b VARCHAR(20) NOT NULL,
        correlation DECIMAL(5,4) DEFAULT NULL,
        sample_size INT DEFAULT 0,
        calc_date DATE NOT NULL,
        created_at DATETIME,
        INDEX idx_date (calc_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8");

    // 8. Daily Picks Bridge — maps daily stock picks to live signal IDs
    $conn->query("CREATE TABLE IF NOT EXISTS lm_picks_bridge (
        id INT AUTO_INCREMENT PRIMARY KEY,
        source_table VARCHAR(50) NOT NULL,
        source_id INT NOT NULL,
        signal_id INT DEFAULT NULL,
        algorithm_name VARCHAR(100) NOT NULL,
        ticker VARCHAR(20) NOT NULL,
        pick_date DATE NOT NULL,
        direction VARCHAR(10) DEFAULT 'LONG',
        entry_price DECIMAL(12,4) DEFAULT NULL,
        tp_pct DECIMAL(5,2) DEFAULT NULL,
        sl_pct DECIMAL(5,2) DEFAULT NULL,
        max_hold_hours INT DEFAULT 168,
        status VARCHAR(20) DEFAULT 'pending',
        created_at DATETIME,
        UNIQUE KEY uq_source (source_table, source_id),
        INDEX idx_status (status),
        INDEX idx_date (pick_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8");

    return true;
}
?>
