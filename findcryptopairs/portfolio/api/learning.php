<?php
/**
 * Self-Adjusting Learning Algorithm for Crypto Pairs
 * Analyzes past performance and suggests parameter adjustments.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   analyze_and_adjust — Run full analysis and store recommended adjustments
 *   permutation_scan   — Run exhaustive parameter permutation scan
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'analyze_and_adjust';
$response = array('ok' => true, 'action' => $action);

function cr_quick_backtest($conn, $algo, $tp, $sl, $mhd, $cap) {
    $where = '';
    if ($algo !== '') {
        $safe = $conn->real_escape_string($algo);
        $where = " AND fp.algorithm_name = '$safe'";
    }
    $res = $conn->query("SELECT fp.entry_price, fp.pick_date, fp.symbol, fp.algorithm_name, fp.direction
                         FROM cr_pair_picks fp
                         WHERE fp.entry_price > 0 $where ORDER BY fp.pick_date ASC");
    if (!$res || $res->num_rows === 0) {
        return array('trades' => 0, 'wins' => 0, 'return_pct' => 0, 'win_rate' => 0, 'total_pnl' => 0);
    }

    $capital = $cap;
    $trades = 0; $wins = 0; $total_pnl = 0;
    $fee_pct = 0.1; // 0.1% trading fee

    while ($pick = $res->fetch_assoc()) {
        $eprice = (float)$pick['entry_price'];
        $pdate = $pick['pick_date'];
        $sym = $pick['symbol'];
        $dir = isset($pick['direction']) ? strtoupper($pick['direction']) : 'LONG';

        $pos = $capital * 0.20;
        if ($pos < 10) continue;
        $psize = round($pos / $eprice, 8);

        $ss = $conn->real_escape_string($sym);
        $sd = $conn->real_escape_string($pdate);
        $pr = $conn->query("SELECT high, low, close, price_date FROM cr_price_history WHERE symbol='$ss' AND price_date >= '$sd' ORDER BY price_date ASC LIMIT " . ($mhd + 3));

        $dc = 0; $exit_p = $eprice; $sold = false;
        if ($pr && $pr->num_rows > 0) {
            while ($d = $pr->fetch_assoc()) {
                $dc++;
                $dh = (float)$d['high'];
                $dl = (float)$d['low'];
                $dc_p = (float)$d['close'];

                if ($dir === 'SHORT') {
                    $worst_intra = (($eprice - $dh) / $eprice) * 100;
                    $best_intra  = (($eprice - $dl) / $eprice) * 100;
                } else {
                    $worst_intra = (($dl - $eprice) / $eprice) * 100;
                    $best_intra  = (($dh - $eprice) / $eprice) * 100;
                }

                if ($worst_intra <= -$sl && $sl < 999) {
                    if ($dir === 'SHORT') $exit_p = $eprice * (1 + $sl / 100);
                    else $exit_p = $eprice * (1 - $sl / 100);
                    $sold = true; break;
                }
                if ($best_intra >= $tp && $tp < 999) {
                    if ($dir === 'SHORT') $exit_p = $eprice * (1 - $tp / 100);
                    else $exit_p = $eprice * (1 + $tp / 100);
                    $sold = true; break;
                }
                if ($dc >= $mhd) { $exit_p = $dc_p; $sold = true; break; }
                $exit_p = $dc_p;
            }
        }

        if ($dir === 'SHORT') $gpnl = ($eprice - $exit_p) * $psize;
        else $gpnl = ($exit_p - $eprice) * $psize;

        $fees = round($eprice * $psize * $fee_pct / 100, 2) + round($exit_p * $psize * $fee_pct / 100, 2);
        $pnl = $gpnl - $fees;
        $trades++; $total_pnl += $pnl;
        if ($pnl > 0) $wins++;
        $capital += $pnl;
    }

    $wr = ($trades > 0) ? round($wins / $trades * 100, 2) : 0;
    $tr_pct = ($cap > 0) ? round(($capital - $cap) / $cap * 100, 4) : 0;
    return array('trades' => $trades, 'wins' => $wins, 'return_pct' => $tr_pct, 'win_rate' => $wr, 'total_pnl' => round($total_pnl, 2));
}

if ($action === 'analyze_and_adjust') {
    $algo_res = $conn->query("SELECT DISTINCT algorithm_name FROM cr_pair_picks WHERE entry_price > 0");
    $algo_list = array();
    if ($algo_res) { while ($r = $algo_res->fetch_assoc()) $algo_list[] = $r['algorithm_name']; }

    // Crypto-appropriate parameter grid (higher values than stocks)
    $tp_grid = array(5, 10, 15, 20, 30, 50, 100);
    $sl_grid = array(3, 5, 8, 10, 15, 20, 25);
    $hold_grid = array(3, 7, 14, 30, 60, 90, 180);

    $recommendations = array();
    foreach ($algo_list as $algo) {
        $best_return = -9999;
        $best_params = array('tp' => 20, 'sl' => 10, 'hold' => 90);
        $profitable = 0; $total_tested = 0;

        foreach ($tp_grid as $tp) {
            foreach ($sl_grid as $sl) {
                foreach ($hold_grid as $hold) {
                    $r = cr_quick_backtest($conn, $algo, $tp, $sl, $hold, 10000);
                    if ($r['trades'] > 0) {
                        $total_tested++;
                        if ($r['return_pct'] > 0) $profitable++;
                        if ($r['return_pct'] > $best_return) {
                            $best_return = $r['return_pct'];
                            $best_params = array('tp' => $tp, 'sl' => $sl, 'hold' => $hold);
                        }
                    }
                }
            }
        }

        $current = cr_quick_backtest($conn, $algo, 20, 10, 90, 10000);
        $verdict = 'NO_PROFITABLE_PARAMS_FOUND';
        if ($best_return > 0) $verdict = 'PROFITABLE_PARAMS_EXIST';
        elseif ($best_return > $current['return_pct']) $verdict = 'IMPROVABLE_BUT_STILL_LOSING';

        $recommendations[] = array(
            'algorithm' => $algo,
            'current_performance' => $current,
            'best_params' => $best_params,
            'best_return_pct' => round($best_return, 4),
            'profitable_combos' => $profitable,
            'total_combos_tested' => $total_tested,
            'verdict' => $verdict
        );

        $now = date('Y-m-d H:i:s');
        $sa = $conn->real_escape_string($algo);
        $bf = ($best_return > 0) ? 'Profitable: TP:' . $best_params['tp'] . '% SL:' . $best_params['sl'] . '% Hold:' . $best_params['hold'] . 'd' : 'No profitable params';
        $wf = $conn->real_escape_string('Default: ' . $current['return_pct'] . '%');
        $conn->query("INSERT INTO cr_algo_performance (algorithm_name, strategy_type, total_picks, total_trades, win_rate, avg_return_pct, best_for, worst_for, updated_at)
                      VALUES ('$sa', 'learning_scan', " . $current['trades'] . ", " . $current['trades'] . ", " . $current['win_rate'] . ", " . round($current['return_pct'], 4) . ", '" . $conn->real_escape_string($bf) . "', '$wf', '$now')
                      ON DUPLICATE KEY UPDATE total_trades=" . $current['trades'] . ", win_rate=" . $current['win_rate'] . ", avg_return_pct=" . round($current['return_pct'], 4) . ", best_for='" . $conn->real_escape_string($bf) . "', worst_for='$wf', updated_at='$now'");
    }

    $response['recommendations'] = $recommendations;
    $response['total_algorithms'] = count($algo_list);
}

if ($action === 'permutation_scan') {
    $tp_grid = array(3, 5, 8, 10, 15, 20, 25, 30, 50, 100, 999);
    $sl_grid = array(2, 3, 5, 8, 10, 15, 20, 25, 999);
    $hold_grid = array(1, 3, 7, 14, 21, 30, 60, 90, 180, 365);

    $algo_filter = isset($_GET['algorithms']) ? trim($_GET['algorithms']) : '';
    $top_n = isset($_GET['top']) ? (int)$_GET['top'] : 20;
    if ($top_n < 5) $top_n = 5; if ($top_n > 100) $top_n = 100;

    $all_perms = array();
    $tested = 0;

    foreach ($tp_grid as $tp) {
        foreach ($sl_grid as $sl) {
            foreach ($hold_grid as $hold) {
                $r = cr_quick_backtest($conn, $algo_filter, $tp, $sl, $hold, 10000);
                if ($r['trades'] > 0) {
                    $all_perms[] = array(
                        'take_profit' => $tp, 'stop_loss' => $sl, 'max_hold_days' => $hold,
                        'return_pct' => $r['return_pct'], 'win_rate' => $r['win_rate'],
                        'trades' => $r['trades'], 'total_pnl' => $r['total_pnl']
                    );
                }
                $tested++;
            }
        }
    }

    $ret_arr = array();
    $cnt = count($all_perms);
    for ($i = 0; $i < $cnt; $i++) $ret_arr[$i] = $all_perms[$i]['return_pct'];
    arsort($ret_arr);
    $sorted = array(); $rank = 0;
    foreach ($ret_arr as $idx => $val) { $sorted[] = $all_perms[$idx]; $rank++; if ($rank >= $top_n) break; }

    asort($ret_arr);
    $worst = array(); $rank = 0;
    foreach ($ret_arr as $idx => $val) { $worst[] = $all_perms[$idx]; $rank++; if ($rank >= 5) break; }

    $profitable = 0;
    foreach ($all_perms as $p) { if ($p['return_pct'] > 0) $profitable++; }

    $response['total_combos'] = count($tp_grid) * count($sl_grid) * count($hold_grid);
    $response['tested'] = $tested;
    $response['profitable_combos'] = $profitable;
    $response['profitability_rate'] = ($cnt > 0) ? round($profitable / $cnt * 100, 2) : 0;
    $response['algorithms'] = $algo_filter ? $algo_filter : 'ALL';
    $response['top_permutations'] = $sorted;
    $response['worst_permutations'] = $worst;
}

$now = date('Y-m-d H:i:s');
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$conn->query("INSERT INTO cr_audit_log (action_type, details, ip_address, created_at) VALUES ('learning', '" . $conn->real_escape_string($action) . "', '$ip', '$now')");

echo json_encode($response);
$conn->close();
?>
