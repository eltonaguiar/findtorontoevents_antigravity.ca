<?php
/**
 * Daily Picks Aggregation API — Crypto, Forex & Stocks
 * Serves daily picks from the Live Trading Monitor's 19-algorithm signal engine.
 * PHP 5.2 compatible (no short arrays, no http_response_code, no spread operator).
 *
 * Actions (public):
 *   ?action=crypto    — Active crypto picks
 *   ?action=forex     — Active forex picks
 *   ?action=stocks    — Active stock picks
 *   ?action=momentum  — Highest-conviction picks across all assets
 *   ?action=wins      — Recent winning trades
 *   ?action=all       — All asset classes combined
 *
 * Filters:
 *   &timeline=scalp|daytrader|swing|all   — Filter by hold time
 *   &budget=small|medium|large            — Position sizing guidance
 *   &min_strength=0-100                   — Minimum signal strength
 *
 * Data sources (all existing, no new data pipelines):
 *   lm_signals     — Active BUY signals from 19 algorithms
 *   lm_trades      — Closed trades with realized PnL
 *   lm_price_cache — Latest prices
 */

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'all';
$timeline = isset($_GET['timeline']) ? strtolower(trim($_GET['timeline'])) : 'all';
$budget = isset($_GET['budget']) ? strtolower(trim($_GET['budget'])) : '';
$min_strength = isset($_GET['min_strength']) ? max(0, min(100, (int)$_GET['min_strength'])) : 0;

// ─── Timeline mapping (max_hold_hours) ──────────────────────
function _dp_timeline_filter($timeline) {
    if ($timeline === 'scalp')     return 4;
    if ($timeline === 'daytrader') return 24;
    if ($timeline === 'swing')     return 168;
    return 0; // 'all' — no filter
}

function _dp_timeline_category($max_hold_hours) {
    if ($max_hold_hours <= 4)   return 'scalp';
    if ($max_hold_hours <= 24)  return 'daytrader';
    if ($max_hold_hours <= 168) return 'swing';
    return 'position';
}

function _dp_timeline_label($cat) {
    if ($cat === 'scalp')     return 'Scalp (1-4 hours)';
    if ($cat === 'daytrader') return 'Day Trade (4-24 hours)';
    if ($cat === 'swing')     return 'Swing (1-7 days)';
    if ($cat === 'position')  return 'Position (7+ days)';
    return 'All timeframes';
}

// ─── Budget guidance ────────────────────────────────────────
function _dp_budget_guidance($budget) {
    $guidance = array(
        'small'  => 'Position size: $25-50 per trade, max 3 open positions. Use tight stop-losses. Focus on crypto with low minimum order sizes.',
        'medium' => 'Position size: $250-500 per trade, max 5 open positions. Diversify across asset classes. Standard stop-losses.',
        'large'  => 'Position size: $500-2,500 per trade, max 10 open positions. Full diversification. Consider scaling into positions.'
    );
    if ($budget && isset($guidance[$budget])) {
        return array(
            'selected' => $budget,
            'guidance'  => $guidance[$budget]
        );
    }
    return array(
        'small'  => $guidance['small'],
        'medium' => $guidance['medium'],
        'large'  => $guidance['large']
    );
}

// ─── Fetch active signals by asset class ────────────────────
function _dp_get_picks($conn, $asset_class, $timeline, $min_strength) {
    $now = date('Y-m-d H:i:s');
    $where = "status='active' AND expires_at > '" . $conn->real_escape_string($now) . "'";

    if ($asset_class !== '') {
        $where .= " AND asset_class='" . $conn->real_escape_string(strtoupper($asset_class)) . "'";
    }

    if ($min_strength > 0) {
        $where .= " AND signal_strength >= " . (int)$min_strength;
    }

    $max_hold = _dp_timeline_filter($timeline);
    if ($max_hold > 0) {
        $where .= " AND max_hold_hours <= " . (int)$max_hold;
    }

    // Grade gate: exclude signals from D-grade backtested algorithms
    $where .= " AND NOT EXISTS (
        SELECT 1 FROM lm_ml_status ms
        WHERE ms.algorithm_name = s.algorithm_name
          AND ms.asset_class = s.asset_class
          AND ms.backtest_grade = 'D'
    )";

    $sql = "SELECT s.*, p.last_price as current_price
            FROM lm_signals s
            LEFT JOIN lm_price_cache p ON s.symbol = p.symbol
            WHERE $where
            ORDER BY s.signal_strength DESC, s.signal_time DESC
            LIMIT 50";

    $res = $conn->query($sql);
    if (!$res) return array();

    $picks = array();
    while ($row = $res->fetch_assoc()) {
        $rationale_decoded = json_decode($row['rationale'], true);
        if (!is_array($rationale_decoded)) {
            $rationale_decoded = $row['rationale'];
        }

        $hold = (int)$row['max_hold_hours'];
        $tl_cat = _dp_timeline_category($hold);

        $picks[] = array(
            'symbol'            => $row['symbol'],
            'asset_class'       => $row['asset_class'],
            'signal_type'       => $row['signal_type'],
            'entry_price'       => (float)$row['entry_price'],
            'current_price'     => isset($row['current_price']) ? (float)$row['current_price'] : (float)$row['entry_price'],
            'target_tp_pct'     => (float)$row['target_tp_pct'],
            'target_sl_pct'     => (float)$row['target_sl_pct'],
            'algorithm'         => $row['algorithm_name'],
            'signal_strength'   => (int)$row['signal_strength'],
            'max_hold_hours'    => $hold,
            'timeline_category' => $tl_cat,
            'timeline_label'    => _dp_timeline_label($tl_cat),
            'signal_time'       => $row['signal_time'],
            'expires_at'        => $row['expires_at'],
            'rationale'         => $rationale_decoded
        );
    }

    return $picks;
}

// ─── Fetch recent winning trades ────────────────────────────
function _dp_get_wins($conn, $asset_class, $days) {
    $since = date('Y-m-d H:i:s', time() - ($days * 86400));
    $where = "status='closed' AND realized_pnl_usd > 0 AND exit_time >= '" . $conn->real_escape_string($since) . "'";

    if ($asset_class !== '' && $asset_class !== 'all') {
        $where .= " AND asset_class='" . $conn->real_escape_string(strtoupper($asset_class)) . "'";
    }

    $sql = "SELECT * FROM lm_trades WHERE $where ORDER BY exit_time DESC LIMIT 20";
    $res = $conn->query($sql);
    if (!$res) return array();

    $wins = array();
    while ($row = $res->fetch_assoc()) {
        $wins[] = array(
            'symbol'          => $row['symbol'],
            'asset_class'     => $row['asset_class'],
            'algorithm'       => $row['algorithm_name'],
            'direction'       => $row['direction'],
            'entry_price'     => (float)$row['entry_price'],
            'exit_price'      => (float)$row['exit_price'],
            'realized_pnl'    => (float)$row['realized_pnl_usd'],
            'realized_pct'    => (float)$row['realized_pct'],
            'hold_hours'      => (float)$row['hold_hours'],
            'exit_reason'     => $row['exit_reason'],
            'entry_time'      => $row['entry_time'],
            'exit_time'       => $row['exit_time']
        );
    }

    return $wins;
}

// ─── Performance summary (30-day stats) ─────────────────────
function _dp_performance_summary($conn, $asset_class) {
    $since = date('Y-m-d H:i:s', time() - (30 * 86400));
    $where = "status='closed' AND exit_time >= '" . $conn->real_escape_string($since) . "'";

    if ($asset_class !== '' && $asset_class !== 'all') {
        $where .= " AND asset_class='" . $conn->real_escape_string(strtoupper($asset_class)) . "'";
    }

    $sql = "SELECT
        COUNT(*) as total_trades,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(AVG(CASE WHEN realized_pnl_usd > 0 THEN realized_pct ELSE NULL END), 2) as avg_win_pct,
        ROUND(AVG(CASE WHEN realized_pnl_usd <= 0 THEN realized_pct ELSE NULL END), 2) as avg_loss_pct,
        ROUND(SUM(realized_pnl_usd), 2) as total_pnl,
        ROUND(AVG(hold_hours), 1) as avg_hold_hours
    FROM lm_trades WHERE $where";

    $res = $conn->query($sql);
    $stats = $res ? $res->fetch_assoc() : array();
    $total = isset($stats['total_trades']) ? (int)$stats['total_trades'] : 0;
    $wins = isset($stats['wins']) ? (int)$stats['wins'] : 0;
    $win_rate = $total > 0 ? round($wins / $total * 100, 1) : 0;

    // Best algorithm
    $best_algo = 'N/A';
    $sql2 = "SELECT algorithm_name, COUNT(*) as trades,
        ROUND(SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) as wr
    FROM lm_trades WHERE $where AND algorithm_name != ''
    GROUP BY algorithm_name HAVING trades >= 3 ORDER BY wr DESC, trades DESC LIMIT 1";
    $res2 = $conn->query($sql2);
    if ($res2 && $row2 = $res2->fetch_assoc()) {
        $best_algo = $row2['algorithm_name'] . ' (' . $row2['wr'] . '% WR, ' . $row2['trades'] . ' trades)';
    }

    return array(
        'total_trades_30d' => $total,
        'wins'             => $wins,
        'losses'           => $total - $wins,
        'win_rate'         => $win_rate,
        'avg_win_pct'      => isset($stats['avg_win_pct']) ? (float)$stats['avg_win_pct'] : 0,
        'avg_loss_pct'     => isset($stats['avg_loss_pct']) ? (float)$stats['avg_loss_pct'] : 0,
        'total_pnl_usd'    => isset($stats['total_pnl']) ? (float)$stats['total_pnl'] : 0,
        'avg_hold_hours'   => isset($stats['avg_hold_hours']) ? (float)$stats['avg_hold_hours'] : 0,
        'best_algorithm'   => $best_algo
    );
}

// ─── Consecutive wins for momentum ──────────────────────────
function _dp_consecutive_wins($conn, $asset_class) {
    $where = "status='closed'";
    if ($asset_class !== '' && $asset_class !== 'all') {
        $where .= " AND asset_class='" . $conn->real_escape_string(strtoupper($asset_class)) . "'";
    }

    // Get symbols with 2+ consecutive recent wins
    $sql = "SELECT symbol, asset_class,
        COUNT(*) as recent_trades,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as recent_wins
    FROM (
        SELECT symbol, asset_class, realized_pnl_usd
        FROM lm_trades WHERE $where
        ORDER BY exit_time DESC LIMIT 100
    ) recent
    GROUP BY symbol, asset_class
    HAVING recent_wins >= 2 AND recent_wins = recent_trades
    ORDER BY recent_wins DESC
    LIMIT 10";

    $res = $conn->query($sql);
    if (!$res) return array();

    $streaks = array();
    while ($row = $res->fetch_assoc()) {
        $streaks[] = array(
            'symbol'       => $row['symbol'],
            'asset_class'  => $row['asset_class'],
            'win_streak'   => (int)$row['recent_wins']
        );
    }

    return $streaks;
}

// ─── Build response ─────────────────────────────────────────
function _dp_respond($conn, $asset_class, $timeline, $budget, $min_strength) {
    $now_est = gmdate('Y-m-d H:i:s', time() - (5 * 3600));

    $picks = _dp_get_picks($conn, $asset_class, $timeline, $min_strength);
    $recent_wins = _dp_get_wins($conn, $asset_class, 7);
    $perf = _dp_performance_summary($conn, $asset_class);

    $label = $asset_class ? strtoupper($asset_class) : 'ALL';

    $response = array(
        'ok'                   => true,
        'asset_class'          => $label,
        'generated_at'         => $now_est . ' EST',
        'timeline_filter'      => $timeline,
        'pick_count'           => count($picks),
        'picks'                => $picks,
        'recent_wins'          => $recent_wins,
        'recent_win_count'     => count($recent_wins),
        'performance_summary'  => $perf,
        'budget_guidance'      => _dp_budget_guidance($budget),
        'disclaimer'           => 'Not financial advice. These are paper trading signals from automated algorithms. Past performance does not guarantee future results. Do your own research.'
    );

    echo json_encode($response);
}

// ─── Momentum: high-conviction + win streaks ────────────────
function _dp_momentum($conn, $asset_filter, $timeline, $budget) {
    $now_est = gmdate('Y-m-d H:i:s', time() - (5 * 3600));

    // High-strength signals (70+)
    $picks = _dp_get_picks($conn, $asset_filter, $timeline, 70);

    // Consecutive win streaks
    $streaks = _dp_consecutive_wins($conn, $asset_filter);

    // Merge: mark picks that also have win streaks
    $streak_symbols = array();
    foreach ($streaks as $s) {
        $streak_symbols[$s['symbol']] = $s['win_streak'];
    }

    foreach ($picks as $idx => $p) {
        $sym = $p['symbol'];
        if (isset($streak_symbols[$sym])) {
            $picks[$idx]['win_streak'] = $streak_symbols[$sym];
            $picks[$idx]['momentum_reason'] = 'High signal strength + ' . $streak_symbols[$sym] . ' consecutive wins';
        } else {
            $picks[$idx]['win_streak'] = 0;
            $picks[$idx]['momentum_reason'] = 'High signal strength (' . $p['signal_strength'] . '/100)';
        }
    }

    // Sort: streak symbols first, then by strength
    // PHP 5.2: use a named function for usort
    usort($picks, '_dp_momentum_sort');

    $perf = _dp_performance_summary($conn, $asset_filter);

    $response = array(
        'ok'                  => true,
        'action'              => 'momentum',
        'generated_at'        => $now_est . ' EST',
        'description'         => 'Highest-conviction picks most likely to continue going up. Ranked by signal strength (70+) and consecutive win streaks.',
        'pick_count'          => count($picks),
        'picks'               => $picks,
        'win_streaks'         => $streaks,
        'performance_summary' => $perf,
        'budget_guidance'     => _dp_budget_guidance($budget),
        'disclaimer'          => 'Not financial advice. These are paper trading signals from automated algorithms. Past performance does not guarantee future results. Do your own research.'
    );

    echo json_encode($response);
}

function _dp_momentum_sort($a, $b) {
    // Symbols with win streaks first
    if ($a['win_streak'] != $b['win_streak']) {
        return $b['win_streak'] - $a['win_streak'];
    }
    // Then by signal strength
    return $b['signal_strength'] - $a['signal_strength'];
}

// ─── Wins action ────────────────────────────────────────────
function _dp_wins_action($conn, $asset_filter, $budget) {
    $now_est = gmdate('Y-m-d H:i:s', time() - (5 * 3600));

    $wins = _dp_get_wins($conn, $asset_filter, 7);
    $perf = _dp_performance_summary($conn, $asset_filter);

    $response = array(
        'ok'                  => true,
        'action'              => 'wins',
        'generated_at'        => $now_est . ' EST',
        'description'         => 'Recently closed winning trades (last 7 days).',
        'win_count'           => count($wins),
        'wins'                => $wins,
        'performance_summary' => $perf,
        'budget_guidance'     => _dp_budget_guidance($budget),
        'disclaimer'          => 'Not financial advice. These are paper trading results from automated algorithms. Past performance does not guarantee future results.'
    );

    echo json_encode($response);
}

// ─── All action (combined) ──────────────────────────────────
function _dp_all($conn, $timeline, $budget, $min_strength) {
    $now_est = gmdate('Y-m-d H:i:s', time() - (5 * 3600));

    $crypto_picks = _dp_get_picks($conn, 'CRYPTO', $timeline, $min_strength);
    $forex_picks  = _dp_get_picks($conn, 'FOREX',  $timeline, $min_strength);
    $stock_picks  = _dp_get_picks($conn, 'STOCK',  $timeline, $min_strength);
    $recent_wins  = _dp_get_wins($conn, 'all', 7);
    $perf         = _dp_performance_summary($conn, '');

    $response = array(
        'ok'                  => true,
        'action'              => 'all',
        'generated_at'        => $now_est . ' EST',
        'timeline_filter'     => $timeline,
        'crypto'              => array('count' => count($crypto_picks), 'picks' => $crypto_picks),
        'forex'               => array('count' => count($forex_picks),  'picks' => $forex_picks),
        'stocks'              => array('count' => count($stock_picks),  'picks' => $stock_picks),
        'total_picks'         => count($crypto_picks) + count($forex_picks) + count($stock_picks),
        'recent_wins'         => $recent_wins,
        'recent_win_count'    => count($recent_wins),
        'performance_summary' => $perf,
        'budget_guidance'     => _dp_budget_guidance($budget),
        'disclaimer'          => 'Not financial advice. These are paper trading signals from automated algorithms. Past performance does not guarantee future results. Do your own research.'
    );

    echo json_encode($response);
}

// ─── Snapshot action (admin only, for daily caching) ────────
function _dp_snapshot($conn, $timeline, $budget, $min_strength) {
    $key = isset($_GET['key']) ? $_GET['key'] : '';
    if ($key !== 'livetrader2026') {
        echo json_encode(array('ok' => false, 'error' => 'Admin key required for snapshot'));
        return;
    }

    // Generate full data
    $now_est = gmdate('Y-m-d H:i:s', time() - (5 * 3600));
    $crypto_picks = _dp_get_picks($conn, 'CRYPTO', $timeline, $min_strength);
    $forex_picks  = _dp_get_picks($conn, 'FOREX',  $timeline, $min_strength);
    $stock_picks  = _dp_get_picks($conn, 'STOCK',  $timeline, $min_strength);
    $recent_wins  = _dp_get_wins($conn, 'all', 7);
    $perf         = _dp_performance_summary($conn, '');

    $snapshot = array(
        'ok'            => true,
        'snapshot_time' => $now_est,
        'crypto'        => array('count' => count($crypto_picks), 'picks' => $crypto_picks),
        'forex'         => array('count' => count($forex_picks),  'picks' => $forex_picks),
        'stocks'        => array('count' => count($stock_picks),  'picks' => $stock_picks),
        'total_picks'   => count($crypto_picks) + count($forex_picks) + count($stock_picks),
        'recent_wins'   => $recent_wins,
        'performance'   => $perf
    );

    // Cache to file
    $cache_dir = dirname(__FILE__) . '/cache';
    if (!is_dir($cache_dir)) @mkdir($cache_dir, 0755, true);
    $cache_file = $cache_dir . '/daily_picks_snapshot.json';
    @file_put_contents($cache_file, json_encode($snapshot));

    echo json_encode(array(
        'ok'           => true,
        'action'       => 'snapshot',
        'snapshot_time' => $now_est,
        'crypto_count' => count($crypto_picks),
        'forex_count'  => count($forex_picks),
        'stock_count'  => count($stock_picks),
        'total'        => count($crypto_picks) + count($forex_picks) + count($stock_picks),
        'wins_7d'      => count($recent_wins),
        'cached_to'    => $cache_file
    ));
}

// ═══════════════════════════════════════════════════════════════
//  ROUTER
// ═══════════════════════════════════════════════════════════════

$snapshot_flag = isset($_GET['snapshot']) && $_GET['snapshot'] === '1';
if ($snapshot_flag) {
    _dp_snapshot($conn, $timeline, $budget, $min_strength);
} elseif ($action === 'crypto') {
    _dp_respond($conn, 'CRYPTO', $timeline, $budget, $min_strength);
} elseif ($action === 'forex') {
    _dp_respond($conn, 'FOREX', $timeline, $budget, $min_strength);
} elseif ($action === 'stocks') {
    _dp_respond($conn, 'STOCK', $timeline, $budget, $min_strength);
} elseif ($action === 'momentum') {
    $asset_filter = isset($_GET['asset']) ? strtoupper(trim($_GET['asset'])) : '';
    _dp_momentum($conn, $asset_filter, $timeline, $budget);
} elseif ($action === 'wins') {
    $asset_filter = isset($_GET['asset']) ? strtoupper(trim($_GET['asset'])) : 'all';
    _dp_wins_action($conn, $asset_filter, $budget);
} elseif ($action === 'all') {
    _dp_all($conn, $timeline, $budget, $min_strength);
} else {
    echo json_encode(array(
        'ok'    => false,
        'error' => 'Unknown action: ' . $action . '. Valid: crypto, forex, stocks, momentum, wins, all'
    ));
}

$conn->close();
