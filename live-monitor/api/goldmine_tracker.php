<?php
/**
 * goldmine_tracker.php — Multi-Page Goldmine Checker: Recommendations vs Reality
 * Unified tracking API that archives picks from ALL systems and tracks outcomes.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   ?action=schema                           — Ensure all tables exist
 *   ?action=archive&key=livetrader2026       — Archive picks from all systems
 *   ?action=update_outcomes&key=livetrader2026 — Update prices + check TP/SL
 *   ?action=check_health&key=livetrader2026  — Generate health snapshots + alerts
 *   ?action=dashboard                        — Per-system stats overview
 *   ?action=picks&status=open|closed|all     — Paginated unified pick list
 *   ?action=system_detail&system=X           — Deep dive on one system
 *   ?action=ticker_history&ticker=AAPL       — All picks for a ticker
 *   ?action=alerts                           — Active failure alerts
 *   ?action=leaderboard                      — Systems + algos ranked by accuracy
 *   ?action=enriched&id=X                    — Single pick with enrichment
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/goldmine_schema.php';

$action = isset($_GET['action']) ? $_GET['action'] : 'dashboard';
$key    = isset($_GET['key'])    ? $_GET['key']    : '';
$admin  = ($key === 'livetrader2026');
$now    = date('Y-m-d H:i:s');
$today  = date('Y-m-d');

// Ensure schema on every request (lightweight IF NOT EXISTS)
_gm_ensure_schema($conn);

// ── Cache helper ──
$CACHE_DIR = dirname(__FILE__) . '/cache/';
if (!is_dir($CACHE_DIR)) { @mkdir($CACHE_DIR, 0755, true); }

function _gm_cache_get($key, $ttl_sec) {
    global $CACHE_DIR;
    $f = $CACHE_DIR . 'gm_' . md5($key) . '.json';
    if (file_exists($f) && (time() - filemtime($f)) < $ttl_sec) {
        $d = @file_get_contents($f);
        if ($d !== false) return json_decode($d, true);
    }
    return false;
}
function _gm_cache_set($key, $data) {
    global $CACHE_DIR;
    $f = $CACHE_DIR . 'gm_' . md5($key) . '.json';
    @file_put_contents($f, json_encode($data));
}

// ── HTTP helper (cURL primary, file_get_contents fallback) ──
function _gm_http_get($url, $headers_arr) {
    if (function_exists('curl_init')) {
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        if (!empty($headers_arr)) {
            curl_setopt($ch, CURLOPT_HTTPHEADER, $headers_arr);
        }
        curl_setopt($ch, CURLOPT_USERAGENT, 'GoldmineTracker/1.0 (findtorontoevents.ca)');
        $resp = curl_exec($ch);
        curl_close($ch);
        if ($resp !== false) return $resp;
    }
    $ctx = stream_context_create(array('http' => array(
        'timeout' => 15,
        'user_agent' => 'GoldmineTracker/1.0 (findtorontoevents.ca)'
    )));
    return @file_get_contents($url, false, $ctx);
}

// ── Escape helper ──
function _gm_esc($conn, $val) {
    return $conn->real_escape_string($val);
}

// ────────────────────────────────────────────────────────────
//  ADMIN ACTIONS
// ────────────────────────────────────────────────────────────

if ($action === 'schema') {
    echo json_encode(array('ok' => true, 'message' => 'Schema ensured'));
    exit;
}

// ── ARCHIVE: Pull picks from all systems ──
if ($action === 'archive') {
    if (!$admin) { echo json_encode(array('ok' => false, 'error' => 'Unauthorized')); exit; }

    $stats = array();

    // 1. Consolidated Picks — from consensus_tracked
    $stats['consolidated'] = _gm_archive_consolidated($conn);

    // 2. Live Signals — from lm_signals
    $stats['live_signal'] = _gm_archive_live_signals($conn);

    // 3. Edge Dashboard — from lm_opportunities
    $stats['edge'] = _gm_archive_edge($conn);

    // 4. Meme Coins — from ejaguiar1_memecoin.mc_winners (cross-DB)
    $stats['meme'] = _gm_archive_meme($conn);

    // 5. Sports Betting — from lm_sports_daily_picks (cross-DB)
    $stats['sports'] = _gm_archive_sports($conn);

    // 6. Horizon Picks — from report_cache or cURL
    $stats['horizon'] = _gm_archive_horizon($conn);

    // 7. Top Picks — from report_cache
    $stats['top_picks'] = _gm_archive_top_picks($conn);

    // 8. Penny Stocks — snapshot top movers
    $stats['penny'] = _gm_archive_penny($conn);

    echo json_encode(array('ok' => true, 'action' => 'archive', 'stats' => $stats));
    exit;
}

// ── UPDATE OUTCOMES: Fetch prices and check TP/SL ──
if ($action === 'update_outcomes') {
    if (!$admin) { echo json_encode(array('ok' => false, 'error' => 'Unauthorized')); exit; }

    $result = _gm_update_outcomes($conn);
    echo json_encode(array('ok' => true, 'action' => 'update_outcomes', 'result' => $result));
    exit;
}

// ── CHECK HEALTH: Generate health snapshots + alerts ──
if ($action === 'check_health') {
    if (!$admin) { echo json_encode(array('ok' => false, 'error' => 'Unauthorized')); exit; }

    $result = _gm_check_health($conn);
    echo json_encode(array('ok' => true, 'action' => 'check_health', 'result' => $result));
    exit;
}

// ────────────────────────────────────────────────────────────
//  PUBLIC ACTIONS
// ────────────────────────────────────────────────────────────

// ── DASHBOARD: Per-system stats overview ──
if ($action === 'dashboard') {
    $cached = _gm_cache_get('dashboard', 300);
    if ($cached) { echo json_encode($cached); exit; }

    $systems = array();
    $r = $conn->query("SELECT source_system,
        COUNT(*) as total_picks,
        SUM(CASE WHEN status != 'open' THEN 1 ELSE 0 END) as closed_picks,
        SUM(CASE WHEN status = 'tp_hit' THEN 1 ELSE 0 END) as tp_wins,
        SUM(CASE WHEN status = 'sl_hit' THEN 1 ELSE 0 END) as losses,
        SUM(CASE WHEN status IN ('max_hold','expired') THEN 1 ELSE 0 END) as expired,
        SUM(CASE WHEN status IN ('max_hold','expired') AND final_return_pct > 0 THEN 1 ELSE 0 END) as expired_wins,
        AVG(CASE WHEN status != 'open' THEN final_return_pct ELSE NULL END) as avg_return,
        SUM(CASE WHEN status != 'open' THEN final_return_pct ELSE 0 END) as total_return,
        AVG(CASE WHEN status != 'open' THEN hold_hours ELSE NULL END) as avg_hold
        FROM gm_unified_picks GROUP BY source_system ORDER BY source_system");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $closed = intval($row['closed_picks']);
            $wins   = intval($row['tp_wins']) + intval($row['expired_wins']);
            $row['wins'] = $wins;
            $wr = ($closed > 0) ? round(($wins / $closed) * 100, 1) : 0;
            $row['win_rate'] = $wr;
            $systems[] = $row;
        }
    }

    // Active alerts count
    $alert_r = $conn->query("SELECT COUNT(*) as cnt FROM gm_failure_alerts WHERE is_active = 1");
    $alert_cnt = 0;
    if ($alert_r && ($ar = $alert_r->fetch_assoc())) { $alert_cnt = intval($ar['cnt']); }

    // Top 5 recent winners
    $top_winners = array();
    $tw = $conn->query("SELECT ticker, source_system, final_return_pct, pick_date, exit_date
        FROM gm_unified_picks WHERE status = 'tp_hit' ORDER BY exit_date DESC LIMIT 5");
    if ($tw) { while ($row = $tw->fetch_assoc()) { $top_winners[] = $row; } }

    // Top 5 recent losers
    $top_losers = array();
    $tl = $conn->query("SELECT ticker, source_system, final_return_pct, pick_date, exit_date
        FROM gm_unified_picks WHERE status = 'sl_hit' ORDER BY exit_date DESC LIMIT 5");
    if ($tl) { while ($row = $tl->fetch_assoc()) { $top_losers[] = $row; } }

    $data = array(
        'ok' => true,
        'systems' => $systems,
        'active_alerts' => $alert_cnt,
        'top_winners' => $top_winners,
        'top_losers' => $top_losers,
        'generated_at' => $now
    );
    _gm_cache_set('dashboard', $data);
    echo json_encode($data);
    exit;
}

// ── PICKS: Paginated unified list ──
if ($action === 'picks') {
    $status  = isset($_GET['status'])  ? _gm_esc($conn, $_GET['status'])  : 'all';
    $system  = isset($_GET['system'])  ? _gm_esc($conn, $_GET['system'])  : '';
    $asset   = isset($_GET['asset'])   ? _gm_esc($conn, $_GET['asset'])   : '';
    $ticker  = isset($_GET['ticker'])  ? _gm_esc($conn, $_GET['ticker'])  : '';
    $page    = isset($_GET['page'])    ? max(1, intval($_GET['page']))     : 1;
    $limit   = 50;
    $offset  = ($page - 1) * $limit;

    $where = array('1=1');
    if ($status !== 'all' && $status !== '') { $where[] = "status = '" . $status . "'"; }
    if ($system !== '') { $where[] = "source_system = '" . $system . "'"; }
    if ($asset !== '')  { $where[] = "asset_type = '" . $asset . "'"; }
    if ($ticker !== '') { $where[] = "ticker LIKE '%" . $ticker . "%'"; }

    $wh = implode(' AND ', $where);

    // Count
    $cr = $conn->query("SELECT COUNT(*) as cnt FROM gm_unified_picks WHERE " . $wh);
    $total = 0;
    if ($cr && ($c = $cr->fetch_assoc())) { $total = intval($c['cnt']); }

    // Fetch
    $rows = array();
    $r = $conn->query("SELECT * FROM gm_unified_picks WHERE " . $wh .
        " ORDER BY pick_date DESC, id DESC LIMIT " . $limit . " OFFSET " . $offset);
    if ($r) { while ($row = $r->fetch_assoc()) { $rows[] = $row; } }

    echo json_encode(array(
        'ok' => true,
        'picks' => $rows,
        'total' => $total,
        'page' => $page,
        'pages' => ceil($total / $limit)
    ));
    exit;
}

// ── SYSTEM DETAIL: Deep dive on one system ──
if ($action === 'system_detail') {
    $system = isset($_GET['system']) ? _gm_esc($conn, $_GET['system']) : '';
    if ($system === '') { echo json_encode(array('ok' => false, 'error' => 'system required')); exit; }

    $cached = _gm_cache_get('system_' . $system, 300);
    if ($cached) { echo json_encode($cached); exit; }

    // Overall stats
    $r = $conn->query("SELECT
        COUNT(*) as total,
        SUM(CASE WHEN status != 'open' THEN 1 ELSE 0 END) as closed,
        SUM(CASE WHEN status = 'tp_hit' THEN 1 ELSE 0 END) as tp_wins,
        SUM(CASE WHEN status IN ('max_hold','expired') AND final_return_pct > 0 THEN 1 ELSE 0 END) as expired_wins,
        SUM(CASE WHEN status = 'sl_hit' THEN 1 ELSE 0 END) as losses,
        AVG(CASE WHEN status != 'open' THEN final_return_pct ELSE NULL END) as avg_return,
        SUM(CASE WHEN status != 'open' THEN final_return_pct ELSE 0 END) as total_return,
        MIN(pick_date) as first_pick,
        MAX(pick_date) as last_pick
        FROM gm_unified_picks WHERE source_system = '" . $system . "'");
    $stats = array();
    if ($r && ($row = $r->fetch_assoc())) {
        $row['wins'] = intval($row['tp_wins']) + intval($row['expired_wins']);
        $stats = $row;
    }

    // By algorithm
    $algos = array();
    $r = $conn->query("SELECT algorithm_name,
        COUNT(*) as picks,
        SUM(CASE WHEN status = 'tp_hit' THEN 1 ELSE 0 END) as tp_wins,
        SUM(CASE WHEN status IN ('max_hold','expired') AND final_return_pct > 0 THEN 1 ELSE 0 END) as expired_wins,
        SUM(CASE WHEN status = 'sl_hit' THEN 1 ELSE 0 END) as losses,
        AVG(CASE WHEN status != 'open' THEN final_return_pct ELSE NULL END) as avg_return
        FROM gm_unified_picks WHERE source_system = '" . $system . "' AND algorithm_name != ''
        GROUP BY algorithm_name ORDER BY tp_wins DESC LIMIT 20");
    if ($r) { while ($row = $r->fetch_assoc()) { $row['wins'] = intval($row['tp_wins']) + intval($row['expired_wins']); $algos[] = $row; } }

    // Recent picks
    $recent = array();
    $r = $conn->query("SELECT * FROM gm_unified_picks WHERE source_system = '" . $system . "'
        ORDER BY pick_date DESC LIMIT 20");
    if ($r) { while ($row = $r->fetch_assoc()) { $recent[] = $row; } }

    // Daily win rate trend (last 30 days)
    $trend = array();
    $r = $conn->query("SELECT pick_date,
        COUNT(*) as picks,
        SUM(CASE WHEN status = 'tp_hit' THEN 1 ELSE 0 END) +
        SUM(CASE WHEN status IN ('max_hold','expired') AND final_return_pct > 0 THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN status = 'sl_hit' THEN 1 ELSE 0 END) +
        SUM(CASE WHEN status IN ('max_hold','expired') AND final_return_pct <= 0 THEN 1 ELSE 0 END) as losses
        FROM gm_unified_picks WHERE source_system = '" . $system . "'
        AND pick_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) AND status != 'open'
        GROUP BY pick_date ORDER BY pick_date");
    if ($r) { while ($row = $r->fetch_assoc()) { $trend[] = $row; } }

    $data = array(
        'ok' => true,
        'system' => $system,
        'stats' => $stats,
        'algorithms' => $algos,
        'recent_picks' => $recent,
        'daily_trend' => $trend
    );
    _gm_cache_set('system_' . $system, $data);
    echo json_encode($data);
    exit;
}

// ── TICKER HISTORY: All picks for one ticker across all systems ──
if ($action === 'ticker_history') {
    $ticker = isset($_GET['ticker']) ? _gm_esc($conn, strtoupper($_GET['ticker'])) : '';
    if ($ticker === '') { echo json_encode(array('ok' => false, 'error' => 'ticker required')); exit; }

    $rows = array();
    $r = $conn->query("SELECT * FROM gm_unified_picks WHERE ticker = '" . $ticker . "'
        ORDER BY pick_date DESC LIMIT 100");
    if ($r) { while ($row = $r->fetch_assoc()) { $rows[] = $row; } }

    // Summary
    $sr = $conn->query("SELECT
        COUNT(*) as total,
        SUM(CASE WHEN status = 'tp_hit' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN status = 'sl_hit' THEN 1 ELSE 0 END) as losses,
        AVG(CASE WHEN status != 'open' THEN final_return_pct ELSE NULL END) as avg_return,
        COUNT(DISTINCT source_system) as systems_count,
        GROUP_CONCAT(DISTINCT source_system) as systems
        FROM gm_unified_picks WHERE ticker = '" . $ticker . "'");
    $summary = array();
    if ($sr && ($s = $sr->fetch_assoc())) { $summary = $s; }

    echo json_encode(array('ok' => true, 'ticker' => $ticker, 'summary' => $summary, 'picks' => $rows));
    exit;
}

// ── ALERTS: Active failure alerts ──
if ($action === 'alerts') {
    $rows = array();
    $r = $conn->query("SELECT * FROM gm_failure_alerts WHERE is_active = 1 ORDER BY severity DESC, alert_date DESC");
    if ($r) { while ($row = $r->fetch_assoc()) { $rows[] = $row; } }

    echo json_encode(array('ok' => true, 'active_count' => count($rows), 'alerts' => $rows));
    exit;
}

// ── LEADERBOARD: Systems + algorithms ranked by accuracy ──
if ($action === 'leaderboard') {
    $cached = _gm_cache_get('leaderboard', 600);
    if ($cached) { echo json_encode($cached); exit; }

    // Systems ranked
    $sys_rank = array();
    $r = $conn->query("SELECT source_system,
        COUNT(*) as total,
        SUM(CASE WHEN status = 'tp_hit' THEN 1 ELSE 0 END) as tp_wins,
        SUM(CASE WHEN status IN ('max_hold','expired') AND final_return_pct > 0 THEN 1 ELSE 0 END) as expired_wins,
        SUM(CASE WHEN status != 'open' THEN 1 ELSE 0 END) as closed,
        AVG(CASE WHEN status != 'open' THEN final_return_pct ELSE NULL END) as avg_return,
        SUM(CASE WHEN status != 'open' THEN final_return_pct ELSE 0 END) as total_return
        FROM gm_unified_picks GROUP BY source_system
        HAVING closed > 0 ORDER BY avg_return DESC");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $closed = intval($row['closed']);
            $wins   = intval($row['tp_wins']) + intval($row['expired_wins']);
            $row['wins'] = $wins;
            $row['win_rate'] = ($closed > 0) ? round(($wins / $closed) * 100, 1) : 0;
            $sys_rank[] = $row;
        }
    }

    // Top algorithms across all systems
    $algo_rank = array();
    $r = $conn->query("SELECT algorithm_name, source_system,
        COUNT(*) as total,
        SUM(CASE WHEN status = 'tp_hit' THEN 1 ELSE 0 END) as tp_wins,
        SUM(CASE WHEN status IN ('max_hold','expired') AND final_return_pct > 0 THEN 1 ELSE 0 END) as expired_wins,
        SUM(CASE WHEN status != 'open' THEN 1 ELSE 0 END) as closed,
        AVG(CASE WHEN status != 'open' THEN final_return_pct ELSE NULL END) as avg_return
        FROM gm_unified_picks WHERE algorithm_name != ''
        GROUP BY algorithm_name, source_system
        HAVING closed >= 3 ORDER BY avg_return DESC LIMIT 30");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $closed = intval($row['closed']);
            $wins   = intval($row['tp_wins']) + intval($row['expired_wins']);
            $row['wins'] = $wins;
            $row['win_rate'] = ($closed > 0) ? round(($wins / $closed) * 100, 1) : 0;
            $algo_rank[] = $row;
        }
    }

    // Consistent winners (tickers that won 3+ times)
    $consistent = array();
    $r = $conn->query("SELECT ticker,
        COUNT(*) as times_picked,
        SUM(CASE WHEN status = 'tp_hit' THEN 1 ELSE 0 END) +
        SUM(CASE WHEN status IN ('max_hold','expired') AND final_return_pct > 0 THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN status != 'open' THEN 1 ELSE 0 END) as closed,
        AVG(CASE WHEN status != 'open' THEN final_return_pct ELSE NULL END) as avg_return,
        COUNT(DISTINCT source_system) as systems
        FROM gm_unified_picks GROUP BY ticker
        HAVING wins >= 3 ORDER BY wins DESC, avg_return DESC LIMIT 20");
    if ($r) { while ($row = $r->fetch_assoc()) { $consistent[] = $row; } }

    $data = array(
        'ok' => true,
        'system_ranking' => $sys_rank,
        'algorithm_ranking' => $algo_rank,
        'consistent_winners' => $consistent,
        'generated_at' => $now
    );
    _gm_cache_set('leaderboard', $data);
    echo json_encode($data);
    exit;
}

// ── ENRICHED: Single pick with dividend/earnings enrichment ──
if ($action === 'enriched') {
    $id = isset($_GET['id']) ? intval($_GET['id']) : 0;
    if ($id <= 0) { echo json_encode(array('ok' => false, 'error' => 'id required')); exit; }

    $r = $conn->query("SELECT * FROM gm_unified_picks WHERE id = " . $id);
    if (!$r || $r->num_rows === 0) { echo json_encode(array('ok' => false, 'error' => 'not found')); exit; }
    $pick = $r->fetch_assoc();

    // Dividend enrichment
    $divs = array();
    if ($pick['asset_type'] === 'stock') {
        $dr = $conn->query("SELECT * FROM stock_dividends
            WHERE ticker = '" . _gm_esc($conn, $pick['ticker']) . "'
            AND ex_date >= '" . _gm_esc($conn, $pick['pick_date']) . "'
            AND ex_date <= '" . ($pick['exit_date'] ? _gm_esc($conn, $pick['exit_date']) : $today) . "'
            ORDER BY ex_date");
        if ($dr) { while ($d = $dr->fetch_assoc()) { $divs[] = $d; } }
    }

    // Earnings events
    $earnings = array();
    if ($pick['asset_type'] === 'stock') {
        $er = $conn->query("SELECT * FROM stock_earnings
            WHERE ticker = '" . _gm_esc($conn, $pick['ticker']) . "'
            AND earnings_date >= '" . _gm_esc($conn, $pick['pick_date']) . "'
            AND earnings_date <= '" . ($pick['exit_date'] ? _gm_esc($conn, $pick['exit_date']) : $today) . "'
            ORDER BY earnings_date");
        if ($er) { while ($e = $er->fetch_assoc()) { $earnings[] = $e; } }
    }

    // Fundamentals snapshot
    $fund = array();
    if ($pick['asset_type'] === 'stock') {
        $fr = $conn->query("SELECT * FROM stock_fundamentals
            WHERE ticker = '" . _gm_esc($conn, $pick['ticker']) . "' LIMIT 1");
        if ($fr && $fr->num_rows > 0) { $fund = $fr->fetch_assoc(); }
    }

    echo json_encode(array(
        'ok' => true,
        'pick' => $pick,
        'dividends' => $divs,
        'earnings' => $earnings,
        'fundamentals' => $fund
    ));
    exit;
}

// Default
echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
exit;

// ════════════════════════════════════════════════════════════
//  ARCHIVE FUNCTIONS — one per source system
// ════════════════════════════════════════════════════════════

function _gm_archive_consolidated($conn) {
    global $now;
    $inserted = 0;
    $r = $conn->query("SELECT * FROM consensus_tracked ORDER BY created_at DESC LIMIT 200");
    if (!$r) return array('inserted' => 0, 'error' => 'consensus_tracked not found');

    while ($row = $r->fetch_assoc()) {
        $sid = intval($row['id']);
        $dup = $conn->query("SELECT id FROM gm_unified_picks
            WHERE source_system='consolidated' AND source_table='consensus_tracked'
            AND source_id=" . $sid . " AND pick_date='" . _gm_esc($conn, $row['entry_date']) . "'");
        if ($dup && $dup->num_rows > 0) continue;

        $entry  = floatval($row['entry_price']);
        $tp_pct = floatval($row['target_tp_pct']);
        $sl_pct = floatval($row['target_sl_pct']);
        $tp_price = $entry * (1 + $tp_pct / 100);
        $sl_price = $entry * (1 - $sl_pct / 100);

        $status = 'open';
        $exit_reason = '';
        $final_ret = 0;
        if ($row['status'] === 'closed') {
            $er = $row['exit_reason'];
            if (strpos($er, 'tp') !== false) { $status = 'tp_hit'; }
            elseif (strpos($er, 'sl') !== false) { $status = 'sl_hit'; }
            elseif (strpos($er, 'max') !== false) { $status = 'max_hold'; }
            else { $status = 'expired'; }
            $exit_reason = $er;
            $final_ret = floatval($row['final_return_pct']);
        }

        $hold_hours = intval($row['hold_days']) * 24;

        $conn->query("INSERT INTO gm_unified_picks
            (source_system, source_page, source_id, source_table, pick_date, pick_time,
             asset_type, ticker, asset_name, direction, algorithm_name, algo_count,
             entry_price, target_price, stop_loss_price, target_pct, stop_loss_pct,
             confidence_score, hold_period_hours, metadata_json,
             status, current_price, current_return_pct, peak_price, trough_price,
             exit_price, exit_date, exit_reason, final_return_pct, hold_hours,
             created_at, updated_at)
            VALUES (
             'consolidated', '/findstocks/portfolio2/consolidated.html',
             " . $sid . ", 'consensus_tracked',
             '" . _gm_esc($conn, $row['entry_date']) . "',
             '" . _gm_esc($conn, $row['created_at']) . "',
             'stock', '" . _gm_esc($conn, $row['ticker']) . "',
             '" . _gm_esc($conn, $row['company_name']) . "',
             '" . _gm_esc($conn, $row['direction']) . "',
             '" . _gm_esc($conn, $row['source_algos']) . "',
             " . intval($row['consensus_count']) . ",
             " . $entry . ", " . $tp_price . ", " . $sl_price . ",
             " . $tp_pct . ", " . $sl_pct . ",
             " . intval($row['consensus_score']) . ", " . $hold_hours . ",
             NULL,
             '" . $status . "',
             " . floatval($row['current_price']) . ",
             " . floatval($row['current_return_pct']) . ",
             " . floatval($row['peak_price']) . ",
             " . floatval($row['trough_price']) . ",
             " . floatval($row['exit_price']) . ",
             " . ($row['exit_date'] ? "'" . _gm_esc($conn, $row['exit_date']) . "'" : "NULL") . ",
             '" . _gm_esc($conn, $exit_reason) . "',
             " . $final_ret . ", " . $hold_hours . ",
             '" . $now . "', '" . $now . "')");
        if ($conn->affected_rows > 0) $inserted++;
    }
    return array('inserted' => $inserted);
}

function _gm_archive_live_signals($conn) {
    global $now;
    $inserted = 0;
    $r = $conn->query("SELECT * FROM lm_signals ORDER BY signal_time DESC LIMIT 300");
    if (!$r) return array('inserted' => 0, 'error' => 'lm_signals not found');

    while ($row = $r->fetch_assoc()) {
        $sid = intval($row['id']);

        // Minimum signal strength filter — skip weak signals to improve win rate
        $strength = intval($row['signal_strength']);
        if ($strength < 50) continue;

        $pick_date = substr($row['signal_time'], 0, 10);
        $dup = $conn->query("SELECT id FROM gm_unified_picks
            WHERE source_system='live_signal' AND source_table='lm_signals'
            AND source_id=" . $sid);
        if ($dup && $dup->num_rows > 0) continue;

        $entry  = floatval($row['entry_price']);
        $tp_pct = floatval($row['target_tp_pct']);
        $sl_pct = floatval($row['target_sl_pct']);
        $dir    = strtoupper($row['signal_type']);
        if ($dir === 'BUY') $dir = 'LONG';
        if ($dir === 'SELL' || $dir === 'SHORT') $dir = 'SHORT';

        $tp_price = ($dir === 'LONG') ? $entry * (1 + $tp_pct / 100) : $entry * (1 - $tp_pct / 100);
        $sl_price = ($dir === 'LONG') ? $entry * (1 - $sl_pct / 100) : $entry * (1 + $sl_pct / 100);

        $asset = strtolower($row['asset_class']);
        if ($asset === 'crypto') $asset = 'crypto';
        elseif ($asset === 'forex') $asset = 'forex';
        else $asset = 'stock';

        $conn->query("INSERT INTO gm_unified_picks
            (source_system, source_page, source_id, source_table, pick_date, pick_time,
             asset_type, ticker, direction, algorithm_name, algo_count,
             entry_price, target_price, stop_loss_price, target_pct, stop_loss_pct,
             confidence_score, hold_period_hours,
             status, created_at, updated_at)
            VALUES (
             'live_signal', '/live-monitor/live-monitor.html',
             " . $sid . ", 'lm_signals',
             '" . $pick_date . "',
             '" . _gm_esc($conn, $row['signal_time']) . "',
             '" . $asset . "',
             '" . _gm_esc($conn, $row['symbol']) . "',
             '" . $dir . "',
             '" . _gm_esc($conn, $row['algorithm_name']) . "', 1,
             " . $entry . ", " . $tp_price . ", " . $sl_price . ",
             " . $tp_pct . ", " . $sl_pct . ",
             " . intval($row['signal_strength']) . ",
             " . intval($row['max_hold_hours']) . ",
             'open', '" . $now . "', '" . $now . "')");
        if ($conn->affected_rows > 0) $inserted++;
    }

    // Also map closed trades to update statuses
    $tr = $conn->query("SELECT t.*, s.id as signal_id FROM lm_trades t
        LEFT JOIN lm_signals s ON t.symbol = s.symbol AND t.entry_price = s.entry_price
        WHERE t.status = 'closed' ORDER BY t.id DESC LIMIT 200");
    $updated = 0;
    if ($tr) {
        while ($row = $tr->fetch_assoc()) {
            if (!$row['signal_id']) continue;
            $exit_r = $row['exit_reason'];
            $st = 'expired';
            if (strpos($exit_r, 'tp') !== false) $st = 'tp_hit';
            elseif (strpos($exit_r, 'sl') !== false) $st = 'sl_hit';
            elseif (strpos($exit_r, 'max') !== false) $st = 'max_hold';

            $conn->query("UPDATE gm_unified_picks SET
                status = '" . $st . "',
                exit_reason = '" . _gm_esc($conn, $exit_r) . "',
                final_return_pct = " . floatval($row['realized_pct']) . ",
                hold_hours = " . floatval($row['hold_hours']) . ",
                updated_at = '" . date('Y-m-d H:i:s') . "'
                WHERE source_system = 'live_signal' AND source_id = " . intval($row['signal_id']) . "
                AND status = 'open'");
            if ($conn->affected_rows > 0) $updated++;
        }
    }

    return array('inserted' => $inserted, 'updated_from_trades' => $updated);
}

function _gm_archive_edge($conn) {
    global $now;
    $inserted = 0;
    $r = $conn->query("SELECT * FROM lm_opportunities ORDER BY scan_time DESC LIMIT 100");
    if (!$r) return array('inserted' => 0, 'error' => 'lm_opportunities not found');

    while ($row = $r->fetch_assoc()) {
        $sid = intval($row['id']);
        $pick_date = substr($row['scan_time'], 0, 10);
        $dup = $conn->query("SELECT id FROM gm_unified_picks
            WHERE source_system='edge' AND source_table='lm_opportunities'
            AND source_id=" . $sid);
        if ($dup && $dup->num_rows > 0) continue;

        $entry  = floatval($row['entry_price']);
        $tp_pct = floatval($row['avg_tp_pct']);
        $sl_pct = floatval($row['avg_sl_pct']);
        $dir = strtoupper($row['direction']);
        if ($dir === 'BUY') $dir = 'LONG';
        if ($dir === 'SELL') $dir = 'SHORT';

        $tp_price = ($dir === 'LONG') ? $entry * (1 + $tp_pct / 100) : $entry * (1 - $tp_pct / 100);
        $sl_price = ($dir === 'LONG') ? $entry * (1 - $sl_pct / 100) : $entry * (1 + $sl_pct / 100);

        $asset = strtolower($row['asset_class']);

        $hold = 24; // default
        $hp = $row['holding_period'];
        if ($hp === 'scalp') $hold = 4;
        elseif ($hp === 'daytrader') $hold = 24;
        elseif ($hp === 'swing') $hold = 168;

        $conn->query("INSERT INTO gm_unified_picks
            (source_system, source_page, source_id, source_table, pick_date, pick_time,
             asset_type, ticker, direction, algorithm_name, algo_count,
             entry_price, target_price, stop_loss_price, target_pct, stop_loss_pct,
             confidence_score, hold_period_hours, metadata_json,
             status, created_at, updated_at)
            VALUES (
             'edge', '/live-monitor/edge-dashboard.html',
             " . $sid . ", 'lm_opportunities',
             '" . $pick_date . "',
             '" . _gm_esc($conn, $row['scan_time']) . "',
             '" . $asset . "',
             '" . _gm_esc($conn, $row['symbol']) . "',
             '" . $dir . "',
             'Edge Confluence', " . intval($row['signal_count']) . ",
             " . $entry . ", " . $tp_price . ", " . $sl_price . ",
             " . $tp_pct . ", " . $sl_pct . ",
             " . intval($row['confidence_score']) . ", " . $hold . ",
             '" . _gm_esc($conn, $row['key_reason_now']) . "',
             'open', '" . $now . "', '" . $now . "')");
        if ($conn->affected_rows > 0) $inserted++;
    }
    return array('inserted' => $inserted);
}

function _gm_archive_meme($conn) {
    global $now;
    $inserted = 0;

    // Cross-DB connection to meme coin database
    $mc = @new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
    if ($mc->connect_error) return array('inserted' => 0, 'error' => 'meme DB connect failed');

    $r = $mc->query("SELECT * FROM mc_winners ORDER BY created_at DESC LIMIT 100");
    if (!$r) { $mc->close(); return array('inserted' => 0, 'error' => 'mc_winners query failed'); }

    while ($row = $r->fetch_assoc()) {
        $sid = intval($row['id']);
        $pick_date = substr($row['created_at'], 0, 10);

        $dup = $conn->query("SELECT id FROM gm_unified_picks
            WHERE source_system='meme' AND source_table='mc_winners'
            AND source_id=" . $sid);
        if ($dup && $dup->num_rows > 0) continue;

        $entry   = floatval($row['price_at_signal']);
        $tp_pct  = floatval($row['target_pct']);
        $sl_pct  = floatval($row['risk_pct']);
        $tp_price = $entry * (1 + $tp_pct / 100);
        $sl_price = $entry * (1 - $sl_pct / 100);

        $status = 'open';
        $final_ret = 0;
        $exit_reason = '';
        if ($row['outcome'] === 'win') { $status = 'tp_hit'; $final_ret = floatval($row['pnl_pct']); $exit_reason = 'target_hit'; }
        elseif ($row['outcome'] === 'loss') { $status = 'sl_hit'; $final_ret = floatval($row['pnl_pct']); $exit_reason = 'stop_loss'; }

        $conn->query("INSERT INTO gm_unified_picks
            (source_system, source_page, source_id, source_table, pick_date, pick_time,
             asset_type, ticker, direction, algorithm_name, algo_count,
             entry_price, target_price, stop_loss_price, target_pct, stop_loss_pct,
             confidence_score, hold_period_hours,
             status, exit_reason, final_return_pct,
             exit_date, created_at, updated_at)
            VALUES (
             'meme', '/findcryptopairs/meme.html',
             " . $sid . ", 'mc_winners',
             '" . _gm_esc($conn, $pick_date) . "',
             '" . _gm_esc($conn, $row['created_at']) . "',
             'meme',
             '" . _gm_esc($conn, $row['pair']) . "',
             'LONG', 'Meme Scanner', 1,
             " . $entry . ", " . $tp_price . ", " . $sl_price . ",
             " . $tp_pct . ", " . $sl_pct . ",
             " . intval($row['score']) . ", 2,
             '" . $status . "', '" . _gm_esc($conn, $exit_reason) . "', " . $final_ret . ",
             " . ($row['resolved_at'] ? "'" . _gm_esc($conn, $row['resolved_at']) . "'" : "NULL") . ",
             '" . $now . "', '" . $now . "')");
        if ($conn->affected_rows > 0) $inserted++;
    }

    $mc->close();
    return array('inserted' => $inserted);
}

function _gm_archive_sports($conn) {
    global $now;
    $inserted = 0;

    // Cross-DB — try sports DB first, fallback to stocks
    $sc = @new mysqli('mysql.50webs.com', 'ejaguiar1_sportsbet', 'eltonsportsbets', 'ejaguiar1_sportsbet');
    if ($sc->connect_error) {
        $sc = $conn; // fallback to stocks DB
    }

    $r = $sc->query("SELECT * FROM lm_sports_daily_picks ORDER BY pick_date DESC LIMIT 200");
    if (!$r) {
        if ($sc !== $conn) $sc->close();
        return array('inserted' => 0, 'error' => 'lm_sports_daily_picks not found');
    }

    while ($row = $r->fetch_assoc()) {
        $sid = intval($row['id']);

        $dup = $conn->query("SELECT id FROM gm_unified_picks
            WHERE source_system='sports' AND source_table='lm_sports_daily_picks'
            AND source_id=" . $sid);
        if ($dup && $dup->num_rows > 0) continue;

        $ticker_label = $row['away_team'] . ' @ ' . $row['home_team'];
        $ev = floatval($row['ev_pct']);
        $odds = floatval($row['best_odds']);

        $status = 'open';
        $final_ret = 0;
        $exit_reason = '';
        if (isset($row['result'])) {
            if ($row['result'] === 'win') { $status = 'tp_hit'; $final_ret = floatval($row['pnl']); $exit_reason = 'win'; }
            elseif ($row['result'] === 'loss') { $status = 'sl_hit'; $final_ret = floatval($row['pnl']); $exit_reason = 'loss'; }
            elseif ($row['result'] === 'push') { $status = 'expired'; $exit_reason = 'push'; }
        }

        $conf = 50;
        if (isset($row['confidence'])) {
            if ($row['confidence'] === 'high') $conf = 85;
            elseif ($row['confidence'] === 'medium') $conf = 65;
            else $conf = 40;
        }

        $conn->query("INSERT INTO gm_unified_picks
            (source_system, source_page, source_id, source_table, pick_date, pick_time,
             asset_type, ticker, asset_name, direction, algorithm_name, algo_count,
             entry_price, target_pct, stop_loss_pct,
             confidence_score, hold_period_hours, metadata_json,
             status, exit_reason, final_return_pct,
             created_at, updated_at)
            VALUES (
             'sports', '/live-monitor/sports-betting.html',
             " . $sid . ", 'lm_sports_daily_picks',
             '" . _gm_esc($conn, $row['pick_date']) . "',
             '" . _gm_esc($conn, $row['generated_at']) . "',
             'sports_bet',
             '" . _gm_esc($conn, $row['sport'] . ':' . $row['outcome_name']) . "',
             '" . _gm_esc($conn, $ticker_label) . "',
             'LONG',
             '" . _gm_esc($conn, $row['algorithm']) . "', 1,
             " . $odds . ", " . $ev . ", 100,
             " . $conf . ", 4,
             '" . _gm_esc($conn, $row['market'] . '|' . $row['best_book']) . "',
             '" . $status . "', '" . _gm_esc($conn, $exit_reason) . "', " . $final_ret . ",
             '" . $now . "', '" . $now . "')");
        if ($conn->affected_rows > 0) $inserted++;
    }

    if ($sc !== $conn) $sc->close();
    return array('inserted' => $inserted);
}

function _gm_archive_horizon($conn) {
    global $now;
    $inserted = 0;

    // Try to fetch horizon picks via internal cURL
    $url = 'https://findtorontoevents.ca/findstocks/portfolio2/api/horizon_picks.php?nocache=1';
    $resp = _gm_http_get($url, array());
    if (!$resp) return array('inserted' => 0, 'error' => 'horizon_picks fetch failed');

    $data = json_decode($resp, true);
    if (!$data || !isset($data['ok']) || !$data['ok']) return array('inserted' => 0, 'error' => 'horizon_picks bad response');

    $horizons = array('quick', 'swing', 'longterm');
    foreach ($horizons as $hz) {
        if (!isset($data[$hz]) || !isset($data[$hz]['picks'])) continue;
        $picks = $data[$hz]['picks'];
        $hold_hours = 336; // 14 days default
        if ($hz === 'quick') $hold_hours = 336;
        elseif ($hz === 'swing') $hold_hours = 1440; // 60 days
        elseif ($hz === 'longterm') $hold_hours = 6048; // 252 days

        foreach ($picks as $i => $p) {
            $ticker = isset($p['ticker']) ? $p['ticker'] : '';
            if ($ticker === '') continue;

            $dup = $conn->query("SELECT id FROM gm_unified_picks
                WHERE source_system='horizon' AND ticker='" . _gm_esc($conn, $ticker) . "'
                AND pick_date='" . date('Y-m-d') . "'
                AND metadata_json LIKE '%" . _gm_esc($conn, $hz) . "%'");
            if ($dup && $dup->num_rows > 0) continue;

            $entry = isset($p['latest_price']) ? floatval($p['latest_price']) : 0;
            $score = isset($p['score']) ? intval($p['score']) : 0;
            $tp_pct = 10;
            $sl_pct = 5;
            if ($hz === 'swing') { $tp_pct = 20; $sl_pct = 8; }
            if ($hz === 'longterm') { $tp_pct = 40; $sl_pct = 15; }

            $tp_price = $entry * (1 + $tp_pct / 100);
            $sl_price = $entry * (1 - $sl_pct / 100);

            $conn->query("INSERT INTO gm_unified_picks
                (source_system, source_page, source_id, source_table, pick_date, pick_time,
                 asset_type, ticker, asset_name, direction, algorithm_name, algo_count,
                 entry_price, target_price, stop_loss_price, target_pct, stop_loss_pct,
                 confidence_score, hold_period_hours, metadata_json,
                 status, created_at, updated_at)
                VALUES (
                 'horizon', '/findstocks/portfolio2/horizon-picks.html',
                 0, 'horizon_picks',
                 '" . date('Y-m-d') . "', '" . $now . "',
                 'stock', '" . _gm_esc($conn, $ticker) . "',
                 '" . _gm_esc($conn, isset($p['company_name']) ? $p['company_name'] : '') . "',
                 'LONG',
                 'Horizon " . ucfirst($hz) . "', 1,
                 " . $entry . ", " . $tp_price . ", " . $sl_price . ",
                 " . $tp_pct . ", " . $sl_pct . ",
                 " . $score . ", " . $hold_hours . ",
                 '{\"horizon\":\"" . $hz . "\"}',
                 'open', '" . $now . "', '" . $now . "')");
            if ($conn->affected_rows > 0) $inserted++;
        }
    }
    return array('inserted' => $inserted);
}

function _gm_archive_top_picks($conn) {
    global $now;
    $inserted = 0;

    $r = $conn->query("SELECT cache_data FROM report_cache
        WHERE cache_key = 'top_picks_v3' ORDER BY updated_at DESC LIMIT 1");
    if (!$r || $r->num_rows === 0) return array('inserted' => 0, 'error' => 'no top_picks cache');

    $row = $r->fetch_assoc();
    $data = json_decode($row['cache_data'], true);
    if (!$data) return array('inserted' => 0, 'error' => 'bad top_picks JSON');

    // Top picks may have different structures — handle both array and keyed
    $picks = array();
    if (isset($data['picks'])) $picks = $data['picks'];
    elseif (isset($data['swing'])) $picks = $data['swing'];
    else $picks = $data;

    if (!is_array($picks)) return array('inserted' => 0, 'error' => 'no picks array');

    foreach ($picks as $p) {
        $ticker = isset($p['ticker']) ? $p['ticker'] : '';
        if ($ticker === '') continue;

        $dup = $conn->query("SELECT id FROM gm_unified_picks
            WHERE source_system='top_picks' AND ticker='" . _gm_esc($conn, $ticker) . "'
            AND pick_date='" . date('Y-m-d') . "'");
        if ($dup && $dup->num_rows > 0) continue;

        $entry = isset($p['latest_price']) ? floatval($p['latest_price']) : (isset($p['price']) ? floatval($p['price']) : 0);
        $score = isset($p['score']) ? intval($p['score']) : 0;
        $algo  = isset($p['algorithm']) ? $p['algorithm'] : (isset($p['strategy_name']) ? $p['strategy_name'] : 'Top Pick');

        $conn->query("INSERT INTO gm_unified_picks
            (source_system, source_page, source_id, source_table, pick_date, pick_time,
             asset_type, ticker, direction, algorithm_name, algo_count,
             entry_price, target_pct, stop_loss_pct,
             confidence_score, hold_period_hours,
             status, created_at, updated_at)
            VALUES (
             'top_picks', '/findstocks/portfolio2/picks.html',
             0, 'report_cache',
             '" . date('Y-m-d') . "', '" . $now . "',
             'stock', '" . _gm_esc($conn, $ticker) . "', 'LONG',
             '" . _gm_esc($conn, $algo) . "', 1,
             " . $entry . ", 8, 4,
             " . $score . ", 336,
             'open', '" . $now . "', '" . $now . "')");
        if ($conn->affected_rows > 0) $inserted++;
    }
    return array('inserted' => $inserted);
}

function _gm_archive_penny($conn) {
    global $now;
    $inserted = 0;

    // Snapshot top 20 penny stock movers
    $url = 'https://findtorontoevents.ca/findstocks/portfolio2/api/penny_stocks.php?region=both&sort=percentchange&min_volume=500000&max_results=20';
    $resp = _gm_http_get($url, array());
    if (!$resp) return array('inserted' => 0, 'error' => 'penny_stocks fetch failed');

    $data = json_decode($resp, true);
    if (!$data || !isset($data['ok']) || !$data['ok']) return array('inserted' => 0, 'error' => 'penny_stocks bad response');

    $stocks = isset($data['stocks']) ? $data['stocks'] : (isset($data['results']) ? $data['results'] : array());

    foreach ($stocks as $i => $s) {
        if ($i >= 20) break;
        $ticker = isset($s['symbol']) ? $s['symbol'] : '';
        if ($ticker === '') continue;

        $dup = $conn->query("SELECT id FROM gm_unified_picks
            WHERE source_system='penny' AND ticker='" . _gm_esc($conn, $ticker) . "'
            AND pick_date='" . date('Y-m-d') . "'");
        if ($dup && $dup->num_rows > 0) continue;

        $price = isset($s['regularMarketPrice']) ? floatval($s['regularMarketPrice']) : (isset($s['price']) ? floatval($s['price']) : 0);
        $vol   = isset($s['regularMarketVolume']) ? intval($s['regularMarketVolume']) : 0;
        $chg   = isset($s['regularMarketChangePercent']) ? floatval($s['regularMarketChangePercent']) : 0;

        $conn->query("INSERT INTO gm_unified_picks
            (source_system, source_page, source_id, source_table, pick_date, pick_time,
             asset_type, ticker, asset_name, direction, algorithm_name,
             entry_price, target_pct, stop_loss_pct,
             confidence_score, hold_period_hours, metadata_json,
             status, created_at, updated_at)
            VALUES (
             'penny', '/findstocks/portfolio2/penny-stocks.html',
             0, 'penny_screener',
             '" . date('Y-m-d') . "', '" . $now . "',
             'stock', '" . _gm_esc($conn, $ticker) . "',
             '" . _gm_esc($conn, isset($s['shortName']) ? $s['shortName'] : '') . "',
             'LONG', 'Penny Screener',
             " . $price . ", 15, 10,
             " . min(100, max(0, intval($chg * 2))) . ", 336,
             '{\"volume\":" . $vol . ",\"change_pct\":" . round($chg, 2) . "}',
             'open', '" . $now . "', '" . $now . "')");
        if ($conn->affected_rows > 0) $inserted++;
    }
    return array('inserted' => $inserted);
}

// ════════════════════════════════════════════════════════════
//  UPDATE OUTCOMES — fetch current prices, check TP/SL/max_hold
// ════════════════════════════════════════════════════════════

function _gm_update_outcomes($conn) {
    global $now;
    $updated = 0;
    $closed = 0;

    // Get all open picks
    $r = $conn->query("SELECT * FROM gm_unified_picks WHERE status = 'open' ORDER BY pick_date");
    if (!$r) return array('error' => 'query failed');

    $picks = array();
    while ($row = $r->fetch_assoc()) { $picks[] = $row; }

    // Group by asset type to batch price lookups
    $stock_tickers = array();
    $crypto_tickers = array();
    $forex_tickers = array();

    foreach ($picks as $p) {
        if ($p['asset_type'] === 'stock') $stock_tickers[$p['ticker']] = 1;
        elseif ($p['asset_type'] === 'crypto' || $p['asset_type'] === 'meme') $crypto_tickers[$p['ticker']] = 1;
        elseif ($p['asset_type'] === 'forex') $forex_tickers[$p['ticker']] = 1;
    }

    // Fetch prices from lm_price_cache (live monitor prices)
    $prices = array();
    $pr = $conn->query("SELECT symbol, price, updated_at FROM lm_price_cache");
    if ($pr) {
        while ($row = $pr->fetch_assoc()) {
            $prices[$row['symbol']] = floatval($row['price']);
        }
    }

    // Also check daily_prices for stocks
    $stock_list = array_keys($stock_tickers);
    if (count($stock_list) > 0) {
        $in = "'" . implode("','", array_map(array($conn, 'real_escape_string'), $stock_list)) . "'";
        $dp = $conn->query("SELECT ticker, close_price FROM daily_prices
            WHERE ticker IN (" . $in . ") ORDER BY trade_date DESC");
        if ($dp) {
            $seen = array();
            while ($row = $dp->fetch_assoc()) {
                if (!isset($seen[$row['ticker']])) {
                    $prices[$row['ticker']] = floatval($row['close_price']);
                    $seen[$row['ticker']] = 1;
                }
            }
        }
    }

    // Process each open pick
    foreach ($picks as $p) {
        $ticker = $p['ticker'];
        $id = intval($p['id']);

        // Skip sports bets — they resolve differently
        if ($p['asset_type'] === 'sports_bet') continue;

        $current = isset($prices[$ticker]) ? $prices[$ticker] : 0;
        if ($current <= 0) continue;

        $entry = floatval($p['entry_price']);
        if ($entry <= 0) continue;

        $dir = $p['direction'];
        if ($dir === 'LONG') {
            $return_pct = (($current - $entry) / $entry) * 100;
        } else {
            $return_pct = (($entry - $current) / $entry) * 100;
        }

        // Track peak/trough
        $peak   = max(floatval($p['peak_price']), $current);
        $trough = floatval($p['trough_price']);
        if ($trough <= 0) $trough = $current;
        $trough = min($trough, $current);

        // Check TP/SL
        $tp_pct = floatval($p['target_pct']);
        $sl_pct = floatval($p['stop_loss_pct']);
        $hold_max = intval($p['hold_period_hours']);
        $pick_time = strtotime($p['pick_time']);
        $hold_elapsed = (time() - $pick_time) / 3600;

        $new_status = 'open';
        $exit_reason = '';

        if ($return_pct >= $tp_pct && $tp_pct > 0) {
            $new_status = 'tp_hit';
            $exit_reason = 'target_hit';
        } elseif ($return_pct <= -$sl_pct && $sl_pct > 0) {
            $new_status = 'sl_hit';
            $exit_reason = 'stop_loss_hit';
        } elseif ($hold_max > 0 && $hold_elapsed >= $hold_max) {
            $new_status = 'max_hold';
            $exit_reason = 'max_hold_expired';
        }

        $exit_date_sql = 'NULL';
        $final_ret = $return_pct;
        if ($new_status !== 'open') {
            $exit_date_sql = "'" . $now . "'";
            $closed++;
        }

        // Dividend enrichment for stocks
        $div_earned = floatval($p['dividends_earned']);
        $earn_events = intval($p['earnings_events']);
        if ($p['asset_type'] === 'stock' && $new_status !== 'open') {
            $dr = $conn->query("SELECT SUM(amount) as total FROM stock_dividends
                WHERE ticker = '" . _gm_esc($conn, $ticker) . "'
                AND ex_date >= '" . _gm_esc($conn, $p['pick_date']) . "'
                AND ex_date <= '" . date('Y-m-d') . "'");
            if ($dr && ($d = $dr->fetch_assoc()) && $d['total']) {
                $div_earned = floatval($d['total']);
            }
            $er2 = $conn->query("SELECT COUNT(*) as cnt FROM stock_earnings
                WHERE ticker = '" . _gm_esc($conn, $ticker) . "'
                AND earnings_date >= '" . _gm_esc($conn, $p['pick_date']) . "'
                AND earnings_date <= '" . date('Y-m-d') . "'");
            if ($er2 && ($e = $er2->fetch_assoc())) {
                $earn_events = intval($e['cnt']);
            }
        }

        $total_ret = $final_ret + ($entry > 0 ? ($div_earned / $entry) * 100 : 0);

        $conn->query("UPDATE gm_unified_picks SET
            current_price = " . $current . ",
            current_return_pct = " . round($return_pct, 4) . ",
            peak_price = " . $peak . ",
            trough_price = " . $trough . ",
            status = '" . $new_status . "',
            exit_price = " . ($new_status !== 'open' ? $current : 0) . ",
            exit_date = " . $exit_date_sql . ",
            exit_reason = '" . _gm_esc($conn, $exit_reason) . "',
            final_return_pct = " . round($final_ret, 4) . ",
            hold_hours = " . round($hold_elapsed, 2) . ",
            dividends_earned = " . round($div_earned, 4) . ",
            earnings_events = " . $earn_events . ",
            total_return_pct = " . round($total_ret, 4) . ",
            updated_at = '" . $now . "'
            WHERE id = " . $id);
        if ($conn->affected_rows > 0) $updated++;
    }

    return array('open_picks' => count($picks), 'updated' => $updated, 'newly_closed' => $closed);
}

// ════════════════════════════════════════════════════════════
//  HEALTH CHECK — generate snapshots + failure alerts
// ════════════════════════════════════════════════════════════

function _gm_check_health($conn) {
    global $now, $today;

    $systems = array('consolidated', 'live_signal', 'edge', 'meme', 'sports', 'horizon', 'top_picks', 'penny');
    $page_urls = array(
        'consolidated' => '/findstocks/portfolio2/consolidated.html',
        'live_signal'  => '/live-monitor/live-monitor.html',
        'edge'         => '/live-monitor/edge-dashboard.html',
        'meme'         => '/findcryptopairs/meme.html',
        'sports'       => '/live-monitor/sports-betting.html',
        'horizon'      => '/findstocks/portfolio2/horizon-picks.html',
        'top_picks'    => '/findstocks/portfolio2/picks.html',
        'penny'        => '/findstocks/portfolio2/penny-stocks.html'
    );

    // Thresholds
    $WARN_WIN_RATE  = 40;
    $CRIT_WIN_RATE  = 25;
    $WARN_CONSEC    = 5;
    $CRIT_CONSEC    = 10;
    $WARN_STALE     = 3;   // days
    $CRIT_STALE     = 7;
    $WARN_AVG_RET   = -2;
    $CRIT_AVG_RET   = -5;

    $alerts_created = 0;
    $health_snaps = 0;

    // Auto-resolve stale alerts
    $conn->query("UPDATE gm_failure_alerts SET is_active = 0, resolved_at = '" . $now . "'
        WHERE is_active = 1 AND alert_date < DATE_SUB(CURDATE(), INTERVAL 7 DAY)");

    foreach ($systems as $sys) {
        // Overall stats
        $r = $conn->query("SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status != 'open' THEN 1 ELSE 0 END) as closed,
            SUM(CASE WHEN status = 'tp_hit' THEN 1 ELSE 0 END) as tp_wins,
            SUM(CASE WHEN status = 'sl_hit' THEN 1 ELSE 0 END) as losses,
            SUM(CASE WHEN status IN ('max_hold','expired') THEN 1 ELSE 0 END) as expired,
            SUM(CASE WHEN status IN ('max_hold','expired') AND final_return_pct > 0 THEN 1 ELSE 0 END) as expired_wins,
            AVG(CASE WHEN status != 'open' THEN final_return_pct ELSE NULL END) as avg_ret,
            SUM(CASE WHEN status != 'open' THEN final_return_pct ELSE 0 END) as total_ret,
            AVG(CASE WHEN status != 'open' THEN hold_hours ELSE NULL END) as avg_hold,
            MAX(pick_date) as last_pick_date
            FROM gm_unified_picks WHERE source_system = '" . _gm_esc($conn, $sys) . "'");

        if (!$r || $r->num_rows === 0) continue;
        $s = $r->fetch_assoc();
        $total_closed = intval($s['closed']);
        $wins = intval($s['tp_wins']) + intval($s['expired_wins']);
        $losses = intval($s['losses']);
        $win_rate = ($total_closed > 0) ? round(($wins / $total_closed) * 100, 1) : 0;

        // 7-day and 30-day accuracy
        $wr7 = _gm_win_rate_period($conn, $sys, 7);
        $wr30 = _gm_win_rate_period($conn, $sys, 30);

        // Best/worst picks
        $best_t = ''; $best_pct = 0; $worst_t = ''; $worst_pct = 0;
        $br = $conn->query("SELECT ticker, final_return_pct FROM gm_unified_picks
            WHERE source_system='" . _gm_esc($conn, $sys) . "' AND status != 'open'
            ORDER BY final_return_pct DESC LIMIT 1");
        if ($br && ($b = $br->fetch_assoc())) { $best_t = $b['ticker']; $best_pct = floatval($b['final_return_pct']); }

        $wr = $conn->query("SELECT ticker, final_return_pct FROM gm_unified_picks
            WHERE source_system='" . _gm_esc($conn, $sys) . "' AND status != 'open'
            ORDER BY final_return_pct ASC LIMIT 1");
        if ($wr && ($w = $wr->fetch_assoc())) { $worst_t = $w['ticker']; $worst_pct = floatval($w['final_return_pct']); }

        // Is failing?
        $is_failing = 0;
        $fail_reasons = array();

        // Check win rate
        if ($wr30 > 0 && $wr30 < $CRIT_WIN_RATE && $total_closed >= 5) {
            $is_failing = 1;
            $fail_reasons[] = 'Win rate critically low: ' . $wr30 . '%';
            _gm_create_alert($conn, $sys, 'accuracy_drop', 'critical',
                $sys . ': Win rate critically low (' . $wr30 . '%)',
                'The 30-day win rate has dropped to ' . $wr30 . '% which is below the critical threshold of ' . $CRIT_WIN_RATE . '%. Review algorithm parameters and recent market conditions.',
                '', $wr30, $CRIT_WIN_RATE, isset($page_urls[$sys]) ? $page_urls[$sys] : '');
            $alerts_created++;
        } elseif ($wr30 > 0 && $wr30 < $WARN_WIN_RATE && $total_closed >= 5) {
            $fail_reasons[] = 'Win rate below warning: ' . $wr30 . '%';
            _gm_create_alert($conn, $sys, 'accuracy_drop', 'warning',
                $sys . ': Win rate declining (' . $wr30 . '%)',
                'The 30-day win rate is ' . $wr30 . '%, approaching the critical threshold.',
                '', $wr30, $WARN_WIN_RATE, isset($page_urls[$sys]) ? $page_urls[$sys] : '');
            $alerts_created++;
        }

        // Check consecutive losses
        $consec = _gm_consecutive_losses($conn, $sys);
        if ($consec >= $CRIT_CONSEC) {
            $is_failing = 1;
            $fail_reasons[] = $consec . ' consecutive losses';
            _gm_create_alert($conn, $sys, 'losing_streak', 'critical',
                $sys . ': ' . $consec . ' consecutive losses',
                'The system has lost ' . $consec . ' trades in a row, indicating potential systematic failure.',
                '', $consec, $CRIT_CONSEC, isset($page_urls[$sys]) ? $page_urls[$sys] : '');
            $alerts_created++;
        } elseif ($consec >= $WARN_CONSEC) {
            $fail_reasons[] = $consec . ' consecutive losses';
            _gm_create_alert($conn, $sys, 'losing_streak', 'warning',
                $sys . ': ' . $consec . ' consecutive losses',
                'The system is on a losing streak.',
                '', $consec, $WARN_CONSEC, isset($page_urls[$sys]) ? $page_urls[$sys] : '');
            $alerts_created++;
        }

        // Check staleness
        $last_pick = $s['last_pick_date'];
        if ($last_pick) {
            $days_since = (strtotime($today) - strtotime($last_pick)) / 86400;
            if ($days_since >= $CRIT_STALE) {
                $fail_reasons[] = 'No picks in ' . intval($days_since) . ' days';
                _gm_create_alert($conn, $sys, 'stale_data', 'critical',
                    $sys . ': No new picks for ' . intval($days_since) . ' days',
                    'This system has not generated any new picks recently. Check data sources and cron jobs.',
                    '', $days_since, $CRIT_STALE, isset($page_urls[$sys]) ? $page_urls[$sys] : '');
                $alerts_created++;
            } elseif ($days_since >= $WARN_STALE) {
                $fail_reasons[] = 'No picks in ' . intval($days_since) . ' days';
                _gm_create_alert($conn, $sys, 'stale_data', 'warning',
                    $sys . ': ' . intval($days_since) . ' days since last pick',
                    'Data may be going stale. Check refresh mechanisms.',
                    '', $days_since, $WARN_STALE, isset($page_urls[$sys]) ? $page_urls[$sys] : '');
                $alerts_created++;
            }
        }

        // Rapid decline: 7d accuracy dropping significantly vs 30d
        if ($wr7 > 0 && $wr30 > 0 && $total_closed >= 5) {
            $decline = $wr30 - $wr7;
            if ($decline >= 20) {
                $is_failing = 1;
                $fail_reasons[] = 'Rapid decline: 7d=' . $wr7 . '% vs 30d=' . $wr30 . '%';
                _gm_create_alert($conn, $sys, 'rapid_decline', 'critical',
                    $sys . ': Accuracy plummeting (7d: ' . $wr7 . '% vs 30d: ' . $wr30 . '%)',
                    'Win rate has dropped ' . round($decline, 1) . ' percentage points in the last 7 days compared to 30-day average. This indicates a sudden regime change or data issue.',
                    '', $wr7, $wr30, isset($page_urls[$sys]) ? $page_urls[$sys] : '');
                $alerts_created++;
            } elseif ($decline >= 12) {
                $fail_reasons[] = 'Declining: 7d=' . $wr7 . '% vs 30d=' . $wr30 . '%';
                _gm_create_alert($conn, $sys, 'rapid_decline', 'warning',
                    $sys . ': Accuracy declining (7d: ' . $wr7 . '% vs 30d: ' . $wr30 . '%)',
                    'Win rate has dropped ' . round($decline, 1) . ' percentage points recently. Monitor closely.',
                    '', $wr7, $wr30, isset($page_urls[$sys]) ? $page_urls[$sys] : '');
                $alerts_created++;
            }
        }

        // Avg return check — now creates alerts
        $avg_ret = floatval($s['avg_ret']);
        if ($total_closed >= 5 && $avg_ret < $CRIT_AVG_RET) {
            $is_failing = 1;
            $fail_reasons[] = 'Average return: ' . round($avg_ret, 2) . '%';
            _gm_create_alert($conn, $sys, 'negative_roi', 'critical',
                $sys . ': Average return deeply negative (' . round($avg_ret, 1) . '%)',
                'The average return per trade is ' . round($avg_ret, 2) . '%, well below the critical threshold of ' . $CRIT_AVG_RET . '%. The system is losing money on average.',
                '', $avg_ret, $CRIT_AVG_RET, isset($page_urls[$sys]) ? $page_urls[$sys] : '');
            $alerts_created++;
        } elseif ($total_closed >= 5 && $avg_ret < $WARN_AVG_RET) {
            $fail_reasons[] = 'Average return: ' . round($avg_ret, 2) . '%';
            _gm_create_alert($conn, $sys, 'negative_roi', 'warning',
                $sys . ': Average return negative (' . round($avg_ret, 1) . '%)',
                'The average return per trade is ' . round($avg_ret, 2) . '%, approaching the critical threshold.',
                '', $avg_ret, $WARN_AVG_RET, isset($page_urls[$sys]) ? $page_urls[$sys] : '');
            $alerts_created++;
        }

        // Zero picks in last 7 days for active systems
        $r7picks = $conn->query("SELECT COUNT(*) as cnt FROM gm_unified_picks
            WHERE source_system = '" . _gm_esc($conn, $sys) . "'
            AND pick_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)");
        $recent_count = 0;
        if ($r7picks && ($r7row = $r7picks->fetch_assoc())) { $recent_count = intval($r7row['cnt']); }
        if ($recent_count === 0 && intval($s['total']) > 0) {
            $fail_reasons[] = 'Zero picks in last 7 days';
            _gm_create_alert($conn, $sys, 'zero_picks', 'warning',
                $sys . ': No picks generated in 7 days',
                'This system has existing picks but generated zero new picks in the last 7 days. Data pipeline may be broken.',
                '', 0, 1, isset($page_urls[$sys]) ? $page_urls[$sys] : '');
            $alerts_created++;
        }

        // Per-algorithm underperformance within this system
        $algo_r = $conn->query("SELECT algorithm_name,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'tp_hit' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN status != 'open' THEN 1 ELSE 0 END) as closed,
            AVG(CASE WHEN status != 'open' THEN final_return_pct ELSE NULL END) as avg_ret
            FROM gm_unified_picks
            WHERE source_system = '" . _gm_esc($conn, $sys) . "'
            AND algorithm_name != '' AND status != 'open'
            AND pick_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY algorithm_name HAVING closed >= 3
            ORDER BY avg_ret ASC LIMIT 3");
        if ($algo_r) {
            while ($algo = $algo_r->fetch_assoc()) {
                $algo_closed = intval($algo['closed']);
                $algo_wins = intval($algo['wins']);
                $algo_wr = ($algo_closed > 0) ? round(($algo_wins / $algo_closed) * 100, 1) : 0;
                $algo_avg = floatval($algo['avg_ret']);
                if ($algo_wr < 20 && $algo_closed >= 5) {
                    _gm_create_alert($conn, $sys, 'algo_underperform', 'critical',
                        $sys . ': Algorithm "' . $algo['algorithm_name'] . '" failing (' . $algo_wr . '% win rate)',
                        'Algorithm "' . $algo['algorithm_name'] . '" has only a ' . $algo_wr . '% win rate across ' . $algo_closed . ' trades in the last 30 days. Average return: ' . round($algo_avg, 2) . '%. Consider disabling or re-tuning.',
                        '', $algo_wr, 20, isset($page_urls[$sys]) ? $page_urls[$sys] : '');
                    $alerts_created++;
                } elseif ($algo_wr < 35 && $algo_closed >= 5) {
                    _gm_create_alert($conn, $sys, 'algo_underperform', 'warning',
                        $sys . ': Algorithm "' . $algo['algorithm_name'] . '" underperforming (' . $algo_wr . '% win rate)',
                        'Algorithm "' . $algo['algorithm_name'] . '" has a ' . $algo_wr . '% win rate across ' . $algo_closed . ' trades. Average return: ' . round($algo_avg, 2) . '%.',
                        '', $algo_wr, 35, isset($page_urls[$sys]) ? $page_urls[$sys] : '');
                    $alerts_created++;
                }
            }
        }

        // Insert health snapshot
        $fail_text = implode('; ', $fail_reasons);
        $conn->query("REPLACE INTO gm_system_health
            (snap_date, source_system, total_picks, closed_picks, wins, losses, expired,
             win_rate, avg_return_pct, total_return_pct, avg_hold_hours,
             best_pick_ticker, best_pick_pct, worst_pick_ticker, worst_pick_pct,
             accuracy_7d, accuracy_30d, is_failing, failure_reason, created_at)
            VALUES (
             '" . $today . "', '" . _gm_esc($conn, $sys) . "',
             " . intval($s['total']) . ", " . $total_closed . ",
             " . $wins . ", " . $losses . ", " . intval($s['expired']) . ",
             " . $win_rate . ", " . round(floatval($s['avg_ret']), 4) . ",
             " . round(floatval($s['total_ret']), 4) . ",
             " . round(floatval($s['avg_hold']), 2) . ",
             '" . _gm_esc($conn, $best_t) . "', " . $best_pct . ",
             '" . _gm_esc($conn, $worst_t) . "', " . $worst_pct . ",
             " . $wr7 . ", " . $wr30 . ",
             " . $is_failing . ",
             '" . _gm_esc($conn, $fail_text) . "',
             '" . $now . "')");
        $health_snaps++;

        // Auto-resolve system-level alerts if system recovered (NOT per-algo alerts)
        if ($wr30 >= $WARN_WIN_RATE && $consec < $WARN_CONSEC) {
            $conn->query("UPDATE gm_failure_alerts SET is_active = 0, resolved_at = '" . $now . "'
                WHERE source_system = '" . _gm_esc($conn, $sys) . "' AND is_active = 1
                AND alert_type IN ('accuracy_drop', 'losing_streak', 'rapid_decline', 'negative_roi')");
        }
        // Auto-resolve algo_underperform only after 3 days (give algos time to recover)
        $conn->query("UPDATE gm_failure_alerts SET is_active = 0, resolved_at = '" . $now . "'
            WHERE source_system = '" . _gm_esc($conn, $sys) . "' AND is_active = 1
            AND alert_type = 'algo_underperform'
            AND alert_date < DATE_SUB(CURDATE(), INTERVAL 3 DAY)");
    }

    // ── Cross-system health checks ──

    // 1. Sports bankroll drawdown
    $alerts_created += _gm_check_sports_bankroll($conn);

    // 2. Conviction system accuracy
    $alerts_created += _gm_check_conviction_health($conn);

    // 3. Paper trading equity
    $alerts_created += _gm_check_paper_trading($conn);

    // 4. Overall portfolio health (all systems combined)
    $alerts_created += _gm_check_portfolio_health($conn);

    return array('health_snapshots' => $health_snaps, 'alerts_created' => $alerts_created);
}

// ── Sports Bankroll Drawdown Check ──
function _gm_check_sports_bankroll($conn) {
    global $now, $today;
    $created = 0;

    $sc = @new mysqli('mysql.50webs.com', 'ejaguiar1_sportsbet', 'eltonsportsbets', 'ejaguiar1_sportsbet');
    if ($sc->connect_error) return 0;

    // Current bankroll vs initial
    $INITIAL = 1000.00;
    $r = $sc->query("SELECT COALESCE(SUM(pnl), 0) as total_pnl FROM lm_sports_bets WHERE result IS NOT NULL");
    if (!$r) { $sc->close(); return 0; }
    $row = $r->fetch_assoc();
    $bankroll = $INITIAL + floatval($row['total_pnl']);
    $drawdown_pct = (($INITIAL - $bankroll) / $INITIAL) * 100;

    // Win rate
    $sr = $sc->query("SELECT
        COUNT(*) as total,
        SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins
        FROM lm_sports_bets WHERE result IS NOT NULL");
    $sports_wr = 0;
    $sports_total = 0;
    if ($sr && ($srow = $sr->fetch_assoc())) {
        $sports_total = intval($srow['total']);
        $swins = intval($srow['wins']);
        $sports_wr = ($sports_total > 0) ? round(($swins / $sports_total) * 100, 1) : 0;
    }

    // Recent streak (last 10)
    $streak_r = $sc->query("SELECT result FROM lm_sports_bets WHERE result IS NOT NULL ORDER BY settled_at DESC LIMIT 10");
    $consec_losses = 0;
    if ($streak_r) {
        while ($srow = $streak_r->fetch_assoc()) {
            if ($srow['result'] === 'loss') $consec_losses++;
            else break;
        }
    }

    $sc->close();

    // Bankroll drawdown alerts
    if ($drawdown_pct >= 30) {
        _gm_create_alert($conn, 'sports', 'bankroll_drawdown', 'critical',
            'Sports: Bankroll down ' . round($drawdown_pct, 1) . '% ($' . round($bankroll, 2) . ')',
            'Sports betting bankroll has drawn down ' . round($drawdown_pct, 1) . '% from $' . $INITIAL . ' to $' . round($bankroll, 2) . '. Consider pausing paper betting or reducing stake sizes.',
            '', $drawdown_pct, 30, '/live-monitor/sports-betting.html');
        $created++;
    } elseif ($drawdown_pct >= 15) {
        _gm_create_alert($conn, 'sports', 'bankroll_drawdown', 'warning',
            'Sports: Bankroll down ' . round($drawdown_pct, 1) . '% ($' . round($bankroll, 2) . ')',
            'Sports betting bankroll has drawn down ' . round($drawdown_pct, 1) . '% from initial $' . $INITIAL . '.',
            '', $drawdown_pct, 15, '/live-monitor/sports-betting.html');
        $created++;
    }

    // Sports win rate
    if ($sports_total >= 10 && $sports_wr < 40) {
        _gm_create_alert($conn, 'sports', 'accuracy_drop', 'warning',
            'Sports: Overall win rate low (' . $sports_wr . '% across ' . $sports_total . ' bets)',
            'Sports betting overall win rate is ' . $sports_wr . '%. Below 40% on value bets indicates model issues.',
            '', $sports_wr, 40, '/live-monitor/sports-betting.html');
        $created++;
    }

    // Sports losing streak
    if ($consec_losses >= 7) {
        _gm_create_alert($conn, 'sports', 'losing_streak', 'critical',
            'Sports: ' . $consec_losses . ' consecutive losses',
            'Sports betting has lost ' . $consec_losses . ' bets in a row.',
            '', $consec_losses, 7, '/live-monitor/sports-betting.html');
        $created++;
    }

    return $created;
}

// ── Conviction System Accuracy Check ──
function _gm_check_conviction_health($conn) {
    global $now, $today;
    $created = 0;

    // Check md_conviction_performance table exists
    $r = $conn->query("SHOW TABLES LIKE 'md_conviction_performance'");
    if (!$r || $r->num_rows === 0) return 0;

    // Overall conviction accuracy (30d)
    $pr = $conn->query("SELECT
        COUNT(*) as total,
        SUM(CASE WHEN outcome_30d = 'correct' THEN 1 ELSE 0 END) as correct,
        AVG(CASE WHEN return_30d IS NOT NULL THEN return_30d ELSE NULL END) as avg_ret
        FROM md_conviction_performance
        WHERE conviction_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        AND outcome_30d != 'pending'");
    if (!$pr) return 0;
    $row = $pr->fetch_assoc();
    $total = intval($row['total']);
    $correct = intval($row['correct']);
    $conv_wr = ($total > 0) ? round(($correct / $total) * 100, 1) : 0;
    $conv_avg_ret = floatval($row['avg_ret']);

    if ($total >= 5 && $conv_wr < 35) {
        _gm_create_alert($conn, 'conviction', 'accuracy_drop', 'critical',
            'Conviction: 30d accuracy only ' . $conv_wr . '% (' . $correct . '/' . $total . ')',
            'The conviction scoring system has a ' . $conv_wr . '% accuracy over the last 30 days. Average return: ' . round($conv_avg_ret, 2) . '%.',
            '', $conv_wr, 35, '/live-monitor/conviction-alerts.html');
        $created++;
    } elseif ($total >= 5 && $conv_wr < 50) {
        _gm_create_alert($conn, 'conviction', 'accuracy_drop', 'warning',
            'Conviction: 30d accuracy ' . $conv_wr . '% (' . $correct . '/' . $total . ')',
            'Conviction scoring accuracy is below 50%. Review scoring weights.',
            '', $conv_wr, 50, '/live-monitor/conviction-alerts.html');
        $created++;
    }

    // High-conviction picks failing (score >= 70 but bad outcome)
    $hc = $conn->query("SELECT
        COUNT(*) as total,
        SUM(CASE WHEN outcome_30d = 'correct' THEN 1 ELSE 0 END) as correct
        FROM md_conviction_performance
        WHERE conviction_score >= 70
        AND conviction_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        AND outcome_30d != 'pending'");
    if ($hc && ($hrow = $hc->fetch_assoc())) {
        $hc_total = intval($hrow['total']);
        $hc_correct = intval($hrow['correct']);
        $hc_wr = ($hc_total > 0) ? round(($hc_correct / $hc_total) * 100, 1) : 0;
        if ($hc_total >= 3 && $hc_wr < 45) {
            _gm_create_alert($conn, 'conviction', 'conviction_failing', 'critical',
                'High-conviction picks failing: only ' . $hc_wr . '% accurate (score >= 70)',
                'Picks with conviction score >= 70 are only ' . $hc_wr . '% accurate (' . $hc_correct . '/' . $hc_total . '). Scoring model may need recalibration.',
                '', $hc_wr, 45, '/live-monitor/conviction-alerts.html');
            $created++;
        }
    }

    return $created;
}

// ── Paper Trading Equity Check ──
function _gm_check_paper_trading($conn) {
    global $now, $today;
    $created = 0;

    $r = $conn->query("SHOW TABLES LIKE 'lm_trades'");
    if (!$r || $r->num_rows === 0) return 0;

    // 7-day paper trading P&L
    $pr = $conn->query("SELECT
        COUNT(*) as total,
        SUM(CASE WHEN realized_pct > 0 THEN 1 ELSE 0 END) as wins,
        SUM(realized_pct) as total_pnl,
        AVG(realized_pct) as avg_pnl
        FROM lm_trades WHERE status = 'closed'
        AND closed_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)");
    if (!$pr) return 0;
    $row = $pr->fetch_assoc();
    $total = intval($row['total']);
    $total_pnl = floatval($row['total_pnl']);
    $pt_wins = intval($row['wins']);
    $pt_wr = ($total > 0) ? round(($pt_wins / $total) * 100, 1) : 0;

    if ($total >= 5 && $total_pnl < -15) {
        _gm_create_alert($conn, 'paper_trading', 'drawdown', 'critical',
            'Paper Trading: 7d cumulative loss ' . round($total_pnl, 1) . '%',
            'Paper trading has lost a cumulative ' . round($total_pnl, 1) . '% across ' . $total . ' trades in 7 days. Win rate: ' . $pt_wr . '%.',
            '', $total_pnl, -15, '/live-monitor/live-monitor.html');
        $created++;
    } elseif ($total >= 5 && $total_pnl < -8) {
        _gm_create_alert($conn, 'paper_trading', 'drawdown', 'warning',
            'Paper Trading: 7d loss ' . round($total_pnl, 1) . '%',
            'Paper trading is down ' . round($total_pnl, 1) . '% this week. Win rate: ' . $pt_wr . '%.',
            '', $total_pnl, -8, '/live-monitor/live-monitor.html');
        $created++;
    }

    return $created;
}

// ── Overall Portfolio Health ──
function _gm_check_portfolio_health($conn) {
    global $now, $today;
    $created = 0;

    // Check how many systems are failing
    $r = $conn->query("SELECT COUNT(*) as failing FROM gm_system_health
        WHERE snap_date = '" . $today . "' AND is_failing = 1");
    if ($r && ($row = $r->fetch_assoc())) {
        $failing = intval($row['failing']);
        if ($failing >= 4) {
            _gm_create_alert($conn, 'portfolio', 'systemic_failure', 'critical',
                'Portfolio-wide: ' . $failing . ' systems failing simultaneously',
                $failing . ' prediction systems are flagged as failing on the same day. This may indicate a broad market regime change or data source outage.',
                '', $failing, 4, '/live-monitor/goldmine-dashboard.html');
            $created++;
        } elseif ($failing >= 2) {
            _gm_create_alert($conn, 'portfolio', 'systemic_failure', 'warning',
                'Portfolio: ' . $failing . ' systems underperforming',
                $failing . ' systems are showing issues. Monitor for correlation.',
                '', $failing, 2, '/live-monitor/goldmine-dashboard.html');
            $created++;
        }
    }

    // Open positions bleeding
    $neg = $conn->query("SELECT COUNT(*) as cnt, AVG(current_return_pct) as avg_ret
        FROM gm_unified_picks WHERE status = 'open' AND current_return_pct < -5");
    if ($neg && ($nrow = $neg->fetch_assoc())) {
        $neg_count = intval($nrow['cnt']);
        $neg_avg = floatval($nrow['avg_ret']);
        if ($neg_count >= 10) {
            _gm_create_alert($conn, 'portfolio', 'open_positions_bleeding', 'critical',
                'Portfolio: ' . $neg_count . ' open positions down >5% (avg: ' . round($neg_avg, 1) . '%)',
                $neg_count . ' currently open picks are in the red by more than 5%. Average unrealized loss: ' . round($neg_avg, 1) . '%.',
                '', $neg_count, 10, '/live-monitor/goldmine-dashboard.html');
            $created++;
        }
    }

    return $created;
}

function _gm_win_rate_period($conn, $sys, $days) {
    $r = $conn->query("SELECT
        SUM(CASE WHEN status = 'tp_hit' THEN 1 ELSE 0 END) as tp_wins,
        SUM(CASE WHEN status IN ('max_hold','expired') AND final_return_pct > 0 THEN 1 ELSE 0 END) as expired_wins,
        SUM(CASE WHEN status != 'open' THEN 1 ELSE 0 END) as closed
        FROM gm_unified_picks
        WHERE source_system = '" . _gm_esc($conn, $sys) . "'
        AND pick_date >= DATE_SUB(CURDATE(), INTERVAL " . intval($days) . " DAY)
        AND status != 'open'");
    if (!$r || $r->num_rows === 0) return 0;
    $row = $r->fetch_assoc();
    $closed = intval($row['closed']);
    if ($closed === 0) return 0;
    $wins = intval($row['tp_wins']) + intval($row['expired_wins']);
    return round(($wins / $closed) * 100, 1);
}

function _gm_consecutive_losses($conn, $sys) {
    $r = $conn->query("SELECT status FROM gm_unified_picks
        WHERE source_system = '" . _gm_esc($conn, $sys) . "' AND status != 'open'
        ORDER BY exit_date DESC, id DESC LIMIT 20");
    if (!$r) return 0;
    $consec = 0;
    while ($row = $r->fetch_assoc()) {
        if ($row['status'] === 'sl_hit') { $consec++; }
        else { break; }
    }
    return $consec;
}

function _gm_create_alert($conn, $sys, $type, $severity, $title, $desc, $tickers, $metric, $threshold, $url) {
    global $now, $today;
    // Check for existing alert for same system+type+date
    $dup = $conn->query("SELECT id, is_active FROM gm_failure_alerts
        WHERE source_system = '" . _gm_esc($conn, $sys) . "'
        AND alert_type = '" . _gm_esc($conn, $type) . "'
        AND alert_date = '" . $today . "'");
    if ($dup && $dup->num_rows > 0) {
        $existing = $dup->fetch_assoc();
        // If alert was resolved, reactivate it with updated data
        if (intval($existing['is_active']) === 0) {
            $conn->query("UPDATE gm_failure_alerts SET
                is_active = 1, resolved_at = NULL,
                severity = '" . _gm_esc($conn, $severity) . "',
                title = '" . _gm_esc($conn, $title) . "',
                description = '" . _gm_esc($conn, $desc) . "',
                metric_value = " . floatval($metric) . ",
                threshold_value = " . floatval($threshold) . "
                WHERE id = " . intval($existing['id']));
        }
        return;
    }

    $conn->query("INSERT INTO gm_failure_alerts
        (alert_date, source_system, alert_type, severity, title, description,
         affected_tickers, metric_value, threshold_value, page_url, is_active, created_at)
        VALUES (
         '" . $today . "', '" . _gm_esc($conn, $sys) . "',
         '" . _gm_esc($conn, $type) . "', '" . _gm_esc($conn, $severity) . "',
         '" . _gm_esc($conn, $title) . "', '" . _gm_esc($conn, $desc) . "',
         '" . _gm_esc($conn, $tickers) . "',
         " . floatval($metric) . ", " . floatval($threshold) . ",
         '" . _gm_esc($conn, $url) . "', 1, '" . $now . "')");
}
?>
