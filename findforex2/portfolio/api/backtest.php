<?php
/**
 * Backtesting Engine for Forex Portfolio Analysis
 * Runs simulated forex trades with pip-based pricing.
 * PHP 5.2 compatible.
 *
 * Key differences from stocks/mutual funds:
 * - Uses pip-based profit calculation
 * - Supports LONG and SHORT directions
 * - Leverage support (1x to 50x)
 * - Spread modeling (entry slippage in pips)
 * - Standard lot size = 100,000 units (micro lot = 1,000)
 */
require_once dirname(__FILE__) . '/db_connect.php';

function _fxp_param($key, $default) {
    if (isset($_POST[$key]) && $_POST[$key] !== '') return $_POST[$key];
    if (isset($_GET[$key]) && $_GET[$key] !== '') return $_GET[$key];
    return $default;
}

$portfolio_id = (int)_fxp_param('portfolio_id', 0);
$params = array();

if ($portfolio_id > 0) {
    $res = $conn->query("SELECT * FROM fxp_portfolios WHERE id=$portfolio_id");
    if ($res && $row = $res->fetch_assoc()) {
        $params['algorithms']      = $row['algorithm_filter'];
        $params['strategy']        = $row['strategy_type'];
        $params['take_profit_pips']= (float)$row['take_profit_pips'];
        $params['stop_loss_pips']  = (float)$row['stop_loss_pips'];
        $params['max_hold_days']   = (int)$row['max_hold_days'];
        $params['initial_capital'] = (float)$row['initial_capital'];
        $params['leverage']        = (int)$row['leverage'];
        $params['spread_pips']     = (float)$row['spread_pips'];
        $params['position_size']   = (float)$row['position_size_pct'];
        $params['max_positions']   = (int)$row['max_positions'];
    }
}

$algorithms      = _fxp_param('algorithms',      isset($params['algorithms']) ? $params['algorithms'] : '');
$strategy        = _fxp_param('strategy',         isset($params['strategy']) ? $params['strategy'] : 'balanced');
$tp_pips         = (float)_fxp_param('take_profit_pips', isset($params['take_profit_pips']) ? $params['take_profit_pips'] : 100);
$sl_pips         = (float)_fxp_param('stop_loss_pips',   isset($params['stop_loss_pips']) ? $params['stop_loss_pips'] : 50);
$max_hold_days   = (int)_fxp_param('max_hold_days',      isset($params['max_hold_days']) ? $params['max_hold_days'] : 30);
$initial_capital = (float)_fxp_param('initial_capital',   isset($params['initial_capital']) ? $params['initial_capital'] : 10000);
$leverage        = (int)_fxp_param('leverage',            isset($params['leverage']) ? $params['leverage'] : 10);
$spread_pips     = (float)_fxp_param('spread_pips',       isset($params['spread_pips']) ? $params['spread_pips'] : 1.5);
$position_pct    = (float)_fxp_param('position_size',     isset($params['position_size']) ? $params['position_size'] : 3);
$max_positions   = (int)_fxp_param('max_positions',       isset($params['max_positions']) ? $params['max_positions'] : 5);
$save_results    = (int)_fxp_param('save', 0);

if ($leverage < 1) $leverage = 1;
if ($leverage > 50) $leverage = 50;

// --- Fetch Picks ---
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

$sql = "SELECT fp.*, p.base_currency, p.quote_currency, p.category, p.pip_value
        FROM fxp_pair_picks fp
        LEFT JOIN fxp_pairs p ON fp.symbol = p.symbol
        WHERE fp.entry_price > 0 $where_algo
        ORDER BY fp.pick_date ASC, fp.symbol ASC";

$picks_res = $conn->query($sql);
if (!$picks_res || $picks_res->num_rows === 0) {
    echo json_encode(array(
        'ok' => false,
        'error' => 'No forex picks found. Import picks first via import_picks.php',
        'params' => array('algorithms' => $algorithms, 'strategy' => $strategy)
    ));
    $conn->close();
    exit;
}

// --- Run Backtest ---
$capital         = $initial_capital;
$peak_capital    = $initial_capital;
$max_drawdown    = 0;
$total_trades    = 0;
$winning_trades  = 0;
$losing_trades   = 0;
$total_spread    = 0;
$total_wins_pips = 0;
$total_losses_pips = 0;
$best_trade_pips  = -9999;
$worst_trade_pips = 9999;
$total_hold_days = 0;
$trades          = array();
$trade_returns   = array();
$equity_curve    = array();

while ($pick = $picks_res->fetch_assoc()) {
    $symbol     = $pick['symbol'];
    $entry_price= (float)$pick['entry_price'];
    $pick_date  = $pick['pick_date'];
    $algo_name  = $pick['algorithm_name'];
    $direction  = isset($pick['direction']) ? strtoupper($pick['direction']) : 'LONG';
    $pip_value  = isset($pick['pip_value']) ? (float)$pick['pip_value'] : 0.0001;
    $category   = isset($pick['category']) ? $pick['category'] : '';

    if ($pip_value <= 0) $pip_value = 0.0001;

    // Position sizing: use percentage of capital with leverage
    $position_value = $capital * ($position_pct / 100) * $leverage;
    // Convert to lot size (standard lot = 100,000 units)
    $lot_size = round($position_value / 100000, 4);
    if ($lot_size < 0.01) $lot_size = 0.01; // Minimum micro lot

    // Calculate spread cost in dollars
    // For standard lot: 1 pip = ~$10 (for most USD pairs)
    $pip_dollar_value = $lot_size * 100000 * $pip_value;
    // For JPY pairs, pip_value is 0.01, so 1 pip of USDJPY at lot_size * 100000 * 0.01
    // This simplifies: pip_dollar_value approximates the $ value per pip for this lot
    // For non-USD quote currencies, this is approximate but acceptable for backtesting
    $spread_cost = $spread_pips * $pip_dollar_value;

    // Fetch price history
    $safe_sym  = $conn->real_escape_string($symbol);
    $safe_date = $conn->real_escape_string($pick_date);
    $price_sql = "SELECT price_date, open_price, high_price, low_price, close_price FROM fxp_price_history
                  WHERE symbol='$safe_sym' AND price_date >= '$safe_date'
                  ORDER BY price_date ASC
                  LIMIT " . ($max_hold_days + 5);
    $price_res = $conn->query($price_sql);

    if (!$price_res || $price_res->num_rows === 0) {
        // No price data - flat trade minus spread
        $trade = array(
            'symbol' => $symbol, 'category' => $category, 'direction' => $direction,
            'algorithm' => $algo_name, 'entry_date' => $pick_date, 'entry_price' => $entry_price,
            'exit_date' => $pick_date, 'exit_price' => $entry_price, 'lot_size' => $lot_size,
            'pip_profit' => -$spread_pips, 'spread_cost' => round($spread_cost, 2),
            'gross_profit' => 0, 'net_profit' => round(-$spread_cost, 2),
            'return_pct' => round(-$spread_cost / ($capital * $position_pct / 100) * 100, 4),
            'exit_reason' => 'no_price_data', 'hold_days' => 0
        );
        $trades[] = $trade;
        $total_trades++;
        $losing_trades++;
        $total_spread += $spread_cost;
        $total_losses_pips += $spread_pips;
        $capital -= $spread_cost;
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
        $day_high  = (float)$day['high_price'];
        $day_low   = (float)$day['low_price'];
        $day_close = (float)$day['close_price'];
        $day_date  = $day['price_date'];

        // Calculate pip movement based on direction
        if ($direction === 'LONG') {
            $pips_from_high = ($day_high - $entry_price) / $pip_value;
            $pips_from_low  = ($day_low - $entry_price) / $pip_value;
            $pips_at_close  = ($day_close - $entry_price) / $pip_value;
        } else {
            // SHORT: profit when price goes down
            $pips_from_high = ($entry_price - $day_low) / $pip_value;
            $pips_from_low  = ($entry_price - $day_high) / $pip_value;
            $pips_at_close  = ($entry_price - $day_close) / $pip_value;
        }

        // Check stop loss first (worst case in a day)
        if ($pips_from_low <= -$sl_pips && $sl_pips < 9999) {
            if ($direction === 'LONG') {
                $exit_price = $entry_price - ($sl_pips * $pip_value);
            } else {
                $exit_price = $entry_price + ($sl_pips * $pip_value);
            }
            $exit_date = $day_date;
            $exit_reason = 'stop_loss';
            $sold = true;
            break;
        }

        // Check take profit (best case in a day)
        if ($pips_from_high >= $tp_pips && $tp_pips < 9999) {
            if ($direction === 'LONG') {
                $exit_price = $entry_price + ($tp_pips * $pip_value);
            } else {
                $exit_price = $entry_price - ($tp_pips * $pip_value);
            }
            $exit_date = $day_date;
            $exit_reason = 'take_profit';
            $sold = true;
            break;
        }

        // Max hold reached
        if ($day_count >= $max_hold_days) {
            $exit_price = $day_close;
            $exit_date = $day_date;
            $exit_reason = 'max_hold';
            $sold = true;
            break;
        }
    }

    if (!$sold && $day_count > 0) {
        $exit_reason = 'end_of_data';
    }

    // Calculate P&L in pips
    if ($direction === 'LONG') {
        $raw_pips = ($exit_price - $entry_price) / $pip_value;
    } else {
        $raw_pips = ($entry_price - $exit_price) / $pip_value;
    }
    $net_pips = $raw_pips - $spread_pips;

    // Convert pips to dollars
    $gross_dollar = $raw_pips * $pip_dollar_value;
    $net_dollar = $net_pips * $pip_dollar_value;

    $margin_used = ($capital * $position_pct / 100);
    $return_pct = ($margin_used > 0) ? ($net_dollar / $margin_used) * 100 : 0;

    $trade = array(
        'symbol'       => $symbol,
        'category'     => $category,
        'direction'    => $direction,
        'algorithm'    => $algo_name,
        'entry_date'   => $pick_date,
        'entry_price'  => round($entry_price, 6),
        'exit_date'    => $exit_date,
        'exit_price'   => round($exit_price, 6),
        'lot_size'     => $lot_size,
        'pip_profit'   => round($net_pips, 2),
        'spread_cost'  => round($spread_cost, 2),
        'gross_profit' => round($gross_dollar, 2),
        'net_profit'   => round($net_dollar, 2),
        'return_pct'   => round($return_pct, 4),
        'exit_reason'  => $exit_reason,
        'hold_days'    => $day_count
    );

    $trades[] = $trade;
    $total_trades++;
    $total_spread += $spread_cost;
    $capital += $net_dollar;
    $total_hold_days += $day_count;

    if ($net_pips > $best_trade_pips) $best_trade_pips = $net_pips;
    if ($net_pips < $worst_trade_pips) $worst_trade_pips = $net_pips;

    if ($net_dollar > 0) {
        $winning_trades++;
        $total_wins_pips += $net_pips;
    } else {
        $losing_trades++;
        $total_losses_pips += abs($net_pips);
    }

    if ($capital > $peak_capital) $peak_capital = $capital;
    $drawdown = ($peak_capital > 0) ? (($peak_capital - $capital) / $peak_capital) * 100 : 0;
    if ($drawdown > $max_drawdown) $max_drawdown = $drawdown;

    $trade_returns[] = $return_pct;
    $equity_curve[] = array('trade' => $total_trades, 'capital' => round($capital, 2), 'date' => $exit_date);
}

// --- Aggregate Metrics ---
$final_value   = round($capital, 2);
$total_return  = ($initial_capital > 0) ? round(($capital - $initial_capital) / $initial_capital * 100, 4) : 0;
$win_rate      = ($total_trades > 0) ? round($winning_trades / $total_trades * 100, 2) : 0;
$avg_win_pips  = ($winning_trades > 0) ? round($total_wins_pips / $winning_trades, 2) : 0;
$avg_loss_pips = ($losing_trades > 0) ? round($total_losses_pips / $losing_trades, 2) : 0;
$avg_hold      = ($total_trades > 0) ? round($total_hold_days / $total_trades, 2) : 0;

// Sharpe & Sortino
$sharpe = 0;
$sortino = 0;
if (count($trade_returns) > 1) {
    $mean = array_sum($trade_returns) / count($trade_returns);
    $variance = 0;
    $dvar = 0;
    $dcnt = 0;
    foreach ($trade_returns as $r) {
        $variance += ($r - $mean) * ($r - $mean);
        if ($r < 0) { $dvar += $r * $r; $dcnt++; }
    }
    $stddev = sqrt($variance / count($trade_returns));
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

// Expectancy in pips
$loss_rate = ($total_trades > 0) ? $losing_trades / $total_trades : 0;
$win_rate_dec = ($total_trades > 0) ? $winning_trades / $total_trades : 0;
$expectancy_pips = round(($win_rate_dec * $avg_win_pips) - ($loss_rate * $avg_loss_pips), 4);

// Per-algorithm breakdown
$algo_stats = array();
foreach ($trades as $t) {
    $a = $t['algorithm'];
    if (!isset($algo_stats[$a])) $algo_stats[$a] = array('trades' => 0, 'wins' => 0, 'losses' => 0, 'total_pips' => 0, 'total_pnl' => 0);
    $algo_stats[$a]['trades']++;
    $algo_stats[$a]['total_pips'] += $t['pip_profit'];
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
        'avg_pips' => ($as['trades'] > 0) ? round($as['total_pips'] / $as['trades'], 2) : 0,
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

// --- Response ---
$response = array(
    'ok' => true,
    'params' => array(
        'algorithms'       => $algorithms,
        'strategy'         => $strategy,
        'take_profit_pips' => $tp_pips,
        'stop_loss_pips'   => $sl_pips,
        'max_hold_days'    => $max_hold_days,
        'initial_capital'  => $initial_capital,
        'leverage'         => $leverage,
        'spread_pips'      => $spread_pips,
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
        'avg_win_pips'         => $avg_win_pips,
        'avg_loss_pips'        => $avg_loss_pips,
        'best_trade_pips'      => ($total_trades > 0) ? round($best_trade_pips, 2) : 0,
        'worst_trade_pips'     => ($total_trades > 0) ? round($worst_trade_pips, 2) : 0,
        'avg_hold_days'        => $avg_hold,
        'max_drawdown_pct'     => round($max_drawdown, 4),
        'total_spread_cost'    => round($total_spread, 2),
        'leverage_used'        => $leverage,
        'sharpe_ratio'         => $sharpe,
        'sortino_ratio'        => $sortino,
        'profit_factor'        => $profit_factor,
        'expectancy_pips'      => $expectancy_pips
    ),
    'algorithm_breakdown' => $algo_breakdown,
    'exit_reasons' => $exit_reasons,
    'equity_curve' => $equity_curve,
    'trades' => $trades
);

// --- Save Results ---
if ($save_results === 1) {
    $now = date('Y-m-d H:i:s');
    $run_name = $strategy . '_tp' . $tp_pips . '_sl' . $sl_pips . '_' . $max_hold_days . 'd_' . $leverage . 'x';
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

    $sql = "INSERT INTO fxp_backtest_results
            (portfolio_id, run_name, algorithm_filter, strategy_type, start_date, end_date,
             initial_capital, final_value, total_return_pct, total_trades, winning_trades,
             losing_trades, win_rate, avg_win_pips, avg_loss_pips, best_trade_pips, worst_trade_pips,
             max_drawdown_pct, total_spread_cost, sharpe_ratio, sortino_ratio, profit_factor,
             expectancy_pips, avg_hold_days, leverage_used, params_json, created_at)
            VALUES ($portfolio_id, '$safe_name', '$safe_algos', '$safe_strat',
                    '" . $conn->real_escape_string($start_d) . "', '" . $conn->real_escape_string($end_d) . "',
                    $initial_capital, $final_value, $total_return, $total_trades, $winning_trades,
                    $losing_trades, $win_rate, $avg_win_pips, $avg_loss_pips,
                    " . (($total_trades > 0) ? round($best_trade_pips, 2) : 0) . ",
                    " . (($total_trades > 0) ? round($worst_trade_pips, 2) : 0) . ",
                    " . round($max_drawdown, 4) . ", " . round($total_spread, 2) . ",
                    $sharpe, $sortino, $profit_factor, $expectancy_pips, $avg_hold,
                    $leverage, '$params_json', '$now')";

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
            $conn->query("INSERT INTO fxp_backtest_trades
                (backtest_id, symbol, algorithm_name, direction, entry_date, entry_price, exit_date, exit_price,
                 lot_size, pip_profit, spread_cost, gross_profit, net_profit, return_pct, exit_reason, hold_days)
                VALUES ($bt_id, '$ss', '$sa', '$sd', '$se', " . $t['entry_price'] . ", '$sx', " . $t['exit_price'] . ",
                 " . $t['lot_size'] . ", " . $t['pip_profit'] . ", " . $t['spread_cost'] . ",
                 " . $t['gross_profit'] . ", " . $t['net_profit'] . ", " . $t['return_pct'] . ", '$sr', " . $t['hold_days'] . ")");
        }
    }

    $ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
    $conn->query("INSERT INTO fxp_audit_log (action_type, details, ip_address, created_at)
                  VALUES ('backtest', '" . $conn->real_escape_string('FX Backtest: ' . $run_name) . "', '$ip', '$now')");
}

echo json_encode($response);
$conn->close();
?>
