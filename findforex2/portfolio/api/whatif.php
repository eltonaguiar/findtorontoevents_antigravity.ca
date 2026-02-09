<?php
/**
 * What-If Analysis Engine for Forex Portfolio
 * Multi-scenario comparison, per-algorithm analysis.
 * PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/db_connect.php';

function _fxwi_param($key, $default) {
    if (isset($_POST[$key]) && $_POST[$key] !== '') return $_POST[$key];
    if (isset($_GET[$key]) && $_GET[$key] !== '') return $_GET[$key];
    return $default;
}

$scenario        = _fxwi_param('scenario', '');
$algorithms      = _fxwi_param('algorithms', '');
$tp_pips         = (float)_fxwi_param('take_profit_pips', 100);
$sl_pips         = (float)_fxwi_param('stop_loss_pips', 50);
$max_hold_days   = (int)_fxwi_param('max_hold_days', 30);
$initial_capital = (float)_fxwi_param('initial_capital', 10000);
$leverage        = (int)_fxwi_param('leverage', 10);
$spread_pips     = (float)_fxwi_param('spread_pips', 1.5);
$compare_mode    = (int)_fxwi_param('compare', 0);
$compare_algos   = (int)_fxwi_param('compare_algos', 0);

if ($leverage < 1) $leverage = 1;
if ($leverage > 50) $leverage = 50;

// --- Preset Scenarios (forex-appropriate) ---
$scenarios = array(
    'scalp_10pip'     => array('name' => 'Scalp 10 Pips',         'description' => 'Ultra-fast scalp, 10 pip target, 8 pip stop.',        'tp' => 10,   'sl' => 8,    'hold' => 1),
    'scalp_20pip'     => array('name' => 'Scalp 20 Pips',         'description' => 'Quick scalp, 20 pip target, 12 pip stop.',             'tp' => 20,   'sl' => 12,   'hold' => 1),
    'day_50pip'       => array('name' => 'Day Trade 50 Pips',     'description' => 'Intraday, 50 pip target, 30 pip stop.',                'tp' => 50,   'sl' => 30,   'hold' => 1),
    'day_100pip'      => array('name' => 'Day Trade 100 Pips',    'description' => 'Extended intraday, 100 pip target, 50 pip stop.',      'tp' => 100,  'sl' => 50,   'hold' => 3),
    'swing_200pip'    => array('name' => 'Swing 200 Pips',        'description' => 'Multi-day swing, 200 pip target, 80 pip stop.',        'tp' => 200,  'sl' => 80,   'hold' => 10),
    'swing_500pip'    => array('name' => 'Swing 500 Pips',        'description' => 'Large swing, 500 pip target, 150 pip stop.',           'tp' => 500,  'sl' => 150,  'hold' => 30),
    'carry_long'      => array('name' => 'Carry Trade Long',      'description' => 'Long-term carry, 300 pip target, 200 pip stop.',       'tp' => 300,  'sl' => 200,  'hold' => 60),
    'trend_follow'    => array('name' => 'Trend Following',       'description' => 'Ride the trend, 400 pip target, 120 pip stop.',        'tp' => 400,  'sl' => 120,  'hold' => 30),
    'conservative'    => array('name' => 'Conservative',          'description' => 'Tight risk, 80 pip target, 40 pip stop.',              'tp' => 80,   'sl' => 40,   'hold' => 14),
    'aggressive'      => array('name' => 'Aggressive',            'description' => 'Wide targets, high risk/reward. 250 pip TP, 60 pip SL.', 'tp' => 250, 'sl' => 60, 'hold' => 14)
);

// --- Inline backtest for forex ---
function run_fxp_backtest($conn, $algo_filter, $tp, $sl, $mhd, $cap, $lev, $spr, $pos_pct) {
    $where = '';
    if ($algo_filter !== '') {
        $alist = explode(',', $algo_filter);
        $esc = array();
        foreach ($alist as $a) {
            $a = trim($a);
            if ($a !== '') $esc[] = "'" . $conn->real_escape_string($a) . "'";
        }
        if (count($esc) > 0) $where = " AND fp.algorithm_name IN (" . implode(',', $esc) . ")";
    }

    $sql = "SELECT fp.*, p.pip_value, p.category
            FROM fxp_pair_picks fp LEFT JOIN fxp_pairs p ON fp.symbol = p.symbol
            WHERE fp.entry_price > 0 $where
            ORDER BY fp.pick_date ASC, fp.symbol ASC";
    $picks = $conn->query($sql);

    $result = array(
        'total_trades' => 0, 'winning_trades' => 0, 'losing_trades' => 0,
        'win_rate' => 0, 'total_return_pct' => 0, 'final_value' => $cap,
        'max_drawdown_pct' => 0, 'total_spread_cost' => 0, 'sharpe_ratio' => 0,
        'profit_factor' => 0, 'expectancy_pips' => 0, 'avg_hold_days' => 0,
        'avg_win_pips' => 0, 'avg_loss_pips' => 0,
        'best_trade_pips' => 0, 'worst_trade_pips' => 0,
        'trades' => array(), 'algo_breakdown' => array()
    );
    if (!$picks || $picks->num_rows === 0) return $result;

    $capital = $cap;
    $peak = $cap;
    $max_dd = 0;
    $tt = 0; $wins = 0; $losses = 0; $tspread = 0;
    $tw_pips = 0; $tl_pips = 0; $g_wins = 0; $g_losses = 0;
    $best_p = -9999; $worst_p = 9999; $t_hold = 0;
    $trades = array(); $returns = array(); $algo_s = array();

    if ($lev < 1) $lev = 1;
    if ($lev > 50) $lev = 50;

    while ($pick = $picks->fetch_assoc()) {
        $sym = $pick['symbol'];
        $eprice = (float)$pick['entry_price'];
        $pdate = $pick['pick_date'];
        $algo = $pick['algorithm_name'];
        $dir = isset($pick['direction']) ? strtoupper($pick['direction']) : 'LONG';
        $pip_val = isset($pick['pip_value']) ? (float)$pick['pip_value'] : 0.0001;
        if ($pip_val <= 0) $pip_val = 0.0001;

        $pos_val = $capital * ($pos_pct / 100) * $lev;
        $lot = round($pos_val / 100000, 4);
        if ($lot < 0.01) $lot = 0.01;
        $pip_dollar = $lot * 100000 * $pip_val;
        $scost = $spr * $pip_dollar;

        $ss = $conn->real_escape_string($sym);
        $sd = $conn->real_escape_string($pdate);
        $pr = $conn->query("SELECT price_date, high_price, low_price, close_price FROM fxp_price_history WHERE symbol='$ss' AND price_date >= '$sd' ORDER BY price_date ASC LIMIT " . ($mhd + 5));

        $dc = 0; $sold = false; $exit_p = $eprice; $exit_d = $pdate; $ex_r = 'end_of_data';
        if ($pr && $pr->num_rows > 0) {
            while ($d = $pr->fetch_assoc()) {
                $dc++;
                $dh = (float)$d['high_price'];
                $dl = (float)$d['low_price'];
                $dc_price = (float)$d['close_price'];
                $dd = $d['price_date'];

                if ($dir === 'LONG') {
                    $pips_best = ($dh - $eprice) / $pip_val;
                    $pips_worst = ($dl - $eprice) / $pip_val;
                } else {
                    $pips_best = ($eprice - $dl) / $pip_val;
                    $pips_worst = ($eprice - $dh) / $pip_val;
                }

                if ($pips_worst <= -$sl && $sl < 9999) {
                    if ($dir === 'LONG') $exit_p = $eprice - ($sl * $pip_val);
                    else $exit_p = $eprice + ($sl * $pip_val);
                    $exit_d = $dd; $ex_r = 'stop_loss'; $sold = true; break;
                }
                if ($pips_best >= $tp && $tp < 9999) {
                    if ($dir === 'LONG') $exit_p = $eprice + ($tp * $pip_val);
                    else $exit_p = $eprice - ($tp * $pip_val);
                    $exit_d = $dd; $ex_r = 'take_profit'; $sold = true; break;
                }
                if ($dc >= $mhd) {
                    $exit_p = $dc_price; $exit_d = $dd; $ex_r = 'max_hold'; $sold = true; break;
                }
            }
            if (!$sold && $dc > 0) {
                $exit_p = $dc_price;
            }
        }

        if ($dir === 'LONG') $raw_pips = ($exit_p - $eprice) / $pip_val;
        else $raw_pips = ($eprice - $exit_p) / $pip_val;
        $net_pips = $raw_pips - $spr;
        $npnl = $net_pips * $pip_dollar;
        $margin = ($capital * $pos_pct / 100);
        $rpct = ($margin > 0) ? ($npnl / $margin) * 100 : 0;

        $trades[] = array(
            'symbol' => $sym, 'direction' => $dir, 'algorithm' => $algo,
            'entry_date' => $pdate, 'entry_price' => round($eprice, 6),
            'exit_date' => $exit_d, 'exit_price' => round($exit_p, 6),
            'lot_size' => $lot, 'pip_profit' => round($net_pips, 2),
            'net_profit' => round($npnl, 2), 'return_pct' => round($rpct, 4),
            'exit_reason' => $ex_r, 'hold_days' => $dc
        );

        $tt++; $tspread += $scost; $capital += $npnl;
        $returns[] = $rpct; $t_hold += $dc;
        if ($net_pips > $best_p) $best_p = $net_pips;
        if ($net_pips < $worst_p) $worst_p = $net_pips;
        if ($npnl > 0) { $wins++; $tw_pips += $net_pips; $g_wins += $npnl; }
        else { $losses++; $tl_pips += abs($net_pips); $g_losses += abs($npnl); }
        if ($capital > $peak) $peak = $capital;
        $ddv = ($peak > 0) ? (($peak - $capital) / $peak) * 100 : 0;
        if ($ddv > $max_dd) $max_dd = $ddv;

        if (!isset($algo_s[$algo])) $algo_s[$algo] = array('t' => 0, 'w' => 0, 'l' => 0, 'pips' => 0, 'pnl' => 0);
        $algo_s[$algo]['t']++; $algo_s[$algo]['pips'] += $net_pips; $algo_s[$algo]['pnl'] += $npnl;
        if ($npnl > 0) $algo_s[$algo]['w']++; else $algo_s[$algo]['l']++;
    }

    $wr = ($tt > 0) ? round($wins / $tt * 100, 2) : 0;
    $awp = ($wins > 0) ? round($tw_pips / $wins, 2) : 0;
    $alp = ($losses > 0) ? round($tl_pips / $losses, 2) : 0;
    $pf = ($g_losses > 0) ? round($g_wins / $g_losses, 4) : ($g_wins > 0 ? 999 : 0);
    $exp_p = round((($tt > 0 ? $wins / $tt : 0) * $awp) - (($tt > 0 ? $losses / $tt : 0) * $alp), 4);
    $ah = ($tt > 0) ? round($t_hold / $tt, 2) : 0;

    $sharpe = 0;
    if (count($returns) > 1) {
        $mean = array_sum($returns) / count($returns);
        $var = 0;
        foreach ($returns as $r) { $var += ($r - $mean) * ($r - $mean); }
        $std = sqrt($var / count($returns));
        if ($std > 0) $sharpe = round($mean / $std, 4);
    }

    $total_ret = ($cap > 0) ? round(($capital - $cap) / $cap * 100, 4) : 0;

    $ab = array();
    foreach ($algo_s as $aname => $as) {
        $ab[] = array(
            'algorithm' => $aname,
            'trades' => $as['t'], 'wins' => $as['w'], 'losses' => $as['l'],
            'win_rate' => ($as['t'] > 0) ? round($as['w'] / $as['t'] * 100, 2) : 0,
            'avg_pips' => ($as['t'] > 0) ? round($as['pips'] / $as['t'], 2) : 0,
            'total_pnl' => round($as['pnl'], 2)
        );
    }

    return array(
        'total_trades' => $tt, 'winning_trades' => $wins, 'losing_trades' => $losses,
        'win_rate' => $wr, 'avg_win_pips' => $awp, 'avg_loss_pips' => $alp,
        'total_return_pct' => $total_ret, 'final_value' => round($capital, 2),
        'max_drawdown_pct' => round($max_dd, 4), 'total_spread_cost' => round($tspread, 2),
        'sharpe_ratio' => $sharpe, 'profit_factor' => $pf, 'expectancy_pips' => $exp_p,
        'avg_hold_days' => $ah, 'best_trade_pips' => ($tt > 0) ? round($best_p, 2) : 0,
        'worst_trade_pips' => ($tt > 0) ? round($worst_p, 2) : 0,
        'trades' => $trades, 'algo_breakdown' => $ab
    );
}

// --- Compare All Scenarios ---
if ($compare_mode === 1) {
    $comparison = array();
    foreach ($scenarios as $key => $sc) {
        $r = run_fxp_backtest($conn, $algorithms, $sc['tp'], $sc['sl'], $sc['hold'], $initial_capital, $leverage, $spread_pips, 3);
        $comparison[] = array(
            'scenario_key' => $key, 'name' => $sc['name'], 'description' => $sc['description'],
            'params' => array('take_profit_pips' => $sc['tp'], 'stop_loss_pips' => $sc['sl'], 'max_hold_days' => $sc['hold']),
            'summary' => array(
                'total_trades' => $r['total_trades'], 'win_rate' => $r['win_rate'],
                'total_return_pct' => $r['total_return_pct'], 'final_value' => $r['final_value'],
                'max_drawdown_pct' => $r['max_drawdown_pct'], 'total_spread_cost' => $r['total_spread_cost'],
                'sharpe_ratio' => $r['sharpe_ratio'], 'profit_factor' => $r['profit_factor'],
                'expectancy_pips' => $r['expectancy_pips'], 'avg_hold_days' => $r['avg_hold_days'],
                'avg_win_pips' => $r['avg_win_pips'], 'avg_loss_pips' => $r['avg_loss_pips'],
                'best_trade_pips' => $r['best_trade_pips'], 'worst_trade_pips' => $r['worst_trade_pips']
            )
        );
    }

    $ret_arr = array();
    $cnt = count($comparison);
    for ($i = 0; $i < $cnt; $i++) $ret_arr[$i] = $comparison[$i]['summary']['total_return_pct'];
    arsort($ret_arr);
    $sorted = array();
    foreach ($ret_arr as $idx => $val) $sorted[] = $comparison[$idx];

    echo json_encode(array('ok' => true, 'mode' => 'comparison', 'algorithms' => $algorithms, 'initial_capital' => $initial_capital, 'leverage' => $leverage, 'scenarios' => $sorted));
    $conn->close();
    exit;
}

// --- Compare Algorithms ---
if ($compare_algos === 1) {
    $algo_res = $conn->query("SELECT DISTINCT algorithm_name FROM fxp_pair_picks WHERE entry_price > 0 ORDER BY algorithm_name");
    $algo_list = array();
    if ($algo_res) { while ($ar = $algo_res->fetch_assoc()) $algo_list[] = $ar['algorithm_name']; }

    $tp_use = $tp_pips; $sl_use = $sl_pips; $mhd_use = $max_hold_days;
    if ($scenario !== '' && isset($scenarios[$scenario])) {
        $sc = $scenarios[$scenario];
        $tp_use = $sc['tp']; $sl_use = $sc['sl']; $mhd_use = $sc['hold'];
    }

    $algo_comp = array();
    foreach ($algo_list as $aname) {
        $r = run_fxp_backtest($conn, $aname, $tp_use, $sl_use, $mhd_use, $initial_capital, $leverage, $spread_pips, 3);
        $algo_comp[] = array(
            'algorithm' => $aname,
            'params' => array('take_profit_pips' => $tp_use, 'stop_loss_pips' => $sl_use, 'max_hold_days' => $mhd_use),
            'summary' => array(
                'total_trades' => $r['total_trades'], 'win_rate' => $r['win_rate'],
                'total_return_pct' => $r['total_return_pct'], 'final_value' => $r['final_value'],
                'max_drawdown_pct' => $r['max_drawdown_pct'], 'sharpe_ratio' => $r['sharpe_ratio'],
                'profit_factor' => $r['profit_factor'], 'expectancy_pips' => $r['expectancy_pips'],
                'avg_hold_days' => $r['avg_hold_days']
            )
        );
    }

    $ret2 = array();
    $cnt2 = count($algo_comp);
    for ($i = 0; $i < $cnt2; $i++) $ret2[$i] = $algo_comp[$i]['summary']['total_return_pct'];
    arsort($ret2);
    $sorted2 = array();
    foreach ($ret2 as $idx => $val) $sorted2[] = $algo_comp[$idx];

    echo json_encode(array('ok' => true, 'mode' => 'algorithm_comparison', 'scenario' => $scenario, 'initial_capital' => $initial_capital, 'leverage' => $leverage, 'algorithms' => $sorted2));
    $conn->close();
    exit;
}

// --- Single Scenario ---
if ($scenario !== '' && isset($scenarios[$scenario])) {
    $sc = $scenarios[$scenario];
    $tp_pips = $sc['tp']; $sl_pips = $sc['sl']; $max_hold_days = $sc['hold'];
}

$result = run_fxp_backtest($conn, $algorithms, $tp_pips, $sl_pips, $max_hold_days, $initial_capital, $leverage, $spread_pips, 3);

$response = array(
    'ok' => true, 'mode' => 'single',
    'params' => array(
        'scenario' => $scenario, 'algorithms' => $algorithms,
        'take_profit_pips' => $tp_pips, 'stop_loss_pips' => $sl_pips,
        'max_hold_days' => $max_hold_days, 'initial_capital' => $initial_capital,
        'leverage' => $leverage, 'spread_pips' => $spread_pips
    ),
    'summary' => array(
        'total_trades' => $result['total_trades'], 'winning_trades' => $result['winning_trades'],
        'losing_trades' => $result['losing_trades'], 'win_rate' => $result['win_rate'],
        'avg_win_pips' => $result['avg_win_pips'], 'avg_loss_pips' => $result['avg_loss_pips'],
        'total_return_pct' => $result['total_return_pct'], 'final_value' => $result['final_value'],
        'max_drawdown_pct' => $result['max_drawdown_pct'], 'total_spread_cost' => $result['total_spread_cost'],
        'sharpe_ratio' => $result['sharpe_ratio'], 'profit_factor' => $result['profit_factor'],
        'expectancy_pips' => $result['expectancy_pips'], 'avg_hold_days' => $result['avg_hold_days'],
        'best_trade_pips' => $result['best_trade_pips'], 'worst_trade_pips' => $result['worst_trade_pips']
    ),
    'algorithm_breakdown' => $result['algo_breakdown'],
    'trades' => $result['trades']
);

$now = date('Y-m-d H:i:s');
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$conn->query("INSERT INTO fxp_whatif_scenarios (scenario_name, query_text, params_json, results_json, created_at)
              VALUES ('" . $conn->real_escape_string($scenario) . "', '', '" . $conn->real_escape_string(json_encode($response['params'])) . "', '" . $conn->real_escape_string(json_encode($response['summary'])) . "', '$now')");

echo json_encode($response);
$conn->close();
?>
