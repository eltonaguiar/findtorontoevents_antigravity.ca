<?php
/**
 * Rolling Performance Weights API
 * Calculates 7-day and 30-day rolling win rates for each algorithm,
 * replacing static all-time averages in the consensus scoring system.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   refresh     — Recalculate rolling metrics for all algorithms
 *   dashboard   — Rolling vs all-time win rates side by side
 *   trend       — Is each algorithm trending up or down?
 *   get_weight  — Get blended rolling weight for a specific algorithm
 *
 * Usage:
 *   GET .../rolling_perf.php?action=refresh&key=stocksrefresh2026
 *   GET .../rolling_perf.php?action=dashboard
 *   GET .../rolling_perf.php?action=trend
 *   GET .../rolling_perf.php?action=get_weight&source=stock_picks&algorithm=CAN+SLIM
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'dashboard';
$response = array('ok' => true, 'action' => $action);
$admin_key = 'stocksrefresh2026';
$is_admin = (isset($_GET['key']) && $_GET['key'] === $admin_key);

// ═══════════════════════════════════════════════
// Auto-create table
// ═══════════════════════════════════════════════
$conn->query("CREATE TABLE IF NOT EXISTS algorithm_rolling_perf (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_table VARCHAR(30) NOT NULL DEFAULT 'stock_picks',
    algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
    period VARCHAR(10) NOT NULL DEFAULT '30d',
    calc_date DATE NOT NULL,
    total_picks INT NOT NULL DEFAULT 0,
    resolved_picks INT NOT NULL DEFAULT 0,
    wins INT NOT NULL DEFAULT 0,
    losses INT NOT NULL DEFAULT 0,
    win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    avg_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    avg_win_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    avg_loss_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    profit_factor DECIMAL(8,4) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    UNIQUE KEY idx_algo_period_date (source_table, algorithm_name, period, calc_date),
    KEY idx_date (calc_date),
    KEY idx_algo (algorithm_name)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ═══════════════════════════════════════════════
// Helper: Calculate rolling performance for a specific algo & period
// ═══════════════════════════════════════════════
function _rp_calc_rolling($conn, $source, $algo, $days) {
    $safe_algo = $conn->real_escape_string($algo);

    if ($source === 'stock_picks') {
        // stock_picks uses backtest_results for outcomes or daily_prices
        // We use the actual resolved picks approach: check if entry_price + daily_prices show win/loss
        $sql = "SELECT sp.ticker, sp.entry_price, sp.pick_date, sp.algorithm_name
                FROM stock_picks sp
                WHERE sp.algorithm_name = '$safe_algo'
                  AND sp.entry_price > 0
                  AND sp.pick_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY)
                ORDER BY sp.pick_date DESC";
        $res = $conn->query($sql);
        if (!$res || $res->num_rows === 0) {
            return array('total' => 0, 'resolved' => 0, 'wins' => 0, 'losses' => 0,
                         'win_rate' => 0, 'avg_return' => 0, 'avg_win' => 0, 'avg_loss' => 0, 'pf' => 0);
        }

        $wins = 0;
        $losses = 0;
        $total_gain = 0;
        $total_loss_amt = 0;
        $total_return = 0;
        $total = 0;
        $resolved = 0;

        while ($pick = $res->fetch_assoc()) {
            $total++;
            $entry = (float)$pick['entry_price'];
            $ticker = $pick['ticker'];
            $pdate = $pick['pick_date'];
            if ($entry <= 0) continue;

            // Look up latest price to determine outcome
            $st = $conn->real_escape_string($ticker);
            $sd = $conn->real_escape_string($pdate);
            $pr = $conn->query("SELECT close_price FROM daily_prices
                                WHERE ticker='$st' AND trade_date > '$sd'
                                ORDER BY trade_date DESC LIMIT 1");
            if ($pr && $pr->num_rows > 0) {
                $prow = $pr->fetch_assoc();
                $latest = (float)$prow['close_price'];
                if ($latest > 0) {
                    $resolved++;
                    $ret_pct = (($latest - $entry) / $entry) * 100;
                    $total_return += $ret_pct;
                    if ($ret_pct > 0) {
                        $wins++;
                        $total_gain += $ret_pct;
                    } else {
                        $losses++;
                        $total_loss_amt += abs($ret_pct);
                    }
                }
            }
        }

        $wr = ($resolved > 0) ? round($wins / $resolved * 100, 2) : 0;
        $avg_ret = ($resolved > 0) ? round($total_return / $resolved, 4) : 0;
        $avg_win = ($wins > 0) ? round($total_gain / $wins, 4) : 0;
        $avg_loss = ($losses > 0) ? round($total_loss_amt / $losses, 4) : 0;
        $pf = ($total_loss_amt > 0) ? round($total_gain / $total_loss_amt, 4) : ($total_gain > 0 ? 99.99 : 0);

        return array('total' => $total, 'resolved' => $resolved, 'wins' => $wins, 'losses' => $losses,
                     'win_rate' => $wr, 'avg_return' => $avg_ret, 'avg_win' => $avg_win, 'avg_loss' => $avg_loss, 'pf' => $pf);

    } else {
        // miracle_picks2 or miracle_picks3 have outcome column
        $table = ($source === 'miracle_picks3') ? 'miracle_picks3' : 'miracle_picks2';
        $sql = "SELECT outcome, outcome_pct FROM $table
                WHERE strategy_name = '$safe_algo'
                  AND outcome IN ('won','lost')
                  AND entry_price > 0
                  AND scan_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY)";
        $res = $conn->query($sql);
        if (!$res || $res->num_rows === 0) {
            return array('total' => 0, 'resolved' => 0, 'wins' => 0, 'losses' => 0,
                         'win_rate' => 0, 'avg_return' => 0, 'avg_win' => 0, 'avg_loss' => 0, 'pf' => 0);
        }

        $wins = 0;
        $losses = 0;
        $total_gain = 0;
        $total_loss_amt = 0;
        $total_return = 0;
        $resolved = 0;

        while ($row = $res->fetch_assoc()) {
            $resolved++;
            $pct = (float)$row['outcome_pct'];
            $total_return += $pct;
            if ($row['outcome'] === 'won') {
                $wins++;
                $total_gain += abs($pct);
            } else {
                $losses++;
                $total_loss_amt += abs($pct);
            }
        }

        $wr = ($resolved > 0) ? round($wins / $resolved * 100, 2) : 0;
        $avg_ret = ($resolved > 0) ? round($total_return / $resolved, 4) : 0;
        $avg_win = ($wins > 0) ? round($total_gain / $wins, 4) : 0;
        $avg_loss = ($losses > 0) ? round($total_loss_amt / $losses, 4) : 0;
        $pf = ($total_loss_amt > 0) ? round($total_gain / $total_loss_amt, 4) : ($total_gain > 0 ? 99.99 : 0);

        return array('total' => $resolved, 'resolved' => $resolved, 'wins' => $wins, 'losses' => $losses,
                     'win_rate' => $wr, 'avg_return' => $avg_ret, 'avg_win' => $avg_win, 'avg_loss' => $avg_loss, 'pf' => $pf);
    }
}

// ═══════════════════════════════════════════════
// ACTION: refresh — Recalculate for all algorithms
// ═══════════════════════════════════════════════
if ($action === 'refresh') {
    if (!$is_admin) {
        $response['ok'] = false;
        $response['error'] = 'Admin key required';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $today = date('Y-m-d');
    $now = date('Y-m-d H:i:s');
    $periods = array('7d' => 7, '30d' => 30);
    $processed = 0;

    // 1. stock_picks algorithms
    $ar = $conn->query("SELECT DISTINCT algorithm_name FROM stock_picks WHERE entry_price > 0");
    if ($ar) {
        while ($row = $ar->fetch_assoc()) {
            $algo = $row['algorithm_name'];
            foreach ($periods as $label => $days) {
                $perf = _rp_calc_rolling($conn, 'stock_picks', $algo, $days);
                $safe_algo = $conn->real_escape_string($algo);
                $conn->query("REPLACE INTO algorithm_rolling_perf
                    (source_table, algorithm_name, period, calc_date, total_picks, resolved_picks,
                     wins, losses, win_rate, avg_return_pct, avg_win_pct, avg_loss_pct, profit_factor, created_at)
                    VALUES ('stock_picks', '$safe_algo', '$label', '$today',
                    {$perf['total']}, {$perf['resolved']}, {$perf['wins']}, {$perf['losses']},
                    {$perf['win_rate']}, {$perf['avg_return']}, {$perf['avg_win']}, {$perf['avg_loss']},
                    {$perf['pf']}, '$now')");
            }
            $processed++;
        }
    }

    // 2. miracle_picks3 strategies
    $sr = $conn->query("SELECT DISTINCT strategy_name FROM miracle_picks3 WHERE entry_price > 0 AND outcome IN ('won','lost')");
    if ($sr) {
        while ($row = $sr->fetch_assoc()) {
            $strat = $row['strategy_name'];
            foreach ($periods as $label => $days) {
                $perf = _rp_calc_rolling($conn, 'miracle_picks3', $strat, $days);
                $safe_strat = $conn->real_escape_string($strat);
                $conn->query("REPLACE INTO algorithm_rolling_perf
                    (source_table, algorithm_name, period, calc_date, total_picks, resolved_picks,
                     wins, losses, win_rate, avg_return_pct, avg_win_pct, avg_loss_pct, profit_factor, created_at)
                    VALUES ('miracle_picks3', '$safe_strat', '$label', '$today',
                    {$perf['total']}, {$perf['resolved']}, {$perf['wins']}, {$perf['losses']},
                    {$perf['win_rate']}, {$perf['avg_return']}, {$perf['avg_win']}, {$perf['avg_loss']},
                    {$perf['pf']}, '$now')");
            }
            $processed++;
        }
    }

    // 3. miracle_picks2 strategies
    $sr2 = $conn->query("SELECT DISTINCT strategy_name FROM miracle_picks2 WHERE entry_price > 0 AND outcome IN ('won','lost')");
    if ($sr2) {
        while ($row = $sr2->fetch_assoc()) {
            $strat = $row['strategy_name'];
            foreach ($periods as $label => $days) {
                $perf = _rp_calc_rolling($conn, 'miracle_picks2', $strat, $days);
                $safe_strat = $conn->real_escape_string($strat);
                $conn->query("REPLACE INTO algorithm_rolling_perf
                    (source_table, algorithm_name, period, calc_date, total_picks, resolved_picks,
                     wins, losses, win_rate, avg_return_pct, avg_win_pct, avg_loss_pct, profit_factor, created_at)
                    VALUES ('miracle_picks2', '$safe_strat', '$label', '$today',
                    {$perf['total']}, {$perf['resolved']}, {$perf['wins']}, {$perf['losses']},
                    {$perf['win_rate']}, {$perf['avg_return']}, {$perf['avg_win']}, {$perf['avg_loss']},
                    {$perf['pf']}, '$now')");
            }
            $processed++;
        }
    }

    $response['processed'] = $processed;
    $response['date'] = $today;

} elseif ($action === 'dashboard') {
    // ═══════════════════════════════════════════════
    // ACTION: dashboard — Rolling vs all-time comparison
    // ═══════════════════════════════════════════════
    $source = isset($_GET['source']) ? trim($_GET['source']) : '';

    $where = '';
    if ($source !== '') {
        $where = " AND rp.source_table = '" . $conn->real_escape_string($source) . "'";
    }

    // Get latest 30d rolling for each algo
    $sql = "SELECT rp.source_table, rp.algorithm_name, rp.win_rate as rolling_30d_wr,
                   rp.avg_return_pct as rolling_30d_return, rp.profit_factor as rolling_30d_pf,
                   rp.resolved_picks as rolling_30d_trades, rp.calc_date
            FROM algorithm_rolling_perf rp
            WHERE rp.period = '30d' $where
            ORDER BY rp.source_table, rp.algorithm_name";
    $res = $conn->query($sql);

    $algos = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $key = $row['source_table'] . ':' . $row['algorithm_name'];

            // Get 7d rolling too
            $safe_src = $conn->real_escape_string($row['source_table']);
            $safe_algo = $conn->real_escape_string($row['algorithm_name']);
            $r7 = $conn->query("SELECT win_rate, avg_return_pct, profit_factor, resolved_picks
                                FROM algorithm_rolling_perf
                                WHERE source_table='$safe_src' AND algorithm_name='$safe_algo'
                                  AND period='7d' ORDER BY calc_date DESC LIMIT 1");
            $rolling_7d = ($r7 && $r7->num_rows > 0) ? $r7->fetch_assoc() : null;

            // Get all-time win rate from backtest_results or miracle_results
            $all_time_wr = 0;
            if ($row['source_table'] === 'stock_picks') {
                $atr = $conn->query("SELECT win_rate FROM backtest_results WHERE algorithm_filter='$safe_algo' ORDER BY id DESC LIMIT 1");
                if ($atr && $atr->num_rows > 0) {
                    $atrow = $atr->fetch_assoc();
                    $all_time_wr = (float)$atrow['win_rate'];
                }
            } elseif ($row['source_table'] === 'miracle_picks3') {
                $atr = $conn->query("SELECT win_rate FROM miracle_results3 WHERE strategy_name='$safe_algo' AND period='daily' ORDER BY id DESC LIMIT 1");
                if ($atr && $atr->num_rows > 0) {
                    $atrow = $atr->fetch_assoc();
                    $all_time_wr = (float)$atrow['win_rate'];
                }
            } elseif ($row['source_table'] === 'miracle_picks2') {
                $atr = $conn->query("SELECT win_rate FROM miracle_results2 WHERE strategy_name='$safe_algo' AND period='daily' ORDER BY id DESC LIMIT 1");
                if ($atr && $atr->num_rows > 0) {
                    $atrow = $atr->fetch_assoc();
                    $all_time_wr = (float)$atrow['win_rate'];
                }
            }

            $entry = array(
                'source' => $row['source_table'],
                'algorithm' => $row['algorithm_name'],
                'all_time_wr' => $all_time_wr,
                'rolling_30d_wr' => (float)$row['rolling_30d_wr'],
                'rolling_30d_return' => (float)$row['rolling_30d_return'],
                'rolling_30d_pf' => (float)$row['rolling_30d_pf'],
                'rolling_30d_trades' => (int)$row['rolling_30d_trades'],
                'rolling_7d_wr' => $rolling_7d ? (float)$rolling_7d['win_rate'] : 0,
                'rolling_7d_trades' => $rolling_7d ? (int)$rolling_7d['resolved_picks'] : 0,
                'calc_date' => $row['calc_date']
            );

            // Trend indicator
            $wr_diff = $entry['rolling_30d_wr'] - $all_time_wr;
            if ($wr_diff > 5) { $entry['trend'] = 'hot_streak'; }
            elseif ($wr_diff > 0) { $entry['trend'] = 'improving'; }
            elseif ($wr_diff > -5) { $entry['trend'] = 'stable'; }
            else { $entry['trend'] = 'cold_streak'; }

            // Blended weight for consensus (0.6 * rolling + 0.4 * all-time)
            $blended = round(0.6 * $entry['rolling_30d_wr'] + 0.4 * $all_time_wr, 2);
            $entry['blended_weight'] = $blended;

            $algos[] = $entry;
        }
    }

    // Sort by blended weight descending
    $bw_arr = array();
    for ($i = 0; $i < count($algos); $i++) $bw_arr[$i] = $algos[$i]['blended_weight'];
    arsort($bw_arr);
    $sorted = array();
    foreach ($bw_arr as $idx => $val) $sorted[] = $algos[$idx];

    $response['algorithms'] = $sorted;
    $response['count'] = count($sorted);

    // Summary stats
    $hot = 0;
    $cold = 0;
    foreach ($sorted as $a) {
        if ($a['trend'] === 'hot_streak') $hot++;
        if ($a['trend'] === 'cold_streak') $cold++;
    }
    $response['summary'] = array('hot_streak' => $hot, 'cold_streak' => $cold, 'total' => count($sorted));

} elseif ($action === 'trend') {
    // ═══════════════════════════════════════════════
    // ACTION: trend — Historical rolling performance trend
    // ═══════════════════════════════════════════════
    $source = isset($_GET['source']) ? trim($_GET['source']) : 'stock_picks';
    $algorithm = isset($_GET['algorithm']) ? trim($_GET['algorithm']) : '';
    $limit = isset($_GET['limit']) ? max(1, min(90, (int)$_GET['limit'])) : 30;

    if ($algorithm === '') {
        $response['ok'] = false;
        $response['error'] = 'Missing algorithm parameter';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $safe_src = $conn->real_escape_string($source);
    $safe_algo = $conn->real_escape_string($algorithm);

    $history = array();
    $hr = $conn->query("SELECT calc_date, period, win_rate, avg_return_pct, profit_factor, resolved_picks
                         FROM algorithm_rolling_perf
                         WHERE source_table='$safe_src' AND algorithm_name='$safe_algo'
                         ORDER BY calc_date DESC, period LIMIT " . ($limit * 2));
    if ($hr) {
        while ($row = $hr->fetch_assoc()) {
            $history[] = $row;
        }
    }

    $response['source'] = $source;
    $response['algorithm'] = $algorithm;
    $response['history'] = $history;
    $response['count'] = count($history);

} elseif ($action === 'get_weight') {
    // ═══════════════════════════════════════════════
    // ACTION: get_weight — Blended rolling weight for consensus
    // ═══════════════════════════════════════════════
    $source = isset($_GET['source']) ? trim($_GET['source']) : 'stock_picks';
    $algorithm = isset($_GET['algorithm']) ? trim($_GET['algorithm']) : '';

    if ($algorithm === '') {
        $response['ok'] = false;
        $response['error'] = 'Missing algorithm parameter';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $safe_src = $conn->real_escape_string($source);
    $safe_algo = $conn->real_escape_string($algorithm);

    // Get 30d rolling
    $r30 = $conn->query("SELECT win_rate FROM algorithm_rolling_perf
                          WHERE source_table='$safe_src' AND algorithm_name='$safe_algo' AND period='30d'
                          ORDER BY calc_date DESC LIMIT 1");
    $rolling_wr = ($r30 && $r30->num_rows > 0) ? (float)$r30->fetch_assoc() : 0;
    if (is_array($rolling_wr)) $rolling_wr = (float)$rolling_wr['win_rate'];

    // Get all-time
    $all_time_wr = 50; // default 50% if unknown
    if ($source === 'stock_picks') {
        $atr = $conn->query("SELECT win_rate FROM backtest_results WHERE algorithm_filter='$safe_algo' ORDER BY id DESC LIMIT 1");
        if ($atr && $atr->num_rows > 0) { $all_time_wr = (float)$atr->fetch_assoc(); if (is_array($all_time_wr)) $all_time_wr = (float)$all_time_wr['win_rate']; }
    } elseif ($source === 'miracle_picks3') {
        $atr = $conn->query("SELECT win_rate FROM miracle_results3 WHERE strategy_name='$safe_algo' ORDER BY id DESC LIMIT 1");
        if ($atr && $atr->num_rows > 0) { $atrow = $atr->fetch_assoc(); $all_time_wr = (float)$atrow['win_rate']; }
    } elseif ($source === 'miracle_picks2') {
        $atr = $conn->query("SELECT win_rate FROM miracle_results2 WHERE strategy_name='$safe_algo' ORDER BY id DESC LIMIT 1");
        if ($atr && $atr->num_rows > 0) { $atrow = $atr->fetch_assoc(); $all_time_wr = (float)$atrow['win_rate']; }
    }

    $blended = round(0.6 * $rolling_wr + 0.4 * $all_time_wr, 2);

    $response['source'] = $source;
    $response['algorithm'] = $algorithm;
    $response['rolling_30d_wr'] = $rolling_wr;
    $response['all_time_wr'] = $all_time_wr;
    $response['blended_weight'] = $blended;
    $response['weight_for_consensus'] = round($blended / 100, 4); // normalized 0-1
}

echo json_encode($response);
$conn->close();
