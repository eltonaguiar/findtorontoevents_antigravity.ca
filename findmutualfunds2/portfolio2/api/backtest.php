<?php
/**
 * Backtesting Engine for Mutual Funds Portfolio v2
 * Runs simulated fund trades with NAV-based pricing.
 * PHP 5.2 compatible.
 *
 * Key differences from stocks:
 * - Uses NAV instead of OHLCV (no intraday highs/lows)
 * - No day trading (min 1-day settle)
 * - Redemption fees instead of per-trade commissions
 * - Units (fractional) instead of whole shares
 */
require_once dirname(__FILE__) . '/db_connect.php';

function _mf2_param($key, $default) {
    if (isset($_POST[$key]) && $_POST[$key] !== '') return $_POST[$key];
    if (isset($_GET[$key]) && $_GET[$key] !== '') return $_GET[$key];
    return $default;
}

$portfolio_id = (int)_mf2_param('portfolio_id', 0);
$params = array();

if ($portfolio_id > 0) {
    $res = $conn->query("SELECT * FROM mf2_portfolios WHERE id=$portfolio_id");
    if ($res && $row = $res->fetch_assoc()) {
        $params['algorithms']      = $row['algorithm_filter'];
        $params['strategy']        = $row['strategy_type'];
        $params['target_return']   = (float)$row['target_return_pct'];
        $params['stop_loss']       = (float)$row['stop_loss_pct'];
        $params['max_hold_days']   = (int)$row['max_hold_days'];
        $params['initial_capital'] = (float)$row['initial_capital'];
        $params['redemption_fee']  = (float)$row['redemption_fee_pct'];
        $params['position_size']   = (float)$row['position_size_pct'];
        $params['max_positions']   = (int)$row['max_positions'];
    }
}

$algorithms      = _mf2_param('algorithms',      isset($params['algorithms']) ? $params['algorithms'] : '');
$strategy        = _mf2_param('strategy',         isset($params['strategy']) ? $params['strategy'] : 'balanced');
$target_return   = (float)_mf2_param('target_return',   isset($params['target_return']) ? $params['target_return'] : 10);
$stop_loss       = (float)_mf2_param('stop_loss',       isset($params['stop_loss']) ? $params['stop_loss'] : 8);
$max_hold_days   = (int)_mf2_param('max_hold_days',     isset($params['max_hold_days']) ? $params['max_hold_days'] : 90);
$initial_capital = (float)_mf2_param('initial_capital', isset($params['initial_capital']) ? $params['initial_capital'] : 10000);
$redemption_fee  = (float)_mf2_param('redemption_fee',  isset($params['redemption_fee']) ? $params['redemption_fee'] : 0);
$position_pct    = (float)_mf2_param('position_size',   isset($params['position_size']) ? $params['position_size'] : 20);
$max_positions   = (int)_mf2_param('max_positions',     isset($params['max_positions']) ? $params['max_positions'] : 5);
$save_results    = (int)_mf2_param('save', 0);

// ─── Fetch Picks ───
$where_algo = '';
if ($algorithms !== '') {
    $algo_list = explode(',', $algorithms);
    $escaped = array();
    foreach ($algo_list as $a) {
        $a = trim($a);
        if ($a !== '') $escaped[] = "'" . $conn->real_escape_string($a) . "'";
    }
    if (count($escaped) > 0) {
        $where_algo = " AND fp.algorithm_name IN (" . implode(',', $escaped) . ")";
    }
}

$sql = "SELECT fp.*, f.fund_name, f.fund_family, f.category, f.expense_ratio
        FROM mf2_fund_picks fp
        LEFT JOIN mf2_funds f ON fp.symbol = f.symbol
        WHERE fp.entry_nav > 0 $where_algo
        ORDER BY fp.pick_date ASC, fp.symbol ASC";

$picks_res = $conn->query($sql);
if (!$picks_res || $picks_res->num_rows === 0) {
    echo json_encode(array(
        'ok' => false,
        'error' => 'No fund picks found. Import picks first via import_picks.php',
        'params' => array('algorithms' => $algorithms, 'strategy' => $strategy)
    ));
    $conn->close();
    exit;
}

// ─── Run Backtest ───
$capital         = $initial_capital;
$peak_capital    = $initial_capital;
$max_drawdown    = 0;
$total_trades    = 0;
$winning_trades  = 0;
$losing_trades   = 0;
$total_fees      = 0;
$total_wins_pct  = 0;
$total_losses_pct = 0;
$best_trade      = -9999;
$worst_trade     = 9999;
$total_hold_days = 0;
$trades          = array();
$daily_returns   = array();
$equity_curve    = array();

while ($pick = $picks_res->fetch_assoc()) {
    $symbol    = $pick['symbol'];
    $entry_nav = (float)$pick['entry_nav'];
    $pick_date = $pick['pick_date'];
    $algo_name = $pick['algorithm_name'];
    $fund_name = isset($pick['fund_name']) ? $pick['fund_name'] : '';
    $category  = isset($pick['category']) ? $pick['category'] : '';
    $expense   = isset($pick['expense_ratio']) ? (float)$pick['expense_ratio'] : 0;

    // Position sizing
    $position_value = $capital * ($position_pct / 100);
    if ($position_value < $entry_nav) continue;
    $units = round($position_value / $entry_nav, 4);
    if ($units <= 0) continue;

    // Fetch NAV history
    $safe_sym  = $conn->real_escape_string($symbol);
    $safe_date = $conn->real_escape_string($pick_date);
    $nav_sql = "SELECT nav_date, nav FROM mf2_nav_history
                WHERE symbol='$safe_sym' AND nav_date >= '$safe_date'
                ORDER BY nav_date ASC
                LIMIT " . ($max_hold_days + 5);
    $nav_res = $conn->query($nav_sql);

    if (!$nav_res || $nav_res->num_rows === 0) {
        // No NAV data — record as flat trade
        $fee = round($units * $entry_nav * $redemption_fee / 100, 2);
        $trade = array(
            'symbol' => $symbol, 'fund_name' => $fund_name, 'category' => $category,
            'algorithm' => $algo_name, 'entry_date' => $pick_date, 'entry_nav' => $entry_nav,
            'exit_date' => $pick_date, 'exit_nav' => $entry_nav, 'units' => $units,
            'gross_profit' => 0, 'fees_paid' => $fee, 'net_profit' => -$fee,
            'return_pct' => round(-$fee / ($entry_nav * $units) * 100, 4),
            'exit_reason' => 'no_nav_data', 'hold_days' => 0
        );
        $trades[] = $trade;
        $total_trades++;
        $losing_trades++;
        $total_fees += $fee;
        $total_losses_pct += abs($trade['return_pct']);
        $capital -= $fee;
        continue;
    }

    // Simulate holding period using daily NAV
    $day_count  = 0;
    $sold       = false;
    $exit_nav   = $entry_nav;
    $exit_date  = $pick_date;
    $exit_reason = 'end_of_data';

    while ($day = $nav_res->fetch_assoc()) {
        $day_count++;
        $day_nav  = (float)$day['nav'];
        $day_date = $day['nav_date'];

        $change_pct = (($day_nav - $entry_nav) / $entry_nav) * 100;

        // Target return hit
        if ($change_pct >= $target_return && $target_return < 999) {
            $exit_nav = $day_nav;
            $exit_date = $day_date;
            $exit_reason = 'target_hit';
            $sold = true;
            break;
        }

        // Stop loss hit
        if ($change_pct <= -$stop_loss && $stop_loss < 999) {
            $exit_nav = $day_nav;
            $exit_date = $day_date;
            $exit_reason = 'stop_loss';
            $sold = true;
            break;
        }

        // Max hold
        if ($day_count >= $max_hold_days) {
            $exit_nav = $day_nav;
            $exit_date = $day_date;
            $exit_reason = 'max_hold';
            $sold = true;
            break;
        }
    }

    if (!$sold && $day_count > 0) {
        $exit_reason = 'end_of_data';
    }

    // Calculate P&L
    $gross_profit = ($exit_nav - $entry_nav) * $units;
    $fee = round(abs($exit_nav * $units) * $redemption_fee / 100, 2);
    // Account for daily expense ratio drag over holding period
    $annual_expense_drag = $expense / 100;
    $expense_days_drag = $annual_expense_drag * ($day_count / 365.25) * ($entry_nav * $units);
    $total_fee = $fee + round($expense_days_drag, 2);
    $net_profit = $gross_profit - $total_fee;
    $return_pct = ($entry_nav * $units > 0) ? ($net_profit / ($entry_nav * $units)) * 100 : 0;

    $trade = array(
        'symbol'      => $symbol,
        'fund_name'   => $fund_name,
        'category'    => $category,
        'algorithm'   => $algo_name,
        'entry_date'  => $pick_date,
        'entry_nav'   => round($entry_nav, 4),
        'exit_date'   => $exit_date,
        'exit_nav'    => round($exit_nav, 4),
        'units'       => $units,
        'gross_profit'=> round($gross_profit, 2),
        'fees_paid'   => round($total_fee, 2),
        'net_profit'  => round($net_profit, 2),
        'return_pct'  => round($return_pct, 4),
        'exit_reason' => $exit_reason,
        'hold_days'   => $day_count
    );

    $trades[] = $trade;
    $total_trades++;
    $total_fees += $total_fee;
    $capital += $net_profit;
    $total_hold_days += $day_count;

    if ($return_pct > $best_trade) $best_trade = $return_pct;
    if ($return_pct < $worst_trade) $worst_trade = $return_pct;

    if ($net_profit > 0) {
        $winning_trades++;
        $total_wins_pct += $return_pct;
    } else {
        $losing_trades++;
        $total_losses_pct += abs($return_pct);
    }

    if ($capital > $peak_capital) $peak_capital = $capital;
    $drawdown = ($peak_capital > 0) ? (($peak_capital - $capital) / $peak_capital) * 100 : 0;
    if ($drawdown > $max_drawdown) $max_drawdown = $drawdown;

    $daily_returns[] = $return_pct;
    $equity_curve[] = array('trade' => $total_trades, 'capital' => round($capital, 2), 'date' => $exit_date);
}

// ─── Aggregate Metrics ───
$final_value  = round($capital, 2);
$total_return = ($initial_capital > 0) ? round(($capital - $initial_capital) / $initial_capital * 100, 4) : 0;
$win_rate     = ($total_trades > 0) ? round($winning_trades / $total_trades * 100, 2) : 0;
$avg_win_pct  = ($winning_trades > 0) ? round($total_wins_pct / $winning_trades, 4) : 0;
$avg_loss_pct = ($losing_trades > 0) ? round($total_losses_pct / $losing_trades, 4) : 0;
$avg_hold     = ($total_trades > 0) ? round($total_hold_days / $total_trades, 2) : 0;
$fee_drag     = ($initial_capital > 0) ? round($total_fees / $initial_capital * 100, 4) : 0;

// Sharpe & Sortino
$sharpe = 0;
$sortino = 0;
if (count($daily_returns) > 1) {
    $mean = array_sum($daily_returns) / count($daily_returns);
    $variance = 0;
    $dvar = 0;
    $dcnt = 0;
    foreach ($daily_returns as $r) {
        $variance += ($r - $mean) * ($r - $mean);
        if ($r < 0) { $dvar += $r * $r; $dcnt++; }
    }
    $stddev = sqrt($variance / count($daily_returns));
    if ($stddev > 0) $sharpe = round($mean / $stddev, 4);
    if ($dcnt > 0) {
        $dstd = sqrt($dvar / $dcnt);
        if ($dstd > 0) $sortino = round($mean / $dstd, 4);
    }
}

// Profit factor
$gross_wins = 0;
$gross_losses = 0;
foreach ($trades as $t) {
    if ($t['net_profit'] > 0) $gross_wins += $t['net_profit'];
    else $gross_losses += abs($t['net_profit']);
}
$profit_factor = ($gross_losses > 0) ? round($gross_wins / $gross_losses, 4) : ($gross_wins > 0 ? 999 : 0);

// Expectancy
$loss_rate = ($total_trades > 0) ? $losing_trades / $total_trades : 0;
$win_rate_dec = ($total_trades > 0) ? $winning_trades / $total_trades : 0;
$expectancy = round(($win_rate_dec * $avg_win_pct) - ($loss_rate * $avg_loss_pct), 4);

// Per-algorithm breakdown
$algo_stats = array();
foreach ($trades as $t) {
    $a = $t['algorithm'];
    if (!isset($algo_stats[$a])) $algo_stats[$a] = array('trades' => 0, 'wins' => 0, 'losses' => 0, 'total_return' => 0, 'total_pnl' => 0);
    $algo_stats[$a]['trades']++;
    $algo_stats[$a]['total_return'] += $t['return_pct'];
    $algo_stats[$a]['total_pnl'] += $t['net_profit'];
    if ($t['net_profit'] > 0) $algo_stats[$a]['wins']++;
    else $algo_stats[$a]['losses']++;
}
$algo_breakdown = array();
foreach ($algo_stats as $aname => $as) {
    $algo_breakdown[] = array(
        'algorithm' => $aname,
        'trades' => $as['trades'], 'wins' => $as['wins'], 'losses' => $as['losses'],
        'win_rate' => ($as['trades'] > 0) ? round($as['wins'] / $as['trades'] * 100, 2) : 0,
        'avg_return_pct' => ($as['trades'] > 0) ? round($as['total_return'] / $as['trades'], 4) : 0,
        'total_pnl' => round($as['total_pnl'], 2)
    );
}

// Exit reason breakdown
$exit_reasons = array();
foreach ($trades as $t) {
    $r = $t['exit_reason'];
    if (!isset($exit_reasons[$r])) $exit_reasons[$r] = 0;
    $exit_reasons[$r]++;
}

// ─── Response ───
$response = array(
    'ok' => true,
    'params' => array(
        'algorithms'       => $algorithms,
        'strategy'         => $strategy,
        'target_return_pct'=> $target_return,
        'stop_loss_pct'    => $stop_loss,
        'max_hold_days'    => $max_hold_days,
        'initial_capital'  => $initial_capital,
        'redemption_fee_pct' => $redemption_fee,
        'position_size_pct'=> $position_pct,
        'max_positions'    => $max_positions
    ),
    'summary' => array(
        'initial_capital'      => $initial_capital,
        'final_value'          => $final_value,
        'total_return_pct'     => $total_return,
        'total_trades'         => $total_trades,
        'winning_trades'       => $winning_trades,
        'losing_trades'        => $losing_trades,
        'win_rate'             => $win_rate,
        'avg_win_pct'          => $avg_win_pct,
        'avg_loss_pct'         => $avg_loss_pct,
        'best_trade_pct'       => ($total_trades > 0) ? round($best_trade, 4) : 0,
        'worst_trade_pct'      => ($total_trades > 0) ? round($worst_trade, 4) : 0,
        'avg_hold_days'        => $avg_hold,
        'max_drawdown_pct'     => round($max_drawdown, 4),
        'total_fees'           => round($total_fees, 2),
        'fee_drag_pct'         => $fee_drag,
        'sharpe_ratio'         => $sharpe,
        'sortino_ratio'        => $sortino,
        'profit_factor'        => $profit_factor,
        'expectancy'           => $expectancy
    ),
    'algorithm_breakdown' => $algo_breakdown,
    'exit_reasons' => $exit_reasons,
    'equity_curve' => $equity_curve,
    'trades' => $trades
);

// ─── Save Results ───
if ($save_results === 1) {
    $now = date('Y-m-d H:i:s');
    $run_name = $strategy . '_tr' . $target_return . '_sl' . $stop_loss . '_' . $max_hold_days . 'd';
    $safe_name  = $conn->real_escape_string($run_name);
    $safe_algos = $conn->real_escape_string($algorithms);
    $safe_strat = $conn->real_escape_string($strategy);
    $params_json = $conn->real_escape_string(json_encode($response['params']));

    $start_d = '';
    $end_d = '';
    if (count($trades) > 0) {
        $start_d = $trades[0]['entry_date'];
        $end_d = $trades[count($trades) - 1]['exit_date'];
    }

    $sql = "INSERT INTO mf2_backtest_results
            (portfolio_id, run_name, algorithm_filter, strategy_type, start_date, end_date,
             initial_capital, final_value, total_return_pct, total_trades, winning_trades,
             losing_trades, win_rate, avg_win_pct, avg_loss_pct, best_trade_pct, worst_trade_pct,
             max_drawdown_pct, total_fees, sharpe_ratio, sortino_ratio, profit_factor,
             expectancy, avg_hold_days, fee_drag_pct, params_json, created_at)
            VALUES ($portfolio_id, '$safe_name', '$safe_algos', '$safe_strat',
                    '" . $conn->real_escape_string($start_d) . "', '" . $conn->real_escape_string($end_d) . "',
                    $initial_capital, $final_value, $total_return, $total_trades, $winning_trades,
                    $losing_trades, $win_rate, $avg_win_pct, $avg_loss_pct,
                    " . (($total_trades > 0) ? round($best_trade, 4) : 0) . ",
                    " . (($total_trades > 0) ? round($worst_trade, 4) : 0) . ",
                    " . round($max_drawdown, 4) . ", " . round($total_fees, 2) . ",
                    $sharpe, $sortino, $profit_factor, $expectancy, $avg_hold,
                    $fee_drag, '$params_json', '$now')";

    if ($conn->query($sql)) {
        $bt_id = $conn->insert_id;
        $response['backtest_id'] = $bt_id;

        foreach ($trades as $t) {
            $ss = $conn->real_escape_string($t['symbol']);
            $sa = $conn->real_escape_string($t['algorithm']);
            $se = $conn->real_escape_string($t['entry_date']);
            $sx = $conn->real_escape_string(isset($t['exit_date']) ? $t['exit_date'] : '');
            $sr = $conn->real_escape_string($t['exit_reason']);
            $conn->query("INSERT INTO mf2_backtest_trades
                (backtest_id, symbol, algorithm_name, entry_date, entry_nav, exit_date, exit_nav,
                 units, gross_profit, fees_paid, net_profit, return_pct, exit_reason, hold_days)
                VALUES ($bt_id, '$ss', '$sa', '$se', " . $t['entry_nav'] . ", '$sx', " . $t['exit_nav'] . ",
                 " . $t['units'] . ", " . $t['gross_profit'] . ", " . $t['fees_paid'] . ",
                 " . $t['net_profit'] . ", " . $t['return_pct'] . ", '$sr', " . $t['hold_days'] . ")");
        }
    }

    $ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
    $conn->query("INSERT INTO mf2_audit_log (action_type, details, ip_address, created_at)
                  VALUES ('backtest', '" . $conn->real_escape_string('MF Backtest: ' . $run_name) . "', '$ip', '$now')");
}

echo json_encode($response);
$conn->close();
?>
