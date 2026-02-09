<?php
/**
 * DayTrades Miracle Claude — Budget-Aware Pick Recommender
 * Given a dollar budget + trading style, returns the optimal pick(s) with exact
 * shares, fees, net profit/loss calculations.
 * PHP 5.2 compatible.
 *
 * Usage:
 *   GET .../budget_pick2.php?budget=250                    — best pick for $250
 *   GET .../budget_pick2.php?budget=1000&top=5             — top 5 picks for $1000
 *   GET .../budget_pick2.php?budget=500&cdr_only=1         — CDR-only picks for $500
 *   GET .../budget_pick2.php?budget=100&strategy=X         — filter by strategy
 *   GET .../budget_pick2.php?budget=250&days=7             — include last 7 days of picks
 *   GET .../budget_pick2.php?budget=250&fresh=1            — run a fresh scan first
 *   GET .../budget_pick2.php?budget=250&style=intraday     — day trade (today only)
 *   GET .../budget_pick2.php?budget=250&style=overnight    — day trade (next day close)
 *   GET .../budget_pick2.php?budget=250&style=swing        — swing trade (up to 1 week)
 *   GET .../budget_pick2.php?budget=250&style=longterm     — buy & hold (weeks/months)
 */
require_once dirname(__FILE__) . '/db_connect2.php';
require_once dirname(__FILE__) . '/questrade_fees2.php';

$budget     = isset($_GET['budget']) ? (float)$_GET['budget'] : 0;
$top_n      = isset($_GET['top']) ? (int)$_GET['top'] : 5;
$cdr_only   = isset($_GET['cdr_only']) ? (int)$_GET['cdr_only'] : 0;
$strategy   = isset($_GET['strategy']) ? trim($_GET['strategy']) : '';
$days       = isset($_GET['days']) ? (int)$_GET['days'] : 0;
$fresh_scan = isset($_GET['fresh']) ? (int)$_GET['fresh'] : 0;
$style      = isset($_GET['style']) ? trim(strtolower($_GET['style'])) : '';

// ─── Trading style definitions ───
// Each style adjusts TP/SL multipliers and gives score bonuses/penalties
// to strategies that match or conflict with the desired hold period.
$style_configs = array(
    'intraday' => array(
        'label'       => 'Day Trade (Today)',
        'max_hold'    => '1 day',
        'tp_mult'     => 0.6,
        'sl_mult'     => 0.7,
        'preferred'   => 'Gap Up Momentum,Sector Momentum Leader,CDR Zero-Fee Play,Volume Surge Breakout',
        'penalized'   => 'Earnings Catalyst Runner,Mean Reversion Sniper,Momentum Continuation',
        'bonus'       => 15,
        'penalty'     => -12
    ),
    'overnight' => array(
        'label'       => 'Day Trade (Next Day)',
        'max_hold'    => '2 days',
        'tp_mult'     => 0.8,
        'sl_mult'     => 0.85,
        'preferred'   => 'Gap Up Momentum,Volume Surge Breakout,CDR Zero-Fee Play,Sector Momentum Leader',
        'penalized'   => 'Earnings Catalyst Runner',
        'bonus'       => 10,
        'penalty'     => -8
    ),
    'swing' => array(
        'label'       => 'Swing Trade (Up to 1 Week)',
        'max_hold'    => '5-7 days',
        'tp_mult'     => 1.0,
        'sl_mult'     => 1.0,
        'preferred'   => 'Momentum Continuation,Oversold Bounce,Mean Reversion Sniper,Earnings Catalyst Runner,CDR Zero-Fee Play',
        'penalized'   => '',
        'bonus'       => 10,
        'penalty'     => 0
    ),
    'longterm' => array(
        'label'       => 'Buy & Hold (Weeks/Months)',
        'max_hold'    => '30+ days',
        'tp_mult'     => 2.0,
        'sl_mult'     => 1.5,
        'preferred'   => 'Momentum Continuation,Mean Reversion Sniper,Oversold Bounce,CDR Zero-Fee Play',
        'penalized'   => 'Gap Up Momentum,Sector Momentum Leader',
        'bonus'       => 12,
        'penalty'     => -8
    )
);

$active_style = null;
$style_label  = '';
if ($style !== '' && isset($style_configs[$style])) {
    $active_style = $style_configs[$style];
    $style_label  = $active_style['label'];
}

if ($budget <= 0) {
    echo json_encode(array('ok' => false, 'error' => 'Please provide a budget amount. Example: ?budget=250'));
    $conn->close();
    exit;
}

if ($top_n < 1) $top_n = 5;
if ($top_n > 20) $top_n = 20;

// ─── Optionally run a fresh scan first ───
if ($fresh_scan) {
    $scan_url = 'https://findtorontoevents.ca/findstocks2_global/api/scanner2.php?top=25';
    $ctx = stream_context_create(array('http' => array('timeout' => 120, 'header' => "User-Agent: BudgetPick/1.0\r\n")));
    @file_get_contents($scan_url, false, $ctx);
}

// ─── Load today's (or recent) picks ───
$where = array("outcome = 'pending'");
if ($days > 0) {
    $where[] = "scan_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY)";
} else {
    $where[] = "scan_date = CURDATE()";
}
if ($cdr_only) {
    $where[] = "is_cdr = 1";
}
if ($strategy !== '') {
    $where[] = "strategy_name = '" . $conn->real_escape_string($strategy) . "'";
}

$where_sql = implode(' AND ', $where);
$sql = "SELECT * FROM miracle_picks2 WHERE $where_sql ORDER BY score DESC";
$res = $conn->query($sql);

$candidates = array();
if ($res) {
    while ($row = $res->fetch_assoc()) {
        $candidates[] = $row;
    }
}

if (count($candidates) === 0) {
    // Try expanding to last 7 days if no today picks
    $where[1] = "scan_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)";
    $where_sql = implode(' AND ', $where);
    $res = $conn->query("SELECT * FROM miracle_picks2 WHERE $where_sql ORDER BY score DESC");
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $candidates[] = $row;
        }
    }
}

if (count($candidates) === 0) {
    echo json_encode(array(
        'ok'      => true,
        'budget'  => $budget,
        'style'   => $style,
        'style_label' => $style_label,
        'message' => 'No picks available. Run the scanner first: scanner2.php',
        'picks'   => array()
    ));
    $conn->close();
    exit;
}

// ─── Helper: check if strategy name is in a comma-separated list ───
function _in_list($name, $csv) {
    if ($csv === '') return false;
    $parts = explode(',', $csv);
    for ($i = 0; $i < count($parts); $i++) {
        if (trim($parts[$i]) === $name) return true;
    }
    return false;
}

// ─── Calculate budget-specific metrics for each candidate ───
$budget_picks = array();

foreach ($candidates as $pick) {
    $entry_price = (float)$pick['entry_price'];
    $orig_tp     = (float)$pick['take_profit_price'];
    $orig_sl     = (float)$pick['stop_loss_price'];
    $tp_pct      = (float)$pick['take_profit_pct'];
    $sl_pct      = (float)$pick['stop_loss_pct'];
    $ticker      = $pick['ticker'];
    $is_cdr      = (int)$pick['is_cdr'];
    $strat_name  = $pick['strategy_name'];

    // ─── Style-adjusted TP/SL ───
    $tp_price = $orig_tp;
    $sl_price = $orig_sl;
    if ($active_style !== null) {
        $tp_move = ($orig_tp - $entry_price) * $active_style['tp_mult'];
        $sl_move = ($entry_price - $orig_sl) * $active_style['sl_mult'];
        $tp_price = round($entry_price + $tp_move, 4);
        $sl_price = round($entry_price - $sl_move, 4);
        // Recalculate percentages
        if ($entry_price > 0) {
            $tp_pct = round(($tp_price - $entry_price) / $entry_price * 100, 2);
            $sl_pct = round(($entry_price - $sl_price) / $entry_price * 100, 2);
        }
    }

    // Can we afford at least 1 share?
    if ($entry_price <= 0 || $entry_price > $budget) continue;

    // Calculate max shares we can buy
    $max_shares = floor($budget / $entry_price);
    if ($max_shares < 1) continue;

    $invested = round($max_shares * $entry_price, 2);
    $leftover = round($budget - $invested, 2);

    // ─── Calculate exact Questrade fees (round-trip: buy + sell) ───
    $buy_fees  = questrade_calc_fees2($ticker, $invested, $max_shares, false, 'questrade');
    $sell_at_tp = $max_shares * $tp_price;
    $sell_fees_tp = questrade_calc_fees2($ticker, $sell_at_tp, $max_shares, true, 'questrade');
    $sell_at_sl = $max_shares * $sl_price;
    $sell_fees_sl = questrade_calc_fees2($ticker, $sell_at_sl, $max_shares, true, 'questrade');

    $total_fee_buy = $buy_fees['total_fee'];

    // ─── Scenario: Take Profit Hit ───
    $gross_profit_tp = round(($tp_price - $entry_price) * $max_shares, 2);
    $total_fees_tp   = round($total_fee_buy + $sell_fees_tp['total_fee'], 2);
    $net_profit_tp   = round($gross_profit_tp - $total_fees_tp, 2);
    $net_return_tp   = ($invested > 0) ? round(($net_profit_tp / $invested) * 100, 2) : 0;

    // ─── Scenario: Stop Loss Hit ───
    $gross_loss_sl   = round(($sl_price - $entry_price) * $max_shares, 2); // negative
    $total_fees_sl   = round($total_fee_buy + $sell_fees_sl['total_fee'], 2);
    $net_loss_sl     = round($gross_loss_sl - $total_fees_sl, 2); // more negative
    $net_return_sl   = ($invested > 0) ? round(($net_loss_sl / $invested) * 100, 2) : 0;

    // ─── Fee drag (what % of gross profit goes to fees) ───
    $fee_drag_pct = ($gross_profit_tp > 0) ? round(($total_fees_tp / $gross_profit_tp) * 100, 1) : 100;

    // ─── Skip if fees eat more than 50% of profit (not worth it) ───
    if ($fee_drag_pct > 50 && $net_profit_tp < 5) continue;

    // ─── Risk/reward in dollars ───
    $dollar_risk   = abs($net_loss_sl);
    $dollar_reward = $net_profit_tp;
    $rr_ratio      = ($dollar_risk > 0) ? round($dollar_reward / $dollar_risk, 2) : 0;

    // ─── Budget score: emphasizes net profit and low fee drag ───
    $base_score = (int)$pick['score'];
    $budget_score = $base_score;

    // Bonus for low fee drag
    if ($fee_drag_pct < 5)       $budget_score += 15;
    elseif ($fee_drag_pct < 15)  $budget_score += 10;
    elseif ($fee_drag_pct < 30)  $budget_score += 5;

    // Bonus for good net profit relative to budget
    $profit_pct_of_budget = ($budget > 0) ? ($net_profit_tp / $budget) * 100 : 0;
    if ($profit_pct_of_budget >= 5)      $budget_score += 10;
    elseif ($profit_pct_of_budget >= 3)  $budget_score += 7;
    elseif ($profit_pct_of_budget >= 1)  $budget_score += 3;

    // Bonus for CDR (zero fees)
    if ($is_cdr) $budget_score += 5;

    // Penalty if net profit is tiny (< $5)
    if ($net_profit_tp < 5) $budget_score -= 10;

    // ─── Style-based scoring adjustments ───
    if ($active_style !== null) {
        if (_in_list($strat_name, $active_style['preferred'])) {
            $budget_score += $active_style['bonus'];
        }
        if (_in_list($strat_name, $active_style['penalized'])) {
            $budget_score += $active_style['penalty']; // negative
        }
    }

    if ($budget_score > 100) $budget_score = 100;
    if ($budget_score < 0)   $budget_score = 0;

    // Confidence
    $confidence = 'low';
    if ($budget_score >= 70) $confidence = 'high';
    elseif ($budget_score >= 50) $confidence = 'medium';

    // ─── Breakeven calculation ───
    // How much does the stock need to move (%) just to cover fees?
    $breakeven_move_pct = ($invested > 0) ? round(($total_fees_tp / $invested) * 100, 3) : 0;

    // ─── Determine hold period label ───
    $hold_label = '';
    if ($active_style !== null) {
        $hold_label = $active_style['max_hold'];
    }

    $budget_picks[] = array(
        'rank'             => 0,
        'ticker'           => $ticker,
        'company'          => '',
        'strategy'         => $strat_name,
        'is_cdr'           => $is_cdr,
        'budget'           => $budget,
        'entry_price'      => $entry_price,
        'shares'           => $max_shares,
        'invested'         => $invested,
        'leftover'         => $leftover,
        // Take-profit scenario
        'tp_price'         => $tp_price,
        'tp_pct'           => $tp_pct,
        'gross_profit'     => $gross_profit_tp,
        'total_fees'       => $total_fees_tp,
        'net_profit'       => $net_profit_tp,
        'net_return_pct'   => $net_return_tp,
        'fee_breakdown_buy'=> $buy_fees['fee_breakdown'],
        'fee_breakdown_sell'=> $sell_fees_tp['fee_breakdown'],
        // Stop-loss scenario
        'sl_price'         => $sl_price,
        'sl_pct'           => $sl_pct,
        'net_loss'         => $net_loss_sl,
        'net_loss_pct'     => $net_return_sl,
        // Analysis
        'fee_drag_pct'     => $fee_drag_pct,
        'breakeven_pct'    => $breakeven_move_pct,
        'risk_reward'      => $rr_ratio,
        'budget_score'     => $budget_score,
        'original_score'   => $base_score,
        'confidence'       => $confidence,
        'hold_period'      => $hold_label,
        'scan_date'        => $pick['scan_date'],
        'signals'          => json_decode($pick['signals_json'], true)
    );
}

// ─── Sort by budget_score DESC ───
$count = count($budget_picks);
for ($i = 0; $i < $count - 1; $i++) {
    for ($j = 0; $j < $count - $i - 1; $j++) {
        if ($budget_picks[$j]['budget_score'] < $budget_picks[$j + 1]['budget_score']) {
            $tmp = $budget_picks[$j];
            $budget_picks[$j] = $budget_picks[$j + 1];
            $budget_picks[$j + 1] = $tmp;
        }
    }
}

// Assign ranks and limit
$top_budget_picks = array_slice($budget_picks, 0, $top_n);
for ($i = 0; $i < count($top_budget_picks); $i++) {
    $top_budget_picks[$i]['rank'] = $i + 1;
}

// ─── Enrich with company names from watchlist ───
$tickers_in = array();
foreach ($top_budget_picks as $p) {
    $tickers_in[] = "'" . $conn->real_escape_string($p['ticker']) . "'";
}
if (count($tickers_in) > 0) {
    $in_sql = implode(',', $tickers_in);
    $res = $conn->query("SELECT ticker, company_name FROM miracle_watchlist2 WHERE ticker IN ($in_sql)");
    $names = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $names[$row['ticker']] = $row['company_name'];
        }
    }
    for ($i = 0; $i < count($top_budget_picks); $i++) {
        $t = $top_budget_picks[$i]['ticker'];
        if (isset($names[$t])) {
            $top_budget_picks[$i]['company'] = $names[$t];
        }
    }
}

// ─── Build recommendation text for #1 pick ───
$recommendation = '';
if (count($top_budget_picks) > 0) {
    $best = $top_budget_picks[0];
    $cdr_note = $best['is_cdr'] ? ' (CDR = $0 commission)' : '';
    $style_note = $style_label !== '' ? ' [' . $style_label . ']' : '';
    $recommendation = 'With $' . number_format($budget, 2) . $style_note . ', buy '
        . $best['shares'] . ' share' . ($best['shares'] > 1 ? 's' : '') . ' of '
        . $best['ticker'] . ' at $' . number_format($best['entry_price'], 2) . $cdr_note . '. '
        . 'Set stop-loss at $' . number_format($best['sl_price'], 2)
        . ' and take-profit at $' . number_format($best['tp_price'], 2) . '. ';

    if ($best['hold_period'] !== '') {
        $recommendation .= 'Max hold: ' . $best['hold_period'] . '. ';
    }

    if ($best['net_profit'] > 0) {
        $recommendation .= 'If TP hits: +$' . number_format($best['net_profit'], 2)
            . ' net profit (' . $best['net_return_pct'] . '% return). ';
    }
    $recommendation .= 'If SL hits: -$' . number_format(abs($best['net_loss']), 2)
        . ' net loss (' . $best['net_loss_pct'] . '%). ';
    $recommendation .= 'Fees: $' . number_format($best['total_fees'], 2)
        . ' round-trip (' . $best['fee_drag_pct'] . '% of profit). ';
    $recommendation .= 'R:R ' . $best['risk_reward'] . ':1. ';
    $recommendation .= 'Stock must move ' . $best['breakeven_pct'] . '% just to break even on fees.';
}

// ─── Summary stats ───
$affordable_count = count($budget_picks);
$cdr_affordable = 0;
$avg_fee_drag = 0;
foreach ($budget_picks as $bp) {
    if ($bp['is_cdr']) $cdr_affordable++;
    $avg_fee_drag += $bp['fee_drag_pct'];
}
$avg_fee_drag = ($affordable_count > 0) ? round($avg_fee_drag / $affordable_count, 1) : 0;

echo json_encode(array(
    'ok'             => true,
    'budget'         => $budget,
    'style'          => $style,
    'style_label'    => $style_label,
    'affordable'     => $affordable_count,
    'cdr_affordable' => $cdr_affordable,
    'avg_fee_drag'   => $avg_fee_drag,
    'recommendation' => $recommendation,
    'picks'          => $top_budget_picks
));

$conn->close();
?>
