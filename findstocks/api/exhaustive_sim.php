<?php
/**
 * Exhaustive Simulation Engine — Batched
 * Runs every permutation of TP, SL, hold period, direction (LONG/SHORT),
 * algorithm, and algorithm-combo portfolio across a full parameter grid.
 * Designed for batch execution via GitHub Actions (one HTTP call per batch).
 * PHP 5.2 compatible.
 *
 * Usage:
 *   GET .../exhaustive_sim.php?key=stocksrefresh2026&batch=0     — run batch 0
 *   GET .../exhaustive_sim.php?key=stocksrefresh2026&status=1    — check progress
 *   GET .../exhaustive_sim.php?key=stocksrefresh2026&results=1   — get final results
 *   GET .../exhaustive_sim.php?key=stocksrefresh2026&reset=1     — clear and restart
 */
$auth_key = isset($_GET['key']) ? $_GET['key'] : '';
if ($auth_key !== 'stocksrefresh2026') {
    header('HTTP/1.1 403 Forbidden');
    header('Content-Type: application/json');
    echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
    exit;
}

require_once dirname(__FILE__) . '/db_connect.php';

// ─── Ensure simulation table exists ───
$conn->query("CREATE TABLE IF NOT EXISTS simulation_grid (
    id INT AUTO_INCREMENT PRIMARY KEY,
    batch_id INT DEFAULT 0,
    direction VARCHAR(5) DEFAULT 'LONG',
    algorithm VARCHAR(80) DEFAULT '',
    algo_combo VARCHAR(255) DEFAULT '',
    tp DECIMAL(6,2),
    sl DECIMAL(6,2),
    hold_days INT,
    commission DECIMAL(6,2),
    regime VARCHAR(20) DEFAULT 'all',
    total_trades INT DEFAULT 0,
    winning_trades INT DEFAULT 0,
    win_rate DECIMAL(6,2) DEFAULT 0,
    total_return_pct DECIMAL(10,4) DEFAULT 0,
    final_value DECIMAL(12,2) DEFAULT 10000,
    max_drawdown_pct DECIMAL(8,4) DEFAULT 0,
    sharpe_ratio DECIMAL(8,4) DEFAULT 0,
    profit_factor DECIMAL(8,4) DEFAULT 0,
    total_pnl DECIMAL(12,2) DEFAULT 0,
    total_commissions DECIMAL(10,2) DEFAULT 0,
    created_at DATETIME,
    INDEX idx_dir (direction),
    INDEX idx_algo (algorithm),
    INDEX idx_ret (total_return_pct),
    INDEX idx_batch (batch_id)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS simulation_meta (
    meta_key VARCHAR(50) PRIMARY KEY,
    meta_value TEXT,
    updated_at DATETIME
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ─── Status check ───
if (isset($_GET['status'])) {
    $total_rows = 0;
    $r = $conn->query("SELECT COUNT(*) as c FROM simulation_grid");
    if ($r) { $row = $r->fetch_assoc(); $total_rows = (int)$row['c']; }

    $last_batch = 0;
    $r = $conn->query("SELECT MAX(batch_id) as mb FROM simulation_grid");
    if ($r) { $row = $r->fetch_assoc(); $last_batch = (int)$row['mb']; }

    $meta_r = $conn->query("SELECT meta_value FROM simulation_meta WHERE meta_key='total_combos'");
    $total_combos = 0;
    if ($meta_r && $row = $meta_r->fetch_assoc()) $total_combos = (int)$row['meta_value'];

    $meta_r2 = $conn->query("SELECT meta_value FROM simulation_meta WHERE meta_key='status'");
    $sim_status = 'unknown';
    if ($meta_r2 && $row = $meta_r2->fetch_assoc()) $sim_status = $row['meta_value'];

    echo json_encode(array(
        'ok' => true, 'status' => $sim_status,
        'completed_rows' => $total_rows, 'total_planned' => $total_combos,
        'last_batch' => $last_batch,
        'progress_pct' => ($total_combos > 0) ? round($total_rows / $total_combos * 100, 1) : 0
    ));
    $conn->close();
    exit;
}

// ─── Reset ───
if (isset($_GET['reset'])) {
    $conn->query("TRUNCATE TABLE simulation_grid");
    $now = date('Y-m-d H:i:s');
    $conn->query("REPLACE INTO simulation_meta (meta_key, meta_value, updated_at) VALUES ('status', 'ready', '$now')");
    $conn->query("REPLACE INTO simulation_meta (meta_key, meta_value, updated_at) VALUES ('total_combos', '0', '$now')");
    echo json_encode(array('ok' => true, 'message' => 'Simulation reset'));
    $conn->close();
    exit;
}

// ─── Results ───
if (isset($_GET['results'])) {
    $limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 50;
    $dir_filter = isset($_GET['direction']) ? $conn->real_escape_string($_GET['direction']) : '';
    $sort = isset($_GET['sort']) ? $_GET['sort'] : 'total_return_pct';
    $allowed_sorts = array('total_return_pct', 'win_rate', 'sharpe_ratio', 'profit_factor', 'total_pnl');
    if (!in_array($sort, $allowed_sorts)) $sort = 'total_return_pct';

    $where = " WHERE total_trades > 0";
    if ($dir_filter !== '') $where .= " AND direction='" . $conn->real_escape_string($dir_filter) . "'";

    // Top performers
    $top = array();
    $r = $conn->query("SELECT * FROM simulation_grid $where ORDER BY $sort DESC LIMIT $limit");
    if ($r) { while ($row = $r->fetch_assoc()) $top[] = $row; }

    // Worst performers
    $worst = array();
    $r = $conn->query("SELECT * FROM simulation_grid $where ORDER BY $sort ASC LIMIT 20");
    if ($r) { while ($row = $r->fetch_assoc()) $worst[] = $row; }

    // Summary stats
    $summary = array();
    $r = $conn->query("SELECT direction,
                        COUNT(*) as total_combos,
                        SUM(CASE WHEN total_return_pct > 0 THEN 1 ELSE 0 END) as profitable_combos,
                        AVG(total_return_pct) as avg_return,
                        MAX(total_return_pct) as best_return,
                        MIN(total_return_pct) as worst_return,
                        AVG(win_rate) as avg_win_rate,
                        MAX(sharpe_ratio) as best_sharpe
                       FROM simulation_grid $where GROUP BY direction");
    if ($r) { while ($row = $r->fetch_assoc()) $summary[$row['direction']] = $row; }

    // Best per algorithm
    $best_per_algo = array();
    $r = $conn->query("SELECT sg.* FROM simulation_grid sg
                       INNER JOIN (
                           SELECT algorithm, direction, MAX(total_return_pct) as best_ret
                           FROM simulation_grid $where GROUP BY algorithm, direction
                       ) bpa ON sg.algorithm = bpa.algorithm AND sg.direction = bpa.direction
                               AND sg.total_return_pct = bpa.best_ret
                       ORDER BY sg.total_return_pct DESC");
    if ($r) { while ($row = $r->fetch_assoc()) $best_per_algo[] = $row; }

    // Best combo portfolios
    $best_combos = array();
    $r = $conn->query("SELECT * FROM simulation_grid $where AND algo_combo != '' ORDER BY total_return_pct DESC LIMIT 20");
    if ($r) { while ($row = $r->fetch_assoc()) $best_combos[] = $row; }

    // Best short-selling strategies
    $best_shorts = array();
    $r = $conn->query("SELECT * FROM simulation_grid WHERE direction='SHORT' AND total_trades > 0 ORDER BY total_return_pct DESC LIMIT 20");
    if ($r) { while ($row = $r->fetch_assoc()) $best_shorts[] = $row; }

    // Heatmap data: TP vs SL for best hold_days (LONG)
    $heatmap = array();
    $r = $conn->query("SELECT tp, sl, hold_days, AVG(total_return_pct) as avg_ret, MAX(total_return_pct) as max_ret
                       FROM simulation_grid WHERE direction='LONG' AND total_trades > 0
                       GROUP BY tp, sl, hold_days ORDER BY avg_ret DESC LIMIT 200");
    if ($r) { while ($row = $r->fetch_assoc()) $heatmap[] = $row; }

    echo json_encode(array(
        'ok' => true,
        'summary' => $summary,
        'top_performers' => $top,
        'worst_performers' => $worst,
        'best_per_algorithm' => $best_per_algo,
        'best_combos' => $best_combos,
        'best_shorts' => $best_shorts,
        'heatmap' => $heatmap
    ));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════════
// ─── RUN A BATCH ───
// ═══════════════════════════════════════════════
$batch_num = isset($_GET['batch']) ? (int)$_GET['batch'] : 0;
$start_time = microtime(true);
$now = date('Y-m-d H:i:s');

// Update status
$conn->query("REPLACE INTO simulation_meta (meta_key, meta_value, updated_at) VALUES ('status', 'running', '$now')");

// ─── Define full parameter grid ───
$tp_values   = array(3, 5, 8, 10, 15, 20, 30, 50, 999);
$sl_values   = array(2, 3, 5, 8, 10, 15, 20, 999);
$hold_values = array(1, 2, 3, 5, 7, 10, 14, 20, 30);
$comm_values = array(0, 5, 10);
$directions  = array('LONG', 'SHORT');

// Get algorithms
$algo_names = array();
$res = $conn->query("SELECT DISTINCT algorithm_name FROM stock_picks WHERE entry_price > 0 ORDER BY algorithm_name");
if ($res) { while ($row = $res->fetch_assoc()) $algo_names[] = $row['algorithm_name']; }
$algo_names[] = ''; // Empty = all algorithms combined

// Build combo portfolios (pairs of algorithms)
$algo_combos = array();
$n = count($algo_names) - 1; // exclude the '' entry
for ($i = 0; $i < $n; $i++) {
    for ($j = $i + 1; $j < $n; $j++) {
        $algo_combos[] = $algo_names[$i] . ',' . $algo_names[$j];
    }
}
// Add "all combined" as a combo
$algo_combos[] = implode(',', array_slice($algo_names, 0, $n));

// Build the full permutation list
// Total: dirs(2) * algos(N+1) * tp(9) * sl(8) * hold(9) * comm(3) + combos
// That's potentially thousands — we batch them
$combos_per_batch = 30; // Do 30 combos per HTTP call (~1-2 seconds each)
$current_idx = 0;
$batch_start = $batch_num * $combos_per_batch;
$batch_end   = $batch_start + $combos_per_batch;
$ran = 0;
$results_in_batch = array();

// Pre-load all picks and prices into memory for speed
$all_picks = array();
$picks_res = $conn->query("SELECT sp.ticker, sp.algorithm_name, sp.entry_price, sp.pick_date, s.company_name
                           FROM stock_picks sp LEFT JOIN stocks s ON sp.ticker = s.ticker
                           WHERE sp.entry_price > 0 ORDER BY sp.pick_date ASC");
if ($picks_res) { while ($row = $picks_res->fetch_assoc()) $all_picks[] = $row; }

// Pre-load price data keyed by ticker
$all_prices = array();
$pres = $conn->query("SELECT ticker, trade_date, high_price, low_price, close_price
                      FROM daily_prices ORDER BY ticker, trade_date ASC");
if ($pres) {
    while ($row = $pres->fetch_assoc()) {
        $t = $row['ticker'];
        if (!isset($all_prices[$t])) $all_prices[$t] = array();
        $all_prices[$t][] = $row;
    }
}

// ─── In-memory backtest function ───
function _mem_backtest($picks, $prices, $tp, $sl, $hold, $comm, $direction, $algo_filter, $slip) {
    $capital = 10000;
    $peak = 10000;
    $max_dd = 0;
    $wins = 0; $losses = 0; $total_comm = 0;
    $returns_arr = array();

    foreach ($picks as $pick) {
        $algo = $pick['algorithm_name'];
        if ($algo_filter !== '' && strpos(',' . $algo_filter . ',', ',' . $algo . ',') === false) continue;

        $ticker = $pick['ticker'];
        $entry_raw = (float)$pick['entry_price'];
        $pick_date = $pick['pick_date'];

        if (!isset($prices[$ticker]) || count($prices[$ticker]) === 0) continue;

        // Find start index in price array
        $p_arr = $prices[$ticker];
        $start_idx = -1;
        $p_count = count($p_arr);
        for ($i = 0; $i < $p_count; $i++) {
            if ($p_arr[$i]['trade_date'] >= $pick_date) { $start_idx = $i; break; }
        }
        if ($start_idx < 0) continue;

        // Position sizing
        $pos_pct = 10;
        if ($direction === 'LONG') {
            $eff_entry = $entry_raw * (1 + $slip / 100);
        } else {
            $eff_entry = $entry_raw * (1 - $slip / 100);
        }
        $pos_val = $capital * ($pos_pct / 100);
        if ($pos_val < $eff_entry + $comm) continue;
        $shares = (int)floor(($pos_val - $comm) / $eff_entry);
        if ($shares <= 0) continue;

        $day_count = 0;
        $sold = false;
        $exit_p = $eff_entry;
        $day_close = 0;

        for ($d = $start_idx; $d < $p_count; $d++) {
            $day_count++;
            $dh = (float)$p_arr[$d]['high_price'];
            $dl = (float)$p_arr[$d]['low_price'];
            $day_close = (float)$p_arr[$d]['close_price'];

            if ($direction === 'LONG') {
                $sl_p = $eff_entry * (1 - $sl / 100);
                $tp_p = $eff_entry * (1 + $tp / 100);
                if ($sl < 999 && $dl <= $sl_p) { $exit_p = $sl_p; $sold = true; break; }
                if ($tp < 999 && $dh >= $tp_p) { $exit_p = $tp_p; $sold = true; break; }
            } else {
                $tp_p = $eff_entry * (1 - $tp / 100);
                $sl_p = $eff_entry * (1 + $sl / 100);
                if ($sl < 999 && $dh >= $sl_p) { $exit_p = $sl_p; $sold = true; break; }
                if ($tp < 999 && $dl <= $tp_p) { $exit_p = $tp_p; $sold = true; break; }
            }
            if ($day_count >= $hold) { $exit_p = $day_close; $sold = true; break; }
        }
        if (!$sold && $day_close > 0) $exit_p = $day_close;

        // Apply exit slippage
        if ($direction === 'LONG') {
            $eff_exit = $exit_p * (1 - $slip / 100);
            $gross = ($eff_exit - $eff_entry) * $shares;
        } else {
            $eff_exit = $exit_p * (1 + $slip / 100);
            $gross = ($eff_entry - $eff_exit) * $shares;
        }

        $net = $gross - ($comm * 2);
        $ret = ($eff_entry * $shares > 0) ? ($net / ($eff_entry * $shares)) * 100 : 0;
        $total_comm += $comm * 2;

        if ($net > 0) $wins++; else $losses++;
        $capital += $net;
        if ($capital > $peak) $peak = $capital;
        $dd = ($peak > 0) ? (($peak - $capital) / $peak) * 100 : 0;
        if ($dd > $max_dd) $max_dd = $dd;
        $returns_arr[] = $ret;
    }

    $total = $wins + $losses;
    $wr = ($total > 0) ? round($wins / $total * 100, 2) : 0;
    $total_ret = round(($capital - 10000) / 10000 * 100, 4);

    $sharpe = 0;
    if (count($returns_arr) > 1) {
        $mean = array_sum($returns_arr) / count($returns_arr);
        $var = 0;
        foreach ($returns_arr as $r) $var += ($r - $mean) * ($r - $mean);
        $std = sqrt($var / count($returns_arr));
        if ($std > 0) $sharpe = round(($mean / $std) * sqrt(252), 4);
    }

    $gw = 0; $gl = 0;
    // Approximate gross wins/losses from capital
    $pnl = round($capital - 10000, 2);

    $pf = 0;
    if ($losses > 0 && $wins > 0) {
        // Estimate PF from win rate and avg returns
        $avg_win = ($wins > 0) ? ($pnl > 0 ? $pnl / $wins : 0) : 0;
        $avg_loss = ($losses > 0 && $pnl < 0) ? abs($pnl) / $losses : 1;
        $pf = ($avg_loss > 0) ? round(abs($avg_win) / $avg_loss, 4) : 0;
    }

    return array(
        'total' => $total, 'wins' => $wins, 'losses' => $losses,
        'win_rate' => $wr, 'total_return_pct' => $total_ret,
        'final_value' => round($capital, 2), 'max_dd' => round($max_dd, 4),
        'sharpe' => $sharpe, 'pf' => $pf,
        'pnl' => $pnl, 'comm' => round($total_comm, 2)
    );
}

// ─── Iterate over the full grid ───
$total_planned = 0;

foreach ($directions as $dir) {
    // Single algorithms + all
    foreach ($algo_names as $algo) {
        foreach ($comm_values as $cmv) {
            foreach ($tp_values as $tpv) {
                foreach ($sl_values as $slv) {
                    foreach ($hold_values as $hdv) {
                        if ($current_idx >= $batch_start && $current_idx < $batch_end) {
                            // Run this combo
                            $bt = _mem_backtest($all_picks, $all_prices, $tpv, $slv, $hdv, $cmv, $dir, $algo, 0.5);
                            if ($bt['total'] > 0) {
                                $safe_algo = $conn->real_escape_string($algo);
                                $conn->query("INSERT INTO simulation_grid
                                    (batch_id, direction, algorithm, algo_combo, tp, sl, hold_days, commission,
                                     total_trades, winning_trades, win_rate, total_return_pct, final_value,
                                     max_drawdown_pct, sharpe_ratio, profit_factor, total_pnl, total_commissions, created_at)
                                    VALUES ($batch_num, '$dir', '$safe_algo', '', $tpv, $slv, $hdv, $cmv,
                                     {$bt['total']}, {$bt['wins']}, {$bt['win_rate']}, {$bt['total_return_pct']},
                                     {$bt['final_value']}, {$bt['max_dd']}, {$bt['sharpe']}, {$bt['pf']},
                                     {$bt['pnl']}, {$bt['comm']}, '$now')");
                                $results_in_batch[] = array('dir' => $dir, 'algo' => ($algo !== '' ? $algo : 'ALL'),
                                    'tp' => $tpv, 'sl' => $slv, 'hold' => $hdv, 'comm' => $cmv,
                                    'ret' => $bt['total_return_pct'], 'wr' => $bt['win_rate']);
                            }
                            $ran++;
                        }
                        $current_idx++;
                        $total_planned++;

                        // Safety: don't exceed 25 seconds
                        if (microtime(true) - $start_time > 25) break;
                    }
                    if (microtime(true) - $start_time > 25) break;
                }
                if (microtime(true) - $start_time > 25) break;
            }
            if (microtime(true) - $start_time > 25) break;
        }
        if (microtime(true) - $start_time > 25) break;
    }
    if (microtime(true) - $start_time > 25) break;

    // Combo portfolios
    foreach ($algo_combos as $combo) {
        foreach ($comm_values as $cmv) {
            // Only test key TP/SL/hold combos for combos (reduced grid)
            $combo_tp = array(5, 10, 20, 999);
            $combo_sl = array(3, 5, 10, 999);
            $combo_hd = array(2, 7, 14, 30);
            foreach ($combo_tp as $tpv) {
                foreach ($combo_sl as $slv) {
                    foreach ($combo_hd as $hdv) {
                        if ($current_idx >= $batch_start && $current_idx < $batch_end) {
                            $bt = _mem_backtest($all_picks, $all_prices, $tpv, $slv, $hdv, $cmv, $dir, $combo, 0.5);
                            if ($bt['total'] > 0) {
                                $safe_combo = $conn->real_escape_string($combo);
                                $conn->query("INSERT INTO simulation_grid
                                    (batch_id, direction, algorithm, algo_combo, tp, sl, hold_days, commission,
                                     total_trades, winning_trades, win_rate, total_return_pct, final_value,
                                     max_drawdown_pct, sharpe_ratio, profit_factor, total_pnl, total_commissions, created_at)
                                    VALUES ($batch_num, '$dir', '', '$safe_combo', $tpv, $slv, $hdv, $cmv,
                                     {$bt['total']}, {$bt['wins']}, {$bt['win_rate']}, {$bt['total_return_pct']},
                                     {$bt['final_value']}, {$bt['max_dd']}, {$bt['sharpe']}, {$bt['pf']},
                                     {$bt['pnl']}, {$bt['comm']}, '$now')");
                                $results_in_batch[] = array('dir' => $dir, 'algo' => 'COMBO:' . $combo,
                                    'tp' => $tpv, 'sl' => $slv, 'hold' => $hdv, 'comm' => $cmv,
                                    'ret' => $bt['total_return_pct'], 'wr' => $bt['win_rate']);
                            }
                            $ran++;
                        }
                        $current_idx++;
                        $total_planned++;
                        if (microtime(true) - $start_time > 25) break;
                    }
                    if (microtime(true) - $start_time > 25) break;
                }
                if (microtime(true) - $start_time > 25) break;
            }
            if (microtime(true) - $start_time > 25) break;
        }
        if (microtime(true) - $start_time > 25) break;
    }
    if (microtime(true) - $start_time > 25) break;
}

// Update meta
$conn->query("REPLACE INTO simulation_meta (meta_key, meta_value, updated_at) VALUES ('total_combos', '$total_planned', '$now')");
$total_batches = (int)ceil($total_planned / $combos_per_batch);
$is_done = ($batch_num >= $total_batches - 1) ? 'complete' : 'running';
$conn->query("REPLACE INTO simulation_meta (meta_key, meta_value, updated_at) VALUES ('status', '$is_done', '$now')");
$conn->query("REPLACE INTO simulation_meta (meta_key, meta_value, updated_at) VALUES ('last_batch', '$batch_num', '$now')");

$elapsed = round(microtime(true) - $start_time, 2);

echo json_encode(array(
    'ok' => true,
    'batch' => $batch_num,
    'combos_ran' => $ran,
    'total_planned' => $total_planned,
    'total_batches' => $total_batches,
    'next_batch' => ($is_done === 'complete') ? null : $batch_num + 1,
    'status' => $is_done,
    'elapsed_seconds' => $elapsed,
    'sample_results' => array_slice($results_in_batch, 0, 5)
));

// Audit
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'cron';
$detail = $conn->real_escape_string("ExhaustiveSim batch=$batch_num ran=$ran elapsed={$elapsed}s");
$conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('exhaustive_sim', '$detail', '$ip', '$now')");

$conn->close();
?>
