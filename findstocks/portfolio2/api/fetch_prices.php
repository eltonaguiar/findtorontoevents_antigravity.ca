<?php
/**
 * Fetch historical price data from Yahoo Finance / Stooq.
 * PHP 5.2 compatible.
 *
 * Usage: GET .../fetch_prices.php               — fetch all stocks missing data
 *        GET .../fetch_prices.php?ticker=AAPL   — fetch one stock
 *        GET .../fetch_prices.php?range=6mo     — custom range
 *        GET .../fetch_prices.php?force=1       — re-fetch even if data exists
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'fetched' => 0, 'errors' => array(), 'tickers' => array());

$single_ticker = isset($_GET['ticker']) ? trim($_GET['ticker']) : '';
$range         = isset($_GET['range']) ? trim($_GET['range']) : '1y';

$valid_ranges = array('1mo', '3mo', '6mo', '1y', '2y', '5y');
$found_range = false;
foreach ($valid_ranges as $vr) {
    if ($vr === $range) { $found_range = true; break; }
}
if (!$found_range) $range = '1y';

$tickers = array();
if ($single_ticker !== '') {
    $tickers = array(strtoupper($single_ticker));
} else {
    $skip_mode = isset($_GET['force']) ? false : true;
    $sql = "SELECT DISTINCT s.ticker FROM stocks s";
    if ($skip_mode) {
        $sql .= " LEFT JOIN (SELECT ticker, COUNT(*) as cnt FROM daily_prices GROUP BY ticker) dp ON s.ticker = dp.ticker";
        $sql .= " WHERE dp.cnt IS NULL OR dp.cnt < 50";
    }
    $sql .= " ORDER BY s.ticker";
    $res = $conn->query($sql);
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $tickers[] = $row['ticker'];
        }
    }
}

if (count($tickers) === 0) {
    $results['ok'] = true;
    $results['message'] = 'No tickers need price data. All stocks already have sufficient data.';
    echo json_encode($results);
    $conn->close();
    exit;
}

if (count($tickers) > 10) {
    $tickers = array_slice($tickers, 0, 10);
    $results['note'] = 'Limited to 10 tickers per call. Call again for more.';
}

function fetch_yahoo_chart_v2($ticker, $range) {
    $url = 'https://query1.finance.yahoo.com/v8/finance/chart/'
         . urlencode($ticker)
         . '?range=' . urlencode($range)
         . '&interval=1d&includeAdjustedClose=true';

    $ctx = stream_context_create(array(
        'http' => array(
            'method' => 'GET',
            'header' => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n",
            'timeout' => 10
        )
    ));

    $json = @file_get_contents($url, false, $ctx);
    if ($json === false) return null;

    $data = json_decode($json, true);
    if (!$data || !isset($data['chart']['result'][0])) return null;

    $result = $data['chart']['result'][0];
    if (!isset($result['timestamp']) || !isset($result['indicators']['quote'][0])) return null;

    $timestamps = $result['timestamp'];
    $quote      = $result['indicators']['quote'][0];
    $adjclose   = isset($result['indicators']['adjclose'][0]['adjclose'])
                  ? $result['indicators']['adjclose'][0]['adjclose']
                  : array();

    $prices = array();
    $count = count($timestamps);
    for ($i = 0; $i < $count; $i++) {
        $o = isset($quote['open'][$i])   ? $quote['open'][$i]   : null;
        $h = isset($quote['high'][$i])   ? $quote['high'][$i]   : null;
        $l = isset($quote['low'][$i])    ? $quote['low'][$i]    : null;
        $c = isset($quote['close'][$i])  ? $quote['close'][$i]  : null;
        $v = isset($quote['volume'][$i]) ? $quote['volume'][$i] : 0;
        $ac = isset($adjclose[$i])       ? $adjclose[$i]        : $c;
        if ($o === null || $h === null || $l === null || $c === null) continue;
        $prices[] = array(
            'date' => date('Y-m-d', $timestamps[$i]),
            'open' => round($o, 4), 'high' => round($h, 4),
            'low' => round($l, 4), 'close' => round($c, 4),
            'adj_close' => round($ac, 4), 'volume' => (int)$v
        );
    }
    return $prices;
}

function fetch_stooq_csv_v2($ticker, $range) {
    $end_ts = time();
    if ($range === '1mo')      $start_ts = $end_ts - 30 * 86400;
    elseif ($range === '3mo')  $start_ts = $end_ts - 90 * 86400;
    elseif ($range === '6mo')  $start_ts = $end_ts - 180 * 86400;
    elseif ($range === '2y')   $start_ts = $end_ts - 730 * 86400;
    elseif ($range === '5y')   $start_ts = $end_ts - 1825 * 86400;
    else                       $start_ts = $end_ts - 365 * 86400;

    $url = 'https://stooq.com/q/d/l/?s=' . urlencode($ticker) . '.US&d1=' . date('Ymd', $start_ts) . '&d2=' . date('Ymd', $end_ts) . '&i=d';
    $ctx = stream_context_create(array('http' => array('method' => 'GET', 'header' => "User-Agent: Mozilla/5.0\r\n", 'timeout' => 10)));
    $csv = @file_get_contents($url, false, $ctx);
    if ($csv === false || strlen($csv) < 50) return null;

    $lines = explode("\n", trim($csv));
    if (count($lines) < 2) return null;

    $prices = array();
    $cnt = count($lines);
    for ($i = 1; $i < $cnt; $i++) {
        $cols = explode(',', trim($lines[$i]));
        if (count($cols) < 5) continue;
        $prices[] = array(
            'date' => $cols[0], 'open' => round((float)$cols[1], 4),
            'high' => round((float)$cols[2], 4), 'low' => round((float)$cols[3], 4),
            'close' => round((float)$cols[4], 4), 'adj_close' => round((float)$cols[4], 4),
            'volume' => isset($cols[5]) ? (int)$cols[5] : 0
        );
    }
    return count($prices) > 0 ? $prices : null;
}

foreach ($tickers as $ticker) {
    $safe_ticker = $conn->real_escape_string($ticker);
    $prices = fetch_yahoo_chart_v2($ticker, $range);
    if ($prices === null) {
        $prices = fetch_stooq_csv_v2($ticker, $range);
    }
    if ($prices === null) {
        $results['errors'][] = $ticker . ': Failed to fetch from any source';
        continue;
    }

    $inserted = 0;
    foreach ($prices as $p) {
        $d = $conn->real_escape_string($p['date']);
        $o = (float)$p['open']; $h = (float)$p['high'];
        $l = (float)$p['low'];  $c = (float)$p['close'];
        $ac = (float)$p['adj_close']; $v = (int)$p['volume'];
        $sql = "INSERT INTO daily_prices (ticker, trade_date, open_price, high_price, low_price, close_price, adj_close, volume)
                VALUES ('$safe_ticker', '$d', $o, $h, $l, $c, $ac, $v)
                ON DUPLICATE KEY UPDATE open_price=$o, high_price=$h, low_price=$l, close_price=$c, adj_close=$ac, volume=$v";
        if ($conn->query($sql)) $inserted++;
    }

    $results['tickers'][] = array('ticker' => $ticker, 'prices' => $inserted);
    $results['fetched']++;
}

$now = date('Y-m-d H:i:s');
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('fetch_prices', '" . $conn->real_escape_string('Fetched ' . $results['fetched'] . ' tickers') . "', '$ip', '$now')");

echo json_encode($results);
$conn->close();
?>
