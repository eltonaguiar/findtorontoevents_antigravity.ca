<?php
/**
 * Backtesting Engine for Crypto Pairs Portfolio
 * Runs simulated crypto trades with OHLCV-based pricing.
 * PHP 5.2 compatible.
 *
 * Key differences from stocks/funds:
 * - Supports LONG and SHORT direction
 * - 24/7 market (no weekday filtering needed)
 * - Higher volatility parameters
 * - Percentage-based position sizing
 * - Uses close prices for entry/exit
 */
require_once dirname(__FILE__) . '/db_connect.php';

function _cr_param($key, $default) {
    if (isset($_POST[$key]) && $_POST[$key] !== '') return $_POST[$key];
    if (isset($_GET[$key]) && $_GET[$key] !== '') return $_GET[$key];
    return $default;
}

$portfolio_id = (int)_cr_param('portfolio_id', 0);
$params = array();

if ($portfolio_id > 0) {
    $res = $conn->query("SELECT * FROM cr_portfolios WHERE id=$portfolio_id");
    if ($res && $row = $res->fetch_assoc()) {
        $params['algorithms']      = $row['algorithm_filter'];
        $params['strategy']        = $row['strategy_type'];
        $params['take_profit']     = (float)$row['take_profit_pct'];
        $params['stop_loss']       = (float)$row['stop_loss_pct'];
        $params['max_hold_days']   = (int)$row['max_hold_days'];
        $params['initial_capital'] = (float)$row['initial_capital'];
        $params['position_size']   = (float)$row['position_size_pct'];
        $params['max_positions']   = (int)$row['max_positions'];
    }
}

$algorithms      = _cr_param('algorithms',      isset($params['algorithms']) ? $params['algorithms'] : '');
$strategy        = _cr_param('strategy',         isset($params['strategy']) ? $params['strategy'] : 'balanced');
$take_profit     = (float)_cr_param('take_profit',     isset($params['take_profit']) ? $params['take_profit'] : 20);
$stop_loss       = (float)_cr_param('stop_loss',       isset($params['stop_loss']) ? $params['stop_loss'] : 10);
$max_hold_days   = (int)_cr_param('max_hold_days',     isset($params['max_hold_days']) ? $params['max_hold_days'] : 90);
$initial_capital = (float)_cr_param('initial_capital', isset($params['initial_capital']) ? $params['initial_capital'] : 10000);
$position_pct    = (float)_cr_param('position_size',   isset($params['position_size']) ? $params['position_size'] : 20);
$max_positions   = (int)_cr_param('max_positions',     isset($params['max_positions']) ? $params['max_positions'] : 5);
$save_results    = (int)_cr_param('save', 0);

// Trading fee: 0.1% per trade (typical crypto exchange)
$trading_fee_pct = (float)_cr_param('trading_fee', 0.1);

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

$sql = "SELECT fp.*, p.pair_name, p.base_asset, p.category
        FROM cr_pair_picks fp
        LEFT JOIN cr_pairs p ON fp.symbol = p.symbol
        WHERE fp.entry_price > 0 $where_algo
        ORDER BY fp.pick_date ASC, fp.symbol ASC";

$picks_res = $conn->query($sql);
if (!$picks_res || $picks_res->num_rows === 0) {
    echo json_encode(array(
        'ok' => false,
        'error' => 'No crypto pair picks found. Import picks first via import_picks.php',
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
    $symbol      = $pick['symbol'];
    $entry_price = (float)$pick['entry_price'];
    $pick_date   = $pick['pick_date'];
    $algo_name   = $pick['algorithm_name'];
    $direction   = isset($pick['direction']) ? strtoupper($pick['direction']) : 'LONG';
    $pair_name   = isset($pick['pair_name']) ? $pick['pair_name'] : '';
    $category    = isset($pick['category']) ? $pick['category'] : '';

    // Position sizing
    $position_value = $capital * ($position_pct / 100);
    if ($position_value < 10) continue; // minimum $10 position
    $position_size = round($position_value / $entry_price, 8);
    if ($position_size <= 0) continue;

    // Fetch price history after pick date
    $safe_sym  = $conn->real_escape_string($symbol);
    $safe_date = $conn->real_escape_string($pick_date);
    $price_sql = "SELECT price_date, open, high, low, close FROM cr_price_history
                  WHERE symbol='$safe_sym' AND price_date >= '$safe_date'
                  ORDER BY price_date ASC
                  LIMIT " . ($max_hold_days + 5);
    $price_res = $conn->query($price_sql);

    if (!$price_res || $price_res->num_rows === 0) {
        // No price data - flat trade with fees
        $entry_fee = round($position_value * $trading_fee_pct / 100, 2);
        $exit_fee  = round($position_value * $trading_fee_pct / 100, 2);
        $fee = $entry_fee + $exit_fee;
        $trade = array(
            'symbol' => $symbol, 'pair_name' => $pair_name, 'category' => $category,
            'algorithm' => $algo_name, 'direction' => $direction,
            'entry_date' => $pick_date, 'entry_price' => $entry_price,
            'exit_date' => $pick_date, 'exit_price' => $entry_price,
            'position_size' => $position_size,
            'gross_profit' => 0, 'fees_paid' => $fee, 'net_profit' => -$fee,
            'return_pct' => round(-$fee / $position_value * 100, 4),
            'exit_reason' => 'no_price_data', 'hold_days' => 0
        );
        $trades[] = $trade;
        $total_trades++;
        $losing_trades++;
        $total_fees += $fee;
        $total_losses_pct += abs($trade['return_pct']);
        $capital -= $fee;
        continue;
    }

    // Simulate holding period
    $day_count   = 0;
    $sold        = false;
    $exit_price  = $entry_price;
    $exit_date   = $pick_date;
    $exit_reason = 'end_of_data';

    while ($day = $price_res->fetch_assoc()) {
        $day_count++;
        $day_high  = (float)$day['high'];
        $day_low   = (float)$day['low'];
        $day_close = (float)$day['close'];
        $day_date  = $day['price_date'];

        // Calculate P&L based on direction
        if ($direction === 'SHORT') {
            // SHORT: profit when price goes down
            $change_pct = (($entry_price - $day_close) / $entry_price) * 100;
            $worst_intraday = (($entry_price - $day_high) / $entry_price) * 100; // worst for short = high price
            $best_intraday  = (($entry_price - $day_low) / $entry_price) * 100;  // best for short = low price
        } else {
            // LONG: profit when price goes up
            $change_pct = (($day_close - $entry_price) / $entry_price) * 100;
            $worst_intraday = (($day_low - $entry_price) / $entry_price) * 100;
            $best_intraday  = (($day_high - $entry_price) / $entry_price) * 100;
        }

        // Check stop loss (intraday)
        if ($worst_intraday <= -$stop_loss && $stop_loss < 999) {
            // Stopped out at the stop loss level
            if ($direction === 'SHORT') {
                $exit_price = $entry_price * (1 + $stop_loss / 100);
            } else {
                $exit_price = $entry_price * (1 - $stop_loss / 100);
            }
            $exit_date = $day_date;
            $exit_reason = 'stop_loss';
            $sold = true;
            break;
        }

        // Check take profit (intraday)
        if ($best_intraday >= $take_profit && $take_profit < 999) {
            if ($direction === 'SHORT') {
                $exit_price = $entry_price * (1 - $take_profit / 100);
            } else {
                $exit_price = $entry_price * (1 + $take_profit / 100);
            }
            $exit_date = $day_date;
            $exit_reason = 'take_profit';
            $sold = true;
            break;
        }

        // Max hold
        if ($day_count >= $max_hold_days) {
            $exit_price = $day_close;
            $exit_date = $day_date;
            $exit_reason = 'max_hold';
            $sold = true;
            break;
        }

        $exit_price = $day_close;
        $exit_date = $day_date;
    }

    if (!$sold && $day_count > 0) {
        $exit_reason = 'end_of_data';
    }

    // Calculate P&L
    if ($direction === 'SHORT') {
        $gross_profit = ($entry_price - $exit_price) * $position_size;
    } else {
        $gross_profit = ($exit_price - $entry_price) * $position_size;
    }

    $entry_fee = round($entry_price * $position_size * $trading_fee_pct / 100, 2);
    $exit_fee  = round($exit_price * $position_size * $trading_fee_pct / 100, 2);
    $total_fee = $entry_fee + $exit_fee;
    $net_profit = $gross_profit - $total_fee;
    $return_pct = ($position_value > 0) ? ($net_profit / $position_value) * 100 : 0;

    $trade = array(
        'symbol'        => $symbol,
        'pair_name'     => $pair_name,
        'category'      => $category,
        'algorithm'     => $algo_name,
        'direction'     => $direction,
        'entry_date'    => $pick_date,
        'entry_price'   => round($entry_price, 8),
        'exit_date'     => $exit_date,
        'exit_price'    => round($exit_price, 8),
        'position_size' => $position_size,
        'gross_profit'  => round($gross_profit, 2),
        'fees_paid'     => round($total_fee, 2),
        'net_profit'    => round($net_profit, 2),
        'return_pct'    => round($return_pct, 4),
        'exit_reason'   => $exit_reason,
        'hold_days'     => $day_count
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
    if ($stddev > 0) $sharpe = round(($mean / $stddev) * sqrt(252), 4);
    if ($dcnt > 0) {
        $dstd = sqrt($dvar / $dcnt);
        if ($dstd > 0) $sortino = round(($mean / $dstd) * sqrt(252), 4);
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

// Direction breakdown
$dir_stats = array('LONG' => array('t' => 0, 'w' => 0, 'pnl' => 0), 'SHORT' => array('t' => 0, 'w' => 0, 'pnl' => 0));
foreach ($trades as $t) {
    $d = $t['direction'];
    if (!isset($dir_stats[$d])) $dir_stats[$d] = array('t' => 0, 'w' => 0, 'pnl' => 0);
    $dir_stats[$d]['t']++;
    if ($t['net_profit'] > 0) $dir_stats[$d]['w']++;
    $dir_stats[$d]['pnl'] += $t['net_profit'];
}
$direction_breakdown = array();
foreach ($dir_stats as $dname => $ds) {
    $direction_breakdown[] = array(
        'direction' => $dname,
        'trades' => $ds['t'],
        'win_rate' => ($ds['t'] > 0) ? round($ds['w'] / $ds['t'] * 100, 2) : 0,
        'total_pnl' => round($ds['pnl'], 2)
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
        'take_profit_pct'  => $take_profit,
        'stop_loss_pct'    => $stop_loss,
        'max_hold_days'    => $max_hold_days,
        'initial_capital'  => $initial_capital,
        'trading_fee_pct'  => $trading_fee_pct,
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
    'algorithm_breakdown'  => $algo_breakdown,
    'direction_breakdown'  => $direction_breakdown,
    'exit_reasons'         => $exit_reasons,
    'equity_curve'         => $equity_curve,
    'trades'               => $trades
);

// ─── Save Results ───
if ($save_results === 1) {
    $now = date('Y-m-d H:i:s');
    $run_name = $strategy . '_tp' . $take_profit . '_sl' . $stop_loss . '_' . $max_hold_days . 'd';
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

    $sql = "INSERT INTO cr_backtest_results
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
            $sd = $conn->real_escape_string($t['direction']);
            $se = $conn->real_escape_string($t['entry_date']);
            $sx = $conn->real_escape_string(isset($t['exit_date']) ? $t['exit_date'] : '');
            $sr = $conn->real_escape_string($t['exit_reason']);
            $conn->query("INSERT INTO cr_backtest_trades
                (backtest_id, symbol, algorithm_name, direction, entry_date, entry_price, exit_date, exit_price,
                 position_size, gross_profit, fees_paid, net_profit, return_pct, exit_reason, hold_days)
                VALUES ($bt_id, '$ss', '$sa', '$sd', '$se', " . $t['entry_price'] . ", '$sx', " . $t['exit_price'] . ",
                 " . $t['position_size'] . ", " . $t['gross_profit'] . ", " . $t['fees_paid'] . ",
                 " . $t['net_profit'] . ", " . $t['return_pct'] . ", '$sr', " . $t['hold_days'] . ")");
        }
    }

    $ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
    $conn->query("INSERT INTO cr_audit_log (action_type, details, ip_address, created_at)
                  VALUES ('backtest', '" . $conn->real_escape_string('CR Backtest: ' . $run_name) . "', '$ip', '$now')");
}

echo json_encode($response);
$conn->close();
?>
