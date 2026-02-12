<?php
/**
 * Mutual Funds Forward Performance Tracking — Schema
 * Tables for tracking MF pick outcomes, daily snapshots, and self-learning lessons.
 * PHP 5.2 compatible.
 *
 * Usage:
 *   require_once dirname(__FILE__) . '/mf2_performance_tracking_schema.php';
 *   mf2_ensure_tracking_schema($conn);
 *
 * Or call directly:
 *   GET https://findtorontoevents.ca/findmutualfunds2/portfolio2/api/mf2_performance_tracking_schema.php
 */

if (basename($_SERVER['SCRIPT_FILENAME']) === basename(__FILE__)) {
    require_once dirname(__FILE__) . '/db_connect.php';
}

function mf2_ensure_tracking_schema($conn) {
    $response = array('ok' => true, 'tables_created' => array(), 'errors' => array());

    // ── mf2_tracked_picks: each algorithm pick as a virtual position ──
    $sql = "CREATE TABLE IF NOT EXISTS mf2_tracked_picks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        algorithm_name VARCHAR(100) NOT NULL,
        pick_date DATE NOT NULL,
        entry_nav DECIMAL(12,4) NOT NULL,
        current_nav DECIMAL(12,4) DEFAULT NULL,
        current_return_pct DECIMAL(8,4) DEFAULT NULL,
        status ENUM('open','closed') DEFAULT 'open',
        exit_date DATE DEFAULT NULL,
        exit_nav DECIMAL(12,4) DEFAULT NULL,
        exit_reason VARCHAR(50) DEFAULT NULL,
        final_return_pct DECIMAL(8,4) DEFAULT NULL,
        peak_nav DECIMAL(12,4) DEFAULT NULL,
        trough_nav DECIMAL(12,4) DEFAULT NULL,
        hold_days INT DEFAULT 0,
        score DECIMAL(5,2) DEFAULT NULL,
        rating VARCHAR(10) DEFAULT NULL,
        created_at DATETIME DEFAULT NULL,
        UNIQUE KEY idx_symbol_algo_date (symbol, algorithm_name, pick_date),
        KEY idx_status (status),
        KEY idx_symbol (symbol)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8";
    if ($conn->query($sql)) {
        $response['tables_created'][] = 'mf2_tracked_picks';
    } else {
        $response['ok'] = false;
        $response['errors'][] = 'mf2_tracked_picks: ' . $conn->error;
    }

    // ── mf2_tracking_daily: daily snapshot of overall tracking performance ──
    $sql = "CREATE TABLE IF NOT EXISTS mf2_tracking_daily (
        id INT AUTO_INCREMENT PRIMARY KEY,
        track_date DATE NOT NULL,
        open_positions INT DEFAULT 0,
        total_closed INT DEFAULT 0,
        total_wins INT DEFAULT 0,
        total_losses INT DEFAULT 0,
        win_rate DECIMAL(5,2) DEFAULT 0,
        avg_win_pct DECIMAL(8,4) DEFAULT 0,
        avg_loss_pct DECIMAL(8,4) DEFAULT 0,
        avg_return_pct DECIMAL(8,4) DEFAULT 0,
        best_symbol VARCHAR(20) DEFAULT NULL,
        worst_symbol VARCHAR(20) DEFAULT NULL,
        avg_hold_days DECIMAL(5,1) DEFAULT 0,
        created_at DATETIME DEFAULT NULL,
        UNIQUE KEY idx_track_date (track_date)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8";
    if ($conn->query($sql)) {
        $response['tables_created'][] = 'mf2_tracking_daily';
    } else {
        $response['ok'] = false;
        $response['errors'][] = 'mf2_tracking_daily: ' . $conn->error;
    }

    // ── mf2_tracking_lessons: auto-detected patterns and self-learning insights ──
    $sql = "CREATE TABLE IF NOT EXISTS mf2_tracking_lessons (
        id INT AUTO_INCREMENT PRIMARY KEY,
        lesson_date DATE NOT NULL,
        lesson_type VARCHAR(50) NOT NULL,
        lesson_title VARCHAR(200) NOT NULL,
        lesson_text TEXT NOT NULL,
        confidence DECIMAL(5,2) DEFAULT 0,
        supporting_data TEXT DEFAULT NULL,
        applied TINYINT DEFAULT 0,
        impact_score DECIMAL(5,2) DEFAULT NULL,
        created_at DATETIME DEFAULT NULL,
        KEY idx_type (lesson_type),
        KEY idx_date (lesson_date)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8";
    if ($conn->query($sql)) {
        $response['tables_created'][] = 'mf2_tracking_lessons';
    } else {
        $response['ok'] = false;
        $response['errors'][] = 'mf2_tracking_lessons: ' . $conn->error;
    }

    return $response;
}

// When called directly, run schema creation and output JSON
if (basename($_SERVER['SCRIPT_FILENAME']) === basename(__FILE__)) {
    $result = mf2_ensure_tracking_schema($conn);
    echo json_encode($result);
    $conn->close();
}
?>
