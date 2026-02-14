<?php
/**
 * Engine Health Scorer v1.0
 * ========================
 * Monitors all prediction engines, grades them A-F, and recommends
 * which to trust, investigate, or disable.
 *
 * Creates tables:
 *   eh_engine_grades  — current grade per engine
 *   eh_grade_history  — historical grade snapshots for trend analysis
 *   eh_alerts         — engine health alerts (degradation, improvement)
 *
 * Actions:
 *   ?action=grade_all    — Compute health grades for all engines
 *   ?action=leaderboard  — Show engines ranked by health score
 *   ?action=alerts       — Show recent health alerts
 *   ?action=status       — Table row counts and freshness
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

// Ensure tables
$conn->query("CREATE TABLE IF NOT EXISTS eh_engine_grades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    engine_name VARCHAR(60) NOT NULL,
    health_score FLOAT DEFAULT 0,
    health_grade VARCHAR(2) DEFAULT 'F',
    total_signals INT DEFAULT 0,
    resolved_signals INT DEFAULT 0,
    win_rate FLOAT DEFAULT 0,
    total_pnl FLOAT DEFAULT 0,
    avg_pnl FLOAT DEFAULT 0,
    sharpe_estimate FLOAT DEFAULT 0,
    data_freshness_hours FLOAT DEFAULT 999,
    signal_frequency_daily FLOAT DEFAULT 0,
    recommendation VARCHAR(30) DEFAULT 'INVESTIGATE',
    details TEXT,
    graded_at DATETIME,
    UNIQUE KEY engine_idx (engine_name)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS eh_grade_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    engine_name VARCHAR(60) NOT NULL,
    health_score FLOAT DEFAULT 0,
    health_grade VARCHAR(2) DEFAULT 'F',
    win_rate FLOAT DEFAULT 0,
    total_pnl FLOAT DEFAULT 0,
    resolved_signals INT DEFAULT 0,
    snapshot_at DATETIME,
    KEY engine_time (engine_name, snapshot_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS eh_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    engine_name VARCHAR(60) NOT NULL,
    alert_type VARCHAR(30) NOT NULL,
    severity VARCHAR(15) NOT NULL DEFAULT 'INFO',
    message TEXT,
    old_grade VARCHAR(2) DEFAULT '',
    new_grade VARCHAR(2) DEFAULT '',
    created_at DATETIME,
    KEY engine_time (engine_name, created_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$action = isset($_GET['action']) ? $_GET['action'] : 'grade_all';

switch ($action) {
    case 'grade_all':   _eh_grade_all($conn); break;
    case 'leaderboard': _eh_leaderboard($conn); break;
    case 'alerts':      _eh_alerts($conn); break;
    case 'status':      _eh_status($conn); break;
    default: echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}
$conn->close();

// ═══════════════════════════════════════════════════════════════
//  GRADE ALL: Compute health scores for all engines
// ═══════════════════════════════════════════════════════════════
function _eh_grade_all($conn) {
    $start = microtime(true);
    $results = array();

    // Get unified audit performance data
    $engines_data = array();
    $r = $conn->query("SELECT engine_name,
        COUNT(*) as total,
        SUM(CASE WHEN status != 'ACTIVE' THEN 1 ELSE 0 END) as resolved,
        SUM(CASE WHEN pnl_pct > 0 AND status != 'ACTIVE' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN pnl_pct <= 0 AND status != 'ACTIVE' THEN 1 ELSE 0 END) as losses,
        SUM(CASE WHEN status != 'ACTIVE' THEN pnl_pct ELSE 0 END) as total_pnl,
        AVG(CASE WHEN status != 'ACTIVE' THEN pnl_pct ELSE NULL END) as avg_pnl,
        MAX(signal_time) as latest_signal,
        MIN(signal_time) as earliest_signal,
        AVG(predictability_score) as avg_pred_score
        FROM ua_predictions GROUP BY engine_name");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $engines_data[$row['engine_name']] = $row;
        }
    }

    // Also check engines not in UA yet but known
    $known_engines = array(
        'Hybrid Engine', 'TV Technicals', 'Expert Consensus', 'Academic Edge',
        'Kimi Enhanced', 'Alpha Hunter', 'Proven Picks', 'Meme Scanner',
        'Crypto Winners', 'Live Monitor', 'Sports ML', 'Pro Signal Engine'
    );

    // Supplement with engine-specific data
    $supplements = array();

    // Proven Picks from its own table
    $r2 = $conn->query("SELECT COUNT(*) as total,
        SUM(CASE WHEN status='RESOLVED' AND pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN status='RESOLVED' THEN 1 ELSE 0 END) as resolved,
        SUM(CASE WHEN status='RESOLVED' THEN pnl_pct ELSE 0 END) as total_pnl,
        MAX(created_at) as latest_signal
        FROM pp_proven_picks");
    if ($r2 && $r2->num_rows > 0) {
        $pp = $r2->fetch_assoc();
        $supplements['Proven Picks'] = $pp;
    }

    // Meme Scanner
    $r3 = $conn->query("SELECT COUNT(*) as total,
        SUM(CASE WHEN outcome='win' OR outcome='partial_win' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN outcome IS NOT NULL AND outcome != '' THEN 1 ELSE 0 END) as resolved,
        MAX(created_at) as latest_signal
        FROM mc_winners");
    if ($r3 && $r3->num_rows > 0) {
        $ms = $r3->fetch_assoc();
        $supplements['Meme Scanner'] = $ms;
    }

    // Crypto Winners
    $r4 = $conn->query("SELECT COUNT(*) as total,
        SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN outcome IS NOT NULL AND outcome != '' THEN 1 ELSE 0 END) as resolved,
        MAX(created_at) as latest_signal
        FROM cw_winners");
    if ($r4 && $r4->num_rows > 0) {
        $cw = $r4->fetch_assoc();
        $supplements['Crypto Winners'] = $cw;
    }

    $now = time();

    foreach ($known_engines as $engine) {
        $ua = isset($engines_data[$engine]) ? $engines_data[$engine] : null;
        $sup = isset($supplements[$engine]) ? $supplements[$engine] : null;

        // Merge data
        $total = 0; $resolved = 0; $wins = 0; $total_pnl = 0; $avg_pnl = 0; $latest = '';

        if ($ua) {
            $total = (int)$ua['total'];
            $resolved = (int)$ua['resolved'];
            $wins = (int)$ua['wins'];
            $total_pnl = (float)$ua['total_pnl'];
            $avg_pnl = ($ua['avg_pnl'] !== null) ? (float)$ua['avg_pnl'] : 0;
            $latest = $ua['latest_signal'];
        }
        if ($sup) {
            // Use supplement data if UA doesn't have it (or as override)
            if (!$ua) {
                $total = (int)$sup['total'];
                $resolved = (int)$sup['resolved'];
                $wins = (int)$sup['wins'];
                $total_pnl = isset($sup['total_pnl']) ? (float)$sup['total_pnl'] : 0;
                $latest = $sup['latest_signal'];
            }
        }

        $win_rate = ($resolved > 0) ? round($wins / $resolved * 100, 1) : 0;

        // Data freshness (hours since latest signal)
        $freshness_hours = 999;
        if ($latest && $latest !== '' && $latest !== '0000-00-00 00:00:00') {
            $ts = strtotime($latest);
            if ($ts > 0) {
                $freshness_hours = round(($now - $ts) / 3600, 1);
            }
        }

        // Signal frequency (signals per day)
        $sig_freq = 0;
        if ($ua && $ua['earliest_signal'] && $ua['latest_signal']) {
            $span_hours = (strtotime($ua['latest_signal']) - strtotime($ua['earliest_signal'])) / 3600;
            if ($span_hours > 0) {
                $sig_freq = round($total / ($span_hours / 24), 2);
            }
        }

        // Estimate Sharpe (simplified: avg_pnl / stddev proxy)
        $sharpe = 0;
        if ($resolved >= 3 && $avg_pnl != 0) {
            // Use win_rate as a proxy for consistency
            $vol_proxy = max(0.1, abs($avg_pnl) * (1 + (100 - $win_rate) / 100));
            $sharpe = round($avg_pnl / $vol_proxy, 2);
        }

        // === HEALTH SCORE COMPUTATION (0-100) ===
        $score = 0;
        $details = array();

        // 1. Win Rate (30 pts max)
        if ($resolved >= 3) {
            $wr_pts = min(30, $win_rate * 0.4); // 75% WR = 30 pts
            $score += $wr_pts;
            $details[] = 'WR: ' . $win_rate . '% (' . round($wr_pts, 1) . 'pts)';
        } elseif ($resolved > 0) {
            $wr_pts = min(15, $win_rate * 0.2); // halved for small sample
            $score += $wr_pts;
            $details[] = 'WR: ' . $win_rate . '% (small sample, ' . round($wr_pts, 1) . 'pts)';
        } else {
            $details[] = 'WR: N/A (0 resolved)';
        }

        // 2. P&L Performance (25 pts max)
        if ($resolved > 0) {
            if ($total_pnl > 0) {
                $pnl_pts = min(25, $total_pnl * 0.5);
                $score += $pnl_pts;
                $details[] = 'PnL: +' . round($total_pnl, 2) . '% (' . round($pnl_pts, 1) . 'pts)';
            } else {
                // Negative PnL gets 0
                $details[] = 'PnL: ' . round($total_pnl, 2) . '% (0pts)';
            }
        }

        // 3. Signal Volume (15 pts max)
        if ($total >= 20) { $vol_pts = 15; }
        elseif ($total >= 10) { $vol_pts = 10; }
        elseif ($total >= 5) { $vol_pts = 7; }
        elseif ($total >= 1) { $vol_pts = 3; }
        else { $vol_pts = 0; }
        $score += $vol_pts;
        $details[] = 'Volume: ' . $total . ' signals (' . $vol_pts . 'pts)';

        // 4. Data Freshness (15 pts max)
        if ($freshness_hours <= 6) { $fresh_pts = 15; }
        elseif ($freshness_hours <= 24) { $fresh_pts = 12; }
        elseif ($freshness_hours <= 48) { $fresh_pts = 8; }
        elseif ($freshness_hours <= 96) { $fresh_pts = 4; }
        else { $fresh_pts = 0; }
        $score += $fresh_pts;
        $details[] = 'Fresh: ' . $freshness_hours . 'h (' . $fresh_pts . 'pts)';

        // 5. Statistical Confidence (15 pts max)
        if ($resolved >= 30) { $conf_pts = 15; }
        elseif ($resolved >= 15) { $conf_pts = 10; }
        elseif ($resolved >= 5) { $conf_pts = 5; }
        elseif ($resolved >= 1) { $conf_pts = 2; }
        else { $conf_pts = 0; }
        $score += $conf_pts;
        $details[] = 'Confidence: ' . $resolved . ' resolved (' . $conf_pts . 'pts)';

        // Grade
        if ($score >= 80) { $grade = 'A'; }
        elseif ($score >= 65) { $grade = 'B'; }
        elseif ($score >= 50) { $grade = 'C'; }
        elseif ($score >= 35) { $grade = 'D'; }
        else { $grade = 'F'; }

        // Recommendation
        if ($grade === 'A' || $grade === 'B') {
            $rec = 'TRUST';
        } elseif ($grade === 'C') {
            $rec = 'MONITOR';
        } elseif ($grade === 'D') {
            $rec = 'INVESTIGATE';
        } else {
            if ($resolved >= 5 && $win_rate < 20) { $rec = 'DISABLE'; }
            elseif ($total == 0) { $rec = 'NOT_ACTIVE'; }
            else { $rec = 'INVESTIGATE'; }
        }

        // Penalty for confirmed bad performance
        if ($resolved >= 5 && $win_rate < 10) {
            $score = max(0, $score - 20);
            $grade = 'F';
            $rec = 'DISABLE';
            $details[] = 'PENALTY: -20pts (WR<10% with 5+ samples)';
        }

        // Check for grade change (alert)
        $prev_grade = '';
        $pg = $conn->query(sprintf("SELECT health_grade FROM eh_engine_grades WHERE engine_name='%s'", $conn->real_escape_string($engine)));
        if ($pg && $pg->num_rows > 0) {
            $pgr = $pg->fetch_assoc();
            $prev_grade = $pgr['health_grade'];
        }

        // Upsert grade
        $conn->query(sprintf(
            "DELETE FROM eh_engine_grades WHERE engine_name='%s'",
            $conn->real_escape_string($engine)
        ));
        $conn->query(sprintf(
            "INSERT INTO eh_engine_grades (engine_name, health_score, health_grade, total_signals, resolved_signals,
             win_rate, total_pnl, avg_pnl, sharpe_estimate, data_freshness_hours, signal_frequency_daily,
             recommendation, details, graded_at)
             VALUES ('%s', %.1f, '%s', %d, %d, %.1f, %.4f, %.4f, %.2f, %.1f, %.2f, '%s', '%s', '%s')",
            $conn->real_escape_string($engine),
            $score, $conn->real_escape_string($grade),
            $total, $resolved, $win_rate, $total_pnl, $avg_pnl,
            $sharpe, $freshness_hours, $sig_freq,
            $conn->real_escape_string($rec),
            $conn->real_escape_string(implode(' | ', $details)),
            date('Y-m-d H:i:s')
        ));

        // History snapshot
        $conn->query(sprintf(
            "INSERT INTO eh_grade_history (engine_name, health_score, health_grade, win_rate, total_pnl, resolved_signals, snapshot_at)
             VALUES ('%s', %.1f, '%s', %.1f, %.4f, %d, '%s')",
            $conn->real_escape_string($engine),
            $score, $conn->real_escape_string($grade),
            $win_rate, $total_pnl, $resolved,
            date('Y-m-d H:i:s')
        ));

        // Alert on grade change
        if ($prev_grade !== '' && $prev_grade !== $grade) {
            $grades_order = array('F' => 0, 'D' => 1, 'C' => 2, 'B' => 3, 'A' => 4);
            $old_val = isset($grades_order[$prev_grade]) ? $grades_order[$prev_grade] : 0;
            $new_val = isset($grades_order[$grade]) ? $grades_order[$grade] : 0;
            $type = ($new_val > $old_val) ? 'IMPROVEMENT' : 'DEGRADATION';
            $sev = ($new_val < $old_val && $grade === 'F') ? 'CRITICAL' : (($new_val < $old_val) ? 'WARNING' : 'INFO');

            $conn->query(sprintf(
                "INSERT INTO eh_alerts (engine_name, alert_type, severity, message, old_grade, new_grade, created_at)
                 VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s')",
                $conn->real_escape_string($engine),
                $conn->real_escape_string($type),
                $conn->real_escape_string($sev),
                $conn->real_escape_string($engine . ' grade changed: ' . $prev_grade . ' -> ' . $grade),
                $conn->real_escape_string($prev_grade),
                $conn->real_escape_string($grade),
                date('Y-m-d H:i:s')
            ));
        }

        $results[] = array(
            'engine' => $engine,
            'score' => round($score, 1),
            'grade' => $grade,
            'recommendation' => $rec,
            'total_signals' => $total,
            'resolved' => $resolved,
            'win_rate' => $win_rate,
            'total_pnl' => round($total_pnl, 2),
            'freshness_hours' => $freshness_hours,
            'details' => $details
        );
    }

    // Sort by score descending
    usort($results, '_eh_sort_by_score');

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array(
        'ok' => true,
        'engines' => $results,
        'total_engines' => count($results),
        'elapsed_ms' => $elapsed,
        'graded_at' => date('Y-m-d H:i:s')
    ));
}

function _eh_sort_by_score($a, $b) {
    if ($a['score'] == $b['score']) return 0;
    return ($a['score'] > $b['score']) ? -1 : 1;
}

// ═══════════════════════════════════════════════════════════════
//  LEADERBOARD: Show engines ranked by health score
// ═══════════════════════════════════════════════════════════════
function _eh_leaderboard($conn) {
    $engines = array();
    $r = $conn->query("SELECT * FROM eh_engine_grades ORDER BY health_score DESC");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $engines[] = $row;
        }
    }
    echo json_encode(array('ok' => true, 'engines' => $engines));
}

// ═══════════════════════════════════════════════════════════════
//  ALERTS: Show recent health alerts
// ═══════════════════════════════════════════════════════════════
function _eh_alerts($conn) {
    $alerts = array();
    $r = $conn->query("SELECT * FROM eh_alerts ORDER BY created_at DESC LIMIT 50");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $alerts[] = $row;
        }
    }
    echo json_encode(array('ok' => true, 'alerts' => $alerts));
}

// ═══════════════════════════════════════════════════════════════
//  STATUS: Table row counts
// ═══════════════════════════════════════════════════════════════
function _eh_status($conn) {
    $tables = array('eh_engine_grades', 'eh_grade_history', 'eh_alerts');
    $result = array();
    foreach ($tables as $t) {
        $cnt = 0;
        $r = $conn->query("SELECT COUNT(*) as cnt FROM " . $t);
        if ($r) { $row = $r->fetch_assoc(); $cnt = (int)$row['cnt']; }
        $result[] = array('table' => $t, 'rows' => $cnt);
    }
    echo json_encode(array('ok' => true, 'tables' => $result));
}
