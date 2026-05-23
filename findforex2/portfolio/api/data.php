<?php
/**
 * Data listing endpoint for Forex Portfolio dashboard.
 * PHP 5.2 compatible.
 *
 * Types: picks, algorithms, portfolios, backtests, scenarios, stats, prices
 */
require_once dirname(__FILE__) . '/db_connect.php';

$type = isset($_GET['type']) ? trim($_GET['type']) : 'stats';
$response = array('ok' => true, 'type' => $type);

if ($type === 'picks') {
    $algo_filter = isset($_GET['algorithm']) ? trim($_GET['algorithm']) : '';
    $where = '';
    if ($algo_filter !== '') {
        $safe = $conn->real_escape_string($algo_filter);
        $where = " WHERE fp.algorithm_name = '$safe'";
    }
    $sql = "SELECT fp.*, p.base_currency, p.quote_currency, p.category, p.pip_value
            FROM fxp_pair_picks fp
            LEFT JOIN fxp_pairs p ON fp.symbol = p.symbol
            $where
            ORDER BY fp.score DESC, fp.pick_date DESC";
    $res = $conn->query($sql);
    $picks = array();
    if ($res) { while ($row = $res->fetch_assoc()) $picks[] = $row; }
    $response['picks'] = $picks;
    $response['count'] = count($picks);

} elseif ($type === 'algorithms') {
    $sql = "SELECT a.*, COUNT(fp.id) as pick_count
            FROM fxp_algorithms a
            LEFT JOIN fxp_pair_picks fp ON a.name = fp.algorithm_name
            GROUP BY a.id ORDER BY a.family, a.name";
    $res = $conn->query($sql);
    $algos = array();
    if ($res) { while ($row = $res->fetch_assoc()) $algos[] = $row; }
    $response['algorithms'] = $algos;

} elseif ($type === 'portfolios') {
    $res = $conn->query("SELECT * FROM fxp_portfolios ORDER BY strategy_type, name");
    $portfolios = array();
    if ($res) { while ($row = $res->fetch_assoc()) $portfolios[] = $row; }
    $response['portfolios'] = $portfolios;

} elseif ($type === 'backtests') {
    $limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 50;
    if ($limit < 1) $limit = 50; if ($limit > 200) $limit = 200;
    $res = $conn->query("SELECT * FROM fxp_backtest_results ORDER BY created_at DESC LIMIT $limit");
    $backtests = array();
    if ($res) { while ($row = $res->fetch_assoc()) $backtests[] = $row; }
    $response['backtests'] = $backtests;

} elseif ($type === 'scenarios') {
    $response['scenarios'] = array(
        array('key' => 'scalp_10pip',    'name' => 'Scalp 10 Pips',      'tp' => 10,  'sl' => 8,   'hold' => 1),
        array('key' => 'scalp_20pip',    'name' => 'Scalp 20 Pips',      'tp' => 20,  'sl' => 12,  'hold' => 1),
        array('key' => 'day_50pip',      'name' => 'Day Trade 50 Pips',   'tp' => 50,  'sl' => 30,  'hold' => 1),
        array('key' => 'day_100pip',     'name' => 'Day Trade 100 Pips',  'tp' => 100, 'sl' => 50,  'hold' => 3),
        array('key' => 'swing_200pip',   'name' => 'Swing 200 Pips',     'tp' => 200, 'sl' => 80,  'hold' => 10),
        array('key' => 'swing_500pip',   'name' => 'Swing 500 Pips',     'tp' => 500, 'sl' => 150, 'hold' => 30),
        array('key' => 'carry_long',     'name' => 'Carry Trade Long',   'tp' => 300, 'sl' => 200, 'hold' => 60),
        array('key' => 'trend_follow',   'name' => 'Trend Following',    'tp' => 400, 'sl' => 120, 'hold' => 30),
        array('key' => 'conservative',   'name' => 'Conservative',       'tp' => 80,  'sl' => 40,  'hold' => 14),
        array('key' => 'aggressive',     'name' => 'Aggressive',         'tp' => 250, 'sl' => 60,  'hold' => 14)
    );

} elseif ($type === 'prices') {
    $symbol = isset($_GET['symbol']) ? trim(strtoupper($_GET['symbol'])) : '';
    if ($symbol === '') {
        $response['ok'] = false;
        $response['error'] = 'symbol parameter required';
    } else {
        $safe = $conn->real_escape_string($symbol);
        $res = $conn->query("SELECT price_date, open_price, high_price, low_price, close_price, volume FROM fxp_price_history WHERE symbol='$safe' ORDER BY price_date ASC");
        $prices = array();
        if ($res) { while ($row = $res->fetch_assoc()) $prices[] = $row; }
        $response['symbol'] = $symbol;
        $response['prices'] = $prices;
        $response['count'] = count($prices);
    }

} elseif ($type === 'algo_performance') {
    $res = $conn->query("SELECT * FROM fxp_algo_performance ORDER BY win_rate DESC");
    $perfs = array();
    if ($res) { while ($row = $res->fetch_assoc()) $perfs[] = $row; }
    $response['performance'] = $perfs;

} elseif ($type === 'stats') {
    $stats = array();

    $res = $conn->query("SELECT COUNT(*) as c FROM fxp_pairs");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_pairs'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(*) as c FROM fxp_pair_picks");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_picks'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(*) as c FROM fxp_price_history");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_price_records'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(*) as c FROM fxp_backtest_results");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_backtests'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(DISTINCT algorithm_name) as c FROM fxp_pair_picks");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['active_algorithms'] = (int)$row['c'];

    $res = $conn->query("SELECT MIN(pick_date) as mn, MAX(pick_date) as mx FROM fxp_pair_picks");
    if ($res) {
        $row = $res->fetch_assoc();
        $stats['pick_date_range'] = array('earliest' => $row['mn'], 'latest' => $row['mx']);
    }

    $res = $conn->query("SELECT MIN(price_date) as mn, MAX(price_date) as mx FROM fxp_price_history");
    if ($res) {
        $row = $res->fetch_assoc();
        $stats['price_date_range'] = array('earliest' => $row['mn'], 'latest' => $row['mx']);
    }

    $algo_breakdown = array();
    $res = $conn->query("SELECT algorithm_name, COUNT(*) as cnt, AVG(score) as avg_score
                         FROM fxp_pair_picks GROUP BY algorithm_name ORDER BY cnt DESC");
    if ($res) { while ($row = $res->fetch_assoc()) $algo_breakdown[] = $row; }
    $stats['algorithm_breakdown'] = $algo_breakdown;

    // Category breakdown
    $cat_breakdown = array();
    $res = $conn->query("SELECT p.category, COUNT(*) as cnt
                         FROM fxp_pair_picks fp JOIN fxp_pairs p ON fp.symbol = p.symbol
                         GROUP BY p.category ORDER BY cnt DESC");
    if ($res) { while ($row = $res->fetch_assoc()) $cat_breakdown[] = $row; }
    $stats['category_breakdown'] = $cat_breakdown;

    // Direction breakdown
    $dir_breakdown = array();
    $res = $conn->query("SELECT direction, COUNT(*) as cnt FROM fxp_pair_picks GROUP BY direction ORDER BY cnt DESC");
    if ($res) { while ($row = $res->fetch_assoc()) $dir_breakdown[] = $row; }
    $stats['direction_breakdown'] = $dir_breakdown;

    $response['stats'] = $stats;

} else {
    $response['ok'] = false;
    $response['error'] = 'Unknown type. Use: picks, algorithms, portfolios, backtests, scenarios, stats, prices, algo_performance';
}

echo json_encode($response);
$conn->close();
?>
