<?php
/**
 * command_center.php — Unified Command Center Stats API
 * Aggregates performance data from all 6 asset classes.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   ?action=stats     — Full aggregated stats (public, cached 5 min)
 *   ?action=summary   — Lightweight summary for nav badges (public, cached 2 min)
 *   ?action=refresh&key=livetrader2026 — Force-refresh cache (admin)
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

require_once dirname(__FILE__) . '/db_config.php';

// Primary DB connection (stocks, crypto, forex, consensus, paper trading)
$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'DB connection failed'));
    exit;
}
$conn->set_charset('utf8');

// Sports DB connection
$sports_conn = @new mysqli($sports_servername, $sports_username, $sports_password, $sports_dbname);
$sports_ok = ($sports_conn && !$sports_conn->connect_error);
if ($sports_ok) $sports_conn->set_charset('utf8');

$action = isset($_GET['action']) ? $_GET['action'] : 'stats';
$key    = isset($_GET['key'])    ? $_GET['key']    : '';
$admin  = ($key === 'livetrader2026');
$now    = date('Y-m-d H:i:s');

// ── Cache helper ──
$CACHE_DIR = dirname(__FILE__) . '/cache/';
if (!is_dir($CACHE_DIR)) { @mkdir($CACHE_DIR, 0755, true); }

function _cc_cache_get($key, $ttl_sec) {
    global $CACHE_DIR;
    $f = $CACHE_DIR . 'cc_' . md5($key) . '.json';
    if (file_exists($f) && (time() - filemtime($f)) < $ttl_sec) {
        $d = @file_get_contents($f);
        if ($d !== false) return json_decode($d, true);
    }
    return false;
}

function _cc_cache_set($key, $data) {
    global $CACHE_DIR;
    $f = $CACHE_DIR . 'cc_' . md5($key) . '.json';
    @file_put_contents($f, json_encode($data));
}

// ── Escape helper ──
function _cc_esc($conn, $val) {
    return $conn->real_escape_string($val);
}

// ── Safe extraction helpers ──
function _cc_int($row, $key) {
    return isset($row[$key]) ? intval($row[$key]) : 0;
}

function _cc_float($row, $key, $decimals) {
    return isset($row[$key]) ? round(floatval($row[$key]), $decimals) : 0;
}

// ────────────────────────────────────────────────────────────
//  DATA FUNCTIONS
// ────────────────────────────────────────────────────────────

/**
 * Paper trading stats for a given asset class from lm_trades
 */
function _cc_get_paper_trading_stats($conn, $asset_class) {
    $defaults = array(
        'total_trades' => 0, 'wins' => 0, 'losses' => 0,
        'win_rate' => 0, 'total_pnl' => 0, 'open_positions' => 0,
        'avg_pnl_per_trade' => 0
    );
    $ac = _cc_esc($conn, $asset_class);
    $r = @$conn->query("SELECT
        COUNT(*) as total_trades,
        SUM(CASE WHEN status='closed' AND realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN status='closed' AND realized_pnl_usd <= 0 THEN 1 ELSE 0 END) as losses,
        SUM(CASE WHEN status='closed' THEN realized_pnl_usd ELSE 0 END) as total_pnl,
        SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) as open_positions,
        AVG(CASE WHEN status='closed' THEN realized_pnl_usd ELSE NULL END) as avg_pnl
        FROM lm_trades WHERE asset_class='" . $ac . "'");
    if (!$r) return $defaults;
    $row = $r->fetch_assoc();
    if (!$row) return $defaults;
    $wins   = _cc_int($row, 'wins');
    $losses = _cc_int($row, 'losses');
    $closed = $wins + $losses;
    return array(
        'total_trades'      => _cc_int($row, 'total_trades'),
        'wins'              => $wins,
        'losses'            => $losses,
        'win_rate'          => ($closed > 0) ? round(($wins / $closed) * 100, 1) : 0,
        'total_pnl'         => _cc_float($row, 'total_pnl', 2),
        'open_positions'    => _cc_int($row, 'open_positions'),
        'avg_pnl_per_trade' => _cc_float($row, 'avg_pnl', 2)
    );
}

/**
 * Consensus picks stats from consensus_tracked
 */
function _cc_get_consensus_stats($conn) {
    $defaults = array(
        'total' => 0, 'open' => 0, 'closed' => 0,
        'wins' => 0, 'losses' => 0, 'win_rate' => 0,
        'avg_return' => 0, 'total_return' => 0
    );
    $r = @$conn->query("SELECT
        COUNT(*) as total_positions,
        SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) as open_positions,
        SUM(CASE WHEN status LIKE 'closed%' THEN 1 ELSE 0 END) as closed_positions,
        SUM(CASE WHEN status='closed_win' THEN 1 ELSE 0 END) as consensus_wins,
        SUM(CASE WHEN status='closed_loss' THEN 1 ELSE 0 END) as consensus_losses,
        AVG(CASE WHEN status LIKE 'closed%' THEN final_return_pct ELSE NULL END) as avg_return,
        SUM(CASE WHEN status LIKE 'closed%' THEN final_return_pct ELSE 0 END) as total_return
        FROM consensus_tracked");
    if (!$r) return $defaults;
    $row = $r->fetch_assoc();
    if (!$row) return $defaults;
    $wins   = _cc_int($row, 'consensus_wins');
    $closed = _cc_int($row, 'closed_positions');
    return array(
        'total'        => _cc_int($row, 'total_positions'),
        'open'         => _cc_int($row, 'open_positions'),
        'closed'       => $closed,
        'wins'         => $wins,
        'losses'       => _cc_int($row, 'consensus_losses'),
        'win_rate'     => ($closed > 0) ? round(($wins / $closed) * 100, 1) : 0,
        'avg_return'   => _cc_float($row, 'avg_return', 2),
        'total_return' => _cc_float($row, 'total_return', 2)
    );
}

/**
 * Active signals grouped by asset_class from lm_signals
 */
function _cc_get_signals_by_class($conn) {
    $out = array('STOCK' => 0, 'CRYPTO' => 0, 'FOREX' => 0);
    $r = @$conn->query("SELECT asset_class, COUNT(*) as active_signals
        FROM lm_signals WHERE status='active' AND expires_at > NOW()
        GROUP BY asset_class");
    if (!$r) return $out;
    while ($row = $r->fetch_assoc()) {
        $ac = strtoupper($row['asset_class']);
        $out[$ac] = _cc_int($row, 'active_signals');
    }
    return $out;
}

/**
 * Goldmine unified picks stats grouped by source_system
 */
function _cc_get_goldmine_stats($conn) {
    $systems = array();
    $r = @$conn->query("SELECT source_system,
        COUNT(*) as total_picks,
        SUM(CASE WHEN status != 'open' THEN 1 ELSE 0 END) as closed,
        SUM(CASE WHEN status = 'tp_hit' THEN 1 ELSE 0 END) as tp_wins,
        SUM(CASE WHEN status IN ('max_hold','expired') AND final_return_pct > 0 THEN 1 ELSE 0 END) as expired_wins,
        SUM(CASE WHEN status = 'sl_hit' THEN 1 ELSE 0 END) as losses,
        AVG(CASE WHEN status != 'open' THEN final_return_pct ELSE NULL END) as avg_return,
        SUM(CASE WHEN status != 'open' THEN final_return_pct ELSE 0 END) as total_return
        FROM gm_unified_picks GROUP BY source_system ORDER BY source_system");
    if (!$r) return $systems;
    while ($row = $r->fetch_assoc()) {
        $closed = _cc_int($row, 'closed');
        $wins   = _cc_int($row, 'tp_wins') + _cc_int($row, 'expired_wins');
        $systems[] = array(
            'source_system' => $row['source_system'],
            'total_picks'   => _cc_int($row, 'total_picks'),
            'closed'        => $closed,
            'wins'          => $wins,
            'losses'        => _cc_int($row, 'losses'),
            'win_rate'      => ($closed > 0) ? round(($wins / $closed) * 100, 1) : 0,
            'avg_return'    => _cc_float($row, 'avg_return', 2),
            'total_return'  => _cc_float($row, 'total_return', 2)
        );
    }
    return $systems;
}

/**
 * Active failure alerts count
 */
function _cc_get_alert_count($conn) {
    $r = @$conn->query("SELECT COUNT(*) as cnt FROM gm_failure_alerts WHERE is_active = 1");
    if (!$r) return 0;
    $row = $r->fetch_assoc();
    return $row ? _cc_int($row, 'cnt') : 0;
}

/**
 * Sports betting stats from lm_sports_bets (separate DB)
 */
function _cc_get_sports_stats($sports_conn, $sports_ok) {
    $defaults = array(
        'total_bets' => 0, 'wins' => 0, 'losses' => 0, 'pending' => 0,
        'win_rate' => 0, 'total_pnl' => 0, 'total_wagered' => 0, 'roi_pct' => 0
    );
    if (!$sports_ok) return $defaults;
    $r = @$sports_conn->query("SELECT
        COUNT(*) as total_bets,
        SUM(CASE WHEN result='won' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN result='lost' THEN 1 ELSE 0 END) as losses,
        SUM(CASE WHEN status='pending' OR status='active' THEN 1 ELSE 0 END) as pending,
        SUM(CASE WHEN pnl IS NOT NULL THEN pnl ELSE 0 END) as total_pnl,
        SUM(bet_amount) as total_wagered
        FROM lm_sports_bets");
    if (!$r) return $defaults;
    $row = $r->fetch_assoc();
    if (!$row) return $defaults;
    $wins    = _cc_int($row, 'wins');
    $losses  = _cc_int($row, 'losses');
    $settled = $wins + $losses;
    $wagered = _cc_float($row, 'total_wagered', 2);
    $pnl     = _cc_float($row, 'total_pnl', 2);
    return array(
        'total_bets'    => _cc_int($row, 'total_bets'),
        'wins'          => $wins,
        'losses'        => $losses,
        'pending'       => _cc_int($row, 'pending'),
        'win_rate'      => ($settled > 0) ? round(($wins / $settled) * 100, 1) : 0,
        'total_pnl'     => $pnl,
        'total_wagered' => $wagered,
        'roi_pct'       => ($wagered > 0) ? round(($pnl / $wagered) * 100, 2) : 0
    );
}

/**
 * Penny stock stats from gm_unified_picks WHERE source_system = 'penny_stock'
 */
function _cc_get_penny_stats($conn) {
    $defaults = array(
        'total_picks' => 0, 'closed' => 0, 'wins' => 0,
        'win_rate' => 0, 'avg_return' => 0
    );
    $r = @$conn->query("SELECT
        COUNT(*) as total_picks,
        SUM(CASE WHEN status != 'open' THEN 1 ELSE 0 END) as closed,
        SUM(CASE WHEN status = 'tp_hit' THEN 1 ELSE 0 END) as tp_wins,
        SUM(CASE WHEN status IN ('max_hold','expired') AND final_return_pct > 0 THEN 1 ELSE 0 END) as expired_wins,
        AVG(CASE WHEN status != 'open' THEN final_return_pct ELSE NULL END) as avg_return
        FROM gm_unified_picks WHERE source_system = 'penny_stock'");
    if (!$r) return $defaults;
    $row = $r->fetch_assoc();
    if (!$row) return $defaults;
    $closed = _cc_int($row, 'closed');
    $wins   = _cc_int($row, 'tp_wins') + _cc_int($row, 'expired_wins');
    return array(
        'total_picks' => _cc_int($row, 'total_picks'),
        'closed'      => $closed,
        'wins'        => $wins,
        'win_rate'    => ($closed > 0) ? round(($wins / $closed) * 100, 1) : 0,
        'avg_return'  => _cc_float($row, 'avg_return', 2)
    );
}

/**
 * Meme coin stats from gm_unified_picks WHERE source_system = 'meme'
 */
function _cc_get_meme_stats($conn) {
    $defaults = array(
        'total_picks' => 0, 'closed' => 0, 'wins' => 0,
        'win_rate' => 0, 'avg_return' => 0
    );
    $r = @$conn->query("SELECT
        COUNT(*) as total_picks,
        SUM(CASE WHEN status != 'open' THEN 1 ELSE 0 END) as closed,
        SUM(CASE WHEN status = 'tp_hit' THEN 1 ELSE 0 END) as tp_wins,
        SUM(CASE WHEN status IN ('max_hold','expired') AND final_return_pct > 0 THEN 1 ELSE 0 END) as expired_wins,
        AVG(CASE WHEN status != 'open' THEN final_return_pct ELSE NULL END) as avg_return
        FROM gm_unified_picks WHERE source_system = 'meme'");
    if (!$r) return $defaults;
    $row = $r->fetch_assoc();
    if (!$row) return $defaults;
    $closed = _cc_int($row, 'closed');
    $wins   = _cc_int($row, 'tp_wins') + _cc_int($row, 'expired_wins');
    return array(
        'total_picks' => _cc_int($row, 'total_picks'),
        'closed'      => $closed,
        'wins'        => $wins,
        'win_rate'    => ($closed > 0) ? round(($wins / $closed) * 100, 1) : 0,
        'avg_return'  => _cc_float($row, 'avg_return', 2)
    );
}

/**
 * Recent activity — last 10 events across trades, signals, and sports bets
 * Merges from multiple sources and sorts by timestamp
 */
function _cc_get_recent_activity($conn, $sports_conn, $sports_ok) {
    $events = array();

    // Recent closed trades from lm_trades
    $r = @$conn->query("SELECT symbol, asset_class, direction, realized_pnl_usd, realized_pct,
        exit_reason, exit_time as event_time
        FROM lm_trades WHERE status='closed' ORDER BY exit_time DESC LIMIT 5");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $events[] = array(
                'type'       => 'trade_closed',
                'asset'      => $row['asset_class'],
                'symbol'     => $row['symbol'],
                'detail'     => $row['direction'] . ' ' . $row['exit_reason'],
                'pnl'        => _cc_float($row, 'realized_pnl_usd', 2),
                'pnl_pct'    => _cc_float($row, 'realized_pct', 2),
                'event_time' => $row['event_time']
            );
        }
    }

    // Recent active signals from lm_signals
    $r = @$conn->query("SELECT symbol, asset_class, algorithm_name, signal_type,
        signal_strength, signal_time as event_time
        FROM lm_signals WHERE status='active' ORDER BY signal_time DESC LIMIT 5");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $events[] = array(
                'type'       => 'signal',
                'asset'      => $row['asset_class'],
                'symbol'     => $row['symbol'],
                'detail'     => $row['algorithm_name'] . ' ' . $row['signal_type'] . ' (str:' . $row['signal_strength'] . ')',
                'pnl'        => null,
                'pnl_pct'    => null,
                'event_time' => $row['event_time']
            );
        }
    }

    // Recent settled sports bets
    if ($sports_ok) {
        $r = @$sports_conn->query("SELECT sport, pick, result, pnl, bet_amount,
            settled_at as event_time
            FROM lm_sports_bets WHERE result IS NOT NULL ORDER BY settled_at DESC LIMIT 5");
        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $amt = floatval($row['bet_amount']);
                $events[] = array(
                    'type'       => 'sports_bet',
                    'asset'      => 'SPORTS',
                    'symbol'     => $row['sport'],
                    'detail'     => $row['pick'] . ' - ' . $row['result'],
                    'pnl'        => _cc_float($row, 'pnl', 2),
                    'pnl_pct'    => ($amt > 0) ? round((floatval($row['pnl']) / $amt) * 100, 1) : 0,
                    'event_time' => $row['event_time']
                );
            }
        }
    }

    // Sort by event_time descending, take top 10
    usort($events, '_cc_sort_by_time');
    return array_slice($events, 0, 10);
}

/**
 * Sort helper for recent activity (newest first)
 */
function _cc_sort_by_time($a, $b) {
    $ta = isset($a['event_time']) ? $a['event_time'] : '';
    $tb = isset($b['event_time']) ? $b['event_time'] : '';
    if ($ta === $tb) return 0;
    return ($ta > $tb) ? -1 : 1;
}

/**
 * Calculate overall aggregates from all asset class data
 */
function _cc_calc_overall($stocks_pt, $crypto_pt, $forex_pt, $consensus, $sports, $penny, $meme) {
    // Total closed trades across paper trading
    $pt_closed = ($stocks_pt['wins'] + $stocks_pt['losses'])
               + ($crypto_pt['wins'] + $crypto_pt['losses'])
               + ($forex_pt['wins'] + $forex_pt['losses']);
    $pt_wins   = $stocks_pt['wins'] + $crypto_pt['wins'] + $forex_pt['wins'];

    // Add consensus, sports, goldmine subsets
    $total_closed = $pt_closed + $consensus['closed']
                  + ($sports['wins'] + $sports['losses'])
                  + $penny['closed'] + $meme['closed'];
    $total_wins   = $pt_wins + $consensus['wins'] + $sports['wins']
                  + $penny['wins'] + $meme['wins'];

    // Total PnL (USD-denominated systems only)
    $total_pnl = $stocks_pt['total_pnl'] + $crypto_pt['total_pnl']
               + $forex_pt['total_pnl'] + $sports['total_pnl'];

    // Count positive asset classes
    $positive = 0;
    if ($stocks_pt['total_pnl'] > 0 || $consensus['avg_return'] > 0) $positive++;
    if ($crypto_pt['total_pnl'] > 0) $positive++;
    if ($forex_pt['total_pnl'] > 0) $positive++;
    if ($sports['total_pnl'] > 0) $positive++;
    if ($penny['avg_return'] > 0) $positive++;
    if ($meme['avg_return'] > 0) $positive++;

    return array(
        'total_asset_classes'    => 6,
        'asset_classes_positive' => $positive,
        'total_closed_trades'    => $total_closed,
        'total_wins'             => $total_wins,
        'overall_win_rate'       => ($total_closed > 0) ? round(($total_wins / $total_closed) * 100, 1) : 0,
        'total_pnl_usd'         => round($total_pnl, 2)
    );
}

// ────────────────────────────────────────────────────────────
//  ACTION: refresh (admin only)
// ────────────────────────────────────────────────────────────

if ($action === 'refresh') {
    if (!$admin) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Unauthorized'));
        $conn->close();
        if ($sports_ok) $sports_conn->close();
        exit;
    }
    // Delete all command center cache files
    $files = glob($CACHE_DIR . 'cc_*.json');
    $deleted = 0;
    if ($files) {
        foreach ($files as $cf) {
            if (@unlink($cf)) $deleted++;
        }
    }
    // Rebuild stats cache immediately
    $stocks_pt  = _cc_get_paper_trading_stats($conn, 'STOCK');
    $crypto_pt  = _cc_get_paper_trading_stats($conn, 'CRYPTO');
    $forex_pt   = _cc_get_paper_trading_stats($conn, 'FOREX');
    $consensus  = _cc_get_consensus_stats($conn);
    $signals    = _cc_get_signals_by_class($conn);
    $goldmine   = _cc_get_goldmine_stats($conn);
    $alerts     = _cc_get_alert_count($conn);
    $sports     = _cc_get_sports_stats($sports_conn, $sports_ok);
    $penny      = _cc_get_penny_stats($conn);
    $meme       = _cc_get_meme_stats($conn);
    $activity   = _cc_get_recent_activity($conn, $sports_conn, $sports_ok);

    $total_signals = 0;
    foreach ($signals as $cnt) { $total_signals += $cnt; }

    $overall = _cc_calc_overall($stocks_pt, $crypto_pt, $forex_pt, $consensus, $sports, $penny, $meme);
    $overall['active_signals'] = $total_signals;
    $overall['active_alerts']  = $alerts;
    $overall['active_positions'] = $stocks_pt['open_positions'] + $crypto_pt['open_positions'] + $forex_pt['open_positions'];

    $data = array(
        'ok'           => true,
        'action'       => 'refresh',
        'generated_at' => $now,
        'from_cache'   => false,
        'cache_files_deleted' => $deleted,
        'overall'      => $overall,
        'asset_classes' => array(
            'stocks' => array(
                'scope' => 'STOCKS', 'label' => 'Stocks & ETFs',
                'paper_trading' => $stocks_pt, 'consensus' => $consensus,
                'active_signals' => isset($signals['STOCK']) ? $signals['STOCK'] : 0
            ),
            'crypto' => array(
                'scope' => 'CRYPTO', 'label' => 'Cryptocurrency',
                'paper_trading' => $crypto_pt,
                'active_signals' => isset($signals['CRYPTO']) ? $signals['CRYPTO'] : 0
            ),
            'meme_coins' => array(
                'scope' => 'MEME', 'label' => 'Meme Coins',
                'goldmine_stats' => $meme
            ),
            'forex' => array(
                'scope' => 'FOREX', 'label' => 'Forex',
                'paper_trading' => $forex_pt,
                'active_signals' => isset($signals['FOREX']) ? $signals['FOREX'] : 0
            ),
            'sports' => array(
                'scope' => 'SPORTS', 'label' => 'Sports Betting',
                'betting_stats' => $sports
            ),
            'penny_stocks' => array(
                'scope' => 'PENNY', 'label' => 'Penny Stocks',
                'goldmine_stats' => $penny
            )
        ),
        'goldmine'        => $goldmine,
        'recent_activity' => $activity
    );
    _cc_cache_set('stats', $data);
    echo json_encode($data);
    $conn->close();
    if ($sports_ok) $sports_conn->close();
    exit;
}

// ────────────────────────────────────────────────────────────
//  ACTION: stats (public, 300s cache)
// ────────────────────────────────────────────────────────────

if ($action === 'stats') {
    $cached = _cc_cache_get('stats', 300);
    if ($cached && !$admin) {
        $cached['from_cache'] = true;
        echo json_encode($cached);
        $conn->close();
        if ($sports_ok) $sports_conn->close();
        exit;
    }

    // Gather all data
    $stocks_pt  = _cc_get_paper_trading_stats($conn, 'STOCK');
    $crypto_pt  = _cc_get_paper_trading_stats($conn, 'CRYPTO');
    $forex_pt   = _cc_get_paper_trading_stats($conn, 'FOREX');
    $consensus  = _cc_get_consensus_stats($conn);
    $signals    = _cc_get_signals_by_class($conn);
    $goldmine   = _cc_get_goldmine_stats($conn);
    $alerts     = _cc_get_alert_count($conn);
    $sports     = _cc_get_sports_stats($sports_conn, $sports_ok);
    $penny      = _cc_get_penny_stats($conn);
    $meme       = _cc_get_meme_stats($conn);
    $activity   = _cc_get_recent_activity($conn, $sports_conn, $sports_ok);

    // Total active signals
    $total_signals = 0;
    foreach ($signals as $cnt) { $total_signals += $cnt; }

    // Overall aggregates
    $overall = _cc_calc_overall($stocks_pt, $crypto_pt, $forex_pt, $consensus, $sports, $penny, $meme);
    $overall['active_signals'] = $total_signals;
    $overall['active_alerts']  = $alerts;

    $data = array(
        'ok'           => true,
        'action'       => 'stats',
        'generated_at' => $now,
        'from_cache'   => false,
        'overall'      => $overall,
        'asset_classes' => array(
            'stocks' => array(
                'scope' => 'STOCKS',
                'label' => 'Stocks & ETFs',
                'paper_trading'  => $stocks_pt,
                'consensus'      => $consensus,
                'active_signals' => isset($signals['STOCK']) ? $signals['STOCK'] : 0,
                'links' => array(
                    array('text' => 'Consolidated Picks', 'href' => '/findstocks/portfolio2/consolidated.html'),
                    array('text' => 'Dashboard', 'href' => '/findstocks/portfolio2/dashboard.html'),
                    array('text' => 'Dividends', 'href' => '/findstocks/portfolio2/dividends.html'),
                    array('text' => 'Smart Money', 'href' => '/findstocks/portfolio2/smart-money.html')
                )
            ),
            'crypto' => array(
                'scope' => 'CRYPTO',
                'label' => 'Cryptocurrency',
                'paper_trading'  => $crypto_pt,
                'active_signals' => isset($signals['CRYPTO']) ? $signals['CRYPTO'] : 0,
                'links' => array(
                    array('text' => 'Crypto Winners', 'href' => '/findcryptopairs/winners.html')
                )
            ),
            'meme_coins' => array(
                'scope' => 'MEME',
                'label' => 'Meme Coins',
                'goldmine_stats' => $meme,
                'links' => array(
                    array('text' => 'Meme Scanner', 'href' => '/findcryptopairs/meme-scanner.html')
                )
            ),
            'forex' => array(
                'scope' => 'FOREX',
                'label' => 'Forex',
                'paper_trading'  => $forex_pt,
                'active_signals' => isset($signals['FOREX']) ? $signals['FOREX'] : 0,
                'links' => array(
                    array('text' => 'Live Monitor', 'href' => '/live-monitor/')
                )
            ),
            'sports' => array(
                'scope' => 'SPORTS',
                'label' => 'Sports Betting',
                'betting_stats' => $sports,
                'links' => array(
                    array('text' => 'Sports Dashboard', 'href' => '/live-monitor/sports-dashboard.html')
                )
            ),
            'penny_stocks' => array(
                'scope' => 'PENNY',
                'label' => 'Penny Stocks',
                'goldmine_stats' => $penny,
                'links' => array(
                    array('text' => 'Penny Finder', 'href' => '/findstocks/tools.html')
                )
            )
        ),
        'goldmine'        => $goldmine,
        'recent_activity' => $activity
    );

    _cc_cache_set('stats', $data);
    echo json_encode($data);
    $conn->close();
    if ($sports_ok) $sports_conn->close();
    exit;
}

// ────────────────────────────────────────────────────────────
//  ACTION: summary (public, 120s cache)
// ────────────────────────────────────────────────────────────

if ($action === 'summary') {
    $cached = _cc_cache_get('summary', 120);
    if ($cached && !$admin) {
        $cached['from_cache'] = true;
        echo json_encode($cached);
        $conn->close();
        if ($sports_ok) $sports_conn->close();
        exit;
    }

    // Lightweight queries — just key metrics per asset class
    $stocks_pt = _cc_get_paper_trading_stats($conn, 'STOCK');
    $crypto_pt = _cc_get_paper_trading_stats($conn, 'CRYPTO');
    $forex_pt  = _cc_get_paper_trading_stats($conn, 'FOREX');
    $sports    = _cc_get_sports_stats($sports_conn, $sports_ok);
    $signals   = _cc_get_signals_by_class($conn);
    $alerts    = _cc_get_alert_count($conn);

    // Consensus — just open/closed/win_rate
    $con_open = 0; $con_closed = 0; $con_wr = 0;
    $r = @$conn->query("SELECT
        SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) as o,
        SUM(CASE WHEN status LIKE 'closed%' THEN 1 ELSE 0 END) as c,
        SUM(CASE WHEN status='closed_win' THEN 1 ELSE 0 END) as w
        FROM consensus_tracked");
    if ($r && ($row = $r->fetch_assoc())) {
        $con_open   = _cc_int($row, 'o');
        $con_closed = _cc_int($row, 'c');
        $con_wins   = _cc_int($row, 'w');
        $con_wr     = ($con_closed > 0) ? round(($con_wins / $con_closed) * 100, 1) : 0;
    }

    $total_signals = 0;
    foreach ($signals as $cnt) { $total_signals += $cnt; }

    $data = array(
        'ok'           => true,
        'action'       => 'summary',
        'generated_at' => $now,
        'from_cache'   => false,
        'badges' => array(
            'stocks' => array(
                'pnl'            => $stocks_pt['total_pnl'],
                'win_rate'       => $stocks_pt['win_rate'],
                'open'           => $stocks_pt['open_positions'],
                'consensus_open' => $con_open,
                'consensus_wr'   => $con_wr,
                'signals'        => isset($signals['STOCK']) ? $signals['STOCK'] : 0
            ),
            'crypto' => array(
                'pnl'      => $crypto_pt['total_pnl'],
                'win_rate' => $crypto_pt['win_rate'],
                'open'     => $crypto_pt['open_positions'],
                'signals'  => isset($signals['CRYPTO']) ? $signals['CRYPTO'] : 0
            ),
            'forex' => array(
                'pnl'      => $forex_pt['total_pnl'],
                'win_rate' => $forex_pt['win_rate'],
                'open'     => $forex_pt['open_positions'],
                'signals'  => isset($signals['FOREX']) ? $signals['FOREX'] : 0
            ),
            'sports' => array(
                'pnl'      => $sports['total_pnl'],
                'win_rate' => $sports['win_rate'],
                'pending'  => $sports['pending']
            ),
            'alerts'        => $alerts,
            'total_signals' => $total_signals
        )
    );

    _cc_cache_set('summary', $data);
    echo json_encode($data);
    $conn->close();
    if ($sports_ok) $sports_conn->close();
    exit;
}

// ────────────────────────────────────────────────────────────
//  Unknown action fallback
// ────────────────────────────────────────────────────────────

header('HTTP/1.0 400 Bad Request');
echo json_encode(array(
    'ok' => false,
    'error' => 'Unknown action: ' . $action,
    'valid_actions' => array('stats', 'summary', 'refresh')
));
$conn->close();
if ($sports_ok) $sports_conn->close();
?>
