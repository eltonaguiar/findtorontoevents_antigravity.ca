<?php
/**
 * Force no-cache headers and return user 2's creators. Admin only.
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Cache-Control: post-check=0, pre-check=0', false);
header('Pragma: no-cache');
header('Expires: 0');

require_once dirname(__FILE__) . '/session_auth.php';
require_session_admin();

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

$user_id = 2; // Force user 2

// Get user 2's raw JSON
$query = $conn->query("SELECT creators FROM user_lists WHERE user_id = $user_id");
if (!$query || $query->num_rows === 0) {
    echo json_encode(array('error' => 'User 2 has no creator list'));
    exit;
}

$row = $query->fetch_assoc();
$raw_json = $row['creators'];
$decoded = json_decode($raw_json, true);

// Count and check for Brunitarte
$count = is_array($decoded) ? count($decoded) : 0;
$has_brunitarte = false;
if (is_array($decoded)) {
    foreach ($decoded as $c) {
        if (isset($c['name']) && $c['name'] === 'Brunitarte') {
            $has_brunitarte = true;
            break;
        }
    }
}

// Add debug headers
header("X-Creator-Count: $count");
header("X-Has-Brunitarte: " . ($has_brunitarte ? 'true' : 'false'));
header("X-Timestamp: " . time());

echo json_encode(array(
    'creators' => $decoded,
    'debug' => array(
        'count' => $count,
        'has_brunitarte' => $has_brunitarte,
        'timestamp' => time()
    )
));

$conn->close();
?>