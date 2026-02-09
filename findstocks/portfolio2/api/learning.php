<?php
/**
 * Self-Adjusting Learning Algorithm Engine
 * Analyzes past performance and suggests parameter adjustments.
 * Creates "Learning" variants of each algorithm with auto-tuned parameters.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   analyze_and_adjust — Run full analysis and store recommended adjustments
 *   get_recommendations — View current recommendations without applying
 *   permutation_scan   — Run exhaustive parameter permutation scan
 *   bear_analysis      — Analyze short/bear market performance patterns
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'get_recommendations';

$response = array('ok' => true, 'action' => $action);

// ─── Helper: Run a quick inline backtest for a given algo/params combo ───
function quick_backtest($conn, $algo, $tp, $sl, $mhd, $cap, $comm, $slip) {
    $where = '';
    if ($algo !== '') {
        $safe = $conn->real_escape_string($algo);
        $where = " AND sp.algorithm_name = '$safe'";
    }
    $sql = "SELECT sp.entry_price, sp.pick_date, sp.ticker, sp.algorithm_name
            FROM stock_picks sp WHERE sp.entry_price > 0 $where
            ORDER BY sp.pick_date ASC";
    $res = $conn->query($sql);
    if (!$res || $res->num_rows === 0) {
        return array('trades' => 0, 'wins' => 0, 'return_pct' => 0, 'win_rate' => 0, 'avg_return' => 0, 'total_pnl' => 0);
    }

    $capital = $cap;
    $trades = 0;
    $wins = 0;
    $total_ret = 0;
    $total_pnl = 0;

    while ($pick = $res->fetch_assoc()) {
        $entry = (float)$pick['entry_price'] * (1 + $slip / 100);
        $pdate = $pick['pick_date'];
        $ticker = $pick['ticker'];
        $pos = $capital * 0.10;
        if ($pos < $entry + $comm) continue;
        $shares = (int)floor(($pos - $comm) / $entry);
        if ($shares <= 0) continue;

        $st = $conn->real_escape_string($ticker);
        $sd = $conn->real_escape_string($pdate);
        $pr = $conn->query("SELECT high_price, low_price, close_price, trade_date FROM daily_prices
                            WHERE ticker='$st' AND trade_date >= '$sd' ORDER BY trade_date ASC LIMIT " . ($mhd + 3));

        $dc = 0;
        $exit_p = $entry;
        $sold = false;
        $dclose = 0;
        if ($pr && $pr->num_rows > 0) {
            while ($d = $pr->fetch_assoc()) {
                $dc++;
                $dh = (float)$d['high_price'];
                $dl = (float)$d['low_price'];
                $dclose = (float)$d['close_price'];
                $tp_p = $entry * (1 + $tp / 100);
                $sl_p = $entry * (1 - $sl / 100);
                if ($dl <= $sl_p && $sl < 999) { $exit_p = $sl_p; $sold = true; break; }
                if ($dh >= $tp_p && $tp < 999) { $exit_p = $tp_p; $sold = true; break; }
                if ($dc >= $mhd) { $exit_p = $dclose; $sold = true; break; }
            }
            if (!$sold && $dc > 0 && $dclose > 0) $exit_p = $dclose;
        }

        $eff_exit = $exit_p * (1 - $slip / 100);
        $pnl = ($eff_exit - $entry) * $shares - $comm * 2;
        $rpct = ($entry * $shares > 0) ? ($pnl / ($entry * $shares)) * 100 : 0;

        $trades++;
        $total_ret += $rpct;
        $total_pnl += $pnl;
        if ($pnl > 0) $wins++;
        $capital += $pnl;
    }

    $wr = ($trades > 0) ? round($wins / $trades * 100, 2) : 0;
    $ar = ($trades > 0) ? round($total_ret / $trades, 4) : 0;
    $tr = ($cap > 0) ? round(($capital - $cap) / $cap * 100, 4) : 0;

    return array('trades' => $trades, 'wins' => $wins, 'return_pct' => $tr, 'win_rate' => $wr, 'avg_return' => $ar, 'total_pnl' => round($total_pnl, 2));
}

// ─── Action: Analyze and Adjust ───
if ($action === 'analyze_and_adjust' || $action === 'get_recommendations') {
    // Get all algorithms with picks
    $algo_res = $conn->query("SELECT DISTINCT algorithm_name FROM stock_picks WHERE entry_price > 0");
    $algo_list = array();
    if ($algo_res) {
        while ($r = $algo_res->fetch_assoc()) {
            $algo_list[] = $r['algorithm_name'];
        }
    }

    // Parameter grid to search
    $tp_grid = array(5, 10, 15, 20, 30, 50);
    $sl_grid = array(3, 5, 8, 10, 15);
    $hold_grid = array(1, 2, 5, 7, 14, 30);

    $recommendations = array();
    $adjustments_made = 0;

    foreach ($algo_list as $algo) {
        $best_return = -9999;
        $best_params = array('tp' => 10, 'sl' => 5, 'hold' => 7);
        $all_results = array();

        // Quick scan of parameter combinations
        foreach ($tp_grid as $tp) {
            foreach ($sl_grid as $sl) {
                foreach ($hold_grid as $hold) {
                    $r = quick_backtest($conn, $algo, $tp, $sl, $hold, 10000, 10, 0.5);
                    if ($r['trades'] > 0) {
                        $all_results[] = array('tp' => $tp, 'sl' => $sl, 'hold' => $hold, 'result' => $r);
                        if ($r['return_pct'] > $best_return) {
                            $best_return = $r['return_pct'];
                            $best_params = array('tp' => $tp, 'sl' => $sl, 'hold' => $hold);
                        }
                    }
                }
            }
        }

        // Current default performance
        $current = quick_backtest($conn, $algo, 10, 5, 7, 10000, 10, 0.5);

        // Categorize into profitable/losing parameter regions
        $profitable_combos = 0;
        $losing_combos = 0;
        foreach ($all_results as $ar) {
            if ($ar['result']['return_pct'] > 0) $profitable_combos++;
            else $losing_combos++;
        }

        $rec = array(
            'algorithm' => $algo,
            'current_performance' => $current,
            'best_params' => $best_params,
            'best_return_pct' => round($best_return, 4),
            'improvement_pct' => round($best_return - $current['return_pct'], 4),
            'profitable_combos' => $profitable_combos,
            'losing_combos' => $losing_combos,
            'total_combos_tested' => count($all_results),
            'verdict' => ''
        );

        // Verdict
        if ($best_return > 0) {
            $rec['verdict'] = 'PROFITABLE_PARAMS_EXIST';
        } elseif ($best_return > $current['return_pct']) {
            $rec['verdict'] = 'IMPROVABLE_BUT_STILL_LOSING';
        } else {
            $rec['verdict'] = 'NO_PROFITABLE_PARAMS_FOUND';
        }

        $recommendations[] = $rec;

        // Save to algorithm_performance table
        if ($action === 'analyze_and_adjust') {
            $now = date('Y-m-d H:i:s');
            $safe_algo = $conn->real_escape_string($algo);
            $safe_best = ($best_return > 0) ? 'Profitable with TP:' . $best_params['tp'] . '% SL:' . $best_params['sl'] . '% Hold:' . $best_params['hold'] . 'd' : 'No profitable params found';
            $safe_worst = $conn->real_escape_string('Current default: ' . $current['return_pct'] . '% return');
            $conn->query("INSERT INTO algorithm_performance (algorithm_name, strategy_type, total_picks, total_trades, win_rate, avg_return_pct, best_for, worst_for, updated_at)
                          VALUES ('$safe_algo', 'learning_scan', " . $current['trades'] . ", " . $current['trades'] . ", " . $current['win_rate'] . ", " . $current['avg_return'] . ", '$safe_best', '$safe_worst', '$now')
                          ON DUPLICATE KEY UPDATE total_picks=" . $current['trades'] . ", total_trades=" . $current['trades'] . ", win_rate=" . $current['win_rate'] . ", avg_return_pct=" . $current['avg_return'] . ", best_for='$safe_best', worst_for='$safe_worst', updated_at='$now'");
            $adjustments_made++;
        }
    }

    $response['recommendations'] = $recommendations;
    $response['adjustments_made'] = $adjustments_made;
    $response['total_algorithms'] = count($algo_list);
}

// ─── Action: Exhaustive Permutation Scan ───
if ($action === 'permutation_scan') {
    $tp_grid = array(3, 5, 7, 10, 15, 20, 25, 30, 40, 50, 75, 100, 999);
    $sl_grid = array(2, 3, 5, 7, 10, 15, 20, 30, 999);
    $hold_grid = array(1, 2, 3, 5, 7, 10, 14, 21, 30, 60, 90);

    $algo_filter = isset($_GET['algorithms']) ? trim($_GET['algorithms']) : '';
    $top_n = isset($_GET['top']) ? (int)$_GET['top'] : 20;
    if ($top_n < 5) $top_n = 5;
    if ($top_n > 100) $top_n = 100;

    $all_perms = array();
    $total_combos = count($tp_grid) * count($sl_grid) * count($hold_grid);
    $tested = 0;

    foreach ($tp_grid as $tp) {
        foreach ($sl_grid as $sl) {
            foreach ($hold_grid as $hold) {
                $r = quick_backtest($conn, $algo_filter, $tp, $sl, $hold, 10000, 10, 0.5);
                if ($r['trades'] > 0) {
                    $all_perms[] = array(
                        'take_profit' => $tp,
                        'stop_loss' => $sl,
                        'max_hold_days' => $hold,
                        'return_pct' => $r['return_pct'],
                        'win_rate' => $r['win_rate'],
                        'trades' => $r['trades'],
                        'total_pnl' => $r['total_pnl']
                    );
                }
                $tested++;
            }
        }
    }

    // Sort by return descending
    $returns_arr = array();
    $cnt = count($all_perms);
    for ($i = 0; $i < $cnt; $i++) {
        $returns_arr[$i] = $all_perms[$i]['return_pct'];
    }
    arsort($returns_arr);
    $sorted = array();
    $rank = 0;
    foreach ($returns_arr as $idx => $val) {
        $sorted[] = $all_perms[$idx];
        $rank++;
        if ($rank >= $top_n) break;
    }

    // Also get bottom N
    asort($returns_arr);
    $worst = array();
    $rank = 0;
    foreach ($returns_arr as $idx => $val) {
        $worst[] = $all_perms[$idx];
        $rank++;
        if ($rank >= 5) break;
    }

    // Stats
    $profitable = 0;
    $losing = 0;
    foreach ($all_perms as $p) {
        if ($p['return_pct'] > 0) $profitable++;
        else $losing++;
    }

    $response['total_combos'] = $total_combos;
    $response['tested'] = $tested;
    $response['profitable_combos'] = $profitable;
    $response['losing_combos'] = $losing;
    $response['profitability_rate'] = ($cnt > 0) ? round($profitable / $cnt * 100, 2) : 0;
    $response['algorithms'] = $algo_filter ? $algo_filter : 'ALL';
    $response['top_permutations'] = $sorted;
    $response['worst_permutations'] = $worst;
}

// ─── Action: Bear Market / Short Analysis ───
if ($action === 'bear_analysis') {
    // Identify stocks that declined - these would have been good SHORT candidates
    $sql = "SELECT sp.ticker, sp.algorithm_name, sp.pick_date, sp.entry_price, s.company_name
            FROM stock_picks sp
            LEFT JOIN stocks s ON sp.ticker = s.ticker
            WHERE sp.entry_price > 0
            ORDER BY sp.pick_date ASC";
    $picks = $conn->query($sql);

    $short_candidates = array();
    $long_losers = array();

    if ($picks) {
        while ($p = $picks->fetch_assoc()) {
            $ticker = $p['ticker'];
            $entry = (float)$p['entry_price'];
            $pdate = $p['pick_date'];

            $st = $conn->real_escape_string($ticker);
            $sd = $conn->real_escape_string($pdate);
            // Get latest available price
            $latest = $conn->query("SELECT close_price, trade_date FROM daily_prices WHERE ticker='$st' ORDER BY trade_date DESC LIMIT 1");
            if (!$latest || $latest->num_rows === 0) continue;
            $l = $latest->fetch_assoc();
            $current = (float)$l['close_price'];

            $change_pct = (($current - $entry) / $entry) * 100;

            $item = array(
                'ticker' => $ticker,
                'company' => isset($p['company_name']) ? $p['company_name'] : '',
                'algorithm' => $p['algorithm_name'],
                'pick_date' => $pdate,
                'entry_price' => round($entry, 2),
                'current_price' => round($current, 2),
                'change_pct' => round($change_pct, 2),
                'latest_date' => $l['trade_date']
            );

            if ($change_pct < -3) {
                // Would have been profitable as a SHORT
                $item['short_profit_pct'] = round(-$change_pct, 2);
                $short_candidates[] = $item;
            }
            if ($change_pct < 0) {
                $long_losers[] = $item;
            }
        }
    }

    // Sort short candidates by profit (descending)
    $sp_arr = array();
    $cnt_s = count($short_candidates);
    for ($i = 0; $i < $cnt_s; $i++) {
        $sp_arr[$i] = $short_candidates[$i]['short_profit_pct'];
    }
    arsort($sp_arr);
    $sorted_shorts = array();
    foreach ($sp_arr as $idx => $val) {
        $sorted_shorts[] = $short_candidates[$idx];
    }

    // Inverse algorithm concept
    $inverse_algos = array(
        array(
            'name' => 'Inverse Technical Momentum',
            'concept' => 'When Technical Momentum says BUY, go SHORT. This algorithm had the worst long performance, suggesting its picks tend to decline.',
            'based_on' => 'Technical Momentum',
            'strategy' => 'SHORT when original says BUY. Use inverted TP/SL: profit from decline, stop if price rises.'
        ),
        array(
            'name' => 'Inverse VAM (V2)',
            'concept' => 'Short stocks flagged by Volatility-Adjusted Momentum V2. 0% win rate on longs suggests bearish bias.',
            'based_on' => 'Volatility-Adjusted Momentum (V2)',
            'strategy' => 'SHORT immediately on signal. 5% profit target (decline), 10% stop loss (if rises).'
        ),
        array(
            'name' => 'Bear Sentiment Fade',
            'concept' => 'New algorithm: identify stocks with highest algorithmic conviction (score 90+) that are declining. Fade the optimism.',
            'based_on' => 'All algorithms',
            'strategy' => 'SHORT high-score picks that drop >2% on Day 1. Ride the momentum reversal.'
        )
    );

    $response['short_candidates'] = $sorted_shorts;
    $response['long_losers_count'] = count($long_losers);
    $response['total_picks'] = count($long_losers) + (count($short_candidates) > 0 ? count($short_candidates) : 0);
    $response['inverse_algorithms'] = $inverse_algos;
    $response['insight'] = 'With ' . count($long_losers) . ' out of picks declining, an inverse/short strategy would have captured these losses as gains. The system may be better at identifying stocks about to decline than stocks about to rise.';
}

// Audit log
$now = date('Y-m-d H:i:s');
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('learning', '" . $conn->real_escape_string($action) . "', '$ip', '$now')");

echo json_encode($response);
$conn->close();
?>
