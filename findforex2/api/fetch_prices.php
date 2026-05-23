<?php
/**
 * Fetch forex price data from Yahoo Finance.
 * PHP 5.2 compatible.
 * Usage: GET .../fetch_prices.php              — fetch all pairs
 *        GET .../fetch_prices.php?pair=EURUSD  — fetch one pair
 *        GET .../fetch_prices.php?range=1y     — custom range
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'fetched' => 0, 'errors' => array(), 'pairs' => array());
$single_pair = isset($_GET['pair']) ? strtoupper(trim($_GET['pair'])) : '';
$range = isset($_GET['range']) ? trim($_GET['range']) : '1y';

$valid_ranges = array('1mo', '3mo', '6mo', '1y', '2y');
$found = false;
foreach ($valid_ranges as $vr) { if ($vr === $range) { $found = true; break; } }
if (!$found) $range = '1y';

// Get pairs to fetch
$pairs = array();
if ($single_pair !== '') {
    $res = $conn->query("SELECT pair, yahoo_ticker FROM fx_pairs WHERE pair='" . $conn->real_escape_string($single_pair) . "'");
    if ($res && $row = $res->fetch_assoc()) $pairs[] = $row;
} else {
    $res = $conn->query("SELECT fp.pair, fp.yahoo_ticker FROM fx_pairs fp
                         LEFT JOIN (SELECT pair, COUNT(*) as cnt FROM fx_prices GROUP BY pair) pp ON fp.pair = pp.pair
                         WHERE pp.cnt IS NULL OR pp.cnt < 50 ORDER BY fp.pair");
    if ($res) { while ($row = $res->fetch_assoc()) $pairs[] = $row; }
}

if (count($pairs) === 0) {
    $results['errors'][] = 'No pairs to fetch. Run setup_schema.php first.';
    echo json_encode($results);
    $conn->close();
    exit;
}

if (count($pairs) > 10) {
    $pairs = array_slice($pairs, 0, 10);
    $results['note'] = 'Limited to 10 pairs per call.';
}

foreach ($pairs as $pinfo) {
    $pair = $pinfo['pair'];
    $yahoo = $pinfo['yahoo_ticker'];
    $safe_pair = $conn->real_escape_string($pair);

    $url = 'https://query1.finance.yahoo.com/v8/finance/chart/' . urlencode($yahoo) . '?range=' . urlencode($range) . '&interval=1d';
    $ctx = stream_context_create(array('http' => array('method' => 'GET', 'header' => "User-Agent: Mozilla/5.0\r\n", 'timeout' => 10)));
    $json = @file_get_contents($url, false, $ctx);

    if ($json === false) {
        $results['errors'][] = $pair . ': fetch failed';
        continue;
    }

    $data = json_decode($json, true);
    if (!$data || !isset($data['chart']['result'][0]['timestamp'])) {
        $results['errors'][] = $pair . ': invalid data';
        continue;
    }

    $r = $data['chart']['result'][0];
    $ts = $r['timestamp'];
    $q = $r['indicators']['quote'][0];
    $inserted = 0;

    $cnt = count($ts);
    for ($i = 0; $i < $cnt; $i++) {
        $o = isset($q['open'][$i]) ? $q['open'][$i] : null;
        $h = isset($q['high'][$i]) ? $q['high'][$i] : null;
        $l = isset($q['low'][$i]) ? $q['low'][$i] : null;
        $c = isset($q['close'][$i]) ? $q['close'][$i] : null;
        $v = isset($q['volume'][$i]) ? (int)$q['volume'][$i] : 0;
        if ($o === null || $c === null) continue;

        $d = date('Y-m-d', $ts[$i]);
        $sql = "INSERT INTO fx_prices (pair, trade_date, open_price, high_price, low_price, close_price, volume)
                VALUES ('$safe_pair','$d',$o,$h,$l,$c,$v)
                ON DUPLICATE KEY UPDATE open_price=$o, high_price=$h, low_price=$l, close_price=$c, volume=$v";
        if ($conn->query($sql)) $inserted++;
    }

    $results['pairs'][] = array('pair' => $pair, 'prices' => $inserted);
    $results['fetched']++;
}

echo json_encode($results);
$conn->close();
?>
