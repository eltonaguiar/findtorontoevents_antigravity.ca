<?php
/**
 * penny_stocks.php — Yahoo Finance Screener proxy for penny stocks.
 * Finds high-volume, exchange-listed penny stocks (no OTC).
 *
 * GET params:
 *   region     = ca | us | both  (default: ca)
 *   max_price  = float           (default: 5.00, max 20)
 *   min_price  = float           (default: 0.01)
 *   min_volume = int             (default: 100000)
 *   sort       = dayvolume | intradayprice | percentchange | intradaymarketcap (default: dayvolume)
 *   sort_dir   = DESC | ASC      (default: DESC)
 *   offset     = int             (default: 0)
 *   size       = int             (default: 50, max 100)
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// ── Input validation ──
$region = isset($_GET['region']) ? strtolower($_GET['region']) : 'ca';
if ($region !== 'ca' && $region !== 'us' && $region !== 'both') $region = 'ca';

$max_price = isset($_GET['max_price']) ? floatval($_GET['max_price']) : 5.0;
if ($max_price <= 0 || $max_price > 20) $max_price = 5.0;

$min_price = isset($_GET['min_price']) ? floatval($_GET['min_price']) : 0.01;
if ($min_price < 0) $min_price = 0.01;

$min_volume = isset($_GET['min_volume']) ? intval($_GET['min_volume']) : 100000;
if ($min_volume < 0) $min_volume = 100000;

$sort_field = isset($_GET['sort']) ? $_GET['sort'] : 'dayvolume';
$allowed_sorts = array('dayvolume', 'intradayprice', 'percentchange', 'intradaymarketcap');
if (!in_array($sort_field, $allowed_sorts)) $sort_field = 'dayvolume';

$sort_dir = isset($_GET['sort_dir']) ? strtoupper($_GET['sort_dir']) : 'DESC';
if ($sort_dir !== 'ASC' && $sort_dir !== 'DESC') $sort_dir = 'DESC';

$offset = isset($_GET['offset']) ? max(0, intval($_GET['offset'])) : 0;
$size   = isset($_GET['size'])   ? min(max(1, intval($_GET['size'])), 100) : 50;

// ── Cache (30 min) ──
$cache_key  = md5($region . '|' . $max_price . '|' . $min_price . '|' . $min_volume . '|' . $sort_field . '|' . $sort_dir . '|' . $offset . '|' . $size);
$cache_dir  = dirname(__FILE__) . '/cache';
if (!is_dir($cache_dir)) @mkdir($cache_dir, 0755, true);
$cache_file = $cache_dir . '/penny_' . $cache_key . '.json';

if (file_exists($cache_file) && (time() - filemtime($cache_file)) < 1800) {
    $cached = file_get_contents($cache_file);
    if ($cached) { echo $cached; exit; }
}

// ── Yahoo crumb/cookie auth ──
$_ps_cookie = '';
$_ps_crumb  = '';

function _ps_get_crumb() {
    global $_ps_cookie, $_ps_crumb;

    // Step 1: hit fc.yahoo.com to get cookies
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, 'https://fc.yahoo.com');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_HEADER, true);
    curl_setopt($ch, CURLOPT_NOBODY, false);
    $resp = curl_exec($ch);
    curl_close($ch);
    if (!$resp) return false;

    // Extract cookies
    $cookies = array();
    preg_match_all('/Set-Cookie:\s*([^;\r\n]+)/i', $resp, $m);
    if (isset($m[1])) {
        foreach ($m[1] as $c) $cookies[] = trim($c);
    }
    $_ps_cookie = implode('; ', $cookies);
    if ($_ps_cookie === '') return false;

    // Step 2: fetch crumb
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, 'https://query2.finance.yahoo.com/v1/test/getcrumb');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
    curl_setopt($ch, CURLOPT_HTTPHEADER, array('Cookie: ' . $_ps_cookie));
    $crumb = curl_exec($ch);
    curl_close($ch);

    if ($crumb && strlen($crumb) > 0 && strlen($crumb) < 50 && strpos($crumb, '<') === false) {
        $_ps_crumb = trim($crumb);
        return true;
    }
    return false;
}

// ── Get auth ──
if (!_ps_get_crumb()) {
    echo json_encode(array('ok' => false, 'error' => 'Failed to get Yahoo Finance auth'));
    exit;
}

// ── Build screener query ──
$operands = array();

// Price filter
$operands[] = array('operator' => 'btwn', 'operands' => array('intradayprice', $min_price, $max_price));

// Volume filter
$operands[] = array('operator' => 'gt', 'operands' => array('dayvolume', $min_volume));

// Region filter
if ($region === 'both') {
    // For 'both', use OR on ca + us
    $operands[] = array(
        'operator' => 'or',
        'operands' => array(
            array('operator' => 'eq', 'operands' => array('region', 'ca')),
            array('operator' => 'eq', 'operands' => array('region', 'us'))
        )
    );
} else {
    $operands[] = array('operator' => 'eq', 'operands' => array('region', $region));
}

$body = array(
    'offset'    => $offset,
    'size'      => $size,
    'sortField' => $sort_field,
    'sortType'  => $sort_dir,
    'quoteType' => 'EQUITY',
    'query'     => array(
        'operator' => 'and',
        'operands' => $operands
    )
);

// ── POST to Yahoo screener ──
$url = 'https://query2.finance.yahoo.com/v1/finance/screener?crumb=' . urlencode($_ps_crumb);
$json_body = json_encode($body);

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, $json_body);
curl_setopt($ch, CURLOPT_TIMEOUT, 30);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
curl_setopt($ch, CURLOPT_HTTPHEADER, array(
    'Content-Type: application/json',
    'Cookie: ' . $_ps_cookie
));
$raw = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if (!$raw || $http_code < 200 || $http_code >= 300) {
    echo json_encode(array(
        'ok' => false,
        'error' => 'Yahoo screener request failed',
        'http_code' => $http_code,
        'debug' => substr($raw, 0, 300)
    ));
    exit;
}

$data = json_decode($raw, true);
if (!$data) {
    echo json_encode(array('ok' => false, 'error' => 'Invalid JSON from Yahoo', 'raw' => substr($raw, 0, 300)));
    exit;
}

// Handle Yahoo error response
if (isset($data['finance']['error']) && $data['finance']['error'] !== null) {
    echo json_encode(array(
        'ok' => false,
        'error' => 'Yahoo screener error: ' . (isset($data['finance']['error']['description']) ? $data['finance']['error']['description'] : 'unknown')
    ));
    exit;
}

if (!isset($data['finance']['result']) || !is_array($data['finance']['result']) || count($data['finance']['result']) === 0) {
    echo json_encode(array('ok' => false, 'error' => 'No results from Yahoo screener', 'raw' => substr($raw, 0, 500)));
    exit;
}

$result = $data['finance']['result'][0];
$quotes = isset($result['quotes']) ? $result['quotes'] : array();
$total  = isset($result['total'])  ? intval($result['total']) : 0;

// ── OTC/Pink Sheet exchanges to exclude ──
$blocked_exchanges = array('PNK', 'OTC', 'OBB', 'OTCQX', 'OTCQB', 'OTCBB', 'PKC', 'OQX', 'OQB');

// ── Recognized exchange labels ──
function _ps_exchange_info($exchange, $symbol) {
    $map = array(
        'TOR' => array('label' => 'TSX',           'country' => 'CA', 'rrsp' => true),
        'CVE' => array('label' => 'TSX-V',         'country' => 'CA', 'rrsp' => true),
        'CNQ' => array('label' => 'CSE',           'country' => 'CA', 'rrsp' => true),
        'NEO' => array('label' => 'NEO',           'country' => 'CA', 'rrsp' => true),
        'VAN' => array('label' => 'TSX-V',         'country' => 'CA', 'rrsp' => true),
        'NYQ' => array('label' => 'NYSE',          'country' => 'US', 'rrsp' => true),
        'NMS' => array('label' => 'NASDAQ',        'country' => 'US', 'rrsp' => true),
        'NGM' => array('label' => 'NASDAQ',        'country' => 'US', 'rrsp' => true),
        'NCM' => array('label' => 'NASDAQ',        'country' => 'US', 'rrsp' => true),
        'ASE' => array('label' => 'NYSE American', 'country' => 'US', 'rrsp' => true),
        'PCX' => array('label' => 'NYSE Arca',     'country' => 'US', 'rrsp' => true),
        'BTS' => array('label' => 'BATS',          'country' => 'US', 'rrsp' => true)
    );
    if (isset($map[$exchange])) return $map[$exchange];
    // Fallback: check symbol suffix for Canadian
    if (strpos($symbol, '.TO') !== false || strpos($symbol, '.V') !== false) {
        return array('label' => $exchange, 'country' => 'CA', 'rrsp' => true);
    }
    return array('label' => $exchange, 'country' => 'US', 'rrsp' => false);
}

// ── Format results ──
$stocks = array();
foreach ($quotes as $q) {
    $exchange = isset($q['exchange']) ? $q['exchange'] : '';

    // Skip OTC/Pink Sheets
    if (in_array($exchange, $blocked_exchanges)) continue;

    $symbol = isset($q['symbol']) ? $q['symbol'] : '';
    $exinfo = _ps_exchange_info($exchange, $symbol);

    $price      = isset($q['regularMarketPrice'])         ? $q['regularMarketPrice']         : 0;
    $change     = isset($q['regularMarketChange'])        ? round($q['regularMarketChange'], 4) : 0;
    $change_pct = isset($q['regularMarketChangePercent']) ? round($q['regularMarketChangePercent'], 2) : 0;
    $volume     = isset($q['regularMarketVolume'])        ? intval($q['regularMarketVolume']) : 0;
    $avg_vol    = isset($q['averageDailyVolume3Month'])   ? intval($q['averageDailyVolume3Month']) : 0;
    $mcap       = isset($q['marketCap'])                  ? $q['marketCap'] : 0;

    $stocks[] = array(
        'symbol'          => $symbol,
        'name'            => isset($q['shortName']) ? $q['shortName'] : (isset($q['longName']) ? $q['longName'] : ''),
        'price'           => $price,
        'currency'        => isset($q['currency']) ? $q['currency'] : '',
        'change'          => $change,
        'change_pct'      => $change_pct,
        'volume'          => $volume,
        'avg_volume_3m'   => $avg_vol,
        'market_cap'      => $mcap,
        'exchange'        => $exinfo['label'],
        'exchange_raw'    => $exchange,
        'country'         => $exinfo['country'],
        'rrsp_eligible'   => $exinfo['rrsp'],
        'fifty_two_low'   => isset($q['fiftyTwoWeekLow'])  ? $q['fiftyTwoWeekLow']  : 0,
        'fifty_two_high'  => isset($q['fiftyTwoWeekHigh']) ? $q['fiftyTwoWeekHigh'] : 0,
        'day_low'         => isset($q['regularMarketDayLow'])  ? $q['regularMarketDayLow']  : 0,
        'day_high'        => isset($q['regularMarketDayHigh']) ? $q['regularMarketDayHigh'] : 0,
        'prev_close'      => isset($q['regularMarketPreviousClose']) ? $q['regularMarketPreviousClose'] : 0
    );
}

// ── Output ──
$output = array(
    'ok'         => true,
    'region'     => $region,
    'max_price'  => $max_price,
    'min_price'  => $min_price,
    'min_volume' => $min_volume,
    'sort'       => $sort_field,
    'sort_dir'   => $sort_dir,
    'total'      => $total,
    'count'      => count($stocks),
    'offset'     => $offset,
    'size'       => $size,
    'stocks'     => $stocks,
    'cached'     => false,
    'timestamp'  => date('Y-m-d H:i:s')
);

$json = json_encode($output);
@file_put_contents($cache_file, $json);
echo $json;
