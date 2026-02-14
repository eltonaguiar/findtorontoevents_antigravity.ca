<?php
/**
 * Unified Prediction Audit Trail v1.0
 * 
 * Aggregates ALL predictions from ALL engines into one auditable table.
 * This is the single source of truth for platform performance measurement.
 *
 * Every prediction gets a unique ID, entry timestamp, exit conditions,
 * and a resolution with P&L — regardless of which engine generated it.
 *
 * PHP 5.2 compatible.
 *
 * Actions:
 *   ?action=collect      — Collect active signals from all engines into unified table
 *   ?action=audit        — Show unified audit trail with performance stats
 *   ?action=performance  — Cross-engine performance comparison
 *   ?action=asset_report — Per-asset performance across all engines
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

// ═══ Schema ═══
$conn->query("CREATE TABLE IF NOT EXISTS ua_predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    engine_name VARCHAR(50) NOT NULL,
    engine_signal_id VARCHAR(50) DEFAULT '',
    asset_class VARCHAR(20) NOT NULL DEFAULT 'CRYPTO',
    pair VARCHAR(30) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    confidence FLOAT DEFAULT 0,
    entry_price FLOAT DEFAULT 0,
    tp_price FLOAT DEFAULT 0,
    sl_price FLOAT DEFAULT 0,
    tp_pct FLOAT DEFAULT 0,
    sl_pct FLOAT DEFAULT 0,
    predictability_score FLOAT DEFAULT 0,
    signal_time DATETIME,
    expires_at DATETIME,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    exit_price FLOAT DEFAULT 0,
    pnl_pct FLOAT DEFAULT 0,
    exit_reason VARCHAR(30) DEFAULT '',
    resolved_at DATETIME DEFAULT NULL,
    hold_hours FLOAT DEFAULT 0,
    collected_at DATETIME,
    UNIQUE KEY engine_sig (engine_name, engine_signal_id),
    KEY status_idx (status),
    KEY pair_idx (pair),
    KEY engine_idx (engine_name)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS ua_engine_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    engine_name VARCHAR(50) NOT NULL,
    asset_class VARCHAR(20) DEFAULT 'ALL',
    total_predictions INT DEFAULT 0,
    resolved INT DEFAULT 0,
    tp_hits INT DEFAULT 0,
    sl_hits INT DEFAULT 0,
    expired INT DEFAULT 0,
    win_rate FLOAT DEFAULT 0,
    avg_pnl FLOAT DEFAULT 0,
    total_pnl FLOAT DEFAULT 0,
    best_trade_pnl FLOAT DEFAULT 0,
    worst_trade_pnl FLOAT DEFAULT 0,
    avg_hold_hours FLOAT DEFAULT 0,
    sharpe_ratio FLOAT DEFAULT 0,
    profit_factor FLOAT DEFAULT 0,
    computed_at DATETIME,
    UNIQUE KEY eng_class (engine_name, asset_class)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$action = isset($_GET['action']) ? $_GET['action'] : 'audit';

switch ($action) {
    case 'collect':   _ua_collect($conn); break;
    case 'sync_resolutions': _ua_sync_resolutions($conn); break;
    case 'audit':     _ua_audit($conn); break;
    case 'performance': _ua_performance($conn); break;
    case 'asset_report': _ua_asset_report($conn); break;
    default: echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}
$conn->close();

// ═══════════════════════════════════════════════════════════════
//  COLLECT: Pull active signals from all engines into unified table
// ═══════════════════════════════════════════════════════════════
function _ua_collect($conn) {
    $start = microtime(true);
    $collected = 0;
    $skipped = 0;

    // Fetch predictability scores for weighting
    $ps = array();
    $r = $conn->query("SELECT pair, predictability_score FROM ps_scores");
    if ($r) { while ($row = $r->fetch_assoc()) { $ps[$row['pair']] = (float)$row['predictability_score']; } }

    // Define engine endpoints and how to parse their signals
    $engines = array(
        array('name' => 'Hybrid Engine', 'url' => 'https://findtorontoevents.ca/findcryptopairs/api/hybrid_engine.php?action=signals', 'sig_key' => 'active', 'id_field' => 'id'),
        array('name' => 'TV Technicals', 'url' => 'https://findtorontoevents.ca/findcryptopairs/api/tv_technicals.php?action=signals', 'sig_key' => 'active', 'id_field' => 'id'),
        array('name' => 'Kimi Enhanced', 'url' => 'https://findtorontoevents.ca/findcryptopairs/api/kimi_enhanced.php?action=signals', 'sig_key' => 'active', 'id_field' => 'id'),
        array('name' => 'Academic Edge', 'url' => 'https://findtorontoevents.ca/findcryptopairs/api/academic_edge.php?action=signals', 'sig_key' => 'active', 'id_field' => 'id'),
        array('name' => 'Expert Consensus', 'url' => 'https://findtorontoevents.ca/findcryptopairs/api/expert_consensus.php?action=signals', 'sig_key' => 'active', 'id_field' => 'id'),
        array('name' => 'Alpha Hunter', 'url' => 'https://findtorontoevents.ca/findcryptopairs/api/alpha_hunter.php?action=signals', 'sig_key' => 'active', 'id_field' => 'id')
    );

    foreach ($engines as $eng) {
        $ch = curl_init($eng['url']);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        $resp = curl_exec($ch);
        curl_close($ch);
        if (!$resp) continue;
        $data = json_decode($resp, true);
        if (!is_array($data)) continue;

        $signals = isset($data[$eng['sig_key']]) ? $data[$eng['sig_key']] : array();
        if (!is_array($signals)) continue;

        foreach ($signals as $sig) {
            $sig_id = isset($sig[$eng['id_field']]) ? $sig[$eng['id_field']] : '';
            if ($sig_id === '') continue;

            $pair = isset($sig['pair']) ? $sig['pair'] : '';
            $dir = isset($sig['direction']) ? strtoupper($sig['direction']) : '';
            $conf = isset($sig['confidence']) ? (float)$sig['confidence'] : 0;
            $entry = isset($sig['entry_price']) ? (float)$sig['entry_price'] : 0;
            $tp_pct = isset($sig['tp_pct']) ? (float)$sig['tp_pct'] : 0;
            $sl_pct = isset($sig['sl_pct']) ? (float)$sig['sl_pct'] : 0;
            $created = isset($sig['created_at']) ? $sig['created_at'] : date('Y-m-d H:i:s');
            $expires = isset($sig['expires_at']) ? $sig['expires_at'] : '';
            $status = isset($sig['status']) ? strtoupper($sig['status']) : 'ACTIVE';

            $pred_score = isset($ps[$pair]) ? $ps[$pair] : 0;

            // Check if already exists
            $check = $conn->query(sprintf(
                "SELECT id FROM ua_predictions WHERE engine_name='%s' AND engine_signal_id='%s'",
                $conn->real_escape_string($eng['name']),
                $conn->real_escape_string($sig_id)
            ));
            if ($check && $check->num_rows > 0) {
                $skipped++;
                continue;
            }

            $conn->query(sprintf(
                "INSERT INTO ua_predictions (engine_name, engine_signal_id, asset_class, pair, direction, 
                 confidence, entry_price, tp_pct, sl_pct, predictability_score,
                 signal_time, expires_at, status, collected_at)
                 VALUES ('%s','%s','CRYPTO','%s','%s',%.2f,%.8f,%.2f,%.2f,%.1f,'%s','%s','%s','%s')",
                $conn->real_escape_string($eng['name']),
                $conn->real_escape_string($sig_id),
                $conn->real_escape_string($pair),
                $conn->real_escape_string($dir),
                $conf, $entry, $tp_pct, $sl_pct, $pred_score,
                $conn->real_escape_string($created),
                $conn->real_escape_string($expires),
                $conn->real_escape_string($status),
                date('Y-m-d H:i:s')
            ));
            $collected++;
        }
    }

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array(
        'ok' => true,
        'collected' => $collected,
        'skipped_duplicates' => $skipped,
        'elapsed_ms' => $elapsed
    ));
}

// ═══════════════════════════════════════════════════════════════
//  SYNC RESOLUTIONS: Pull resolved signals from engines and update
//  ua_predictions rows from ACTIVE to resolved status.
//  This fixes the audit showing 0 resolved when engines have history.
// ═══════════════════════════════════════════════════════════════
function _ua_sync_resolutions($conn) {
    $start = microtime(true);
    $synced = 0;
    $errors = array();

    // Engines that return 'history' array with resolved signals
    $engines = array(
        array('name' => 'Hybrid Engine', 'url' => 'https://findtorontoevents.ca/findcryptopairs/api/hybrid_engine.php?action=signals', 'hist_key' => 'history', 'id_field' => 'id'),
        array('name' => 'TV Technicals', 'url' => 'https://findtorontoevents.ca/findcryptopairs/api/tv_technicals.php?action=signals', 'hist_key' => 'history', 'id_field' => 'id'),
        array('name' => 'Expert Consensus', 'url' => 'https://findtorontoevents.ca/findcryptopairs/api/expert_consensus.php?action=signals', 'hist_key' => 'history', 'id_field' => 'id'),
        array('name' => 'Alpha Hunter', 'url' => 'https://findtorontoevents.ca/findcryptopairs/api/alpha_hunter.php?action=signals', 'hist_key' => 'history', 'id_field' => 'id'),
        array('name' => 'Kimi Enhanced', 'url' => 'https://findtorontoevents.ca/findcryptopairs/api/kimi_enhanced.php?action=signals', 'hist_key' => 'history', 'id_field' => 'id'),
        array('name' => 'Academic Edge', 'url' => 'https://findtorontoevents.ca/findcryptopairs/api/academic_edge.php?action=signals', 'hist_key' => 'history', 'id_field' => 'id')
    );

    foreach ($engines as $eng) {
        $ch = curl_init($eng['url']);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        $resp = curl_exec($ch);
        curl_close($ch);
        if (!$resp) { $errors[] = $eng['name'] . ': no response'; continue; }
        $data = json_decode($resp, true);
        if (!is_array($data)) { $errors[] = $eng['name'] . ': invalid JSON'; continue; }

        $history = isset($data[$eng['hist_key']]) ? $data[$eng['hist_key']] : array();
        if (!is_array($history)) continue;

        foreach ($history as $h) {
            $sig_id = isset($h[$eng['id_field']]) ? $h[$eng['id_field']] : '';
            if ($sig_id === '') continue;

            // Get resolution info from engine
            $status = isset($h['status']) ? strtoupper($h['status']) : '';
            if ($status === '' || $status === 'ACTIVE') continue; // only resolved

            $exit_price = 0;
            if (isset($h['exit_price'])) { $exit_price = (float)$h['exit_price']; }
            elseif (isset($h['current_price'])) { $exit_price = (float)$h['current_price']; }
            elseif (isset($h['price'])) { $exit_price = (float)$h['price']; }

            $pnl = isset($h['pnl_pct']) ? (float)$h['pnl_pct'] : 0;
            $reason = isset($h['exit_reason']) ? $h['exit_reason'] : $status;
            $resolved_at = isset($h['resolved_at']) ? $h['resolved_at'] : date('Y-m-d H:i:s');

            // Try to update matching ua_predictions row
            $sql = sprintf(
                "UPDATE ua_predictions SET status='%s', exit_price=%.8f, pnl_pct=%.4f, exit_reason='%s', resolved_at='%s'
                 WHERE engine_name='%s' AND engine_signal_id='%s' AND status='ACTIVE'",
                $conn->real_escape_string($status),
                $exit_price,
                $pnl,
                $conn->real_escape_string($reason),
                $conn->real_escape_string($resolved_at),
                $conn->real_escape_string($eng['name']),
                $conn->real_escape_string($sig_id)
            );
            $conn->query($sql);
            if ($conn->affected_rows > 0) {
                $synced++;
            } else {
                // Signal was resolved before it was collected — INSERT it as resolved
                $check = $conn->query(sprintf(
                    "SELECT id FROM ua_predictions WHERE engine_name='%s' AND engine_signal_id='%s'",
                    $conn->real_escape_string($eng['name']),
                    $conn->real_escape_string($sig_id)
                ));
                if (!$check || $check->num_rows == 0) {
                    // Missing entirely — insert the resolved signal
                    $pair = isset($h['pair']) ? $h['pair'] : '';
                    $dir = isset($h['direction']) ? strtoupper($h['direction']) : '';
                    $conf = isset($h['confidence']) ? (float)$h['confidence'] : 0;
                    $entry_price = isset($h['entry_price']) ? (float)$h['entry_price'] : 0;
                    $tp_pct = isset($h['tp_pct']) ? (float)$h['tp_pct'] : 0;
                    $sl_pct = isset($h['sl_pct']) ? (float)$h['sl_pct'] : 0;
                    $created = isset($h['created_at']) ? $h['created_at'] : '';
                    $ps_val = 0;
                    $ps_r = $conn->query(sprintf("SELECT predictability_score FROM ps_scores WHERE pair='%s'", $conn->real_escape_string($pair)));
                    if ($ps_r && $ps_r->num_rows > 0) { $ps_row = $ps_r->fetch_assoc(); $ps_val = (float)$ps_row['predictability_score']; }

                    $conn->query(sprintf(
                        "INSERT INTO ua_predictions (engine_name, engine_signal_id, asset_class, pair, direction,
                         confidence, entry_price, tp_pct, sl_pct, predictability_score,
                         signal_time, status, exit_price, pnl_pct, exit_reason, resolved_at, collected_at)
                         VALUES ('%s','%s','CRYPTO','%s','%s',%.2f,%.8f,%.2f,%.2f,%.1f,'%s','%s',%.8f,%.4f,'%s','%s','%s')",
                        $conn->real_escape_string($eng['name']),
                        $conn->real_escape_string($sig_id),
                        $conn->real_escape_string($pair),
                        $conn->real_escape_string($dir),
                        $conf, $entry_price, $tp_pct, $sl_pct, $ps_val,
                        $conn->real_escape_string($created),
                        $conn->real_escape_string($status),
                        $exit_price, $pnl,
                        $conn->real_escape_string($reason),
                        $conn->real_escape_string($resolved_at),
                        date('Y-m-d H:i:s')
                    ));
                    if ($conn->affected_rows > 0) $synced++;
                }
            }
        }
    }

    // Also resolve expired predictions (signals older than 96h still ACTIVE)
    $expired = 0;
    $r = $conn->query("SELECT id, pair, direction, entry_price FROM ua_predictions 
        WHERE status='ACTIVE' AND signal_time < DATE_SUB(NOW(), INTERVAL 96 HOUR)");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            // Mark as expired
            $conn->query(sprintf(
                "UPDATE ua_predictions SET status='EXPIRED', exit_reason='EXPIRED_96H', resolved_at='%s' WHERE id=%d",
                date('Y-m-d H:i:s'), (int)$row['id']
            ));
            if ($conn->affected_rows > 0) $expired++;
        }
    }

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array(
        'ok' => true,
        'synced_from_engines' => $synced,
        'expired_stale' => $expired,
        'errors' => $errors,
        'elapsed_ms' => $elapsed
    ));
}

// ═══════════════════════════════════════════════════════════════
//  AUDIT: Show unified audit trail
// ═══════════════════════════════════════════════════════════════
function _ua_audit($conn) {
    $active = array();
    $resolved = array();

    $r = $conn->query("SELECT * FROM ua_predictions WHERE status='ACTIVE' ORDER BY signal_time DESC LIMIT 100");
    if ($r) { while ($row = $r->fetch_assoc()) { $active[] = $row; } }

    $r = $conn->query("SELECT * FROM ua_predictions WHERE status != 'ACTIVE' ORDER BY resolved_at DESC LIMIT 100");
    if ($r) { while ($row = $r->fetch_assoc()) { $resolved[] = $row; } }

    // Quick stats
    $total = 0; $wins = 0; $total_pnl = 0;
    $r = $conn->query("SELECT COUNT(*) as cnt, SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins, 
        SUM(pnl_pct) as total_pnl FROM ua_predictions WHERE status != 'ACTIVE'");
    if ($r) {
        $row = $r->fetch_assoc();
        $total = (int)$row['cnt'];
        $wins = (int)$row['wins'];
        $total_pnl = (float)$row['total_pnl'];
    }

    echo json_encode(array(
        'ok' => true,
        'stats' => array(
            'active_predictions' => count($active),
            'resolved_predictions' => $total,
            'win_rate' => ($total > 0) ? round($wins / $total * 100, 1) : 0,
            'total_pnl' => round($total_pnl, 2)
        ),
        'active' => $active,
        'resolved' => $resolved
    ));
}

// ═══════════════════════════════════════════════════════════════
//  PERFORMANCE: Cross-engine comparison
// ═══════════════════════════════════════════════════════════════
function _ua_performance($conn) {
    $engines = array();
    $r = $conn->query("SELECT engine_name, 
        COUNT(*) as total,
        SUM(CASE WHEN status != 'ACTIVE' THEN 1 ELSE 0 END) as resolved,
        SUM(CASE WHEN pnl_pct > 0 AND status != 'ACTIVE' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN status != 'ACTIVE' THEN pnl_pct ELSE 0 END) as total_pnl,
        AVG(CASE WHEN status != 'ACTIVE' THEN pnl_pct ELSE NULL END) as avg_pnl,
        MAX(CASE WHEN status != 'ACTIVE' THEN pnl_pct ELSE NULL END) as best_pnl,
        MIN(CASE WHEN status != 'ACTIVE' THEN pnl_pct ELSE NULL END) as worst_pnl,
        AVG(predictability_score) as avg_pred_score
        FROM ua_predictions GROUP BY engine_name ORDER BY total_pnl DESC");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $resolved = (int)$row['resolved'];
            $wins = (int)$row['wins'];
            $row['win_rate'] = ($resolved > 0) ? round($wins / $resolved * 100, 1) : 0;
            $engines[] = $row;
        }
    }

    echo json_encode(array('ok' => true, 'engines' => $engines));
}

// ═══════════════════════════════════════════════════════════════
//  ASSET REPORT: Per-asset performance across all engines
// ═══════════════════════════════════════════════════════════════
function _ua_asset_report($conn) {
    $assets = array();
    $r = $conn->query("SELECT pair,
        COUNT(*) as total_signals,
        SUM(CASE WHEN status != 'ACTIVE' THEN 1 ELSE 0 END) as resolved,
        SUM(CASE WHEN pnl_pct > 0 AND status != 'ACTIVE' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN status != 'ACTIVE' THEN pnl_pct ELSE 0 END) as total_pnl,
        AVG(predictability_score) as avg_pred_score,
        COUNT(DISTINCT engine_name) as engines_covering
        FROM ua_predictions GROUP BY pair ORDER BY total_signals DESC");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $resolved = (int)$row['resolved'];
            $wins = (int)$row['wins'];
            $row['win_rate'] = ($resolved > 0) ? round($wins / $resolved * 100, 1) : 0;
            $assets[] = $row;
        }
    }

    echo json_encode(array('ok' => true, 'assets' => $assets));
}
