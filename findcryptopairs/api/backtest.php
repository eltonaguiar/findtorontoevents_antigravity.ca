<?php
/**
 * Backtest crypto signals
 * PHP 5.2 compatible
 * Parameters: strategies (comma-sep), take_profit (%), stop_loss (%), max_hold_days, 
 *             exchange_fee_pct (%), initial_capital, position_size (%)
 */
require_once dirname(__FILE__) . '/db_connect.php';

function _get_param($key, $default) {
    if (isset($_POST[$key]) && $_POST[$key] !== '') return $_POST[$key];
    if (isset($_GET[$key]) && $_GET[$key] !== '') return $_GET[$key];
    return $default;
}

$strategies_filter = _get_param('strategies', '');
$take_profit = (float)_get_param('take_profit', 10);
$stop_loss = (float)_get_param('stop_loss', 5);
$max_hold_days = (int)_get_param('max_hold_days', 30);
$exchange_fee_pct = (float)_get_param('exchange_fee_pct', 0.1);
$initial_capital = (float)_get_param('initial_capital', 10000);
$position_size = (float)_get_param('position_size', 10);

// Build WHERE clause for strategies
$where_strategy = '';
if ($strategies_filter !== '') {
    $strategy_list = explode(',', $strategies_filter);
    $escaped = array();
    foreach ($strategy_list as $s) {
        $s = trim($s);
        if ($s !== '') {
            $escaped[] = "'" . $conn->real_escape_string($s) . "'";
        }
    }
    if (count($escaped) > 0) {
        $where_strategy = " AND strategy_name IN (" . implode(',', $escaped) . ")";
    }
}

// Fetch signals
$signals_sql = "SELECT id, pair, strategy_name, signal_date, entry_price, direction 
                FROM cp_signals 
                WHERE entry_price > 0 $where_strategy 
                ORDER BY signal_date ASC, pair ASC";
$signals_res = $conn->query($signals_sql);

if (!$signals_res || $signals_res->num_rows === 0) {
    echo json_encode(array(
        'ok' => false,
        'error' => 'No signals found. Run seed_signals.php first.',
        'params' => array('strategies' => $strategies_filter)
    ));
    $conn->close();
    exit;
}

// Preload all prices into memory for faster lookup
$prices_map = array();
$prices_res = $conn->query("SELECT pair, trade_date, open_price, high_price, low_price, close_price 
                            FROM cp_prices 
                            ORDER BY pair, trade_date ASC");
if ($prices_res) {
    while ($pr = $prices_res->fetch_assoc()) {
        $pair = $pr['pair'];
        if (!isset($prices_map[$pair])) {
            $prices_map[$pair] = array();
        }
        $prices_map[$pair][] = $pr;
    }
}

// Run backtest
$capital = $initial_capital;
$peak_capital = $initial_capital;
$max_drawdown = 0;
$total_trades = 0;
$winning_trades = 0;
$losing_trades = 0;
$total_fees = 0;
$total_wins_pct = 0;
$total_losses_pct = 0;
$best_trade = -9999;
$worst_trade = 9999;
$total_hold_days = 0;
$trades = array();
$daily_returns = array();

while ($signal = $signals_res->fetch_assoc()) {
    $pair = $signal['pair'];
    $entry_price = (float)$signal['entry_price'];
    $signal_date = $signal['signal_date'];
    $strategy_name = $signal['strategy_name'];
    $direction = isset($signal['direction']) ? strtolower($signal['direction']) : 'long';
    
    // Position sizing
    $position_value = $capital * ($position_size / 100);
    if ($position_value < 10) continue; // minimum $10 position
    $position_size_units = round($position_value / $entry_price, 8);
    if ($position_size_units <= 0) continue;
    
    // Get price data for this pair after signal date
    if (!isset($prices_map[$pair])) {
        // No price data - flat trade with fees
        $entry_fee = round($position_value * $exchange_fee_pct / 100, 2);
        $exit_fee = round($position_value * $exchange_fee_pct / 100, 2);
        $fee = $entry_fee + $exit_fee;
        $trade = array(
            'pair' => $pair,
            'strategy' => $strategy_name,
            'direction' => $direction,
            'entry_date' => $signal_date,
            'entry_price' => $entry_price,
            'exit_date' => $signal_date,
            'exit_price' => $entry_price,
            'position_size' => $position_size_units,
            'gross_profit' => 0,
            'fees_paid' => $fee,
            'net_profit' => -$fee,
            'return_pct' => round(-$fee / $position_value * 100, 4),
            'exit_reason' => 'no_price_data',
            'hold_days' => 0
        );
        $trades[] = $trade;
        $total_trades++;
        $losing_trades++;
        $total_fees += $fee;
        $total_losses_pct += abs($trade['return_pct']);
        $capital -= $fee;
        continue;
    }
    
    $prices = $prices_map[$pair];
    $found_start = false;
    $price_idx = 0;
    
    // Find starting price index (first price >= signal_date)
    for ($i = 0; $i < count($prices); $i++) {
        if ($prices[$i]['trade_date'] >= $signal_date) {
            $price_idx = $i;
            $found_start = true;
            break;
        }
    }
    
    if (!$found_start) {
        // Signal date is after all price data
        $entry_fee = round($position_value * $exchange_fee_pct / 100, 2);
        $exit_fee = round($position_value * $exchange_fee_pct / 100, 2);
        $fee = $entry_fee + $exit_fee;
        $trade = array(
            'pair' => $pair,
            'strategy' => $strategy_name,
            'direction' => $direction,
            'entry_date' => $signal_date,
            'entry_price' => $entry_price,
            'exit_date' => $signal_date,
            'exit_price' => $entry_price,
            'position_size' => $position_size_units,
            'gross_profit' => 0,
            'fees_paid' => $fee,
            'net_profit' => -$fee,
            'return_pct' => round(-$fee / $position_value * 100, 4),
            'exit_reason' => 'no_future_data',
            'hold_days' => 0
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
    $day_count = 0;
    $sold = false;
    $exit_price = $entry_price;
    $exit_date = $signal_date;
    $exit_reason = 'end_of_data';
    
    for ($i = $price_idx; $i < count($prices) && $day_count < $max_hold_days; $i++) {
        $day = $prices[$i];
        $day_count++;
        $day_high = (float)$day['high_price'];
        $day_low = (float)$day['low_price'];
        $day_close = (float)$day['close_price'];
        $day_date = $day['trade_date'];
        
        // Calculate P&L based on direction
        if ($direction === 'short') {
            // SHORT: profit when price goes down
            $change_pct = (($entry_price - $day_close) / $entry_price) * 100;
            $worst_intraday = (($entry_price - $day_high) / $entry_price) * 100;
            $best_intraday = (($entry_price - $day_low) / $entry_price) * 100;
        } else {
            // LONG: profit when price goes up
            $change_pct = (($day_close - $entry_price) / $entry_price) * 100;
            $worst_intraday = (($day_low - $entry_price) / $entry_price) * 100;
            $best_intraday = (($day_high - $entry_price) / $entry_price) * 100;
        }
        
        // Check stop loss (intraday)
        if ($worst_intraday <= -$stop_loss && $stop_loss < 999) {
            if ($direction === 'short') {
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
            if ($direction === 'short') {
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
    if ($direction === 'short') {
        $gross_profit = ($entry_price - $exit_price) * $position_size_units;
    } else {
        $gross_profit = ($exit_price - $entry_price) * $position_size_units;
    }
    
    $entry_fee = round($entry_price * $position_size_units * $exchange_fee_pct / 100, 2);
    $exit_fee = round($exit_price * $position_size_units * $exchange_fee_pct / 100, 2);
    $total_fee = $entry_fee + $exit_fee;
    $net_profit = $gross_profit - $total_fee;
    $return_pct = ($position_value > 0) ? ($net_profit / $position_value) * 100 : 0;
    
    $trade = array(
        'pair' => $pair,
        'strategy' => $strategy_name,
        'direction' => $direction,
        'entry_date' => $signal_date,
        'entry_price' => round($entry_price, 8),
        'exit_date' => $exit_date,
        'exit_price' => round($exit_price, 8),
        'position_size' => $position_size_units,
        'gross_profit' => round($gross_profit, 2),
        'fees_paid' => round($total_fee, 2),
        'net_profit' => round($net_profit, 2),
        'return_pct' => round($return_pct, 4),
        'exit_reason' => $exit_reason,
        'hold_days' => $day_count
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
}

// Aggregate metrics
$final_value = round($capital, 2);
$total_return_pct = ($initial_capital > 0) ? round(($capital - $initial_capital) / $initial_capital * 100, 4) : 0;
$win_rate = ($total_trades > 0) ? round($winning_trades / $total_trades * 100, 2) : 0;
$avg_win_pct = ($winning_trades > 0) ? round($total_wins_pct / $winning_trades, 4) : 0;
$avg_loss_pct = ($losing_trades > 0) ? round($total_losses_pct / $losing_trades, 4) : 0;
$avg_hold = ($total_trades > 0) ? round($total_hold_days / $total_trades, 2) : 0;

// Sharpe ratio
$sharpe = 0;
if (count($daily_returns) > 1) {
    $mean = array_sum($daily_returns) / count($daily_returns);
    $variance = 0;
    foreach ($daily_returns as $r) {
        $variance += ($r - $mean) * ($r - $mean);
    }
    $stddev = sqrt($variance / count($daily_returns));
    if ($stddev > 0) {
        $sharpe = round($mean / $stddev, 4);
    }
}

// Profit factor
$gross_wins = 0;
$gross_losses = 0;
foreach ($trades as $t) {
    if ($t['net_profit'] > 0) {
        $gross_wins += $t['net_profit'];
    } else {
        $gross_losses += abs($t['net_profit']);
    }
}
$profit_factor = ($gross_losses > 0) ? round($gross_wins / $gross_losses, 4) : ($gross_wins > 0 ? 999 : 0);

// Expectancy
$loss_rate = ($total_trades > 0) ? $losing_trades / $total_trades : 0;
$win_rate_dec = ($total_trades > 0) ? $winning_trades / $total_trades : 0;
$expectancy = round(($win_rate_dec * $avg_win_pct) - ($loss_rate * $avg_loss_pct), 4);

// Response
$response = array(
    'ok' => true,
    'params' => array(
        'strategies' => $strategies_filter,
        'take_profit' => $take_profit,
        'stop_loss' => $stop_loss,
        'max_hold_days' => $max_hold_days,
        'exchange_fee_pct' => $exchange_fee_pct,
        'initial_capital' => $initial_capital,
        'position_size' => $position_size
    ),
    'summary' => array(
        'total_trades' => $total_trades,
        'wins' => $winning_trades,
        'losses' => $losing_trades,
        'win_rate' => $win_rate,
        'total_return_pct' => $total_return_pct,
        'sharpe' => $sharpe,
        'max_drawdown' => round($max_drawdown, 4),
        'profit_factor' => $profit_factor,
        'expectancy' => $expectancy,
        'initial_capital' => $initial_capital,
        'final_value' => $final_value,
        'total_fees' => round($total_fees, 2)
    ),
    'trades' => $trades
);

// Audit log
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$now = date('Y-m-d H:i:s');
$details = 'Backtest: ' . $total_trades . ' trades, ' . $total_return_pct . '% return';
$conn->query("INSERT INTO cp_audit_log (action_type, details, ip_address, created_at) 
              VALUES ('backtest', '" . $conn->real_escape_string($details) . "', '$ip', '$now')");

echo json_encode($response);
$conn->close();
?>
