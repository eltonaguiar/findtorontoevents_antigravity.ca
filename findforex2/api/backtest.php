<?php
/**
 * Backtest forex signals
 * PHP 5.2 compatible
 *
 * Parameters:
 *   strategies      - comma-separated strategy names (empty = all)
 *   take_profit     - take profit % (default 2)
 *   stop_loss       - stop loss % (default 1)
 *   max_hold_days   - max holding period (default 14)
 *   spread_pips     - spread in pips (default 2)
 *   initial_capital - starting capital (default 10000)
 *   position_size   - % of capital per trade (default 10)
 */
require_once dirname(__FILE__) . '/db_connect.php';

// ─── Parse Parameters ───
function _bt_param($key, $default) {
    if (isset($_POST[$key]) && $_POST[$key] !== '') return $_POST[$key];
    if (isset($_GET[$key]) && $_GET[$key] !== '') return $_GET[$key];
    return $default;
}

$strategies_filter = _bt_param('strategies', '');
$take_profit_pct = (float)_bt_param('take_profit', 2);
$stop_loss_pct = (float)_bt_param('stop_loss', 1);
$max_hold_days = (int)_bt_param('max_hold_days', 14);
$spread_pips = (float)_bt_param('spread_pips', 2);
$initial_capital = (float)_bt_param('initial_capital', 10000);
$position_size_pct = (float)_bt_param('position_size', 10);

// ─── Fetch Signals ───
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

$sql = "SELECT * FROM fx_signals WHERE entry_price > 0 $where_strategy ORDER BY signal_date ASC, pair ASC";
$signals_res = $conn->query($sql);

if (!$signals_res) {
    echo json_encode(array('ok' => false, 'error' => 'Failed to fetch signals: ' . $conn->error));
    exit;
}

// ─── Preload Prices ───
$prices_cache = array();
$prices_res = $conn->query("SELECT pair, trade_date, open_price, high_price, low_price, close_price 
                            FROM fx_prices 
                            ORDER BY pair, trade_date ASC");
if ($prices_res) {
    while ($row = $prices_res->fetch_assoc()) {
        $pair = $row['pair'];
        if (!isset($prices_cache[$pair])) {
            $prices_cache[$pair] = array();
        }
        $prices_cache[$pair][$row['trade_date']] = array(
            'open' => (float)$row['open_price'],
            'high' => (float)$row['high_price'],
            'low' => (float)$row['low_price'],
            'close' => (float)$row['close_price']
        );
    }
}

// ─── Backtest Loop ───
$capital = $initial_capital;
$trades = array();
$total_trades = 0;
$winning_trades = 0;
$losing_trades = 0;
$total_wins_pct = 0;
$total_losses_pct = 0;
$total_spread_cost = 0;
$peak_capital = $initial_capital;
$max_drawdown = 0;
$daily_returns = array();

while ($signal = $signals_res->fetch_assoc()) {
    $pair = $signal['pair'];
    $entry_date = $signal['signal_date'];
    $entry_price = (float)$signal['entry_price'];
    $direction = $signal['direction'];
    
    if (!isset($prices_cache[$pair])) {
        continue;
    }
    
    // Find entry date in prices
    $entry_timestamp = strtotime($entry_date);
    $exit_date = null;
    $exit_price = 0;
    $exit_reason = '';
    $hold_days = 0;
    
    // Calculate TP/SL prices (for long positions)
    $tp_price = $entry_price * (1 + $take_profit_pct / 100);
    $sl_price = $entry_price * (1 - $stop_loss_pct / 100);
    
    // Get pip value for this pair (default 0.0001 for most pairs)
    $pip_value = 0.0001;
    $pair_info = $conn->query("SELECT pip_value FROM fx_pairs WHERE pair = '" . $conn->real_escape_string($pair) . "'");
    if ($pair_info && $pair_row = $pair_info->fetch_assoc()) {
        $pip_value = (float)$pair_row['pip_value'];
    }
    
    // Calculate spread cost as %: (spread_pips * pip_value / entry_price) * 100
    $spread_cost_pct = ($spread_pips * $pip_value / $entry_price) * 100;
    
    // Look through subsequent prices
    $found_entry = false;
    foreach ($prices_cache[$pair] as $price_date => $price_data) {
        $price_timestamp = strtotime($price_date);
        
        // Skip until we reach entry date
        if ($price_timestamp < $entry_timestamp) {
            continue;
        }
        
        if (!$found_entry) {
            $found_entry = true;
            $hold_days = 0;
        }
        
        $hold_days++;
        
        // Check TP hit
        if ($price_data['high'] >= $tp_price) {
            $exit_date = $price_date;
            $exit_price = $tp_price;
            $exit_reason = 'take_profit';
            break;
        }
        
        // Check SL hit
        if ($price_data['low'] <= $sl_price) {
            $exit_date = $price_date;
            $exit_price = $sl_price;
            $exit_reason = 'stop_loss';
            break;
        }
        
        // Check max hold days
        if ($hold_days >= $max_hold_days) {
            $exit_date = $price_date;
            $exit_price = $price_data['close'];
            $exit_reason = 'max_hold';
            break;
        }
    }
    
    // If no exit found, skip this signal
    if (!$exit_date) {
        continue;
    }
    
    // Calculate trade metrics
    $position_value = $capital * ($position_size_pct / 100);
    $return_pct = (($exit_price - $entry_price) / $entry_price) * 100;
    $gross_profit = $position_value * ($return_pct / 100);
    $spread_cost = $position_value * ($spread_cost_pct / 100);
    $net_profit = $gross_profit - $spread_cost;
    
    $capital += $net_profit;
    $total_trades++;
    $total_spread_cost += $spread_cost;
    
    if ($net_profit > 0) {
        $winning_trades++;
        $total_wins_pct += $return_pct;
    } else {
        $losing_trades++;
        $total_losses_pct += abs($return_pct);
    }
    
    // Track drawdown
    if ($capital > $peak_capital) {
        $peak_capital = $capital;
    }
    $drawdown = ($peak_capital > 0) ? (($peak_capital - $capital) / $peak_capital) * 100 : 0;
    if ($drawdown > $max_drawdown) {
        $max_drawdown = $drawdown;
    }
    
    // Daily return
    $daily_returns[] = $return_pct;
    
    // Store trade
    $trades[] = array(
        'pair' => $pair,
        'strategy' => $signal['strategy_name'],
        'entry_date' => $entry_date,
        'exit_date' => $exit_date,
        'entry_price' => round($entry_price, 6),
        'exit_price' => round($exit_price, 6),
        'direction' => $direction,
        'hold_days' => $hold_days,
        'exit_reason' => $exit_reason,
        'return_pct' => round($return_pct, 4),
        'gross_profit' => round($gross_profit, 2),
        'spread_cost' => round($spread_cost, 2),
        'net_profit' => round($net_profit, 2)
    );
}

// ─── Calculate Metrics ───
$final_value = round($capital, 2);
$total_return_pct = ($initial_capital > 0) ? round(($capital - $initial_capital) / $initial_capital * 100, 4) : 0;
$win_rate = ($total_trades > 0) ? round($winning_trades / $total_trades * 100, 2) : 0;
$avg_win_pct = ($winning_trades > 0) ? round($total_wins_pct / $winning_trades, 4) : 0;
$avg_loss_pct = ($losing_trades > 0) ? round($total_losses_pct / $losing_trades, 4) : 0;

// Sharpe ratio — annualized: mean/stddev * sqrt(252)
$sharpe = 0;
if (count($daily_returns) > 1) {
    $mean = array_sum($daily_returns) / count($daily_returns);
    $variance = 0;
    foreach ($daily_returns as $r) {
        $variance += ($r - $mean) * ($r - $mean);
    }
    $stddev = sqrt($variance / count($daily_returns));
    if ($stddev > 0) {
        $sharpe = round(($mean / $stddev) * sqrt(252), 4);
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

// ─── Summary ───
$summary = array(
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
    'total_spread_cost' => round($total_spread_cost, 2),
    'avg_win_pct' => $avg_win_pct,
    'avg_loss_pct' => $avg_loss_pct
);

// ─── Parameters Used ───
$params = array(
    'strategies' => $strategies_filter,
    'take_profit' => $take_profit_pct,
    'stop_loss' => $stop_loss_pct,
    'max_hold_days' => $max_hold_days,
    'spread_pips' => $spread_pips,
    'initial_capital' => $initial_capital,
    'position_size' => $position_size_pct
);

// Audit log
$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : 'unknown';
$ip_esc = $conn->real_escape_string($ip);
$details = "Backtest: $total_trades trades, " . round($total_return_pct, 2) . "% return";
$details_esc = $conn->real_escape_string($details);
$now = date('Y-m-d H:i:s');
$conn->query("INSERT INTO fx_audit_log (action_type, details, ip_address, created_at) 
              VALUES ('backtest', '$details_esc', '$ip_esc', '$now')");

$result = array(
    'ok' => true,
    'summary' => $summary,
    'trades' => $trades,
    'params' => $params
);

echo json_encode($result);
$conn->close();
?>
