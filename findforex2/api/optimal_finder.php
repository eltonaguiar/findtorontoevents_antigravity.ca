<?php
/**
 * Grid search for optimal forex backtest parameters
 * PHP 5.2 compatible. Optimized for shared hosting.
 */
error_reporting(E_ALL);
ini_set('display_errors', '1');
set_time_limit(120);
ini_set('memory_limit', '64M');

require_once dirname(__FILE__) . '/db_connect.php';

function _of_param($key, $default) {
    if (isset($_GET[$key]) && $_GET[$key] !== '') return $_GET[$key];
    if (isset($_POST[$key]) && $_POST[$key] !== '') return $_POST[$key];
    return $default;
}

$strategies_filter = _of_param('strategies', '');
$sort_by = _of_param('sort_by', 'total_return_pct');
$quick_mode = (int)_of_param('quick', 1);
$top_n = (int)_of_param('top', 10);
if ($top_n > 50) $top_n = 50;
$initial_capital = (float)_of_param('initial_capital', 10000);
$position_size_pct = 10;

$valid_sorts = array('total_return_pct', 'win_rate', 'sharpe_ratio', 'profit_factor', 'expectancy');
$found = false;
foreach ($valid_sorts as $vs) { if ($vs === $sort_by) { $found = true; break; } }
if (!$found) $sort_by = 'total_return_pct';

$start_time = microtime(true);

// ─── Grid ───
if ($quick_mode) {
    $tp_grid   = array(1, 3, 5, 10, 999);
    $sl_grid   = array(1, 2, 5, 999);
    $hold_grid = array(1, 7, 14, 30, 90);
    $spread_grid = array(1, 2, 3);
} else {
    $tp_grid   = array(0.5, 1, 2, 3, 5, 7, 10, 20, 999);
    $sl_grid   = array(0.5, 1, 2, 3, 5, 10, 999);
    $hold_grid = array(1, 3, 7, 14, 30, 60, 90);
    $spread_grid = array(1, 2, 3, 5);
}

// ─── Load signals ───
$where = '';
if ($strategies_filter !== '') {
    $parts = explode(',', $strategies_filter);
    $esc = array();
    foreach ($parts as $s) {
        $s = trim($s);
        if ($s !== '') $esc[] = "'" . $conn->real_escape_string($s) . "'";
    }
    if (count($esc) > 0) $where = " AND strategy_name IN (" . implode(',', $esc) . ")";
}

$signals = array();
$sr = $conn->query("SELECT pair, strategy_name, signal_date, entry_price, direction FROM fx_signals WHERE entry_price > 0 $where ORDER BY signal_date ASC");
if ($sr) { while ($row = $sr->fetch_assoc()) $signals[] = $row; }

if (count($signals) === 0) {
    echo json_encode(array('ok' => false, 'error' => 'No signals found. Run seed_signals.php first.'));
    $conn->close();
    exit;
}

// ─── Load prices into indexed arrays for fast lookup ───
$pair_dates = array(); // pair => array of dates
$pair_prices = array(); // pair => date => {o,h,l,c}

$pr = $conn->query("SELECT pair, trade_date, open_price, high_price, low_price, close_price FROM fx_prices ORDER BY pair, trade_date ASC");
if ($pr) {
    while ($row = $pr->fetch_assoc()) {
        $p = $row['pair'];
        if (!isset($pair_dates[$p])) {
            $pair_dates[$p] = array();
            $pair_prices[$p] = array();
        }
        $pair_dates[$p][] = $row['trade_date'];
        $pair_prices[$p][$row['trade_date']] = array(
            'o' => (float)$row['open_price'],
            'h' => (float)$row['high_price'],
            'l' => (float)$row['low_price'],
            'c' => (float)$row['close_price']
        );
    }
}

// Build date index maps: pair => date => index
$pair_date_idx = array();
foreach ($pair_dates as $p => $dates) {
    $pair_date_idx[$p] = array();
    $cnt = count($dates);
    for ($i = 0; $i < $cnt; $i++) {
        $pair_date_idx[$p][$dates[$i]] = $i;
    }
}

// ─── Load pip values ───
$pip_values = array();
$pvr = $conn->query("SELECT pair, pip_value FROM fx_pairs");
if ($pvr) { while ($r = $pvr->fetch_assoc()) $pip_values[$r['pair']] = (float)$r['pip_value']; }

// ─── Grid search ───
$all_results = array();
$total_perms = count($tp_grid) * count($sl_grid) * count($hold_grid) * count($spread_grid);

foreach ($tp_grid as $tp) {
    foreach ($sl_grid as $sl) {
        foreach ($hold_grid as $hold) {
            foreach ($spread_grid as $spread) {
                $capital = $initial_capital;
                $trades = 0; $wins = 0; $losses = 0;
                $peak = $initial_capital; $max_dd = 0;
                $returns = array();
                $gross_w = 0; $gross_l = 0;
                $tw_pct = 0; $tl_pct = 0;

                foreach ($signals as $sig) {
                    $pair = $sig['pair'];
                    if (!isset($pair_date_idx[$pair])) continue;
                    $entry_date = $sig['signal_date'];
                    if (!isset($pair_date_idx[$pair][$entry_date])) continue;

                    $ep = (float)$sig['entry_price'];
                    $si = $pair_date_idx[$pair][$entry_date];
                    $dates = $pair_dates[$pair];
                    $cnt = count($dates);

                    $tp_price = $ep * (1 + $tp / 100);
                    $sl_price = $ep * (1 - $sl / 100);
                    $pip = isset($pip_values[$pair]) ? $pip_values[$pair] : 0.0001;
                    $spread_cost_pct = ($spread * $pip / $ep) * 100;

                    $exit_p = 0; $hd = 0;
                    for ($i = $si; $i < $cnt; $i++) {
                        $hd++;
                        $d = $dates[$i];
                        $pd = $pair_prices[$pair][$d];

                        if ($pd['h'] >= $tp_price) { $exit_p = $tp_price; break; }
                        if ($pd['l'] <= $sl_price) { $exit_p = $sl_price; break; }
                        if ($hd >= $hold) { $exit_p = $pd['c']; break; }
                    }
                    if ($exit_p <= 0) continue;

                    $pos_val = $capital * ($position_size_pct / 100);
                    $ret = (($exit_p - $ep) / $ep) * 100;
                    $gross = $pos_val * ($ret / 100);
                    $sc = $pos_val * ($spread_cost_pct / 100);
                    $net = $gross - $sc;

                    $capital += $net;
                    $trades++;
                    $returns[] = $ret - $spread_cost_pct;

                    if ($net > 0) { $wins++; $tw_pct += $ret; $gross_w += $net; }
                    else { $losses++; $tl_pct += abs($ret); $gross_l += abs($net); }

                    if ($capital > $peak) $peak = $capital;
                    $dd = ($peak > 0) ? (($peak - $capital) / $peak) * 100 : 0;
                    if ($dd > $max_dd) $max_dd = $dd;
                }

                if ($trades === 0) continue;

                $wr = round($wins / $trades * 100, 2);
                $tr = round(($capital - $initial_capital) / $initial_capital * 100, 4);

                $sharpe = 0;
                if (count($returns) > 1) {
                    $mean = array_sum($returns) / count($returns);
                    $var = 0;
                    foreach ($returns as $r) { $var += ($r - $mean) * ($r - $mean); }
                    $std = sqrt($var / count($returns));
                    if ($std > 0) $sharpe = round($mean / $std, 4);
                }

                $pf = ($gross_l > 0) ? round($gross_w / $gross_l, 4) : ($gross_w > 0 ? 999 : 0);
                $aw = ($wins > 0) ? $tw_pct / $wins : 0;
                $al = ($losses > 0) ? $tl_pct / $losses : 0;
                $wr_d = ($trades > 0) ? $wins / $trades : 0;
                $lr_d = ($trades > 0) ? $losses / $trades : 0;
                $exp = round(($wr_d * $aw) - ($lr_d * $al), 4);

                $label = 'TP' . $tp . '/SL' . $sl . '/H' . $hold . '/Sp' . $spread;

                $all_results[] = array(
                    'rank' => 0,
                    'params' => array(
                        'take_profit' => $tp,
                        'stop_loss' => $sl,
                        'max_hold_days' => $hold,
                        'spread_pips' => $spread,
                        'label' => $label
                    ),
                    'summary' => array(
                        'total_trades' => $trades,
                        'winning_trades' => $wins,
                        'losing_trades' => $losses,
                        'win_rate' => $wr,
                        'total_return_pct' => $tr,
                        'sharpe_ratio' => $sharpe,
                        'max_drawdown_pct' => round($max_dd, 4),
                        'profit_factor' => $pf,
                        'expectancy' => $exp,
                        'final_value' => round($capital, 2)
                    )
                );
            }
        }
    }
}

// ─── Sort ───
function _of_cmp_return($a, $b) { if ($a['summary']['total_return_pct'] == $b['summary']['total_return_pct']) return 0; return ($a['summary']['total_return_pct'] > $b['summary']['total_return_pct']) ? -1 : 1; }
function _of_cmp_sharpe($a, $b) { if ($a['summary']['sharpe_ratio'] == $b['summary']['sharpe_ratio']) return 0; return ($a['summary']['sharpe_ratio'] > $b['summary']['sharpe_ratio']) ? -1 : 1; }
function _of_cmp_winrate($a, $b) { if ($a['summary']['win_rate'] == $b['summary']['win_rate']) return 0; return ($a['summary']['win_rate'] > $b['summary']['win_rate']) ? -1 : 1; }
function _of_cmp_pf($a, $b) { if ($a['summary']['profit_factor'] == $b['summary']['profit_factor']) return 0; return ($a['summary']['profit_factor'] > $b['summary']['profit_factor']) ? -1 : 1; }
function _of_cmp_exp($a, $b) { if ($a['summary']['expectancy'] == $b['summary']['expectancy']) return 0; return ($a['summary']['expectancy'] > $b['summary']['expectancy']) ? -1 : 1; }

if ($sort_by === 'sharpe_ratio') { usort($all_results, '_of_cmp_sharpe'); }
elseif ($sort_by === 'win_rate') { usort($all_results, '_of_cmp_winrate'); }
elseif ($sort_by === 'profit_factor') { usort($all_results, '_of_cmp_pf'); }
elseif ($sort_by === 'expectancy') { usort($all_results, '_of_cmp_exp'); }
else { usort($all_results, '_of_cmp_return'); }

// Assign ranks
$cnt = count($all_results);
for ($i = 0; $i < $cnt; $i++) { $all_results[$i]['rank'] = $i + 1; }

$top_results = array_slice($all_results, 0, $top_n);
$worst_results = array_slice($all_results, max(0, $cnt - 5));

$elapsed = round(microtime(true) - $start_time, 2);

$best_ret = ($cnt > 0) ? $all_results[0]['summary']['total_return_pct'] : 0;
$worst_ret = ($cnt > 0) ? $all_results[$cnt - 1]['summary']['total_return_pct'] : 0;

// Audit
$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : 'unknown';
$conn->query("INSERT INTO fx_audit_log (action_type, details, ip_address, created_at) VALUES ('optimal_finder','" . $conn->real_escape_string("Grid: $total_perms perms, $cnt valid, {$elapsed}s") . "','" . $conn->real_escape_string($ip) . "','" . date('Y-m-d H:i:s') . "')");

echo json_encode(array(
    'ok' => true,
    'total_permutations' => $total_perms,
    'valid_results' => $cnt,
    'elapsed_seconds' => $elapsed,
    'sort_by' => $sort_by,
    'quick_mode' => ($quick_mode === 1),
    'best_return_pct' => $best_ret,
    'worst_return_pct' => $worst_ret,
    'top_results' => $top_results,
    'worst_results' => $worst_results
));
$conn->close();
?>
