<?php
/**
 * Optimal Conditions Finder
 *
 * Runs a grid search across many TP/SL/hold-period/vol-filter/fee-model
 * combinations to find the parameter set that yields the best returns,
 * win rate, Sharpe, or profit factor.
 *
 * Returns all permutations sorted by the chosen metric so the UI can show
 * "which conditions won."
 *
 * PHP 5.2 compatible.
 *
 * Usage:
 *   GET .../optimal_finder.php                                 — run full grid, all algos
 *   GET .../optimal_finder.php?algorithms=Blue+Chip+Growth     — single algo
 *   GET .../optimal_finder.php?sort_by=sharpe_ratio            — sort by Sharpe
 *   GET .../optimal_finder.php?quick=1                         — reduced grid (faster)
 */
require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/questrade_fees.php';

// ─── Parameters ───
function _of_param($key, $default) {
    if (isset($_GET[$key]) && $_GET[$key] !== '') return $_GET[$key];
    if (isset($_POST[$key]) && $_POST[$key] !== '') return $_POST[$key];
    return $default;
}

$algorithms      = _of_param('algorithms', '');
$initial_capital = (float)_of_param('initial_capital', 10000);
$slippage        = (float)_of_param('slippage', 0.5);
$sort_by         = _of_param('sort_by', 'total_return_pct');
$quick_mode      = (int)_of_param('quick', 0);
$top_n           = (int)_of_param('top', 25);
$fee_model       = _of_param('fee_model', 'questrade');

$valid_sorts = array('total_return_pct', 'win_rate', 'sharpe_ratio', 'profit_factor', 'expectancy', 'final_value');
$found_sort = false;
foreach ($valid_sorts as $vs) {
    if ($vs === $sort_by) { $found_sort = true; break; }
}
if (!$found_sort) $sort_by = 'total_return_pct';

// ─── Build parameter grid ───
if ($quick_mode) {
    $tp_values   = array(5, 10, 20, 50, 999);
    $sl_values   = array(3, 5, 10, 999);
    $hold_values = array(1, 7, 30, 90);
    $vol_values  = array('off', 'skip_high');
    $comm_values = array(
        array('model' => 'questrade', 'comm' => 0),
        array('model' => 'flat_10',   'comm' => 10)
    );
} else {
    $tp_values   = array(3, 5, 10, 15, 20, 30, 50, 999);
    $sl_values   = array(2, 3, 5, 8, 10, 15, 999);
    $hold_values = array(1, 2, 7, 14, 30, 60, 90, 180);
    $vol_values  = array('off', 'skip_high', 'skip_elevated', 'calm_only');
    $comm_values = array(
        array('model' => 'questrade', 'comm' => 0),
        array('model' => 'flat_10',   'comm' => 10),
        array('model' => 'zero',      'comm' => 0)
    );
}

// ─── Load all picks once ───
$where_algo = '';
if ($algorithms !== '') {
    $algo_list = explode(',', $algorithms);
    $escaped = array();
    foreach ($algo_list as $a) {
        $a = trim($a);
        if ($a !== '') {
            $escaped[] = "'" . $conn->real_escape_string($a) . "'";
        }
    }
    if (count($escaped) > 0) {
        $where_algo = " AND sp.algorithm_name IN (" . implode(',', $escaped) . ")";
    }
}

$sql = "SELECT sp.ticker, sp.entry_price, sp.pick_date, sp.algorithm_name, s.company_name
        FROM stock_picks sp
        LEFT JOIN stocks s ON sp.ticker = s.ticker
        WHERE sp.entry_price > 0 $where_algo
        ORDER BY sp.pick_date ASC, sp.ticker ASC";
$picks_res = $conn->query($sql);
$all_picks = array();
if ($picks_res) {
    while ($row = $picks_res->fetch_assoc()) {
        $all_picks[] = $row;
    }
}

if (count($all_picks) === 0) {
    header('Content-Type: application/json');
    echo json_encode(array('ok' => false, 'error' => 'No picks found for the selected algorithms'));
    $conn->close();
    exit;
}

// ─── Load VIX data for vol filtering ───
$vix_data = array();
$vres = $conn->query("SELECT trade_date, vix_close, regime FROM market_regimes ORDER BY trade_date");
if ($vres) {
    while ($vr = $vres->fetch_assoc()) {
        $vix_data[$vr['trade_date']] = array('vix' => (float)$vr['vix_close'], 'regime' => $vr['regime']);
    }
}

// Helper: get VIX for a date (fallback to previous days)
function _of_get_vix($date) {
    global $vix_data;
    for ($i = 0; $i < 5; $i++) {
        $d = date('Y-m-d', strtotime($date) - ($i * 86400));
        if (isset($vix_data[$d])) return $vix_data[$d];
    }
    return array('vix' => 0, 'regime' => 'unknown');
}

// Helper: should skip trade based on vol filter
function _of_vol_skip($date, $filter_mode, $max_vix_val) {
    if ($filter_mode === 'off') return false;
    $v = _of_get_vix($date);
    $vix = $v['vix'];
    if ($vix <= 0) return false;
    if ($filter_mode === 'skip_high')     return ($vix >= 25);
    if ($filter_mode === 'skip_elevated') return ($vix >= 20);
    if ($filter_mode === 'calm_only')     return ($vix >= 16);
    if ($filter_mode === 'custom')        return ($vix >= $max_vix_val);
    return false;
}

// ─── Preload price data for all tickers ───
$ticker_prices = array();
$ticker_list = array();
foreach ($all_picks as $pk) {
    $t = $pk['ticker'];
    if (!isset($ticker_prices[$t])) {
        $ticker_prices[$t] = array();
        $ticker_list[] = $t;
    }
}
foreach ($ticker_list as $t) {
    $safe_t = $conn->real_escape_string($t);
    $pres = $conn->query("SELECT trade_date, high_price, low_price, close_price FROM daily_prices WHERE ticker='$safe_t' ORDER BY trade_date ASC");
    if ($pres) {
        while ($pr = $pres->fetch_assoc()) {
            $ticker_prices[$t][$pr['trade_date']] = array(
                'h' => (float)$pr['high_price'],
                'l' => (float)$pr['low_price'],
                'c' => (float)$pr['close_price']
            );
        }
    }
}

// ─── Fast inline backtest (no DB queries inside loop) ───
function fast_backtest($picks, $ticker_prices, $tp, $sl, $mhd, $cap, $comm_per_trade, $fee_mdl, $slip, $vol_mode) {
    $capital = $cap;
    $peak = $cap;
    $max_dd = 0;
    $total_trades = 0;
    $wins = 0;
    $losses = 0;
    $total_comm = 0;
    $total_wins_pct = 0;
    $total_losses_pct = 0;
    $gross_wins = 0;
    $gross_losses = 0;
    $returns = array();
    $vol_skipped = 0;
    $best_trade = null;
    $worst_trade = null;

    $pick_cnt = count($picks);
    for ($pi = 0; $pi < $pick_cnt; $pi++) {
        $pick = $picks[$pi];
        $ticker = $pick['ticker'];
        $entry = (float)$pick['entry_price'];
        $pick_date = $pick['pick_date'];
        $algo = $pick['algorithm_name'];

        if ($entry <= 0) continue;

        // Vol filter
        if (_of_vol_skip($pick_date, $vol_mode, 25)) {
            $vol_skipped++;
            continue;
        }

        $eff_entry = $entry * (1 + $slip / 100);
        $pos_val = $capital * 0.10; // 10% position size
        if ($pos_val < $eff_entry + $comm_per_trade) continue;
        $shares = (int)floor(($pos_val - $comm_per_trade) / $eff_entry);
        if ($shares <= 0) continue;

        // Calculate commission for this trade
        if ($fee_mdl === 'questrade') {
            $buy_val = $eff_entry * $shares;
            $buy_fees = questrade_calc_fees($ticker, 'buy', $buy_val, $shares);
            $buy_comm = $buy_fees['total'];
        } elseif ($fee_mdl === 'zero') {
            $buy_comm = 0;
        } else {
            $buy_comm = $comm_per_trade;
        }

        // Get price dates for this ticker starting from pick_date
        if (!isset($ticker_prices[$ticker])) continue;
        $prices = $ticker_prices[$ticker];
        $date_keys = array_keys($prices);
        $date_cnt = count($date_keys);

        // Find start index
        $start_idx = -1;
        for ($di = 0; $di < $date_cnt; $di++) {
            if ($date_keys[$di] >= $pick_date) {
                $start_idx = $di;
                break;
            }
        }
        if ($start_idx < 0) continue;

        $day_count = 0;
        $sold = false;
        $exit_p = $entry;
        $exit_d = $pick_date;
        $exit_r = 'end_of_data';

        $end_idx = min($start_idx + $mhd + 5, $date_cnt);
        for ($di = $start_idx; $di < $end_idx; $di++) {
            $day_count++;
            $dd = $date_keys[$di];
            $dh = $prices[$dd]['h'];
            $dl = $prices[$dd]['l'];
            $dc = $prices[$dd]['c'];

            $tp_p = $eff_entry * (1 + $tp / 100);
            $sl_p = $eff_entry * (1 - $sl / 100);

            if ($dl <= $sl_p && $sl < 999) {
                $exit_p = $sl_p; $exit_d = $dd; $exit_r = 'stop_loss'; $sold = true; break;
            }
            if ($dh >= $tp_p && $tp < 999) {
                $exit_p = $tp_p; $exit_d = $dd; $exit_r = 'take_profit'; $sold = true; break;
            }
            if ($day_count >= $mhd) {
                $exit_p = $dc; $exit_d = $dd; $exit_r = 'max_hold'; $sold = true; break;
            }
        }
        if (!$sold && $day_count > 0) {
            $last_d = $date_keys[min($start_idx + $day_count - 1, $date_cnt - 1)];
            $exit_p = $prices[$last_d]['c'];
            $exit_d = $last_d;
        }

        $eff_exit = $exit_p * (1 - $slip / 100);

        // Sell commission
        if ($fee_mdl === 'questrade') {
            $sell_val = $eff_exit * $shares;
            $sell_fees = questrade_calc_fees($ticker, 'sell', $sell_val, $shares);
            $sell_comm = $sell_fees['total'];
        } elseif ($fee_mdl === 'zero') {
            $sell_comm = 0;
        } else {
            $sell_comm = $comm_per_trade;
        }

        $gross_pnl = ($eff_exit - $eff_entry) * $shares;
        $comm_tot = $buy_comm + $sell_comm;
        $net_pnl = $gross_pnl - $comm_tot;
        $ret_pct = ($eff_entry * $shares > 0) ? ($net_pnl / ($eff_entry * $shares)) * 100 : 0;

        $total_trades++;
        $total_comm += $comm_tot;
        $capital += $net_pnl;
        $returns[] = $ret_pct;

        if ($net_pnl > 0) { $wins++; $total_wins_pct += $ret_pct; $gross_wins += $net_pnl; }
        else { $losses++; $total_losses_pct += abs($ret_pct); $gross_losses += abs($net_pnl); }

        if ($capital > $peak) $peak = $capital;
        $dd_pct = ($peak > 0) ? (($peak - $capital) / $peak) * 100 : 0;
        if ($dd_pct > $max_dd) $max_dd = $dd_pct;

        // Track best/worst trade
        if ($best_trade === null || $ret_pct > $best_trade['return_pct']) {
            $best_trade = array('ticker' => $ticker, 'algo' => $algo, 'entry_date' => $pick_date, 'exit_date' => $exit_d, 'return_pct' => round($ret_pct, 2), 'exit_reason' => $exit_r);
        }
        if ($worst_trade === null || $ret_pct < $worst_trade['return_pct']) {
            $worst_trade = array('ticker' => $ticker, 'algo' => $algo, 'entry_date' => $pick_date, 'exit_date' => $exit_d, 'return_pct' => round($ret_pct, 2), 'exit_reason' => $exit_r);
        }
    }

    // Metrics
    $wr = ($total_trades > 0) ? round($wins / $total_trades * 100, 2) : 0;
    $aw = ($wins > 0) ? round($total_wins_pct / $wins, 4) : 0;
    $al = ($losses > 0) ? round($total_losses_pct / $losses, 4) : 0;
    $pf = ($gross_losses > 0) ? round($gross_wins / $gross_losses, 4) : ($gross_wins > 0 ? 999 : 0);
    $lr = ($total_trades > 0) ? $losses / $total_trades : 0;
    $wrd = ($total_trades > 0) ? $wins / $total_trades : 0;
    $exp = round(($wrd * $aw) - ($lr * $al), 4);

    $sharpe = 0;
    if (count($returns) > 1) {
        $mean = array_sum($returns) / count($returns);
        $var = 0;
        foreach ($returns as $r) { $var += ($r - $mean) * ($r - $mean); }
        $std = sqrt($var / count($returns));
        if ($std > 0) $sharpe = round($mean / $std, 4);
    }

    $total_ret = ($cap > 0) ? round(($capital - $cap) / $cap * 100, 4) : 0;

    return array(
        'total_trades' => $total_trades,
        'winning_trades' => $wins,
        'losing_trades' => $losses,
        'win_rate' => $wr,
        'avg_win_pct' => $aw,
        'avg_loss_pct' => $al,
        'total_return_pct' => $total_ret,
        'final_value' => round($capital, 2),
        'max_drawdown_pct' => round($max_dd, 4),
        'total_commissions' => round($total_comm, 2),
        'sharpe_ratio' => $sharpe,
        'profit_factor' => $pf,
        'expectancy' => $exp,
        'vol_skipped' => $vol_skipped,
        'best_trade' => $best_trade,
        'worst_trade' => $worst_trade
    );
}

// ─── Run the grid search ───
$start_time = microtime(true);
$all_results = array();
$total_combos = 0;

foreach ($comm_values as $cv) {
    $fm = $cv['model'];
    $comm = $cv['comm'];

    foreach ($vol_values as $vf) {
        foreach ($tp_values as $tp) {
            foreach ($sl_values as $sl) {
                foreach ($hold_values as $hold) {
                    $total_combos++;

                    $result = fast_backtest($all_picks, $ticker_prices, $tp, $sl, $hold, $initial_capital, $comm, $fm, $slippage, $vf);

                    // Only include combos that had at least 1 trade
                    if ($result['total_trades'] === 0) continue;

                    $label_tp = ($tp >= 999) ? 'None' : ($tp . '%');
                    $label_sl = ($sl >= 999) ? 'None' : ($sl . '%');
                    $label_hold = $hold . 'd';
                    $label_vol = $vf;
                    $label_fm = $fm;

                    $all_results[] = array(
                        'params' => array(
                            'take_profit' => $tp,
                            'stop_loss' => $sl,
                            'max_hold_days' => $hold,
                            'vol_filter' => $vf,
                            'fee_model' => $fm,
                            'commission' => $comm,
                            'label' => 'TP:' . $label_tp . ' SL:' . $label_sl . ' Hold:' . $label_hold . ' Vol:' . $label_vol . ' Fee:' . $label_fm
                        ),
                        'summary' => $result
                    );
                }
            }
        }
    }
}

// ─── Sort by chosen metric ───
$sort_vals = array();
$cnt_r = count($all_results);
for ($i = 0; $i < $cnt_r; $i++) {
    $sort_vals[$i] = isset($all_results[$i]['summary'][$sort_by]) ? (float)$all_results[$i]['summary'][$sort_by] : 0;
}
arsort($sort_vals);

$sorted = array();
$rank = 0;
foreach ($sort_vals as $idx => $val) {
    $rank++;
    $entry = $all_results[$idx];
    $entry['rank'] = $rank;
    $sorted[] = $entry;
    if ($rank >= $top_n) break;
}

// Also find worst N for contrast
asort($sort_vals);
$worst = array();
$wrank = 0;
foreach ($sort_vals as $idx => $val) {
    $wrank++;
    $entry = $all_results[$idx];
    $entry['rank'] = $wrank;
    $worst[] = $entry;
    if ($wrank >= 5) break;
}

$elapsed = round(microtime(true) - $start_time, 2);

// ─── Assemble response ───
$response = array(
    'ok' => true,
    'algorithms' => $algorithms,
    'sort_by' => $sort_by,
    'total_permutations' => $total_combos,
    'total_with_trades' => $cnt_r,
    'elapsed_seconds' => $elapsed,
    'initial_capital' => $initial_capital,
    'total_picks' => count($all_picks),
    'top_results' => $sorted,
    'worst_results' => $worst,
    'grid_summary' => array(
        'tp_values' => $tp_values,
        'sl_values' => $sl_values,
        'hold_values' => $hold_values,
        'vol_filters' => $vol_values,
        'fee_models' => $comm_values
    )
);

// Audit log
$now = date('Y-m-d H:i:s');
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$detail = $conn->real_escape_string('Optimal finder: combos=' . $total_combos . ' with_trades=' . $cnt_r . ' sort=' . $sort_by . ' algo=' . $algorithms . ' elapsed=' . $elapsed . 's');
$conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('optimal_finder', '$detail', '$ip', '$now')");

header('Content-Type: application/json');
echo json_encode($response);
$conn->close();
?>
