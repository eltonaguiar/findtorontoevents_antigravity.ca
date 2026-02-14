<?php
/**
 * AI Personal Prediction Tracker v1.0
 * Records personal AI predictions with entry price, TP, SL, thesis.
 * Auto-resolves by checking live Kraken prices.
 *
 * Actions:
 *   predict       — Record a new AI prediction (requires key)
 *   monitor       — Check all open predictions against live prices, auto-resolve
 *   history       — All AI predictions with outcomes
 *   stats         — Win/loss/pending stats for AI predictions
 *   seed_batch    — Seed multiple AI predictions at once (requires key)
 *   reset         — Clear all AI predictions (requires key)
 *
 * PHP 5.2 compatible.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit;
}

error_reporting(0);
ini_set('display_errors', '0');

$API_KEY = 'ai_predict2026';

$conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'Database connection failed'));
    exit;
}
$conn->set_charset('utf8');

// Ensure table exists for AI predictions
$conn->query("CREATE TABLE IF NOT EXISTS ai_personal_predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    batch_id VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    kraken_pair VARCHAR(30) NOT NULL,
    direction VARCHAR(10) NOT NULL DEFAULT 'LONG',
    entry_price DECIMAL(20,10) NOT NULL,
    current_price DECIMAL(20,10) DEFAULT NULL,
    tp_price DECIMAL(20,10) NOT NULL,
    sl_price DECIMAL(20,10) NOT NULL,
    tp_pct DECIMAL(8,4) NOT NULL,
    sl_pct DECIMAL(8,4) NOT NULL,
    confidence VARCHAR(20) NOT NULL,
    thesis TEXT NOT NULL,
    timeframe VARCHAR(20) NOT NULL DEFAULT '24h',
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    pnl_pct DECIMAL(8,4) DEFAULT NULL,
    peak_pnl_pct DECIMAL(8,4) DEFAULT NULL,
    trough_pnl_pct DECIMAL(8,4) DEFAULT NULL,
    exit_price DECIMAL(20,10) DEFAULT NULL,
    exit_reason VARCHAR(50) DEFAULT NULL,
    checks_count INT DEFAULT 0,
    last_check DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL,
    resolved_at DATETIME DEFAULT NULL,
    ai_model VARCHAR(50) DEFAULT 'Grok',
    prediction_type VARCHAR(20) DEFAULT 'PERSONAL',
    INDEX idx_status (status),
    INDEX idx_batch (batch_id),
    INDEX idx_symbol (symbol),
    INDEX idx_created (created_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$action = isset($_GET['action']) ? $_GET['action'] : 'monitor';

switch ($action) {
    case 'predict':
        _require_key();
        _record_prediction($conn);
        break;
    case 'seed_batch':
        _require_key();
        _seed_batch($conn);
        break;
    case 'monitor':
        _monitor_predictions($conn);
        break;
    case 'history':
        _prediction_history($conn);
        break;
    case 'stats':
        _prediction_stats($conn);
        break;
    case 'reset':
        _require_key();
        _reset_predictions($conn);
        break;
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

$conn->close();

// ═══════════════════════════════════════════════════════════════════════
//  Auth helper
// ═══════════════════════════════════════════════════════════════════════
function _require_key()
{
    global $API_KEY;
    $key = isset($_GET['key']) ? $_GET['key'] : (isset($_POST['key']) ? $_POST['key'] : '');
    if ($key !== $API_KEY) {
        echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
        exit;
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  Record a single prediction
// ═══════════════════════════════════════════════════════════════════════
function _record_prediction($conn)
{
    $symbol     = isset($_GET['symbol']) ? strtoupper(trim($_GET['symbol'])) : '';
    $pair       = isset($_GET['pair']) ? strtoupper(trim($_GET['pair'])) : '';
    $direction  = isset($_GET['direction']) ? strtoupper(trim($_GET['direction'])) : 'LONG';
    $entry      = isset($_GET['entry']) ? floatval($_GET['entry']) : 0;
    $tp_pct     = isset($_GET['tp_pct']) ? floatval($_GET['tp_pct']) : 6;
    $sl_pct     = isset($_GET['sl_pct']) ? floatval($_GET['sl_pct']) : 3;
    $confidence = isset($_GET['confidence']) ? $_GET['confidence'] : 'MEDIUM';
    $thesis     = isset($_GET['thesis']) ? $_GET['thesis'] : '';
    $timeframe  = isset($_GET['timeframe']) ? $_GET['timeframe'] : '24h';
    $batch_id   = isset($_GET['batch_id']) ? $_GET['batch_id'] : date('Y-m-d_H');
    $ai_model   = isset($_GET['ai_model']) ? $_GET['ai_model'] : 'Grok';

    if ($symbol === '' || $entry <= 0) {
        echo json_encode(array('ok' => false, 'error' => 'symbol and entry price required'));
        return;
    }

    // If no pair specified, try common Kraken pair names
    if ($pair === '') {
        $pair = $symbol . 'USD';
    }

    $tp_price = $direction === 'LONG'
        ? $entry * (1 + $tp_pct / 100)
        : $entry * (1 - $tp_pct / 100);

    $sl_price = $direction === 'LONG'
        ? $entry * (1 - $sl_pct / 100)
        : $entry * (1 + $sl_pct / 100);

    $sql = sprintf(
        "INSERT INTO ai_personal_predictions (batch_id, symbol, kraken_pair, direction, entry_price, tp_price, sl_price, tp_pct, sl_pct, confidence, thesis, timeframe, status, created_at, ai_model)
         VALUES ('%s','%s','%s','%s','%.10f','%.10f','%.10f','%.4f','%.4f','%s','%s','%s','OPEN','%s','%s')",
        $conn->real_escape_string($batch_id),
        $conn->real_escape_string($symbol),
        $conn->real_escape_string($pair),
        $conn->real_escape_string($direction),
        $entry, $tp_price, $sl_price, $tp_pct, $sl_pct,
        $conn->real_escape_string($confidence),
        $conn->real_escape_string($thesis),
        $conn->real_escape_string($timeframe),
        date('Y-m-d H:i:s'),
        $conn->real_escape_string($ai_model)
    );

    if ($conn->query($sql)) {
        echo json_encode(array(
            'ok' => true,
            'prediction_id' => $conn->insert_id,
            'symbol' => $symbol,
            'entry' => $entry,
            'tp' => $tp_price,
            'sl' => $sl_price,
            'direction' => $direction,
            'confidence' => $confidence,
            'ai_model' => $ai_model,
            'message' => 'AI prediction recorded. Will auto-resolve when price hits TP or SL.'
        ));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'DB insert failed: ' . $conn->error));
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  Seed a batch of predictions at once (POST JSON body)
// ═══════════════════════════════════════════════════════════════════════
function _seed_batch($conn)
{
    // Accept GET params as JSON-encoded predictions array
    $json_str = isset($_GET['predictions']) ? $_GET['predictions'] : '';
    if ($json_str === '') {
        // Try POST body
        $json_str = file_get_contents('php://input');
    }

    $predictions = json_decode($json_str, true);
    if (!$predictions || !is_array($predictions)) {
        echo json_encode(array('ok' => false, 'error' => 'Invalid predictions JSON'));
        return;
    }

    $batch_id = isset($_GET['batch_id']) ? $_GET['batch_id'] : date('Y-m-d_H-i');
    $inserted = 0;
    $results = array();

    foreach ($predictions as $p) {
        $symbol    = isset($p['symbol']) ? strtoupper(trim($p['symbol'])) : '';
        $pair      = isset($p['pair']) ? strtoupper(trim($p['pair'])) : ($symbol . 'USD');
        $direction = isset($p['direction']) ? strtoupper($p['direction']) : 'LONG';
        $entry     = isset($p['entry']) ? floatval($p['entry']) : 0;
        $tp_pct    = isset($p['tp_pct']) ? floatval($p['tp_pct']) : 6;
        $sl_pct    = isset($p['sl_pct']) ? floatval($p['sl_pct']) : 3;
        $confidence = isset($p['confidence']) ? $p['confidence'] : 'MEDIUM';
        $thesis    = isset($p['thesis']) ? $p['thesis'] : '';
        $timeframe = isset($p['timeframe']) ? $p['timeframe'] : '24h';
        $ai_model  = isset($p['ai_model']) ? $p['ai_model'] : 'Grok';

        if ($symbol === '' || $entry <= 0) {
            $results[] = array('symbol' => $symbol, 'ok' => false, 'error' => 'missing data');
            continue;
        }

        $tp_price = $direction === 'LONG'
            ? $entry * (1 + $tp_pct / 100)
            : $entry * (1 - $tp_pct / 100);
        $sl_price = $direction === 'LONG'
            ? $entry * (1 - $sl_pct / 100)
            : $entry * (1 + $sl_pct / 100);

        $sql = sprintf(
            "INSERT INTO ai_personal_predictions (batch_id, symbol, kraken_pair, direction, entry_price, tp_price, sl_price, tp_pct, sl_pct, confidence, thesis, timeframe, status, created_at, ai_model)
             VALUES ('%s','%s','%s','%s','%.10f','%.10f','%.10f','%.4f','%.4f','%s','%s','%s','OPEN','%s','%s')",
            $conn->real_escape_string($batch_id),
            $conn->real_escape_string($symbol),
            $conn->real_escape_string($pair),
            $conn->real_escape_string($direction),
            $entry, $tp_price, $sl_price, $tp_pct, $sl_pct,
            $conn->real_escape_string($confidence),
            $conn->real_escape_string($thesis),
            $conn->real_escape_string($timeframe),
            date('Y-m-d H:i:s'),
            $conn->real_escape_string($ai_model)
        );

        if ($conn->query($sql)) {
            $inserted++;
            $results[] = array('symbol' => $symbol, 'ok' => true, 'id' => $conn->insert_id);
        } else {
            $results[] = array('symbol' => $symbol, 'ok' => false, 'error' => $conn->error);
        }
    }

    echo json_encode(array(
        'ok' => true,
        'batch_id' => $batch_id,
        'total' => count($predictions),
        'inserted' => $inserted,
        'results' => $results
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  Monitor: check live Kraken prices for all OPEN predictions
// ═══════════════════════════════════════════════════════════════════════
function _monitor_predictions($conn)
{
    $start = microtime(true);

    // Get all open predictions
    $res = $conn->query("SELECT * FROM ai_personal_predictions WHERE status = 'OPEN' ORDER BY created_at DESC");
    if (!$res || $res->num_rows === 0) {
        // Also fetch recently resolved
        $recent = $conn->query("SELECT * FROM ai_personal_predictions ORDER BY created_at DESC LIMIT 20");
        $all = array();
        if ($recent) {
            while ($r = $recent->fetch_assoc()) {
                $all[] = $r;
            }
        }
        echo json_encode(array(
            'ok' => true,
            'open_count' => 0,
            'message' => 'No open AI predictions to monitor',
            'recent' => $all
        ));
        return;
    }

    // Collect unique Kraken pairs
    $pairs_map = array(); // kraken_pair => array of prediction rows
    $open = array();
    while ($row = $res->fetch_assoc()) {
        $open[] = $row;
        $kp = $row['kraken_pair'];
        if (!isset($pairs_map[$kp])) {
            $pairs_map[$kp] = array();
        }
        $pairs_map[$kp][] = $row;
    }

    // Fetch live prices from Kraken in one batch call
    $pair_list = implode(',', array_keys($pairs_map));
    $live_prices = _fetch_kraken_batch($pair_list);

    $just_resolved = array();
    $still_open = array();
    $now = date('Y-m-d H:i:s');

    foreach ($open as $pred) {
        $kp = $pred['kraken_pair'];
        $live = isset($live_prices[$kp]) ? $live_prices[$kp] : null;

        if (!$live) {
            // Try alternate pair naming
            $alt = str_replace('USD', 'USDT', $kp);
            $live = isset($live_prices[$alt]) ? $live_prices[$alt] : null;
        }

        if (!$live) {
            $pred['live_price'] = null;
            $pred['live_pnl_pct'] = null;
            $pred['status_note'] = 'Could not fetch price';
            $still_open[] = $pred;
            continue;
        }

        $current = floatval($live['price']);
        $entry = floatval($pred['entry_price']);
        $tp = floatval($pred['tp_price']);
        $sl = floatval($pred['sl_price']);
        $direction = $pred['direction'];

        // Calculate current P&L
        if ($direction === 'LONG') {
            $pnl_pct = (($current - $entry) / $entry) * 100;
        } else {
            $pnl_pct = (($entry - $current) / $entry) * 100;
        }

        // Track peak/trough
        $peak = floatval($pred['peak_pnl_pct']);
        $trough = floatval($pred['trough_pnl_pct']);
        if ($pnl_pct > $peak) $peak = $pnl_pct;
        if ($pnl_pct < $trough) $trough = $pnl_pct;

        $checks = intval($pred['checks_count']) + 1;

        // Check if TP or SL hit
        $resolved = false;
        $exit_reason = '';

        if ($direction === 'LONG') {
            if ($current >= $tp) {
                $resolved = true;
                $exit_reason = 'TP_HIT';
            } else if ($current <= $sl) {
                $resolved = true;
                $exit_reason = 'SL_HIT';
            }
        } else {
            if ($current <= $tp) {
                $resolved = true;
                $exit_reason = 'TP_HIT';
            } else if ($current >= $sl) {
                $resolved = true;
                $exit_reason = 'SL_HIT';
            }
        }

        // Check for time expiry (48h max for any prediction)
        $created = strtotime($pred['created_at']);
        $hours_open = (time() - $created) / 3600;
        if (!$resolved && $hours_open >= 48) {
            $resolved = true;
            $exit_reason = 'EXPIRED_48H';
        }

        if ($resolved) {
            // Update DB
            $conn->query(sprintf(
                "UPDATE ai_personal_predictions SET status='RESOLVED', current_price='%.10f', pnl_pct='%.4f',
                 peak_pnl_pct='%.4f', trough_pnl_pct='%.4f', exit_price='%.10f', exit_reason='%s',
                 checks_count=%d, last_check='%s', resolved_at='%s' WHERE id=%d",
                $current, $pnl_pct, $peak, $trough, $current,
                $conn->real_escape_string($exit_reason), $checks, $now, $now, intval($pred['id'])
            ));

            $pred['status'] = 'RESOLVED';
            $pred['exit_reason'] = $exit_reason;
            $pred['exit_price'] = $current;
            $pred['pnl_pct'] = round($pnl_pct, 4);
            $pred['live_price'] = $current;
            $pred['hours_open'] = round($hours_open, 1);
            $just_resolved[] = $pred;
        } else {
            // Update tracking fields
            $conn->query(sprintf(
                "UPDATE ai_personal_predictions SET current_price='%.10f', pnl_pct='%.4f',
                 peak_pnl_pct='%.4f', trough_pnl_pct='%.4f',
                 checks_count=%d, last_check='%s' WHERE id=%d",
                $current, $pnl_pct, $peak, $trough, $checks, $now, intval($pred['id'])
            ));

            $pred['live_price'] = $current;
            $pred['live_pnl_pct'] = round($pnl_pct, 2);
            $pred['peak_pnl_pct'] = round($peak, 2);
            $pred['trough_pnl_pct'] = round($trough, 2);
            $pred['hours_open'] = round($hours_open, 1);
            $pred['checks_count'] = $checks;

            // Calculate distance to TP and SL
            if ($direction === 'LONG') {
                $pred['dist_to_tp_pct'] = round((($tp - $current) / $current) * 100, 2);
                $pred['dist_to_sl_pct'] = round((($current - $sl) / $current) * 100, 2);
            } else {
                $pred['dist_to_tp_pct'] = round((($current - $tp) / $current) * 100, 2);
                $pred['dist_to_sl_pct'] = round((($sl - $current) / $current) * 100, 2);
            }

            $still_open[] = $pred;
        }
    }

    // Also get recently resolved for context
    $recent_resolved = array();
    $rr = $conn->query("SELECT * FROM ai_personal_predictions WHERE status = 'RESOLVED' ORDER BY resolved_at DESC LIMIT 10");
    if ($rr) {
        while ($row = $rr->fetch_assoc()) {
            $recent_resolved[] = $row;
        }
    }

    $elapsed = round((microtime(true) - $start) * 1000, 1);

    echo json_encode(array(
        'ok' => true,
        'timestamp' => date('Y-m-d H:i:s T'),
        'latency_ms' => $elapsed,
        'open_count' => count($still_open),
        'just_resolved_count' => count($just_resolved),
        'open_predictions' => $still_open,
        'just_resolved' => $just_resolved,
        'recent_resolved' => $recent_resolved
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  History: all predictions
// ═══════════════════════════════════════════════════════════════════════
function _prediction_history($conn)
{
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 50;
    $batch = isset($_GET['batch_id']) ? $conn->real_escape_string($_GET['batch_id']) : '';

    $where = '';
    if ($batch !== '') {
        $where = " WHERE batch_id = '" . $batch . "'";
    }

    $res = $conn->query("SELECT * FROM ai_personal_predictions" . $where . " ORDER BY created_at DESC LIMIT " . $limit);
    $rows = array();
    if ($res) {
        while ($r = $res->fetch_assoc()) {
            $rows[] = $r;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'total' => count($rows),
        'predictions' => $rows
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  Stats: overall accuracy
// ═══════════════════════════════════════════════════════════════════════
function _prediction_stats($conn)
{
    $total_res = $conn->query("SELECT
        COUNT(*) as total,
        SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as open_count,
        SUM(CASE WHEN status = 'RESOLVED' THEN 1 ELSE 0 END) as resolved_count,
        SUM(CASE WHEN exit_reason = 'TP_HIT' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN exit_reason = 'SL_HIT' THEN 1 ELSE 0 END) as losses,
        SUM(CASE WHEN exit_reason = 'EXPIRED_48H' THEN 1 ELSE 0 END) as expired,
        AVG(CASE WHEN status = 'RESOLVED' THEN pnl_pct ELSE NULL END) as avg_pnl,
        MAX(CASE WHEN status = 'RESOLVED' THEN pnl_pct ELSE NULL END) as best_trade,
        MIN(CASE WHEN status = 'RESOLVED' THEN pnl_pct ELSE NULL END) as worst_trade,
        AVG(CASE WHEN status = 'OPEN' THEN pnl_pct ELSE NULL END) as avg_open_pnl
    FROM ai_personal_predictions");
    $stats = $total_res->fetch_assoc();

    $resolved = intval($stats['resolved_count']);
    $wins = intval($stats['wins']);
    $win_rate = $resolved > 0 ? round(($wins / $resolved) * 100, 1) : 0;

    // Per-confidence breakdown
    $conf_res = $conn->query("SELECT confidence,
        COUNT(*) as total,
        SUM(CASE WHEN exit_reason = 'TP_HIT' THEN 1 ELSE 0 END) as wins,
        AVG(CASE WHEN status = 'RESOLVED' THEN pnl_pct ELSE NULL END) as avg_pnl
    FROM ai_personal_predictions GROUP BY confidence");
    $by_confidence = array();
    if ($conf_res) {
        while ($r = $conf_res->fetch_assoc()) {
            $r['win_rate'] = intval($r['total']) > 0 ? round((intval($r['wins']) / intval($r['total'])) * 100, 1) : 0;
            $by_confidence[] = $r;
        }
    }

    // Per-batch breakdown
    $batch_res = $conn->query("SELECT batch_id,
        COUNT(*) as total,
        SUM(CASE WHEN exit_reason = 'TP_HIT' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN exit_reason = 'SL_HIT' THEN 1 ELSE 0 END) as losses,
        SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as still_open,
        AVG(CASE WHEN status = 'RESOLVED' THEN pnl_pct ELSE NULL END) as avg_pnl,
        MIN(created_at) as batch_time
    FROM ai_personal_predictions GROUP BY batch_id ORDER BY batch_time DESC LIMIT 20");
    $by_batch = array();
    if ($batch_res) {
        while ($r = $batch_res->fetch_assoc()) {
            $resolved_in_batch = intval($r['wins']) + intval($r['losses']);
            $r['win_rate'] = $resolved_in_batch > 0 ? round((intval($r['wins']) / $resolved_in_batch) * 100, 1) : 0;
            $by_batch[] = $r;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'overall' => array(
            'total_predictions' => intval($stats['total']),
            'open' => intval($stats['open_count']),
            'resolved' => $resolved,
            'wins' => $wins,
            'losses' => intval($stats['losses']),
            'expired' => intval($stats['expired']),
            'win_rate' => $win_rate,
            'avg_pnl' => $stats['avg_pnl'] !== null ? round(floatval($stats['avg_pnl']), 4) : null,
            'best_trade' => $stats['best_trade'],
            'worst_trade' => $stats['worst_trade'],
            'avg_open_pnl' => $stats['avg_open_pnl'] !== null ? round(floatval($stats['avg_open_pnl']), 4) : null
        ),
        'by_confidence' => $by_confidence,
        'by_batch' => $by_batch
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  Reset all predictions
// ═══════════════════════════════════════════════════════════════════════
function _reset_predictions($conn)
{
    $conn->query("DELETE FROM ai_personal_predictions");
    echo json_encode(array('ok' => true, 'message' => 'All AI predictions cleared'));
}

// ═══════════════════════════════════════════════════════════════════════
//  Kraken batch price fetch
// ═══════════════════════════════════════════════════════════════════════
function _fetch_kraken_batch($pair_list)
{
    $url = 'https://api.kraken.com/0/public/Ticker?pair=' . $pair_list;
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'PredictionTracker/1.0');

    $resp = curl_exec($ch);
    curl_close($ch);

    if (!$resp) return array();

    $data = json_decode($resp, true);
    if (!$data || isset($data['error']) && !empty($data['error'])) return array();

    $prices = array();
    if (isset($data['result'])) {
        foreach ($data['result'] as $pair_key => $ticker) {
            $last_price = floatval($ticker['c'][0]); // Last trade price
            $high = floatval($ticker['h'][1]);        // 24h high
            $low = floatval($ticker['l'][1]);         // 24h low
            $vol = floatval($ticker['v'][1]);         // 24h volume

            $prices[$pair_key] = array(
                'price' => $last_price,
                'high_24h' => $high,
                'low_24h' => $low,
                'volume_24h' => $vol,
                'bid' => floatval($ticker['b'][0]),
                'ask' => floatval($ticker['a'][0])
            );
        }
    }

    return $prices;
}
?>