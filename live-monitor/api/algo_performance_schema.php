<?php
/**
 * algo_performance_schema.php — Schema for pick performance tracking.
 * Adds columns to lm_signals and creates lm_pick_performance table.
 */

function _ap_ensure_schema($conn) {
    // ── Add param tracking columns to lm_signals (if not already present) ──
    $check = $conn->query("SHOW COLUMNS FROM lm_signals LIKE 'param_source'");
    if ($check && $check->num_rows === 0) {
        $conn->query("ALTER TABLE lm_signals
            ADD COLUMN param_source VARCHAR(10) NOT NULL DEFAULT 'original' AFTER rationale,
            ADD COLUMN tp_original DECIMAL(6,2) NOT NULL DEFAULT 0 AFTER param_source,
            ADD COLUMN sl_original DECIMAL(6,2) NOT NULL DEFAULT 0 AFTER tp_original,
            ADD COLUMN hold_original INT NOT NULL DEFAULT 0 AFTER sl_original");
    }

    // ── Daily algorithm performance snapshot table ──
    $conn->query("CREATE TABLE IF NOT EXISTS lm_algo_performance (
        id INT AUTO_INCREMENT PRIMARY KEY,
        snap_date DATE NOT NULL,
        algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
        asset_class VARCHAR(10) NOT NULL DEFAULT '',
        param_source VARCHAR(10) NOT NULL DEFAULT 'original',
        signals_count INT NOT NULL DEFAULT 0,
        trades_count INT NOT NULL DEFAULT 0,
        wins INT NOT NULL DEFAULT 0,
        losses INT NOT NULL DEFAULT 0,
        expired INT NOT NULL DEFAULT 0,
        total_pnl_pct DECIMAL(12,4) NOT NULL DEFAULT 0,
        avg_pnl_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
        win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
        best_trade_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
        worst_trade_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
        avg_hold_hours DECIMAL(8,2) NOT NULL DEFAULT 0,
        tp_used DECIMAL(6,2) NOT NULL DEFAULT 0,
        sl_used DECIMAL(6,2) NOT NULL DEFAULT 0,
        hold_used INT NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_snap (snap_date, algorithm_name, asset_class, param_source),
        KEY idx_date (snap_date),
        KEY idx_algo (algorithm_name),
        KEY idx_source (param_source)
    ) ENGINE=InnoDB");

    // ── Virtual comparison table: stores what-if results for both param sets ──
    $conn->query("CREATE TABLE IF NOT EXISTS lm_virtual_comparison (
        id INT AUTO_INCREMENT PRIMARY KEY,
        trade_id INT NOT NULL DEFAULT 0,
        signal_id INT NOT NULL DEFAULT 0,
        algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
        asset_class VARCHAR(10) NOT NULL DEFAULT '',
        symbol VARCHAR(20) NOT NULL DEFAULT '',
        direction VARCHAR(10) NOT NULL DEFAULT '',
        entry_price DECIMAL(18,8) NOT NULL DEFAULT 0,
        actual_param_source VARCHAR(10) NOT NULL DEFAULT 'original',
        actual_tp DECIMAL(6,2) NOT NULL DEFAULT 0,
        actual_sl DECIMAL(6,2) NOT NULL DEFAULT 0,
        actual_hold INT NOT NULL DEFAULT 0,
        actual_pnl_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
        actual_outcome VARCHAR(10) NOT NULL DEFAULT '',
        original_tp DECIMAL(6,2) NOT NULL DEFAULT 0,
        original_sl DECIMAL(6,2) NOT NULL DEFAULT 0,
        original_hold INT NOT NULL DEFAULT 0,
        virtual_original_pnl DECIMAL(10,4) NOT NULL DEFAULT 0,
        virtual_original_outcome VARCHAR(10) NOT NULL DEFAULT '',
        learned_tp DECIMAL(6,2) NOT NULL DEFAULT 0,
        learned_sl DECIMAL(6,2) NOT NULL DEFAULT 0,
        learned_hold INT NOT NULL DEFAULT 0,
        virtual_learned_pnl DECIMAL(10,4) NOT NULL DEFAULT 0,
        virtual_learned_outcome VARCHAR(10) NOT NULL DEFAULT '',
        opened_at DATETIME,
        closed_at DATETIME,
        created_at DATETIME NOT NULL,
        KEY idx_trade (trade_id),
        KEY idx_algo (algorithm_name),
        KEY idx_source (actual_param_source)
    ) ENGINE=InnoDB");

    return true;
}
