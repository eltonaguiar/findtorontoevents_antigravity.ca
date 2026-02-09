<?php
/**
 * Fetch historical NAV data for mutual funds from Yahoo Finance.
 * Mutual funds trade once per day at NAV — no OHLC intraday data.
 * PHP 5.2 compatible.
 *
 * Usage: GET .../fetch_nav.php?range=1y&batch=10
 */
require_once dirname(__FILE__) . '/db_connect.php';

$range = isset($_GET['range']) ? $_GET['range'] : '1y';
$batch_size = isset($_GET['batch']) ? (int)$_GET['batch'] : 10;
if ($batch_size < 1 || $batch_size > 30) $batch_size = 10;

// Get tickers needing more data
$sql = "SELECT f.ticker FROM mf_funds f
        LEFT JOIN (SELECT ticker, COUNT(*) as cnt FROM mf_nav_history GROUP BY ticker) nh ON f.ticker = nh.ticker
        WHERE nh.cnt IS NULL OR nh.cnt < 50
        ORDER BY f.ticker LIMIT $batch_size";
$res = $conn->query($sql);
$tickers = array();
if ($res) { while ($row = $res->fetch_assoc()) $tickers[] = $row['ticker']; }

if (count($tickers) === 0) {
    echo json_encode(array('ok' => true, 'fetched' => 0, 'message' => 'All tickers populated'));
    $conn->close();
    exit;
}

$range_map = array('1m' => 2678400, '3m' => 7948800, '6m' => 15897600, '1y' => 31536000, '2y' => 63072000, '5y' => 157680000);
$period_sec = isset($range_map[$range]) ? $range_map[$range] : 31536000;
$now_ts = time();
$from_ts = $now_ts - $period_sec;

$fetched = 0;
$errors = array();

foreach ($tickers as $ticker) {
    $safe = $conn->real_escape_string($ticker);

    // Yahoo Finance chart API
    $url = 'https://query1.finance.yahoo.com/v8/finance/chart/' . urlencode($ticker)
         . '?period1=' . $from_ts . '&period2=' . $now_ts . '&interval=1d';

    $ctx = stream_context_create(array('http' => array('timeout' => 15, 'header' => "User-Agent: Mozilla/5.0\r\n")));
    $json = @file_get_contents($url, false, $ctx);

    if ($json === false) {
        $errors[] = $ticker . ': fetch failed';
        continue;
    }

    $data = json_decode($json, true);
    if (!$data || !isset($data['chart']['result'][0])) {
        $errors[] = $ticker . ': no data';
        continue;
    }

    $result = $data['chart']['result'][0];
    $timestamps = isset($result['timestamp']) ? $result['timestamp'] : array();
    $closes = isset($result['indicators']['adjclose'][0]['adjclose']) ? $result['indicators']['adjclose'][0]['adjclose'] : array();
    $quote = isset($result['indicators']['quote'][0]) ? $result['indicators']['quote'][0] : array();

    $inserted = 0;
    $cnt = count($timestamps);
    for ($i = 0; $i < $cnt; $i++) {
        if (!isset($timestamps[$i]) || !isset($closes[$i]) || $closes[$i] === null) continue;

        $date = date('Y-m-d', (int)$timestamps[$i]);
        $nav = round((float)$closes[$i], 4);
        $close_raw = isset($quote['close'][$i]) ? round((float)$quote['close'][$i], 4) : $nav;
        $vol = isset($quote['volume'][$i]) ? (int)$quote['volume'][$i] : 0;

        // Calculate change_pct from previous day
        $change = 0;
        if ($i > 0 && isset($closes[$i - 1]) && $closes[$i - 1] > 0) {
            $change = round(($nav - (float)$closes[$i - 1]) / (float)$closes[$i - 1] * 100, 4);
        }

        $sql = "INSERT INTO mf_nav_history (ticker, nav_date, nav_price, adj_nav, change_pct, volume)
                VALUES ('$safe', '$date', $close_raw, $nav, $change, $vol)
                ON DUPLICATE KEY UPDATE nav_price=$close_raw, adj_nav=$nav, change_pct=$change, volume=$vol";
        if ($conn->query($sql)) $inserted++;
    }

    if ($inserted > 0) $fetched++;
}

$remaining = 0;
$r = $conn->query("SELECT COUNT(DISTINCT f.ticker) as cnt FROM mf_funds f LEFT JOIN (SELECT ticker, COUNT(*) as cnt FROM mf_nav_history GROUP BY ticker) nh ON f.ticker = nh.ticker WHERE nh.cnt IS NULL OR nh.cnt < 50");
if ($r && $row = $r->fetch_assoc()) $remaining = (int)$row['cnt'];

$response = array('ok' => true, 'fetched' => $fetched, 'tickers' => $tickers, 'errors' => $errors);
if ($remaining > 0) $response['note'] = $remaining . ' tickers still need data';

// Audit
$now = date('Y-m-d H:i:s');
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$conn->query("INSERT INTO mf_audit_log (action_type, details, ip_address, created_at) VALUES ('fetch_nav', 'Fetched $fetched tickers', '$ip', '$now')");

echo json_encode($response);
$conn->close();
?>
