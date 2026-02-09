<?php
/**
 * Horizon Picks API - Actionable stock picks organized by time horizon.
 * "I need money in 2 weeks" vs "I can wait 1 year" — different picks, different strategies.
 *
 * Each horizon shows top picks + backtested performance stats + $1000 projection.
 * Results cached in report_cache for 6 hours.
 * PHP 5.2 compatible.
 *
 * Usage:
 *   GET horizon_picks.php                  — all three horizons
 *   GET horizon_picks.php?urgency=14       — highlights the 2-week horizon
 *   GET horizon_picks.php?nocache=1        — bypass cache
 */
require_once dirname(__FILE__) . '/db_connect.php';

$urgency_days = isset($_GET['urgency']) ? (int)$_GET['urgency'] : 0;
$nocache = isset($_GET['nocache']) ? (int)$_GET['nocache'] : 0;
$now = date('Y-m-d H:i:s');

// ─── Check cache first ───
$cache_key = 'horizon_picks_v1';
if (!$nocache) {
    $ck = $conn->real_escape_string($cache_key);
    $cache_res = $conn->query("SELECT cache_data, updated_at FROM report_cache WHERE cache_key='$ck' LIMIT 1");
    if ($cache_res && $crow = $cache_res->fetch_assoc()) {
        $age_hours = (time() - strtotime($crow['updated_at'])) / 3600;
        if ($age_hours < 6) {
            $cached = json_decode($crow['cache_data'], true);
            if ($cached) {
                $cached['from_cache'] = true;
                $cached['cache_age_hours'] = round($age_hours, 1);
                if ($urgency_days > 0) {
                    $cached['urgency_days'] = $urgency_days;
                    $cached['recommended_horizon'] = _map_urgency($urgency_days);
                }
                echo json_encode($cached);
                $conn->close();
                exit;
            }
        }
    }
}

// ─── Strategy Profiles ───
$profiles = array(
    'quick' => array(
        'name'        => 'Quick Gains',
        'subtitle'    => '1-2 Weeks',
        'description' => 'Short-term momentum plays. Tight stops, fast exits. Best when you need returns quickly.',
        'tp_pct'      => 10,
        'sl_pct'      => 5,
        'hold_days'   => 10,
        'min_score'   => 60,
        'color'       => '#eab308',
        'icon'        => 'zap',
        'risk_level'  => 'High',
        'urgency_label' => 'Need money in 1-2 weeks'
    ),
    'swing' => array(
        'name'        => 'Swing Trades',
        'subtitle'    => '1-3 Months',
        'description' => 'Trend-following positions. Moderate risk with room for the trade to develop.',
        'tp_pct'      => 20,
        'sl_pct'      => 8,
        'hold_days'   => 60,
        'min_score'   => 55,
        'color'       => '#6366f1',
        'icon'        => 'trending-up',
        'risk_level'  => 'Medium',
        'urgency_label' => 'Can wait 1-3 months'
    ),
    'longterm' => array(
        'name'        => 'Long-Term Growth',
        'subtitle'    => '6-12 Months',
        'description' => 'Blue chip quality stocks. Wide stops, buy-and-hold mentality. Compound wealth over time.',
        'tp_pct'      => 40,
        'sl_pct'      => 15,
        'hold_days'   => 252,
        'min_score'   => 50,
        'color'       => '#22c55e',
        'icon'        => 'shield',
        'risk_level'  => 'Low',
        'urgency_label' => 'Can wait 6-12 months'
    )
);

function _map_urgency($days) {
    if ($days <= 14) return 'quick';
    if ($days <= 90) return 'swing';
    return 'longterm';
}

// ─── Helper: get latest price ───
function _hp_latest_price($conn, $ticker) {
    $safe = $conn->real_escape_string($ticker);
    $res = $conn->query("SELECT close_price, trade_date FROM daily_prices WHERE ticker='$safe' ORDER BY trade_date DESC LIMIT 1");
    if ($res && $row = $res->fetch_assoc()) return $row;
    return null;
}

// ─── Helper: run mini backtest for a horizon ───
function _hp_run_backtest($conn, $tp_pct, $sl_pct, $max_hold) {
    // Get all picks with price data
    $sql = "SELECT sp.ticker, sp.entry_price, sp.pick_date, sp.algorithm_name
            FROM stock_picks sp
            WHERE sp.entry_price > 0
            ORDER BY sp.pick_date DESC
            LIMIT 500";
    $res = $conn->query($sql);
    if (!$res) return array('total_trades' => 0, 'win_rate' => 0, 'avg_win_pct' => 0, 'avg_loss_pct' => 0, 'total_return_pct' => 0);

    $picks = array();
    while ($row = $res->fetch_assoc()) {
        $picks[] = $row;
    }

    $total = 0;
    $wins = 0;
    $losses = 0;
    $sum_win = 0;
    $sum_loss = 0;
    $total_return = 0;
    $best_trade = -999;
    $worst_trade = 999;

    foreach ($picks as $pick) {
        $ticker = $pick['ticker'];
        $entry = (float)$pick['entry_price'];
        $pdate = $pick['pick_date'];
        if ($entry <= 0) continue;

        $safe_t = $conn->real_escape_string($ticker);
        $safe_d = $conn->real_escape_string($pdate);
        $lim = $max_hold + 5;
        $price_res = $conn->query("SELECT high_price, low_price, close_price FROM daily_prices WHERE ticker='$safe_t' AND trade_date >= '$safe_d' ORDER BY trade_date ASC LIMIT $lim");
        if (!$price_res || $price_res->num_rows < 2) continue;

        $tp_price = $entry * (1 + $tp_pct / 100);
        $sl_price = $entry * (1 - $sl_pct / 100);
        $day_count = 0;
        $exit_price = $entry;
        $exit_reason = 'end_of_data';

        while ($day = $price_res->fetch_assoc()) {
            $day_count++;
            $hi = (float)$day['high_price'];
            $lo = (float)$day['low_price'];
            $cl = (float)$day['close_price'];

            if ($lo <= $sl_price && $sl_pct < 999) {
                $exit_price = $sl_price;
                $exit_reason = 'stop_loss';
                break;
            }
            if ($hi >= $tp_price && $tp_pct < 999) {
                $exit_price = $tp_price;
                $exit_reason = 'take_profit';
                break;
            }
            if ($day_count >= $max_hold) {
                $exit_price = $cl;
                $exit_reason = 'max_hold';
                break;
            }
            $exit_price = $cl;
        }

        $ret_pct = ($entry > 0) ? (($exit_price - $entry) / $entry * 100) : 0;
        $total++;
        $total_return += $ret_pct;

        if ($ret_pct > $best_trade) $best_trade = $ret_pct;
        if ($ret_pct < $worst_trade) $worst_trade = $ret_pct;

        if ($ret_pct >= 0) {
            $wins++;
            $sum_win += $ret_pct;
        } else {
            $losses++;
            $sum_loss += abs($ret_pct);
        }
    }

    $win_rate = ($total > 0) ? round($wins / $total * 100, 1) : 0;
    $avg_win = ($wins > 0) ? round($sum_win / $wins, 2) : 0;
    $avg_loss = ($losses > 0) ? round($sum_loss / $losses, 2) : 0;
    $avg_return = ($total > 0) ? round($total_return / $total, 2) : 0;

    // $1000 projection: expected value per trade * assumed number of trades
    $expected_per_trade = ($win_rate / 100 * $avg_win) - ((100 - $win_rate) / 100 * $avg_loss);
    $projection = round(1000 * (1 + $expected_per_trade * 6 / 100), 2); // 6 trades worth
    $best_case = round(1000 * (1 + $avg_win * 6 / 100), 2);
    $worst_case = round(1000 * (1 - $avg_loss * 3 / 100), 2);

    return array(
        'total_trades'     => $total,
        'wins'             => $wins,
        'losses'           => $losses,
        'win_rate'         => $win_rate,
        'avg_win_pct'      => $avg_win,
        'avg_loss_pct'     => $avg_loss,
        'avg_return_pct'   => $avg_return,
        'best_trade_pct'   => ($total > 0) ? round($best_trade, 2) : 0,
        'worst_trade_pct'  => ($total > 0) ? round($worst_trade, 2) : 0,
        'projection_1000'  => array(
            'expected' => $projection,
            'best_case' => $best_case,
            'worst_case' => $worst_case
        )
    );
}

// ─── Helper: get top picks for a horizon ───
function _hp_get_picks($conn, $key, $profile) {
    $min_score = (int)$profile['min_score'];
    $picks = array();

    // Algorithm preference by horizon
    if ($key === 'quick') {
        $order = "CASE
            WHEN sp.algorithm_name LIKE '%Momentum%' THEN 1
            WHEN sp.algorithm_name LIKE '%Scalp%' THEN 2
            WHEN sp.algorithm_name LIKE '%Day%' THEN 3
            WHEN sp.algorithm_name LIKE '%Technical%' THEN 4
            ELSE 5
        END, sp.score DESC, sp.pick_date DESC";
    } elseif ($key === 'swing') {
        $order = "CASE
            WHEN sp.algorithm_name LIKE '%Swing%' THEN 1
            WHEN sp.algorithm_name LIKE '%CAN SLIM%' THEN 2
            WHEN sp.algorithm_name LIKE '%Composite%' THEN 3
            WHEN sp.algorithm_name LIKE '%Momentum%' THEN 4
            ELSE 5
        END, sp.score DESC, sp.pick_date DESC";
    } else {
        $order = "CASE
            WHEN sp.algorithm_name LIKE '%Blue Chip%' THEN 1
            WHEN sp.algorithm_name LIKE '%Dividend%' THEN 2
            WHEN sp.algorithm_name LIKE '%Quality%' THEN 3
            WHEN sp.algorithm_name LIKE '%ETF%' THEN 4
            WHEN sp.algorithm_name LIKE '%Growth%' THEN 5
            ELSE 6
        END, sp.score DESC, sp.pick_date DESC";
    }

    $sql = "SELECT sp.*, s.company_name
            FROM stock_picks sp
            LEFT JOIN stocks s ON sp.ticker = s.ticker
            WHERE sp.entry_price > 0 AND sp.score >= $min_score
            ORDER BY $order
            LIMIT 60";
    $res = $conn->query($sql);
    if (!$res) return $picks;

    $seen = array();
    $count = 0;

    while ($row = $res->fetch_assoc()) {
        $ticker = $row['ticker'];
        if (isset($seen[$ticker])) continue;

        $latest = _hp_latest_price($conn, $ticker);
        if (!$latest) continue;

        $entry = (float)$row['entry_price'];
        $current = (float)$latest['close_price'];
        if ($entry <= 0 || $current <= 0) continue;

        // Skip stale price data
        $age_days = (int)((time() - strtotime($latest['trade_date'])) / 86400);
        if ($age_days > 10) continue;

        $tp_price = round($entry * (1 + $profile['tp_pct'] / 100), 2);
        $sl_price = round($entry * (1 - $profile['sl_pct'] / 100), 2);
        $current_return = round(($current - $entry) / $entry * 100, 2);

        $status = 'active';
        if ($current >= $tp_price) $status = 'tp_hit';
        if ($current <= $sl_price) $status = 'sl_hit';

        $dist_tp = round(($tp_price - $current) / $current * 100, 2);
        $dist_sl = round(($current - $sl_price) / $current * 100, 2);

        $risk = $entry - $sl_price;
        $reward = $tp_price - $entry;
        $rr = ($risk > 0) ? round($reward / $risk, 2) : 0;

        $picks[] = array(
            'ticker'         => $ticker,
            'company_name'   => isset($row['company_name']) ? $row['company_name'] : '',
            'algorithm'      => $row['algorithm_name'],
            'pick_date'      => $row['pick_date'],
            'score'          => (int)$row['score'],
            'rating'         => isset($row['rating']) ? $row['rating'] : '',
            'risk_level'     => isset($row['risk_level']) ? $row['risk_level'] : '',
            'entry_price'    => $entry,
            'current_price'  => $current,
            'price_date'     => $latest['trade_date'],
            'target'         => $tp_price,
            'stop_loss'      => $sl_price,
            'current_return' => $current_return,
            'dist_to_tp'     => $dist_tp,
            'dist_to_sl'     => $dist_sl,
            'risk_reward'    => $rr,
            'status'         => $status
        );

        $seen[$ticker] = true;
        $count++;
        if ($count >= 6) break;
    }

    return $picks;
}

// ─── Build response ───
$response = array(
    'ok' => true,
    'generated_at' => $now,
    'horizons' => array()
);

foreach ($profiles as $key => $profile) {
    $backtest = _hp_run_backtest($conn, $profile['tp_pct'], $profile['sl_pct'], $profile['hold_days']);
    $picks = _hp_get_picks($conn, $key, $profile);

    $response['horizons'][] = array(
        'key'           => $key,
        'name'          => $profile['name'],
        'subtitle'      => $profile['subtitle'],
        'description'   => $profile['description'],
        'tp_pct'        => $profile['tp_pct'],
        'sl_pct'        => $profile['sl_pct'],
        'hold_days'     => $profile['hold_days'],
        'risk_level'    => $profile['risk_level'],
        'color'         => $profile['color'],
        'icon'          => $profile['icon'],
        'urgency_label' => $profile['urgency_label'],
        'backtest'      => $backtest,
        'picks'         => $picks,
        'pick_count'    => count($picks)
    );
}

// Handle urgency
if ($urgency_days > 0) {
    $response['urgency_days'] = $urgency_days;
    $response['recommended_horizon'] = _map_urgency($urgency_days);
}

// ─── Save to cache ───
$json_data = json_encode($response);
$safe_data = $conn->real_escape_string($json_data);
$safe_key = $conn->real_escape_string($cache_key);
$conn->query("DELETE FROM report_cache WHERE cache_key='$safe_key'");
$conn->query("INSERT INTO report_cache (cache_key, cache_data, updated_at) VALUES ('$safe_key', '$safe_data', '$now')");

$response['from_cache'] = false;
echo json_encode($response);
$conn->close();
?>
