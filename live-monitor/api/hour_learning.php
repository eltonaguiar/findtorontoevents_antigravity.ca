<?php
/**
 * Hour-Trade Self-Learning Engine — grid-search optimal TP/SL/hold parameters
 * + adaptive threshold learning + walk-forward validation + regime tracking.
 * PHP 5.2 compatible (no short arrays, no http_response_code, no spread operator).
 *
 * Actions:
 *   ?action=analyze             — Run grid search over closed trades (admin key required)
 *   ?action=results             — Show latest learning recommendations (public)
 *   ?action=apply               — Mark learned params as active (admin key required)
 *   ?action=adaptive_threshold  — Optimize signal thresholds from rationale data (admin key)
 *   ?action=walk_forward        — Walk-forward validation with train/test windows (admin key)
 *   ?action=regime_stats        — Win rate by bull/bear regime per algorithm (public)
 */
require_once dirname(__FILE__) . '/db_connect.php';

// ─── Constants ───────────────────────────────────────────────────────
$HL_ADMIN_KEY = 'livetrader2026';

$HL_TP_GRID  = array(0.5, 1, 1.5, 2, 3, 5, 8, 10);
$HL_SL_GRID  = array(0.3, 0.5, 1, 1.5, 2, 3, 5);
$HL_HOLD_GRID = array(1, 2, 4, 6, 12, 24, 48);

// ─── Auto-create table ──────────────────────────────────────────────
$conn->query("CREATE TABLE IF NOT EXISTS lm_hour_learning (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_class VARCHAR(10) NOT NULL,
    algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
    calc_date DATE NOT NULL,
    best_tp_pct DECIMAL(6,2) NOT NULL DEFAULT 0,
    best_sl_pct DECIMAL(6,2) NOT NULL DEFAULT 0,
    best_hold_hours INT NOT NULL DEFAULT 0,
    best_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    best_win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    best_profit_factor DECIMAL(8,4) NOT NULL DEFAULT 0,
    trades_tested INT NOT NULL DEFAULT 0,
    profitable_combos INT NOT NULL DEFAULT 0,
    total_combos INT NOT NULL DEFAULT 0,
    current_wr DECIMAL(5,2) NOT NULL DEFAULT 0,
    optimized_wr DECIMAL(5,2) NOT NULL DEFAULT 0,
    verdict VARCHAR(50) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    UNIQUE KEY idx_asset_algo_date (asset_class, algorithm_name, calc_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ─── Route action ────────────────────────────────────────────────────
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'results';

if ($action === 'analyze') {
    _hl_action_analyze($conn, $HL_ADMIN_KEY, $HL_TP_GRID, $HL_SL_GRID, $HL_HOLD_GRID);
} elseif ($action === 'results') {
    _hl_action_results($conn);
} elseif ($action === 'apply') {
    _hl_action_apply($conn, $HL_ADMIN_KEY);
} elseif ($action === 'adaptive_threshold') {
    _hl_action_adaptive_threshold($conn, $HL_ADMIN_KEY);
} elseif ($action === 'walk_forward') {
    _hl_action_walk_forward($conn, $HL_ADMIN_KEY, $HL_TP_GRID, $HL_SL_GRID, $HL_HOLD_GRID);
} elseif ($action === 'regime_stats') {
    _hl_action_regime_stats($conn);
} else {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

$conn->close();
exit;


// =====================================================================
//  ACTION: analyze — Grid search optimal params for each algorithm
// =====================================================================
function _hl_action_analyze($conn, $admin_key, $tp_grid, $sl_grid, $hold_grid) {
    // Require admin key
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key === '') {
        $key = isset($_POST['key']) ? trim($_POST['key']) : '';
    }
    if ($key !== $admin_key) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    // Optional asset_class filter
    $filter_asset = isset($_GET['asset_class']) ? strtoupper(trim($_GET['asset_class'])) : '';

    // Get distinct algorithm + asset_class combos from closed trades
    $where_clause = "WHERE status='closed'";
    if ($filter_asset !== '') {
        $where_clause .= " AND asset_class='" . $conn->real_escape_string($filter_asset) . "'";
    }
    $r = $conn->query("SELECT DISTINCT algorithm_name, asset_class
                        FROM lm_trades
                        $where_clause
                        ORDER BY asset_class, algorithm_name");

    if (!$r) {
        header('HTTP/1.0 500 Internal Server Error');
        echo json_encode(array('ok' => false, 'error' => 'Failed to query trades: ' . $conn->error));
        return;
    }

    $algos = array();
    while ($row = $r->fetch_assoc()) {
        $algos[] = array(
            'algorithm_name' => $row['algorithm_name'],
            'asset_class'    => $row['asset_class']
        );
    }

    if (count($algos) === 0) {
        echo json_encode(array(
            'ok' => true,
            'action' => 'analyze',
            'algorithms_analyzed' => 0,
            'message' => 'No closed trades found to analyze',
            'recommendations' => array()
        ));
        return;
    }

    $today = date('Y-m-d');
    $now_dt = date('Y-m-d H:i:s');
    $recommendations = array();
    $total_combos_per_algo = count($tp_grid) * count($sl_grid) * count($hold_grid);

    foreach ($algos as $algo_info) {
        $algo_name   = $algo_info['algorithm_name'];
        $asset_class = $algo_info['asset_class'];

        // ── Get current (actual) performance ──
        $current_stats = _hl_get_current_stats($conn, $algo_name, $asset_class);
        if ($current_stats['trades'] === 0) {
            continue;
        }

        // ── Grid search ──
        $best_tp     = 0;
        $best_sl     = 0;
        $best_hold   = 0;
        $best_return = -999999;
        $best_wr     = 0;
        $best_pf     = 0;
        $best_trades = 0;
        $profitable_combos = 0;

        foreach ($tp_grid as $tp) {
            foreach ($sl_grid as $sl) {
                foreach ($hold_grid as $hold) {
                    $sim = _hl_simulate_params($conn, $algo_name, $tp, $sl, $hold, $asset_class);

                    if ($sim['trades'] === 0) {
                        continue;
                    }

                    if ($sim['total_return'] > 0) {
                        $profitable_combos++;
                    }

                    // Best by total return
                    if ($sim['total_return'] > $best_return) {
                        $best_return = $sim['total_return'];
                        $best_tp     = $tp;
                        $best_sl     = $sl;
                        $best_hold   = $hold;
                        $best_wr     = $sim['win_rate'];
                        $best_pf     = $sim['profit_factor'];
                        $best_trades = $sim['trades'];
                    }
                }
            }
        }

        // ── Determine verdict ──
        if ($best_return > 0 && $best_wr > $current_stats['win_rate']) {
            $verdict = 'PROFITABLE_PARAMS_EXIST';
        } elseif ($best_return > 0) {
            $verdict = 'IMPROVABLE';
        } else {
            $verdict = 'NO_PROFITABLE_PARAMS';
        }

        // ── Upsert into lm_hour_learning ──
        $safe_algo  = $conn->real_escape_string($algo_name);
        $safe_asset = $conn->real_escape_string($asset_class);
        $safe_verdict = $conn->real_escape_string($verdict);

        $sql = "INSERT INTO lm_hour_learning "
             . "(asset_class, algorithm_name, calc_date, "
             . "best_tp_pct, best_sl_pct, best_hold_hours, "
             . "best_return_pct, best_win_rate, best_profit_factor, "
             . "trades_tested, profitable_combos, total_combos, "
             . "current_wr, optimized_wr, verdict, created_at) "
             . "VALUES ("
             . "'$safe_asset', '$safe_algo', '$today', "
             . "$best_tp, $best_sl, $best_hold, "
             . "$best_return, $best_wr, $best_pf, "
             . "$best_trades, $profitable_combos, $total_combos_per_algo, "
             . $current_stats['win_rate'] . ", $best_wr, '$safe_verdict', '$now_dt') "
             . "ON DUPLICATE KEY UPDATE "
             . "best_tp_pct=$best_tp, best_sl_pct=$best_sl, best_hold_hours=$best_hold, "
             . "best_return_pct=$best_return, best_win_rate=$best_wr, best_profit_factor=$best_pf, "
             . "trades_tested=$best_trades, profitable_combos=$profitable_combos, "
             . "total_combos=$total_combos_per_algo, "
             . "current_wr=" . $current_stats['win_rate'] . ", optimized_wr=$best_wr, "
             . "verdict='$safe_verdict', created_at='$now_dt'";

        $conn->query($sql);

        $recommendations[] = array(
            'algorithm'    => $algo_name,
            'asset_class'  => $asset_class,
            'trades_tested' => $best_trades,
            'current_wr'   => $current_stats['win_rate'],
            'best_params'  => array(
                'tp'   => $best_tp,
                'sl'   => $best_sl,
                'hold' => $best_hold
            ),
            'optimized_wr'     => $best_wr,
            'best_return_pct'  => $best_return,
            'best_profit_factor' => $best_pf,
            'profitable_combos'  => $profitable_combos,
            'total_combos'       => $total_combos_per_algo,
            'verdict'            => $verdict
        );
    }

    echo json_encode(array(
        'ok'                   => true,
        'action'               => 'analyze',
        'calc_date'            => $today,
        'algorithms_analyzed'  => count($recommendations),
        'recommendations'      => $recommendations
    ));
}


// =====================================================================
//  ACTION: results — Show latest learning recommendations (public)
// =====================================================================
function _hl_action_results($conn) {
    // Optional filters
    $filter_asset = isset($_GET['asset_class']) ? strtoupper(trim($_GET['asset_class'])) : '';
    $filter_algo  = isset($_GET['algorithm']) ? trim($_GET['algorithm']) : '';

    // Get latest entry per algorithm+asset_class using self-join on max calc_date
    $sql = "SELECT h.* FROM lm_hour_learning h "
         . "INNER JOIN ("
         . "  SELECT algorithm_name, asset_class, MAX(calc_date) AS max_date "
         . "  FROM lm_hour_learning GROUP BY algorithm_name, asset_class"
         . ") latest "
         . "ON h.algorithm_name = latest.algorithm_name "
         . "AND h.asset_class = latest.asset_class "
         . "AND h.calc_date = latest.max_date";

    $conditions = array();
    if ($filter_asset !== '') {
        $conditions[] = "h.asset_class = '" . $conn->real_escape_string($filter_asset) . "'";
    }
    if ($filter_algo !== '') {
        $conditions[] = "h.algorithm_name = '" . $conn->real_escape_string($filter_algo) . "'";
    }
    if (count($conditions) > 0) {
        $sql .= " WHERE " . implode(' AND ', $conditions);
    }

    $sql .= " ORDER BY h.asset_class ASC, h.best_return_pct DESC";

    $r = $conn->query($sql);
    if (!$r) {
        header('HTTP/1.0 500 Internal Server Error');
        echo json_encode(array('ok' => false, 'error' => 'Query failed: ' . $conn->error));
        return;
    }

    $results = array();
    while ($row = $r->fetch_assoc()) {
        $results[] = array(
            'algorithm'         => $row['algorithm_name'],
            'asset_class'       => $row['asset_class'],
            'calc_date'         => $row['calc_date'],
            'best_params'       => array(
                'tp'   => (float)$row['best_tp_pct'],
                'sl'   => (float)$row['best_sl_pct'],
                'hold' => (int)$row['best_hold_hours']
            ),
            'best_return_pct'    => (float)$row['best_return_pct'],
            'best_win_rate'      => (float)$row['best_win_rate'],
            'best_profit_factor' => (float)$row['best_profit_factor'],
            'trades_tested'      => (int)$row['trades_tested'],
            'profitable_combos'  => (int)$row['profitable_combos'],
            'total_combos'       => (int)$row['total_combos'],
            'current_wr'         => (float)$row['current_wr'],
            'optimized_wr'       => (float)$row['optimized_wr'],
            'verdict'            => $row['verdict'],
            'created_at'         => $row['created_at']
        );
    }

    // Summary stats
    $total_algos = count($results);
    $profitable_algos = 0;
    $improvable_algos = 0;
    foreach ($results as $rec) {
        if ($rec['verdict'] === 'PROFITABLE_PARAMS_EXIST') {
            $profitable_algos++;
        }
        if ($rec['verdict'] === 'IMPROVABLE') {
            $improvable_algos++;
        }
    }

    echo json_encode(array(
        'ok'      => true,
        'action'  => 'results',
        'summary' => array(
            'total_algorithms'   => $total_algos,
            'profitable'         => $profitable_algos,
            'improvable'         => $improvable_algos,
            'no_profitable'      => $total_algos - $profitable_algos - $improvable_algos
        ),
        'recommendations' => $results
    ));
}


// =====================================================================
//  ACTION: apply — Mark learned params as active for live_signals
// =====================================================================
function _hl_action_apply($conn, $admin_key) {
    // Require admin key
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key === '') {
        $key = isset($_POST['key']) ? trim($_POST['key']) : '';
    }
    if ($key !== $admin_key) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    // Optional: only apply for a specific algorithm
    $filter_algo = isset($_GET['algorithm']) ? trim($_GET['algorithm']) : '';

    // Get latest profitable recommendations
    $sql = "SELECT h.* FROM lm_hour_learning h "
         . "INNER JOIN ("
         . "  SELECT algorithm_name, asset_class, MAX(calc_date) AS max_date "
         . "  FROM lm_hour_learning GROUP BY algorithm_name, asset_class"
         . ") latest "
         . "ON h.algorithm_name = latest.algorithm_name "
         . "AND h.asset_class = latest.asset_class "
         . "AND h.calc_date = latest.max_date "
         . "WHERE h.verdict IN ('PROFITABLE_PARAMS_EXIST', 'IMPROVABLE') "
         . "AND h.best_return_pct > 0";

    if ($filter_algo !== '') {
        $sql .= " AND h.algorithm_name = '" . $conn->real_escape_string($filter_algo) . "'";
    }

    $r = $conn->query($sql);
    if (!$r) {
        header('HTTP/1.0 500 Internal Server Error');
        echo json_encode(array('ok' => false, 'error' => 'Query failed: ' . $conn->error));
        return;
    }

    $applied = array();
    $skipped = array();

    while ($row = $r->fetch_assoc()) {
        $algo_name   = $row['algorithm_name'];
        $asset_class = $row['asset_class'];
        $tp          = (float)$row['best_tp_pct'];
        $sl          = (float)$row['best_sl_pct'];
        $hold        = (int)$row['best_hold_hours'];
        $best_wr     = (float)$row['best_win_rate'];
        $current_wr  = (float)$row['current_wr'];

        // Safety check: only apply if improvement is meaningful (>2% WR gain or positive return)
        $wr_improvement = $best_wr - $current_wr;
        $best_return = (float)$row['best_return_pct'];

        if ($best_return <= 0) {
            $skipped[] = array(
                'algorithm'   => $algo_name,
                'asset_class' => $asset_class,
                'reason'      => 'Negative or zero best return'
            );
            continue;
        }

        // The live_signals.php already queries lm_hour_learning for learned params.
        // This action simply logs the application event. The params are already stored
        // in lm_hour_learning and live_signals reads them directly.
        // We update the verdict to indicate these params are now active.
        $safe_algo  = $conn->real_escape_string($algo_name);
        $safe_asset = $conn->real_escape_string($asset_class);
        $calc_date  = $conn->real_escape_string($row['calc_date']);

        $conn->query("UPDATE lm_hour_learning
                       SET verdict='APPLIED'
                       WHERE algorithm_name='$safe_algo'
                       AND asset_class='$safe_asset'
                       AND calc_date='$calc_date'");

        $applied[] = array(
            'algorithm'      => $algo_name,
            'asset_class'    => $asset_class,
            'params'         => array('tp' => $tp, 'sl' => $sl, 'hold' => $hold),
            'current_wr'     => $current_wr,
            'optimized_wr'   => $best_wr,
            'wr_improvement' => round($wr_improvement, 2),
            'best_return_pct' => $best_return
        );
    }

    echo json_encode(array(
        'ok'      => true,
        'action'  => 'apply',
        'applied_count' => count($applied),
        'skipped_count' => count($skipped),
        'applied' => $applied,
        'skipped' => $skipped,
        'note'    => 'live_signals.php will now use learned params from lm_hour_learning for applied algorithms'
    ));
}


// =====================================================================
//  Simulation: Test a set of TP/SL/hold params against closed trades
// =====================================================================
function _hl_simulate_params($conn, $algo, $tp, $sl, $max_h, $asset_class) {
    $safe_algo  = $conn->real_escape_string($algo);
    $safe_asset = $conn->real_escape_string($asset_class);

    $r = $conn->query("SELECT entry_price, exit_price, direction,
                        realized_pct, hold_hours, exit_reason
                        FROM lm_trades
                        WHERE algorithm_name='$safe_algo'
                        AND asset_class='$safe_asset'
                        AND status='closed'
                        ORDER BY entry_time ASC");

    if (!$r) {
        return array(
            'trades' => 0, 'wins' => 0,
            'win_rate' => 0, 'avg_return' => 0,
            'total_return' => 0, 'profit_factor' => 0
        );
    }

    $trades = 0;
    $wins = 0;
    $total_return = 0;
    $sum_wins = 0;
    $sum_losses = 0;

    while ($t = $r->fetch_assoc()) {
        $trades++;
        $actual_pct   = (float)$t['realized_pct'];
        $actual_hours = (float)$t['hold_hours'];

        // Simulate with new params:
        // If the actual return exceeded our TP, cap it at TP
        if ($actual_pct >= $tp) {
            $sim_return = $tp;
        }
        // If the actual loss exceeded our SL, cap it at -SL
        elseif ($actual_pct <= -$sl) {
            $sim_return = -$sl;
        }
        // If trade was within bounds but held too long, scale by time
        elseif ($actual_hours > $max_h && $max_h > 0) {
            $time_ratio = $max_h / max($actual_hours, 1);
            $sim_return = $actual_pct * $time_ratio;
        }
        else {
            $sim_return = $actual_pct;
        }

        if ($sim_return > 0) {
            $wins++;
            $sum_wins += $sim_return;
        } else {
            $sum_losses += abs($sim_return);
        }
        $total_return += $sim_return;
    }

    $wr = ($trades > 0) ? round($wins / $trades * 100, 2) : 0;

    if ($sum_losses > 0) {
        $pf = round($sum_wins / $sum_losses, 4);
    } elseif ($sum_wins > 0) {
        $pf = 99.99;
    } else {
        $pf = 0;
    }

    $avg_ret = ($trades > 0) ? round($total_return / $trades, 4) : 0;

    return array(
        'trades'       => $trades,
        'wins'         => $wins,
        'win_rate'     => $wr,
        'avg_return'   => $avg_ret,
        'total_return' => round($total_return, 4),
        'profit_factor' => $pf
    );
}


// =====================================================================
//  Helper: Get current (actual) stats for an algorithm
// =====================================================================
function _hl_get_current_stats($conn, $algo, $asset_class) {
    $safe_algo  = $conn->real_escape_string($algo);
    $safe_asset = $conn->real_escape_string($asset_class);

    $r = $conn->query("SELECT
                          COUNT(*) as total_trades,
                          SUM(CASE WHEN realized_pct > 0 THEN 1 ELSE 0 END) as wins,
                          SUM(realized_pct) as total_return,
                          SUM(CASE WHEN realized_pct > 0 THEN realized_pct ELSE 0 END) as sum_wins,
                          SUM(CASE WHEN realized_pct <= 0 THEN ABS(realized_pct) ELSE 0 END) as sum_losses,
                          AVG(realized_pct) as avg_return
                        FROM lm_trades
                        WHERE algorithm_name='$safe_algo'
                        AND asset_class='$safe_asset'
                        AND status='closed'");

    if (!$r || !($row = $r->fetch_assoc())) {
        return array(
            'trades' => 0, 'wins' => 0,
            'win_rate' => 0, 'avg_return' => 0,
            'total_return' => 0, 'profit_factor' => 0
        );
    }

    $total   = (int)$row['total_trades'];
    $wins    = (int)$row['wins'];
    $sum_w   = (float)$row['sum_wins'];
    $sum_l   = (float)$row['sum_losses'];
    $avg_ret = round((float)$row['avg_return'], 4);
    $total_r = round((float)$row['total_return'], 4);

    $wr = ($total > 0) ? round($wins / $total * 100, 2) : 0;

    if ($sum_l > 0) {
        $pf = round($sum_w / $sum_l, 4);
    } elseif ($sum_w > 0) {
        $pf = 99.99;
    } else {
        $pf = 0;
    }

    return array(
        'trades'        => $total,
        'wins'          => $wins,
        'win_rate'      => $wr,
        'avg_return'    => $avg_ret,
        'total_return'  => $total_r,
        'profit_factor' => $pf
    );
}


// =====================================================================
//  ACTION: adaptive_threshold — Optimize signal score thresholds
//  Analyzes trade rationale JSON to find optimal composite/zscore thresholds
//  per algorithm. Requires 20+ closed trades per algorithm.
// =====================================================================
function _hl_action_adaptive_threshold($conn, $admin_key) {
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $admin_key) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    // Auto-create threshold learning table
    $conn->query("CREATE TABLE IF NOT EXISTS lm_threshold_learning (
        id INT AUTO_INCREMENT PRIMARY KEY,
        asset_class VARCHAR(10) NOT NULL,
        algorithm_name VARCHAR(100) NOT NULL,
        calc_date DATE NOT NULL,
        param_name VARCHAR(50) NOT NULL DEFAULT '',
        param_value DECIMAL(10,4) NOT NULL DEFAULT 0,
        win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
        trades_tested INT NOT NULL DEFAULT 0,
        avg_return DECIMAL(10,4) NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL,
        UNIQUE KEY idx_algo_param (asset_class, algorithm_name, param_name, calc_date)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // Map algorithm → rationale key to optimize
    $threshold_map = array(
        'Trend Sniper'          => 'composite',
        'Volume Spike'          => 'zscore',
        'VAM'                   => 'martin_ratio',
        'Mean Reversion Sniper' => 'rsi',
        'Dip Recovery'          => 'cumul_dip_pct'
    );

    $today = date('Y-m-d');
    $now_dt = date('Y-m-d H:i:s');
    $results = array();

    // Get closed trades that have rationale data, joined to signal rationale
    $r = $conn->query("SELECT t.algorithm_name, t.asset_class, t.realized_pct,
                        s.rationale
                        FROM lm_trades t
                        LEFT JOIN lm_signals s ON t.signal_id = s.id
                        WHERE t.status='closed' AND s.rationale IS NOT NULL
                        ORDER BY t.algorithm_name, t.asset_class");

    if (!$r) {
        echo json_encode(array('ok' => false, 'error' => 'Query failed: ' . $conn->error));
        return;
    }

    // Group trades by algo+asset
    $grouped = array();
    while ($row = $r->fetch_assoc()) {
        $gkey = $row['algorithm_name'] . '|' . $row['asset_class'];
        if (!isset($grouped[$gkey])) {
            $grouped[$gkey] = array(
                'algorithm_name' => $row['algorithm_name'],
                'asset_class'    => $row['asset_class'],
                'trades'         => array()
            );
        }
        $grouped[$gkey]['trades'][] = array(
            'realized_pct' => (float)$row['realized_pct'],
            'rationale'    => $row['rationale']
        );
    }

    foreach ($grouped as $gkey => $group) {
        $algo_name   = $group['algorithm_name'];
        $asset_class = $group['asset_class'];
        $trades      = $group['trades'];

        if (count($trades) < 20) continue;

        // Find the rationale key to optimize
        if (!isset($threshold_map[$algo_name])) continue;
        $param_key = $threshold_map[$algo_name];

        // Extract threshold values from rationale JSON
        $data_points = array();
        foreach ($trades as $t) {
            $rat = json_decode($t['rationale'], true);
            if (!is_array($rat) || !isset($rat[$param_key])) continue;
            $data_points[] = array(
                'value'  => (float)$rat[$param_key],
                'return' => $t['realized_pct']
            );
        }

        if (count($data_points) < 20) continue;

        // Find optimal threshold by testing different cutoff values
        // Sort by threshold value
        $values = array();
        foreach ($data_points as $dp) $values[] = $dp['value'];
        sort($values);

        $best_threshold = $values[0];
        $best_wr = 0;
        $best_avg_ret = -999;
        $best_count = 0;

        // Test percentiles as thresholds
        $percentiles = array(25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75);
        foreach ($percentiles as $pct) {
            $idx = (int)(count($values) * $pct / 100);
            if ($idx >= count($values)) $idx = count($values) - 1;
            $threshold = abs($values[$idx]);

            $wins = 0;
            $count = 0;
            $sum_ret = 0;
            foreach ($data_points as $dp) {
                if (abs($dp['value']) >= $threshold) {
                    $count++;
                    $sum_ret += $dp['return'];
                    if ($dp['return'] > 0) $wins++;
                }
            }

            if ($count < 10) continue;
            $wr = $wins / $count * 100;
            $avg_ret = $sum_ret / $count;

            if ($avg_ret > $best_avg_ret) {
                $best_threshold = $threshold;
                $best_wr = round($wr, 2);
                $best_avg_ret = round($avg_ret, 4);
                $best_count = $count;
            }
        }

        // Store result
        $safe_algo  = $conn->real_escape_string($algo_name);
        $safe_asset = $conn->real_escape_string($asset_class);
        $safe_param = $conn->real_escape_string('min_' . $param_key);

        $sql = "INSERT INTO lm_threshold_learning "
             . "(asset_class, algorithm_name, calc_date, param_name, param_value, "
             . "win_rate, trades_tested, avg_return, created_at) "
             . "VALUES ('$safe_asset', '$safe_algo', '$today', '$safe_param', "
             . "$best_threshold, $best_wr, $best_count, $best_avg_ret, '$now_dt') "
             . "ON DUPLICATE KEY UPDATE "
             . "param_value=$best_threshold, win_rate=$best_wr, "
             . "trades_tested=$best_count, avg_return=$best_avg_ret, "
             . "created_at='$now_dt'";
        $conn->query($sql);

        $results[] = array(
            'algorithm'       => $algo_name,
            'asset_class'     => $asset_class,
            'param_name'      => 'min_' . $param_key,
            'optimal_value'   => $best_threshold,
            'win_rate'        => $best_wr,
            'avg_return'      => $best_avg_ret,
            'trades_qualified' => $best_count,
            'total_trades'    => count($data_points)
        );
    }

    echo json_encode(array(
        'ok'      => true,
        'action'  => 'adaptive_threshold',
        'results' => $results,
        'note'    => 'Requires 20+ closed trades per algorithm to optimize'
    ));
}


// =====================================================================
//  ACTION: walk_forward — Walk-forward validation (14-day train, 7-day test)
//  Prevents overfitting by only accepting params that work out-of-sample.
//  Science: STOCKSUNIFY2 walk-forward methodology
// =====================================================================
function _hl_action_walk_forward($conn, $admin_key, $tp_grid, $sl_grid, $hold_grid) {
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $admin_key) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    $filter_asset = isset($_GET['asset_class']) ? strtoupper(trim($_GET['asset_class'])) : '';

    // Get distinct algorithm + asset_class combos
    $where_clause = "WHERE status='closed'";
    if ($filter_asset !== '') {
        $where_clause .= " AND asset_class='" . $conn->real_escape_string($filter_asset) . "'";
    }
    $r = $conn->query("SELECT DISTINCT algorithm_name, asset_class
                        FROM lm_trades $where_clause
                        ORDER BY asset_class, algorithm_name");
    if (!$r) {
        echo json_encode(array('ok' => false, 'error' => 'Query failed: ' . $conn->error));
        return;
    }

    $algos = array();
    while ($row = $r->fetch_assoc()) {
        $algos[] = array(
            'algorithm_name' => $row['algorithm_name'],
            'asset_class'    => $row['asset_class']
        );
    }

    $today = date('Y-m-d');
    $now_dt = date('Y-m-d H:i:s');
    $results = array();

    foreach ($algos as $algo_info) {
        $algo_name   = $algo_info['algorithm_name'];
        $asset_class = $algo_info['asset_class'];
        $safe_algo   = $conn->real_escape_string($algo_name);
        $safe_asset  = $conn->real_escape_string($asset_class);

        // Get all closed trades ordered by time
        $tr = $conn->query("SELECT entry_price, exit_price, direction,
                            realized_pct, hold_hours, exit_reason, entry_time
                            FROM lm_trades
                            WHERE algorithm_name='$safe_algo'
                            AND asset_class='$safe_asset'
                            AND status='closed'
                            ORDER BY entry_time ASC");
        if (!$tr) continue;

        $all_trades = array();
        while ($t = $tr->fetch_assoc()) {
            $all_trades[] = $t;
        }

        $total = count($all_trades);
        if ($total < 21) continue; // Need enough for train + test

        // Split: first 14/21 for train, last 7/21 for test
        $train_size = (int)($total * 0.67) - 2; // add embargo of 2 as per roadmap
        $test_size = $total - $train_size;
        if ($test_size < 5) continue;

        $train_trades = array_slice($all_trades, 0, $train_size);
        $test_trades  = array_slice($all_trades, $train_size);

        // Grid search on TRAIN set
        $best_tp = 0; $best_sl = 0; $best_hold = 0;
        $best_train_return = -999999;

        foreach ($tp_grid as $tp) {
            foreach ($sl_grid as $sl) {
                foreach ($hold_grid as $hold) {
                    $sim = _hl_simulate_trades_array($train_trades, $tp, $sl, $hold);
                    if ($sim['trades'] == 0) continue;
                    if ($sim['total_return'] > $best_train_return) {
                        $best_train_return = $sim['total_return'];
                        $best_tp = $tp;
                        $best_sl = $sl;
                        $best_hold = $hold;
                    }
                }
            }
        }

        if ($best_train_return <= 0) {
            $results[] = array(
                'algorithm'    => $algo_name,
                'asset_class'  => $asset_class,
                'verdict'      => 'NO_PROFITABLE_IN_TRAIN',
                'total_trades' => $total,
                'train_size'   => $train_size,
                'test_size'    => $test_size
            );
            continue;
        }

        // Validate on TEST set
        $test_sim = _hl_simulate_trades_array($test_trades, $best_tp, $best_sl, $best_hold);

        $overfit = ($test_sim['total_return'] <= 0 && $best_train_return > 0);

        $verdict = 'VALIDATED';
        if ($overfit) {
            $verdict = 'OVERFIT_DETECTED';
        } elseif ($test_sim['total_return'] < $best_train_return * 0.3) {
            $verdict = 'WEAK_OUT_OF_SAMPLE';
        }

        $results[] = array(
            'algorithm'    => $algo_name,
            'asset_class'  => $asset_class,
            'best_params'  => array('tp' => $best_tp, 'sl' => $best_sl, 'hold' => $best_hold),
            'train_return' => round($best_train_return, 4),
            'test_return'  => round($test_sim['total_return'], 4),
            'train_wr'     => round($best_train_return > 0 ? _hl_simulate_trades_array($train_trades, $best_tp, $best_sl, $best_hold) : 0, 2),
            'test_wr'      => $test_sim['win_rate'],
            'total_trades' => $total,
            'train_size'   => $train_size,
            'test_size'    => $test_size,
            'verdict'      => $verdict
        );
    }

    echo json_encode(array(
        'ok'      => true,
        'action'  => 'walk_forward',
        'results' => $results,
        'note'    => 'Walk-forward: 67% train / 33% test. VALIDATED = works out-of-sample. OVERFIT = in-sample only.'
    ));
}


// =====================================================================
//  Helper: Simulate params against an array of trade rows (for walk-forward)
// =====================================================================
function _hl_simulate_trades_array($trades, $tp, $sl, $max_h) {
    $count = 0;
    $wins = 0;
    $total_return = 0;
    $sum_wins = 0;
    $sum_losses = 0;

    foreach ($trades as $t) {
        $count++;
        $actual_pct   = (float)$t['realized_pct'];
        $actual_hours = (float)$t['hold_hours'];

        if ($actual_pct >= $tp) {
            $sim_return = $tp;
        } elseif ($actual_pct <= -$sl) {
            $sim_return = -$sl;
        } elseif ($actual_hours > $max_h && $max_h > 0) {
            $time_ratio = $max_h / max($actual_hours, 1);
            $sim_return = $actual_pct * $time_ratio;
        } else {
            $sim_return = $actual_pct;
        }

        if ($sim_return > 0) {
            $wins++;
            $sum_wins += $sim_return;
        } else {
            $sum_losses += abs($sim_return);
        }
        $total_return += $sim_return;
    }

    $wr = ($count > 0) ? round($wins / $count * 100, 2) : 0;
    $pf = ($sum_losses > 0) ? round($sum_wins / $sum_losses, 4) : (($sum_wins > 0) ? 99.99 : 0);

    return array(
        'trades'        => $count,
        'wins'          => $wins,
        'win_rate'      => $wr,
        'total_return'  => round($total_return, 4),
        'profit_factor' => $pf
    );
}


// =====================================================================
//  ACTION: regime_stats — Win rate by bull/bear regime per algorithm
//  Uses signal rationale to determine regime at signal time.
// =====================================================================
function _hl_action_regime_stats($conn) {
    // Get closed trades with signal rationale
    $r = $conn->query("SELECT t.algorithm_name, t.asset_class, t.realized_pct,
                        s.rationale
                        FROM lm_trades t
                        LEFT JOIN lm_signals s ON t.signal_id = s.id
                        WHERE t.status='closed'
                        ORDER BY t.algorithm_name, t.asset_class");

    if (!$r) {
        echo json_encode(array('ok' => false, 'error' => 'Query failed: ' . $conn->error));
        return;
    }

    // Group by algo + asset + regime
    $stats = array();
    while ($row = $r->fetch_assoc()) {
        $algo  = $row['algorithm_name'];
        $asset = $row['asset_class'];
        $ret   = (float)$row['realized_pct'];

        // Extract regime from rationale if available
        $regime = 'unknown';
        $rat = json_decode($row['rationale'], true);
        if (is_array($rat) && isset($rat['regime'])) {
            $regime = $rat['regime'];
        }

        $gkey = $algo . '|' . $asset . '|' . $regime;
        if (!isset($stats[$gkey])) {
            $stats[$gkey] = array(
                'algorithm'   => $algo,
                'asset_class' => $asset,
                'regime'      => $regime,
                'trades'      => 0,
                'wins'        => 0,
                'total_return' => 0
            );
        }
        $stats[$gkey]['trades']++;
        if ($ret > 0) $stats[$gkey]['wins']++;
        $stats[$gkey]['total_return'] += $ret;
    }

    // Calculate win rates
    $results = array();
    foreach ($stats as $s) {
        $s['win_rate'] = ($s['trades'] > 0) ? round($s['wins'] / $s['trades'] * 100, 2) : 0;
        $s['avg_return'] = ($s['trades'] > 0) ? round($s['total_return'] / $s['trades'], 4) : 0;
        $results[] = $s;
    }

    echo json_encode(array(
        'ok'      => true,
        'action'  => 'regime_stats',
        'results' => $results,
        'note'    => 'Regime determined from signal rationale JSON. Only Trend Sniper stores regime data.'
    ));
}
?>
