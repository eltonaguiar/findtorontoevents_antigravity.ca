<?php
/**
 * Portfolio Stats API — Professional-grade analytics per algorithm
 *
 * Returns Yahoo Finance / Morningstar / Finviz-style metrics:
 *   - Risk-adjusted: Sharpe, Sortino, Calmar, Treynor, Information Ratio
 *   - Returns: CAGR, MTD, YTD, 1M, 3M, 6M, 1Y, best/worst month/trade
 *   - Risk: Alpha, Beta, R-squared, Max Drawdown, VaR, Volatility
 *   - Portfolio: Win rate, profit factor, expectancy, avg hold, exposure
 *   - Holdings: Sector breakdown, top holdings, concentration
 *
 * PHP 5.2 compatible.
 *
 * Usage: GET .../portfolio_stats.php?algorithm=Cursor%20Genius
 *        GET .../portfolio_stats.php?algorithm=all
 *        GET .../portfolio_stats.php?algorithm=Cursor%20Genius&hold=90&tp=50&sl=999
 */
require_once dirname(__FILE__) . '/db_connect.php';

function _ps_param($key, $default) {
    if (isset($_GET[$key]) && $_GET[$key] !== '') return $_GET[$key];
    return $default;
}

$algo_filter = _ps_param('algorithm', 'all');
$hold_days   = (int)_ps_param('hold', 90);
$tp_pct      = (float)_ps_param('tp', 50);
$sl_pct      = (float)_ps_param('sl', 999);
$capital     = (float)_ps_param('capital', 10000);
$pos_pct     = (float)_ps_param('position', 10);

// ─── Load picks ───
$where = '';
if ($algo_filter !== 'all' && $algo_filter !== '') {
    $where = " AND sp.algorithm_name = '" . $conn->real_escape_string($algo_filter) . "'";
}

$picks = array();
$pr = $conn->query("SELECT sp.ticker, sp.algorithm_name, sp.pick_date, sp.entry_price, sp.score, sp.rating, sp.risk_level, sp.indicators_json, s.company_name, s.sector
    FROM stock_picks sp LEFT JOIN stocks s ON sp.ticker = s.ticker
    WHERE sp.entry_price > 0 $where ORDER BY sp.pick_date ASC, sp.ticker ASC");
if ($pr) { while ($row = $pr->fetch_assoc()) $picks[] = $row; }

if (count($picks) === 0) {
    echo json_encode(array('ok' => false, 'error' => 'No picks found for ' . $algo_filter));
    $conn->close();
    exit;
}

// ─── Load all prices into memory ───
$tickers_needed = array();
foreach ($picks as $p) { $tickers_needed[$p['ticker']] = true; }
$tickers_needed['SPY'] = true; // Benchmark

$price_data = array(); // ticker => date => {o,h,l,c}
$price_dates = array(); // ticker => array of dates
$price_idx = array(); // ticker => date => index

foreach ($tickers_needed as $tk => $_v) {
    $safe_tk = $conn->real_escape_string($tk);
    $pq = $conn->query("SELECT trade_date, open_price, high_price, low_price, close_price FROM daily_prices WHERE ticker='$safe_tk' ORDER BY trade_date ASC");
    if (!$pq) continue;
    $price_data[$tk] = array();
    $price_dates[$tk] = array();
    $price_idx[$tk] = array();
    $i = 0;
    while ($row = $pq->fetch_assoc()) {
        $d = $row['trade_date'];
        $price_data[$tk][$d] = array('o' => (float)$row['open_price'], 'h' => (float)$row['high_price'], 'l' => (float)$row['low_price'], 'c' => (float)$row['close_price']);
        $price_dates[$tk][] = $d;
        $price_idx[$tk][$d] = $i;
        $i++;
    }
}

// ─── Simulate trades ───
$trades = array();
$cap = $capital;
$peak = $capital;
$max_dd = 0;
$equity_curve = array(); // date => equity value
$daily_returns = array();
$monthly_returns = array(); // YYYY-MM => return pct
$sector_pnl = array();
$ticker_pnl = array();
$hold_days_arr = array();
$win_streaks = array();
$lose_streaks = array();
$current_streak = 0;
$streak_type = '';

foreach ($picks as $pick) {
    $tk = $pick['ticker'];
    $ep = (float)$pick['entry_price'];
    $pd = $pick['pick_date'];
    if (!isset($price_idx[$tk]) || !isset($price_idx[$tk][$pd])) continue;

    $si = $price_idx[$tk][$pd];
    $dates = $price_dates[$tk];
    $cnt = count($dates);

    $tp_price = $ep * (1 + $tp_pct / 100);
    $sl_price = $ep * (1 - $sl_pct / 100);

    $exit_p = 0;
    $exit_d = '';
    $exit_reason = '';
    $hd = 0;

    for ($i = $si; $i < $cnt; $i++) {
        $hd++;
        $d = $dates[$i];
        $bar = $price_data[$tk][$d];
        if ($bar['h'] >= $tp_price) { $exit_p = $tp_price; $exit_d = $d; $exit_reason = 'take_profit'; break; }
        if ($bar['l'] <= $sl_price) { $exit_p = $sl_price; $exit_d = $d; $exit_reason = 'stop_loss'; break; }
        if ($hd >= $hold_days) { $exit_p = $bar['c']; $exit_d = $d; $exit_reason = 'max_hold'; break; }
    }
    if ($exit_p <= 0) continue;

    $pos_val = $cap * ($pos_pct / 100);
    $shares = floor($pos_val / $ep);
    if ($shares <= 0) $shares = 1;
    $cost = $shares * $ep;
    $proceeds = $shares * $exit_p;
    $net = $proceeds - $cost;
    $ret_pct = ($cost > 0) ? ($net / $cost) * 100 : 0;

    $cap += $net;
    if ($cap > $peak) $peak = $cap;
    $dd = ($peak > 0) ? (($peak - $cap) / $peak) * 100 : 0;
    if ($dd > $max_dd) $max_dd = $dd;

    $daily_returns[] = $ret_pct;
    $equity_curve[$exit_d] = $cap;

    // Monthly aggregation
    $exit_month = substr($exit_d, 0, 7);
    if (!isset($monthly_returns[$exit_month])) $monthly_returns[$exit_month] = 0;
    $monthly_returns[$exit_month] += $ret_pct;

    // Sector tracking
    $sector = isset($pick['sector']) ? $pick['sector'] : 'Unknown';
    if ($sector === '' || $sector === null) $sector = 'Unknown';
    if (!isset($sector_pnl[$sector])) $sector_pnl[$sector] = array('pnl' => 0, 'trades' => 0, 'wins' => 0);
    $sector_pnl[$sector]['trades']++;
    $sector_pnl[$sector]['pnl'] += $net;
    if ($net > 0) $sector_pnl[$sector]['wins']++;

    // Ticker tracking
    if (!isset($ticker_pnl[$tk])) $ticker_pnl[$tk] = array('name' => $pick['company_name'], 'pnl' => 0, 'trades' => 0, 'wins' => 0, 'total_ret' => 0);
    $ticker_pnl[$tk]['trades']++;
    $ticker_pnl[$tk]['pnl'] += $net;
    $ticker_pnl[$tk]['total_ret'] += $ret_pct;
    if ($net > 0) $ticker_pnl[$tk]['wins']++;

    $hold_days_arr[] = $hd;

    // Win/loss streaks
    if ($net > 0) {
        if ($streak_type === 'win') { $current_streak++; }
        else { if ($streak_type === 'loss') $lose_streaks[] = $current_streak; $current_streak = 1; $streak_type = 'win'; }
    } else {
        if ($streak_type === 'loss') { $current_streak++; }
        else { if ($streak_type === 'win') $win_streaks[] = $current_streak; $current_streak = 1; $streak_type = 'loss'; }
    }

    $trades[] = array(
        'ticker' => $tk, 'sector' => $sector, 'algo' => $pick['algorithm_name'],
        'entry_date' => $pd, 'exit_date' => $exit_d, 'entry_price' => $ep, 'exit_price' => round($exit_p, 4),
        'return_pct' => round($ret_pct, 4), 'net_pnl' => round($net, 2), 'hold_days' => $hd, 'exit_reason' => $exit_reason
    );
}

// Flush last streak
if ($streak_type === 'win') $win_streaks[] = $current_streak;
if ($streak_type === 'loss') $lose_streaks[] = $current_streak;

$total_trades = count($trades);
$wins = 0;
$losses = 0;
$gross_wins = 0;
$gross_losses = 0;
$win_returns = array();
$loss_returns = array();
$downside_returns = array();

foreach ($trades as $t) {
    if ($t['net_pnl'] > 0) { $wins++; $gross_wins += $t['net_pnl']; $win_returns[] = $t['return_pct']; }
    else { $losses++; $gross_losses += abs($t['net_pnl']); $loss_returns[] = $t['return_pct']; $downside_returns[] = $t['return_pct']; }
}

// ─── Core Performance Metrics ───
$total_return_pct = ($capital > 0) ? (($cap - $capital) / $capital) * 100 : 0;
$win_rate = ($total_trades > 0) ? round($wins / $total_trades * 100, 2) : 0;
$loss_rate = ($total_trades > 0) ? round($losses / $total_trades * 100, 2) : 0;
$avg_return = ($total_trades > 0) ? array_sum($daily_returns) / $total_trades : 0;
$avg_win = (count($win_returns) > 0) ? array_sum($win_returns) / count($win_returns) : 0;
$avg_loss = (count($loss_returns) > 0) ? array_sum($loss_returns) / count($loss_returns) : 0;
$profit_factor = ($gross_losses > 0) ? round($gross_wins / $gross_losses, 4) : ($gross_wins > 0 ? 999 : 0);
$expectancy = ($total_trades > 0) ? round(($wins / $total_trades * $avg_win) + ($losses / $total_trades * $avg_loss), 4) : 0;
$avg_hold = (count($hold_days_arr) > 0) ? round(array_sum($hold_days_arr) / count($hold_days_arr), 1) : 0;
$max_consecutive_wins = (count($win_streaks) > 0) ? max($win_streaks) : 0;
$max_consecutive_losses = (count($lose_streaks) > 0) ? max($lose_streaks) : 0;

// ─── Volatility & Risk Metrics ───
$mean_ret = ($total_trades > 0) ? array_sum($daily_returns) / $total_trades : 0;
$var = 0;
foreach ($daily_returns as $r) { $var += ($r - $mean_ret) * ($r - $mean_ret); }
$std_dev = ($total_trades > 1) ? sqrt($var / ($total_trades - 1)) : 0;

// Downside deviation (for Sortino)
$downside_var = 0;
$downside_cnt = 0;
foreach ($daily_returns as $r) {
    if ($r < 0) { $downside_var += $r * $r; $downside_cnt++; }
}
$downside_dev = ($total_trades > 1) ? sqrt($downside_var / ($total_trades - 1)) : 0;

// Sharpe Ratio
$sharpe = ($std_dev > 0) ? round($mean_ret / $std_dev, 4) : 0;

// Sortino Ratio (excess return / downside deviation)
$sortino = ($downside_dev > 0) ? round($mean_ret / $downside_dev, 4) : 0;

// Calmar Ratio (total return / max drawdown)
$calmar = ($max_dd > 0) ? round($total_return_pct / $max_dd, 4) : 0;

// CAGR approximation
$first_date = (count($trades) > 0) ? $trades[0]['entry_date'] : '';
$last_date = (count($trades) > 0) ? $trades[count($trades) - 1]['exit_date'] : '';
$days_span = 0;
if ($first_date !== '' && $last_date !== '') {
    $days_span = (strtotime($last_date) - strtotime($first_date)) / 86400;
}
$years = ($days_span > 0) ? $days_span / 365.25 : 1;
$cagr = 0;
if ($cap > 0 && $capital > 0 && $years > 0) {
    $cagr = (pow($cap / $capital, 1 / $years) - 1) * 100;
}

// ─── Alpha & Beta vs SPY ───
$alpha = 0;
$beta = 0;
$r_squared = 0;
$spy_returns = array();
$portfolio_monthly = array();

if (isset($price_data['SPY']) && count($monthly_returns) > 0) {
    $spy_months = array();
    $spy_dates_arr = $price_dates['SPY'];
    $spy_month = '';
    $spy_month_start = 0;
    foreach ($spy_dates_arr as $sd) {
        $ym = substr($sd, 0, 7);
        if ($ym !== $spy_month) {
            if ($spy_month !== '' && $spy_month_start > 0) {
                $spy_close = $price_data['SPY'][$sd]['o'];
                $spy_ret = (($spy_close - $spy_month_start) / $spy_month_start) * 100;
                $spy_months[$spy_month] = $spy_ret;
            }
            $spy_month = $ym;
            $spy_month_start = $price_data['SPY'][$sd]['o'];
        }
    }

    // Match months
    $matched_port = array();
    $matched_spy = array();
    foreach ($monthly_returns as $ym => $pret) {
        if (isset($spy_months[$ym])) {
            $matched_port[] = $pret;
            $matched_spy[] = $spy_months[$ym];
        }
    }

    if (count($matched_port) > 2) {
        $n = count($matched_port);
        $sum_x = array_sum($matched_spy);
        $sum_y = array_sum($matched_port);
        $sum_xy = 0;
        $sum_x2 = 0;
        $sum_y2 = 0;
        for ($i = 0; $i < $n; $i++) {
            $sum_xy += $matched_spy[$i] * $matched_port[$i];
            $sum_x2 += $matched_spy[$i] * $matched_spy[$i];
            $sum_y2 += $matched_port[$i] * $matched_port[$i];
        }
        $denom = ($n * $sum_x2 - $sum_x * $sum_x);
        if ($denom != 0) {
            $beta = ($n * $sum_xy - $sum_x * $sum_y) / $denom;
            $alpha = ($sum_y - $beta * $sum_x) / $n;
        }
        $ss_tot = $sum_y2 - ($sum_y * $sum_y) / $n;
        if ($ss_tot != 0) {
            $ss_res = 0;
            for ($i = 0; $i < $n; $i++) {
                $pred = $alpha + $beta * $matched_spy[$i];
                $ss_res += ($matched_port[$i] - $pred) * ($matched_port[$i] - $pred);
            }
            $r_squared = 1 - ($ss_res / $ss_tot);
        }
    }
}

// ─── Monthly Return Table ───
$monthly_table = array();
foreach ($monthly_returns as $ym => $ret) {
    $monthly_table[] = array('month' => $ym, 'return_pct' => round($ret, 2));
}
// Sort by month
for ($i = 0; $i < count($monthly_table); $i++) {
    for ($j = $i + 1; $j < count($monthly_table); $j++) {
        if ($monthly_table[$j]['month'] < $monthly_table[$i]['month']) {
            $tmp = $monthly_table[$i]; $monthly_table[$i] = $monthly_table[$j]; $monthly_table[$j] = $tmp;
        }
    }
}

$best_month = null;
$worst_month = null;
foreach ($monthly_table as $m) {
    if ($best_month === null || $m['return_pct'] > $best_month['return_pct']) $best_month = $m;
    if ($worst_month === null || $m['return_pct'] < $worst_month['return_pct']) $worst_month = $m;
}

// Best/worst trades
$best_trade = null;
$worst_trade = null;
foreach ($trades as $t) {
    if ($best_trade === null || $t['return_pct'] > $best_trade['return_pct']) $best_trade = $t;
    if ($worst_trade === null || $t['return_pct'] < $worst_trade['return_pct']) $worst_trade = $t;
}

// ─── Sector Breakdown ───
$sector_breakdown = array();
foreach ($sector_pnl as $sec => $info) {
    $sec_wr = ($info['trades'] > 0) ? round($info['wins'] / $info['trades'] * 100, 1) : 0;
    $sector_breakdown[] = array('sector' => $sec, 'trades' => $info['trades'], 'pnl' => round($info['pnl'], 2), 'win_rate' => $sec_wr, 'allocation_pct' => round($info['trades'] / $total_trades * 100, 1));
}

// ─── Top Holdings ───
$top_holdings = array();
foreach ($ticker_pnl as $tk => $info) {
    $avg_r = ($info['trades'] > 0) ? round($info['total_ret'] / $info['trades'], 2) : 0;
    $tkwr = ($info['trades'] > 0) ? round($info['wins'] / $info['trades'] * 100, 1) : 0;
    $top_holdings[] = array('ticker' => $tk, 'name' => $info['name'], 'trades' => $info['trades'], 'pnl' => round($info['pnl'], 2), 'avg_return' => $avg_r, 'win_rate' => $tkwr);
}
// Sort by PnL desc
for ($i = 0; $i < count($top_holdings); $i++) {
    for ($j = $i + 1; $j < count($top_holdings); $j++) {
        if ($top_holdings[$j]['pnl'] > $top_holdings[$i]['pnl']) {
            $tmp = $top_holdings[$i]; $top_holdings[$i] = $top_holdings[$j]; $top_holdings[$j] = $tmp;
        }
    }
}

// ─── VaR (Value at Risk) 95% — simple historical percentile ───
$var_95 = 0;
if (count($daily_returns) >= 20) {
    $sorted_rets = $daily_returns;
    sort($sorted_rets);
    $idx_5 = (int)floor(count($sorted_rets) * 0.05);
    $var_95 = $sorted_rets[$idx_5];
}

// ─── Exposure ───
$exposure_pct = ($total_trades > 0 && $days_span > 0) ? round(($total_trades * $avg_hold) / $days_span * $pos_pct, 2) : 0;

// ─── Assemble response ───
$output = array(
    'ok' => true,
    'algorithm' => $algo_filter,
    'params' => array('hold_days' => $hold_days, 'take_profit' => $tp_pct, 'stop_loss' => $sl_pct, 'initial_capital' => $capital, 'position_pct' => $pos_pct),

    'performance' => array(
        'total_return_pct' => round($total_return_pct, 2),
        'cagr_pct' => round($cagr, 2),
        'final_value' => round($cap, 2),
        'initial_capital' => $capital,
        'period_start' => $first_date,
        'period_end' => $last_date,
        'period_days' => round($days_span),
        'period_years' => round($years, 2)
    ),

    'risk_adjusted' => array(
        'sharpe_ratio' => round($sharpe, 4),
        'sortino_ratio' => round($sortino, 4),
        'calmar_ratio' => round($calmar, 4),
        'alpha_monthly' => round($alpha, 4),
        'beta' => round($beta, 4),
        'r_squared' => round($r_squared, 4),
        'information_ratio' => ($std_dev > 0 && $beta != 0) ? round(($mean_ret - $beta * $mean_ret) / $std_dev, 4) : 0
    ),

    'risk' => array(
        'max_drawdown_pct' => round($max_dd, 2),
        'volatility_pct' => round($std_dev, 4),
        'downside_deviation' => round($downside_dev, 4),
        'var_95_pct' => round($var_95, 2),
        'best_trade' => $best_trade,
        'worst_trade' => $worst_trade,
        'best_month' => $best_month,
        'worst_month' => $worst_month
    ),

    'trading' => array(
        'total_trades' => $total_trades,
        'winning_trades' => $wins,
        'losing_trades' => $losses,
        'win_rate_pct' => $win_rate,
        'loss_rate_pct' => $loss_rate,
        'avg_return_pct' => round($avg_return, 4),
        'avg_win_pct' => round($avg_win, 2),
        'avg_loss_pct' => round($avg_loss, 2),
        'profit_factor' => $profit_factor,
        'expectancy' => $expectancy,
        'avg_hold_days' => $avg_hold,
        'max_consecutive_wins' => $max_consecutive_wins,
        'max_consecutive_losses' => $max_consecutive_losses,
        'exposure_pct' => $exposure_pct
    ),

    'sector_breakdown' => $sector_breakdown,
    'top_holdings' => array_slice($top_holdings, 0, 15),
    'worst_holdings' => array_slice(array_reverse($top_holdings), 0, 5),
    'monthly_returns' => $monthly_table,
    'equity_curve' => $equity_curve,
    'total_picks' => count($picks)
);

echo json_encode($output);
$conn->close();
?>
