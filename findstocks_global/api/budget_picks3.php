<?php
/**
 * Budget-Aware Picks API for DayTraders Miracle v3.
 * Returns picks personalized to a user's budget and preferred timeframe.
 * Calculates exact share count, Questrade fees, and net P/L.
 * PHP 5.2 compatible.
 *
 * Usage:
 *   GET budget_picks3.php?budget=500&timeframe=daytrade
 *   GET budget_picks3.php?budget=2000&timeframe=swing&cdr_only=1
 *
 * Timeframes:
 *   intraday  - exit by today's close (tightest TP/SL)
 *   daytrade  - exit by next trading day's close
 *   swing     - hold up to 1 week (5 trading days)
 *   longterm  - buy and hold (weeks to months)
 */
require_once dirname(__FILE__) . '/db_connect3.php';

// ─── CDR list (from Questrade — $0 commission) ───
$CDR_TICKERS = array(
    'AAPL','AMD','AMZN','CSCO','CRM','GOOG','GOOGL','IBM','INTC','META','MSFT','NFLX','NVDA',
    'COST','DIS','HD','MCD','NKE','SBUX','TSLA','WMT',
    'ABBV','CVS','JNJ','PFE','UNH',
    'BAC','BRK.B','GS','JPM','V','MA',
    'BA','CAT','GE','MMM','XOM','CVX'
);

function _bp_is_cdr($ticker) {
    global $CDR_TICKERS;
    $upper = strtoupper(trim($ticker));
    $base = preg_replace('/\.(TO|V|CN)$/', '', $upper);
    return in_array($upper, $CDR_TICKERS) || in_array($base, $CDR_TICKERS);
}

function _bp_is_canadian($ticker) {
    return (bool)preg_match('/\.(TO|V|CN)$/i', $ticker);
}

function _bp_calc_fees($ticker, $entry, $exit, $shares) {
    if (_bp_is_cdr($ticker) || _bp_is_canadian($ticker)) {
        return array('total' => 0, 'forex' => 0, 'ecn' => 0, 'sec' => 0, 'is_cdr' => _bp_is_cdr($ticker));
    }
    $buy_val = $entry * $shares;
    $sell_val = $exit * $shares;
    $forex = ($buy_val + $sell_val) * 0.0175;
    $ecn = $shares * 0.0035 * 2;
    $sec = $sell_val * 0.0000278;
    $total = round($forex + $ecn + $sec, 2);
    return array('total' => $total, 'forex' => round($forex, 2), 'ecn' => round($ecn, 4), 'sec' => round($sec, 4), 'is_cdr' => false);
}

// ─── Parse parameters ───
$budget = isset($_GET['budget']) ? (float)$_GET['budget'] : 0;
$timeframe = isset($_GET['timeframe']) ? trim($_GET['timeframe']) : 'daytrade';
$cdr_only = isset($_GET['cdr_only']) ? (int)$_GET['cdr_only'] : 0;

if ($budget < 50 || $budget > 500000) {
    echo json_encode(array('ok' => false, 'error' => 'Budget must be between $50 and $500,000'));
    $conn->close();
    exit;
}

// ─── Timeframe profiles ───
$profiles = array(
    'intraday' => array(
        'name' => 'Intraday (Same Day)',
        'description' => 'Exit by today\'s market close. Tightest stops for quick scalps.',
        'tp_multiplier' => 0.5,
        'sl_multiplier' => 0.5,
        'tp_min' => 1.0,
        'tp_max' => 5.0,
        'sl_min' => 0.5,
        'sl_max' => 3.0,
        'max_hold' => '0 days (exit today)',
        'urgency' => 'Must close by 4 PM ET today',
        'icon' => 'clock',
        'color' => '#ef4444',
        'prefer_strategies' => array('Gap Up Momentum', 'Volume Surge Breakout', 'CDR Zero-Fee Priority')
    ),
    'daytrade' => array(
        'name' => 'Day Trade (Next Day Close)',
        'description' => 'Can hold overnight. Exit by next trading day close.',
        'tp_multiplier' => 0.75,
        'sl_multiplier' => 0.75,
        'tp_min' => 2.0,
        'tp_max' => 8.0,
        'sl_min' => 1.0,
        'sl_max' => 5.0,
        'max_hold' => '1 trading day',
        'urgency' => 'Exit by next day close',
        'icon' => 'zap',
        'color' => '#eab308',
        'prefer_strategies' => array('Gap Up Momentum', 'Volume Surge Breakout', 'Momentum Continuation', 'CDR Zero-Fee Priority')
    ),
    'swing' => array(
        'name' => 'Swing Trade (Up to 1 Week)',
        'description' => 'Hold up to 5 trading days. Wider stops for trend riding.',
        'tp_multiplier' => 1.5,
        'sl_multiplier' => 1.2,
        'tp_min' => 5.0,
        'tp_max' => 20.0,
        'sl_min' => 3.0,
        'sl_max' => 10.0,
        'max_hold' => '5 trading days',
        'urgency' => 'Exit within 1 week',
        'icon' => 'trending',
        'color' => '#6366f1',
        'prefer_strategies' => array('Momentum Continuation', 'Sector Momentum Leader', 'Mean Reversion Sniper', 'Earnings Catalyst Runner')
    ),
    'longterm' => array(
        'name' => 'Buy & Hold (Long-Term)',
        'description' => 'Hold for weeks to months. Widest stops for major moves.',
        'tp_multiplier' => 3.0,
        'sl_multiplier' => 2.0,
        'tp_min' => 15.0,
        'tp_max' => 50.0,
        'sl_min' => 8.0,
        'sl_max' => 20.0,
        'max_hold' => 'Weeks to months',
        'urgency' => 'Patient capital — let winners run',
        'icon' => 'shield',
        'color' => '#22c55e',
        'prefer_strategies' => array('Momentum Continuation', 'Oversold Bounce', 'Sector Momentum Leader')
    )
);

if (!isset($profiles[$timeframe])) {
    echo json_encode(array('ok' => false, 'error' => 'Invalid timeframe. Use: intraday, daytrade, swing, longterm'));
    $conn->close();
    exit;
}

$profile = $profiles[$timeframe];

// ─── Fetch recent picks ───
$where = "scan_date >= DATE_SUB(CURDATE(), INTERVAL 3 DAY)";
if ($cdr_only) {
    $where .= " AND is_cdr = 1";
}

// Build strategy preference ordering
$prefer = $profile['prefer_strategies'];
$order_parts = array();
for ($pi = 0; $pi < count($prefer); $pi++) {
    $safe_strat = $conn->real_escape_string($prefer[$pi]);
    $order_parts[] = "WHEN strategy_name = '$safe_strat' THEN $pi";
}
$strat_order = '';
if (count($order_parts) > 0) {
    $strat_order = 'CASE ' . implode(' ', $order_parts) . ' ELSE 99 END ASC, ';
}

$sql = "SELECT * FROM miracle_picks3
        WHERE $where AND entry_price > 0
        ORDER BY $strat_order score DESC, scan_date DESC
        LIMIT 100";

$res = $conn->query($sql);
if (!$res) {
    echo json_encode(array('ok' => false, 'error' => 'Database error: ' . $conn->error));
    $conn->close();
    exit;
}

// ─── Process picks with budget ───
$picks = array();
$seen_tickers = array();
$max_picks = 12;

while ($row = $res->fetch_assoc()) {
    $ticker = $row['ticker'];

    // One pick per ticker
    if (isset($seen_tickers[$ticker])) continue;

    $entry = (float)$row['entry_price'];
    if ($entry <= 0) continue;

    // Must be affordable
    if ($entry > $budget) continue;

    // Calculate shares
    $shares = (int)floor($budget / $entry);
    if ($shares < 1) continue;

    $position_value = round($shares * $entry, 2);

    // Adjust TP/SL based on timeframe profile
    $orig_tp_pct = (float)$row['take_profit_pct'];
    $orig_sl_pct = (float)$row['stop_loss_pct'];

    $adj_tp_pct = $orig_tp_pct * $profile['tp_multiplier'];
    $adj_sl_pct = $orig_sl_pct * $profile['sl_multiplier'];

    // Clamp to profile min/max
    if ($adj_tp_pct < $profile['tp_min']) $adj_tp_pct = $profile['tp_min'];
    if ($adj_tp_pct > $profile['tp_max']) $adj_tp_pct = $profile['tp_max'];
    if ($adj_sl_pct < $profile['sl_min']) $adj_sl_pct = $profile['sl_min'];
    if ($adj_sl_pct > $profile['sl_max']) $adj_sl_pct = $profile['sl_max'];

    $adj_tp_pct = round($adj_tp_pct, 2);
    $adj_sl_pct = round($adj_sl_pct, 2);

    $tp_price = round($entry * (1 + $adj_tp_pct / 100), 2);
    $sl_price = round($entry * (1 - $adj_sl_pct / 100), 2);

    // Calculate fees
    $buy_fees = _bp_calc_fees($ticker, $entry, $entry, $shares);
    $sell_fees_tp = _bp_calc_fees($ticker, $tp_price, $tp_price, $shares);
    $sell_fees_sl = _bp_calc_fees($ticker, $sl_price, $sl_price, $shares);

    $total_fee_tp = round($buy_fees['total'] + $sell_fees_tp['total'], 2);
    $total_fee_sl = round($buy_fees['total'] + $sell_fees_sl['total'], 2);

    // Net P/L
    $gross_profit = round(($tp_price - $entry) * $shares, 2);
    $net_profit = round($gross_profit - $total_fee_tp, 2);

    $gross_loss = round(($entry - $sl_price) * $shares, 2);
    $net_loss = round(-$gross_loss - $total_fee_sl, 2);

    // Risk:Reward
    $risk = abs($net_loss);
    $reward = $net_profit;
    $rr_ratio = ($risk > 0) ? round($reward / $risk, 2) : 0;

    // Fee drag percentage
    $fee_drag = ($position_value > 0) ? round($total_fee_tp / $position_value * 100, 3) : 0;

    // Budget utilization
    $utilization = round($position_value / $budget * 100, 1);

    // Parse signals
    $signals = array();
    if (isset($row['signals_json']) && $row['signals_json'] !== '') {
        $decoded = json_decode($row['signals_json'], true);
        if ($decoded) $signals = $decoded;
    }

    $pick = array(
        'ticker' => $ticker,
        'company_name' => isset($row['company_name']) ? $row['company_name'] : '',
        'strategy_name' => isset($row['strategy_name']) ? $row['strategy_name'] : '',
        'score' => (int)$row['score'],
        'confidence' => isset($row['confidence']) ? $row['confidence'] : 'Okay',
        'is_cdr' => (int)$row['is_cdr'],
        'scan_date' => isset($row['scan_date']) ? $row['scan_date'] : '',
        'entry_price' => $entry,
        'take_profit_price' => $tp_price,
        'stop_loss_price' => $sl_price,
        'take_profit_pct' => $adj_tp_pct,
        'stop_loss_pct' => $adj_sl_pct,
        'orig_tp_pct' => $orig_tp_pct,
        'orig_sl_pct' => $orig_sl_pct,
        'shares' => $shares,
        'position_value' => $position_value,
        'budget_utilization' => $utilization,
        'fees_roundtrip' => $total_fee_tp,
        'fee_drag_pct' => $fee_drag,
        'gross_profit' => $gross_profit,
        'net_profit' => $net_profit,
        'gross_loss' => $gross_loss,
        'net_loss' => $net_loss,
        'risk_reward' => $rr_ratio,
        'risk_reward_ratio' => isset($row['risk_reward_ratio']) ? (float)$row['risk_reward_ratio'] : 0,
        'signals' => $signals
    );

    $picks[] = $pick;
    $seen_tickers[$ticker] = true;
    if (count($picks) >= $max_picks) break;
}

// ─── Summary stats ───
$total_net = 0;
$total_risk = 0;
$cdr_count = 0;
$best_pick = null;
$best_profit = -999;
foreach ($picks as $pk) {
    $total_net = $total_net + $pk['net_profit'];
    $total_risk = $total_risk + abs($pk['net_loss']);
    if ($pk['is_cdr']) $cdr_count++;
    if ($pk['net_profit'] > $best_profit) {
        $best_profit = $pk['net_profit'];
        $best_pick = $pk['ticker'];
    }
}

$avg_profit = (count($picks) > 0) ? round($total_net / count($picks), 2) : 0;
$avg_risk = (count($picks) > 0) ? round($total_risk / count($picks), 2) : 0;

$response = array(
    'ok' => true,
    'budget' => $budget,
    'timeframe' => $timeframe,
    'profile' => array(
        'name' => $profile['name'],
        'description' => $profile['description'],
        'max_hold' => $profile['max_hold'],
        'urgency' => $profile['urgency'],
        'color' => $profile['color'],
        'tp_range' => $profile['tp_min'] . '-' . $profile['tp_max'] . '%',
        'sl_range' => $profile['sl_min'] . '-' . $profile['sl_max'] . '%'
    ),
    'picks' => $picks,
    'count' => count($picks),
    'summary' => array(
        'total_potential_profit' => $total_net,
        'total_potential_risk' => $total_risk,
        'avg_profit_per_pick' => $avg_profit,
        'avg_risk_per_pick' => $avg_risk,
        'cdr_picks' => $cdr_count,
        'best_pick' => $best_pick,
        'best_profit' => $best_profit
    ),
    'profiles' => $profiles
);

echo json_encode($response);
$conn->close();
?>
