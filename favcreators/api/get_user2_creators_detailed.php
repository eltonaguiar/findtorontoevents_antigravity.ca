<?php
// Get all creators that user 2 follows with their current status
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: application/json');

$user_id = 2;

// Get user's followed creators
$user_list_sql = "SELECT creators FROM user_lists WHERE user_id = $user_id";
$user_list_result = $conn->query($user_list_sql);

$results = array();

if ($user_list_result && $user_list_result->num_rows > 0) {
    $row = $user_list_result->fetch_assoc();
    $creators_data = json_decode($row['creators'], true);

    foreach ($creators_data as $creator_json) {
        if (!isset($creator_json['id']))
            continue;

        $cid = $conn->real_escape_string($creator_json['id']);

        // Check if exists in creators table
        $check_sql = "SELECT id, name, follower_count FROM creators WHERE id = '$cid'";
        $check_result = $conn->query($check_sql);

        if ($check_result && $check_result->num_rows > 0) {
            $creator = $check_result->fetch_assoc();

            // Check if has content
            $content_sql = "SELECT COUNT(*) as count FROM creator_mentions WHERE creator_id = '$cid'";
            $content_result = $conn->query($content_sql);
            $content_row = $content_result->fetch_assoc();

            $results[] = array(
                'id' => $creator['id'],
                'name' => $creator['name'],
                'follower_count' => intval($creator['follower_count']),
                'content_count' => intval($content_row['count']),
                'passes_filter' => ($creator['follower_count'] >= 50000 && $content_row['count'] > 0)
            );
        }
    }
}

echo json_encode(array(
    'total_followed' => count($results),
    'creators' => $results
), JSON_PRETTY_PRINT);

$conn->close();
?>