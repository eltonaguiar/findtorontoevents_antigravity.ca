<?php
/**
 * Backfill script: copy guest list (user_id=0) to all existing users who don't have a list yet. Admin only.
 * GET: returns JSON with count of users backfilled.
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

// Get guest list
$guest_query = $conn->query("SELECT creators FROM user_lists WHERE user_id = 0");
if (!$guest_query || $guest_query->num_rows === 0) {
    echo json_encode(array('error' => 'No guest list found (user_id=0)', 'backfilled' => 0));
    $conn->close();
    exit;
}

$guest_row = $guest_query->fetch_assoc();
$guest_creators = $guest_row['creators'];
$guest_creators_esc = $conn->real_escape_string($guest_creators);
$guest_count = count(json_decode($guest_creators, true));

// Get all users who don't have a list yet
$users_query = $conn->query("SELECT id, email FROM users WHERE id NOT IN (SELECT user_id FROM user_lists)");
$backfilled = 0;

if ($users_query) {
    while ($user = $users_query->fetch_assoc()) {
        $user_id = $user['id'];
        $email = $user['email'];

        // Insert guest list for this user
        $insert = $conn->query("INSERT INTO user_lists (user_id, creators) VALUES ($user_id, '$guest_creators_esc')");

        if ($insert) {
            $backfilled++;
        }
    }
}

echo json_encode(array(
    'status' => 'success',
    'backfilled' => $backfilled,
    'guest_creator_count' => $guest_count
));

$conn->close();
?>