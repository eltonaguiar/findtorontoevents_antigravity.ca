<?php
/**
 * Fetch VIX (CBOE Volatility Index) and SPY data to populate market_regimes table.
 * VIX > 25 = elevated volatility, VIX > 30 = high, VIX > 40 = extreme.
 * Also computes SPY 200-day SMA and classifies regime.
 * PHP 5.2 compatible.
 *
 * Usage: GET .../fetch_vix.php             — fetch last 2 years
 *        GET .../fetch_vix.php?range=5y    — custom range
 *        GET .../fetch_vix.php?force=1     — overwrite existing data
 */
require_once dirname(__FILE__) . '/db_connect.php';

$range = isset($_GET['range']) ? trim($_GET['range']) : '2y';
$force = isset($_GET['force']) ? (int)$_GET['force'] : 0;

$range_map = array('6mo' => 15897600, '1y' => 31536000, '2y' => 63072000, '3y' => 94608000, '5y' => 157680000);
$period_sec = isset($range_map[$range]) ? $range_map[$range] : 63072000;
$now_ts = time();
$from_ts = $now_ts - $period_sec;

$results = array('ok' => true, 'vix_rows' => 0, 'spy_rows' => 0, 'regimes_classified' => 0);

// ─── Helper: fetch Yahoo Finance data ───
function _fetch_yahoo($ticker, $from, $to) {
    $url = 'https://query1.finance.yahoo.com/v8/finance/chart/' . urlencode($ticker)
         . '?period1=' . $from . '&period2=' . $to . '&interval=1d';
    $ctx = stream_context_create(array('http' => array('timeout' => 20, 'header' => "User-Agent: Mozilla/5.0\r\n")));
    $json = @file_get_contents($url, false, $ctx);
    if ($json === false) return null;
    $data = json_decode($json, true);
    if (!$data || !isset($data['chart']['result'][0])) return null;
    return $data['chart']['result'][0];
}

// ─── 1. Fetch VIX data ───
$vix_data = _fetch_yahoo('^VIX', $from_ts, $now_ts);
$vix_by_date = array();

if ($vix_data && isset($vix_data['timestamp'])) {
    $timestamps = $vix_data['timestamp'];
    $quote = isset($vix_data['indicators']['quote'][0]) ? $vix_data['indicators']['quote'][0] : array();

    $cnt = count($timestamps);
    for ($i = 0; $i < $cnt; $i++) {
        if (!isset($timestamps[$i]) || !isset($quote['close'][$i]) || $quote['close'][$i] === null) continue;
        $date = date('Y-m-d', (int)$timestamps[$i]);
        $vix_close = round((float)$quote['close'][$i], 2);
        $vix_by_date[$date] = $vix_close;
    }
    $results['vix_rows'] = count($vix_by_date);
}

// ─── 2. Fetch SPY data ───
$spy_data = _fetch_yahoo('SPY', $from_ts, $now_ts);
$spy_by_date = array();
$spy_closes_ordered = array(); // for SMA calculation

if ($spy_data && isset($spy_data['timestamp'])) {
    $timestamps = $spy_data['timestamp'];
    $quote = isset($spy_data['indicators']['quote'][0]) ? $spy_data['indicators']['quote'][0] : array();

    $cnt = count($timestamps);
    for ($i = 0; $i < $cnt; $i++) {
        if (!isset($timestamps[$i]) || !isset($quote['close'][$i]) || $quote['close'][$i] === null) continue;
        $date = date('Y-m-d', (int)$timestamps[$i]);
        $spy_close = round((float)$quote['close'][$i], 2);
        $spy_by_date[$date] = $spy_close;
        $spy_closes_ordered[] = array('date' => $date, 'close' => $spy_close);
    }
    $results['spy_rows'] = count($spy_by_date);
}

// ─── 3. Compute SPY 200-day SMA and classify regimes ───
$sma_window = 200;
$classified = 0;

for ($i = 0; $i < count($spy_closes_ordered); $i++) {
    $date = $spy_closes_ordered[$i]['date'];
    $spy_close = $spy_closes_ordered[$i]['close'];

    // Calculate SMA200
    $sma200 = 0;
    if ($i >= $sma_window - 1) {
        $sum = 0;
        for ($j = $i - $sma_window + 1; $j <= $i; $j++) {
            $sum += $spy_closes_ordered[$j]['close'];
        }
        $sma200 = round($sum / $sma_window, 2);
    }

    // Get VIX for this date
    $vix = isset($vix_by_date[$date]) ? $vix_by_date[$date] : 0;

    // Classify regime
    $regime = 'unknown';
    if ($vix > 0 && $sma200 > 0) {
        if ($vix >= 35) {
            $regime = 'extreme_vol';
        } elseif ($vix >= 25) {
            $regime = 'high_vol';
        } elseif ($vix >= 20) {
            if ($spy_close >= $sma200) {
                $regime = 'moderate_bull';
            } else {
                $regime = 'moderate_bear';
            }
        } else {
            // VIX < 20 = calm
            if ($spy_close >= $sma200) {
                $regime = 'calm_bull';
            } else {
                $regime = 'calm_bear';
            }
        }
    } elseif ($vix > 0) {
        // No SMA yet but have VIX
        if ($vix >= 35) $regime = 'extreme_vol';
        elseif ($vix >= 25) $regime = 'high_vol';
        elseif ($vix >= 20) $regime = 'moderate';
        else $regime = 'calm';
    }

    // Insert/update
    $safe_date = $conn->real_escape_string($date);
    if ($force) {
        $sql = "REPLACE INTO market_regimes (trade_date, spy_close, spy_sma200, vix_close, regime)
                VALUES ('$safe_date', $spy_close, $sma200, $vix, '$regime')";
    } else {
        $sql = "INSERT INTO market_regimes (trade_date, spy_close, spy_sma200, vix_close, regime)
                VALUES ('$safe_date', $spy_close, $sma200, $vix, '$regime')
                ON DUPLICATE KEY UPDATE spy_close=$spy_close, spy_sma200=$sma200, vix_close=$vix, regime='$regime'";
    }
    if ($conn->query($sql)) $classified++;
}

$results['regimes_classified'] = $classified;

// ─── Summary stats ───
$regime_counts = array();
$r = $conn->query("SELECT regime, COUNT(*) as cnt FROM market_regimes GROUP BY regime ORDER BY cnt DESC");
if ($r) { while ($row = $r->fetch_assoc()) $regime_counts[$row['regime']] = (int)$row['cnt']; }
$results['regime_distribution'] = $regime_counts;

// Latest VIX
$r = $conn->query("SELECT trade_date, vix_close, spy_close, spy_sma200, regime FROM market_regimes ORDER BY trade_date DESC LIMIT 1");
if ($r && $row = $r->fetch_assoc()) $results['latest'] = $row;

// VIX stats
$r = $conn->query("SELECT AVG(vix_close) as avg_vix, MIN(vix_close) as min_vix, MAX(vix_close) as max_vix,
                    STDDEV(vix_close) as std_vix FROM market_regimes WHERE vix_close > 0");
if ($r && $row = $r->fetch_assoc()) {
    $results['vix_stats'] = array(
        'avg' => round((float)$row['avg_vix'], 2),
        'min' => round((float)$row['min_vix'], 2),
        'max' => round((float)$row['max_vix'], 2),
        'std' => round((float)$row['std_vix'], 2)
    );
}

// Audit
$now = date('Y-m-d H:i:s');
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at)
              VALUES ('fetch_vix', 'VIX rows: " . count($vix_by_date) . ", SPY rows: " . count($spy_by_date) . ", Classified: $classified', '$ip', '$now')");

echo json_encode($results);
$conn->close();
?>
