<?php
/**
 * Data listing endpoint for mutual funds portfolio2 dashboard.
 * PHP 5.2 compatible.
 *
 * Types: picks, algorithms, portfolios, backtests, scenarios, stats, navs, algo_performance
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
    $sql = "SELECT fp.*, f.fund_name, f.fund_family, f.category, f.expense_ratio, f.morningstar_rating
            FROM mf2_fund_picks fp
            LEFT JOIN mf2_funds f ON fp.symbol = f.symbol
            $where
            ORDER BY fp.score DESC, fp.pick_date DESC";
    $res = $conn->query($sql);
    $picks = array();
    if ($res) { while ($row = $res->fetch_assoc()) $picks[] = $row; }
    $response['picks'] = $picks;
    $response['count'] = count($picks);

} elseif ($type === 'algorithms') {
    $sql = "SELECT a.*, COUNT(fp.id) as pick_count
            FROM mf2_algorithms a
            LEFT JOIN mf2_fund_picks fp ON a.name = fp.algorithm_name
            GROUP BY a.id ORDER BY a.family, a.name";
    $res = $conn->query($sql);
    $algos = array();
    if ($res) { while ($row = $res->fetch_assoc()) $algos[] = $row; }
    $response['algorithms'] = $algos;

} elseif ($type === 'portfolios') {
    $res = $conn->query("SELECT * FROM mf2_portfolios ORDER BY strategy_type, name");
    $portfolios = array();
    if ($res) { while ($row = $res->fetch_assoc()) $portfolios[] = $row; }
    $response['portfolios'] = $portfolios;

} elseif ($type === 'backtests') {
    $limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 50;
    if ($limit < 1) $limit = 50; if ($limit > 200) $limit = 200;
    $res = $conn->query("SELECT * FROM mf2_backtest_results ORDER BY created_at DESC LIMIT $limit");
    $backtests = array();
    if ($res) { while ($row = $res->fetch_assoc()) $backtests[] = $row; }
    $response['backtests'] = $backtests;

} elseif ($type === 'scenarios') {
    $response['scenarios'] = array(
        array('key' => 'short_tactical',     'name' => 'Short Tactical (1 Month)',   'target' => 5,   'sl' => 3,  'hold' => 21),
        array('key' => 'momentum_monthly',   'name' => 'Monthly Momentum',           'target' => 8,   'sl' => 5,  'hold' => 30),
        array('key' => 'swing_quarter',      'name' => 'Quarterly Swing',            'target' => 10,  'sl' => 8,  'hold' => 63),
        array('key' => 'conservative_hold',  'name' => 'Conservative Hold (6M)',     'target' => 12,  'sl' => 5,  'hold' => 126),
        array('key' => 'growth_6m',          'name' => 'Growth (6 Months)',          'target' => 20,  'sl' => 10, 'hold' => 126),
        array('key' => 'buy_hold_1y',        'name' => 'Buy & Hold (1 Year)',        'target' => 999, 'sl' => 999,'hold' => 252),
        array('key' => 'income_steady',      'name' => 'Income Steady',             'target' => 6,   'sl' => 3,  'hold' => 180),
        array('key' => 'aggressive_rotation','name' => 'Aggressive Rotation',       'target' => 15,  'sl' => 8,  'hold' => 42),
        array('key' => 'value_patient',      'name' => 'Patient Value',             'target' => 15,  'sl' => 12, 'hold' => 189),
        array('key' => 'balanced_moderate',  'name' => 'Balanced Moderate',         'target' => 10,  'sl' => 7,  'hold' => 84)
    );

} elseif ($type === 'navs') {
    $symbol = isset($_GET['symbol']) ? trim(strtoupper($_GET['symbol'])) : '';
    if ($symbol === '') {
        $response['ok'] = false;
        $response['error'] = 'symbol parameter required';
    } else {
        $safe = $conn->real_escape_string($symbol);
        $res = $conn->query("SELECT nav_date, nav, daily_return_pct FROM mf2_nav_history WHERE symbol='$safe' ORDER BY nav_date ASC");
        $navs = array();
        if ($res) { while ($row = $res->fetch_assoc()) $navs[] = $row; }
        $response['symbol'] = $symbol;
        $response['navs'] = $navs;
        $response['count'] = count($navs);
    }

} elseif ($type === 'algo_performance') {
    $res = $conn->query("SELECT * FROM mf2_algo_performance ORDER BY win_rate DESC");
    $perfs = array();
    if ($res) { while ($row = $res->fetch_assoc()) $perfs[] = $row; }
    $response['performance'] = $perfs;

} elseif ($type === 'stats') {
    $stats = array();

    $res = $conn->query("SELECT COUNT(*) as c FROM mf2_funds");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_funds'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(*) as c FROM mf2_fund_picks");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_picks'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(*) as c FROM mf2_nav_history");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_nav_records'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(*) as c FROM mf2_backtest_results");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_backtests'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(DISTINCT algorithm_name) as c FROM mf2_fund_picks");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['active_algorithms'] = (int)$row['c'];

    $res = $conn->query("SELECT MIN(pick_date) as mn, MAX(pick_date) as mx FROM mf2_fund_picks");
    if ($res) {
        $row = $res->fetch_assoc();
        $stats['pick_date_range'] = array('earliest' => $row['mn'], 'latest' => $row['mx']);
    }

    $res = $conn->query("SELECT MIN(nav_date) as mn, MAX(nav_date) as mx FROM mf2_nav_history");
    if ($res) {
        $row = $res->fetch_assoc();
        $stats['nav_date_range'] = array('earliest' => $row['mn'], 'latest' => $row['mx']);
    }

    $algo_breakdown = array();
    $res = $conn->query("SELECT algorithm_name, COUNT(*) as cnt, AVG(score) as avg_score
                         FROM mf2_fund_picks GROUP BY algorithm_name ORDER BY cnt DESC");
    if ($res) { while ($row = $res->fetch_assoc()) $algo_breakdown[] = $row; }
    $stats['algorithm_breakdown'] = $algo_breakdown;

    // Category breakdown
    $cat_breakdown = array();
    $res = $conn->query("SELECT f.category, COUNT(*) as cnt, AVG(f.expense_ratio) as avg_expense
                         FROM mf2_fund_picks fp JOIN mf2_funds f ON fp.symbol = f.symbol
                         GROUP BY f.category ORDER BY cnt DESC");
    if ($res) { while ($row = $res->fetch_assoc()) $cat_breakdown[] = $row; }
    $stats['category_breakdown'] = $cat_breakdown;

    $response['stats'] = $stats;

} else {
    $response['ok'] = false;
    $response['error'] = 'Unknown type. Use: picks, algorithms, portfolios, backtests, scenarios, stats, navs, algo_performance';
}

echo json_encode($response);
$conn->close();
?>
