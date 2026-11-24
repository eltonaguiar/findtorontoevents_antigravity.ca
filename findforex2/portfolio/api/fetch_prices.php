<?php
/**
 * Fetch historical price data for forex pairs.
 * Uses Yahoo Finance (EURUSD=X format) as primary source.
 * Falls back to static sample data if Yahoo fails.
 * PHP 5.2 compatible.
 *
 * Usage: GET .../fetch_prices.php                  -- fetch all pairs missing data
 *        GET .../fetch_prices.php?symbol=EURUSD    -- fetch one pair
 *        GET .../fetch_prices.php?range=6mo        -- custom range
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'fetched' => 0, 'errors' => array(), 'pairs' => array());

$single = isset($_GET['symbol']) ? trim(strtoupper($_GET['symbol'])) : '';
$range  = isset($_GET['range']) ? trim($_GET['range']) : '1y';

$valid_ranges = array('1mo', '3mo', '6mo', '1y', '2y', '5y');
$found = false;
foreach ($valid_ranges as $vr) {
    if ($vr === $range) { $found = true; break; }
}
if (!$found) $range = '1y';

$symbols = array();
if ($single !== '') {
    $symbols = array($single);
} else {
    $skip_mode = isset($_GET['force']) ? false : true;
    $sql = "SELECT DISTINCT p.symbol FROM fxp_pairs p";
    if ($skip_mode) {
        $sql .= " LEFT JOIN (SELECT symbol, COUNT(*) as cnt FROM fxp_price_history GROUP BY symbol) ph ON p.symbol = ph.symbol";
        $sql .= " WHERE ph.cnt IS NULL OR ph.cnt < 20";
    }
    $sql .= " ORDER BY p.symbol";
    $res = $conn->query($sql);
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $symbols[] = $row['symbol'];
        }
    }
}

if (count($symbols) === 0) {
    $results['message'] = 'No pairs need price data. All pairs already have sufficient data.';
    echo json_encode($results);
    $conn->close();
    exit;
}

if (count($symbols) > 10) {
    $symbols = array_slice($symbols, 0, 10);
    $results['note'] = 'Limited to 10 pairs per call. Call again for more.';
}

function fetch_fxp_prices($symbol, $range) {
    // Yahoo Finance uses EURUSD=X format for forex
    $yahoo_symbol = $symbol . '=X';
    $url = 'https://query1.finance.yahoo.com/v8/finance/chart/'
         . urlencode($yahoo_symbol)
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
    if ($json !== false) {
        $data = json_decode($json, true);
        if ($data && isset($data['chart']['result'][0])) {
            $result = $data['chart']['result'][0];
            if (isset($result['timestamp']) && isset($result['indicators']['quote'][0])) {
                $timestamps = $result['timestamp'];
                $quote = $result['indicators']['quote'][0];

                $prices = array();
                $count = count($timestamps);
                for ($i = 0; $i < $count; $i++) {
                    $o = isset($quote['open'][$i]) ? $quote['open'][$i] : null;
                    $h = isset($quote['high'][$i]) ? $quote['high'][$i] : null;
                    $l = isset($quote['low'][$i]) ? $quote['low'][$i] : null;
                    $c = isset($quote['close'][$i]) ? $quote['close'][$i] : null;
                    $v = isset($quote['volume'][$i]) ? $quote['volume'][$i] : 0;
                    if ($c === null) continue;

                    $prices[] = array(
                        'date' => date('Y-m-d', $timestamps[$i]),
                        'open' => round($o !== null ? $o : $c, 6),
                        'high' => round($h !== null ? $h : $c, 6),
                        'low' => round($l !== null ? $l : $c, 6),
                        'close' => round($c, 6),
                        'volume' => (int)$v
                    );
                }
                if (count($prices) > 0) return $prices;
            }
        }
    }

    return null;
}

// Static fallback data generator for when Yahoo is unavailable
function generate_sample_prices($symbol) {
    // Base prices for common pairs
    $base_prices = array(
        'EURUSD' => 1.0850, 'GBPUSD' => 1.2650, 'USDJPY' => 149.50,
        'USDCAD' => 1.3580, 'AUDUSD' => 0.6520, 'NZDUSD' => 0.6085,
        'USDCHF' => 0.8820, 'EURGBP' => 0.8575
    );
    $base = isset($base_prices[$symbol]) ? $base_prices[$symbol] : 1.0000;
    $is_jpy = (strpos($symbol, 'JPY') !== false);
    $volatility = $is_jpy ? 0.5 : 0.003;

    $prices = array();
    $price = $base;
    // Generate 252 trading days (1 year)
    $date = strtotime('-1 year');
    for ($i = 0; $i < 252; $i++) {
        $date = strtotime('+1 day', $date);
        // Skip weekends
        $dow = date('w', $date);
        if ($dow == 0 || $dow == 6) continue;

        // Random walk
        $change = (mt_rand(-100, 100) / 100) * $volatility;
        $price = $price + $change;
        $high = $price + abs($change) * 0.5;
        $low = $price - abs($change) * 0.5;

        $decimals = $is_jpy ? 3 : 6;
        $prices[] = array(
            'date' => date('Y-m-d', $date),
            'open' => round($price - $change * 0.3, $decimals),
            'high' => round($high, $decimals),
            'low' => round($low, $decimals),
            'close' => round($price, $decimals),
            'volume' => mt_rand(50000, 500000)
        );
    }
    return $prices;
}

foreach ($symbols as $symbol) {
    $safe = $conn->real_escape_string($symbol);
    $prices = fetch_fxp_prices($symbol, $range);

    // Fallback to sample data
    if ($prices === null) {
        $prices = generate_sample_prices($symbol);
        $results['note'] = isset($results['note']) ? $results['note'] : '';
        $results['note'] .= ' ' . $symbol . ' used sample data (Yahoo unavailable).';
    }

    if ($prices === null || count($prices) === 0) {
        $results['errors'][] = $symbol . ': Failed to fetch price data';
        continue;
    }

    $inserted = 0;
    foreach ($prices as $p) {
        $d = $conn->real_escape_string($p['date']);
        $o = (float)$p['open'];
        $h = (float)$p['high'];
        $l = (float)$p['low'];
        $c = (float)$p['close'];
        $v = (int)$p['volume'];
        $sql = "INSERT INTO fxp_price_history (symbol, price_date, open_price, high_price, low_price, close_price, volume)
                VALUES ('$safe', '$d', $o, $h, $l, $c, $v)
                ON DUPLICATE KEY UPDATE open_price=$o, high_price=$h, low_price=$l, close_price=$c, volume=$v";
        if ($conn->query($sql)) $inserted++;
    }

    $results['pairs'][] = array('symbol' => $symbol, 'price_records' => $inserted);
    $results['fetched']++;
}

$now = date('Y-m-d H:i:s');
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$conn->query("INSERT INTO fxp_audit_log (action_type, details, ip_address, created_at) VALUES ('fetch_prices', '" . $conn->real_escape_string('Fetched ' . $results['fetched'] . ' pairs') . "', '$ip', '$now')");

echo json_encode($results);
$conn->close();
?>
