<?php
/**
 * Deep Analysis & Learning Engine
 * Finds top trades, optimal parameters, patterns, and self-tuning recommendations.
 * PHP 5.2 compatible.
 *
 * Usage:
 *   GET .../analyze.php?type=top_trades      — top/worst trades across all picks
 *   GET .../analyze.php?type=optimal_params   — grid search for best TP/SL/hold combo
 *   GET .../analyze.php?type=algo_report      — per-algorithm performance breakdown
 *   GET .../analyze.php?type=best_possible    — theoretical best trades from price data
 *   GET .../analyze.php?type=learning_recs    — self-tuning recommendations per algorithm
 */
require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/questrade_fees.php';

$type = isset($_GET['type']) ? trim($_GET['type']) : 'algo_report';
$fee_model = isset($_GET['fee_model']) ? $_GET['fee_model'] : 'questrade';
$response = array('ok' => true, 'type' => $type, 'fee_model' => $fee_model);

// ─── Helper: run a mini-backtest and return metrics ───
function _mini_backtest($conn, $algo_filter, $tp, $sl, $mhd, $commission, $fm) {
    if (!isset($fm)) $fm = 'questrade';
    $where_algo = '';
    if ($algo_filter !== '') {
        $escaped = array();
        $parts = explode(',', $algo_filter);
        foreach ($parts as $a) {
            $a = trim($a);
            if ($a !== '') $escaped[] = "'" . $conn->real_escape_string($a) . "'";
        }
        if (count($escaped) > 0) $where_algo = " AND sp.algorithm_name IN (" . implode(',', $escaped) . ")";
    }

    $sql = "SELECT sp.ticker, sp.algorithm_name, sp.entry_price, sp.pick_date, s.company_name
            FROM stock_picks sp LEFT JOIN stocks s ON sp.ticker = s.ticker
            WHERE sp.entry_price > 0 $where_algo ORDER BY sp.pick_date ASC";
    $res = $conn->query($sql);
    if (!$res) return null;

    $slip = 0.5;
    $trades = array();
    $wins = 0; $losses = 0; $total_pnl = 0; $total_comm = 0;

    while ($pick = $res->fetch_assoc()) {
        $ticker = $pick['ticker'];
        $entry = (float)$pick['entry_price'] * (1 + $slip / 100);
        $pick_date = $pick['pick_date'];

        $safe_t = $conn->real_escape_string($ticker);
        $safe_d = $conn->real_escape_string($pick_date);
        $pres = $conn->query("SELECT trade_date, high_price, low_price, close_price FROM daily_prices
                              WHERE ticker='$safe_t' AND trade_date >= '$safe_d' ORDER BY trade_date ASC LIMIT " . ($mhd + 5));

        $day_count = 0; $sold = false; $exit_p = $entry; $exit_d = $pick_date; $exit_r = 'end_of_data';
        $day_close = 0; $max_high = 0; $min_low = 999999;

        if ($pres && $pres->num_rows > 0) {
            while ($day = $pres->fetch_assoc()) {
                $day_count++;
                $dh = (float)$day['high_price']; $dl = (float)$day['low_price']; $day_close = (float)$day['close_price'];
                if ($dh > $max_high) $max_high = $dh;
                if ($dl < $min_low) $min_low = $dl;

                $tp_p = $entry * (1 + $tp / 100);
                $sl_p = $entry * (1 - $sl / 100);

                if ($sl < 999 && $dl <= $sl_p) { $exit_p = $sl_p; $exit_d = $day['trade_date']; $exit_r = 'stop_loss'; $sold = true; break; }
                if ($tp < 999 && $dh >= $tp_p) { $exit_p = $tp_p; $exit_d = $day['trade_date']; $exit_r = 'take_profit'; $sold = true; break; }
                if ($day_count >= $mhd) { $exit_p = $day_close; $exit_d = $day['trade_date']; $exit_r = 'max_hold'; $sold = true; break; }
            }
            if (!$sold && $day_count > 0) { $exit_p = $day_close; }
        }

        $eff_exit = $exit_p * (1 - $slip / 100);
        $gross = $eff_exit - $entry;

        // Use Questrade fee model
        $bf = questrade_calc_fees($ticker, $entry * 1, 1, false, $fm);
        $sf = questrade_calc_fees($ticker, $eff_exit * 1, 1, true, $fm);
        if ($fm === 'flat_10') { $bf['total_fee'] = $commission; $sf['total_fee'] = $commission; }
        $trade_comm = round($bf['total_fee'] + $sf['total_fee'], 2);

        $net = $gross - $trade_comm;
        $ret = ($entry > 0) ? ($net / $entry) * 100 : 0;

        $trades[] = array(
            'ticker' => $ticker, 'company' => $pick['company_name'], 'algo' => $pick['algorithm_name'],
            'entry_date' => $pick_date, 'exit_date' => $exit_d, 'entry' => round($entry, 2), 'exit' => round($eff_exit, 2),
            'net' => round($net, 2), 'return_pct' => round($ret, 4), 'exit_reason' => $exit_r,
            'hold_days' => $day_count, 'max_high' => round($max_high, 4), 'min_low' => round($min_low, 4),
            'has_cdr' => $bf['is_cdr'], 'forex_fee' => round($bf['forex_fee'] + $sf['forex_fee'], 2)
        );

        if ($net > 0) $wins++; else $losses++;
        $total_pnl += $net;
        $total_comm += $trade_comm;
    }

    $total = $wins + $losses;
    $wr = ($total > 0) ? round($wins / $total * 100, 2) : 0;

    return array('trades' => $trades, 'wins' => $wins, 'losses' => $losses, 'total' => $total,
                 'win_rate' => $wr, 'total_pnl' => round($total_pnl, 2), 'total_comm' => round($total_comm, 2));
}

// ═══════════ TOP TRADES ═══════════
if ($type === 'top_trades') {
    $bt = _mini_backtest($conn, '', 999, 999, 30, 10, $fee_model);
    if (!$bt) { $response['error'] = 'No data'; echo json_encode($response); $conn->close(); exit; }

    $trades = $bt['trades'];

    // Sort by return_pct descending
    $returns = array();
    $cnt = count($trades);
    for ($i = 0; $i < $cnt; $i++) $returns[$i] = $trades[$i]['return_pct'];
    arsort($returns);
    $top = array(); $bottom = array();
    $idx = 0;
    foreach ($returns as $k => $v) {
        if ($idx < 10) $top[] = $trades[$k];
        $idx++;
    }
    asort($returns);
    $idx = 0;
    foreach ($returns as $k => $v) {
        if ($idx < 10) $bottom[] = $trades[$k];
        $idx++;
    }

    // Best possible: look at max_high vs entry for each trade
    $best_possible = array();
    foreach ($trades as $t) {
        $max_gain = ($t['entry'] > 0 && $t['max_high'] > 0) ? round(($t['max_high'] - $t['entry']) / $t['entry'] * 100, 2) : 0;
        $max_loss = ($t['entry'] > 0 && $t['min_low'] > 0) ? round(($t['entry'] - $t['min_low']) / $t['entry'] * 100, 2) : 0;
        $best_possible[] = array(
            'ticker' => $t['ticker'], 'company' => $t['company'], 'algo' => $t['algo'],
            'entry_date' => $t['entry_date'], 'entry' => $t['entry'],
            'max_high' => $t['max_high'], 'max_gain_pct' => $max_gain,
            'min_low' => $t['min_low'], 'max_loss_pct' => $max_loss,
            'actual_return_pct' => $t['return_pct']
        );
    }
    // Sort best_possible by max_gain_pct desc
    $gains = array();
    $cnt = count($best_possible);
    for ($i = 0; $i < $cnt; $i++) $gains[$i] = $best_possible[$i]['max_gain_pct'];
    arsort($gains);
    $sorted_bp = array();
    foreach ($gains as $k => $v) $sorted_bp[] = $best_possible[$k];

    $response['top_winners'] = $top;
    $response['top_losers'] = $bottom;
    $response['best_possible_trades'] = array_slice($sorted_bp, 0, 10);

    echo json_encode($response); $conn->close(); exit;
}

// ═══════════ OPTIMAL PARAMS (Grid Search) ═══════════
if ($type === 'optimal_params') {
    $algo_filter = isset($_GET['algorithm']) ? trim($_GET['algorithm']) : '';
    $grid = array();
    $tp_values = array(3, 5, 8, 10, 15, 20, 30, 50, 999);
    $sl_values = array(2, 3, 5, 8, 10, 15, 20, 999);
    $hold_values = array(1, 2, 3, 5, 7, 14, 30);

    // Limit grid size to avoid timeout
    $best_combo = null;
    $best_return = -9999;
    $all_results = array();
    $count = 0;

    foreach ($tp_values as $tp) {
        foreach ($sl_values as $sl) {
            foreach ($hold_values as $hold) {
                $count++;
                if ($count > 200) break; // safety limit
                $bt = _mini_backtest($conn, $algo_filter, $tp, $sl, $hold, 10, $fee_model);
                if (!$bt || $bt['total'] === 0) continue;

                $result = array(
                    'tp' => $tp, 'sl' => $sl, 'hold' => $hold,
                    'trades' => $bt['total'], 'win_rate' => $bt['win_rate'],
                    'total_pnl' => $bt['total_pnl'], 'commissions' => $bt['total_comm']
                );
                $all_results[] = $result;

                if ($bt['total_pnl'] > $best_return) {
                    $best_return = $bt['total_pnl'];
                    $best_combo = $result;
                }
            }
            if ($count > 200) break;
        }
        if ($count > 200) break;
    }

    // Sort all results by total_pnl descending
    $pnls = array();
    $cnt = count($all_results);
    for ($i = 0; $i < $cnt; $i++) $pnls[$i] = $all_results[$i]['total_pnl'];
    arsort($pnls);
    $sorted = array();
    foreach ($pnls as $k => $v) $sorted[] = $all_results[$k];

    $response['algorithm'] = ($algo_filter !== '') ? $algo_filter : 'ALL';
    $response['best_combo'] = $best_combo;
    $response['top_10_combos'] = array_slice($sorted, 0, 10);
    $response['worst_5_combos'] = array_slice(array_reverse($sorted), 0, 5);
    $response['total_combos_tested'] = count($all_results);

    echo json_encode($response); $conn->close(); exit;
}

// ═══════════ PER-ALGORITHM REPORT ═══════════
if ($type === 'algo_report') {
    $algos = array();
    $res = $conn->query("SELECT DISTINCT algorithm_name FROM stock_picks WHERE entry_price > 0 ORDER BY algorithm_name");
    if ($res) { while ($row = $res->fetch_assoc()) $algos[] = $row['algorithm_name']; }

    $reports = array();
    foreach ($algos as $algo) {
        // 7-day hold
        $bt7 = _mini_backtest($conn, $algo, 999, 999, 7, 10, $fee_model);
        // 1-day hold
        $bt1 = _mini_backtest($conn, $algo, 999, 999, 1, 10, $fee_model);
        // With stops: 10/5/7
        $bt_stops = _mini_backtest($conn, $algo, 10, 5, 7, 10, $fee_model);

        $report = array(
            'algorithm' => $algo,
            'total_picks' => ($bt7) ? $bt7['total'] : 0,
            'hold_7d' => array(
                'win_rate' => ($bt7) ? $bt7['win_rate'] : 0,
                'total_pnl' => ($bt7) ? $bt7['total_pnl'] : 0,
                'wins' => ($bt7) ? $bt7['wins'] : 0,
                'losses' => ($bt7) ? $bt7['losses'] : 0
            ),
            'hold_1d' => array(
                'win_rate' => ($bt1) ? $bt1['win_rate'] : 0,
                'total_pnl' => ($bt1) ? $bt1['total_pnl'] : 0
            ),
            'with_stops_10_5_7' => array(
                'win_rate' => ($bt_stops) ? $bt_stops['win_rate'] : 0,
                'total_pnl' => ($bt_stops) ? $bt_stops['total_pnl'] : 0
            )
        );

        // Individual trades for this algo (7d)
        if ($bt7 && isset($bt7['trades'])) {
            $report['trades'] = $bt7['trades'];
        }

        $reports[] = $report;
    }

    $response['algorithms'] = $reports;
    echo json_encode($response); $conn->close(); exit;
}

// ═══════════ LEARNING RECOMMENDATIONS ═══════════
if ($type === 'learning_recs') {
    $algos = array();
    $res = $conn->query("SELECT DISTINCT algorithm_name FROM stock_picks WHERE entry_price > 0 ORDER BY algorithm_name");
    if ($res) { while ($row = $res->fetch_assoc()) $algos[] = $row['algorithm_name']; }

    $recommendations = array();
    foreach ($algos as $algo) {
        // Quick grid search for this algo
        $best = null; $best_pnl = -99999;
        $tp_vals = array(5, 10, 15, 20, 30, 999);
        $sl_vals = array(3, 5, 8, 10, 15, 999);
        $hold_vals = array(1, 2, 5, 7, 14, 30);

        foreach ($tp_vals as $tp) {
            foreach ($sl_vals as $sl) {
                foreach ($hold_vals as $hold) {
                    $bt = _mini_backtest($conn, $algo, $tp, $sl, $hold, 10, $fee_model);
                    if (!$bt || $bt['total'] === 0) continue;
                    if ($bt['total_pnl'] > $best_pnl) {
                        $best_pnl = $bt['total_pnl'];
                        $best = array('tp' => $tp, 'sl' => $sl, 'hold' => $hold,
                                      'pnl' => $bt['total_pnl'], 'win_rate' => $bt['win_rate']);
                    }
                }
            }
        }

        // Current default performance (7d hold, no stops)
        $default = _mini_backtest($conn, $algo, 999, 999, 7, 10, $fee_model);
        $default_pnl = ($default) ? $default['total_pnl'] : 0;
        $default_wr = ($default) ? $default['win_rate'] : 0;

        $status = 'unknown';
        $improvement = 0;
        if ($default_pnl > 0) {
            $status = 'profitable';
        } elseif ($best && $best['pnl'] > 0) {
            $status = 'fixable';
            $improvement = round($best['pnl'] - $default_pnl, 2);
        } else {
            $status = 'failing';
        }

        $rec = array(
            'algorithm' => $algo,
            'status' => $status,
            'current' => array('tp' => 'none', 'sl' => 'none', 'hold' => '7d', 'pnl' => $default_pnl, 'win_rate' => $default_wr),
            'recommended' => $best,
            'improvement_dollars' => ($best) ? round($best['pnl'] - $default_pnl, 2) : 0,
            'notes' => array()
        );

        // Generate specific notes
        if ($status === 'profitable') {
            $rec['notes'][] = 'Algorithm is profitable with default settings. Consider tighter stops to protect gains.';
        }
        if ($status === 'fixable' && $best) {
            $rec['notes'][] = 'Algorithm can be fixed. Switch to TP=' . ($best['tp'] >= 999 ? 'none' : $best['tp'] . '%') . ', SL=' . ($best['sl'] >= 999 ? 'none' : $best['sl'] . '%') . ', Hold=' . $best['hold'] . ' days.';
            $rec['notes'][] = 'Expected improvement: +$' . $improvement . ' per $10k capital.';
        }
        if ($status === 'failing') {
            $rec['notes'][] = 'Algorithm is losing money under ALL tested parameter combinations.';
            $rec['notes'][] = 'Consider: (1) suspending picks from this algo, (2) adding market regime filter, (3) more data needed.';
        }
        if ($default && $default['total'] < 5) {
            $rec['notes'][] = 'WARNING: Only ' . $default['total'] . ' trades — sample too small for reliable conclusions.';
        }

        $recommendations[] = $rec;
    }

    $response['recommendations'] = $recommendations;
    $response['summary'] = array(
        'profitable_algos' => 0,
        'fixable_algos' => 0,
        'failing_algos' => 0
    );
    foreach ($recommendations as $r) {
        if ($r['status'] === 'profitable') $response['summary']['profitable_algos']++;
        elseif ($r['status'] === 'fixable') $response['summary']['fixable_algos']++;
        else $response['summary']['failing_algos']++;
    }

    echo json_encode($response); $conn->close(); exit;
}

// ═══════════ BEST POSSIBLE TRADES ═══════════
if ($type === 'best_possible') {
    // For each stock, find the best buy/sell dates in the price history
    $stocks = array();
    $res = $conn->query("SELECT DISTINCT ticker FROM stock_picks");
    if ($res) { while ($row = $res->fetch_assoc()) $stocks[] = $row['ticker']; }

    $best_trades = array();
    foreach ($stocks as $ticker) {
        $safe_t = $conn->real_escape_string($ticker);
        // Get last 30 days of prices
        $pres = $conn->query("SELECT trade_date, open_price, high_price, low_price, close_price
                              FROM daily_prices WHERE ticker='$safe_t' ORDER BY trade_date DESC LIMIT 30");
        if (!$pres) continue;

        $prices = array();
        while ($row = $pres->fetch_assoc()) $prices[] = $row;
        $prices = array_reverse($prices); // chronological

        $cnt = count($prices);
        $best_buy_date = ''; $best_sell_date = ''; $best_gain = 0;

        // O(n^2) find best buy-then-sell
        for ($i = 0; $i < $cnt; $i++) {
            $buy = (float)$prices[$i]['low_price'];
            for ($j = $i + 1; $j < $cnt; $j++) {
                $sell = (float)$prices[$j]['high_price'];
                $gain = ($buy > 0) ? (($sell - $buy) / $buy) * 100 : 0;
                if ($gain > $best_gain) {
                    $best_gain = $gain;
                    $best_buy_date = $prices[$i]['trade_date'];
                    $best_sell_date = $prices[$j]['trade_date'];
                }
            }
        }

        // Also find best 1-week trade
        $best_week_gain = 0; $best_week_buy = ''; $best_week_sell = '';
        for ($i = 0; $i < $cnt; $i++) {
            $buy = (float)$prices[$i]['low_price'];
            $limit = ($i + 5 < $cnt) ? $i + 5 : $cnt - 1;
            for ($j = $i + 1; $j <= $limit; $j++) {
                $sell = (float)$prices[$j]['high_price'];
                $gain = ($buy > 0) ? (($sell - $buy) / $buy) * 100 : 0;
                if ($gain > $best_week_gain) {
                    $best_week_gain = $gain;
                    $best_week_buy = $prices[$i]['trade_date'];
                    $best_week_sell = $prices[$j]['trade_date'];
                }
            }
        }

        // Best 1-day trade
        $best_day_gain = 0; $best_day_date = '';
        for ($i = 0; $i < $cnt; $i++) {
            $day_gain = ((float)$prices[$i]['high_price'] - (float)$prices[$i]['low_price']);
            $day_pct = ((float)$prices[$i]['low_price'] > 0) ? ($day_gain / (float)$prices[$i]['low_price']) * 100 : 0;
            if ($day_pct > $best_day_gain) {
                $best_day_gain = $day_pct;
                $best_day_date = $prices[$i]['trade_date'];
            }
        }

        $best_trades[] = array(
            'ticker' => $ticker,
            'best_month' => array('buy_date' => $best_buy_date, 'sell_date' => $best_sell_date, 'gain_pct' => round($best_gain, 2)),
            'best_week' => array('buy_date' => $best_week_buy, 'sell_date' => $best_week_sell, 'gain_pct' => round($best_week_gain, 2)),
            'best_day' => array('date' => $best_day_date, 'gain_pct' => round($best_day_gain, 2))
        );
    }

    // Sort by best_month gain
    $month_gains = array();
    $cnt = count($best_trades);
    for ($i = 0; $i < $cnt; $i++) $month_gains[$i] = $best_trades[$i]['best_month']['gain_pct'];
    arsort($month_gains);
    $sorted = array();
    foreach ($month_gains as $k => $v) $sorted[] = $best_trades[$k];

    $response['best_trades'] = $sorted;

    echo json_encode($response); $conn->close(); exit;
}

$response['error'] = 'Unknown type. Use: top_trades, optimal_params, algo_report, best_possible, learning_recs';
echo json_encode($response);
$conn->close();
?>
