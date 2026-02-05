<?php
/**
 * Debug script: Check raw JSON from database and validate it. Admin only.
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');

require_once dirname(__FILE__) . '/session_auth.php';
require_session_admin();

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

// Get user 2's raw JSON
$query = $conn->query("SELECT creators FROM user_lists WHERE user_id = 2");
if (!$query || $query->num_rows === 0) {
    echo json_encode(array('error' => 'User 2 has no creator list'));
    exit;
}

$row = $query->fetch_assoc();
$raw_json = $row['creators'];

// Try to decode it
$decoded = json_decode($raw_json, true);
$decode_error = json_last_error_msg();

// Count creators
$count = is_array($decoded) ? count($decoded) : 0;

// Find Brunitarte
$brunitarte_index = -1;
$brunitarte_data = null;
if (is_array($decoded)) {
    foreach ($decoded as $i => $c) {
        if (isset($c['name']) && $c['name'] === 'Brunitarte') {
            $brunitarte_index = $i;
            $brunitarte_data = $c;
            break;
        }
    }
}

// Re-encode to see if it matches
$re_encoded = json_encode($decoded);
$matches_original = ($re_encoded === $raw_json);

// Get all creator names
$all_names = array();
if (is_array($decoded)) {
    foreach ($decoded as $c) {
        $all_names[] = isset($c['name']) ? $c['name'] : 'NO_NAME';
    }
}

$result = array(
    'raw_json_length' => strlen($raw_json),
    'decode_error' => $decode_error,
    'creator_count' => $count,
    'brunitarte_found' => $brunitarte_index >= 0,
    'brunitarte_index' => $brunitarte_index,
    'brunitarte_data' => $brunitarte_data,
    're_encode_matches' => $matches_original,
    'all_creator_names' => $all_names
);

echo json_encode($result);
$conn->close();
?>