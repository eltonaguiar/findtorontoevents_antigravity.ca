<?php
/**
 * algo_performance.php — Performance tracking API: Self-Learning vs Original params.
 *
 * Actions:
 *   ?action=summary        — Overall comparison: learned vs original across all algos
 *   ?action=by_algorithm    — Per-algorithm comparison breakdown
 *   ?action=by_asset        — Per-asset-class comparison
 *   ?action=trades          — Recent closed trades with param source tags
 *   ?action=virtual_compare — Compute virtual outcomes for both param sets on closed trades
 *   ?action=snapshot        — Generate daily performance snapshot (admin, key required)
 *   ?action=backfill        — Tag historical signals with param_source (admin, one-time)
 *   ?action=sharpe          — Sharpe ratio from daily_prices (symbol, days params)
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/db_config.php';
require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/algo_performance_schema.php';

// $conn is created by db_connect.php (exits on failure)
_ap_ensure_schema($conn);

$action = isset($_GET['action']) ? $_GET['action'] : 'summary';

// ═══════════════════════════════════════════════
// Default (original) params lookup for all 19 algorithms
// ═══════════════════════════════════════════════
function _ap_get_default_params($algo_name, $asset_class) {
    // Returns array('tp' => x, 'sl' => y, 'hold' => z)
    // Values match live_signals.php (Feb 11 2026 overhaul: stock TP/hold increased)
    $defaults = array(
        'Momentum Burst'       => array('CRYPTO' => array(3.0, 1.5, 8),   'FOREX' => array(1.5, 0.75, 8),  'STOCK' => array(2.0, 1.0, 16)),
        'RSI Reversal'         => array('CRYPTO' => array(2.0, 1.0, 12),  'FOREX' => array(2.0, 1.0, 12),  'STOCK' => array(2.5, 1.2, 16)),
        'Breakout 24h'         => array('CRYPTO' => array(8.0, 2.0, 16),  'FOREX' => array(8.0, 2.0, 16),  'STOCK' => array(8.0, 2.5, 24)),
        'DCA Dip'              => array('CRYPTO' => array(5.0, 3.0, 48),  'FOREX' => array(5.0, 3.0, 48),  'STOCK' => array(5.0, 3.0, 48)),
        'Bollinger Squeeze'    => array('CRYPTO' => array(2.5, 1.5, 8),   'FOREX' => array(2.5, 1.5, 8),   'STOCK' => array(3.0, 1.5, 16)),
        'MACD Crossover'       => array('CRYPTO' => array(2.0, 1.0, 12),  'FOREX' => array(2.0, 1.0, 12),  'STOCK' => array(2.5, 1.2, 16)),
        'Consensus'            => array('CRYPTO' => array(3.0, 2.0, 24),  'FOREX' => array(3.0, 2.0, 24),  'STOCK' => array(3.5, 2.0, 36)),
        'Volatility Breakout'  => array('CRYPTO' => array(3.0, 2.0, 16),  'FOREX' => array(3.0, 2.0, 16),  'STOCK' => array(3.5, 2.0, 24)),
        'Trend Sniper'         => array('CRYPTO' => array(1.5, 0.75, 8),  'FOREX' => array(0.4, 0.2, 8),   'STOCK' => array(1.5, 0.75, 12)),
        'Dip Recovery'         => array('CRYPTO' => array(2.5, 1.5, 16),  'FOREX' => array(0.6, 0.4, 16),  'STOCK' => array(2.0, 1.0, 24)),
        'Volume Spike'         => array('CRYPTO' => array(2.0, 1.0, 12),  'FOREX' => array(0.5, 0.3, 12),  'STOCK' => array(2.0, 1.0, 16)),
        'VAM'                  => array('CRYPTO' => array(2.0, 1.0, 12),  'FOREX' => array(0.4, 0.2, 12),  'STOCK' => array(1.8, 0.9, 16)),
        'Mean Reversion Sniper'=> array('CRYPTO' => array(2.0, 1.0, 12),  'FOREX' => array(0.5, 0.3, 12),  'STOCK' => array(2.0, 1.0, 16)),
        'ADX Trend Strength'   => array('CRYPTO' => array(1.5, 0.75, 12), 'FOREX' => array(0.4, 0.2, 12),  'STOCK' => array(1.5, 0.75, 16)),
        'StochRSI Crossover'   => array('CRYPTO' => array(2.0, 1.0, 12),  'FOREX' => array(0.5, 0.25, 12), 'STOCK' => array(1.5, 0.75, 16)),
        'Awesome Oscillator'   => array('CRYPTO' => array(1.8, 0.9, 12),  'FOREX' => array(0.4, 0.2, 12),  'STOCK' => array(1.5, 0.75, 16)),
        'RSI(2) Scalp'         => array('CRYPTO' => array(1.2, 0.6, 6),   'FOREX' => array(0.3, 0.15, 6),  'STOCK' => array(1.5, 0.75, 8)),
        'Ichimoku Cloud'       => array('CRYPTO' => array(2.0, 1.0, 16),  'FOREX' => array(0.5, 0.25, 16), 'STOCK' => array(1.8, 0.9, 24)),
        'Alpha Predator'       => array('CRYPTO' => array(2.0, 1.0, 12),  'FOREX' => array(0.5, 0.25, 12), 'STOCK' => array(1.8, 0.9, 16)),
        'Insider Cluster Buy'  => array('STOCK' => array(10.0, 5.0, 504)),
        '13F New Position'     => array('STOCK' => array(12.0, 6.0, 720)),
        'Sentiment Divergence' => array('STOCK' => array(4.0, 2.5, 240)),
        'Contrarian Fear/Greed'=> array('CRYPTO' => array(5.0, 3.0, 168), 'FOREX' => array(2.0, 1.5, 168), 'STOCK' => array(5.0, 3.0, 504))
    );

    if (isset($defaults[$algo_name]) && isset($defaults[$algo_name][$asset_class])) {
        $d = $defaults[$algo_name][$asset_class];
        return array('tp' => $d[0], 'sl' => $d[1], 'hold' => $d[2]);
    }
    // Fallback: generic defaults
    return array('tp' => 3.0, 'sl' => 2.0, 'hold' => 12);
}


// ═══════════════════════════════════════════════
// ACTION: summary — Overall learned vs original comparison
// ═══════════════════════════════════════════════
if ($action === 'summary') {
    $days = isset($_GET['days']) ? max(1, intval($_GET['days'])) : 30;
    $since = date('Y-m-d H:i:s', time() - $days * 86400);

    // Trades grouped by param_source
    $sql = "SELECT
                s.param_source,
                COUNT(t.id) as trades,
                SUM(CASE WHEN t.realized_pct > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN t.realized_pct <= 0 THEN 1 ELSE 0 END) as losses,
                AVG(t.realized_pct) as avg_pnl,
                SUM(t.realized_pct) as total_pnl,
                MAX(t.realized_pct) as best_trade,
                MIN(t.realized_pct) as worst_trade,
                AVG(t.hold_hours) as avg_hold
            FROM lm_trades t
            JOIN lm_signals s ON t.signal_id = s.id
            WHERE t.status = 'closed' AND t.entry_time > '$since'
            GROUP BY s.param_source";

    $res = $conn->query($sql);
    $groups = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $source = $row['param_source'] ? $row['param_source'] : 'original';
            $total = (int)$row['trades'];
            $wins = (int)$row['wins'];
            $groups[$source] = array(
                'trades'      => $total,
                'wins'        => $wins,
                'losses'      => (int)$row['losses'],
                'win_rate'    => $total > 0 ? round($wins / $total * 100, 1) : 0,
                'avg_pnl'     => round((float)$row['avg_pnl'], 4),
                'total_pnl'   => round((float)$row['total_pnl'], 4),
                'best_trade'  => round((float)$row['best_trade'], 4),
                'worst_trade' => round((float)$row['worst_trade'], 4),
                'avg_hold_hrs'=> round((float)$row['avg_hold'], 1)
            );
        }
    }

    // Also get signal counts
    $sql2 = "SELECT param_source, COUNT(*) as cnt FROM lm_signals WHERE signal_time > '$since' GROUP BY param_source";
    $res2 = $conn->query($sql2);
    $signal_counts = array();
    if ($res2) {
        while ($row = $res2->fetch_assoc()) {
            $signal_counts[$row['param_source'] ? $row['param_source'] : 'original'] = (int)$row['cnt'];
        }
    }

    // Count of untagged signals
    $res3 = $conn->query("SELECT COUNT(*) as cnt FROM lm_signals WHERE param_source = '' OR param_source IS NULL");
    $untagged = 0;
    if ($res3) { $r = $res3->fetch_assoc(); $untagged = (int)$r['cnt']; }

    echo json_encode(array(
        'ok'             => true,
        'action'         => 'summary',
        'days'           => $days,
        'performance'    => $groups,
        'signal_counts'  => $signal_counts,
        'untagged_signals' => $untagged,
        'timestamp'      => date('Y-m-d H:i:s')
    ));
    exit;
}


// ═══════════════════════════════════════════════
// ACTION: by_algorithm — Per-algorithm comparison
// ═══════════════════════════════════════════════
if ($action === 'by_algorithm') {
    $days = isset($_GET['days']) ? max(1, intval($_GET['days'])) : 30;
    $since = date('Y-m-d H:i:s', time() - $days * 86400);

    $sql = "SELECT
                t.algorithm_name,
                s.param_source,
                COUNT(t.id) as trades,
                SUM(CASE WHEN t.realized_pct > 0 THEN 1 ELSE 0 END) as wins,
                AVG(t.realized_pct) as avg_pnl,
                SUM(t.realized_pct) as total_pnl,
                AVG(t.target_tp_pct) as avg_tp,
                AVG(t.target_sl_pct) as avg_sl,
                AVG(t.max_hold_hours) as avg_hold
            FROM lm_trades t
            JOIN lm_signals s ON t.signal_id = s.id
            WHERE t.status = 'closed' AND t.entry_time > '$since'
            GROUP BY t.algorithm_name, s.param_source
            ORDER BY t.algorithm_name, s.param_source";

    $res = $conn->query($sql);
    $algos = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $name   = $row['algorithm_name'];
            $source = $row['param_source'] ? $row['param_source'] : 'original';
            $total  = (int)$row['trades'];
            $wins   = (int)$row['wins'];

            if (!isset($algos[$name])) $algos[$name] = array();
            $algos[$name][$source] = array(
                'trades'   => $total,
                'wins'     => $wins,
                'win_rate' => $total > 0 ? round($wins / $total * 100, 1) : 0,
                'avg_pnl'  => round((float)$row['avg_pnl'], 4),
                'total_pnl'=> round((float)$row['total_pnl'], 4),
                'avg_tp'   => round((float)$row['avg_tp'], 2),
                'avg_sl'   => round((float)$row['avg_sl'], 2),
                'avg_hold'  => round((float)$row['avg_hold'], 0)
            );
        }
    }

    // Add default params for reference
    $algo_data = array();
    foreach ($algos as $name => $sources) {
        $defaults = _ap_get_default_params($name, 'CRYPTO');
        $algo_data[] = array(
            'algorithm'      => $name,
            'original'       => isset($sources['original']) ? $sources['original'] : null,
            'learned'        => isset($sources['learned']) ? $sources['learned'] : null,
            'default_params' => $defaults
        );
    }

    echo json_encode(array(
        'ok'         => true,
        'action'     => 'by_algorithm',
        'days'       => $days,
        'algorithms' => $algo_data,
        'timestamp'  => date('Y-m-d H:i:s')
    ));
    exit;
}


// ═══════════════════════════════════════════════
// ACTION: by_asset — Per-asset-class comparison
// ═══════════════════════════════════════════════
if ($action === 'by_asset') {
    $days = isset($_GET['days']) ? max(1, intval($_GET['days'])) : 30;
    $since = date('Y-m-d H:i:s', time() - $days * 86400);

    $sql = "SELECT
                t.asset_class,
                s.param_source,
                COUNT(t.id) as trades,
                SUM(CASE WHEN t.realized_pct > 0 THEN 1 ELSE 0 END) as wins,
                AVG(t.realized_pct) as avg_pnl,
                SUM(t.realized_pct) as total_pnl
            FROM lm_trades t
            JOIN lm_signals s ON t.signal_id = s.id
            WHERE t.status = 'closed' AND t.entry_time > '$since'
            GROUP BY t.asset_class, s.param_source
            ORDER BY t.asset_class";

    $res = $conn->query($sql);
    $assets = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $ac = $row['asset_class'];
            $source = $row['param_source'] ? $row['param_source'] : 'original';
            $total = (int)$row['trades'];
            $wins = (int)$row['wins'];
            if (!isset($assets[$ac])) $assets[$ac] = array();
            $assets[$ac][$source] = array(
                'trades'    => $total,
                'wins'      => $wins,
                'win_rate'  => $total > 0 ? round($wins / $total * 100, 1) : 0,
                'avg_pnl'   => round((float)$row['avg_pnl'], 4),
                'total_pnl' => round((float)$row['total_pnl'], 4)
            );
        }
    }

    echo json_encode(array(
        'ok'        => true,
        'action'    => 'by_asset',
        'days'      => $days,
        'assets'    => $assets,
        'timestamp' => date('Y-m-d H:i:s')
    ));
    exit;
}


// ═══════════════════════════════════════════════
// ACTION: trades — Recent closed trades with param tagging
// ═══════════════════════════════════════════════
if ($action === 'trades') {
    $limit = isset($_GET['limit']) ? min(200, max(1, intval($_GET['limit']))) : 50;
    $asset = isset($_GET['asset']) ? $conn->real_escape_string($_GET['asset']) : '';
    $source_filter = isset($_GET['source']) ? $conn->real_escape_string($_GET['source']) : '';

    $where = "t.status = 'closed'";
    if ($asset) $where .= " AND t.asset_class = '$asset'";
    if ($source_filter) $where .= " AND s.param_source = '$source_filter'";

    $sql = "SELECT t.id, t.asset_class, t.symbol, t.algorithm_name, t.direction,
                   t.entry_price, t.exit_price, t.entry_time, t.exit_time,
                   t.realized_pct, t.realized_pnl_usd, t.exit_reason,
                   t.target_tp_pct, t.target_sl_pct, t.max_hold_hours, t.hold_hours,
                   s.param_source, s.tp_original, s.sl_original, s.hold_original
            FROM lm_trades t
            JOIN lm_signals s ON t.signal_id = s.id
            WHERE $where
            ORDER BY t.exit_time DESC
            LIMIT $limit";

    $res = $conn->query($sql);
    $trades = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $algo = $row['algorithm_name'];
            $ac   = $row['asset_class'];
            $def  = _ap_get_default_params($algo, $ac);
            $orig_tp   = (float)$row['tp_original'] > 0 ? (float)$row['tp_original'] : $def['tp'];
            $orig_sl   = (float)$row['sl_original'] > 0 ? (float)$row['sl_original'] : $def['sl'];
            $orig_hold = (int)$row['hold_original'] > 0 ? (int)$row['hold_original'] : $def['hold'];

            $trades[] = array(
                'id'             => (int)$row['id'],
                'asset_class'    => $ac,
                'symbol'         => $row['symbol'],
                'algorithm'      => $algo,
                'direction'      => $row['direction'],
                'entry_price'    => (float)$row['entry_price'],
                'exit_price'     => (float)$row['exit_price'],
                'entry_time'     => $row['entry_time'],
                'exit_time'      => $row['exit_time'],
                'pnl_pct'        => round((float)$row['realized_pct'], 4),
                'pnl_usd'        => round((float)$row['realized_pnl_usd'], 2),
                'exit_reason'    => $row['exit_reason'],
                'param_source'   => $row['param_source'] ? $row['param_source'] : 'original',
                'params_used'    => array(
                    'tp'   => (float)$row['target_tp_pct'],
                    'sl'   => (float)$row['target_sl_pct'],
                    'hold' => (int)$row['max_hold_hours']
                ),
                'params_original'=> array('tp' => $orig_tp, 'sl' => $orig_sl, 'hold' => $orig_hold),
                'hold_hours'     => round((float)$row['hold_hours'], 1),
                'outcome'        => (float)$row['realized_pct'] > 0 ? 'win' : 'loss'
            );
        }
    }

    echo json_encode(array(
        'ok'     => true,
        'action' => 'trades',
        'count'  => count($trades),
        'trades' => $trades
    ));
    exit;
}


// ═══════════════════════════════════════════════
// ACTION: snapshot — Generate daily performance snapshot (admin)
// ═══════════════════════════════════════════════
if ($action === 'snapshot') {
    $key = isset($_GET['key']) ? $_GET['key'] : '';
    if ($key !== 'livetrader2026') {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Admin key required'));
        exit;
    }

    $today = date('Y-m-d');
    $now = date('Y-m-d H:i:s');

    // Get unique algo/asset/source combos from closed trades
    $sql = "SELECT
                t.algorithm_name, t.asset_class, s.param_source,
                COUNT(t.id) as trades,
                SUM(CASE WHEN t.realized_pct > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN t.realized_pct <= 0 THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN t.exit_reason = 'max_hold' THEN 1 ELSE 0 END) as expired,
                SUM(t.realized_pct) as total_pnl,
                AVG(t.realized_pct) as avg_pnl,
                MAX(t.realized_pct) as best,
                MIN(t.realized_pct) as worst,
                AVG(t.hold_hours) as avg_hold,
                AVG(t.target_tp_pct) as avg_tp,
                AVG(t.target_sl_pct) as avg_sl,
                AVG(t.max_hold_hours) as avg_hold_param
            FROM lm_trades t
            JOIN lm_signals s ON t.signal_id = s.id
            WHERE t.status = 'closed'
            GROUP BY t.algorithm_name, t.asset_class, s.param_source";

    $res = $conn->query($sql);
    $inserted = 0;
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $safe_algo   = $conn->real_escape_string($row['algorithm_name']);
            $safe_asset  = $conn->real_escape_string($row['asset_class']);
            $safe_source = $conn->real_escape_string($row['param_source'] ? $row['param_source'] : 'original');
            $total = (int)$row['trades'];
            $wins  = (int)$row['wins'];
            $wr = $total > 0 ? round($wins / $total * 100, 1) : 0;

            // Count signals for this combo
            $sig_res = $conn->query("SELECT COUNT(*) as cnt FROM lm_signals
                WHERE algorithm_name='$safe_algo' AND asset_class='$safe_asset' AND param_source='$safe_source'");
            $sig_count = 0;
            if ($sig_res) { $sr = $sig_res->fetch_assoc(); $sig_count = (int)$sr['cnt']; }

            $ins = "INSERT INTO lm_algo_performance
                (snap_date, algorithm_name, asset_class, param_source,
                 signals_count, trades_count, wins, losses, expired,
                 total_pnl_pct, avg_pnl_pct, win_rate, best_trade_pct, worst_trade_pct,
                 avg_hold_hours, tp_used, sl_used, hold_used, created_at)
                VALUES ('$today', '$safe_algo', '$safe_asset', '$safe_source',
                 $sig_count, $total, $wins, " . (int)$row['losses'] . ", " . (int)$row['expired'] . ",
                 " . round((float)$row['total_pnl'], 4) . ", " . round((float)$row['avg_pnl'], 4) . ",
                 $wr, " . round((float)$row['best'], 4) . ", " . round((float)$row['worst'], 4) . ",
                 " . round((float)$row['avg_hold'], 1) . ", " . round((float)$row['avg_tp'], 2) . ",
                 " . round((float)$row['avg_sl'], 2) . ", " . round((float)$row['avg_hold_param']) . ", '$now')
                ON DUPLICATE KEY UPDATE
                 signals_count=$sig_count, trades_count=$total, wins=$wins,
                 losses=" . (int)$row['losses'] . ", expired=" . (int)$row['expired'] . ",
                 total_pnl_pct=" . round((float)$row['total_pnl'], 4) . ",
                 avg_pnl_pct=" . round((float)$row['avg_pnl'], 4) . ",
                 win_rate=$wr,
                 best_trade_pct=" . round((float)$row['best'], 4) . ",
                 worst_trade_pct=" . round((float)$row['worst'], 4) . ",
                 avg_hold_hours=" . round((float)$row['avg_hold'], 1) . ",
                 tp_used=" . round((float)$row['avg_tp'], 2) . ",
                 sl_used=" . round((float)$row['avg_sl'], 2) . ",
                 hold_used=" . round((float)$row['avg_hold_param']) . ",
                 created_at='$now'";
            $conn->query($ins);
            $inserted++;
        }
    }

    echo json_encode(array('ok' => true, 'action' => 'snapshot', 'rows_upserted' => $inserted));
    exit;
}


// ═══════════════════════════════════════════════
// ACTION: backfill — Tag historical signals with param_source
// ═══════════════════════════════════════════════
if ($action === 'backfill') {
    $key = isset($_GET['key']) ? $_GET['key'] : '';
    if ($key !== 'livetrader2026') {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Admin key required'));
        exit;
    }

    // Get all untagged signals
    $res = $conn->query("SELECT id, algorithm_name, asset_class, target_tp_pct, target_sl_pct, max_hold_hours
                         FROM lm_signals WHERE param_source = '' OR param_source = 'original'
                         ORDER BY id LIMIT 500");

    $tagged_learned = 0;
    $tagged_original = 0;

    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $algo  = $row['algorithm_name'];
            $asset = $row['asset_class'];
            $sig_tp   = (float)$row['target_tp_pct'];
            $sig_sl   = (float)$row['target_sl_pct'];
            $sig_hold = (int)$row['max_hold_hours'];
            $sig_id   = (int)$row['id'];

            $def = _ap_get_default_params($algo, $asset);
            $orig_tp   = $def['tp'];
            $orig_sl   = $def['sl'];
            $orig_hold = $def['hold'];

            // Determine param_source: if signal params differ from defaults, it's learned
            $is_learned = (abs($sig_tp - $orig_tp) > 0.05 || abs($sig_sl - $orig_sl) > 0.05 || abs($sig_hold - $orig_hold) > 0);

            $source = $is_learned ? 'learned' : 'original';

            $conn->query("UPDATE lm_signals SET
                param_source = '$source',
                tp_original = $orig_tp,
                sl_original = $orig_sl,
                hold_original = $orig_hold
                WHERE id = $sig_id");

            if ($is_learned) $tagged_learned++;
            else $tagged_original++;
        }
    }

    // Count remaining untagged
    $res2 = $conn->query("SELECT COUNT(*) as cnt FROM lm_signals WHERE tp_original = 0");
    $remaining = 0;
    if ($res2) { $r = $res2->fetch_assoc(); $remaining = (int)$r['cnt']; }

    echo json_encode(array(
        'ok'              => true,
        'action'          => 'backfill',
        'tagged_learned'  => $tagged_learned,
        'tagged_original' => $tagged_original,
        'remaining'       => $remaining
    ));
    exit;
}


// ═══════════════════════════════════════════════
// ACTION: learned_params — Show current learned vs original params for all algos
// ═══════════════════════════════════════════════
if ($action === 'learned_params') {
    $res = $conn->query("SELECT algorithm_name, asset_class, best_tp_pct, best_sl_pct, best_hold_hours,
                                current_wr, optimized_wr, verdict, calc_date
                         FROM lm_hour_learning
                         ORDER BY algorithm_name, asset_class");
    $params = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $algo  = $row['algorithm_name'];
            $asset = $row['asset_class'];
            $def   = _ap_get_default_params($algo, $asset);
            $params[] = array(
                'algorithm'    => $algo,
                'asset_class'  => $asset,
                'original'     => $def,
                'learned'      => array(
                    'tp'   => (float)$row['best_tp_pct'],
                    'sl'   => (float)$row['best_sl_pct'],
                    'hold' => (int)$row['best_hold_hours']
                ),
                'original_wr'  => (float)$row['current_wr'],
                'learned_wr'   => (float)$row['optimized_wr'],
                'verdict'      => $row['verdict'],
                'last_updated' => $row['calc_date']
            );
        }
    }

    echo json_encode(array(
        'ok'     => true,
        'action' => 'learned_params',
        'count'  => count($params),
        'params' => $params
    ));
    exit;
}


// ═══════════════════════════════════════════════
// ACTION: sharpe — Sharpe ratio from daily_prices (simple, PHP 5.2 compatible)
// Uses daily returns: (close_t - close_t-1) / close_t-1
// Annualized Sharpe = mean(returns) / std(returns) * sqrt(252)
// ═══════════════════════════════════════════════
if ($action === 'sharpe') {
    $symbol = isset($_GET['symbol']) ? trim($_GET['symbol']) : 'SPY';
    $days   = isset($_GET['days']) ? max(2, min(1000, intval($_GET['days']))) : 252;
    $safe   = $conn->real_escape_string($symbol);

    $chk = $conn->query("SHOW TABLES LIKE 'daily_prices'");
    if (!$chk || $chk->num_rows == 0) {
        echo json_encode(array('ok' => false, 'error' => 'daily_prices table not found'));
        exit;
    }

    $res = $conn->query("SELECT trade_date, close_price FROM daily_prices WHERE ticker='$safe' ORDER BY trade_date ASC LIMIT " . ($days + 1));
    if (!$res || $res->num_rows < 2) {
        echo json_encode(array('ok' => false, 'error' => 'Not enough data for ' . $symbol));
        exit;
    }

    $prices = array();
    while ($row = $res->fetch_assoc()) {
        $prices[] = (float)$row['close_price'];
    }

    $returns = array();
    for ($i = 1; $i < count($prices); $i++) {
        if ($prices[$i - 1] > 0) {
            $returns[] = ($prices[$i] - $prices[$i - 1]) / $prices[$i - 1];
        }
    }

    $n = count($returns);
    if ($n < 2) {
        echo json_encode(array('ok' => false, 'error' => 'Not enough valid returns'));
        exit;
    }

    $mean = array_sum($returns) / $n;
    $variance = 0;
    foreach ($returns as $r) {
        $variance += ($r - $mean) * ($r - $mean);
    }
    $stddev = sqrt($variance / $n);

    $sharpe = 0;
    if ($stddev > 0) {
        $sharpe = round(($mean / $stddev) * sqrt(252), 4);
    }

    echo json_encode(array(
        'ok'             => true,
        'action'         => 'sharpe',
        'symbol'         => $symbol,
        'days'           => $days,
        'return_count'   => $n,
        'mean_daily_ret' => round($mean * 100, 4),
        'std_daily_ret'  => round($stddev * 100, 4),
        'sharpe_ratio'   => $sharpe,
        'period'         => 'annualized (252 trading days)'
    ));
    exit;
}


echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
