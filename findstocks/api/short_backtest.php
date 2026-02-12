<?php
/**
 * Short-Selling Backtest Engine
 * Simulates short positions: borrow-and-sell at entry, buy-back (cover) at exit.
 * Profits when price DROPS; loses when price RISES.
 * PHP 5.2 compatible.
 *
 * Usage: GET with parameters:
 *   algorithms     - comma-separated algorithm names (empty = all)
 *   take_profit    - target profit % when price DROPS (e.g. 10 = cover when stock drops 10%)
 *   stop_loss      - max loss % when price RISES (e.g. 5 = cover when stock rises 5%)
 *   max_hold_days  - max holding period
 *   initial_capital- starting capital (default 10000)
 *   commission     - commission per trade in $ (default 10)
 *   slippage       - slippage % (default 0.5)
 *   position_size  - % of capital per position (default 10)
 *   regime         - bull|bear|all (filter by market regime, default all)
 */
require_once dirname(__FILE__) . '/db_connect.php';

// ─── Parse Parameters ───
function _sp($key, $default) {
    if (isset($_GET[$key]) && $_GET[$key] !== '') return $_GET[$key];
    if (isset($_POST[$key]) && $_POST[$key] !== '') return $_POST[$key];
    return $default;
}

$algorithms      = _sp('algorithms', '');
$take_profit     = (float)_sp('take_profit', 10);
$stop_loss       = (float)_sp('stop_loss', 5);
$max_hold_days   = (int)_sp('max_hold_days', 7);
$initial_capital = (float)_sp('initial_capital', 10000);
$commission      = (float)_sp('commission', 10);
$slippage_pct    = (float)_sp('slippage', 0.5);
$position_pct    = (float)_sp('position_size', 10);
$regime_filter   = _sp('regime', 'all');

// ─── Build algorithm filter ───
$where_algo = '';
if ($algorithms !== '') {
    $algo_list = explode(',', $algorithms);
    $escaped = array();
    foreach ($algo_list as $a) {
        $a = trim($a);
        if ($a !== '') $escaped[] = "'" . $conn->real_escape_string($a) . "'";
    }
    if (count($escaped) > 0) {
        $where_algo = " AND sp.algorithm_name IN (" . implode(',', $escaped) . ")";
    }
}

// ─── Fetch Picks ───
$sql = "SELECT sp.*, s.company_name
        FROM stock_picks sp
        LEFT JOIN stocks s ON sp.ticker = s.ticker
        WHERE sp.entry_price > 0 $where_algo
        ORDER BY sp.pick_date ASC, sp.ticker ASC";

$picks_res = $conn->query($sql);
if (!$picks_res || $picks_res->num_rows === 0) {
    echo json_encode(array('ok' => false, 'error' => 'No picks found'));
    $conn->close();
    exit;
}

// ─── Optional: Detect market regime via SPY ───
// Load SPY data to tag each pick date as bull/bear/sideways
$spy_data = array();
$spy_res = $conn->query("SELECT trade_date, close_price FROM daily_prices WHERE ticker='SPY' ORDER BY trade_date ASC");
if ($spy_res) {
    while ($row = $spy_res->fetch_assoc()) {
        $spy_data[$row['trade_date']] = (float)$row['close_price'];
    }
}

function _detect_regime($pick_date, $spy_data) {
    // Compare SPY 5-day moving average trend
    $dates = array_keys($spy_data);
    $idx = array_search($pick_date, $dates);
    if ($idx === false || $idx < 10) return 'unknown';

    $recent_5 = 0;
    $prior_5 = 0;
    for ($i = 0; $i < 5; $i++) {
        $k1 = $dates[$idx - $i];
        $k2 = $dates[$idx - 5 - $i];
        $recent_5 += $spy_data[$k1];
        $prior_5 += $spy_data[$k2];
    }
    $recent_5 = $recent_5 / 5;
    $prior_5 = $prior_5 / 5;

    $change_pct = ($prior_5 > 0) ? (($recent_5 - $prior_5) / $prior_5) * 100 : 0;

    if ($change_pct > 1) return 'bull';
    if ($change_pct < -1) return 'bear';
    return 'sideways';
}

// ─── Run Short-Selling Backtest ───
$capital         = $initial_capital;
$peak_capital    = $initial_capital;
$max_drawdown    = 0;
$total_trades    = 0;
$winning_trades  = 0;
$losing_trades   = 0;
$total_commission = 0;
$trades          = array();
$daily_returns   = array();
$regime_stats    = array('bull' => array('wins' => 0, 'losses' => 0, 'pnl' => 0),
                         'bear' => array('wins' => 0, 'losses' => 0, 'pnl' => 0),
                         'sideways' => array('wins' => 0, 'losses' => 0, 'pnl' => 0),
                         'unknown' => array('wins' => 0, 'losses' => 0, 'pnl' => 0));

while ($pick = $picks_res->fetch_assoc()) {
    $ticker     = $pick['ticker'];
    $entry_price = (float)$pick['entry_price'];
    $pick_date   = $pick['pick_date'];
    $algo_name   = $pick['algorithm_name'];
    $company     = isset($pick['company_name']) ? $pick['company_name'] : '';

    // Detect market regime
    $regime = _detect_regime($pick_date, $spy_data);
    if ($regime_filter !== 'all' && $regime !== $regime_filter) continue;

    // Apply slippage to SHORT entry — we SELL first, so slippage reduces our sell price
    $effective_entry = $entry_price * (1 - $slippage_pct / 100);

    // Position sizing
    $position_value = $capital * ($position_pct / 100);
    if ($position_value < $effective_entry + $commission) continue;
    $shares = (int)floor(($position_value - $commission) / $effective_entry);
    if ($shares <= 0) continue;

    // Fetch daily prices
    $safe_ticker = $conn->real_escape_string($ticker);
    $safe_date   = $conn->real_escape_string($pick_date);
    $price_sql = "SELECT trade_date, open_price, high_price, low_price, close_price
                  FROM daily_prices
                  WHERE ticker='$safe_ticker' AND trade_date >= '$safe_date'
                  ORDER BY trade_date ASC
                  LIMIT " . ($max_hold_days + 5);
    $price_res = $conn->query($price_sql);

    if (!$price_res || $price_res->num_rows === 0) {
        $trade = array(
            'ticker' => $ticker, 'company' => $company, 'algorithm' => $algo_name,
            'direction' => 'SHORT', 'regime' => $regime,
            'entry_date' => $pick_date, 'entry_price' => round($effective_entry, 4),
            'exit_date' => $pick_date, 'exit_price' => round($entry_price, 4),
            'shares' => $shares, 'gross_profit' => 0,
            'commission_paid' => $commission * 2, 'net_profit' => -($commission * 2),
            'return_pct' => round(-($commission * 2) / ($effective_entry * $shares) * 100, 4),
            'exit_reason' => 'no_price_data', 'hold_days' => 0
        );
        $trades[] = $trade;
        $total_trades++;
        $losing_trades++;
        $total_commission += $commission * 2;
        $capital -= $commission * 2;
        $regime_stats[$regime]['losses']++;
        $regime_stats[$regime]['pnl'] -= $commission * 2;
        continue;
    }

    // ─── Simulate short position ───
    // SHORT: profit = (entry - exit) * shares
    // Take profit when price DROPS to target (entry * (1 - tp%))
    // Stop loss when price RISES to threshold (entry * (1 + sl%))
    $day_count   = 0;
    $sold        = false;
    $exit_price  = 0;
    $exit_date   = '';
    $exit_reason = '';
    $first_day   = true;
    $day_close   = 0;

    while ($day = $price_res->fetch_assoc()) {
        if ($first_day) $first_day = false;
        $day_count++;
        $day_high  = (float)$day['high_price'];
        $day_low   = (float)$day['low_price'];
        $day_close = (float)$day['close_price'];
        $day_date  = $day['trade_date'];

        // SHORT take profit: price drops to target
        $tp_price = $effective_entry * (1 - $take_profit / 100);
        // SHORT stop loss: price rises above threshold
        $sl_price = $effective_entry * (1 + $stop_loss / 100);

        // Check stop loss FIRST — price rising is bad for shorts
        if ($day_high >= $sl_price && $stop_loss < 999) {
            $exit_price  = $sl_price;
            $exit_date   = $day_date;
            $exit_reason = 'stop_loss_short';
            $sold = true;
            break;
        }

        // Check take profit — price dropping is good for shorts
        if ($day_low <= $tp_price && $take_profit < 999) {
            $exit_price  = $tp_price;
            $exit_date   = $day_date;
            $exit_reason = 'take_profit_short';
            $sold = true;
            break;
        }

        // Max hold
        if ($day_count >= $max_hold_days) {
            $exit_price  = $day_close;
            $exit_date   = $day_date;
            $exit_reason = 'max_hold';
            $sold = true;
            break;
        }
    }

    if (!$sold) {
        if ($day_count > 0 && $day_close > 0) {
            $exit_price = $day_close;
            $exit_date  = $day_date;
        } else {
            $exit_price = $entry_price;
            $exit_date  = $pick_date;
        }
        $exit_reason = 'end_of_data';
    }

    // Apply slippage to cover (buying back) — price rises slightly against us
    $effective_exit = $exit_price * (1 + $slippage_pct / 100);

    // SHORT P/L: profit when entry > exit
    $gross_profit = ($effective_entry - $effective_exit) * $shares;
    $comm_total   = $commission * 2;
    $net_profit   = $gross_profit - $comm_total;
    $return_pct   = ($effective_entry * $shares > 0)
                    ? ($net_profit / ($effective_entry * $shares)) * 100
                    : 0;

    $trade = array(
        'ticker'         => $ticker,
        'company'        => $company,
        'algorithm'      => $algo_name,
        'direction'      => 'SHORT',
        'regime'         => $regime,
        'entry_date'     => $pick_date,
        'entry_price'    => round($effective_entry, 4),
        'exit_date'      => $exit_date,
        'exit_price'     => round($effective_exit, 4),
        'shares'         => $shares,
        'gross_profit'   => round($gross_profit, 2),
        'commission_paid'=> round($comm_total, 2),
        'net_profit'     => round($net_profit, 2),
        'return_pct'     => round($return_pct, 4),
        'exit_reason'    => $exit_reason,
        'hold_days'      => $day_count
    );

    $trades[] = $trade;
    $total_trades++;
    $total_commission += $comm_total;
    $capital += $net_profit;

    if ($net_profit > 0) {
        $winning_trades++;
        $regime_stats[$regime]['wins']++;
    } else {
        $losing_trades++;
        $regime_stats[$regime]['losses']++;
    }
    $regime_stats[$regime]['pnl'] += $net_profit;

    if ($capital > $peak_capital) $peak_capital = $capital;
    $drawdown = ($peak_capital > 0) ? (($peak_capital - $capital) / $peak_capital) * 100 : 0;
    if ($drawdown > $max_drawdown) $max_drawdown = $drawdown;

    $daily_returns[] = $return_pct;
}

// ─── Aggregate Metrics ───
$final_value  = round($capital, 2);
$total_return = ($initial_capital > 0) ? round(($capital - $initial_capital) / $initial_capital * 100, 4) : 0;
$win_rate     = ($total_trades > 0) ? round($winning_trades / $total_trades * 100, 2) : 0;

$sharpe = 0;
if (count($daily_returns) > 1) {
    $mean = array_sum($daily_returns) / count($daily_returns);
    $variance = 0;
    foreach ($daily_returns as $r) $variance += ($r - $mean) * ($r - $mean);
    $stddev = sqrt($variance / count($daily_returns));
    if ($stddev > 0) $sharpe = round(($mean / $stddev) * sqrt(252), 4);
}

$gross_wins = 0; $gross_losses = 0;
foreach ($trades as $t) {
    if ($t['net_profit'] > 0) $gross_wins += $t['net_profit'];
    else $gross_losses += abs($t['net_profit']);
}
$profit_factor = ($gross_losses > 0) ? round($gross_wins / $gross_losses, 4) : ($gross_wins > 0 ? 999 : 0);

// ─── Regime Summary ───
$regime_summary = array();
foreach ($regime_stats as $rname => $rs) {
    $rtotal = $rs['wins'] + $rs['losses'];
    $regime_summary[$rname] = array(
        'trades' => $rtotal,
        'wins' => $rs['wins'],
        'losses' => $rs['losses'],
        'win_rate' => ($rtotal > 0) ? round($rs['wins'] / $rtotal * 100, 2) : 0,
        'total_pnl' => round($rs['pnl'], 2)
    );
}

echo json_encode(array(
    'ok' => true,
    'direction' => 'SHORT',
    'params' => array(
        'algorithms' => $algorithms, 'take_profit_pct' => $take_profit,
        'stop_loss_pct' => $stop_loss, 'max_hold_days' => $max_hold_days,
        'initial_capital' => $initial_capital, 'commission' => $commission,
        'slippage_pct' => $slippage_pct, 'regime_filter' => $regime_filter
    ),
    'summary' => array(
        'initial_capital' => $initial_capital, 'final_value' => $final_value,
        'total_return_pct' => $total_return, 'total_trades' => $total_trades,
        'winning_trades' => $winning_trades, 'losing_trades' => $losing_trades,
        'win_rate' => $win_rate, 'max_drawdown_pct' => round($max_drawdown, 4),
        'total_commissions' => round($total_commission, 2),
        'sharpe_ratio' => $sharpe, 'profit_factor' => $profit_factor,
        'gross_wins' => round($gross_wins, 2), 'gross_losses' => round($gross_losses, 2)
    ),
    'regime_breakdown' => $regime_summary,
    'trades' => $trades
));
$conn->close();
?>
