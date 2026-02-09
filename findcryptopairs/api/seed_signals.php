<?php
/**
 * Seed monthly trading signals for all crypto pairs
 * Creates signals based on first trading day of each month in cp_prices
 * PHP 5.2 compatible
 * Usage: GET .../seed_signals.php
 */
require_once dirname(__FILE__) . '/db_connect.php';

$results = array('ok' => true, 'seeded' => 0, 'skipped' => 0, 'errors' => array());

// Get all pairs
$pairs_res = $conn->query("SELECT DISTINCT pair FROM cp_prices ORDER BY pair");
if (!$pairs_res) {
    $results['ok'] = false;
    $results['errors'][] = 'Failed to fetch pairs: ' . $conn->error;
    echo json_encode($results);
    $conn->close();
    exit;
}

$pairs = array();
while ($row = $pairs_res->fetch_assoc()) {
    $pairs[] = $row['pair'];
}

if (count($pairs) === 0) {
    $results['errors'][] = 'No pairs found in cp_prices. Run fetch_prices.php first.';
    echo json_encode($results);
    $conn->close();
    exit;
}

// For each pair, find first trading day of each month
foreach ($pairs as $pair) {
    $safe_pair = $conn->real_escape_string($pair);
    
    // Get all unique year-month combinations for this pair
    $months_res = $conn->query("SELECT DISTINCT YEAR(trade_date) as yr, MONTH(trade_date) as mo 
                                 FROM cp_prices 
                                 WHERE pair='$safe_pair' 
                                 ORDER BY yr, mo");
    
    if (!$months_res) continue;
    
    while ($month_row = $months_res->fetch_assoc()) {
        $yr = (int)$month_row['yr'];
        $mo = (int)$month_row['mo'];
        
        // Find first trading day of this month
        $first_day_sql = "SELECT trade_date, open_price, close_price 
                          FROM cp_prices 
                          WHERE pair='$safe_pair' 
                          AND YEAR(trade_date)=$yr 
                          AND MONTH(trade_date)=$mo 
                          ORDER BY trade_date ASC 
                          LIMIT 1";
        
        $first_day_res = $conn->query($first_day_sql);
        if (!$first_day_res || $first_day_res->num_rows === 0) continue;
        
        $price_row = $first_day_res->fetch_assoc();
        $signal_date = $price_row['trade_date'];
        $open_price = (float)$price_row['open_price'];
        $close_price = (float)$price_row['close_price'];
        
        // Determine strategy based on close vs open
        if ($close_price > $open_price) {
            $strategy_name = 'Trend Following';
        } else {
            $strategy_name = 'Mean Reversion';
        }
        
        // Generate signal hash
        $signal_hash = sha1('cp_' . $pair . '_' . $signal_date . '_' . $strategy_name);
        
        // Check for duplicate
        $safe_hash = $conn->real_escape_string($signal_hash);
        $dup_check = $conn->query("SELECT id FROM cp_signals WHERE signal_hash='$safe_hash' LIMIT 1");
        if ($dup_check && $dup_check->num_rows > 0) {
            $results['skipped']++;
            continue;
        }
        
        // Insert signal
        $safe_strategy = $conn->real_escape_string($strategy_name);
        $safe_date = $conn->real_escape_string($signal_date);
        $signal_time = date('Y-m-d H:i:s');
        $safe_time = $conn->real_escape_string($signal_time);
        
        $insert_sql = "INSERT INTO cp_signals 
                       (pair, strategy_name, signal_date, signal_time, direction, entry_price, signal_hash) 
                       VALUES ('$safe_pair', '$safe_strategy', '$safe_date', '$safe_time', 'long', $open_price, '$safe_hash')";
        
        if ($conn->query($insert_sql)) {
            $results['seeded']++;
        } else {
            $results['errors'][] = $pair . ' ' . $signal_date . ': ' . $conn->error;
        }
    }
}

// Audit log
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$now = date('Y-m-d H:i:s');
$details = 'Seeded ' . $results['seeded'] . ' signals, skipped ' . $results['skipped'];
$conn->query("INSERT INTO cp_audit_log (action_type, details, ip_address, created_at) 
              VALUES ('seed_signals', '" . $conn->real_escape_string($details) . "', '$ip', '$now')");

echo json_encode($results);
$conn->close();
?>
