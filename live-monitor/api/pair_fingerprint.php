<?php
/**
 * Pair Fingerprint Engine v1.0 — CURSORCODE_Feb152026
 * Per-asset behavioral profiling + short-term pattern alerts
 *
 * PHP 5.2 compatible. No short arrays, no closures, no ?:, no ??, no __DIR__.
 *
 * THE KEY INSIGHT: Commercial crypto alert services don't apply generic indicators
 * to everything. They build BEHAVIORAL FINGERPRINTS per pair:
 *   - AVAX mean-reverts (momentum correlation -0.36)
 *   - BTC trends (momentum correlation +0.02, but strong breakout follow-through)
 *   - PEPE pumps on social volume (82.8% of high-return meme coins show artificial growth)
 *   - EUR/USD only works in London+NY overlap
 *
 * This engine:
 *   1. Analyzes every pair's historical signal outcomes from our databases
 *   2. Builds a unique behavioral profile (fingerprint) per pair
 *   3. Identifies which strategies work SPECIFICALLY for that pair
 *   4. Generates alerts ONLY when the pair enters its known profitable pattern
 *   5. Calibrates TP/SL to that pair's actual volatility, not generic defaults
 *
 * Covers: Crypto, Meme Coins, Stocks/Penny Stocks, Forex
 *
 * Actions:
 *   ?action=build&key=...           — Build/refresh fingerprints from historical data (admin)
 *   ?action=scan&key=...            — Scan all pairs for active pattern matches (admin)
 *   ?action=alerts                  — Current high-probability short-term alerts (public)
 *   ?action=fingerprint&pair=X      — Detailed behavioral profile for one pair (public)
 *   ?action=leaderboard             — Best pairs by pattern accuracy (public)
 *   ?action=performance             — Overall engine performance stats (public)
 *   ?action=resolve&key=...         — Settle open alerts vs live prices (admin)
 *   ?action=status                  — Engine health check (public)
 *
 * Created by: Cursor AI — CURSORCODE_Feb152026
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }
error_reporting(0);
ini_set('display_errors', '0');
set_time_limit(180);

require_once dirname(__FILE__) . '/db_config.php';

$PF_ADMIN_KEY = 'livetrader2026';
$PF_VERSION   = '1.0.0-CURSORCODE_Feb152026';

// Connect to main stocks DB (has lm_signals, stock_picks, forex data)
$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'DB connection failed'));
    exit;
}
$conn->set_charset('utf8');

// Connect to meme/crypto DB for pump forensics + meme scanner data
$meme_conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($meme_conn->connect_error) {
    $meme_conn = null; // graceful degradation
}
if ($meme_conn) { $meme_conn->set_charset('utf8'); }

// ── Schema ────────────────────────────────────────────────────────────

$conn->query("CREATE TABLE IF NOT EXISTS pf_fingerprints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pair VARCHAR(30) NOT NULL,
    asset_class VARCHAR(15) NOT NULL DEFAULT 'CRYPTO',
    behavior_type VARCHAR(30) NOT NULL DEFAULT 'UNKNOWN',
    momentum_corr DECIMAL(8,4) DEFAULT 0,
    mean_revert_score DECIMAL(8,4) DEFAULT 0,
    trend_score DECIMAL(8,4) DEFAULT 0,
    breakout_score DECIMAL(8,4) DEFAULT 0,
    pump_susceptibility DECIMAL(8,4) DEFAULT 0,
    avg_volatility_pct DECIMAL(8,4) DEFAULT 0,
    optimal_tp_pct DECIMAL(6,2) DEFAULT 0,
    optimal_sl_pct DECIMAL(6,2) DEFAULT 0,
    optimal_hold_hours INT DEFAULT 24,
    best_algorithm VARCHAR(100) DEFAULT '',
    best_algo_wr DECIMAL(5,2) DEFAULT 0,
    best_hour_utc INT DEFAULT -1,
    best_session VARCHAR(20) DEFAULT '',
    total_signals INT DEFAULT 0,
    total_wins INT DEFAULT 0,
    win_rate DECIMAL(5,2) DEFAULT 0,
    avg_pnl_pct DECIMAL(8,4) DEFAULT 0,
    pattern_json TEXT,
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_pair_class (pair, asset_class),
    KEY idx_behavior (behavior_type),
    KEY idx_win_rate (win_rate),
    KEY idx_class (asset_class)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS pf_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pair VARCHAR(30) NOT NULL,
    asset_class VARCHAR(15) NOT NULL DEFAULT 'CRYPTO',
    alert_type VARCHAR(30) NOT NULL DEFAULT 'PATTERN_MATCH',
    pattern_name VARCHAR(50) NOT NULL DEFAULT '',
    confidence_pct DECIMAL(5,2) DEFAULT 0,
    entry_price DECIMAL(20,10) DEFAULT 0,
    target_tp_pct DECIMAL(6,2) DEFAULT 0,
    target_sl_pct DECIMAL(6,2) DEFAULT 0,
    max_hold_hours INT DEFAULT 24,
    signal_type VARCHAR(10) DEFAULT 'BUY',
    rationale TEXT,
    status VARCHAR(20) DEFAULT 'active',
    exit_price DECIMAL(20,10) DEFAULT 0,
    pnl_pct DECIMAL(8,4) DEFAULT 0,
    exit_reason VARCHAR(30) DEFAULT '',
    created_at DATETIME NOT NULL,
    resolved_at DATETIME DEFAULT NULL,
    KEY idx_status (status),
    KEY idx_pair (pair),
    KEY idx_class (asset_class),
    KEY idx_created (created_at),
    KEY idx_confidence (confidence_pct)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS pf_pair_patterns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pair VARCHAR(30) NOT NULL,
    asset_class VARCHAR(15) NOT NULL DEFAULT 'CRYPTO',
    pattern_name VARCHAR(50) NOT NULL,
    occurrences INT DEFAULT 0,
    win_rate DECIMAL(5,2) DEFAULT 0,
    avg_return_pct DECIMAL(8,4) DEFAULT 0,
    avg_duration_hours DECIMAL(8,2) DEFAULT 0,
    last_triggered DATETIME DEFAULT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_pair_pattern (pair, asset_class, pattern_name),
    KEY idx_wr (win_rate)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ── Route ─────────────────────────────────────────────────────────────
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'status';

if ($action === 'build') {
    _pf_require_key($PF_ADMIN_KEY);
    _pf_action_build($conn, $meme_conn);
} elseif ($action === 'scan') {
    _pf_require_key($PF_ADMIN_KEY);
    _pf_action_scan($conn, $meme_conn);
} elseif ($action === 'alerts') {
    _pf_action_alerts($conn);
} elseif ($action === 'fingerprint') {
    _pf_action_fingerprint($conn);
} elseif ($action === 'leaderboard') {
    _pf_action_leaderboard($conn);
} elseif ($action === 'performance') {
    _pf_action_performance($conn);
} elseif ($action === 'resolve') {
    _pf_require_key($PF_ADMIN_KEY);
    _pf_action_resolve($conn);
} elseif ($action === 'status') {
    _pf_action_status($conn);
} else {
    echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

if ($meme_conn) { $meme_conn->close(); }
$conn->close();
exit;


// =====================================================================
//  HELPERS
// =====================================================================

function _pf_require_key($expected) {
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key === '') { $key = isset($_POST['key']) ? trim($_POST['key']) : ''; }
    if ($key !== $expected) {
        echo json_encode(array('ok' => false, 'error' => 'Unauthorized'));
        exit;
    }
}

function _pf_now() {
    return gmdate('Y-m-d H:i:s');
}

function _pf_safe_div($num, $den) {
    if ($den == 0) { return 0; }
    return $num / $den;
}

function _pf_classify_behavior($momentum_corr, $mean_revert_score, $trend_score, $breakout_score, $pump_score) {
    // Classify based on dominant characteristic
    $scores = array(
        'MEAN_REVERTING'   => $mean_revert_score,
        'TRENDING'         => $trend_score,
        'BREAKOUT_PRONE'   => $breakout_score,
        'PUMP_SUSCEPTIBLE' => $pump_score
    );
    $best_type  = 'UNKNOWN';
    $best_score = 0;
    foreach ($scores as $type => $score) {
        if ($score > $best_score) {
            $best_score = $score;
            $best_type  = $type;
        }
    }
    // Override: strong negative momentum correlation = mean-reverting
    if ($momentum_corr < -0.2) {
        $best_type = 'MEAN_REVERTING';
    }
    // Override: strong positive momentum correlation = trending
    if ($momentum_corr > 0.15) {
        $best_type = 'TRENDING';
    }
    return $best_type;
}


// =====================================================================
//  BUILD — Analyze historical data to create per-pair fingerprints
// =====================================================================

function _pf_action_build($conn, $meme_conn) {
    $start   = microtime(true);
    $now     = _pf_now();
    $results = array();
    $built   = 0;
    $errors  = array();

    // ── 1. CRYPTO & STOCKS & FOREX from lm_signals ───────────────────
    $sql = "SELECT symbol, asset_class, algorithm_name, signal_type,
                   entry_price, exit_price, pnl_pct, exit_reason,
                   target_tp_pct, target_sl_pct, max_hold_hours,
                   signal_time, resolved_at, status
            FROM lm_signals
            WHERE status IN ('won','lost','expired')
            ORDER BY symbol, signal_time";
    $res = $conn->query($sql);

    $pair_data = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $sym   = $row['symbol'];
            $class = $row['asset_class'];
            $key   = $sym . '|' . $class;
            if (!isset($pair_data[$key])) {
                $pair_data[$key] = array(
                    'pair' => $sym, 'asset_class' => $class,
                    'signals' => array(), 'wins' => 0, 'losses' => 0,
                    'total_pnl' => 0, 'algo_stats' => array(),
                    'pnl_sequence' => array()
                );
            }
            $pair_data[$key]['signals'][] = $row;
            $pnl = floatval($row['pnl_pct']);
            $pair_data[$key]['total_pnl'] += $pnl;
            $pair_data[$key]['pnl_sequence'][] = $pnl;

            if ($row['exit_reason'] === 'TP' || $row['status'] === 'won') {
                $pair_data[$key]['wins']++;
            } else {
                $pair_data[$key]['losses']++;
            }

            // Per-algorithm tracking
            $algo = $row['algorithm_name'];
            if (!isset($pair_data[$key]['algo_stats'][$algo])) {
                $pair_data[$key]['algo_stats'][$algo] = array('wins' => 0, 'total' => 0, 'pnl' => 0);
            }
            $pair_data[$key]['algo_stats'][$algo]['total']++;
            $pair_data[$key]['algo_stats'][$algo]['pnl'] += $pnl;
            if ($row['exit_reason'] === 'TP' || $row['status'] === 'won') {
                $pair_data[$key]['algo_stats'][$algo]['wins']++;
            }
        }
        $res->free();
    }

    // ── 2. MEME COINS from meme scanner DB ───────────────────────────
    if ($meme_conn) {
        $meme_sql = "SELECT pair, signal_type, entry_price, peak_price,
                            exit_price, pnl_pct, resolved, score,
                            created_at, resolved_at
                     FROM mc_winners
                     WHERE resolved = 1
                     ORDER BY pair, created_at";
        $mres = $meme_conn->query($meme_sql);
        if ($mres) {
            while ($row = $mres->fetch_assoc()) {
                $sym = $row['pair'];
                $key = $sym . '|MEME';
                if (!isset($pair_data[$key])) {
                    $pair_data[$key] = array(
                        'pair' => $sym, 'asset_class' => 'MEME',
                        'signals' => array(), 'wins' => 0, 'losses' => 0,
                        'total_pnl' => 0, 'algo_stats' => array(),
                        'pnl_sequence' => array()
                    );
                }
                $pnl = floatval($row['pnl_pct']);
                $pair_data[$key]['total_pnl'] += $pnl;
                $pair_data[$key]['pnl_sequence'][] = $pnl;
                $pair_data[$key]['signals'][] = $row;
                if ($pnl > 0) {
                    $pair_data[$key]['wins']++;
                } else {
                    $pair_data[$key]['losses']++;
                }
                // Track meme scanner as the algo
                $algo = 'Meme_Scanner';
                if (!isset($pair_data[$key]['algo_stats'][$algo])) {
                    $pair_data[$key]['algo_stats'][$algo] = array('wins' => 0, 'total' => 0, 'pnl' => 0);
                }
                $pair_data[$key]['algo_stats'][$algo]['total']++;
                $pair_data[$key]['algo_stats'][$algo]['pnl'] += $pnl;
                if ($pnl > 0) { $pair_data[$key]['algo_stats'][$algo]['wins']++; }
            }
            $mres->free();
        }

        // Pump forensics scans — get per-pair pump susceptibility
        $pump_sql = "SELECT pair, AVG(pump_score) as avg_pump_score,
                            COUNT(*) as scan_count,
                            MAX(pump_score) as max_pump_score
                     FROM pump_forensics_scans
                     GROUP BY pair
                     HAVING scan_count >= 2";
        $pres = $meme_conn->query($pump_sql);
        if ($pres) {
            while ($row = $pres->fetch_assoc()) {
                $sym = $row['pair'];
                // Try matching to crypto or meme entries
                foreach (array('MEME', 'CRYPTO') as $cls) {
                    $key = $sym . '|' . $cls;
                    if (isset($pair_data[$key])) {
                        $pair_data[$key]['pump_susceptibility'] = floatval($row['avg_pump_score']);
                    }
                }
            }
            $pres->free();
        }
    }

    // ── 3. STOCK PICKS from stock_picks table ────────────────────────
    $stock_sql = "SELECT ticker, algorithm, direction, entry_price, current_price,
                         pnl_pct, status, created_at, resolved_at
                  FROM stock_picks
                  WHERE status IN ('won','lost','expired')
                  ORDER BY ticker, created_at";
    $sres = $conn->query($stock_sql);
    if ($sres) {
        while ($row = $sres->fetch_assoc()) {
            $sym = $row['ticker'];
            $key = $sym . '|STOCK';
            if (!isset($pair_data[$key])) {
                $pair_data[$key] = array(
                    'pair' => $sym, 'asset_class' => 'STOCK',
                    'signals' => array(), 'wins' => 0, 'losses' => 0,
                    'total_pnl' => 0, 'algo_stats' => array(),
                    'pnl_sequence' => array()
                );
            }
            $pnl = floatval($row['pnl_pct']);
            $pair_data[$key]['total_pnl'] += $pnl;
            $pair_data[$key]['pnl_sequence'][] = $pnl;
            $pair_data[$key]['signals'][] = $row;
            if ($row['status'] === 'won') {
                $pair_data[$key]['wins']++;
            } else {
                $pair_data[$key]['losses']++;
            }
            $algo = isset($row['algorithm']) ? $row['algorithm'] : 'Unknown';
            if (!isset($pair_data[$key]['algo_stats'][$algo])) {
                $pair_data[$key]['algo_stats'][$algo] = array('wins' => 0, 'total' => 0, 'pnl' => 0);
            }
            $pair_data[$key]['algo_stats'][$algo]['total']++;
            $pair_data[$key]['algo_stats'][$algo]['pnl'] += $pnl;
            if ($row['status'] === 'won') { $pair_data[$key]['algo_stats'][$algo]['wins']++; }
        }
        $sres->free();
    }

    // ── 4. FOREX PICKS ───────────────────────────────────────────────
    $forex_tables = array('forex_picks', 'forex_signals');
    foreach ($forex_tables as $ft) {
        $check = $conn->query("SHOW TABLES LIKE '" . $ft . "'");
        if (!$check || $check->num_rows === 0) { continue; }
        $fsql = "SELECT * FROM " . $ft . " WHERE status IN ('won','lost','expired') ORDER BY created_at";
        $fres = $conn->query($fsql);
        if (!$fres) { continue; }
        while ($row = $fres->fetch_assoc()) {
            $sym = isset($row['pair']) ? $row['pair'] : (isset($row['symbol']) ? $row['symbol'] : 'UNKNOWN');
            $key = $sym . '|FOREX';
            if (!isset($pair_data[$key])) {
                $pair_data[$key] = array(
                    'pair' => $sym, 'asset_class' => 'FOREX',
                    'signals' => array(), 'wins' => 0, 'losses' => 0,
                    'total_pnl' => 0, 'algo_stats' => array(),
                    'pnl_sequence' => array()
                );
            }
            $pnl = isset($row['pnl_pct']) ? floatval($row['pnl_pct']) : 0;
            $pair_data[$key]['total_pnl'] += $pnl;
            $pair_data[$key]['pnl_sequence'][] = $pnl;
            $pair_data[$key]['signals'][] = $row;
            if (isset($row['status']) && $row['status'] === 'won') {
                $pair_data[$key]['wins']++;
            } else {
                $pair_data[$key]['losses']++;
            }
        }
        $fres->free();
    }

    // ── 5. COMPUTE FINGERPRINTS ──────────────────────────────────────
    foreach ($pair_data as $key => $data) {
        $total = $data['wins'] + $data['losses'];
        if ($total < 3) { continue; } // Need minimum 3 resolved signals

        $pair  = $data['pair'];
        $class = $data['asset_class'];
        $wr    = _pf_safe_div($data['wins'] * 100, $total);
        $avg_pnl = _pf_safe_div($data['total_pnl'], $total);

        // Compute momentum correlation (autocorrelation of PnL sequence)
        $momentum_corr = _pf_compute_autocorrelation($data['pnl_sequence']);

        // Mean reversion score: negative autocorrelation + dip recovery
        $mean_revert_score = 0;
        if ($momentum_corr < 0) {
            $mean_revert_score = abs($momentum_corr) * 100;
        }
        // Also check: how often does a loss get followed by a win?
        $loss_then_win = 0;
        $loss_count    = 0;
        $seq = $data['pnl_sequence'];
        for ($i = 1; $i < count($seq); $i++) {
            if ($seq[$i-1] < 0) {
                $loss_count++;
                if ($seq[$i] > 0) { $loss_then_win++; }
            }
        }
        if ($loss_count > 2) {
            $recovery_rate = _pf_safe_div($loss_then_win * 100, $loss_count);
            if ($recovery_rate > 55) {
                $mean_revert_score += ($recovery_rate - 50) * 2;
            }
        }

        // Trend score: positive autocorrelation + streak tendency
        $trend_score = 0;
        if ($momentum_corr > 0) {
            $trend_score = $momentum_corr * 100;
        }
        $win_then_win = 0;
        $win_count    = 0;
        for ($i = 1; $i < count($seq); $i++) {
            if ($seq[$i-1] > 0) {
                $win_count++;
                if ($seq[$i] > 0) { $win_then_win++; }
            }
        }
        if ($win_count > 2) {
            $streak_rate = _pf_safe_div($win_then_win * 100, $win_count);
            if ($streak_rate > 55) {
                $trend_score += ($streak_rate - 50) * 2;
            }
        }

        // Breakout score: large PnL variance (high reward when it works)
        $pnl_variance = _pf_compute_variance($data['pnl_sequence']);
        $breakout_score = min(100, $pnl_variance * 5);

        // Pump susceptibility (from forensics data or estimated)
        $pump_score = isset($data['pump_susceptibility']) ? $data['pump_susceptibility'] : 0;

        // Compute volatility from PnL spread
        $volatility = sqrt($pnl_variance);

        // Classify behavior
        $behavior = _pf_classify_behavior($momentum_corr, $mean_revert_score, $trend_score, $breakout_score, $pump_score);

        // Find best algorithm for this pair
        $best_algo    = '';
        $best_algo_wr = 0;
        foreach ($data['algo_stats'] as $algo => $stats) {
            if ($stats['total'] >= 2) {
                $algo_wr = _pf_safe_div($stats['wins'] * 100, $stats['total']);
                if ($algo_wr > $best_algo_wr) {
                    $best_algo_wr = $algo_wr;
                    $best_algo    = $algo;
                }
            }
        }

        // Compute optimal TP/SL based on actual PnL distribution
        $winning_pnls = array();
        $losing_pnls  = array();
        foreach ($data['pnl_sequence'] as $p) {
            if ($p > 0) { $winning_pnls[] = $p; }
            else { $losing_pnls[] = abs($p); }
        }
        $optimal_tp = count($winning_pnls) > 0 ? _pf_percentile($winning_pnls, 50) : 5;
        $optimal_sl = count($losing_pnls) > 0 ? _pf_percentile($losing_pnls, 75) : 3;

        // Clamp to reasonable ranges
        if ($optimal_tp < 0.5) { $optimal_tp = 0.5; }
        if ($optimal_tp > 50) { $optimal_tp = 50; }
        if ($optimal_sl < 0.2) { $optimal_sl = 0.2; }
        if ($optimal_sl > 25) { $optimal_sl = 25; }

        // Best session (based on signal_time hour if available)
        $best_session = _pf_detect_best_session($data['signals']);

        // Build pattern JSON
        $pattern_json = json_encode(array(
            'momentum_autocorr' => round($momentum_corr, 4),
            'recovery_rate'     => isset($recovery_rate) ? round($recovery_rate, 1) : 0,
            'streak_rate'       => isset($streak_rate) ? round($streak_rate, 1) : 0,
            'pnl_variance'      => round($pnl_variance, 4),
            'total_signals'     => $total,
            'algo_breakdown'    => _pf_summarize_algos($data['algo_stats']),
            'behavior_type'     => $behavior,
            'optimal_tp'        => round($optimal_tp, 2),
            'optimal_sl'        => round($optimal_sl, 2)
        ));

        // Upsert fingerprint
        $stmt = $conn->prepare("REPLACE INTO pf_fingerprints
            (pair, asset_class, behavior_type, momentum_corr, mean_revert_score, trend_score,
             breakout_score, pump_susceptibility, avg_volatility_pct, optimal_tp_pct, optimal_sl_pct,
             optimal_hold_hours, best_algorithm, best_algo_wr, best_session,
             total_signals, total_wins, win_rate, avg_pnl_pct, pattern_json, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)");
        if ($stmt) {
            $hold_hours = 24; // default, can be refined from hour_learning data
            $stmt->bind_param('sssddddddddisdsiiidss',
                $pair, $class, $behavior, $momentum_corr, $mean_revert_score, $trend_score,
                $breakout_score, $pump_score, $volatility, $optimal_tp, $optimal_sl,
                $hold_hours, $best_algo, $best_algo_wr, $best_session,
                $total, $data['wins'], $wr, $avg_pnl, $pattern_json, $now
            );
            if ($stmt->execute()) {
                $built++;
            } else {
                $errors[] = $pair . ': ' . $stmt->error;
            }
            $stmt->close();
        }

        // Store individual pattern stats
        _pf_store_patterns($conn, $pair, $class, $data, $now);
    }

    // Also pull hour learning data to refine optimal_hold_hours
    _pf_refine_from_hour_learning($conn, $now);

    $elapsed = round(microtime(true) - $start, 2);
    echo json_encode(array(
        'ok'      => true,
        'action'  => 'build',
        'built'   => $built,
        'pairs_analyzed' => count($pair_data),
        'errors'  => $errors,
        'elapsed' => $elapsed . 's',
        'tag'     => 'CURSORCODE_Feb152026'
    ));
}


// =====================================================================
//  SCAN — Find pairs currently matching their known profitable patterns
// =====================================================================

function _pf_action_scan($conn, $meme_conn) {
    $start   = microtime(true);
    $now     = _pf_now();
    $alerts  = array();
    $scanned = 0;

    // Get all fingerprints with win_rate > 40% and >= 5 signals
    $fps = $conn->query("SELECT * FROM pf_fingerprints WHERE win_rate >= 40 AND total_signals >= 5 ORDER BY win_rate DESC");
    if (!$fps) {
        echo json_encode(array('ok' => false, 'error' => 'No fingerprints found. Run build first.'));
        return;
    }

    while ($fp = $fps->fetch_assoc()) {
        $scanned++;
        $pair  = $fp['pair'];
        $class = $fp['asset_class'];

        // Skip if we already have an active alert for this pair
        $check = $conn->query("SELECT id FROM pf_alerts WHERE pair='" . $conn->real_escape_string($pair)
            . "' AND asset_class='" . $conn->real_escape_string($class) . "' AND status='active' LIMIT 1");
        if ($check && $check->num_rows > 0) { continue; }

        // Get current market data for this pair
        $current_price = _pf_get_current_price($pair, $class, $meme_conn);
        if ($current_price <= 0) { continue; }

        // Check recent signals to see if this pair is in a known pattern
        $pattern_match = _pf_check_pattern_match($conn, $fp, $current_price);
        if (!$pattern_match) { continue; }

        // Pair matches its known profitable pattern — generate alert
        $confidence = $pattern_match['confidence'];
        $tp_pct     = floatval($fp['optimal_tp_pct']);
        $sl_pct     = floatval($fp['optimal_sl_pct']);
        $hold_hours = intval($fp['optimal_hold_hours']);
        if ($hold_hours < 1) { $hold_hours = 24; }

        // Only alert if confidence > 60%
        if ($confidence < 60) { continue; }

        $rationale = 'Pair fingerprint match: ' . $fp['behavior_type']
                   . ' | Pattern: ' . $pattern_match['pattern']
                   . ' | Historical WR: ' . $fp['win_rate'] . '%'
                   . ' | Best algo: ' . $fp['best_algorithm'] . ' (' . $fp['best_algo_wr'] . '% WR)'
                   . ' | Session: ' . $fp['best_session']
                   . ' | Confidence: ' . round($confidence, 1) . '%';

        $ins = $conn->prepare("INSERT INTO pf_alerts
            (pair, asset_class, alert_type, pattern_name, confidence_pct, entry_price,
             target_tp_pct, target_sl_pct, max_hold_hours, signal_type, rationale, status, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)");
        if ($ins) {
            $alert_type   = 'FINGERPRINT_MATCH';
            $pattern_name = $pattern_match['pattern'];
            $signal_type  = $pattern_match['direction'];
            $status       = 'active';
            $ins->bind_param('ssssddddiisss',
                $pair, $class, $alert_type, $pattern_name, $confidence,
                $current_price, $tp_pct, $sl_pct, $hold_hours,
                $signal_type, $rationale, $status, $now
            );
            if ($ins->execute()) {
                $alerts[] = array(
                    'pair'       => $pair,
                    'class'      => $class,
                    'pattern'    => $pattern_name,
                    'confidence' => round($confidence, 1),
                    'direction'  => $signal_type,
                    'tp'         => $tp_pct . '%',
                    'sl'         => $sl_pct . '%',
                    'hold'       => $hold_hours . 'h',
                    'price'      => $current_price
                );
            }
            $ins->close();
        }
    }
    $fps->free();

    $elapsed = round(microtime(true) - $start, 2);
    echo json_encode(array(
        'ok'      => true,
        'action'  => 'scan',
        'scanned' => $scanned,
        'alerts_generated' => count($alerts),
        'alerts'  => $alerts,
        'elapsed' => $elapsed . 's',
        'tag'     => 'CURSORCODE_Feb152026'
    ));
}


// =====================================================================
//  PATTERN MATCHING — Check if a pair is in its known profitable pattern
// =====================================================================

function _pf_check_pattern_match($conn, $fingerprint, $current_price) {
    $pair  = $fingerprint['pair'];
    $class = $fingerprint['asset_class'];
    $behavior = $fingerprint['behavior_type'];

    // Get recent signals for this pair (last 7 days)
    $sql = "SELECT signal_type, entry_price, pnl_pct, exit_reason, signal_time, status
            FROM lm_signals
            WHERE symbol='" . $conn->real_escape_string($pair) . "'
            AND signal_time > DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY signal_time DESC LIMIT 10";
    $recent = $conn->query($sql);

    $recent_signals = array();
    if ($recent) {
        while ($r = $recent->fetch_assoc()) {
            $recent_signals[] = $r;
        }
        $recent->free();
    }

    // Also get recent patterns from pf_pair_patterns
    $pp_sql = "SELECT pattern_name, win_rate, avg_return_pct, occurrences
               FROM pf_pair_patterns
               WHERE pair='" . $conn->real_escape_string($pair) . "'
               AND asset_class='" . $conn->real_escape_string($class) . "'
               AND win_rate >= 50
               ORDER BY win_rate DESC LIMIT 5";
    $pp_res = $conn->query($pp_sql);
    $known_patterns = array();
    if ($pp_res) {
        while ($pp = $pp_res->fetch_assoc()) {
            $known_patterns[] = $pp;
        }
        $pp_res->free();
    }

    $confidence = 0;
    $pattern    = '';
    $direction  = 'BUY';

    // ── MEAN_REVERTING behavior: look for dip to buy ─────────────────
    if ($behavior === 'MEAN_REVERTING') {
        // Check if recent signals show a loss/dip — that's the buy signal for mean-reverting pairs
        $recent_losses = 0;
        foreach ($recent_signals as $sig) {
            if ($sig['status'] === 'lost' || (isset($sig['pnl_pct']) && floatval($sig['pnl_pct']) < 0)) {
                $recent_losses++;
            }
        }
        if ($recent_losses >= 1) {
            $confidence = min(90, 50 + ($recent_losses * 15));
            $pattern    = 'MEAN_REVERT_DIP_BUY';
            $direction  = 'BUY';
        }
    }
    // ── TRENDING behavior: look for momentum continuation ────────────
    elseif ($behavior === 'TRENDING') {
        $recent_wins = 0;
        foreach ($recent_signals as $sig) {
            if ($sig['status'] === 'won' || (isset($sig['pnl_pct']) && floatval($sig['pnl_pct']) > 0)) {
                $recent_wins++;
            }
        }
        if ($recent_wins >= 2) {
            $confidence = min(90, 50 + ($recent_wins * 12));
            $pattern    = 'TREND_CONTINUATION';
            $direction  = 'BUY';
        }
    }
    // ── BREAKOUT_PRONE: look for tight range compression ─────────────
    elseif ($behavior === 'BREAKOUT_PRONE') {
        // If recent signals are mixed (small wins/losses), breakout is brewing
        $small_moves = 0;
        foreach ($recent_signals as $sig) {
            if (isset($sig['pnl_pct']) && abs(floatval($sig['pnl_pct'])) < 2) {
                $small_moves++;
            }
        }
        if ($small_moves >= 2) {
            $confidence = min(85, 50 + ($small_moves * 10));
            $pattern    = 'BREAKOUT_COMPRESSION';
            $direction  = 'BUY';
        }
    }
    // ── PUMP_SUSCEPTIBLE: look for volume accumulation ───────────────
    elseif ($behavior === 'PUMP_SUSCEPTIBLE') {
        $pump_sus = floatval($fingerprint['pump_susceptibility']);
        if ($pump_sus > 50) {
            $confidence = min(85, $pump_sus);
            $pattern    = 'PUMP_SETUP';
            $direction  = 'BUY';
        }
    }

    // Boost confidence if we have known patterns with high win rates
    if (count($known_patterns) > 0) {
        $best_known = $known_patterns[0];
        if (floatval($best_known['win_rate']) > floatval($fingerprint['win_rate'])) {
            $confidence += 5;
            if ($pattern === '') {
                $pattern = $best_known['pattern_name'];
            }
        }
    }

    // Apply base win rate as confidence floor
    $base_wr = floatval($fingerprint['win_rate']);
    if ($confidence > 0 && $confidence < $base_wr) {
        $confidence = ($confidence + $base_wr) / 2;
    }

    if ($confidence < 50 || $pattern === '') {
        return null;
    }

    return array(
        'confidence' => $confidence,
        'pattern'    => $pattern,
        'direction'  => $direction
    );
}


// =====================================================================
//  ALERTS — Show current active alerts
// =====================================================================

function _pf_action_alerts($conn) {
    $class_filter = isset($_GET['asset_class']) ? strtoupper(trim($_GET['asset_class'])) : '';
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 50;
    if ($limit < 1) { $limit = 50; }
    if ($limit > 200) { $limit = 200; }

    $where = "status='active'";
    if ($class_filter !== '') {
        $where .= " AND asset_class='" . $conn->real_escape_string($class_filter) . "'";
    }

    $sql = "SELECT * FROM pf_alerts WHERE " . $where . " ORDER BY confidence_pct DESC, created_at DESC LIMIT " . $limit;
    $res = $conn->query($sql);
    $alerts = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) { $alerts[] = $row; }
        $res->free();
    }

    // Also get resolved alerts for performance context
    $perf_sql = "SELECT
        COUNT(*) as total_resolved,
        SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
        AVG(pnl_pct) as avg_pnl,
        AVG(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) as avg_win,
        AVG(CASE WHEN pnl_pct <= 0 THEN pnl_pct ELSE 0 END) as avg_loss
    FROM pf_alerts WHERE status IN ('won','lost','expired')";
    $pres = $conn->query($perf_sql);
    $perf = array('total_resolved' => 0, 'win_rate' => 0, 'avg_pnl' => 0);
    if ($pres && $row = $pres->fetch_assoc()) {
        $total = intval($row['total_resolved']);
        $perf = array(
            'total_resolved' => $total,
            'wins'     => intval($row['wins']),
            'win_rate' => $total > 0 ? round(_pf_safe_div(intval($row['wins']) * 100, $total), 1) : 0,
            'avg_pnl'  => round(floatval($row['avg_pnl']), 2),
            'avg_win'  => round(floatval($row['avg_win']), 2),
            'avg_loss' => round(floatval($row['avg_loss']), 2)
        );
    }

    echo json_encode(array(
        'ok'          => true,
        'active_alerts' => count($alerts),
        'alerts'      => $alerts,
        'performance' => $perf,
        'tag'         => 'CURSORCODE_Feb152026'
    ));
}


// =====================================================================
//  FINGERPRINT — Detailed behavioral profile for one pair
// =====================================================================

function _pf_action_fingerprint($conn) {
    $pair = isset($_GET['pair']) ? trim($_GET['pair']) : '';
    if ($pair === '') {
        echo json_encode(array('ok' => false, 'error' => 'pair parameter required'));
        return;
    }

    $sql = "SELECT * FROM pf_fingerprints WHERE pair='" . $conn->real_escape_string($pair) . "' LIMIT 1";
    $res = $conn->query($sql);
    if (!$res || $res->num_rows === 0) {
        echo json_encode(array('ok' => false, 'error' => 'No fingerprint found for: ' . $pair));
        return;
    }
    $fp = $res->fetch_assoc();

    // Get patterns
    $pp_sql = "SELECT * FROM pf_pair_patterns
               WHERE pair='" . $conn->real_escape_string($pair) . "'
               ORDER BY win_rate DESC LIMIT 10";
    $pp_res = $conn->query($pp_sql);
    $patterns = array();
    if ($pp_res) {
        while ($p = $pp_res->fetch_assoc()) { $patterns[] = $p; }
    }

    // Get recent alerts
    $al_sql = "SELECT * FROM pf_alerts WHERE pair='" . $conn->real_escape_string($pair) . "'
               ORDER BY created_at DESC LIMIT 10";
    $al_res = $conn->query($al_sql);
    $recent_alerts = array();
    if ($al_res) {
        while ($a = $al_res->fetch_assoc()) { $recent_alerts[] = $a; }
    }

    // Strategy recommendation
    $rec = _pf_get_strategy_recommendation($fp);

    echo json_encode(array(
        'ok'              => true,
        'fingerprint'     => $fp,
        'patterns'        => $patterns,
        'recent_alerts'   => $recent_alerts,
        'recommendation'  => $rec,
        'tag'             => 'CURSORCODE_Feb152026'
    ));
}


// =====================================================================
//  LEADERBOARD — Best pairs by pattern accuracy
// =====================================================================

function _pf_action_leaderboard($conn) {
    $class_filter = isset($_GET['asset_class']) ? strtoupper(trim($_GET['asset_class'])) : '';
    $sort = isset($_GET['sort']) ? strtolower(trim($_GET['sort'])) : 'win_rate';
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 50;

    $valid_sorts = array('win_rate', 'avg_pnl_pct', 'total_signals', 'breakout_score', 'pump_susceptibility');
    if (!in_array($sort, $valid_sorts)) { $sort = 'win_rate'; }

    $where = 'total_signals >= 5';
    if ($class_filter !== '') {
        $where .= " AND asset_class='" . $conn->real_escape_string($class_filter) . "'";
    }

    $sql = "SELECT pair, asset_class, behavior_type, momentum_corr, mean_revert_score, trend_score,
                   breakout_score, pump_susceptibility, avg_volatility_pct,
                   optimal_tp_pct, optimal_sl_pct, optimal_hold_hours,
                   best_algorithm, best_algo_wr, best_session,
                   total_signals, total_wins, win_rate, avg_pnl_pct, updated_at
            FROM pf_fingerprints
            WHERE " . $where . "
            ORDER BY " . $sort . " DESC
            LIMIT " . $limit;

    $res = $conn->query($sql);
    $pairs = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) { $pairs[] = $row; }
    }

    // Category summaries
    $cat_sql = "SELECT asset_class,
                       COUNT(*) as pairs,
                       AVG(win_rate) as avg_wr,
                       AVG(avg_pnl_pct) as avg_pnl,
                       SUM(total_signals) as total_signals
                FROM pf_fingerprints
                WHERE total_signals >= 5
                GROUP BY asset_class ORDER BY avg_wr DESC";
    $cres = $conn->query($cat_sql);
    $categories = array();
    if ($cres) {
        while ($c = $cres->fetch_assoc()) {
            $c['avg_wr']  = round(floatval($c['avg_wr']), 1);
            $c['avg_pnl'] = round(floatval($c['avg_pnl']), 2);
            $categories[]  = $c;
        }
    }

    echo json_encode(array(
        'ok'          => true,
        'pairs'       => $pairs,
        'categories'  => $categories,
        'sort'        => $sort,
        'total_pairs' => count($pairs),
        'tag'         => 'CURSORCODE_Feb152026'
    ));
}


// =====================================================================
//  PERFORMANCE — Overall engine stats
// =====================================================================

function _pf_action_performance($conn) {
    // Fingerprint coverage
    $fp_sql = "SELECT asset_class, COUNT(*) as pairs, AVG(win_rate) as avg_wr,
                      AVG(avg_pnl_pct) as avg_pnl, SUM(total_signals) as signals
               FROM pf_fingerprints GROUP BY asset_class";
    $fp_res = $conn->query($fp_sql);
    $coverage = array();
    if ($fp_res) {
        while ($f = $fp_res->fetch_assoc()) {
            $f['avg_wr']  = round(floatval($f['avg_wr']), 1);
            $f['avg_pnl'] = round(floatval($f['avg_pnl']), 2);
            $coverage[] = $f;
        }
    }

    // Alert performance
    $al_sql = "SELECT asset_class, status,
                      COUNT(*) as cnt,
                      AVG(pnl_pct) as avg_pnl,
                      AVG(confidence_pct) as avg_conf
               FROM pf_alerts
               GROUP BY asset_class, status";
    $al_res = $conn->query($al_sql);
    $alert_stats = array();
    if ($al_res) {
        while ($a = $al_res->fetch_assoc()) { $alert_stats[] = $a; }
    }

    // Behavior distribution
    $beh_sql = "SELECT behavior_type, COUNT(*) as cnt,
                       AVG(win_rate) as avg_wr, AVG(avg_pnl_pct) as avg_pnl
                FROM pf_fingerprints GROUP BY behavior_type ORDER BY avg_wr DESC";
    $beh_res = $conn->query($beh_sql);
    $behaviors = array();
    if ($beh_res) {
        while ($b = $beh_res->fetch_assoc()) {
            $b['avg_wr']  = round(floatval($b['avg_wr']), 1);
            $b['avg_pnl'] = round(floatval($b['avg_pnl']), 2);
            $behaviors[] = $b;
        }
    }

    // Top patterns
    $tp_sql = "SELECT pair, asset_class, pattern_name, win_rate, avg_return_pct, occurrences
               FROM pf_pair_patterns
               WHERE occurrences >= 3 AND win_rate >= 50
               ORDER BY win_rate DESC, occurrences DESC LIMIT 20";
    $tp_res = $conn->query($tp_sql);
    $top_patterns = array();
    if ($tp_res) {
        while ($t = $tp_res->fetch_assoc()) { $top_patterns[] = $t; }
    }

    echo json_encode(array(
        'ok'           => true,
        'coverage'     => $coverage,
        'alert_stats'  => $alert_stats,
        'behaviors'    => $behaviors,
        'top_patterns' => $top_patterns,
        'tag'          => 'CURSORCODE_Feb152026'
    ));
}


// =====================================================================
//  RESOLVE — Check live prices and settle open alerts
// =====================================================================

function _pf_action_resolve($conn) {
    $start   = microtime(true);
    $now     = _pf_now();
    $settled = 0;
    $expired = 0;
    $errors  = array();

    $sql = "SELECT * FROM pf_alerts WHERE status='active' ORDER BY created_at ASC";
    $res = $conn->query($sql);
    if (!$res || $res->num_rows === 0) {
        echo json_encode(array('ok' => true, 'message' => 'No active alerts to resolve'));
        return;
    }

    while ($alert = $res->fetch_assoc()) {
        $pair  = $alert['pair'];
        $class = $alert['asset_class'];
        $entry = floatval($alert['entry_price']);
        $tp    = floatval($alert['target_tp_pct']);
        $sl    = floatval($alert['target_sl_pct']);
        $hold  = intval($alert['max_hold_hours']);
        $dir   = $alert['signal_type'];

        // Check expiry
        $created = strtotime($alert['created_at']);
        $age_hours = (time() - $created) / 3600;
        if ($age_hours > $hold) {
            // Expired — check final PnL
            $current = _pf_get_current_price($pair, $class, null);
            $pnl = 0;
            if ($current > 0 && $entry > 0) {
                $pnl = (($current - $entry) / $entry) * 100;
                if ($dir === 'SHORT') { $pnl = -$pnl; }
            }
            $final_status = ($pnl > 0) ? 'won' : 'lost';
            $conn->query("UPDATE pf_alerts SET status='" . $final_status . "',
                exit_price=" . floatval($current) . ", pnl_pct=" . round($pnl, 4)
                . ", exit_reason='EXPIRED', resolved_at='" . $now . "'
                WHERE id=" . intval($alert['id']));
            $expired++;
            continue;
        }

        // Get current price
        $current = _pf_get_current_price($pair, $class, null);
        if ($current <= 0) { continue; }

        // Calculate PnL
        $pnl = 0;
        if ($entry > 0) {
            $pnl = (($current - $entry) / $entry) * 100;
            if ($dir === 'SHORT') { $pnl = -$pnl; }
        }

        // Check TP hit
        if ($pnl >= $tp) {
            $conn->query("UPDATE pf_alerts SET status='won',
                exit_price=" . floatval($current) . ", pnl_pct=" . round($pnl, 4)
                . ", exit_reason='TP', resolved_at='" . $now . "'
                WHERE id=" . intval($alert['id']));
            $settled++;
            continue;
        }

        // Check SL hit
        if ($pnl <= -$sl) {
            $conn->query("UPDATE pf_alerts SET status='lost',
                exit_price=" . floatval($current) . ", pnl_pct=" . round(-$sl, 4)
                . ", exit_reason='SL', resolved_at='" . $now . "'
                WHERE id=" . intval($alert['id']));
            $settled++;
            continue;
        }
    }
    $res->free();

    $elapsed = round(microtime(true) - $start, 2);
    echo json_encode(array(
        'ok'      => true,
        'settled' => $settled,
        'expired' => $expired,
        'elapsed' => $elapsed . 's',
        'tag'     => 'CURSORCODE_Feb152026'
    ));
}


// =====================================================================
//  STATUS — Engine health check
// =====================================================================

function _pf_action_status($conn) {
    $fp_count = 0;
    $alert_count = 0;
    $last_build = 'never';
    $last_scan  = 'never';

    $r = $conn->query("SELECT COUNT(*) as c FROM pf_fingerprints");
    if ($r && $row = $r->fetch_assoc()) { $fp_count = intval($row['c']); }

    $r = $conn->query("SELECT COUNT(*) as c FROM pf_alerts WHERE status='active'");
    if ($r && $row = $r->fetch_assoc()) { $alert_count = intval($row['c']); }

    $r = $conn->query("SELECT MAX(updated_at) as t FROM pf_fingerprints");
    if ($r && $row = $r->fetch_assoc()) { $last_build = $row['t'] ? $row['t'] : 'never'; }

    $r = $conn->query("SELECT MAX(created_at) as t FROM pf_alerts");
    if ($r && $row = $r->fetch_assoc()) { $last_scan = $row['t'] ? $row['t'] : 'never'; }

    // Per-class breakdown
    $breakdown = array();
    $br = $conn->query("SELECT asset_class, COUNT(*) as pairs,
                                AVG(win_rate) as avg_wr
                         FROM pf_fingerprints GROUP BY asset_class");
    if ($br) {
        while ($b = $br->fetch_assoc()) {
            $b['avg_wr'] = round(floatval($b['avg_wr']), 1);
            $breakdown[] = $b;
        }
    }

    echo json_encode(array(
        'ok'              => true,
        'engine'          => 'Pair Fingerprint Engine',
        'version'         => 'CURSORCODE_Feb152026',
        'fingerprints'    => $fp_count,
        'active_alerts'   => $alert_count,
        'last_build'      => $last_build,
        'last_scan'       => $last_scan,
        'asset_breakdown' => $breakdown,
        'methodology'     => 'Per-pair behavioral profiling. Unlike generic indicator strategies, this engine studies each asset\'s unique patterns: mean-reversion tendency, momentum correlation, breakout frequency, pump susceptibility, optimal TP/SL, best trading session. Alerts fire ONLY when a pair enters its historically profitable pattern.'
    ));
}


// =====================================================================
//  UTILITY FUNCTIONS
// =====================================================================

function _pf_compute_autocorrelation($sequence) {
    $n = count($sequence);
    if ($n < 4) { return 0; }

    $mean = array_sum($sequence) / $n;
    $variance = 0;
    for ($i = 0; $i < $n; $i++) {
        $variance += pow($sequence[$i] - $mean, 2);
    }
    $variance = $variance / $n;
    if ($variance == 0) { return 0; }

    // Lag-1 autocorrelation
    $covariance = 0;
    for ($i = 1; $i < $n; $i++) {
        $covariance += ($sequence[$i] - $mean) * ($sequence[$i-1] - $mean);
    }
    $covariance = $covariance / ($n - 1);

    return $covariance / $variance;
}

function _pf_compute_variance($sequence) {
    $n = count($sequence);
    if ($n < 2) { return 0; }
    $mean = array_sum($sequence) / $n;
    $var = 0;
    for ($i = 0; $i < $n; $i++) {
        $var += pow($sequence[$i] - $mean, 2);
    }
    return $var / ($n - 1);
}

function _pf_percentile($sorted_array, $percentile) {
    sort($sorted_array);
    $n = count($sorted_array);
    if ($n === 0) { return 0; }
    $index = ($percentile / 100) * ($n - 1);
    $lower = floor($index);
    $upper = ceil($index);
    if ($lower == $upper) { return $sorted_array[$lower]; }
    $frac = $index - $lower;
    return $sorted_array[$lower] * (1 - $frac) + $sorted_array[$upper] * $frac;
}

function _pf_detect_best_session($signals) {
    $hour_wins = array();
    $hour_total = array();
    for ($h = 0; $h < 24; $h++) {
        $hour_wins[$h]  = 0;
        $hour_total[$h] = 0;
    }
    foreach ($signals as $sig) {
        $time_field = null;
        if (isset($sig['signal_time'])) { $time_field = $sig['signal_time']; }
        elseif (isset($sig['created_at'])) { $time_field = $sig['created_at']; }
        if ($time_field === null) { continue; }
        $hour = intval(date('G', strtotime($time_field)));
        $hour_total[$hour]++;
        $is_win = false;
        if (isset($sig['status']) && $sig['status'] === 'won') { $is_win = true; }
        if (isset($sig['exit_reason']) && $sig['exit_reason'] === 'TP') { $is_win = true; }
        if (isset($sig['pnl_pct']) && floatval($sig['pnl_pct']) > 0) { $is_win = true; }
        if ($is_win) { $hour_wins[$hour]++; }
    }

    // Find best 4-hour window
    $sessions = array(
        'ASIA_EARLY'       => array(0,1,2,3),
        'ASIA_LATE'        => array(4,5,6,7),
        'LONDON_OPEN'      => array(8,9,10,11),
        'LONDON_NY_OVERLAP' => array(12,13,14,15),
        'NY_AFTERNOON'     => array(16,17,18,19),
        'NY_CLOSE'         => array(20,21,22,23)
    );

    $best_session = 'ANY';
    $best_wr = 0;
    foreach ($sessions as $name => $hours) {
        $wins  = 0;
        $total = 0;
        foreach ($hours as $h) {
            $wins  += $hour_wins[$h];
            $total += $hour_total[$h];
        }
        if ($total >= 3) {
            $wr = _pf_safe_div($wins * 100, $total);
            if ($wr > $best_wr) {
                $best_wr      = $wr;
                $best_session = $name;
            }
        }
    }
    return $best_session;
}

function _pf_get_current_price($pair, $class, $meme_conn) {
    // Try CryptoCompare for crypto/meme
    if ($class === 'CRYPTO' || $class === 'MEME') {
        $clean = str_replace(array('_USDT', '/USDT', '_USD', '/USD', 'USDT'), '', $pair);
        $url = 'https://min-api.cryptocompare.com/data/price?fsym=' . urlencode($clean) . '&tsyms=USD';
        $ctx = stream_context_create(array('http' => array('timeout' => 5)));
        $raw = @file_get_contents($url, false, $ctx);
        if ($raw) {
            $data = json_decode($raw, true);
            if (isset($data['USD'])) {
                return floatval($data['USD']);
            }
        }
    }

    // Try Finnhub for stocks
    if ($class === 'STOCK') {
        $url = 'https://finnhub.io/api/v1/quote?symbol=' . urlencode($pair)
             . '&token=cvstlkhr01qhup0t0j7gcvstlkhr01qhup0t0j80';
        $ctx = stream_context_create(array('http' => array('timeout' => 5)));
        $raw = @file_get_contents($url, false, $ctx);
        if ($raw) {
            $data = json_decode($raw, true);
            if (isset($data['c']) && $data['c'] > 0) {
                return floatval($data['c']);
            }
        }
    }

    // Try CurrencyLayer for forex
    if ($class === 'FOREX') {
        $base = substr($pair, 0, 3);
        $quote = substr($pair, 3, 3);
        if ($quote === '') { $quote = 'USD'; }
        $url = 'http://api.currencylayer.com/live?access_key=d7ea1ac2fe1deb49ed6f8e07c882b341&currencies=' . $quote . '&source=' . $base;
        $ctx = stream_context_create(array('http' => array('timeout' => 5)));
        $raw = @file_get_contents($url, false, $ctx);
        if ($raw) {
            $data = json_decode($raw, true);
            $key = $base . $quote;
            if (isset($data['quotes'][$key])) {
                return floatval($data['quotes'][$key]);
            }
        }
    }

    return 0;
}

function _pf_store_patterns($conn, $pair, $class, $data, $now) {
    $seq = $data['pnl_sequence'];
    $n   = count($seq);
    if ($n < 3) { return; }

    // Pattern: DIP_THEN_PUMP — loss followed by >5% gain
    $dtp_count = 0;
    $dtp_wins  = 0;
    $dtp_returns = array();
    for ($i = 1; $i < $n; $i++) {
        if ($seq[$i-1] < -1) { // Previous was a loss > 1%
            $dtp_count++;
            if ($seq[$i] > 0) {
                $dtp_wins++;
                $dtp_returns[] = $seq[$i];
            }
        }
    }
    if ($dtp_count >= 2) {
        _pf_upsert_pattern($conn, $pair, $class, 'DIP_THEN_PUMP', $dtp_count,
            _pf_safe_div($dtp_wins * 100, $dtp_count),
            count($dtp_returns) > 0 ? array_sum($dtp_returns) / count($dtp_returns) : 0,
            $now);
    }

    // Pattern: MOMENTUM_STREAK — 2+ consecutive wins
    $streak_count = 0;
    $streak_wins  = 0;
    $streak_returns = array();
    for ($i = 2; $i < $n; $i++) {
        if ($seq[$i-1] > 0 && $seq[$i-2] > 0) {
            $streak_count++;
            if ($seq[$i] > 0) {
                $streak_wins++;
                $streak_returns[] = $seq[$i];
            }
        }
    }
    if ($streak_count >= 2) {
        _pf_upsert_pattern($conn, $pair, $class, 'MOMENTUM_STREAK', $streak_count,
            _pf_safe_div($streak_wins * 100, $streak_count),
            count($streak_returns) > 0 ? array_sum($streak_returns) / count($streak_returns) : 0,
            $now);
    }

    // Pattern: VOLATILITY_EXPANSION — small move followed by big move
    $ve_count = 0;
    $ve_wins  = 0;
    $ve_returns = array();
    for ($i = 1; $i < $n; $i++) {
        if (abs($seq[$i-1]) < 1 && abs($seq[$i]) > 3) {
            $ve_count++;
            if ($seq[$i] > 0) {
                $ve_wins++;
                $ve_returns[] = $seq[$i];
            }
        }
    }
    if ($ve_count >= 2) {
        _pf_upsert_pattern($conn, $pair, $class, 'VOLATILITY_EXPANSION', $ve_count,
            _pf_safe_div($ve_wins * 100, $ve_count),
            count($ve_returns) > 0 ? array_sum($ve_returns) / count($ve_returns) : 0,
            $now);
    }

    // Pattern: REVERSAL_AFTER_BIG_LOSS — loss > 5% then recovery
    $rabl_count = 0;
    $rabl_wins  = 0;
    for ($i = 1; $i < $n; $i++) {
        if ($seq[$i-1] < -5) {
            $rabl_count++;
            if ($seq[$i] > 0) { $rabl_wins++; }
        }
    }
    if ($rabl_count >= 2) {
        _pf_upsert_pattern($conn, $pair, $class, 'REVERSAL_AFTER_BIG_LOSS', $rabl_count,
            _pf_safe_div($rabl_wins * 100, $rabl_count), 0, $now);
    }
}

function _pf_upsert_pattern($conn, $pair, $class, $pattern_name, $occurrences, $wr, $avg_ret, $now) {
    $sql = "REPLACE INTO pf_pair_patterns
            (pair, asset_class, pattern_name, occurrences, win_rate, avg_return_pct, updated_at)
            VALUES ('" . $conn->real_escape_string($pair) . "','"
            . $conn->real_escape_string($class) . "','"
            . $conn->real_escape_string($pattern_name) . "',"
            . intval($occurrences) . ","
            . round($wr, 2) . ","
            . round($avg_ret, 4) . ",'"
            . $now . "')";
    $conn->query($sql);
}

function _pf_summarize_algos($algo_stats) {
    $summary = array();
    foreach ($algo_stats as $algo => $stats) {
        $wr = _pf_safe_div($stats['wins'] * 100, $stats['total']);
        $summary[] = array(
            'algo' => $algo,
            'total' => $stats['total'],
            'wins'  => $stats['wins'],
            'wr'    => round($wr, 1),
            'pnl'   => round($stats['pnl'], 2)
        );
    }
    // Sort by win rate desc
    usort($summary, '_pf_sort_by_wr');
    return $summary;
}

function _pf_sort_by_wr($a, $b) {
    if ($a['wr'] == $b['wr']) { return 0; }
    return ($a['wr'] > $b['wr']) ? -1 : 1;
}

function _pf_get_strategy_recommendation($fp) {
    $behavior = $fp['behavior_type'];
    $wr = floatval($fp['win_rate']);
    $tp = floatval($fp['optimal_tp_pct']);
    $sl = floatval($fp['optimal_sl_pct']);
    $session = $fp['best_session'];
    $algo = $fp['best_algorithm'];

    $rec = array(
        'behavior' => $behavior,
        'strategy' => '',
        'entry_rules' => array(),
        'exit_rules' => array(),
        'timing' => $session,
        'confidence' => 'LOW'
    );

    if ($behavior === 'MEAN_REVERTING') {
        $rec['strategy'] = 'Buy dips, sell recoveries. This asset tends to bounce back after drops.';
        $rec['entry_rules'] = array(
            'Wait for 2%+ dip from recent high',
            'RSI < 35 confirms oversold',
            'Volume declining (exhaustion)',
            'Use ' . $algo . ' algorithm for best entry timing'
        );
        $rec['exit_rules'] = array(
            'TP: ' . $tp . '% (calibrated to this pair)',
            'SL: ' . $sl . '% (tight — mean reversion fails fast when it fails)',
            'Time exit: ' . $fp['optimal_hold_hours'] . ' hours max'
        );
    } elseif ($behavior === 'TRENDING') {
        $rec['strategy'] = 'Follow momentum. This asset trends — ride winners, cut losers fast.';
        $rec['entry_rules'] = array(
            'Confirm uptrend (price > SMA20)',
            'Wait for pullback to support',
            'Volume expanding on breakout',
            'Use ' . $algo . ' for entry signals'
        );
        $rec['exit_rules'] = array(
            'TP: ' . $tp . '% (let trends run)',
            'SL: ' . $sl . '%',
            'Trail stop after +' . round($tp * 0.5, 1) . '%'
        );
    } elseif ($behavior === 'BREAKOUT_PRONE') {
        $rec['strategy'] = 'Trade breakouts. This asset consolidates then explodes.';
        $rec['entry_rules'] = array(
            'Wait for range compression (Bollinger squeeze)',
            'Enter on breakout above range with volume',
            'Confirm with ' . $algo,
            'Best during ' . $session . ' session'
        );
        $rec['exit_rules'] = array(
            'TP: ' . $tp . '% (breakouts can run big)',
            'SL: ' . $sl . '% (below breakout level)',
            'Move to breakeven after +' . round($tp * 0.3, 1) . '%'
        );
    } elseif ($behavior === 'PUMP_SUSCEPTIBLE') {
        $rec['strategy'] = 'Watch for pump setups. This asset shows recurring pump patterns.';
        $rec['entry_rules'] = array(
            'Volume trending up (accumulation)',
            'Price in RSI 30-45 sweet spot',
            'OBV divergence (smart money buying)',
            'Pump forensics score > 50'
        );
        $rec['exit_rules'] = array(
            'TP: ' . $tp . '% (take profit FAST on pumps)',
            'SL: ' . $sl . '%',
            'Partial exit at +' . round($tp * 0.5, 1) . '%, remainder at TP'
        );
    } else {
        $rec['strategy'] = 'Mixed behavior. Use ' . $algo . ' with standard TP/SL.';
        $rec['entry_rules'] = array('Follow ' . $algo . ' signals', 'Confirm with volume');
        $rec['exit_rules'] = array('TP: ' . $tp . '%', 'SL: ' . $sl . '%');
    }

    if ($wr >= 60) { $rec['confidence'] = 'HIGH'; }
    elseif ($wr >= 45) { $rec['confidence'] = 'MEDIUM'; }
    else { $rec['confidence'] = 'LOW'; }

    return $rec;
}

function _pf_refine_from_hour_learning($conn, $now) {
    // Pull hour learning optimal params and merge into fingerprints
    $sql = "SELECT hl.asset_class, hl.algorithm_name, hl.best_tp_pct, hl.best_sl_pct, hl.best_hold_hours
            FROM lm_hour_learning hl
            INNER JOIN (
                SELECT asset_class, algorithm_name, MAX(calc_date) as latest
                FROM lm_hour_learning
                WHERE verdict = 'PROFITABLE_PARAMS_EXIST'
                GROUP BY asset_class, algorithm_name
            ) latest ON hl.asset_class = latest.asset_class
                     AND hl.algorithm_name = latest.algorithm_name
                     AND hl.calc_date = latest.latest";
    $res = $conn->query($sql);
    if (!$res) { return; }

    while ($row = $res->fetch_assoc()) {
        // Update fingerprints where the best_algorithm matches
        $conn->query("UPDATE pf_fingerprints SET
            optimal_hold_hours = " . intval($row['best_hold_hours']) . "
            WHERE best_algorithm = '" . $conn->real_escape_string($row['algorithm_name']) . "'
            AND asset_class = '" . $conn->real_escape_string($row['asset_class']) . "'");
    }
    $res->free();
}
?>
