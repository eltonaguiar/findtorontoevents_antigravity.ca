<?php
/**
 * EMERGENCY: Check if Brunitarte is in database RIGHT NOW. Admin only.
 */
header('Content-Type: text/plain; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');

require_once dirname(__FILE__) . '/session_auth.php';
require_session_admin();

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    echo "ERROR: Database not available\n";
    exit;
}

// Get user 2's raw JSON
$query = $conn->query("SELECT creators FROM user_lists WHERE user_id = 2");
if (!$query || $query->num_rows === 0) {
    echo "ERROR: User 2 has no creator list\n";
    exit;
}

$row = $query->fetch_assoc();
$raw_json = $row['creators'];
$decoded = json_decode($raw_json, true);

echo "=== DATABASE CHECK ===\n";
echo "Total creators in DB: " . count($decoded) . "\n\n";

echo "All creator names:\n";
foreach ($decoded as $i => $c) {
    $name = isset($c['name']) ? $c['name'] : 'NO_NAME';
    echo ($i + 1) . ". $name\n";
}

echo "\n=== BRUNITARTE CHECK ===\n";
$found = false;
foreach ($decoded as $c) {
    if (isset($c['name']) && $c['name'] === 'Brunitarte') {
        $found = true;
        echo "FOUND! Brunitarte is in the database\n";
        echo "Data: " . json_encode($c) . "\n";
        break;
    }
}

if (!$found) {
    echo "NOT FOUND! Brunitarte is MISSING from database\n";
}

$conn->close();
?>