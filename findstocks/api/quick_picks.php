<?php
/**
 * Quick Picks API - Curated stock picks for day trading, swing trading, and long-term investing.
 * Each pick includes entry price, take profit, stop loss, and risk:reward ratio.
 * PHP 5.2 compatible.
 *
 * Usage:
 *   GET quick_picks.php                     — all categories
 *   GET quick_picks.php?category=day        — day trading picks only
 *   GET quick_picks.php?category=swing      — swing trading picks only
 *   GET quick_picks.php?category=longterm   — long-term picks only
 *   GET quick_picks.php?urgency=14          — picks for "I need returns in 14 days"
 */
require_once dirname(__FILE__) . '/db_connect.php';

$category = isset($_GET['category']) ? trim($_GET['category']) : 'all';
$urgency_days = isset($_GET['urgency']) ? (int)$_GET['urgency'] : 0;

$response = array('ok' => true, 'generated_at' => date('Y-m-d H:i:s'));

// ─── Strategy Profiles ───
$profiles = array(
    'day' => array(
        'name'        => 'Day Trade',
        'description' => 'Quick 1-2 day holds. High volatility picks with tight stops.',
        'tp_pct'      => 5,
        'sl_pct'      => 3,
        'hold_days'   => 2,
        'min_score'   => 60,
        'risk_reward' => 1.67,
        'urgency'     => 'Need money in 1-2 days',
        'icon'        => 'zap',
        'color'       => '#eab308'
    ),
    'swing' => array(
        'name'        => 'Swing Trade',
        'description' => '1-4 week holds. Trend-following with moderate risk.',
        'tp_pct'      => 15,
        'sl_pct'      => 7,
        'hold_days'   => 20,
        'min_score'   => 55,
        'risk_reward' => 2.14,
        'urgency'     => 'Need money in 2-4 weeks',
        'icon'        => 'trending-up',
        'color'       => '#6366f1'
    ),
    'longterm' => array(
        'name'        => 'Long-Term Investment',
        'description' => '3-12 month holds. Blue chip quality with wide stops.',
        'tp_pct'      => 40,
        'sl_pct'      => 15,
        'hold_days'   => 180,
        'min_score'   => 50,
        'risk_reward' => 2.67,
        'urgency'     => 'Can wait 3-12 months',
        'icon'        => 'shield',
        'color'       => '#22c55e'
    )
);

// ─── Map urgency days to category ───
if ($urgency_days > 0) {
    if ($urgency_days <= 3) {
        $category = 'day';
    } elseif ($urgency_days <= 30) {
        $category = 'swing';
    } else {
        $category = 'longterm';
    }
    $response['urgency_mapped'] = $category;
}

// ─── Helper: Calculate current return % ───
function _qp_get_latest_price($conn, $ticker) {
    $safe = $conn->real_escape_string($ticker);
    $sql = "SELECT close_price, trade_date FROM daily_prices
            WHERE ticker='$safe' ORDER BY trade_date DESC LIMIT 1";
    $res = $conn->query($sql);
    if ($res && $row = $res->fetch_assoc()) {
        return $row;
    }
    return null;
}

// ─── Helper: Get volatility (avg daily range %) ───
function _qp_get_volatility($conn, $ticker) {
    $safe = $conn->real_escape_string($ticker);
    $sql = "SELECT AVG(ABS(high_price - low_price) / NULLIF(open_price, 0) * 100) as avg_range
            FROM daily_prices WHERE ticker='$safe'
            ORDER BY trade_date DESC LIMIT 30";
    $res = $conn->query($sql);
    if ($res && $row = $res->fetch_assoc()) {
        return round((float)$row['avg_range'], 2);
    }
    return 0;
}

// ─── Helper: Get recent price trend ───
function _qp_get_trend($conn, $ticker, $days) {
    $safe = $conn->real_escape_string($ticker);
    $sql = "SELECT close_price FROM daily_prices
            WHERE ticker='$safe' ORDER BY trade_date DESC LIMIT " . (int)$days;
    $res = $conn->query($sql);
    $prices = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $prices[] = (float)$row['close_price'];
        }
    }
    if (count($prices) < 2) return 0;
    $latest = $prices[0];
    $oldest = $prices[count($prices) - 1];
    if ($oldest <= 0) return 0;
    return round(($latest - $oldest) / $oldest * 100, 2);
}

// ─── Build picks for a category ───
function build_picks($conn, $profile_key, $profile) {
    $picks = array();

    // Determine which algorithms to prefer per category
    $algo_boost = '';
    if ($profile_key === 'day') {
        // Day trading: prefer momentum and scalp algos
        $algo_boost = " ORDER BY
            CASE
                WHEN sp.algorithm_name LIKE '%Momentum%' THEN 1
                WHEN sp.algorithm_name LIKE '%Scalp%' THEN 2
                WHEN sp.algorithm_name LIKE '%Day%' THEN 3
                ELSE 4
            END,
            sp.score DESC, sp.pick_date DESC";
    } elseif ($profile_key === 'swing') {
        // Swing: prefer trend and swing algos
        $algo_boost = " ORDER BY
            CASE
                WHEN sp.algorithm_name LIKE '%Swing%' THEN 1
                WHEN sp.algorithm_name LIKE '%Trend%' THEN 2
                WHEN sp.algorithm_name LIKE '%Momentum%' THEN 3
                ELSE 4
            END,
            sp.score DESC, sp.pick_date DESC";
    } else {
        // Long-term: prefer blue chip, value, growth
        $algo_boost = " ORDER BY
            CASE
                WHEN sp.algorithm_name LIKE '%Blue Chip%' THEN 1
                WHEN sp.algorithm_name LIKE '%Value%' THEN 2
                WHEN sp.algorithm_name LIKE '%Growth%' THEN 3
                WHEN sp.algorithm_name LIKE '%ETF%' THEN 4
                WHEN sp.algorithm_name LIKE '%Sector%' THEN 5
                ELSE 6
            END,
            sp.score DESC, sp.pick_date DESC";
    }

    // Fetch recent picks with good scores
    $min_score = (int)$profile['min_score'];
    $sql = "SELECT sp.*, s.company_name
            FROM stock_picks sp
            LEFT JOIN stocks s ON sp.ticker = s.ticker
            WHERE sp.entry_price > 0 AND sp.score >= $min_score
            $algo_boost
            LIMIT 50";

    $res = $conn->query($sql);
    if (!$res) return $picks;

    $seen_tickers = array();
    $count = 0;
    $max_picks = 8;

    while ($row = $res->fetch_assoc()) {
        // Skip duplicates (only 1 pick per ticker)
        $ticker = $row['ticker'];
        if (isset($seen_tickers[$ticker])) continue;

        // Get current price
        $latest = _qp_get_latest_price($conn, $ticker);
        if (!$latest) continue;

        $entry_price = (float)$row['entry_price'];
        $current_price = (float)$latest['close_price'];
        $price_date = $latest['trade_date'];

        // Skip if price data is too old (more than 7 days)
        $date_diff = (int)((time() - strtotime($price_date)) / 86400);
        if ($date_diff > 10) continue;

        // Calculate TP and SL price levels
        $tp_price = round($entry_price * (1 + $profile['tp_pct'] / 100), 2);
        $sl_price = round($entry_price * (1 - $profile['sl_pct'] / 100), 2);

        // Current return
        $current_return = 0;
        if ($entry_price > 0) {
            $current_return = round(($current_price - $entry_price) / $entry_price * 100, 2);
        }

        // Already hit TP or SL?
        $status = 'active';
        if ($current_price >= $tp_price) $status = 'tp_hit';
        if ($current_price <= $sl_price) $status = 'sl_hit';

        // Risk:Reward ratio
        $risk = $entry_price - $sl_price;
        $reward = $tp_price - $entry_price;
        $rr_ratio = ($risk > 0) ? round($reward / $risk, 2) : 0;

        // Distance to TP and SL
        $dist_to_tp = ($current_price > 0) ? round(($tp_price - $current_price) / $current_price * 100, 2) : 0;
        $dist_to_sl = ($current_price > 0) ? round(($current_price - $sl_price) / $current_price * 100, 2) : 0;

        // Get volatility for day trades
        $volatility = 0;
        if ($profile_key === 'day') {
            $volatility = _qp_get_volatility($conn, $ticker);
        }

        // Get trend
        $trend_days = ($profile_key === 'day') ? 5 : (($profile_key === 'swing') ? 20 : 60);
        $trend = _qp_get_trend($conn, $ticker, $trend_days);

        $pick = array(
            'ticker'          => $ticker,
            'company_name'    => isset($row['company_name']) ? $row['company_name'] : '',
            'algorithm'       => $row['algorithm_name'],
            'pick_date'       => $row['pick_date'],
            'entry_price'     => $entry_price,
            'current_price'   => $current_price,
            'price_date'      => $price_date,
            'take_profit'     => $tp_price,
            'stop_loss'       => $sl_price,
            'tp_pct'          => $profile['tp_pct'],
            'sl_pct'          => $profile['sl_pct'],
            'risk_reward'     => $rr_ratio,
            'current_return'  => $current_return,
            'dist_to_tp'      => $dist_to_tp,
            'dist_to_sl'      => $dist_to_sl,
            'status'          => $status,
            'score'           => (int)$row['score'],
            'rating'          => isset($row['rating']) ? $row['rating'] : '',
            'risk_level'      => isset($row['risk_level']) ? $row['risk_level'] : '',
            'hold_days'       => $profile['hold_days'],
            'volatility'      => $volatility,
            'trend'           => $trend
        );

        $picks[] = $pick;
        $seen_tickers[$ticker] = true;
        $count++;
        if ($count >= $max_picks) break;
    }

    return $picks;
}

// ─── Build Response ───
$categories_to_build = array();
if ($category === 'all') {
    $categories_to_build = array('day', 'swing', 'longterm');
} elseif (isset($profiles[$category])) {
    $categories_to_build = array($category);
} else {
    $response['ok'] = false;
    $response['error'] = 'Invalid category. Use: day, swing, longterm, or all';
    echo json_encode($response);
    $conn->close();
    exit;
}

$response['categories'] = array();
foreach ($categories_to_build as $cat) {
    $profile = $profiles[$cat];
    $cat_picks = build_picks($conn, $cat, $profile);

    $response['categories'][] = array(
        'key'         => $cat,
        'name'        => $profile['name'],
        'description' => $profile['description'],
        'tp_pct'      => $profile['tp_pct'],
        'sl_pct'      => $profile['sl_pct'],
        'hold_days'   => $profile['hold_days'],
        'risk_reward' => $profile['risk_reward'],
        'urgency'     => $profile['urgency'],
        'icon'        => $profile['icon'],
        'color'       => $profile['color'],
        'picks'       => $cat_picks,
        'pick_count'  => count($cat_picks)
    );

    // Quick audit log for quick_picks generation (non-pick specific)
    $audit_reasons = 'Generated quick picks for category: ' . $cat;
    $audit_supporting_data = json_encode(array('pick_count' =&gt; count($cat_picks)));
    $audit_pick_details = json_encode($profile);
    $audit_formatted_for_ai = "Review quick picks generation for $cat:\nRationale: " . $audit_reasons . "\nData: " . $audit_supporting_data;

    $safe_reasons = $conn->real_escape_string($audit_reasons);
    $safe_supporting = $conn->real_escape_string($audit_supporting_data);
    $safe_details = $conn->real_escape_string($audit_pick_details);
    $safe_formatted = $conn->real_escape_string($audit_formatted_for_ai);
    $pick_timestamp = date('Y-m-d H:i:s');

    $audit_sql = "INSERT INTO audit_trails 
                  (asset_class, symbol, pick_timestamp, generation_source, reasons, supporting_data, pick_details, formatted_for_ai)
                  VALUES ('STOCKS', 'QUICK_PICKS', '$pick_timestamp', 'quick_picks.php', '$safe_reasons', '$safe_supporting', '$safe_details', '$safe_formatted')";
    $conn->query($audit_sql);
}

// ─── Summary stats ───
$total_picks = 0;
foreach ($response['categories'] as $cat_data) {
    $total_picks = $total_picks + $cat_data['pick_count'];
}
$response['total_picks'] = $total_picks;
$response['profiles'] = $profiles;

echo json_encode($response);
$conn->close();
?>
