<?php
/**
 * CDR availability check + Questrade fee estimate for a ticker.
 * PHP 5.2 compatible.
 *
 * Usage: GET .../cdr_check.php?ticker=AAPL&shares=100&price=175
 *        GET .../cdr_check.php?tickers=AAPL,TSLA,SHOP.TO,PLTR
 */
require_once dirname(__FILE__) . '/questrade_fees.php';

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$single = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';
$multi  = isset($_GET['tickers']) ? $_GET['tickers'] : '';
$shares = isset($_GET['shares']) ? (int)$_GET['shares'] : 100;
$price  = isset($_GET['price']) ? (float)$_GET['price'] : 100;

if ($single !== '') {
    $trade_value = $price * $shares;
    $buy = questrade_calc_fees($single, $trade_value, $shares, false, 'questrade');
    $sell = questrade_calc_fees($single, $trade_value, $shares, true, 'questrade');
    $total_round_trip = round($buy['total_fee'] + $sell['total_fee'], 2);

    echo json_encode(array(
        'ticker'       => $single,
        'has_cdr'      => $buy['is_cdr'],
        'is_canadian'  => $buy['is_canadian'],
        'shares'       => $shares,
        'price'        => $price,
        'trade_value'  => $trade_value,
        'buy_fees'     => $buy,
        'sell_fees'    => $sell,
        'round_trip_total' => $total_round_trip,
        'savings_vs_flat10' => round(20 - $total_round_trip, 2),
        'note' => $buy['is_cdr']
            ? 'CDR available — trade in CAD on NEO Exchange, $0 commission, no forex fee'
            : ($buy['is_canadian']
                ? 'Canadian-listed — $0 commission, no forex fee'
                : 'US stock without CDR — $0 commission but 1.75% forex fee applies')
    ));
} elseif ($multi !== '') {
    $tickers = explode(',', $multi);
    $results = array();
    foreach ($tickers as $t) {
        $t = strtoupper(trim($t));
        if ($t === '') continue;
        $tv = $price * $shares;
        $bf = questrade_calc_fees($t, $tv, $shares, false, 'questrade');
        $sf = questrade_calc_fees($t, $tv, $shares, true, 'questrade');
        $results[] = array(
            'ticker'      => $t,
            'has_cdr'     => $bf['is_cdr'],
            'is_canadian' => $bf['is_canadian'],
            'round_trip_fee' => round($bf['total_fee'] + $sf['total_fee'], 2),
            'category'    => $bf['is_cdr'] ? 'CDR (free)' : ($bf['is_canadian'] ? 'TSX (free)' : 'US (forex fee)')
        );
    }
    echo json_encode(array('results' => $results, 'total_tickers' => count($results)));
} else {
    // Return full CDR list
    echo json_encode(array(
        'cdr_tickers' => $QUESTRADE_CDR_TICKERS,
        'count'       => count($QUESTRADE_CDR_TICKERS),
        'fee_structure' => array(
            'stocks_etfs_commission' => '$0',
            'cdr_commission' => '$0 (trades in CAD)',
            'us_forex_markup' => '1.75%',
            'ecn_per_share' => '$0.0035',
            'sec_fee_on_sells' => '0.00278%',
            'mutual_fund_commission' => '$9.95/trade'
        )
    ));
}
?>
