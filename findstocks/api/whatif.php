<?php
/**
 * What-If Analysis Engine
 * Runs multiple backtest scenarios and returns comparative results.
 * Supports natural-language-style queries mapped to parameters.
 * PHP 5.2 compatible.
 *
 * Usage: POST or GET with parameters:
 *   scenario      — preset scenario name (see list below)
 *   query         — natural language query text (for logging)
 *   algorithms    — comma-separated algorithm names (empty = all)
 *   take_profit   — take profit % (e.g. 10)
 *   stop_loss     — stop loss % (e.g. 5)
 *   max_hold_days — max holding period in trading days
 *   initial_capital — starting capital (default 10000)
 *   commission    — commission per trade in $ (default 10)
 *   slippage      — slippage % (default 0.5)
 *   compare       — 1 to run multiple scenarios for comparison
 */
require_once dirname(__FILE__) . '/db_connect.php';

function _wi_param($key, $default) {
    if (isset($_POST[$key]) && $_POST[$key] !== '') return $_POST[$key];
    if (isset($_GET[$key]) && $_GET[$key] !== '') return $_GET[$key];
    return $default;
}

$scenario       = _wi_param('scenario', '');
$query_text     = _wi_param('query', '');
$algorithms     = _wi_param('algorithms', '');
$take_profit    = (float)_wi_param('take_profit', 10);
$stop_loss      = (float)_wi_param('stop_loss', 5);
$max_hold_days  = (int)_wi_param('max_hold_days', 7);
$initial_capital= (float)_wi_param('initial_capital', 10000);
$commission     = (float)_wi_param('commission', 10);
$slippage       = (float)_wi_param('slippage', 0.5);
$compare_mode   = (int)_wi_param('compare', 0);

// ─── Preset Scenarios ───
$scenarios = array(
    'daytrader_eod' => array(
        'name'        => 'Day Trader (EOD Exit)',
        'description' => 'Buy at open, sell at close same day. Max 1-day hold.',
        'take_profit' => 5,
        'stop_loss'   => 3,
        'max_hold'    => 1
    ),
    'daytrader_2day' => array(
        'name'        => 'Day Trader (2-Day Max)',
        'description' => 'Buy in morning, sell within 2 days. 5% SL, 10% TP.',
        'take_profit' => 10,
        'stop_loss'   => 5,
        'max_hold'    => 2
    ),
    'weekly_10' => array(
        'name'        => 'Weekly Hold (10% Target)',
        'description' => 'Hold up to 7 days, sell at 10% profit or 5% loss.',
        'take_profit' => 10,
        'stop_loss'   => 5,
        'max_hold'    => 7
    ),
    'weekly_20' => array(
        'name'        => 'Weekly Hold (20% Target)',
        'description' => 'Hold up to 7 days, sell at 20% profit or 8% loss.',
        'take_profit' => 20,
        'stop_loss'   => 8,
        'max_hold'    => 7
    ),
    'swing_conservative' => array(
        'name'        => 'Conservative Swing',
        'description' => 'Hold 2-4 weeks, tight stops. 10% TP, 5% SL.',
        'take_profit' => 10,
        'stop_loss'   => 5,
        'max_hold'    => 20
    ),
    'swing_aggressive' => array(
        'name'        => 'Aggressive Swing',
        'description' => 'Hold 2-4 weeks, wide stops. 30% TP, 15% SL.',
        'take_profit' => 30,
        'stop_loss'   => 15,
        'max_hold'    => 20
    ),
    'buy_hold_3m' => array(
        'name'        => 'Buy & Hold (3 Months)',
        'description' => 'Buy and hold for 60 trading days (~3 months).',
        'take_profit' => 999,
        'stop_loss'   => 999,
        'max_hold'    => 60
    ),
    'buy_hold_6m' => array(
        'name'        => 'Buy & Hold (6 Months)',
        'description' => 'Buy and hold for 126 trading days (~6 months).',
        'take_profit' => 999,
        'stop_loss'   => 999,
        'max_hold'    => 126
    ),
    'tight_scalp' => array(
        'name'        => 'Tight Scalp',
        'description' => 'Quick 3% profit target, 2% stop loss, 1 day max.',
        'take_profit' => 3,
        'stop_loss'   => 2,
        'max_hold'    => 1
    ),
    'momentum_ride' => array(
        'name'        => 'Momentum Ride',
        'description' => 'Let winners run. 50% TP, 10% trailing SL, 30 days.',
        'take_profit' => 50,
        'stop_loss'   => 10,
        'max_hold'    => 30
    ),
    'bluechip_30d' => array(
        'name'        => 'Blue Chip 30-Day Hold',
        'description' => 'Buy & hold large-cap growers for 30 days. No TP/SL.',
        'take_profit' => 999,
        'stop_loss'   => 999,
        'max_hold'    => 30
    ),
    'bluechip_90d' => array(
        'name'        => 'Blue Chip 90-Day Hold',
        'description' => 'Buy & hold large-cap growers for 90 days. No TP/SL.',
        'take_profit' => 999,
        'stop_loss'   => 999,
        'max_hold'    => 90
    ),
    'bluechip_180d' => array(
        'name'        => 'Blue Chip 6-Month Hold',
        'description' => 'Buy & hold large-cap growers for 180 days. No TP/SL.',
        'take_profit' => 999,
        'stop_loss'   => 999,
        'max_hold'    => 180
    ),
    'cursor_genius_90d' => array(
        'name'        => 'Cursor Genius 90-Day Hold',
        'description' => 'Data-driven dip-buying on top performers. 90-day hold, no TP/SL.',
        'take_profit' => 999,
        'stop_loss'   => 999,
        'max_hold'    => 90
    ),
    'cursor_genius_50tp' => array(
        'name'        => 'Cursor Genius 50% TP',
        'description' => 'Dip-buying winners with 50% take-profit cap over 90 days.',
        'take_profit' => 50,
        'stop_loss'   => 999,
        'max_hold'    => 90
    ),
    'cursor_genius_20tp' => array(
        'name'        => 'Cursor Genius 20% TP',
        'description' => 'Dip-buying winners with 20% take-profit. Best risk-adjusted Sharpe.',
        'take_profit' => 20,
        'stop_loss'   => 999,
        'max_hold'    => 90
    ),
    'etf_masters_90d' => array(
        'name'        => 'ETF Masters 90-Day Hold',
        'description' => 'Diversified ETF portfolio across 5 tiers. 90-day hold, no TP/SL.',
        'take_profit' => 999,
        'stop_loss'   => 999,
        'max_hold'    => 90
    ),
    'sector_rotation_90d' => array(
        'name'        => 'Sector Rotation 90-Day',
        'description' => 'Equal-weight all 11 GICS sectors. Monthly rebalance, 90-day hold.',
        'take_profit' => 999,
        'stop_loss'   => 999,
        'max_hold'    => 90
    ),
    'sector_momentum_30d' => array(
        'name'        => 'Sector Momentum 30-Day',
        'description' => 'Top 4 momentum sectors each month. 30-day hold for rotation.',
        'take_profit' => 999,
        'stop_loss'   => 999,
        'max_hold'    => 30
    )
);

// ─── Internal backtest runner (calls backtest.php logic inline) ───
function run_backtest_inline($conn, $algo_filter, $tp, $sl, $mhd, $cap, $comm, $slip, $pos_pct) {
    // Build pick query
    $where_algo = '';
    if ($algo_filter !== '') {
        $algo_list = explode(',', $algo_filter);
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
        return array(
            'total_trades' => 0,
            'winning_trades' => 0,
            'losing_trades' => 0,
            'win_rate' => 0,
            'total_return_pct' => 0,
            'final_value' => $cap,
            'max_drawdown_pct' => 0,
            'total_commissions' => 0,
            'sharpe_ratio' => 0,
            'profit_factor' => 0,
            'expectancy' => 0,
            'trades' => array()
        );
    }

    $capital = $cap;
    $peak = $cap;
    $max_dd = 0;
    $total_trades = 0;
    $wins = 0;
    $losses = 0;
    $total_comm = 0;
    $total_wins_pct = 0;
    $total_losses_pct = 0;
    $gross_wins = 0;
    $gross_losses = 0;
    $trades = array();
    $returns = array();

    while ($pick = $picks_res->fetch_assoc()) {
        $ticker = $pick['ticker'];
        $entry = (float)$pick['entry_price'];
        $pick_date = $pick['pick_date'];
        $algo = $pick['algorithm_name'];
        $company = isset($pick['company_name']) ? $pick['company_name'] : '';

        $eff_entry = $entry * (1 + $slip / 100);
        $pos_val = $capital * ($pos_pct / 100);
        if ($pos_val < $eff_entry + $comm) continue;
        $shares = (int)floor(($pos_val - $comm) / $eff_entry);
        if ($shares <= 0) continue;

        $safe_t = $conn->real_escape_string($ticker);
        $safe_d = $conn->real_escape_string($pick_date);
        $price_sql = "SELECT trade_date, high_price, low_price, close_price
                      FROM daily_prices
                      WHERE ticker='$safe_t' AND trade_date >= '$safe_d'
                      ORDER BY trade_date ASC LIMIT " . ($mhd + 5);
        $price_res = $conn->query($price_sql);

        $day_count = 0;
        $sold = false;
        $exit_p = $entry;
        $exit_d = $pick_date;
        $exit_r = 'end_of_data';
        $day_close = 0;

        if ($price_res && $price_res->num_rows > 0) {
            while ($day = $price_res->fetch_assoc()) {
                $day_count++;
                $dh = (float)$day['high_price'];
                $dl = (float)$day['low_price'];
                $day_close = (float)$day['close_price'];
                $dd = $day['trade_date'];

                $tp_p = $eff_entry * (1 + $tp / 100);
                $sl_p = $eff_entry * (1 - $sl / 100);

                if ($dl <= $sl_p && $sl < 999) {
                    $exit_p = $sl_p; $exit_d = $dd; $exit_r = 'stop_loss'; $sold = true; break;
                }
                if ($dh >= $tp_p && $tp < 999) {
                    $exit_p = $tp_p; $exit_d = $dd; $exit_r = 'take_profit'; $sold = true; break;
                }
                if ($day_count >= $mhd) {
                    $exit_p = $day_close; $exit_d = $dd; $exit_r = 'max_hold'; $sold = true; break;
                }
            }
            if (!$sold) {
                if ($day_count > 0 && $day_close > 0) {
                    $exit_p = $day_close;
                }
                $exit_r = 'end_of_data';
            }
        }

        $eff_exit = $exit_p * (1 - $slip / 100);
        $gross_pnl = ($eff_exit - $eff_entry) * $shares;
        $comm_tot = $comm * 2;
        $net_pnl = $gross_pnl - $comm_tot;
        $ret_pct = ($eff_entry * $shares > 0) ? ($net_pnl / ($eff_entry * $shares)) * 100 : 0;

        $trades[] = array(
            'ticker' => $ticker, 'company' => $company, 'algorithm' => $algo,
            'entry_date' => $pick_date, 'entry_price' => round($eff_entry, 4),
            'exit_date' => $exit_d, 'exit_price' => round($eff_exit, 4),
            'shares' => $shares, 'net_profit' => round($net_pnl, 2),
            'return_pct' => round($ret_pct, 4), 'exit_reason' => $exit_r, 'hold_days' => $day_count
        );

        $total_trades++;
        $total_comm += $comm_tot;
        $capital += $net_pnl;
        $returns[] = $ret_pct;

        if ($net_pnl > 0) { $wins++; $total_wins_pct += $ret_pct; $gross_wins += $net_pnl; }
        else { $losses++; $total_losses_pct += abs($ret_pct); $gross_losses += abs($net_pnl); }

        if ($capital > $peak) $peak = $capital;
        $dd = ($peak > 0) ? (($peak - $capital) / $peak) * 100 : 0;
        if ($dd > $max_dd) $max_dd = $dd;
    }

    // Metrics
    $wr = ($total_trades > 0) ? round($wins / $total_trades * 100, 2) : 0;
    $aw = ($wins > 0) ? round($total_wins_pct / $wins, 4) : 0;
    $al = ($losses > 0) ? round($total_losses_pct / $losses, 4) : 0;
    $pf = ($gross_losses > 0) ? round($gross_wins / $gross_losses, 4) : ($gross_wins > 0 ? 999 : 0);
    $lr = ($total_trades > 0) ? $losses / $total_trades : 0;
    $wrd = ($total_trades > 0) ? $wins / $total_trades : 0;
    $exp = round(($wrd * $aw) - ($lr * $al), 4);

    $sharpe = 0;
    if (count($returns) > 1) {
        $mean = array_sum($returns) / count($returns);
        $var = 0;
        foreach ($returns as $r) { $var += ($r - $mean) * ($r - $mean); }
        $std = sqrt($var / count($returns));
        if ($std > 0) $sharpe = round($mean / $std, 4);
    }

    $total_ret = ($cap > 0) ? round(($capital - $cap) / $cap * 100, 4) : 0;

    return array(
        'total_trades' => $total_trades,
        'winning_trades' => $wins,
        'losing_trades' => $losses,
        'win_rate' => $wr,
        'avg_win_pct' => $aw,
        'avg_loss_pct' => $al,
        'total_return_pct' => $total_ret,
        'final_value' => round($capital, 2),
        'max_drawdown_pct' => round($max_dd, 4),
        'total_commissions' => round($total_comm, 2),
        'sharpe_ratio' => $sharpe,
        'profit_factor' => $pf,
        'expectancy' => $exp,
        'trades' => $trades
    );
}

// ─── Comparison Mode: run all preset scenarios ───
if ($compare_mode === 1) {
    $comparison = array();
    foreach ($scenarios as $key => $sc) {
        $result = run_backtest_inline(
            $conn, $algorithms, $sc['take_profit'], $sc['stop_loss'],
            $sc['max_hold'], $initial_capital, $commission, $slippage, 10
        );
        $comparison[] = array(
            'scenario_key' => $key,
            'name' => $sc['name'],
            'description' => $sc['description'],
            'params' => array(
                'take_profit' => $sc['take_profit'],
                'stop_loss' => $sc['stop_loss'],
                'max_hold_days' => $sc['max_hold']
            ),
            'summary' => array(
                'total_trades' => $result['total_trades'],
                'win_rate' => $result['win_rate'],
                'total_return_pct' => $result['total_return_pct'],
                'final_value' => $result['final_value'],
                'max_drawdown_pct' => $result['max_drawdown_pct'],
                'total_commissions' => $result['total_commissions'],
                'sharpe_ratio' => $result['sharpe_ratio'],
                'profit_factor' => $result['profit_factor'],
                'expectancy' => $result['expectancy']
            )
        );
    }

    // Sort by total_return_pct descending
    // PHP 5.2 compatible sort
    $returns_arr = array();
    $count_c = count($comparison);
    for ($i = 0; $i < $count_c; $i++) {
        $returns_arr[$i] = $comparison[$i]['summary']['total_return_pct'];
    }
    arsort($returns_arr);
    $sorted = array();
    foreach ($returns_arr as $idx => $val) {
        $sorted[] = $comparison[$idx];
    }

    $response = array(
        'ok' => true,
        'mode' => 'comparison',
        'algorithms' => $algorithms,
        'initial_capital' => $initial_capital,
        'scenarios' => $sorted
    );

    echo json_encode($response);
    $conn->close();
    exit;
}

// ─── Single Scenario Mode ───
// Apply preset if specified
if ($scenario !== '' && isset($scenarios[$scenario])) {
    $sc = $scenarios[$scenario];
    $take_profit   = $sc['take_profit'];
    $stop_loss     = $sc['stop_loss'];
    $max_hold_days = $sc['max_hold'];
}

$result = run_backtest_inline(
    $conn, $algorithms, $take_profit, $stop_loss,
    $max_hold_days, $initial_capital, $commission, $slippage, 10
);

$response = array(
    'ok' => true,
    'mode' => 'single',
    'params' => array(
        'scenario'     => $scenario,
        'algorithms'   => $algorithms,
        'take_profit'  => $take_profit,
        'stop_loss'    => $stop_loss,
        'max_hold_days'=> $max_hold_days,
        'initial_capital' => $initial_capital,
        'commission'   => $commission,
        'slippage'     => $slippage
    ),
    'summary' => array(
        'total_trades'     => $result['total_trades'],
        'winning_trades'   => $result['winning_trades'],
        'losing_trades'    => $result['losing_trades'],
        'win_rate'         => $result['win_rate'],
        'avg_win_pct'      => $result['avg_win_pct'],
        'avg_loss_pct'     => $result['avg_loss_pct'],
        'total_return_pct' => $result['total_return_pct'],
        'final_value'      => $result['final_value'],
        'max_drawdown_pct' => $result['max_drawdown_pct'],
        'total_commissions'=> $result['total_commissions'],
        'sharpe_ratio'     => $result['sharpe_ratio'],
        'profit_factor'    => $result['profit_factor'],
        'expectancy'       => $result['expectancy']
    ),
    'trades' => $result['trades']
);

// Log the what-if query
$now = date('Y-m-d H:i:s');
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$safe_query = $conn->real_escape_string($query_text);
$safe_params = $conn->real_escape_string(json_encode($response['params']));
$safe_results = $conn->real_escape_string(json_encode($response['summary']));
$conn->query("INSERT INTO whatif_scenarios (scenario_name, query_text, params_json, results_json, created_at)
              VALUES ('" . $conn->real_escape_string($scenario) . "', '$safe_query', '$safe_params', '$safe_results', '$now')");

echo json_encode($response);
$conn->close();
?>
