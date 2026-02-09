<?php
/**
 * DayTrades Miracle Claude — Resolve Pick Outcomes
 * Checks pending picks against latest prices to determine winners/losers.
 * PHP 5.2 compatible.
 *
 * Usage:
 *   GET .../resolve_picks2.php                 — resolve all pending picks
 *   GET .../resolve_picks2.php?days=3          — only resolve picks from last N days
 *   GET .../resolve_picks2.php?max_hold=5      — expire picks older than N days (default 5)
 */
require_once dirname(__FILE__) . '/db_connect2.php';

$results = array('ok' => true, 'resolved' => 0, 'winners' => 0, 'losers' => 0, 'expired' => 0, 'still_pending' => 0, 'errors' => array());

$days_back  = isset($_GET['days']) ? (int)$_GET['days'] : 30;
$max_hold   = isset($_GET['max_hold']) ? (int)$_GET['max_hold'] : 5;

// Get all pending picks
$where = "outcome = 'pending'";
if ($days_back > 0) {
    $where .= " AND scan_date >= DATE_SUB(CURDATE(), INTERVAL $days_back DAY)";
}
$sql = "SELECT * FROM miracle_picks2 WHERE $where ORDER BY scan_date ASC";
$res = $conn->query($sql);

if (!$res) {
    $results['ok'] = false;
    $results['errors'][] = 'Query failed: ' . $conn->error;
    echo json_encode($results);
    $conn->close();
    exit;
}

$pending_picks = array();
while ($row = $res->fetch_assoc()) {
    $pending_picks[] = $row;
}

if (count($pending_picks) === 0) {
    $results['still_pending'] = 0;
    echo json_encode($results);
    $conn->close();
    exit;
}

// Group by ticker for efficient price fetching
$tickers_needed = array();
foreach ($pending_picks as $pick) {
    $tickers_needed[$pick['ticker']] = true;
}

// Fetch current prices from Yahoo
function resolve_fetch_quote($ticker) {
    $url = 'https://query1.finance.yahoo.com/v8/finance/chart/'
         . urlencode($ticker)
         . '?range=10d&interval=1d&includeAdjustedClose=true';

    $ctx = stream_context_create(array(
        'http' => array(
            'method' => 'GET',
            'header' => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n",
            'timeout' => 8
        )
    ));

    $json = @file_get_contents($url, false, $ctx);
    if ($json === false) return null;

    $data = json_decode($json, true);
    if (!$data || !isset($data['chart']['result'][0])) return null;

    $result = $data['chart']['result'][0];
    if (!isset($result['timestamp']) || !isset($result['indicators']['quote'][0])) return null;

    $timestamps = $result['timestamp'];
    $quote = $result['indicators']['quote'][0];

    // Return array of daily bars (date => high/low/close)
    $bars = array();
    $count = count($timestamps);
    for ($i = 0; $i < $count; $i++) {
        $h = isset($quote['high'][$i])  ? $quote['high'][$i]  : null;
        $l = isset($quote['low'][$i])   ? $quote['low'][$i]   : null;
        $c = isset($quote['close'][$i]) ? $quote['close'][$i] : null;
        if ($h === null || $l === null || $c === null) continue;
        $bars[] = array(
            'date'  => date('Y-m-d', $timestamps[$i]),
            'high'  => round($h, 4),
            'low'   => round($l, 4),
            'close' => round($c, 4)
        );
    }
    return $bars;
}

// Fetch prices for all needed tickers
$ticker_prices = array();
$batch = array_keys($tickers_needed);
foreach ($batch as $ticker) {
    $bars = resolve_fetch_quote($ticker);
    if ($bars !== null) {
        $ticker_prices[$ticker] = $bars;
    } else {
        $results['errors'][] = $ticker . ': price fetch failed';
    }
    usleep(200000); // 200ms between requests
}

// Resolve each pick
$now = date('Y-m-d');
foreach ($pending_picks as $pick) {
    $ticker = $pick['ticker'];
    if (!isset($ticker_prices[$ticker])) {
        $results['still_pending']++;
        continue;
    }

    $bars = $ticker_prices[$ticker];
    $entry_price = (float)$pick['entry_price'];
    $tp_price    = (float)$pick['take_profit_price'];
    $sl_price    = (float)$pick['stop_loss_price'];
    $scan_date   = $pick['scan_date'];

    $outcome = 'pending';
    $outcome_price = 0;
    $outcome_pct = 0;
    $outcome_date = '';

    // Check each bar after the scan_date
    foreach ($bars as $bar) {
        if ($bar['date'] <= $scan_date) continue;

        // Check stop loss hit (low touched SL)
        if ($bar['low'] <= $sl_price) {
            $outcome = 'loser';
            $outcome_price = $sl_price;
            $outcome_pct = round((($sl_price - $entry_price) / $entry_price) * 100, 4);
            $outcome_date = $bar['date'];
            break;
        }

        // Check take profit hit (high touched TP)
        if ($bar['high'] >= $tp_price) {
            $outcome = 'winner';
            $outcome_price = $tp_price;
            $outcome_pct = round((($tp_price - $entry_price) / $entry_price) * 100, 4);
            $outcome_date = $bar['date'];
            break;
        }
    }

    // Check if expired (held too long without hitting either target)
    if ($outcome === 'pending') {
        // Calculate days since pick
        $pick_ts = strtotime($scan_date);
        $now_ts  = strtotime($now);
        $hold_days = ($now_ts - $pick_ts) / 86400;

        if ($hold_days >= $max_hold) {
            // Expire: use latest close as exit
            $last_bar = $bars[count($bars) - 1];
            $outcome = 'expired';
            $outcome_price = $last_bar['close'];
            $outcome_pct = round((($last_bar['close'] - $entry_price) / $entry_price) * 100, 4);
            $outcome_date = $last_bar['date'];
        }
    }

    // Update database
    if ($outcome !== 'pending') {
        $safe_outcome = $conn->real_escape_string($outcome);
        $safe_date = $conn->real_escape_string($outcome_date);
        $sql = "UPDATE miracle_picks2 SET outcome='$safe_outcome', outcome_price=$outcome_price, outcome_pct=$outcome_pct, outcome_date='$safe_date' WHERE id=" . (int)$pick['id'];
        if ($conn->query($sql)) {
            $results['resolved']++;
            if ($outcome === 'winner') $results['winners']++;
            elseif ($outcome === 'loser') $results['losers']++;
            elseif ($outcome === 'expired') $results['expired']++;
        }
    } else {
        $results['still_pending']++;
    }
}

// Audit log
$now_ts = date('Y-m-d H:i:s');
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$detail = 'Resolved: ' . $results['resolved'] . ' (W:' . $results['winners'] . ' L:' . $results['losers'] . ' E:' . $results['expired'] . ') Pending:' . $results['still_pending'];
$detail = $conn->real_escape_string($detail);
$conn->query("INSERT INTO miracle_audit2 (action_type, details, ip_address, created_at) VALUES ('resolve', '$detail', '$ip', '$now_ts')");

echo json_encode($results);
$conn->close();
?>
