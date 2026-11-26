<?php
error_reporting(0);
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/ensure_tables.php';

$response = [
    'database' => 'connected',
    'tables' => [],
    'test_user' => null,
    'test_friend' => null,
    'test_hangout' => null
];

// Check if tables exist
$tables_to_check = ['friendt_friends', 'friendt_hangouts', 'friendt_events', 'users'];
foreach ($tables_to_check as $table) {
    $result = $conn->query("SHOW TABLES LIKE '$table'");
    $response['tables'][$table] = $result && $result->num_rows > 0;
}

// Check John Doe user
$john_result = $conn->query("SELECT id, email, display_name FROM users WHERE email = 'johndoe'");
if ($john_result && $john_result->num_rows > 0) {
    $john = $john_result->fetch_assoc();
    $response['test_user'] = $john;
    
    // Check Jane Doe friend
    $jane_result = $conn->query("SELECT id, name, nickname, tags FROM friendt_friends WHERE user_id = {$john['id']} AND id = 'jd_20260302'");
    if ($jane_result && $jane_result->num_rows > 0) {
        $jane = $jane_result->fetch_assoc();
        $response['test_friend'] = $jane;
        $response['test_friend']['tags'] = json_decode($jane['tags'], true);
        
        // Check hangout
        $hangout_result = $conn->query("SELECT id, date, activity FROM friendt_hangouts WHERE friend_id = 'jd_20260302' AND user_id = {$john['id']}");
        if ($hangout_result && $hangout_result->num_rows > 0) {
            $hangout = $hangout_result->fetch_assoc();
            $response['test_hangout'] = $hangout;
        }
    }
}

// Count total friends (should be at least 1)
$friend_count = $conn->query("SELECT COUNT(*) as count FROM friendt_friends WHERE user_id = {$john['id']}");
if ($friend_count) {
    $response['friend_count'] = $friend_count->fetch_assoc()['count'];
}

echo json_encode($response, JSON_PRETTY_PRINT);
$conn->close();
?>