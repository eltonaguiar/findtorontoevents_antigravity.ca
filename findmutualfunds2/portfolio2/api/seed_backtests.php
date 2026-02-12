<?php
/**
 * Seed Backtest History for Mutual Funds Portfolio v2
 * Pre-fetches NAV trajectories, then runs 10 scenarios.
 * PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/db_connect.php';

$force = isset($_GET['force']) ? (int)$_GET['force'] : 0;
$response = array('ok' => true, 'version' => 'v3-prefetch', 'seeded' => 0, 'results' => array());

if ($force !== 1) {
    $chk = $conn->query("SELECT COUNT(*) as c FROM mf2_backtest_results");
    if ($chk) {
        $row = $chk->fetch_assoc();
        if ((int)$row['c'] > 0) {
            $response['message'] = 'Backtests already exist (' . $row['c'] . '). Use ?force=1.';
            echo json_encode($response);
            $conn->close();
            exit;
        }
    }
}

if ($force === 1) {
    $conn->query("DELETE FROM mf2_backtest_results");
    $conn->query("DELETE FROM mf2_backtest_trades");
}

$now = date('Y-m-d H:i:s');

// Step 1: Fetch all picks
$picks_data = array();
$sql = "SELECT fp.id, fp.symbol, fp.algorithm_name, fp.pick_date, fp.entry_nav, f.fund_name, f.expense_ratio
        FROM mf2_fund_picks fp
        LEFT JOIN mf2_funds f ON fp.symbol = f.symbol
        WHERE fp.entry_nav > 0
        ORDER BY fp.pick_date ASC, fp.symbol ASC";
$res = $conn->query($sql);
if ($res) {
    while ($row = $res->fetch_assoc()) {
        $picks_data[] = $row;
    }
}

// Step 2: Pre-fetch NAV trajectory for each pick
$pick_navs = array();
$nav_counts = array();
$pc = count($picks_data);
for ($p = 0; $p < $pc; $p++) {
    $sym = $conn->real_escape_string($picks_data[$p]['symbol']);
    $pd = $conn->real_escape_string($picks_data[$p]['pick_date']);
    $nr = $conn->query("SELECT nav_date, nav FROM mf2_nav_history WHERE symbol='$sym' AND nav_date >= '$pd' ORDER BY nav_date ASC LIMIT 260");
    $traj = array();
    if ($nr) {
        while ($nrow = $nr->fetch_assoc()) {
            $traj[] = array('d' => $nrow['nav_date'], 'n' => (float)$nrow['nav']);
        }
    }
    $pick_navs[] = $traj;
    $nav_counts[] = count($traj);
}

$response['debug'] = array(
    'total_picks' => $pc,
    'picks_with_nav' => 0,
    'picks_without_nav' => 0,
    'sample_nav_counts' => array_slice($nav_counts, 0, 5)
);
for ($p = 0; $p < $pc; $p++) {
    if (count($pick_navs[$p]) > 1) $response['debug']['picks_with_nav']++;
    else $response['debug']['picks_without_nav']++;
}

// Step 3: Run 10 scenarios
$scenarios = array(
    array('n' => 'Short Tactical (1 Month)',   's' => 'tactical',     't' => 5,   'l' => 3,  'h' => 21),
    array('n' => 'Monthly Momentum',           's' => 'momentum',     't' => 8,   'l' => 5,  'h' => 30),
    array('n' => 'Quarterly Swing',            's' => 'swing',        't' => 10,  'l' => 8,  'h' => 63),
    array('n' => 'Conservative Hold (6M)',     's' => 'conservative', 't' => 12,  'l' => 5,  'h' => 126),
    array('n' => 'Growth (6 Months)',          's' => 'growth',       't' => 20,  'l' => 10, 'h' => 126),
    array('n' => 'Buy & Hold (1 Year)',        's' => 'buy_hold',     't' => 999, 'l' => 999,'h' => 252),
    array('n' => 'Income Steady',              's' => 'income',       't' => 6,   'l' => 3,  'h' => 180),
    array('n' => 'Aggressive Rotation',        's' => 'aggressive',   't' => 15,  'l' => 8,  'h' => 42),
    array('n' => 'Patient Value',              's' => 'value',        't' => 15,  'l' => 12, 'h' => 189),
    array('n' => 'Balanced Moderate',          's' => 'balanced',     't' => 10,  'l' => 7,  'h' => 84)
);

$scnt = count($scenarios);
for ($si = 0; $si < $scnt; $si++) {
    $sc = $scenarios[$si];
    $tr_v = $sc['t'];
    $sl_v = $sc['l'];
    $mhd = $sc['h'];
    $cap = 10000;
    $capital = $cap;
    $peak_c = $cap;
    $max_dd = 0;
    $tt = 0; $w = 0; $lo = 0; $tfees = 0;
    $tw_pct = 0; $tl_pct = 0; $gw = 0; $gl = 0;
    $best_t = -9999; $worst_t = 9999; $th = 0;
    $rets = array();
    $trades = array();

    for ($p = 0; $p < $pc; $p++) {
        $pick = $picks_data[$p];
        $traj = $pick_navs[$p];
        $enav = (float)$pick['entry_nav'];
        $tc = count($traj);
        if ($enav <= 0 || $tc < 2) continue;

        $expense = isset($pick['expense_ratio']) ? (float)$pick['expense_ratio'] : 0;
        $pos_val = $capital * 0.2;
        if ($pos_val < $enav) continue;
        $units = round($pos_val / $enav, 4);

        $dc = 0; $sold = false;
        $exit_n = $enav; $exit_d = $pick['pick_date']; $ex_r = 'end_of_data';

        for ($di = 1; $di < $tc; $di++) {
            $dc++;
            $dn = $traj[$di]['n'];
            $dd = $traj[$di]['d'];
            $chg = (($dn - $enav) / $enav) * 100;
            if ($chg >= $tr_v && $tr_v < 999) { $exit_n = $dn; $exit_d = $dd; $ex_r = 'target_hit'; $sold = true; break; }
            if ($chg <= -$sl_v && $sl_v < 999) { $exit_n = $dn; $exit_d = $dd; $ex_r = 'stop_loss'; $sold = true; break; }
            if ($dc >= $mhd) { $exit_n = $dn; $exit_d = $dd; $ex_r = 'max_hold'; $sold = true; break; }
        }

        if (!$sold && $dc > 0) {
            $li = $tc - 1;
            $exit_n = $traj[$li]['n'];
            $exit_d = $traj[$li]['d'];
        }

        $gpnl = ($exit_n - $enav) * $units;
        $ed = ($expense / 100) * ($dc / 365.25) * ($enav * $units);
        $tf = round($ed, 2);
        $np = $gpnl - $tf;
        $rp = ($enav * $units > 0) ? ($np / ($enav * $units)) * 100 : 0;

        $trades[] = array(
            'sym' => $pick['symbol'], 'alg' => $pick['algorithm_name'],
            'ed' => $pick['pick_date'], 'en' => round($enav, 4),
            'xd' => $exit_d, 'xn' => round($exit_n, 4),
            'u' => $units, 'np' => round($np, 2),
            'rp' => round($rp, 4), 'xr' => $ex_r, 'hd' => $dc
        );

        $tt++; $tfees += $tf; $capital += $np;
        $rets[] = $rp; $th += $dc;
        if ($rp > $best_t) $best_t = $rp;
        if ($rp < $worst_t) $worst_t = $rp;
        if ($np > 0) { $w++; $tw_pct += $rp; $gw += $np; }
        else { $lo++; $tl_pct += abs($rp); $gl += abs($np); }
        if ($capital > $peak_c) $peak_c = $capital;
        $ddv = ($peak_c > 0) ? (($peak_c - $capital) / $peak_c) * 100 : 0;
        if ($ddv > $max_dd) $max_dd = $ddv;
    }

    $wr = ($tt > 0) ? round($w / $tt * 100, 2) : 0;
    $aw = ($w > 0) ? round($tw_pct / $w, 4) : 0;
    $al2 = ($lo > 0) ? round($tl_pct / $lo, 4) : 0;
    $pf = ($gl > 0) ? round($gw / $gl, 4) : ($gw > 0 ? 999 : 0);
    $exp3 = round((($tt > 0 ? $w / $tt : 0) * $aw) - (($tt > 0 ? $lo / $tt : 0) * $al2), 4);
    $ah = ($tt > 0) ? round($th / $tt, 2) : 0;
    $fd = ($cap > 0) ? round($tfees / $cap * 100, 4) : 0;
    $tr2 = ($cap > 0) ? round(($capital - $cap) / $cap * 100, 4) : 0;

    $sha = 0;
    $rcnt = count($rets);
    if ($rcnt > 1) {
        $mn = array_sum($rets) / $rcnt;
        $vr = 0;
        for ($ri = 0; $ri < $rcnt; $ri++) { $vr += ($rets[$ri] - $mn) * ($rets[$ri] - $mn); }
        $sd = sqrt($vr / $rcnt);
        if ($sd > 0) $sha = round(($mn / $sd) * sqrt(252), 4);
    }

    // Insert
    $sn = $conn->real_escape_string($sc['n']);
    $ss = $conn->real_escape_string($sc['s']);
    $sd2 = (count($trades) > 0) ? $conn->real_escape_string($trades[0]['ed']) : '';
    $ed2 = (count($trades) > 0) ? $conn->real_escape_string($trades[count($trades) - 1]['xd']) : '';

    $isql = "INSERT INTO mf2_backtest_results
            (portfolio_id, run_name, algorithm_filter, strategy_type, start_date, end_date,
             initial_capital, final_value, total_return_pct, total_trades, winning_trades,
             losing_trades, win_rate, avg_win_pct, avg_loss_pct, best_trade_pct, worst_trade_pct,
             max_drawdown_pct, total_fees, sharpe_ratio, sortino_ratio, profit_factor,
             expectancy, avg_hold_days, fee_drag_pct, params_json, created_at)
            VALUES (0, '$sn', '', '$ss', '$sd2', '$ed2',
                    $cap, " . round($capital, 2) . ", $tr2, $tt, $w, $lo,
                    $wr, $aw, $al2, " . ($tt > 0 ? round($best_t, 4) : 0) . ", " . ($tt > 0 ? round($worst_t, 4) : 0) . ",
                    " . round($max_dd, 4) . ", " . round($tfees, 2) . ", $sha, 0, $pf,
                    $exp3, $ah, $fd, '', '$now')";

    if ($conn->query($isql)) {
        $bt_id = $conn->insert_id;
        $tcnt = count($trades);
        for ($ti = 0; $ti < $tcnt; $ti++) {
            $t = $trades[$ti];
            $conn->query("INSERT INTO mf2_backtest_trades
                (backtest_id, symbol, algorithm_name, entry_date, entry_nav, exit_date, exit_nav,
                 units, gross_profit, fees_paid, net_profit, return_pct, exit_reason, hold_days)
                VALUES ($bt_id, '" . $conn->real_escape_string($t['sym']) . "', '" . $conn->real_escape_string($t['alg']) . "',
                 '" . $conn->real_escape_string($t['ed']) . "', " . $t['en'] . ",
                 '" . $conn->real_escape_string($t['xd']) . "', " . $t['xn'] . ",
                 " . $t['u'] . ", 0, 0, " . $t['np'] . ", " . $t['rp'] . ",
                 '" . $conn->real_escape_string($t['xr']) . "', " . $t['hd'] . ")");
        }
        $response['seeded']++;
        $response['results'][] = array(
            'scenario' => $sc['n'], 'id' => $bt_id, 'trades' => $tt,
            'win_rate' => $wr, 'return_pct' => $tr2, 'final' => round($capital, 2)
        );
    } else {
        $response['results'][] = array('scenario' => $sc['n'], 'error' => $conn->error);
    }
}

$response['message'] = 'Seeded ' . $response['seeded'] . ' backtests';
echo json_encode($response);
$conn->close();
?>
