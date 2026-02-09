<?php
/**
 * Seed monthly trading signals for all forex pairs
 * Creates signals based on first trading day of each month from fx_prices
 * PHP 5.2 compatible
 *
 * Usage: GET or POST .../seed_signals.php
 */
require_once dirname(__FILE__) . '/db_connect.php';

$seeded = 0;
$skipped = 0;
$errors = array();

// Get all pairs
$pairs_res = $conn->query("SELECT DISTINCT pair FROM fx_prices ORDER BY pair");
if (!$pairs_res) {
    echo json_encode(array('ok' => false, 'error' => 'Failed to fetch pairs: ' . $conn->error));
    exit;
}

$pairs = array();
while ($row = $pairs_res->fetch_assoc()) {
    $pairs[] = $row['pair'];
}

// Get all unique months from fx_prices
$months_res = $conn->query("SELECT DISTINCT DATE_FORMAT(trade_date, '%Y-%m-01') as month_start 
                            FROM fx_prices 
                            ORDER BY month_start");
if (!$months_res) {
    echo json_encode(array('ok' => false, 'error' => 'Failed to fetch months: ' . $conn->error));
    exit;
}

$months = array();
while ($row = $months_res->fetch_assoc()) {
    $months[] = $row['month_start'];
}

// For each pair and month, find first trading day and create signal
foreach ($pairs as $pair) {
    $pair_esc = $conn->real_escape_string($pair);
    
    foreach ($months as $month_start) {
        // Find first trading day of this month for this pair
        $month_esc = $conn->real_escape_string($month_start);
        $first_day_res = $conn->query("SELECT trade_date, open_price, close_price 
                                        FROM fx_prices 
                                        WHERE pair = '$pair_esc' 
                                        AND trade_date >= '$month_esc' 
                                        AND trade_date < DATE_ADD('$month_esc', INTERVAL 1 MONTH)
                                        ORDER BY trade_date ASC 
                                        LIMIT 1");
        
        if (!$first_day_res || $first_day_res->num_rows === 0) {
            continue;
        }
        
        $day = $first_day_res->fetch_assoc();
        $signal_date = $day['trade_date'];
        $open_price = (float)$day['open_price'];
        $close_price = (float)$day['close_price'];
        
        if ($open_price <= 0) {
            continue;
        }
        
        // Determine strategy: Trend Following if close > open, Mean Reversion if close < open
        if ($close_price > $open_price) {
            $strategy_name = 'Trend Following';
        } else {
            $strategy_name = 'Mean Reversion';
        }
        
        // Generate signal hash
        $signal_hash = sha1('fx_' . $pair . '_' . $signal_date . '_' . $strategy_name);
        
        // Check for duplicate
        $hash_esc = $conn->real_escape_string($signal_hash);
        $dup_check = $conn->query("SELECT id FROM fx_signals WHERE signal_hash = '$hash_esc'");
        if ($dup_check && $dup_check->num_rows > 0) {
            $skipped++;
            continue;
        }
        
        // Insert signal
        $strategy_esc = $conn->real_escape_string($strategy_name);
        $date_esc = $conn->real_escape_string($signal_date);
        $datetime = date('Y-m-d H:i:s');
        
        $sql = "INSERT INTO fx_signals (pair, strategy_name, signal_date, signal_time, direction, entry_price, signal_hash)
                VALUES ('$pair_esc', '$strategy_esc', '$date_esc', '$datetime', 'long', $open_price, '$hash_esc')";
        
        if ($conn->query($sql)) {
            $seeded++;
        } else {
            $errors[] = "Failed to insert signal for $pair on $signal_date: " . $conn->error;
        }
    }
}

// Audit log
$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : 'unknown';
$ip_esc = $conn->real_escape_string($ip);
$details = "Seeded $seeded signals, skipped $skipped duplicates";
$details_esc = $conn->real_escape_string($details);
$now = date('Y-m-d H:i:s');
$conn->query("INSERT INTO fx_audit_log (action_type, details, ip_address, created_at) 
              VALUES ('seed_signals', '$details_esc', '$ip_esc', '$now')");

$result = array(
    'ok' => true,
    'seeded' => $seeded,
    'skipped' => $skipped,
    'errors' => $errors
);

echo json_encode($result);
$conn->close();
?>
