<?php
/**
 * What-If Analysis Engine for Mutual Funds v2
 * Multi-scenario comparison, per-algorithm analysis.
 * PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/db_connect.php';

function _mfwi_param($key, $default) {
    if (isset($_POST[$key]) && $_POST[$key] !== '') return $_POST[$key];
    if (isset($_GET[$key]) && $_GET[$key] !== '') return $_GET[$key];
    return $default;
}

$scenario        = _mfwi_param('scenario', '');
$algorithms      = _mfwi_param('algorithms', '');
$target_return   = (float)_mfwi_param('target_return', 10);
$stop_loss       = (float)_mfwi_param('stop_loss', 8);
$max_hold_days   = (int)_mfwi_param('max_hold_days', 90);
$initial_capital = (float)_mfwi_param('initial_capital', 10000);
$redemption_fee  = (float)_mfwi_param('redemption_fee', 0);
$compare_mode    = (int)_mfwi_param('compare', 0);
$compare_algos   = (int)_mfwi_param('compare_algos', 0);

// ─── Preset Scenarios (mutual fund-appropriate) ───
$scenarios = array(
    'short_tactical'     => array('name' => 'Short Tactical (1 Month)',    'description' => 'Quick rotation, 1-month max hold.',              'target' => 5,   'stop_loss' => 3,  'max_hold' => 21),
    'momentum_monthly'   => array('name' => 'Monthly Momentum',           'description' => 'Ride monthly momentum, 8% target.',               'target' => 8,   'stop_loss' => 5,  'max_hold' => 30),
    'swing_quarter'      => array('name' => 'Quarterly Swing',            'description' => 'Hold up to 3 months, 10% target.',                'target' => 10,  'stop_loss' => 8,  'max_hold' => 63),
    'conservative_hold'  => array('name' => 'Conservative Hold (6M)',     'description' => 'Patient hold, 12% target, tight stop.',            'target' => 12,  'stop_loss' => 5,  'max_hold' => 126),
    'growth_6m'          => array('name' => 'Growth (6 Months)',          'description' => 'Aggressive 20% target over 6 months.',             'target' => 20,  'stop_loss' => 10, 'max_hold' => 126),
    'buy_hold_1y'        => array('name' => 'Buy & Hold (1 Year)',        'description' => 'No targets, hold for 1 year.',                    'target' => 999, 'stop_loss' => 999,'max_hold' => 252),
    'income_steady'      => array('name' => 'Income Steady',             'description' => 'Bond-focused, 6% target, very tight stop.',         'target' => 6,   'stop_loss' => 3,  'max_hold' => 180),
    'aggressive_rotation'=> array('name' => 'Aggressive Rotation',       'description' => 'Fast rotation, 15% target, 2 months.',              'target' => 15,  'stop_loss' => 8,  'max_hold' => 42),
    'value_patient'      => array('name' => 'Patient Value',             'description' => 'Deep value, wait for recovery over 9 months.',       'target' => 15,  'stop_loss' => 12, 'max_hold' => 189),
    'balanced_moderate'  => array('name' => 'Balanced Moderate',         'description' => '10% target, 7% stop, 4-month hold.',                'target' => 10,  'stop_loss' => 7,  'max_hold' => 84)
);

// ─── Inline backtest for mutual funds ───
function run_mf2_backtest($conn, $algo_filter, $tr, $sl, $mhd, $cap, $rfee, $pos_pct) {
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

    $sql = "SELECT fp.*, f.fund_name, f.expense_ratio
            FROM mf2_fund_picks fp LEFT JOIN mf2_funds f ON fp.symbol = f.symbol
            WHERE fp.entry_nav > 0 $where
            ORDER BY fp.pick_date ASC, fp.symbol ASC";
    $picks = $conn->query($sql);

    $result = array(
        'total_trades' => 0, 'winning_trades' => 0, 'losing_trades' => 0,
        'win_rate' => 0, 'total_return_pct' => 0, 'final_value' => $cap,
        'max_drawdown_pct' => 0, 'total_fees' => 0, 'sharpe_ratio' => 0,
        'profit_factor' => 0, 'expectancy' => 0, 'avg_hold_days' => 0,
        'best_trade_pct' => 0, 'worst_trade_pct' => 0,
        'fee_drag_pct' => 0, 'trades' => array(), 'algo_breakdown' => array()
    );
    if (!$picks || $picks->num_rows === 0) return $result;

    $capital = $cap;
    $peak = $cap;
    $max_dd = 0;
    $tt = 0; $wins = 0; $losses = 0; $tfees = 0;
    $tw_pct = 0; $tl_pct = 0; $g_wins = 0; $g_losses = 0;
    $best = -9999; $worst = 9999; $t_hold = 0;
    $trades = array(); $returns = array(); $algo_s = array();

    while ($pick = $picks->fetch_assoc()) {
        $sym = $pick['symbol'];
        $enav = (float)$pick['entry_nav'];
        $pdate = $pick['pick_date'];
        $algo = $pick['algorithm_name'];
        $fname = isset($pick['fund_name']) ? $pick['fund_name'] : '';
        $expense = isset($pick['expense_ratio']) ? (float)$pick['expense_ratio'] : 0;

        $pos_val = $capital * ($pos_pct / 100);
        if ($pos_val < $enav) continue;
        $units = round($pos_val / $enav, 4);

        $ss = $conn->real_escape_string($sym);
        $sd = $conn->real_escape_string($pdate);
        $nr = $conn->query("SELECT nav_date, nav FROM mf2_nav_history WHERE symbol='$ss' AND nav_date >= '$sd' ORDER BY nav_date ASC LIMIT " . ($mhd + 5));

        $dc = 0; $sold = false; $exit_n = $enav; $exit_d = $pdate; $ex_r = 'end_of_data';
        if ($nr && $nr->num_rows > 0) {
            while ($d = $nr->fetch_assoc()) {
                $dc++;
                $dn = (float)$d['nav'];
                $dd = $d['nav_date'];
                $chg = (($dn - $enav) / $enav) * 100;
                if ($chg >= $tr && $tr < 999) { $exit_n = $dn; $exit_d = $dd; $ex_r = 'target_hit'; $sold = true; break; }
                if ($chg <= -$sl && $sl < 999) { $exit_n = $dn; $exit_d = $dd; $ex_r = 'stop_loss'; $sold = true; break; }
                if ($dc >= $mhd) { $exit_n = $dn; $exit_d = $dd; $ex_r = 'max_hold'; $sold = true; break; }
            }
            if (!$sold && $dc > 0) $exit_n = (float)$d['nav'];
        }

        $gpnl = ($exit_n - $enav) * $units;
        $fee = round(abs($exit_n * $units) * $rfee / 100, 2);
        $exp_drag = ($expense / 100) * ($dc / 365.25) * ($enav * $units);
        $total_fee = $fee + round($exp_drag, 2);
        $npnl = $gpnl - $total_fee;
        $rpct = ($enav * $units > 0) ? ($npnl / ($enav * $units)) * 100 : 0;

        $trades[] = array(
            'symbol' => $sym, 'fund_name' => $fname, 'algorithm' => $algo,
            'entry_date' => $pdate, 'entry_nav' => round($enav, 4),
            'exit_date' => $exit_d, 'exit_nav' => round($exit_n, 4),
            'units' => $units, 'net_profit' => round($npnl, 2),
            'return_pct' => round($rpct, 4), 'exit_reason' => $ex_r, 'hold_days' => $dc
        );

        $tt++; $tfees += $total_fee; $capital += $npnl;
        $returns[] = $rpct; $t_hold += $dc;
        if ($rpct > $best) $best = $rpct;
        if ($rpct < $worst) $worst = $rpct;
        if ($npnl > 0) { $wins++; $tw_pct += $rpct; $g_wins += $npnl; }
        else { $losses++; $tl_pct += abs($rpct); $g_losses += abs($npnl); }
        if ($capital > $peak) $peak = $capital;
        $ddv = ($peak > 0) ? (($peak - $capital) / $peak) * 100 : 0;
        if ($ddv > $max_dd) $max_dd = $ddv;

        if (!isset($algo_s[$algo])) $algo_s[$algo] = array('t' => 0, 'w' => 0, 'l' => 0, 'r' => 0, 'pnl' => 0);
        $algo_s[$algo]['t']++; $algo_s[$algo]['r'] += $rpct; $algo_s[$algo]['pnl'] += $npnl;
        if ($npnl > 0) $algo_s[$algo]['w']++; else $algo_s[$algo]['l']++;
    }

    $wr = ($tt > 0) ? round($wins / $tt * 100, 2) : 0;
    $aw = ($wins > 0) ? round($tw_pct / $wins, 4) : 0;
    $al = ($losses > 0) ? round($tl_pct / $losses, 4) : 0;
    $pf = ($g_losses > 0) ? round($g_wins / $g_losses, 4) : ($g_wins > 0 ? 999 : 0);
    $exp = round((($tt > 0 ? $wins / $tt : 0) * $aw) - (($tt > 0 ? $losses / $tt : 0) * $al), 4);
    $ah = ($tt > 0) ? round($t_hold / $tt, 2) : 0;
    $fdrag = ($cap > 0) ? round($tfees / $cap * 100, 4) : 0;

    $sharpe = 0;
    if (count($returns) > 1) {
        $mean = array_sum($returns) / count($returns);
        $var = 0;
        foreach ($returns as $r) { $var += ($r - $mean) * ($r - $mean); }
        $std = sqrt($var / count($returns));
        if ($std > 0) $sharpe = round(($mean / $std) * sqrt(252), 4);
    }

    $total_ret = ($cap > 0) ? round(($capital - $cap) / $cap * 100, 4) : 0;

    $ab = array();
    foreach ($algo_s as $aname => $as) {
        $ab[] = array(
            'algorithm' => $aname,
            'trades' => $as['t'], 'wins' => $as['w'], 'losses' => $as['l'],
            'win_rate' => ($as['t'] > 0) ? round($as['w'] / $as['t'] * 100, 2) : 0,
            'avg_return_pct' => ($as['t'] > 0) ? round($as['r'] / $as['t'], 4) : 0,
            'total_pnl' => round($as['pnl'], 2)
        );
    }

    return array(
        'total_trades' => $tt, 'winning_trades' => $wins, 'losing_trades' => $losses,
        'win_rate' => $wr, 'avg_win_pct' => $aw, 'avg_loss_pct' => $al,
        'total_return_pct' => $total_ret, 'final_value' => round($capital, 2),
        'max_drawdown_pct' => round($max_dd, 4), 'total_fees' => round($tfees, 2),
        'sharpe_ratio' => $sharpe, 'profit_factor' => $pf, 'expectancy' => $exp,
        'avg_hold_days' => $ah, 'best_trade_pct' => ($tt > 0) ? round($best, 4) : 0,
        'worst_trade_pct' => ($tt > 0) ? round($worst, 4) : 0,
        'fee_drag_pct' => $fdrag, 'trades' => $trades, 'algo_breakdown' => $ab
    );
}

// ─── Compare All Scenarios ───
if ($compare_mode === 1) {
    $comparison = array();
    foreach ($scenarios as $key => $sc) {
        $r = run_mf2_backtest($conn, $algorithms, $sc['target'], $sc['stop_loss'], $sc['max_hold'], $initial_capital, $redemption_fee, 20);
        $comparison[] = array(
            'scenario_key' => $key, 'name' => $sc['name'], 'description' => $sc['description'],
            'params' => array('target_return' => $sc['target'], 'stop_loss' => $sc['stop_loss'], 'max_hold_days' => $sc['max_hold']),
            'summary' => array(
                'total_trades' => $r['total_trades'], 'win_rate' => $r['win_rate'],
                'total_return_pct' => $r['total_return_pct'], 'final_value' => $r['final_value'],
                'max_drawdown_pct' => $r['max_drawdown_pct'], 'total_fees' => $r['total_fees'],
                'sharpe_ratio' => $r['sharpe_ratio'], 'profit_factor' => $r['profit_factor'],
                'expectancy' => $r['expectancy'], 'avg_hold_days' => $r['avg_hold_days'],
                'fee_drag_pct' => $r['fee_drag_pct'],
                'best_trade_pct' => $r['best_trade_pct'], 'worst_trade_pct' => $r['worst_trade_pct']
            )
        );
    }

    $ret_arr = array();
    $cnt = count($comparison);
    for ($i = 0; $i < $cnt; $i++) $ret_arr[$i] = $comparison[$i]['summary']['total_return_pct'];
    arsort($ret_arr);
    $sorted = array();
    foreach ($ret_arr as $idx => $val) $sorted[] = $comparison[$idx];

    echo json_encode(array('ok' => true, 'mode' => 'comparison', 'algorithms' => $algorithms, 'initial_capital' => $initial_capital, 'scenarios' => $sorted));
    $conn->close();
    exit;
}

// ─── Compare Algorithms ───
if ($compare_algos === 1) {
    $algo_res = $conn->query("SELECT DISTINCT algorithm_name FROM mf2_fund_picks WHERE entry_nav > 0 ORDER BY algorithm_name");
    $algo_list = array();
    if ($algo_res) { while ($ar = $algo_res->fetch_assoc()) $algo_list[] = $ar['algorithm_name']; }

    $tr_use = $target_return; $sl_use = $stop_loss; $mhd_use = $max_hold_days;
    if ($scenario !== '' && isset($scenarios[$scenario])) {
        $sc = $scenarios[$scenario];
        $tr_use = $sc['target']; $sl_use = $sc['stop_loss']; $mhd_use = $sc['max_hold'];
    }

    $algo_comp = array();
    foreach ($algo_list as $aname) {
        $r = run_mf2_backtest($conn, $aname, $tr_use, $sl_use, $mhd_use, $initial_capital, $redemption_fee, 20);
        $algo_comp[] = array(
            'algorithm' => $aname,
            'params' => array('target_return' => $tr_use, 'stop_loss' => $sl_use, 'max_hold_days' => $mhd_use),
            'summary' => array(
                'total_trades' => $r['total_trades'], 'win_rate' => $r['win_rate'],
                'total_return_pct' => $r['total_return_pct'], 'final_value' => $r['final_value'],
                'max_drawdown_pct' => $r['max_drawdown_pct'], 'sharpe_ratio' => $r['sharpe_ratio'],
                'profit_factor' => $r['profit_factor'], 'expectancy' => $r['expectancy'],
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

    echo json_encode(array('ok' => true, 'mode' => 'algorithm_comparison', 'scenario' => $scenario, 'initial_capital' => $initial_capital, 'algorithms' => $sorted2));
    $conn->close();
    exit;
}

// ─── Single Scenario ───
if ($scenario !== '' && isset($scenarios[$scenario])) {
    $sc = $scenarios[$scenario];
    $target_return = $sc['target']; $stop_loss = $sc['stop_loss']; $max_hold_days = $sc['max_hold'];
}

$result = run_mf2_backtest($conn, $algorithms, $target_return, $stop_loss, $max_hold_days, $initial_capital, $redemption_fee, 20);

$response = array(
    'ok' => true, 'mode' => 'single',
    'params' => array(
        'scenario' => $scenario, 'algorithms' => $algorithms,
        'target_return' => $target_return, 'stop_loss' => $stop_loss,
        'max_hold_days' => $max_hold_days, 'initial_capital' => $initial_capital,
        'redemption_fee' => $redemption_fee
    ),
    'summary' => array(
        'total_trades' => $result['total_trades'], 'winning_trades' => $result['winning_trades'],
        'losing_trades' => $result['losing_trades'], 'win_rate' => $result['win_rate'],
        'avg_win_pct' => $result['avg_win_pct'], 'avg_loss_pct' => $result['avg_loss_pct'],
        'total_return_pct' => $result['total_return_pct'], 'final_value' => $result['final_value'],
        'max_drawdown_pct' => $result['max_drawdown_pct'], 'total_fees' => $result['total_fees'],
        'sharpe_ratio' => $result['sharpe_ratio'], 'profit_factor' => $result['profit_factor'],
        'expectancy' => $result['expectancy'], 'avg_hold_days' => $result['avg_hold_days'],
        'best_trade_pct' => $result['best_trade_pct'], 'worst_trade_pct' => $result['worst_trade_pct'],
        'fee_drag_pct' => $result['fee_drag_pct']
    ),
    'algorithm_breakdown' => $result['algo_breakdown'],
    'trades' => $result['trades']
);

$now = date('Y-m-d H:i:s');
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$conn->query("INSERT INTO mf2_whatif_scenarios (scenario_name, query_text, params_json, results_json, created_at)
              VALUES ('" . $conn->real_escape_string($scenario) . "', '', '" . $conn->real_escape_string(json_encode($response['params'])) . "', '" . $conn->real_escape_string(json_encode($response['summary'])) . "', '$now')");

echo json_encode($response);
$conn->close();
?>
