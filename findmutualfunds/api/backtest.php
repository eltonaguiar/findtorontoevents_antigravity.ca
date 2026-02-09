<?php
/**
 * Mutual Fund Backtest Engine
 * Simulates buying funds at NAV, holding for a period, accounting for
 * expense ratios, loads (front/back), commissions, and redemption timing.
 * PHP 5.2 compatible.
 *
 * Usage: GET with parameters:
 *   strategies      - comma-separated strategy names (empty = all)
 *   hold_days       - holding period in calendar days (default 90)
 *   target_return   - target return % to sell early (default 999 = none)
 *   stop_loss       - max loss % to exit (default 999 = none)
 *   initial_capital - starting capital (default 10000)
 *   commission      - commission per trade $ (default 9.95 = Questrade MF fee)
 *   fee_model       - questrade|zero|custom (default questrade)
 *   include_expenses- 1 to deduct expense ratio from returns (default 1)
 *
 * Questrade mutual fund fees: $9.95 per buy + $9.95 per sell = $19.90 round trip
 */
require_once dirname(__FILE__) . '/db_connect.php';

function _mfp($key, $default) {
    if (isset($_GET[$key]) && $_GET[$key] !== '') return $_GET[$key];
    if (isset($_POST[$key]) && $_POST[$key] !== '') return $_POST[$key];
    return $default;
}

$strategies      = _mfp('strategies', '');
$hold_days       = (int)_mfp('hold_days', 90);
$target_return   = (float)_mfp('target_return', 999);
$stop_loss       = (float)_mfp('stop_loss', 999);
$initial_capital = (float)_mfp('initial_capital', 10000);
$fee_model       = _mfp('fee_model', 'questrade');
$commission      = (float)_mfp('commission', ($fee_model === 'questrade') ? 9.95 : 0);
$incl_expenses   = (int)_mfp('include_expenses', 1);
$position_pct    = (float)_mfp('position_size', 10);

// Build strategy filter
$where_strat = '';
if ($strategies !== '') {
    $parts = explode(',', $strategies);
    $escaped = array();
    foreach ($parts as $s) {
        $s = trim($s);
        if ($s !== '') $escaped[] = "'" . $conn->real_escape_string($s) . "'";
    }
    if (count($escaped) > 0) $where_strat = " AND ms.strategy_name IN (" . implode(',', $escaped) . ")";
}

// Fetch selections (picks)
$sql = "SELECT ms.*, mf.fund_name, mf.expense_ratio, mf.front_load_pct, mf.back_load_pct, mf.load_type
        FROM mf_selections ms
        LEFT JOIN mf_funds mf ON ms.ticker = mf.ticker
        WHERE ms.nav_at_select > 0 $where_strat
        ORDER BY ms.select_date ASC, ms.ticker ASC";

$picks_res = $conn->query($sql);
if (!$picks_res || $picks_res->num_rows === 0) {
    echo json_encode(array('ok' => false, 'error' => 'No fund selections found. Run setup and import first.'));
    $conn->close();
    exit;
}

// Run backtest
$capital = $initial_capital;
$peak = $initial_capital;
$max_dd = 0;
$total_trades = 0;
$wins = 0;
$losses = 0;
$total_comm = 0;
$total_expenses = 0;
$trades = array();
$daily_returns = array();

while ($pick = $picks_res->fetch_assoc()) {
    $ticker = $pick['ticker'];
    $entry_nav = (float)$pick['nav_at_select'];
    $pick_date = $pick['select_date'];
    $strategy = $pick['strategy_name'];
    $fund_name = isset($pick['fund_name']) ? $pick['fund_name'] : '';
    $expense_ratio = (float)$pick['expense_ratio'];
    $front_load = (float)$pick['front_load_pct'];
    $back_load = (float)$pick['back_load_pct'];

    // Apply front-load fee (reduces effective entry)
    $effective_entry = $entry_nav * (1 + $front_load / 100);

    // Position sizing
    $pos_value = $capital * ($position_pct / 100);
    if ($pos_value < $effective_entry + $commission) continue;
    $shares = ($effective_entry > 0) ? ($pos_value - $commission) / $effective_entry : 0;
    if ($shares <= 0) continue;

    // Fetch NAV history after select date
    $safe_t = $conn->real_escape_string($ticker);
    $safe_d = $conn->real_escape_string($pick_date);
    $nav_sql = "SELECT nav_date, adj_nav FROM mf_nav_history
                WHERE ticker='$safe_t' AND nav_date >= '$safe_d'
                ORDER BY nav_date ASC LIMIT " . ($hold_days + 30);
    $nav_res = $conn->query($nav_sql);

    $day_count = 0;
    $sold = false;
    $exit_nav = $entry_nav;
    $exit_date = $pick_date;
    $exit_reason = 'end_of_data';
    $last_nav = $entry_nav;

    if ($nav_res && $nav_res->num_rows > 0) {
        while ($day = $nav_res->fetch_assoc()) {
            $day_count++;
            $last_nav = (float)$day['adj_nav'];
            $day_date = $day['nav_date'];

            // Calculate return so far
            $current_return = ($effective_entry > 0) ? (($last_nav - $effective_entry) / $effective_entry) * 100 : 0;

            // Stop loss
            if ($stop_loss < 999 && $current_return <= -$stop_loss) {
                $exit_nav = $last_nav;
                $exit_date = $day_date;
                $exit_reason = 'stop_loss';
                $sold = true;
                break;
            }

            // Target return
            if ($target_return < 999 && $current_return >= $target_return) {
                $exit_nav = $last_nav;
                $exit_date = $day_date;
                $exit_reason = 'target_reached';
                $sold = true;
                break;
            }

            // Hold period exceeded
            $days_held = (int)((strtotime($day_date) - strtotime($pick_date)) / 86400);
            if ($days_held >= $hold_days) {
                $exit_nav = $last_nav;
                $exit_date = $day_date;
                $exit_reason = 'hold_period';
                $sold = true;
                break;
            }
        }
        if (!$sold && $day_count > 0) {
            $exit_nav = $last_nav;
            $exit_date = $day_date;
        }
    }

    // Apply back-load fee
    $effective_exit = $exit_nav * (1 - $back_load / 100);

    // Calculate expense ratio drag (pro-rated for hold period)
    $actual_days = (int)((strtotime($exit_date) - strtotime($pick_date)) / 86400);
    if ($actual_days < 1) $actual_days = 1;
    $expense_cost = 0;
    if ($incl_expenses && $expense_ratio > 0) {
        $expense_cost = round($shares * $effective_entry * $expense_ratio * ($actual_days / 365), 2);
    }

    // P/L
    $gross = ($effective_exit - $effective_entry) * $shares;
    $comm_total = $commission * 2;
    $net = $gross - $comm_total - $expense_cost;
    $return_pct = ($effective_entry * $shares > 0) ? ($net / ($effective_entry * $shares)) * 100 : 0;

    $trade = array(
        'ticker' => $ticker, 'fund_name' => $fund_name, 'strategy' => $strategy,
        'entry_date' => $pick_date, 'entry_nav' => round($effective_entry, 4),
        'exit_date' => $exit_date, 'exit_nav' => round($effective_exit, 4),
        'shares' => round($shares, 4), 'hold_days' => $actual_days,
        'gross_profit' => round($gross, 2), 'expense_cost' => round($expense_cost, 2),
        'commission_paid' => round($comm_total, 2), 'net_profit' => round($net, 2),
        'return_pct' => round($return_pct, 4), 'exit_reason' => $exit_reason,
        'expense_ratio' => $expense_ratio
    );

    $trades[] = $trade;
    $total_trades++;
    $total_comm += $comm_total;
    $total_expenses += $expense_cost;
    $capital += $net;

    if ($net > 0) $wins++; else $losses++;

    if ($capital > $peak) $peak = $capital;
    $dd = ($peak > 0) ? (($peak - $capital) / $peak) * 100 : 0;
    if ($dd > $max_dd) $max_dd = $dd;

    $daily_returns[] = $return_pct;
}

// Aggregate metrics
$final_value = round($capital, 2);
$total_return = ($initial_capital > 0) ? round(($capital - $initial_capital) / $initial_capital * 100, 4) : 0;
$win_rate = ($total_trades > 0) ? round($wins / $total_trades * 100, 2) : 0;

// Sharpe
$sharpe = 0;
if (count($daily_returns) > 1) {
    $mean = array_sum($daily_returns) / count($daily_returns);
    $var = 0;
    foreach ($daily_returns as $r) $var += ($r - $mean) * ($r - $mean);
    $std = sqrt($var / count($daily_returns));
    if ($std > 0) $sharpe = round($mean / $std, 4);
}

$gross_wins = 0; $gross_losses = 0;
foreach ($trades as $t) {
    if ($t['net_profit'] > 0) $gross_wins += $t['net_profit'];
    else $gross_losses += abs($t['net_profit']);
}
$pf = ($gross_losses > 0) ? round($gross_wins / $gross_losses, 4) : ($gross_wins > 0 ? 999 : 0);

echo json_encode(array(
    'ok' => true,
    'params' => array(
        'strategies' => $strategies, 'hold_days' => $hold_days,
        'target_return_pct' => $target_return, 'stop_loss_pct' => $stop_loss,
        'initial_capital' => $initial_capital, 'commission' => $commission,
        'include_expenses' => $incl_expenses, 'position_size_pct' => $position_pct
    ),
    'summary' => array(
        'initial_capital' => $initial_capital, 'final_value' => $final_value,
        'total_return_pct' => $total_return, 'total_trades' => $total_trades,
        'winning_trades' => $wins, 'losing_trades' => $losses,
        'win_rate' => $win_rate, 'max_drawdown_pct' => round($max_dd, 4),
        'total_commissions' => round($total_comm, 2),
        'total_expenses' => round($total_expenses, 2),
        'sharpe_ratio' => $sharpe, 'profit_factor' => $pf,
        'gross_wins' => round($gross_wins, 2), 'gross_losses' => round($gross_losses, 2)
    ),
    'trades' => $trades
));
$conn->close();
?>
