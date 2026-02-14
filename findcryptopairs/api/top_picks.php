<?php
/**
 * Top Picks Engine v1.0  —  Multi-Engine Consensus with Forward-Test Tracking
 *
 * Aggregates signals from:  Hybrid v2.0 | Custom Model | Spike Detector
 * Grades every opportunity:  S+ / S / A / B / C / WAIT
 * Forward-tests every pick with live Kraken prices.
 *
 * Actions:
 *   scan    — Poll all engines, generate consensus picks  (~20s, cron/manual)
 *   picks   — Latest picks from DB cache                  (fast, <100ms)
 *   resolve — Check open picks vs live Kraken prices      (~5s)
 *   history — All historical picks with outcomes           (fast)
 *   stats   — Win rate, P&L, Sharpe, streaks              (fast)
 *
 * PHP 5.2 compatible.  No ?:, no ??, array() only, no closures.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

error_reporting(0);
ini_set('display_errors', '0');

$API_KEY = 'toppicks2026';

$conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'DB connection failed'));
    exit;
}
$conn->set_charset('utf8');

// ═══════════════════════════════════════════════════════════════════════
//  Ensure tables
// ═══════════════════════════════════════════════════════════════════════
$conn->query("CREATE TABLE IF NOT EXISTS tp_picks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pick_date DATE NOT NULL,
    asset VARCHAR(10) NOT NULL,
    direction VARCHAR(10) NOT NULL DEFAULT 'LONG',
    entry_price DECIMAL(20,8) NOT NULL,
    tp_price DECIMAL(20,8) NOT NULL,
    sl_price DECIMAL(20,8) NOT NULL,
    tp_pct DECIMAL(8,2) NOT NULL,
    sl_pct DECIMAL(8,2) NOT NULL,
    grade VARCHAR(5) NOT NULL,
    consensus_score INT NOT NULL DEFAULT 0,
    engines_agree INT NOT NULL DEFAULT 0,
    engines_total INT NOT NULL DEFAULT 0,
    hybrid_signal VARCHAR(10) DEFAULT 'WAIT',
    hybrid_conf DECIMAL(8,4) DEFAULT 0,
    hybrid_regime VARCHAR(30) DEFAULT '',
    hybrid_detail TEXT,
    custom_signal VARCHAR(10) DEFAULT 'WAIT',
    custom_score INT DEFAULT 0,
    generic_signal VARCHAR(10) DEFAULT 'WAIT',
    generic_score INT DEFAULT 0,
    spike_signal VARCHAR(10) DEFAULT 'WAIT',
    spike_detail TEXT,
    thesis TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    current_price DECIMAL(20,8) DEFAULT NULL,
    pnl_pct DECIMAL(8,4) DEFAULT NULL,
    peak_pnl DECIMAL(8,4) DEFAULT NULL,
    trough_pnl DECIMAL(8,4) DEFAULT NULL,
    pnl_7d DECIMAL(8,4) DEFAULT NULL,
    pnl_14d DECIMAL(8,4) DEFAULT NULL,
    pnl_30d DECIMAL(8,4) DEFAULT NULL,
    exit_reason VARCHAR(50) DEFAULT NULL,
    exit_price DECIMAL(20,8) DEFAULT NULL,
    checks INT DEFAULT 0,
    resolved_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL,
    INDEX idx_status (status),
    INDEX idx_date (pick_date),
    INDEX idx_asset (asset),
    INDEX idx_grade (grade)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ═══════════════════════════════════════════════════════════════════════
//  Router
// ═══════════════════════════════════════════════════════════════════════
$action = isset($_GET['action']) ? $_GET['action'] : 'picks';

switch ($action) {
    case 'scan':
        _require_key();
        _scan($conn);
        break;
    case 'picks':
        _picks($conn);
        break;
    case 'resolve':
        _resolve($conn);
        break;
    case 'history':
        _history($conn);
        break;
    case 'stats':
        _stats($conn);
        break;
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}
$conn->close();

// ═══════════════════════════════════════════════════════════════════════
//  Auth
// ═══════════════════════════════════════════════════════════════════════
function _require_key()
{
    global $API_KEY;
    $k = isset($_GET['key']) ? $_GET['key'] : '';
    if ($k === '') { $k = isset($_POST['key']) ? $_POST['key'] : ''; }
    if ($k !== $API_KEY) {
        echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
        exit;
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  SCAN — Poll all engines, score consensus, store picks
// ═══════════════════════════════════════════════════════════════════════
function _scan($conn)
{
    $start = microtime(true);
    $base  = 'https://findtorontoevents.ca/findcryptopairs/api/';

    // Parallel fetch from all 3 engines + derivatives feed
    $urls = array(
        'hybrid' => $base . 'hybrid_predictor.php?action=predict_all',
        'model'  => $base . 'prediction_model.php?action=predict_all',
        'spike'  => $base . 'spike_detector.php?action=scan',
        'deriv'  => $base . 'derivatives_feed.php?action=all'
    );
    $raw = _parallel_fetch($urls);

    $hybrid = (isset($raw['hybrid']) && isset($raw['hybrid']['ok']) && $raw['hybrid']['ok']) ? $raw['hybrid'] : null;
    $model  = (isset($raw['model'])  && isset($raw['model']['ok'])  && $raw['model']['ok'])  ? $raw['model']  : null;
    $spike  = (isset($raw['spike'])  && isset($raw['spike']['ok'])  && $raw['spike']['ok'])  ? $raw['spike']  : null;
    $deriv  = (isset($raw['deriv'])  && isset($raw['deriv']['ok'])  && $raw['deriv']['ok'])  ? $raw['deriv']  : null;

    $engines_online = 0;
    if ($hybrid) $engines_online++;
    if ($model)  $engines_online++;
    if ($spike)  $engines_online++;

    if ($engines_online === 0) {
        echo json_encode(array('ok' => false, 'error' => 'All engines offline', 'latency_ms' => round((microtime(true) - $start) * 1000)));
        return;
    }

    $today  = date('Y-m-d');
    $assets = array('BTC', 'ETH', 'AVAX');
    $picks  = array();

    foreach ($assets as $asset) {
        $engines_buy   = 0;
        $engines_total = 0;
        $h_signal = 'OFFLINE'; $h_conf = 0; $h_regime = ''; $h_detail = '';
        $c_signal = 'OFFLINE'; $c_score = 0;
        $g_signal = 'OFFLINE'; $g_score = 0;
        $s_signal = 'OFFLINE'; $s_detail = '';
        $price    = 0;

        // --- Hybrid Engine ---
        if ($hybrid && isset($hybrid['predictions'][$asset])) {
            $h = $hybrid['predictions'][$asset];
            $engines_total++;
            $h_signal = isset($h['hybrid_signal']) ? $h['hybrid_signal'] : 'WAIT';
            $h_conf   = isset($h['confidence']) ? floatval($h['confidence']) : 0;
            $h_regime = isset($h['regime']) ? $h['regime'] : '';
            $h_detail = isset($h['signals_detail']) ? implode(', ', $h['signals_detail']) : '';
            if ($h_signal === 'BUY') $engines_buy++;
            if (isset($h['price']) && floatval($h['price']) > 0) $price = floatval($h['price']);
        }

        // --- Custom Model ---
        if ($model && isset($model['predictions'][$asset])) {
            $m = $model['predictions'][$asset];
            $engines_total++;
            $c_signal = isset($m['customized_signal']) ? $m['customized_signal'] : 'WAIT';
            $c_score  = isset($m['customized_score']) ? intval($m['customized_score']) : 0;
            $g_signal = isset($m['generic_signal']) ? $m['generic_signal'] : 'WAIT';
            $g_score  = isset($m['generic_score']) ? intval($m['generic_score']) : 0;
            if ($c_signal === 'BUY') $engines_buy++;
            if ($price <= 0 && isset($m['price']) && floatval($m['price']) > 0) $price = floatval($m['price']);
        }

        // --- Spike Detector (BTC/ETH only) ---
        if ($spike && isset($spike['results'][$asset])) {
            $s = $spike['results'][$asset];
            $engines_total++;
            $sv = isset($s['verdict']) ? $s['verdict'] : 'WAIT';
            $s_signal = $sv;
            $s_detail = isset($s['active_signals']) ? implode(', ', $s['active_signals']) : '';
            if ($sv !== 'WAIT') $engines_buy++;
            if ($price <= 0 && isset($s['price']) && floatval($s['price']) > 0) $price = floatval($s['price']);
        }

        if ($price <= 0) continue; // skip if no price

        // --- Derivatives Risk Filter (Kimi Swarm Layer 4) ---
        $deriv_score = 0;         // -100..+100
        $deriv_assessment = 'NEUTRAL';
        $deriv_supertrend = 'UNKNOWN';
        $deriv_warnings = array();
        $deriv_factors  = array();

        if ($deriv) {
            // Risk score
            if (isset($deriv['risk_scores'][$asset]) && !isset($deriv['risk_scores'][$asset]['error'])) {
                $rs = $deriv['risk_scores'][$asset];
                $deriv_score      = intval($rs['risk_score']);
                $deriv_assessment = $rs['assessment'];
                if (isset($rs['warnings'])) $deriv_warnings = $rs['warnings'];
                if (isset($rs['factors']))  $deriv_factors  = $rs['factors'];
            }
            // Supertrend
            if (isset($deriv['supertrend'][$asset]) && !isset($deriv['supertrend'][$asset]['error'])) {
                $deriv_supertrend = $deriv['supertrend'][$asset]['signal'];
            }
        }

        // --- Grade Calculation (enhanced with derivatives) ---
        $favorable_regime = ($h_regime === 'TRENDING_UP' || $h_regime === 'TRENDING_UP_STRONG');
        $ratio = ($engines_total > 0) ? ($engines_buy / $engines_total) : 0;
        $deriv_bullish = ($deriv_score >= 20);
        $deriv_bearish = ($deriv_score <= -30);
        $supertrend_confirms = ($deriv_supertrend === 'BULLISH');

        $grade = 'WAIT';
        if ($ratio >= 1.0 && $h_conf >= 0.7 && $favorable_regime && $supertrend_confirms) {
            $grade = 'S+';
        } elseif ($ratio >= 1.0 && $h_conf >= 0.7 && $favorable_regime) {
            $grade = 'S+';
        } elseif ($ratio >= 1.0 && $h_conf >= 0.5 && !$deriv_bearish) {
            $grade = 'S';
        } elseif ($ratio >= 1.0) {
            $grade = ($deriv_bearish) ? 'A' : 'S'; // downgrade if derivatives bearish
        } elseif ($engines_buy >= 2 && $supertrend_confirms) {
            $grade = 'A';
        } elseif ($engines_buy >= 2) {
            $grade = ($deriv_bearish) ? 'B' : 'A';
        } elseif ($engines_buy >= 1 && ($favorable_regime || $h_conf >= 0.6) && !$deriv_bearish) {
            $grade = 'B';
        } elseif ($engines_buy >= 1 && !$deriv_bearish) {
            $grade = 'C';
        } elseif ($engines_buy >= 1 && $deriv_bearish) {
            $grade = 'WAIT'; // derivatives veto: too risky
        }

        // --- TP / SL based on grade ---
        $tp_pct = 8.0;
        $sl_pct = 5.0;
        if ($grade === 'S+' || $grade === 'S') { $tp_pct = 10.0; $sl_pct = 5.0; }
        elseif ($grade === 'A')                 { $tp_pct = 8.0;  $sl_pct = 5.0; }
        elseif ($grade === 'B')                 { $tp_pct = 6.0;  $sl_pct = 4.0; }
        elseif ($grade === 'C')                 { $tp_pct = 5.0;  $sl_pct = 3.5; }

        $tp_price = $price * (1 + $tp_pct / 100);
        $sl_price = $price * (1 - $sl_pct / 100);

        // --- Generate Thesis ---
        $parts = array();
        if ($h_signal !== 'OFFLINE') {
            $ht = 'Hybrid v2.0: ' . $h_signal;
            if ($h_signal === 'BUY' && $h_detail !== '') $ht .= ' (' . $h_detail . ', conf ' . round($h_conf, 2) . ')';
            if ($h_regime !== '') $ht .= ' [' . $h_regime . ']';
            $parts[] = $ht;
        }
        if ($c_signal !== 'OFFLINE') {
            $parts[] = 'Custom Model: ' . $c_signal . ' (score ' . $c_score . '/100)';
        }
        if ($g_signal !== 'OFFLINE') {
            $parts[] = 'Generic Model: ' . $g_signal . ' (score ' . $g_score . '/100)';
        }
        if ($s_signal !== 'OFFLINE') {
            $st = 'Spike Detector: ' . $s_signal;
            if ($s_detail !== '') $st .= ' (' . $s_detail . ')';
            $parts[] = $st;
        }
        // Derivatives layer
        if ($deriv_supertrend !== 'UNKNOWN') {
            $parts[] = 'Supertrend: ' . $deriv_supertrend;
        }
        if ($deriv_assessment !== 'NEUTRAL') {
            $parts[] = 'Derivatives Risk: ' . $deriv_assessment . ' (score ' . $deriv_score . ')';
        }
        if (count($deriv_warnings) > 0) {
            $parts[] = 'WARNINGS: ' . implode('; ', $deriv_warnings);
        }
        $parts[] = $engines_buy . '/' . $engines_total . ' engines agree = ' . ($grade === 'WAIT' ? 'NO TRADE' : $grade . ' GRADE PICK');
        $thesis = implode('. ', $parts) . '.';

        // --- Prevent duplicate pick for same asset+date ---
        $dup = $conn->query(sprintf(
            "SELECT id FROM tp_picks WHERE pick_date='%s' AND asset='%s' LIMIT 1",
            $conn->real_escape_string($today),
            $conn->real_escape_string($asset)
        ));
        if ($dup && $dup->num_rows > 0) {
            // Update existing pick
            $row = $dup->fetch_assoc();
            $conn->query(sprintf(
                "UPDATE tp_picks SET grade='%s', consensus_score=%d, engines_agree=%d, engines_total=%d,
                 hybrid_signal='%s', hybrid_conf='%.4f', hybrid_regime='%s', hybrid_detail='%s',
                 custom_signal='%s', custom_score=%d, generic_signal='%s', generic_score=%d,
                 spike_signal='%s', spike_detail='%s', thesis='%s',
                 entry_price='%.8f', tp_price='%.8f', sl_price='%.8f', tp_pct='%.2f', sl_pct='%.2f'
                 WHERE id=%d",
                $conn->real_escape_string($grade), $engines_buy, $engines_buy, $engines_total,
                $conn->real_escape_string($h_signal), $h_conf, $conn->real_escape_string($h_regime),
                $conn->real_escape_string($h_detail),
                $conn->real_escape_string($c_signal), $c_score,
                $conn->real_escape_string($g_signal), $g_score,
                $conn->real_escape_string($s_signal), $conn->real_escape_string($s_detail),
                $conn->real_escape_string($thesis),
                $price, $tp_price, $sl_price, $tp_pct, $sl_pct,
                intval($row['id'])
            ));
            $pick_id = intval($row['id']);
        } else {
            // Insert new pick
            $conn->query(sprintf(
                "INSERT INTO tp_picks (pick_date,asset,direction,entry_price,tp_price,sl_price,tp_pct,sl_pct,
                 grade,consensus_score,engines_agree,engines_total,
                 hybrid_signal,hybrid_conf,hybrid_regime,hybrid_detail,
                 custom_signal,custom_score,generic_signal,generic_score,
                 spike_signal,spike_detail,thesis,status,created_at)
                 VALUES('%s','%s','LONG','%.8f','%.8f','%.8f','%.2f','%.2f',
                 '%s',%d,%d,%d,
                 '%s','%.4f','%s','%s',
                 '%s',%d,'%s',%d,
                 '%s','%s','%s','%s','%s')",
                $today, $conn->real_escape_string($asset), $price, $tp_price, $sl_price, $tp_pct, $sl_pct,
                $conn->real_escape_string($grade), $engines_buy, $engines_buy, $engines_total,
                $conn->real_escape_string($h_signal), $h_conf, $conn->real_escape_string($h_regime),
                $conn->real_escape_string($h_detail),
                $conn->real_escape_string($c_signal), $c_score,
                $conn->real_escape_string($g_signal), $g_score,
                $conn->real_escape_string($s_signal), $conn->real_escape_string($s_detail),
                $conn->real_escape_string($thesis),
                ($grade === 'WAIT') ? 'NO_TRADE' : 'OPEN',
                date('Y-m-d H:i:s')
            ));
            $pick_id = $conn->insert_id;
        }

        $picks[] = array(
            'id'             => $pick_id,
            'asset'          => $asset,
            'price'          => $price,
            'grade'          => $grade,
            'direction'      => 'LONG',
            'entry_price'    => $price,
            'tp_price'       => round($tp_price, 8),
            'sl_price'       => round($sl_price, 8),
            'tp_pct'         => $tp_pct,
            'sl_pct'         => $sl_pct,
            'engines_agree'  => $engines_buy,
            'engines_total'  => $engines_total,
            'hybrid_signal'  => $h_signal,
            'hybrid_conf'    => round($h_conf, 4),
            'hybrid_regime'  => $h_regime,
            'hybrid_detail'  => $h_detail,
            'custom_signal'  => $c_signal,
            'custom_score'   => $c_score,
            'generic_signal' => $g_signal,
            'generic_score'  => $g_score,
            'spike_signal'   => $s_signal,
            'spike_detail'   => $s_detail,
            'thesis'         => $thesis,
            'status'         => ($grade === 'WAIT') ? 'NO_TRADE' : 'OPEN'
        );
    }

    $elapsed = round((microtime(true) - $start) * 1000);

    echo json_encode(array(
        'ok'             => true,
        'scan_date'      => $today,
        'engines_online' => $engines_online,
        'latency_ms'     => $elapsed,
        'picks'          => $picks,
        'engine_status'  => array(
            'hybrid' => ($hybrid) ? 'ONLINE' : 'OFFLINE',
            'model'  => ($model)  ? 'ONLINE' : 'OFFLINE',
            'spike'  => ($spike)  ? 'ONLINE' : 'OFFLINE',
            'derivatives' => ($deriv) ? 'ONLINE' : 'OFFLINE'
        ),
        'derivatives'    => ($deriv) ? array(
            'risk_scores' => isset($deriv['risk_scores']) ? $deriv['risk_scores'] : null,
            'supertrend'  => isset($deriv['supertrend'])  ? $deriv['supertrend']  : null
        ) : null
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  PICKS — Latest picks from DB (fast)
// ═══════════════════════════════════════════════════════════════════════
function _picks($conn)
{
    $days = isset($_GET['days']) ? intval($_GET['days']) : 7;
    if ($days < 1) $days = 1;
    if ($days > 90) $days = 90;

    $cutoff = date('Y-m-d', strtotime('-' . $days . ' days'));
    $res = $conn->query(sprintf(
        "SELECT * FROM tp_picks WHERE pick_date >= '%s' ORDER BY pick_date DESC, grade ASC",
        $conn->real_escape_string($cutoff)
    ));

    $picks = array();
    if ($res) {
        while ($r = $res->fetch_assoc()) {
            $picks[] = $r;
        }
    }

    // Get latest scan date
    $latest = $conn->query("SELECT MAX(pick_date) as d FROM tp_picks");
    $last_scan = '';
    if ($latest) {
        $lr = $latest->fetch_assoc();
        $last_scan = ($lr && $lr['d']) ? $lr['d'] : '';
    }

    echo json_encode(array(
        'ok'         => true,
        'last_scan'  => $last_scan,
        'days'       => $days,
        'total'      => count($picks),
        'picks'      => $picks
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  RESOLVE — Check open picks vs live Kraken prices
// ═══════════════════════════════════════════════════════════════════════
function _resolve($conn)
{
    $start = microtime(true);

    $res = $conn->query("SELECT * FROM tp_picks WHERE status = 'OPEN' ORDER BY created_at ASC");
    if (!$res || $res->num_rows === 0) {
        echo json_encode(array('ok' => true, 'message' => 'No open picks to resolve', 'resolved' => 0));
        return;
    }

    $open = array();
    $pairs_needed = array();
    while ($row = $res->fetch_assoc()) {
        $open[] = $row;
        $a = $row['asset'];
        if ($a === 'BTC')  $pairs_needed['XXBTZUSD'] = 'BTC';
        if ($a === 'ETH')  $pairs_needed['XETHZUSD'] = 'ETH';
        if ($a === 'AVAX') $pairs_needed['AVAXUSD']  = 'AVAX';
    }

    // Fetch live prices
    $pair_str = implode(',', array_keys($pairs_needed));
    $prices = _fetch_kraken_ticker($pair_str);

    // Map to asset names
    $live = array();
    foreach ($prices as $k => $v) {
        if (isset($pairs_needed[$k])) {
            $live[$pairs_needed[$k]] = floatval($v);
        }
    }

    $now = date('Y-m-d H:i:s');
    $resolved_list = array();
    $updated_list  = array();

    foreach ($open as $pick) {
        $asset = $pick['asset'];
        if (!isset($live[$asset])) continue;

        $current   = $live[$asset];
        $entry     = floatval($pick['entry_price']);
        $tp        = floatval($pick['tp_price']);
        $sl        = floatval($pick['sl_price']);
        $pnl       = (($current - $entry) / $entry) * 100;
        $peak      = max(floatval($pick['peak_pnl']), $pnl);
        $trough    = min(floatval($pick['trough_pnl']), $pnl);
        $checks    = intval($pick['checks']) + 1;
        $created   = strtotime($pick['created_at']);
        $days_open = (time() - $created) / 86400;

        // Track milestone returns
        $pnl_7d  = $pick['pnl_7d'];
        $pnl_14d = $pick['pnl_14d'];
        $pnl_30d = $pick['pnl_30d'];
        if ($days_open >= 7  && ($pnl_7d  === null || $pnl_7d  === '')) $pnl_7d  = $pnl;
        if ($days_open >= 14 && ($pnl_14d === null || $pnl_14d === '')) $pnl_14d = $pnl;
        if ($days_open >= 30 && ($pnl_30d === null || $pnl_30d === '')) $pnl_30d = $pnl;

        // Check TP / SL / Expiry
        $resolved = false;
        $exit_reason = '';

        if ($current >= $tp) {
            $resolved = true;
            $exit_reason = 'TP_HIT';
        } elseif ($current <= $sl) {
            $resolved = true;
            $exit_reason = 'SL_HIT';
        } elseif ($days_open >= 30) {
            $resolved = true;
            $exit_reason = 'EXPIRED_30D';
            if ($pnl_30d === null || $pnl_30d === '') $pnl_30d = $pnl;
        }

        if ($resolved) {
            $conn->query(sprintf(
                "UPDATE tp_picks SET status='%s', current_price='%.8f', pnl_pct='%.4f',
                 peak_pnl='%.4f', trough_pnl='%.4f', exit_price='%.8f', exit_reason='%s',
                 pnl_7d=%s, pnl_14d=%s, pnl_30d=%s, checks=%d, resolved_at='%s' WHERE id=%d",
                ($exit_reason === 'TP_HIT') ? 'WIN' : (($exit_reason === 'SL_HIT') ? 'LOSS' : 'EXPIRED'),
                $current, $pnl, $peak, $trough, $current,
                $conn->real_escape_string($exit_reason),
                ($pnl_7d !== null && $pnl_7d !== '') ? sprintf("'%.4f'", $pnl_7d) : 'NULL',
                ($pnl_14d !== null && $pnl_14d !== '') ? sprintf("'%.4f'", $pnl_14d) : 'NULL',
                ($pnl_30d !== null && $pnl_30d !== '') ? sprintf("'%.4f'", $pnl_30d) : 'NULL',
                $checks, $now, intval($pick['id'])
            ));
            $pick['status']      = ($exit_reason === 'TP_HIT') ? 'WIN' : (($exit_reason === 'SL_HIT') ? 'LOSS' : 'EXPIRED');
            $pick['exit_reason'] = $exit_reason;
            $pick['exit_price']  = $current;
            $pick['pnl_pct']     = round($pnl, 4);
            $resolved_list[] = $pick;
        } else {
            $conn->query(sprintf(
                "UPDATE tp_picks SET current_price='%.8f', pnl_pct='%.4f',
                 peak_pnl='%.4f', trough_pnl='%.4f',
                 pnl_7d=%s, pnl_14d=%s, pnl_30d=%s, checks=%d WHERE id=%d",
                $current, $pnl, $peak, $trough,
                ($pnl_7d !== null && $pnl_7d !== '') ? sprintf("'%.4f'", $pnl_7d) : 'NULL',
                ($pnl_14d !== null && $pnl_14d !== '') ? sprintf("'%.4f'", $pnl_14d) : 'NULL',
                ($pnl_30d !== null && $pnl_30d !== '') ? sprintf("'%.4f'", $pnl_30d) : 'NULL',
                $checks, intval($pick['id'])
            ));
            $pick['current_price'] = $current;
            $pick['pnl_pct']       = round($pnl, 4);
            $pick['peak_pnl']      = round($peak, 4);
            $pick['trough_pnl']    = round($trough, 4);
            $pick['days_open']     = round($days_open, 1);
            $updated_list[] = $pick;
        }
    }

    echo json_encode(array(
        'ok'       => true,
        'latency_ms' => round((microtime(true) - $start) * 1000),
        'live_prices' => $live,
        'just_resolved' => $resolved_list,
        'still_open'    => $updated_list
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  HISTORY — All picks
// ═══════════════════════════════════════════════════════════════════════
function _history($conn)
{
    $limit  = isset($_GET['limit']) ? intval($_GET['limit']) : 100;
    $asset  = isset($_GET['asset']) ? strtoupper(trim($_GET['asset'])) : '';
    $grade  = isset($_GET['grade']) ? strtoupper(trim($_GET['grade'])) : '';
    $status = isset($_GET['status']) ? strtoupper(trim($_GET['status'])) : '';

    $where = array();
    if ($asset !== '')  $where[] = "asset = '" . $conn->real_escape_string($asset) . "'";
    if ($grade !== '')  $where[] = "grade = '" . $conn->real_escape_string($grade) . "'";
    if ($status !== '') $where[] = "status = '" . $conn->real_escape_string($status) . "'";

    $sql = "SELECT * FROM tp_picks";
    if (count($where) > 0) $sql .= " WHERE " . implode(' AND ', $where);
    $sql .= " ORDER BY pick_date DESC, asset ASC LIMIT " . $limit;

    $res  = $conn->query($sql);
    $rows = array();
    if ($res) { while ($r = $res->fetch_assoc()) { $rows[] = $r; } }

    echo json_encode(array('ok' => true, 'total' => count($rows), 'picks' => $rows));
}

// ═══════════════════════════════════════════════════════════════════════
//  STATS — Performance analytics
// ═══════════════════════════════════════════════════════════════════════
function _stats($conn)
{
    // Overall
    $res = $conn->query("SELECT
        COUNT(*) as total,
        SUM(CASE WHEN status='OPEN' THEN 1 ELSE 0 END) as open_ct,
        SUM(CASE WHEN status='NO_TRADE' THEN 1 ELSE 0 END) as no_trade_ct,
        SUM(CASE WHEN status='WIN' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN status='LOSS' THEN 1 ELSE 0 END) as losses,
        SUM(CASE WHEN status='EXPIRED' THEN 1 ELSE 0 END) as expired,
        AVG(CASE WHEN status IN ('WIN','LOSS','EXPIRED') THEN pnl_pct ELSE NULL END) as avg_pnl,
        MAX(CASE WHEN status IN ('WIN','LOSS','EXPIRED') THEN pnl_pct ELSE NULL END) as best,
        MIN(CASE WHEN status IN ('WIN','LOSS','EXPIRED') THEN pnl_pct ELSE NULL END) as worst,
        SUM(CASE WHEN status IN ('WIN','LOSS','EXPIRED') THEN pnl_pct ELSE 0 END) as total_pnl,
        AVG(CASE WHEN pnl_30d IS NOT NULL THEN pnl_30d ELSE NULL END) as avg_30d,
        SUM(CASE WHEN pnl_30d > 0 THEN 1 ELSE 0 END) as dir_correct_30d,
        SUM(CASE WHEN pnl_30d IS NOT NULL THEN 1 ELSE 0 END) as dir_total_30d
    FROM tp_picks WHERE grade != 'WAIT'");

    $s = $res->fetch_assoc();
    $resolved = intval($s['wins']) + intval($s['losses']) + intval($s['expired']);
    $win_rate = ($resolved > 0) ? round((intval($s['wins']) / $resolved) * 100, 1) : 0;
    $dir_accuracy = (intval($s['dir_total_30d']) > 0) ? round((intval($s['dir_correct_30d']) / intval($s['dir_total_30d'])) * 100, 1) : 0;

    // Sharpe approximation (annualized, using resolved pick P&Ls)
    $pnl_res = $conn->query("SELECT pnl_pct FROM tp_picks WHERE status IN ('WIN','LOSS','EXPIRED') AND grade != 'WAIT' ORDER BY resolved_at ASC");
    $pnls = array();
    if ($pnl_res) { while ($r = $pnl_res->fetch_assoc()) { $pnls[] = floatval($r['pnl_pct']); } }
    $sharpe = 0;
    if (count($pnls) >= 3) {
        $mean = array_sum($pnls) / count($pnls);
        $variance = 0;
        foreach ($pnls as $p) { $variance += ($p - $mean) * ($p - $mean); }
        $std = sqrt($variance / count($pnls));
        if ($std > 0) $sharpe = round(($mean / $std) * sqrt(12), 2); // monthly annualized
    }

    // Streak (consecutive wins)
    $streak_res = $conn->query("SELECT status FROM tp_picks WHERE status IN ('WIN','LOSS') AND grade != 'WAIT' ORDER BY resolved_at DESC LIMIT 20");
    $streak = 0;
    $streak_type = '';
    if ($streak_res) {
        $first = true;
        while ($r = $streak_res->fetch_assoc()) {
            if ($first) { $streak_type = $r['status']; $streak = 1; $first = false; }
            elseif ($r['status'] === $streak_type) { $streak++; }
            else { break; }
        }
    }

    // By grade
    $grade_res = $conn->query("SELECT grade,
        COUNT(*) as total,
        SUM(CASE WHEN status='WIN' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN status='LOSS' THEN 1 ELSE 0 END) as losses,
        AVG(CASE WHEN status IN ('WIN','LOSS','EXPIRED') THEN pnl_pct ELSE NULL END) as avg_pnl
    FROM tp_picks WHERE grade != 'WAIT' GROUP BY grade ORDER BY grade ASC");
    $by_grade = array();
    if ($grade_res) {
        while ($r = $grade_res->fetch_assoc()) {
            $gr = intval($r['wins']) + intval($r['losses']);
            $r['win_rate'] = ($gr > 0) ? round((intval($r['wins']) / $gr) * 100, 1) : 0;
            $by_grade[] = $r;
        }
    }

    // By asset
    $asset_res = $conn->query("SELECT asset,
        COUNT(*) as total,
        SUM(CASE WHEN status='WIN' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN status='LOSS' THEN 1 ELSE 0 END) as losses,
        AVG(CASE WHEN status IN ('WIN','LOSS','EXPIRED') THEN pnl_pct ELSE NULL END) as avg_pnl
    FROM tp_picks WHERE grade != 'WAIT' GROUP BY asset ORDER BY asset ASC");
    $by_asset = array();
    if ($asset_res) {
        while ($r = $asset_res->fetch_assoc()) {
            $gr = intval($r['wins']) + intval($r['losses']);
            $r['win_rate'] = ($gr > 0) ? round((intval($r['wins']) / $gr) * 100, 1) : 0;
            $by_asset[] = $r;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'overall' => array(
            'total_picks'   => intval($s['total']),
            'open'          => intval($s['open_ct']),
            'no_trade_days' => intval($s['no_trade_ct']),
            'resolved'      => $resolved,
            'wins'          => intval($s['wins']),
            'losses'        => intval($s['losses']),
            'expired'       => intval($s['expired']),
            'win_rate'      => $win_rate,
            'dir_accuracy_30d' => $dir_accuracy,
            'avg_pnl'       => ($s['avg_pnl'] !== null) ? round(floatval($s['avg_pnl']), 2) : null,
            'total_pnl'     => round(floatval($s['total_pnl']), 2),
            'best_trade'    => ($s['best'] !== null) ? round(floatval($s['best']), 2) : null,
            'worst_trade'   => ($s['worst'] !== null) ? round(floatval($s['worst']), 2) : null,
            'avg_30d_return' => ($s['avg_30d'] !== null) ? round(floatval($s['avg_30d']), 2) : null,
            'sharpe'        => $sharpe,
            'streak'        => $streak,
            'streak_type'   => $streak_type
        ),
        'by_grade' => $by_grade,
        'by_asset' => $by_asset
    ));
}

// ═══════════════════════════════════════════════════════════════════════
//  Parallel cURL
// ═══════════════════════════════════════════════════════════════════════
function _parallel_fetch($urls)
{
    $mh = curl_multi_init();
    $handles = array();

    foreach ($urls as $key => $url) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 60);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_USERAGENT, 'TopPicksEngine/1.0');
        curl_multi_add_handle($mh, $ch);
        $handles[$key] = $ch;
    }

    $running = null;
    do {
        curl_multi_exec($mh, $running);
        curl_multi_select($mh, 0.5);
    } while ($running > 0);

    $results = array();
    foreach ($handles as $key => $ch) {
        $body = curl_multi_getcontent($ch);
        $results[$key] = ($body) ? json_decode($body, true) : null;
        curl_multi_remove_handle($mh, $ch);
        curl_close($ch);
    }
    curl_multi_close($mh);
    return $results;
}

// ═══════════════════════════════════════════════════════════════════════
//  Kraken ticker
// ═══════════════════════════════════════════════════════════════════════
function _fetch_kraken_ticker($pair_str)
{
    $url = 'https://api.kraken.com/0/public/Ticker?pair=' . $pair_str;
    $ch  = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'TopPicks/1.0');
    $resp = curl_exec($ch);
    curl_close($ch);
    if (!$resp) return array();
    $data = json_decode($resp, true);
    if (!$data || !isset($data['result'])) return array();
    $out = array();
    foreach ($data['result'] as $k => $v) {
        $out[$k] = $v['c'][0]; // last trade price
    }
    return $out;
}
?>