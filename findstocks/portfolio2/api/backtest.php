<?php
/**
 * Enhanced Backtesting Engine for Portfolio Analysis v2
 * Runs simulated trades with position sizing, capital management, and full metrics.
 * PHP 5.2 compatible.
 *
 * Parameters (POST or GET):
 *   algorithms      — comma-separated algorithm names (empty = all)
 *   strategy        — daytrader|swing|conservative|aggressive|buy_hold|custom
 *   take_profit     — take profit % (e.g. 10)
 *   stop_loss       — stop loss % (e.g. 5)
 *   max_hold_days   — max holding period in trading days
 *   initial_capital — starting capital (default 10000)
 *   commission      — commission per trade in $ (default 10)
 *   slippage        — slippage % (default 0.5)
 *   position_size   — % of capital per position (default 10)
 *   max_positions   — max concurrent positions (default 10)
 *   save            — 1 to save results to DB
 *   portfolio_id    — use saved portfolio settings
 */
require_once dirname(__FILE__) . '/db_connect.php';

function _bt_param($key, $default) {
    if (isset($_POST[$key]) && $_POST[$key] !== '') return $_POST[$key];
    if (isset($_GET[$key]) && $_GET[$key] !== '') return $_GET[$key];
    return $default;
}

// Load from portfolio template
$portfolio_id = (int)_bt_param('portfolio_id', 0);
$params = array();

if ($portfolio_id > 0) {
    $res = $conn->query("SELECT * FROM portfolios WHERE id=$portfolio_id");
    if ($res && $row = $res->fetch_assoc()) {
        $params['algorithms']      = $row['algorithm_filter'];
        $params['strategy']        = $row['strategy_type'];
        $params['take_profit']     = (float)$row['take_profit_pct'];
        $params['stop_loss']       = (float)$row['stop_loss_pct'];
        $params['max_hold_days']   = (int)$row['max_hold_days'];
        $params['initial_capital'] = (float)$row['initial_capital'];
        $params['commission']      = (float)$row['commission_buy'];
        $params['slippage']        = (float)$row['slippage_pct'] * 100;
        $params['position_size']   = (float)$row['position_size_pct'];
        $params['max_positions']   = (int)$row['max_positions'];
    }
}

$algorithms      = _bt_param('algorithms',      isset($params['algorithms']) ? $params['algorithms'] : '');
$strategy        = _bt_param('strategy',         isset($params['strategy']) ? $params['strategy'] : 'custom');
$take_profit     = (float)_bt_param('take_profit',     isset($params['take_profit']) ? $params['take_profit'] : 10);
$stop_loss       = (float)_bt_param('stop_loss',       isset($params['stop_loss']) ? $params['stop_loss'] : 5);
$max_hold_days   = (int)_bt_param('max_hold_days',     isset($params['max_hold_days']) ? $params['max_hold_days'] : 7);
$initial_capital = (float)_bt_param('initial_capital', isset($params['initial_capital']) ? $params['initial_capital'] : 10000);
$commission      = (float)_bt_param('commission',      isset($params['commission']) ? $params['commission'] : 10);
$slippage_pct    = (float)_bt_param('slippage',        isset($params['slippage']) ? $params['slippage'] : 0.5);
$position_pct    = (float)_bt_param('position_size',   isset($params['position_size']) ? $params['position_size'] : 10);
$max_positions   = (int)_bt_param('max_positions',     isset($params['max_positions']) ? $params['max_positions'] : 10);
$save_results    = (int)_bt_param('save', 0);

// Strategy presets
if ($strategy === 'daytrader') {
    if ($max_hold_days > 2) $max_hold_days = 2;
}
if ($strategy === 'buy_hold') {
    $take_profit = 999;
    $stop_loss   = 999;
}

// ─── Fetch Picks ───
$where_algo = '';
if ($algorithms !== '') {
    $algo_list = explode(',', $algorithms);
    $escaped = array();
    foreach ($algo_list as $a) {
        $a = trim($a);
        if ($a !== '') {
            $escaped[] = "'" . $conn->real_escape_string($a) . "'";
        }
    }
    if (count($escaped) > 0) {
        $where_algo = " AND sp.algorithm_name IN (" . implode(',', $escaped) . ")";
    }
}

$sql = "SELECT sp.*, s.company_name
        FROM stock_picks sp
        LEFT JOIN stocks s ON sp.ticker = s.ticker
        WHERE sp.entry_price > 0 $where_algo
        ORDER BY sp.pick_date ASC, sp.ticker ASC";

$picks_res = $conn->query($sql);
if (!$picks_res || $picks_res->num_rows === 0) {
    echo json_encode(array(
        'ok' => false,
        'error' => 'No picks found. Import picks first via import_picks.php',
        'params' => array(
            'algorithms' => $algorithms,
            'strategy' => $strategy,
            'take_profit' => $take_profit,
            'stop_loss' => $stop_loss,
            'max_hold_days' => $max_hold_days
        )
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
$total_commission = 0;
$total_wins_pct  = 0;
$total_losses_pct = 0;
$best_trade      = -9999;
$worst_trade     = 9999;
$total_hold_days = 0;
$trades          = array();
$daily_returns   = array();
$equity_curve    = array();

// Track open positions for concurrent position limiting
$open_positions = 0;

while ($pick = $picks_res->fetch_assoc()) {
    $ticker     = $pick['ticker'];
    $entry_price = (float)$pick['entry_price'];
    $pick_date   = $pick['pick_date'];
    $algo_name   = $pick['algorithm_name'];
    $company     = isset($pick['company_name']) ? $pick['company_name'] : '';

    // Apply slippage
    $effective_entry = $entry_price * (1 + $slippage_pct / 100);

    // Position sizing
    $position_value = $capital * ($position_pct / 100);
    if ($position_value < $effective_entry + $commission) continue;
    $shares = (int)floor(($position_value - $commission) / $effective_entry);
    if ($shares <= 0) continue;

    // Fetch daily prices
    $safe_ticker = $conn->real_escape_string($ticker);
    $safe_date   = $conn->real_escape_string($pick_date);
    $price_sql = "SELECT trade_date, open_price, high_price, low_price, close_price, volume
                  FROM daily_prices
                  WHERE ticker='$safe_ticker' AND trade_date >= '$safe_date'
                  ORDER BY trade_date ASC
                  LIMIT " . ($max_hold_days + 5);
    $price_res = $conn->query($price_sql);

    if (!$price_res || $price_res->num_rows === 0) {
        $trade = array(
            'ticker' => $ticker, 'company' => $company, 'algorithm' => $algo_name,
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
        $total_losses_pct += abs($trade['return_pct']);
        $capital -= $commission * 2;
        if ($trade['return_pct'] < $worst_trade) $worst_trade = $trade['return_pct'];
        continue;
    }

    // Simulate trading days
    $day_count    = 0;
    $sold         = false;
    $exit_price   = 0;
    $exit_date    = '';
    $exit_reason  = '';
    $day_close    = 0;

    while ($day = $price_res->fetch_assoc()) {
        $day_count++;
        $day_high  = (float)$day['high_price'];
        $day_low   = (float)$day['low_price'];
        $day_close = (float)$day['close_price'];
        $day_date  = $day['trade_date'];

        $tp_price = $effective_entry * (1 + $take_profit / 100);
        $sl_price = $effective_entry * (1 - $stop_loss / 100);

        // Stop loss first (conservative)
        if ($day_low <= $sl_price && $stop_loss < 999) {
            $exit_price  = $sl_price;
            $exit_date   = $day_date;
            $exit_reason = 'stop_loss';
            $sold = true;
            break;
        }

        // Take profit
        if ($day_high >= $tp_price && $take_profit < 999) {
            $exit_price  = $tp_price;
            $exit_date   = $day_date;
            $exit_reason = 'take_profit';
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

    // Apply slippage to exit
    $effective_exit = $exit_price * (1 - $slippage_pct / 100);

    // Calculate P&L
    $gross_profit = ($effective_exit - $effective_entry) * $shares;
    $comm_total   = $commission * 2;
    $net_profit   = $gross_profit - $comm_total;
    $return_pct   = ($effective_entry * $shares > 0)
                    ? ($net_profit / ($effective_entry * $shares)) * 100
                    : 0;

    $trade = array(
        'ticker'         => $ticker,
        'company'        => $company,
        'algorithm'      => $algo_name,
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

    // Track drawdown
    if ($capital > $peak_capital) {
        $peak_capital = $capital;
    }
    $drawdown = ($peak_capital > 0) ? (($peak_capital - $capital) / $peak_capital) * 100 : 0;
    if ($drawdown > $max_drawdown) {
        $max_drawdown = $drawdown;
    }

    $daily_returns[] = $return_pct;
    $equity_curve[] = array('trade' => $total_trades, 'capital' => round($capital, 2), 'date' => $exit_date);
}

// ─── Aggregate Metrics ───
$final_value    = round($capital, 2);
$total_return   = ($initial_capital > 0) ? round(($capital - $initial_capital) / $initial_capital * 100, 4) : 0;
$win_rate       = ($total_trades > 0) ? round($winning_trades / $total_trades * 100, 2) : 0;
$avg_win_pct    = ($winning_trades > 0) ? round($total_wins_pct / $winning_trades, 4) : 0;
$avg_loss_pct   = ($losing_trades > 0) ? round($total_losses_pct / $losing_trades, 4) : 0;
$avg_hold       = ($total_trades > 0) ? round($total_hold_days / $total_trades, 2) : 0;
$commission_drag = ($initial_capital > 0) ? round($total_commission / $initial_capital * 100, 4) : 0;

// Annualized return estimate
$annualized = 0;
if (count($trades) >= 2) {
    $first_date = strtotime($trades[0]['entry_date']);
    $last_date = strtotime($trades[count($trades) - 1]['exit_date']);
    $days = ($last_date - $first_date) / 86400;
    if ($days > 30 && $final_value > 0 && $initial_capital > 0) {
        $years = $days / 365.25;
        if ($years > 0) {
            $annualized = round((pow($final_value / $initial_capital, 1 / $years) - 1) * 100, 4);
        }
    }
}

// Sharpe & Sortino
$sharpe = 0;
$sortino = 0;
if (count($daily_returns) > 1) {
    $mean = array_sum($daily_returns) / count($daily_returns);
    $variance = 0;
    $downside_variance = 0;
    $count_down = 0;
    foreach ($daily_returns as $r) {
        $variance += ($r - $mean) * ($r - $mean);
        if ($r < 0) {
            $downside_variance += $r * $r;
            $count_down++;
        }
    }
    $stddev = sqrt($variance / count($daily_returns));
    if ($stddev > 0) $sharpe = round($mean / $stddev, 4);
    if ($count_down > 0) {
        $downside_std = sqrt($downside_variance / $count_down);
        if ($downside_std > 0) $sortino = round($mean / $downside_std, 4);
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

// ─── ADVANCED METRICS (God-Mode Analytics) ───

// Calmar Ratio = Annualized Return / Max Drawdown
$calmar_ratio = 0;
if ($max_drawdown > 0 && $annualized != 0) {
    $calmar_ratio = round($annualized / $max_drawdown, 4);
}

// Recovery Factor = Total Return / Max Drawdown
$recovery_factor = 0;
if ($max_drawdown > 0) {
    $recovery_factor = round(abs($total_return) / $max_drawdown, 4);
    if ($total_return < 0) $recovery_factor = -$recovery_factor;
}

// Kelly Criterion = W - (1-W)/R where W=win rate, R=avg win/avg loss ratio
$kelly_pct = 0;
if ($avg_loss_pct > 0 && $winning_trades > 0) {
    $win_loss_ratio = $avg_win_pct / $avg_loss_pct;
    $kelly_pct = round(($win_rate_dec - ((1 - $win_rate_dec) / $win_loss_ratio)) * 100, 4);
    if ($kelly_pct < 0) $kelly_pct = 0;
}

// Tail Risk (Value at Risk 95th percentile - 5th percentile loss)
$var_95 = 0;
$cvar_95 = 0;
if (count($daily_returns) >= 10) {
    $sorted_returns = $daily_returns;
    sort($sorted_returns);
    $idx_5pct = (int)floor(count($sorted_returns) * 0.05);
    if ($idx_5pct < count($sorted_returns)) {
        $var_95 = round($sorted_returns[$idx_5pct], 4);
    }
    // Conditional VaR (Expected Shortfall) = mean of worst 5%
    if ($idx_5pct > 0) {
        $tail_sum = 0;
        for ($i = 0; $i < $idx_5pct; $i++) {
            $tail_sum += $sorted_returns[$i];
        }
        $cvar_95 = round($tail_sum / $idx_5pct, 4);
    }
}

// Consecutive Wins / Losses
$max_consec_wins = 0;
$max_consec_losses = 0;
$cur_wins = 0;
$cur_losses = 0;
foreach ($trades as $t) {
    if ($t['net_profit'] > 0) {
        $cur_wins++;
        $cur_losses = 0;
        if ($cur_wins > $max_consec_wins) $max_consec_wins = $cur_wins;
    } else {
        $cur_losses++;
        $cur_wins = 0;
        if ($cur_losses > $max_consec_losses) $max_consec_losses = $cur_losses;
    }
}

// Payoff Ratio (avg win / avg loss)
$payoff_ratio = 0;
if ($avg_loss_pct > 0) {
    $payoff_ratio = round($avg_win_pct / $avg_loss_pct, 4);
}

// Ulcer Index (RMS of drawdowns from peak)
$ulcer_index = 0;
if (count($equity_curve) > 1) {
    $eq_peak = $initial_capital;
    $dd_sq_sum = 0;
    $dd_count = 0;
    foreach ($equity_curve as $ec) {
        $cv = $ec['capital'];
        if ($cv > $eq_peak) $eq_peak = $cv;
        $eq_dd = ($eq_peak > 0) ? (($eq_peak - $cv) / $eq_peak * 100) : 0;
        $dd_sq_sum += $eq_dd * $eq_dd;
        $dd_count++;
    }
    if ($dd_count > 0) {
        $ulcer_index = round(sqrt($dd_sq_sum / $dd_count), 4);
    }
}

// Monthly returns distribution
$monthly_returns = array();
foreach ($trades as $t) {
    $m = substr($t['exit_date'], 0, 7); // YYYY-MM
    if (!isset($monthly_returns[$m])) $monthly_returns[$m] = 0;
    $monthly_returns[$m] += $t['return_pct'];
}

// Positive/negative months
$positive_months = 0;
$negative_months = 0;
$best_month = -9999;
$worst_month = 9999;
foreach ($monthly_returns as $mv) {
    if ($mv > 0) $positive_months++;
    else $negative_months++;
    if ($mv > $best_month) $best_month = $mv;
    if ($mv < $worst_month) $worst_month = $mv;
}
if ($best_month < -9000) $best_month = 0;
if ($worst_month > 9000) $worst_month = 0;

// Skewness and Kurtosis of returns
$skewness = 0;
$kurtosis = 0;
if (count($daily_returns) > 2) {
    $n = count($daily_returns);
    $mean_r = array_sum($daily_returns) / $n;
    $m2 = 0;
    $m3 = 0;
    $m4 = 0;
    foreach ($daily_returns as $r) {
        $diff = $r - $mean_r;
        $m2 += $diff * $diff;
        $m3 += $diff * $diff * $diff;
        $m4 += $diff * $diff * $diff * $diff;
    }
    $m2 = $m2 / $n;
    $m3 = $m3 / $n;
    $m4 = $m4 / $n;
    if ($m2 > 0) {
        $sd_r = sqrt($m2);
        $skewness = round($m3 / ($sd_r * $sd_r * $sd_r), 4);
        $kurtosis = round($m4 / ($m2 * $m2) - 3, 4); // excess kurtosis
    }
}

// Per-algorithm breakdown
$algo_stats = array();
foreach ($trades as $t) {
    $a = $t['algorithm'];
    if (!isset($algo_stats[$a])) {
        $algo_stats[$a] = array('trades' => 0, 'wins' => 0, 'losses' => 0, 'total_return' => 0, 'total_pnl' => 0);
    }
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
        'trades' => $as['trades'],
        'wins' => $as['wins'],
        'losses' => $as['losses'],
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
        'take_profit_pct'  => $take_profit,
        'stop_loss_pct'    => $stop_loss,
        'max_hold_days'    => $max_hold_days,
        'initial_capital'  => $initial_capital,
        'commission'       => $commission,
        'slippage_pct'     => $slippage_pct,
        'position_size_pct'=> $position_pct,
        'max_positions'    => $max_positions
    ),
    'summary' => array(
        'initial_capital'      => $initial_capital,
        'final_value'          => $final_value,
        'total_return_pct'     => $total_return,
        'annualized_return_pct'=> $annualized,
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
        'total_commissions'    => round($total_commission, 2),
        'commission_drag_pct'  => $commission_drag,
        'sharpe_ratio'         => $sharpe,
        'sortino_ratio'        => $sortino,
        'profit_factor'        => $profit_factor,
        'expectancy'           => $expectancy,
        'gross_wins'           => round($gross_wins, 2),
        'gross_losses'         => round($gross_losses, 2),
        // Advanced God-Mode Metrics
        'calmar_ratio'         => $calmar_ratio,
        'recovery_factor'      => $recovery_factor,
        'kelly_criterion_pct'  => $kelly_pct,
        'payoff_ratio'         => $payoff_ratio,
        'var_95'               => $var_95,
        'cvar_95'              => $cvar_95,
        'max_consecutive_wins' => $max_consec_wins,
        'max_consecutive_losses' => $max_consec_losses,
        'ulcer_index'          => $ulcer_index,
        'skewness'             => $skewness,
        'kurtosis'             => $kurtosis,
        'positive_months'      => $positive_months,
        'negative_months'      => $negative_months,
        'best_month_pct'       => round($best_month, 4),
        'worst_month_pct'      => round($worst_month, 4),
        'monthly_win_rate'     => (($positive_months + $negative_months) > 0) ? round($positive_months / ($positive_months + $negative_months) * 100, 2) : 0
    ),
    'monthly_returns' => $monthly_returns,
    'algorithm_breakdown' => $algo_breakdown,
    'exit_reasons' => $exit_reasons,
    'equity_curve' => $equity_curve,
    'trades' => $trades
);

// ─── Save Results ───
if ($save_results === 1) {
    $now = date('Y-m-d H:i:s');
    $run_name = $strategy . '_tp' . $take_profit . '_sl' . $stop_loss . '_' . $max_hold_days . 'd';
    $safe_name   = $conn->real_escape_string($run_name);
    $safe_algos  = $conn->real_escape_string($algorithms);
    $safe_strat  = $conn->real_escape_string($strategy);
    $params_json = $conn->real_escape_string(json_encode($response['params']));

    $start_d = '';
    $end_d = '';
    if (count($trades) > 0) {
        $start_d = $trades[0]['entry_date'];
        $end_d = $trades[count($trades) - 1]['exit_date'];
    }
    $safe_sd = $conn->real_escape_string($start_d);
    $safe_ed = $conn->real_escape_string($end_d);

    $sql = "INSERT INTO backtest_results
            (portfolio_id, run_name, algorithm_filter, strategy_type, start_date, end_date,
             initial_capital, final_value, total_return_pct, annualized_return_pct,
             total_trades, winning_trades, losing_trades, win_rate,
             avg_win_pct, avg_loss_pct, best_trade_pct, worst_trade_pct,
             max_drawdown_pct, total_commissions, sharpe_ratio, sortino_ratio,
             profit_factor, expectancy, avg_hold_days, commission_drag_pct,
             params_json, created_at)
            VALUES ($portfolio_id, '$safe_name', '$safe_algos', '$safe_strat',
                    '$safe_sd', '$safe_ed', $initial_capital, $final_value,
                    $total_return, $annualized, $total_trades, $winning_trades,
                    $losing_trades, $win_rate, $avg_win_pct, $avg_loss_pct,
                    " . (($total_trades > 0) ? round($best_trade, 4) : 0) . ",
                    " . (($total_trades > 0) ? round($worst_trade, 4) : 0) . ",
                    " . round($max_drawdown, 4) . ", " . round($total_commission, 2) . ",
                    $sharpe, $sortino, $profit_factor, $expectancy, $avg_hold,
                    $commission_drag, '$params_json', '$now')";

    if ($conn->query($sql)) {
        $bt_id = $conn->insert_id;
        $response['backtest_id'] = $bt_id;

        foreach ($trades as $t) {
            $st = $conn->real_escape_string($t['ticker']);
            $sa = $conn->real_escape_string($t['algorithm']);
            $se = $conn->real_escape_string($t['entry_date']);
            $sx = $conn->real_escape_string(isset($t['exit_date']) ? $t['exit_date'] : '');
            $sr = $conn->real_escape_string($t['exit_reason']);
            $conn->query("INSERT INTO backtest_trades
                (backtest_id, ticker, algorithm_name, entry_date, entry_price, exit_date, exit_price,
                 shares, gross_profit, commission_paid, net_profit, return_pct, exit_reason, hold_days)
                VALUES ($bt_id, '$st', '$sa', '$se', " . $t['entry_price'] . ", '$sx', " . $t['exit_price'] . ",
                 " . $t['shares'] . ", " . $t['gross_profit'] . ", " . $t['commission_paid'] . ",
                 " . $t['net_profit'] . ", " . $t['return_pct'] . ", '$sr', " . $t['hold_days'] . ")");
        }
    }

    $ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
    $detail = $conn->real_escape_string('Backtest: ' . $run_name . ' — ' . $total_trades . ' trades, return ' . $total_return . '%');
    $conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('backtest', '$detail', '$ip', '$now')");
}

echo json_encode($response);
$conn->close();
?>
