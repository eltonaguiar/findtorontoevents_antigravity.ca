<?php
/**
 * Data listing endpoint for crypto pairs portfolio dashboard.
 * PHP 5.2 compatible.
 *
 * Types: picks, algorithms, portfolios, backtests, scenarios, stats, prices, algo_performance
 */
require_once dirname(__FILE__) . '/db_connect.php';

$type = isset($_GET['type']) ? trim($_GET['type']) : 'stats';
$response = array('ok' => true, 'type' => $type);

if ($type === 'picks') {
    $algo_filter = isset($_GET['algorithm']) ? trim($_GET['algorithm']) : '';
    $dir_filter  = isset($_GET['direction']) ? trim(strtoupper($_GET['direction'])) : '';
    $where = '';
    $conditions = array();
    if ($algo_filter !== '') {
        $safe = $conn->real_escape_string($algo_filter);
        $conditions[] = "fp.algorithm_name = '$safe'";
    }
    if ($dir_filter !== '' && ($dir_filter === 'LONG' || $dir_filter === 'SHORT')) {
        $conditions[] = "fp.direction = '$dir_filter'";
    }
    if (count($conditions) > 0) {
        $where = ' WHERE ' . implode(' AND ', $conditions);
    }
    $sql = "SELECT fp.*, p.pair_name, p.base_asset, p.quote_asset, p.category
            FROM cr_pair_picks fp
            LEFT JOIN cr_pairs p ON fp.symbol = p.symbol
            $where
            ORDER BY fp.score DESC, fp.pick_date DESC";
    $res = $conn->query($sql);
    $picks = array();
    if ($res) { while ($row = $res->fetch_assoc()) $picks[] = $row; }
    $response['picks'] = $picks;
    $response['count'] = count($picks);

} elseif ($type === 'algorithms') {
    $sql = "SELECT a.*, COUNT(fp.id) as pick_count
            FROM cr_algorithms a
            LEFT JOIN cr_pair_picks fp ON a.name = fp.algorithm_name
            GROUP BY a.id ORDER BY a.family, a.name";
    $res = $conn->query($sql);
    $algos = array();
    if ($res) { while ($row = $res->fetch_assoc()) $algos[] = $row; }
    $response['algorithms'] = $algos;

} elseif ($type === 'portfolios') {
    $res = $conn->query("SELECT * FROM cr_portfolios ORDER BY strategy_type, name");
    $portfolios = array();
    if ($res) { while ($row = $res->fetch_assoc()) $portfolios[] = $row; }
    $response['portfolios'] = $portfolios;

} elseif ($type === 'backtests') {
    $limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 50;
    if ($limit < 1) $limit = 50; if ($limit > 200) $limit = 200;
    $res = $conn->query("SELECT * FROM cr_backtest_results ORDER BY created_at DESC LIMIT $limit");
    $backtests = array();
    if ($res) { while ($row = $res->fetch_assoc()) $backtests[] = $row; }
    $response['backtests'] = $backtests;

} elseif ($type === 'scenarios') {
    $response['scenarios'] = array(
        array('key' => 'hodl_1y',           'name' => 'HODL 1 Year',            'tp' => 999, 'sl' => 999, 'hold' => 365),
        array('key' => 'hodl_6m',           'name' => 'HODL 6 Months',          'tp' => 999, 'sl' => 999, 'hold' => 180),
        array('key' => 'dca_weekly',        'name' => 'DCA Weekly Style',       'tp' => 50,  'sl' => 999, 'hold' => 365),
        array('key' => 'dca_monthly',       'name' => 'DCA Monthly Style',      'tp' => 30,  'sl' => 999, 'hold' => 365),
        array('key' => 'swing_20pct',       'name' => 'Swing Trade 20%',        'tp' => 20,  'sl' => 10,  'hold' => 30),
        array('key' => 'swing_50pct',       'name' => 'Swing Trade 50%',        'tp' => 50,  'sl' => 20,  'hold' => 60),
        array('key' => 'scalp_5pct',        'name' => 'Scalp 5%',              'tp' => 5,   'sl' => 3,   'hold' => 3),
        array('key' => 'aggressive_100pct', 'name' => 'Aggressive 100% Target', 'tp' => 100, 'sl' => 25,  'hold' => 90),
        array('key' => 'conservative_btc',  'name' => 'Conservative BTC',       'tp' => 15,  'sl' => 8,   'hold' => 120),
        array('key' => 'altcoin_rotation',  'name' => 'Altcoin Rotation',       'tp' => 25,  'sl' => 15,  'hold' => 30)
    );

} elseif ($type === 'prices') {
    $symbol = isset($_GET['symbol']) ? trim(strtoupper($_GET['symbol'])) : '';
    if ($symbol === '') {
        $response['ok'] = false;
        $response['error'] = 'symbol parameter required';
    } else {
        $safe = $conn->real_escape_string($symbol);
        $res = $conn->query("SELECT price_date, open, high, low, close, volume FROM cr_price_history WHERE symbol='$safe' ORDER BY price_date ASC");
        $prices = array();
        if ($res) { while ($row = $res->fetch_assoc()) $prices[] = $row; }
        $response['symbol'] = $symbol;
        $response['prices'] = $prices;
        $response['count'] = count($prices);
    }

} elseif ($type === 'algo_performance') {
    $res = $conn->query("SELECT * FROM cr_algo_performance ORDER BY win_rate DESC");
    $perfs = array();
    if ($res) { while ($row = $res->fetch_assoc()) $perfs[] = $row; }
    $response['performance'] = $perfs;

} elseif ($type === 'stats') {
    $stats = array();

    $res = $conn->query("SELECT COUNT(*) as c FROM cr_pairs");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_pairs'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(*) as c FROM cr_pair_picks");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_picks'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(*) as c FROM cr_price_history");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_price_records'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(*) as c FROM cr_backtest_results");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_backtests'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(DISTINCT algorithm_name) as c FROM cr_pair_picks");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['active_algorithms'] = (int)$row['c'];

    $res = $conn->query("SELECT MIN(pick_date) as mn, MAX(pick_date) as mx FROM cr_pair_picks");
    if ($res) {
        $row = $res->fetch_assoc();
        $stats['pick_date_range'] = array('earliest' => $row['mn'], 'latest' => $row['mx']);
    }

    $res = $conn->query("SELECT MIN(price_date) as mn, MAX(price_date) as mx FROM cr_price_history");
    if ($res) {
        $row = $res->fetch_assoc();
        $stats['price_date_range'] = array('earliest' => $row['mn'], 'latest' => $row['mx']);
    }

    // Direction breakdown
    $dir_breakdown = array();
    $res = $conn->query("SELECT direction, COUNT(*) as cnt FROM cr_pair_picks GROUP BY direction ORDER BY cnt DESC");
    if ($res) { while ($row = $res->fetch_assoc()) $dir_breakdown[] = $row; }
    $stats['direction_breakdown'] = $dir_breakdown;

    $algo_breakdown = array();
    $res = $conn->query("SELECT algorithm_name, COUNT(*) as cnt, AVG(score) as avg_score
                         FROM cr_pair_picks GROUP BY algorithm_name ORDER BY cnt DESC");
    if ($res) { while ($row = $res->fetch_assoc()) $algo_breakdown[] = $row; }
    $stats['algorithm_breakdown'] = $algo_breakdown;

    // Category breakdown
    $cat_breakdown = array();
    $res = $conn->query("SELECT p.category, COUNT(*) as cnt
                         FROM cr_pair_picks fp JOIN cr_pairs p ON fp.symbol = p.symbol
                         GROUP BY p.category ORDER BY cnt DESC");
    if ($res) { while ($row = $res->fetch_assoc()) $cat_breakdown[] = $row; }
    $stats['category_breakdown'] = $cat_breakdown;

    $response['stats'] = $stats;

} else {
    $response['ok'] = false;
    $response['error'] = 'Unknown type. Use: picks, algorithms, portfolios, backtests, scenarios, stats, prices, algo_performance';
}

echo json_encode($response);
$conn->close();
?>
