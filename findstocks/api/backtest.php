<?php
/**
 * Backtesting Engine for Stock Portfolio Analysis
 * Runs simulated trades using historical price data and configurable exit rules.
 * PHP 5.2 compatible.
 *
 * Usage: POST or GET with parameters:
 *   algorithms     — comma-separated algorithm names (empty = all)
 *   strategy       — daytrader|swing|conservative|aggressive|buy_hold|custom
 *   take_profit    — take profit % (e.g. 10)
 *   stop_loss      — stop loss % (e.g. 5)
 *   max_hold_days  — max holding period in trading days (e.g. 7)
 *   initial_capital— starting capital (default 10000)
 *   commission     — commission per trade in $ (default 10, ignored when fee_model=questrade)
 *   slippage       — slippage % (default 0.1)
 *   position_size  — % of capital per position (default 10)
 *   fee_model      — questrade|flat_10|zero (default questrade)
 *   vol_filter     — off|skip_high|skip_elevated|calm_only|custom (default off)
 *   max_vix        — custom VIX threshold (used when vol_filter=custom)
 *   save           — 1 to save results to DB
 *   portfolio_id   — use a saved portfolio's settings
 */
require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/questrade_fees.php';
require_once dirname(__FILE__) . '/volatility_filter.php';

// ─── Parse Parameters ───
function _bt_param($key, $default) {
    if (isset($_POST[$key]) && $_POST[$key] !== '') return $_POST[$key];
    if (isset($_GET[$key]) && $_GET[$key] !== '') return $_GET[$key];
    return $default;
}

// Load from portfolio template if specified
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
        $params['position_size']   = 10;
    }
}

// Override with request parameters
$algorithms      = _bt_param('algorithms',      isset($params['algorithms']) ? $params['algorithms'] : '');
$strategy        = _bt_param('strategy',         isset($params['strategy']) ? $params['strategy'] : 'custom');
$take_profit     = (float)_bt_param('take_profit',     isset($params['take_profit']) ? $params['take_profit'] : 10);
$stop_loss       = (float)_bt_param('stop_loss',       isset($params['stop_loss']) ? $params['stop_loss'] : 5);
$max_hold_days   = (int)_bt_param('max_hold_days',     isset($params['max_hold_days']) ? $params['max_hold_days'] : 7);
$initial_capital = (float)_bt_param('initial_capital', isset($params['initial_capital']) ? $params['initial_capital'] : 10000);
$commission      = (float)_bt_param('commission',      isset($params['commission']) ? $params['commission'] : 10);
// Slippage: 0.1% per side for stocks (entry: worse fill, exit: worse fill). Default 0.1.
$slippage_pct    = (float)_bt_param('slippage',        isset($params['slippage']) ? $params['slippage'] : 0.1);
$position_pct    = (float)_bt_param('position_size',   isset($params['position_size']) ? $params['position_size'] : 10);
$fee_model       = _bt_param('fee_model', 'questrade');
$vol_filter      = _bt_param('vol_filter', 'off');
$max_vix         = (float)_bt_param('max_vix', 25);
$save_results    = (int)_bt_param('save', 0);
$embargo_days    = (int)_bt_param('embargo_days', 2);  // Purged embargo: skip N days after pick to prevent look-ahead bias

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
        'error' => 'No picks found for the selected algorithms. Import picks first.',
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

// ─── Load VIX data for volatility filter ───
$vix_data = array();
$vol_skipped = 0;
$vol_skipped_tickers = array();
if ($vol_filter !== 'off') {
    $vix_data = vol_load_vix_data($conn);
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
$trades          = array();
$daily_returns   = array();

while ($pick = $picks_res->fetch_assoc()) {
    $ticker     = $pick['ticker'];
    $entry_price = (float)$pick['entry_price'];
    $pick_date   = $pick['pick_date'];

    // ─── Volatility filter: skip trade if market is too volatile ───
    if ($vol_filter !== 'off' && count($vix_data) > 0) {
        $vol_check = vol_should_skip($vix_data, $pick_date, $vol_filter, $max_vix);
        if ($vol_check['skip']) {
            $vol_skipped++;
            $vol_skipped_tickers[] = array(
                'ticker' => $ticker, 'date' => $pick_date,
                'vix' => $vol_check['vix'], 'reason' => $vol_check['reason']
            );
            continue; // Skip this trade entirely
        }
    }
    $algo_name   = $pick['algorithm_name'];
    $company     = isset($pick['company_name']) ? $pick['company_name'] : '';

    // Apply slippage to entry price
    $effective_entry = $entry_price * (1 + $slippage_pct / 100);

    // Calculate position size
    $position_value = $capital * ($position_pct / 100);
    if ($position_value < $effective_entry + $commission) continue; // Can't afford
    $shares = (int)floor(($position_value - $commission) / $effective_entry);
    if ($shares <= 0) continue;

    // Fetch daily prices after pick date
    $safe_ticker = $conn->real_escape_string($ticker);
    $safe_date   = $conn->real_escape_string($pick_date);
    $price_sql = "SELECT trade_date, open_price, high_price, low_price, close_price, volume
                  FROM daily_prices
                  WHERE ticker='$safe_ticker' AND trade_date >= '$safe_date'
                  ORDER BY trade_date ASC
                  LIMIT " . ($max_hold_days + 5);
    $price_res = $conn->query($price_sql);

    if (!$price_res || $price_res->num_rows === 0) {
        // No price data available — simulate with entry price (hold scenario)
        $npd_buy_val  = $effective_entry * $shares;
        $npd_buy_fees = questrade_calc_fees($ticker, $npd_buy_val, $shares, false, $fee_model);
        $npd_sell_fees = questrade_calc_fees($ticker, $npd_buy_val, $shares, true, $fee_model);
        if ($fee_model === 'flat_10') { $npd_buy_fees['total_fee'] = $commission; $npd_sell_fees['total_fee'] = $commission; }
        $npd_comm = round($npd_buy_fees['total_fee'] + $npd_sell_fees['total_fee'], 2);
        $trade = array(
            'ticker'         => $ticker,
            'company'        => $company,
            'algorithm'      => $algo_name,
            'entry_date'     => $pick_date,
            'entry_price'    => round($effective_entry, 4),
            'exit_date'      => $pick_date,
            'exit_price'     => round($entry_price, 4),
            'shares'         => $shares,
            'gross_profit'   => 0,
            'commission_paid'=> $npd_comm,
            'net_profit'     => -$npd_comm,
            'return_pct'     => round(-$npd_comm / ($effective_entry * $shares) * 100, 4),
            'exit_reason'    => 'no_price_data',
            'hold_days'      => 0,
            'has_cdr'        => $npd_buy_fees['is_cdr'],
            'forex_fee'      => round($npd_buy_fees['forex_fee'] + $npd_sell_fees['forex_fee'], 2),
            'ecn_fee'        => round($npd_buy_fees['ecn_fee'] + $npd_sell_fees['ecn_fee'], 2),
            'sec_fee'        => round($npd_sell_fees['sec_fee'], 2),
            'fee_breakdown'  => $npd_buy_fees['fee_breakdown'],
            'vix_at_entry'   => ($vol_filter !== 'off' && count($vix_data) > 0) ? vol_get_vix($vix_data, $pick_date) : null,
            'vol_regime'     => ($vol_filter !== 'off' && count($vix_data) > 0) ? vol_get_regime($vix_data, $pick_date) : null
        );
        $trades[] = $trade;
        $total_trades++;
        $losing_trades++;
        $total_commission += $npd_comm;
        $total_losses_pct += abs($trade['return_pct']);
        $capital -= $npd_comm;
        continue;
    }

    // ─── Simulate trading days ───
    $day_count    = 0;
    $sold         = false;
    $exit_price   = 0;
    $exit_date    = '';
    $exit_reason  = '';
    $first_day    = true;
    $embargo_skipped = 0;  // Purged embargo counter

    while ($day = $price_res->fetch_assoc()) {
        if ($first_day) {
            // On pick day, we enter at entry_price (already known)
            // Check same-day exits for daytrader
            $first_day = false;
        }

        $day_count++;

        // Purged embargo: skip the first N trading days after pick to prevent
        // look-ahead bias (signal may use data from these days). Default 2 days.
        if ($embargo_days > 0 && $day_count <= $embargo_days) {
            $embargo_skipped++;
            continue;
        }
        $day_open  = (float)$day['open_price'];
        $day_high  = (float)$day['high_price'];
        $day_low   = (float)$day['low_price'];
        $day_close = (float)$day['close_price'];
        $day_date  = $day['trade_date'];

        // Calculate thresholds
        $tp_price = $effective_entry * (1 + $take_profit / 100);
        $sl_price = $effective_entry * (1 - $stop_loss / 100);

        // Gap-aware stop loss: if day opens below SL, exit at open price (realistic gap fill)
        if ($day_open > 0 && $day_open <= $sl_price && $stop_loss < 999 && $day_count > 1) {
            $exit_price  = $day_open;  // Gap down — fill at open, not SL
            $exit_date   = $day_date;
            $exit_reason = 'stop_loss';
            $sold = true;
            break;
        }

        // Check stop loss first (conservative assumption: SL triggers before TP on same day)
        if ($day_low <= $sl_price && $stop_loss < 999) {
            $exit_price  = $sl_price;
            $exit_date   = $day_date;
            $exit_reason = 'stop_loss';
            $sold = true;
            break;
        }

        // Gap-aware take profit: if day opens above TP, fill at open (realistic gap fill)
        if ($day_open > 0 && $day_open >= $tp_price && $take_profit < 999 && $day_count > 1) {
            $exit_price  = $day_open;  // Gap up — fill at open, not TP
            $exit_date   = $day_date;
            $exit_reason = 'take_profit';
            $sold = true;
            break;
        }

        // Check take profit
        if ($day_high >= $tp_price && $take_profit < 999) {
            $exit_price  = $tp_price;
            $exit_date   = $day_date;
            $exit_reason = 'take_profit';
            $sold = true;
            break;
        }

        // Check max hold days
        if ($day_count >= $max_hold_days) {
            $exit_price  = $day_close;
            $exit_date   = $day_date;
            $exit_reason = 'max_hold';
            $sold = true;
            break;
        }
    }

    // If not sold (ran out of price data)
    if (!$sold) {
        // Use last available close
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

    // Calculate fees using Questrade model (or legacy flat fee)
    $buy_value = $effective_entry * $shares;
    $sell_value = $effective_exit * $shares;
    $buy_fees  = questrade_calc_fees($ticker, $buy_value, $shares, false, $fee_model);
    $sell_fees = questrade_calc_fees($ticker, $sell_value, $shares, true, $fee_model);

    // For legacy flat_10 mode, use the $commission param
    if ($fee_model === 'flat_10') {
        $buy_fees['total_fee'] = $commission;
        $sell_fees['total_fee'] = $commission;
    }

    $comm_total = round($buy_fees['total_fee'] + $sell_fees['total_fee'], 2);

    // Calculate profit/loss
    $gross_profit = ($effective_exit - $effective_entry) * $shares;
    $net_profit   = $gross_profit - $comm_total;
    $position_value = $effective_entry * $shares;
    $return_pct   = ($position_value > 0)
                    ? ($net_profit / $position_value) * 100
                    : 0;

    // Hard cap: no single trade can lose more than 100% of its allocated capital
    // (prevents impossible -145% losses from calculation errors or leverage bugs)
    if ($return_pct < -100) $return_pct = -100;
    if ($net_profit < -$position_value) $net_profit = -$position_value;

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
        'hold_days'      => $day_count,
        'has_cdr'        => $buy_fees['is_cdr'],
        'forex_fee'      => round($buy_fees['forex_fee'] + $sell_fees['forex_fee'], 2),
        'ecn_fee'        => round($buy_fees['ecn_fee'] + $sell_fees['ecn_fee'], 2),
        'sec_fee'        => round($sell_fees['sec_fee'], 2),
        'fee_breakdown'  => $buy_fees['fee_breakdown'],
        'vix_at_entry'   => ($vol_filter !== 'off' && count($vix_data) > 0) ? vol_get_vix($vix_data, $pick_date) : null,
        'vol_regime'     => ($vol_filter !== 'off' && count($vix_data) > 0) ? vol_get_regime($vix_data, $pick_date) : null
    );

    $trades[] = $trade;
    $total_trades++;
    $total_commission += $comm_total;
    $capital += $net_profit;

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
}

// ─── Calculate Aggregate Metrics ───
$final_value    = round($capital, 2);
$total_return   = ($initial_capital > 0) ? round(($capital - $initial_capital) / $initial_capital * 100, 4) : 0;
$win_rate       = ($total_trades > 0) ? round($winning_trades / $total_trades * 100, 2) : 0;
$avg_win_pct    = ($winning_trades > 0) ? round($total_wins_pct / $winning_trades, 4) : 0;
$avg_loss_pct   = ($losing_trades > 0) ? round($total_losses_pct / $losing_trades, 4) : 0;

// Sharpe ratio (simplified: mean / stddev of returns)
$sharpe = 0;
$sortino = 0;
$profit_factor = 0;
$expectancy = 0;

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
    if ($stddev > 0) {
        $sharpe = round($mean / $stddev, 4);
    }
    if ($count_down > 0) {
        $downside_std = sqrt($downside_variance / $count_down);
        if ($downside_std > 0) {
            $sortino = round($mean / $downside_std, 4);
        }
    }
}

// Profit factor = gross wins / gross losses
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

// Expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
$loss_rate = ($total_trades > 0) ? $losing_trades / $total_trades : 0;
$win_rate_dec = ($total_trades > 0) ? $winning_trades / $total_trades : 0;
$expectancy = round(($win_rate_dec * $avg_win_pct) - ($loss_rate * $avg_loss_pct), 4);

// ─── Fee breakdown totals ───
$total_forex = 0; $total_ecn = 0; $total_sec = 0; $cdr_trades = 0; $us_trades = 0;
foreach ($trades as $t) {
    if (isset($t['forex_fee'])) $total_forex += $t['forex_fee'];
    if (isset($t['ecn_fee']))   $total_ecn += $t['ecn_fee'];
    if (isset($t['sec_fee']))   $total_sec += $t['sec_fee'];
    if (isset($t['has_cdr']) && $t['has_cdr']) $cdr_trades++;
    elseif (isset($t['forex_fee']) && $t['forex_fee'] > 0) $us_trades++;
}

// ─── Build Response ───
$response = array(
    'ok' => true,
    'params' => array(
        'algorithms'      => $algorithms,
        'strategy'        => $strategy,
        'take_profit_pct' => $take_profit,
        'stop_loss_pct'   => $stop_loss,
        'max_hold_days'   => $max_hold_days,
        'initial_capital'  => $initial_capital,
        'commission'      => $commission,
        'slippage_pct'    => $slippage_pct,
        'position_size_pct'=> $position_pct,
        'fee_model'       => $fee_model,
        'fee_model_label' => questrade_fee_label($fee_model),
        'vol_filter'      => $vol_filter,
        'vol_filter_label'=> vol_filter_label($vol_filter, $max_vix),
        'max_vix'         => $max_vix,
        'embargo_days'    => $embargo_days
    ),
    'summary' => array(
        'initial_capital'  => $initial_capital,
        'final_value'      => $final_value,
        'total_return_pct' => $total_return,
        'total_trades'     => $total_trades,
        'winning_trades'   => $winning_trades,
        'losing_trades'    => $losing_trades,
        'win_rate'         => $win_rate,
        'avg_win_pct'      => $avg_win_pct,
        'avg_loss_pct'     => $avg_loss_pct,
        'max_drawdown_pct' => round($max_drawdown, 4),
        'total_commissions'=> round($total_commission, 2),
        'sharpe_ratio'     => $sharpe,
        'sortino_ratio'    => $sortino,
        'profit_factor'    => $profit_factor,
        'expectancy'       => $expectancy,
        'gross_wins'       => round($gross_wins, 2),
        'gross_losses'     => round($gross_losses, 2),
        'total_forex_fees' => round($total_forex, 2),
        'total_ecn_fees'   => round($total_ecn, 2),
        'total_sec_fees'   => round($total_sec, 2),
        'cdr_trades'       => $cdr_trades,
        'us_forex_trades'  => $us_trades,
        'vol_skipped'      => $vol_skipped,
        'vol_skipped_tickers' => array_slice($vol_skipped_tickers, 0, 20)
    ),
    'trades' => $trades
);

// ─── Save Results if requested ───
if ($save_results === 1) {
    $now = date('Y-m-d H:i:s');
    $run_name = $strategy . '_tp' . $take_profit . '_sl' . $stop_loss . '_' . $max_hold_days . 'd';
    $safe_name   = $conn->real_escape_string($run_name);
    $safe_algos  = $conn->real_escape_string($algorithms);
    $safe_strat  = $conn->real_escape_string($strategy);
    $params_json = $conn->real_escape_string(json_encode($response['params']));

    // Find date range from trades
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
             initial_capital, final_value, total_return_pct, total_trades, winning_trades,
             losing_trades, win_rate, avg_win_pct, avg_loss_pct, max_drawdown_pct,
             total_commissions, sharpe_ratio, sortino_ratio, profit_factor, expectancy,
             params_json, created_at)
            VALUES ($portfolio_id, '$safe_name', '$safe_algos', '$safe_strat',
                    '$safe_sd', '$safe_ed', $initial_capital, $final_value,
                    $total_return, $total_trades, $winning_trades, $losing_trades,
                    $win_rate, $avg_win_pct, $avg_loss_pct, " . round($max_drawdown, 4) . ",
                    " . round($total_commission, 2) . ", $sharpe, $sortino, $profit_factor,
                    $expectancy, '$params_json', '$now')";

    if ($conn->query($sql)) {
        $bt_id = $conn->insert_id;
        $response['backtest_id'] = $bt_id;

        // Save individual trades
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

    // Audit log
    $ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
    $detail = $conn->real_escape_string('Backtest: ' . $run_name . ' — ' . $total_trades . ' trades, return ' . $total_return . '%');
    $conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('backtest', '$detail', '$ip', '$now')");
}

echo json_encode($response);
$conn->close();
?>
