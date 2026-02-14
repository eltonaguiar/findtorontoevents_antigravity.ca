<?php
/**
 * Quant Bridge API
 * Stores and serves results from Sprint 1+2 quant bridge modules.
 * PHP 5.2 compatible — no short arrays, no http_response_code()
 *
 * Actions:
 *   store_results  — store module run results (admin key required)
 *   dashboard      — get all bridge module data (public)
 *   module         — get data for a specific module (public)
 *   latest_run     — get latest run summary (public)
 */

require_once dirname(__FILE__) . '/db_connect.php';

$ADMIN_KEY = 'livetrader2026';

// ─── Auto-create quant bridge tables ─────────────────────────────────
$conn->query("
CREATE TABLE IF NOT EXISTS lm_quant_bridge (
    id INT AUTO_INCREMENT PRIMARY KEY,
    module_name VARCHAR(50) NOT NULL,
    run_source VARCHAR(30) NOT NULL DEFAULT 'github',
    status VARCHAR(20) NOT NULL DEFAULT 'success',
    result_data LONGTEXT,
    summary TEXT,
    run_at DATETIME NOT NULL,
    KEY idx_module (module_name),
    KEY idx_run (run_at),
    KEY idx_status (status)
) ENGINE=MyISAM DEFAULT CHARSET=utf8
");

// Sentiment per ticker
$conn->query("
CREATE TABLE IF NOT EXISTS lm_bridge_sentiment (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    sentiment_score DECIMAL(8,4) NOT NULL DEFAULT 0,
    sentiment_label VARCHAR(20) NOT NULL DEFAULT 'neutral',
    confidence DECIMAL(6,4) NOT NULL DEFAULT 0,
    num_articles INT NOT NULL DEFAULT 0,
    positive_pct DECIMAL(5,1) NOT NULL DEFAULT 0,
    negative_pct DECIMAL(5,1) NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_ticker (ticker)
) ENGINE=MyISAM DEFAULT CHARSET=utf8
");

// CUSUM algo health
$conn->query("
CREATE TABLE IF NOT EXISTS lm_bridge_cusum (
    id INT AUTO_INCREMENT PRIMARY KEY,
    algorithm_name VARCHAR(100) NOT NULL,
    decay_status VARCHAR(20) NOT NULL DEFAULT 'unknown',
    recommended_weight DECIMAL(6,3) NOT NULL DEFAULT 1.0,
    last_sharpe DECIMAL(8,4) NOT NULL DEFAULT 0,
    last_win_rate DECIMAL(6,4) NOT NULL DEFAULT 0,
    change_points INT NOT NULL DEFAULT 0,
    total_trades INT NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_algo (algorithm_name)
) ENGINE=MyISAM DEFAULT CHARSET=utf8
");

// Congressional signals
$conn->query("
CREATE TABLE IF NOT EXISTS lm_bridge_congress (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    signal_type VARCHAR(50) NOT NULL,
    strength INT NOT NULL DEFAULT 50,
    members_buying INT NOT NULL DEFAULT 0,
    description TEXT,
    updated_at DATETIME NOT NULL,
    KEY idx_ticker (ticker),
    KEY idx_type (signal_type)
) ENGINE=MyISAM DEFAULT CHARSET=utf8
");

// Options flow / GEX
$conn->query("
CREATE TABLE IF NOT EXISTS lm_bridge_options (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    spot_price DECIMAL(12,2) NOT NULL DEFAULT 0,
    net_gex DECIMAL(20,0) NOT NULL DEFAULT 0,
    gex_signal VARCHAR(30) NOT NULL DEFAULT '',
    pc_oi_ratio DECIMAL(8,3) NOT NULL DEFAULT 0,
    pcr_signal VARCHAR(30) NOT NULL DEFAULT '',
    unusual_count INT NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_ticker (ticker)
) ENGINE=MyISAM DEFAULT CHARSET=utf8
");

// On-chain metrics
$conn->query("
CREATE TABLE IF NOT EXISTS lm_bridge_onchain (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metric_name VARCHAR(50) NOT NULL,
    metric_value DECIMAL(20,4) NOT NULL DEFAULT 0,
    metric_label VARCHAR(100) NOT NULL DEFAULT '',
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_metric (metric_name)
) ENGINE=MyISAM DEFAULT CHARSET=utf8
");

// Portfolio weights
$conn->query("
CREATE TABLE IF NOT EXISTS lm_bridge_portfolio (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_name VARCHAR(30) NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    weight DECIMAL(8,4) NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL,
    KEY idx_strategy (strategy_name),
    KEY idx_ticker (ticker)
) ENGINE=MyISAM DEFAULT CHARSET=utf8
");

// Transfer entropy leaders
$conn->query("
CREATE TABLE IF NOT EXISTS lm_bridge_entropy (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'neutral',
    outgoing_te DECIMAL(10,6) NOT NULL DEFAULT 0,
    incoming_te DECIMAL(10,6) NOT NULL DEFAULT 0,
    net_te DECIMAL(10,6) NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_ticker (ticker)
) ENGINE=MyISAM DEFAULT CHARSET=utf8
");

// ─── CORS ────────────────────────────────────────────────────────────
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

$action = isset($_GET['action']) ? $_GET['action'] : (isset($_POST['action']) ? $_POST['action'] : '');

function _qb_check_key() {
    global $ADMIN_KEY;
    $key = isset($_GET['key']) ? $_GET['key'] : (isset($_POST['key']) ? $_POST['key'] : '');
    return ($key === $ADMIN_KEY);
}

function _qb_now() {
    return gmdate('Y-m-d H:i:s');
}

// ════════════════════════════════════════════════════════════════════════
//  ACTION: store_results — Store results from a bridge module run
// ════════════════════════════════════════════════════════════════════════
if ($action === 'store_results') {
    if (!_qb_check_key()) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
        exit;
    }

    $module  = isset($_POST['module'])  ? $conn->real_escape_string($_POST['module']) : '';
    $source  = isset($_POST['source'])  ? $conn->real_escape_string($_POST['source']) : 'github';
    $status  = isset($_POST['status'])  ? $conn->real_escape_string($_POST['status']) : 'success';
    $data    = isset($_POST['data'])    ? $conn->real_escape_string($_POST['data']) : '{}';
    $summary = isset($_POST['summary']) ? $conn->real_escape_string($_POST['summary']) : '';
    $now     = _qb_now();

    if (!$module) {
        echo json_encode(array('ok' => false, 'error' => 'module required'));
        exit;
    }

    $conn->query("INSERT INTO lm_quant_bridge
        (module_name, run_source, status, result_data, summary, run_at)
        VALUES ('$module', '$source', '$status', '$data', '$summary', '$now')");

    // Also store into specific tables based on module
    $decoded = json_decode(stripslashes($data), true);

    if ($module === 'finbert_sentiment' && is_array($decoded)) {
        $sentiments = isset($decoded['sentiments']) ? $decoded['sentiments'] : $decoded;
        foreach ($sentiments as $s) {
            if (!isset($s['ticker'])) continue;
            $t = $conn->real_escape_string($s['ticker']);
            $sc = floatval($s['sentiment_score']);
            $lb = $conn->real_escape_string($s['sentiment_label']);
            $cf = floatval($s['confidence']);
            $na = intval($s['num_articles']);
            $pp = floatval($s['positive_pct']);
            $np = floatval($s['negative_pct']);
            $conn->query("DELETE FROM lm_bridge_sentiment WHERE ticker='$t'");
            $conn->query("INSERT INTO lm_bridge_sentiment
                (ticker,sentiment_score,sentiment_label,confidence,num_articles,positive_pct,negative_pct,updated_at)
                VALUES ('$t',$sc,'$lb',$cf,$na,$pp,$np,'$now')");
        }
    }

    if ($module === 'cusum_detector' && is_array($decoded)) {
        $health = isset($decoded['algo_health']) ? $decoded['algo_health'] : $decoded;
        foreach ($health as $h) {
            if (!isset($h['algorithm_name'])) continue;
            $a = $conn->real_escape_string($h['algorithm_name']);
            $ds = $conn->real_escape_string($h['decay_status']);
            $rw = floatval($h['recommended_weight']);
            $ls = floatval($h['last_segment_sharpe']);
            $lw = floatval($h['last_segment_wr']);
            $cp = intval($h['change_points_detected']);
            $tt = intval($h['total_trades']);
            $conn->query("DELETE FROM lm_bridge_cusum WHERE algorithm_name='$a'");
            $conn->query("INSERT INTO lm_bridge_cusum
                (algorithm_name,decay_status,recommended_weight,last_sharpe,last_win_rate,change_points,total_trades,updated_at)
                VALUES ('$a','$ds',$rw,$ls,$lw,$cp,$tt,'$now')");
        }
    }

    if ($module === 'congress_tracker' && is_array($decoded)) {
        $signals = isset($decoded['signals']) ? $decoded['signals'] : array();
        $conn->query("DELETE FROM lm_bridge_congress WHERE 1=1");
        foreach ($signals as $sig) {
            $t = $conn->real_escape_string($sig['ticker']);
            $st = $conn->real_escape_string($sig['signal_type']);
            $str = intval($sig['strength']);
            $mb = intval(isset($sig['members_buying']) ? $sig['members_buying'] : 0);
            $desc = $conn->real_escape_string($sig['description']);
            $conn->query("INSERT INTO lm_bridge_congress
                (ticker,signal_type,strength,members_buying,description,updated_at)
                VALUES ('$t','$st',$str,$mb,'$desc','$now')");
        }
    }

    if ($module === 'options_flow' && is_array($decoded)) {
        $opts = isset($decoded['options_data']) ? $decoded['options_data'] : $decoded;
        foreach ($opts as $o) {
            if (!isset($o['ticker'])) continue;
            $t = $conn->real_escape_string($o['ticker']);
            $sp = floatval($o['spot_price']);
            $ng = floatval($o['net_gex']);
            $gs = $conn->real_escape_string($o['gex_signal']);
            $pc = floatval($o['pc_oi_ratio']);
            $ps = $conn->real_escape_string($o['pcr_signal']);
            $uc = intval(count(isset($o['unusual_activity']) ? $o['unusual_activity'] : array()));
            $conn->query("DELETE FROM lm_bridge_options WHERE ticker='$t'");
            $conn->query("INSERT INTO lm_bridge_options
                (ticker,spot_price,net_gex,gex_signal,pc_oi_ratio,pcr_signal,unusual_count,updated_at)
                VALUES ('$t',$sp,$ng,'$gs',$pc,'$ps',$uc,'$now')");
        }
    }

    if ($module === 'onchain_analytics' && is_array($decoded)) {
        $btc = isset($decoded['btc_network']) ? $decoded['btc_network'] : array();
        foreach ($btc as $k => $v) {
            $mk = $conn->real_escape_string('btc_' . $k);
            $mv = floatval($v);
            $conn->query("DELETE FROM lm_bridge_onchain WHERE metric_name='$mk'");
            $conn->query("INSERT INTO lm_bridge_onchain (metric_name,metric_value,metric_label,updated_at) VALUES ('$mk',$mv,'','$now')");
        }
        $tvl = isset($decoded['defi_tvl']) ? $decoded['defi_tvl'] : array();
        foreach ($tvl as $k => $v) {
            $mk = $conn->real_escape_string('defi_' . $k);
            $mv = floatval($v);
            $conn->query("DELETE FROM lm_bridge_onchain WHERE metric_name='$mk'");
            $conn->query("INSERT INTO lm_bridge_onchain (metric_name,metric_value,metric_label,updated_at) VALUES ('$mk',$mv,'','$now')");
        }
    }

    if ($module === 'transfer_entropy' && is_array($decoded)) {
        $leaders = isset($decoded['leaders']) ? $decoded['leaders'] : array();
        foreach ($leaders as $l) {
            if (!isset($l['ticker'])) continue;
            $t = $conn->real_escape_string($l['ticker']);
            $r = $conn->real_escape_string($l['role']);
            $ot = floatval($l['outgoing_te']);
            $it = floatval($l['incoming_te']);
            $nt = floatval($l['net_te']);
            $conn->query("DELETE FROM lm_bridge_entropy WHERE ticker='$t'");
            $conn->query("INSERT INTO lm_bridge_entropy (ticker,role,outgoing_te,incoming_te,net_te,updated_at) VALUES ('$t','$r',$ot,$it,$nt,'$now')");
        }
    }

    echo json_encode(array('ok' => true, 'stored' => $module));
    exit;
}

// ════════════════════════════════════════════════════════════════════════
//  ACTION: dashboard — Full quant bridge dashboard data
// ════════════════════════════════════════════════════════════════════════
if ($action === 'dashboard') {
    $dashboard = array();

    // Latest run per module
    $r = $conn->query("SELECT module_name, status, summary, run_at
        FROM lm_quant_bridge
        WHERE id IN (SELECT MAX(id) FROM lm_quant_bridge GROUP BY module_name)
        ORDER BY run_at DESC");
    $runs = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) { $runs[] = $row; }
        $r->free();
    }
    $dashboard['latest_runs'] = $runs;

    // Sentiment
    $r = $conn->query("SELECT * FROM lm_bridge_sentiment ORDER BY ABS(sentiment_score) DESC");
    $sentiment = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) { $sentiment[] = $row; }
        $r->free();
    }
    $dashboard['sentiment'] = $sentiment;

    // CUSUM health
    $r = $conn->query("SELECT * FROM lm_bridge_cusum ORDER BY recommended_weight DESC");
    $cusum = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) { $cusum[] = $row; }
        $r->free();
    }
    $dashboard['cusum'] = $cusum;

    // Congress signals
    $r = $conn->query("SELECT * FROM lm_bridge_congress ORDER BY strength DESC LIMIT 30");
    $congress = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) { $congress[] = $row; }
        $r->free();
    }
    $dashboard['congress'] = $congress;

    // Options / GEX
    $r = $conn->query("SELECT * FROM lm_bridge_options ORDER BY ABS(net_gex) DESC");
    $options = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) { $options[] = $row; }
        $r->free();
    }
    $dashboard['options'] = $options;

    // On-chain
    $r = $conn->query("SELECT * FROM lm_bridge_onchain ORDER BY metric_name");
    $onchain = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) { $onchain[] = $row; }
        $r->free();
    }
    $dashboard['onchain'] = $onchain;

    // Entropy leaders
    $r = $conn->query("SELECT * FROM lm_bridge_entropy ORDER BY net_te DESC");
    $entropy = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) { $entropy[] = $row; }
        $r->free();
    }
    $dashboard['entropy'] = $entropy;

    echo json_encode(array('ok' => true, 'dashboard' => $dashboard));
    exit;
}

// ════════════════════════════════════════════════════════════════════════
//  ACTION: module — Get data for a specific module
// ════════════════════════════════════════════════════════════════════════
if ($action === 'module') {
    $module = isset($_GET['name']) ? $conn->real_escape_string($_GET['name']) : '';
    if (!$module) {
        echo json_encode(array('ok' => false, 'error' => 'name parameter required'));
        exit;
    }

    $r = $conn->query("SELECT * FROM lm_quant_bridge WHERE module_name='$module' ORDER BY run_at DESC LIMIT 5");
    $results = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $row['result_data'] = json_decode($row['result_data'], true);
            $results[] = $row;
        }
        $r->free();
    }

    echo json_encode(array('ok' => true, 'module' => $module, 'runs' => $results));
    exit;
}

// ════════════════════════════════════════════════════════════════════════
//  ACTION: latest_run — Latest run summary
// ════════════════════════════════════════════════════════════════════════
if ($action === 'latest_run') {
    $r = $conn->query("SELECT * FROM lm_quant_bridge ORDER BY run_at DESC LIMIT 1");
    $latest = null;
    if ($r && $r->num_rows > 0) {
        $latest = $r->fetch_assoc();
        $latest['result_data'] = json_decode($latest['result_data'], true);
        $r->free();
    }

    echo json_encode(array('ok' => true, 'latest' => $latest));
    exit;
}

// Default: list available actions
echo json_encode(array(
    'ok' => true,
    'api' => 'quant_bridge',
    'actions' => array('store_results', 'dashboard', 'module', 'latest_run'),
    'usage' => 'quant_bridge.php?action=dashboard'
));
