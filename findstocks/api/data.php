<?php
/**
 * Data listing endpoint for portfolio dashboard.
 * Returns picks, algorithms, portfolios, backtest history, etc.
 * PHP 5.2 compatible.
 *
 * Usage:
 *   GET .../data.php?type=picks         — list all stock picks
 *   GET .../data.php?type=algorithms    — list algorithms
 *   GET .../data.php?type=portfolios    — list portfolio templates
 *   GET .../data.php?type=backtests     — list saved backtest results
 *   GET .../data.php?type=scenarios     — list predefined scenarios
 *   GET .../data.php?type=stats         — database stats overview
 *   GET .../data.php?type=prices&ticker=AAPL — price history for a ticker
 */
require_once dirname(__FILE__) . '/db_connect.php';

$type = isset($_GET['type']) ? trim($_GET['type']) : 'stats';

$response = array('ok' => true, 'type' => $type);

if ($type === 'picks') {
    // ─── Stock Picks ───
    $algo_filter = isset($_GET['algorithm']) ? trim($_GET['algorithm']) : '';
    $where = '';
    if ($algo_filter !== '') {
        $safe = $conn->real_escape_string($algo_filter);
        $where = " WHERE sp.algorithm_name = '$safe'";
    }
    $sql = "SELECT sp.*, s.company_name
            FROM stock_picks sp
            LEFT JOIN stocks s ON sp.ticker = s.ticker
            $where
            ORDER BY sp.score DESC, sp.pick_date DESC";
    $res = $conn->query($sql);
    $picks = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $picks[] = $row;
        }
    }
    $response['picks'] = $picks;
    $response['count'] = count($picks);

} elseif ($type === 'algorithms') {
    // ─── Algorithms ───
    $sql = "SELECT a.*, COUNT(sp.id) as pick_count
            FROM algorithms a
            LEFT JOIN stock_picks sp ON a.name = sp.algorithm_name
            GROUP BY a.id
            ORDER BY a.family, a.name";
    $res = $conn->query($sql);
    $algos = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $algos[] = $row;
        }
    }
    $response['algorithms'] = $algos;

} elseif ($type === 'portfolios') {
    // ─── Portfolios ───
    $sql = "SELECT * FROM portfolios ORDER BY strategy_type, name";
    $res = $conn->query($sql);
    $portfolios = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $portfolios[] = $row;
        }
    }
    $response['portfolios'] = $portfolios;

} elseif ($type === 'backtests') {
    // ─── Saved Backtest Results ───
    $sql = "SELECT * FROM backtest_results ORDER BY created_at DESC LIMIT 50";
    $res = $conn->query($sql);
    $backtests = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $backtests[] = $row;
        }
    }
    $response['backtests'] = $backtests;

} elseif ($type === 'scenarios') {
    // ─── Predefined Scenarios ───
    $response['scenarios'] = array(
        array('key' => 'daytrader_eod',       'name' => 'Day Trader (EOD Exit)',      'tp' => 5,   'sl' => 3,  'hold' => 1),
        array('key' => 'daytrader_2day',      'name' => 'Day Trader (2-Day Max)',     'tp' => 10,  'sl' => 5,  'hold' => 2),
        array('key' => 'weekly_10',           'name' => 'Weekly Hold (10% Target)',   'tp' => 10,  'sl' => 5,  'hold' => 7),
        array('key' => 'weekly_20',           'name' => 'Weekly Hold (20% Target)',   'tp' => 20,  'sl' => 8,  'hold' => 7),
        array('key' => 'swing_conservative',  'name' => 'Conservative Swing',        'tp' => 10,  'sl' => 5,  'hold' => 20),
        array('key' => 'swing_aggressive',    'name' => 'Aggressive Swing',          'tp' => 30,  'sl' => 15, 'hold' => 20),
        array('key' => 'buy_hold_3m',         'name' => 'Buy & Hold (3 Months)',     'tp' => 999, 'sl' => 999,'hold' => 60),
        array('key' => 'buy_hold_6m',         'name' => 'Buy & Hold (6 Months)',     'tp' => 999, 'sl' => 999,'hold' => 126),
        array('key' => 'tight_scalp',         'name' => 'Tight Scalp',              'tp' => 3,   'sl' => 2,  'hold' => 1),
        array('key' => 'momentum_ride',       'name' => 'Momentum Ride',            'tp' => 50,  'sl' => 10, 'hold' => 30)
    );

} elseif ($type === 'prices') {
    // ─── Price History ───
    $ticker = isset($_GET['ticker']) ? trim($_GET['ticker']) : '';
    if ($ticker === '') {
        $response['ok'] = false;
        $response['error'] = 'ticker parameter required';
    } else {
        $safe = $conn->real_escape_string(strtoupper($ticker));
        $sql = "SELECT trade_date, open_price, high_price, low_price, close_price, volume
                FROM daily_prices WHERE ticker='$safe' ORDER BY trade_date ASC";
        $res = $conn->query($sql);
        $prices = array();
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $prices[] = $row;
            }
        }
        $response['ticker'] = strtoupper($ticker);
        $response['prices'] = $prices;
        $response['count'] = count($prices);
    }

} elseif ($type === 'stats') {
    // ─── Overview Stats ───
    $stats = array();

    $res = $conn->query("SELECT COUNT(*) as c FROM stocks");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_stocks'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(*) as c FROM stock_picks");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_picks'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(*) as c FROM daily_prices");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_price_records'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(*) as c FROM backtest_results");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['total_backtests'] = (int)$row['c'];

    $res = $conn->query("SELECT COUNT(DISTINCT algorithm_name) as c FROM stock_picks");
    $row = ($res) ? $res->fetch_assoc() : array('c' => 0);
    $stats['active_algorithms'] = (int)$row['c'];

    $res = $conn->query("SELECT MIN(pick_date) as mn, MAX(pick_date) as mx FROM stock_picks");
    if ($res) {
        $row = $res->fetch_assoc();
        $stats['pick_date_range'] = array(
            'earliest' => isset($row['mn']) ? $row['mn'] : null,
            'latest'   => isset($row['mx']) ? $row['mx'] : null
        );
    }

    $res = $conn->query("SELECT MIN(trade_date) as mn, MAX(trade_date) as mx FROM daily_prices");
    if ($res) {
        $row = $res->fetch_assoc();
        $stats['price_date_range'] = array(
            'earliest' => isset($row['mn']) ? $row['mn'] : null,
            'latest'   => isset($row['mx']) ? $row['mx'] : null
        );
    }

    // Algorithm breakdown
    $algo_breakdown = array();
    $res = $conn->query("SELECT algorithm_name, COUNT(*) as cnt, AVG(score) as avg_score
                         FROM stock_picks GROUP BY algorithm_name ORDER BY cnt DESC");
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $algo_breakdown[] = $row;
        }
    }
    $stats['algorithm_breakdown'] = $algo_breakdown;

    $response['stats'] = $stats;

} else {
    $response['ok'] = false;
    $response['error'] = 'Unknown type. Use: picks, algorithms, portfolios, backtests, scenarios, prices, stats';
}

echo json_encode($response);
$conn->close();
?>
