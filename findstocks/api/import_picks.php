<?php
/**
 * Import stock picks from daily-stocks.json and pick-performance.json
 * Fetches from the live site URLs.
 * PHP 5.2 compatible.
 *
 * Usage: GET https://findtorontoevents.ca/findstocks/api/import_picks.php
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'imported' => 0, 'skipped' => 0, 'errors' => array());

// ─── Fetch picks from live JSON endpoints ───
$urls = array(
    'https://findtorontoevents.ca/STOCKSUNIFY/data/daily-stocks.json',
    'https://findtorontoevents.ca/data/daily-stocks.json'
);

$all_picks = array();

foreach ($urls as $url) {
    $json = @file_get_contents($url);
    if ($json === false) continue;
    $data = json_decode($json, true);
    if (!$data || !isset($data['stocks'])) continue;

    foreach ($data['stocks'] as $stock) {
        $sym = isset($stock['symbol']) ? $stock['symbol'] : '';
        if ($sym === '') continue;
        // Use pickHash as unique key to allow same stock from different algorithms
        $hash = isset($stock['pickHash']) ? $stock['pickHash'] : ($sym . '_' . (isset($stock['algorithm']) ? $stock['algorithm'] : '') . '_' . (isset($stock['pickedAt']) ? $stock['pickedAt'] : ''));
        if (isset($all_picks[$hash])) continue;
        $all_picks[$hash] = $stock;
    }
}

// Also try pick-performance.json for historical picks
$perf_urls = array(
    'https://findtorontoevents.ca/data/pick-performance.json',
    'https://findtorontoevents.ca/STOCKSUNIFY/data/pick-performance.json'
);
foreach ($perf_urls as $perf_url) {
    $perf_json = @file_get_contents($perf_url);
    if ($perf_json === false) continue;
    $perf_data = json_decode($perf_json, true);
    if (!$perf_data || !isset($perf_data['allPicks'])) continue;
    foreach ($perf_data['allPicks'] as $stock) {
        $sym = isset($stock['symbol']) ? $stock['symbol'] : '';
        if ($sym === '') continue;
        $hash = isset($stock['pickHash']) ? $stock['pickHash'] : ($sym . '_' . (isset($stock['algorithm']) ? $stock['algorithm'] : '') . '_' . (isset($stock['pickedAt']) ? $stock['pickedAt'] : ''));
        if (isset($all_picks[$hash])) continue;
        $all_picks[$hash] = $stock;
    }
}

if (count($all_picks) === 0) {
    $results['ok'] = false;
    $results['errors'][] = 'No picks found from any data source';
    echo json_encode($results);
    $conn->close();
    exit;
}

// ─── Get algorithm ID map ───
$algo_map = array();
$res = $conn->query("SELECT id, name FROM algorithms");
if ($res) {
    while ($row = $res->fetch_assoc()) {
        $algo_map[$row['name']] = (int)$row['id'];
    }
}

// ─── Import each pick ───
foreach ($all_picks as $stock) {
    $ticker     = $conn->real_escape_string(isset($stock['symbol']) ? $stock['symbol'] : '');
    $name       = $conn->real_escape_string(isset($stock['name']) ? $stock['name'] : '');
    $price      = isset($stock['price']) ? (float)$stock['price'] : 0;
    $algo_name  = isset($stock['algorithm']) ? $stock['algorithm'] : 'Unknown';
    $entry      = isset($stock['entryPrice']) ? (float)$stock['entryPrice'] : $price;
    $sim_entry  = isset($stock['simulatedEntryPrice']) ? (float)$stock['simulatedEntryPrice'] : $entry;
    $score_val  = isset($stock['score']) ? (int)$stock['score'] : 0;
    $rating_val = isset($stock['rating']) ? $stock['rating'] : '';
    $risk_val   = isset($stock['risk']) ? $stock['risk'] : 'Medium';
    $tf_val     = isset($stock['timeframe']) ? $stock['timeframe'] : '';
    $sl_price   = isset($stock['stopLoss']) ? (float)$stock['stopLoss'] : 0;
    $pick_hash  = isset($stock['pickHash']) ? $stock['pickHash'] : '';
    $picked_at  = isset($stock['pickedAt']) ? $stock['pickedAt'] : '';

    // Parse pick datetime
    $pick_datetime = '';
    $pick_date = '';
    if ($picked_at !== '') {
        // ISO 8601 format: 2026-01-29T05:25:34.543Z
        $ts = strtotime($picked_at);
        if ($ts !== false) {
            $pick_datetime = date('Y-m-d H:i:s', $ts);
            $pick_date = date('Y-m-d', $ts);
        }
    }
    if ($pick_date === '') {
        $pick_date = date('Y-m-d');
        $pick_datetime = date('Y-m-d H:i:s');
    }

    // Get algorithm ID
    $algo_id = isset($algo_map[$algo_name]) ? $algo_map[$algo_name] : 0;

    // Upsert stock
    $conn->query("INSERT INTO stocks (ticker, company_name) VALUES ('$ticker', '$name')
                  ON DUPLICATE KEY UPDATE company_name='$name'");

    // Check for duplicate pick (same ticker + hash)
    $safe_hash = $conn->real_escape_string($pick_hash);
    $dup = $conn->query("SELECT id FROM stock_picks WHERE ticker='$ticker' AND pick_hash='$safe_hash'");
    if ($dup && $dup->num_rows > 0) {
        $results['skipped']++;
        continue;
    }

    // Insert pick
    $safe_algo   = $conn->real_escape_string($algo_name);
    $safe_rating = $conn->real_escape_string($rating_val);
    $safe_risk   = $conn->real_escape_string($risk_val);
    $safe_tf     = $conn->real_escape_string($tf_val);
    $indicators  = isset($stock['indicators']) ? $conn->real_escape_string(json_encode($stock['indicators'])) : '';

    $sql = "INSERT INTO stock_picks (ticker, algorithm_id, algorithm_name, pick_date, pick_time,
            entry_price, simulated_entry_price, score, rating, risk_level, timeframe,
            stop_loss_price, pick_hash, indicators_json)
            VALUES ('$ticker', $algo_id, '$safe_algo', '$pick_date', '$pick_datetime',
            $entry, $sim_entry, $score_val, '$safe_rating', '$safe_risk', '$safe_tf',
            $sl_price, '$safe_hash', '$indicators')";

    if ($conn->query($sql)) {
        $results['imported']++;
    } else {
        $results['errors'][] = $ticker . ': ' . $conn->error;
    }
}

// Log the import
$now = date('Y-m-d H:i:s');
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$detail = 'Imported ' . $results['imported'] . ', skipped ' . $results['skipped'];
$detail = $conn->real_escape_string($detail);
$conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('import_picks', '$detail', '$ip', '$now')");

echo json_encode($results);
$conn->close();
?>
