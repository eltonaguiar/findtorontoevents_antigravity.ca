<?php
// Sync creators from user_lists to creators table
// This fixes the data integrity issue where quick-add creators aren't in the creators table
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: application/json');

// Known follower counts for popular creators
$known_followers = array(
    'zople' => 600000,
    'lofe' => 2150000,
    'adin ross' => 500000,
    'xqc' => 2000000,
    'pokimane' => 9000000,
    'ninja' => 18000000,
    'shroud' => 10000000,
    'summit1g' => 6000000,
    'drlupo' => 4500000,
    'timthetatman' => 7000000,
    'mrbeast' => 200000000
);

$added = array();
$updated = array();
$skipped = array();

// Get all user lists
$users_sql = "SELECT user_id, creators FROM user_lists";
$users_result = $conn->query($users_sql);

if (!$users_result) {
    echo json_encode(array('error' => 'Failed to query user_lists: ' . $conn->error));
    exit;
}

while ($user_row = $users_result->fetch_assoc()) {
    $creators_data = json_decode($user_row['creators'], true);

    if (!$creators_data)
        continue;

    foreach ($creators_data as $creator) {
        if (!isset($creator['id']) || !isset($creator['name']))
            continue;

        $id = $conn->real_escape_string($creator['id']);
        $name = $conn->real_escape_string($creator['name']);

        // Check if creator exists
        $check_sql = "SELECT id FROM creators WHERE id = '$id'";
        $check_result = $conn->query($check_sql);

        if ($check_result->num_rows == 0) {
            // Creator doesn't exist - add them
            $follower_count = 0;

            // Check if we have known follower count
            $name_lower = strtolower($name);
            if (isset($known_followers[$name_lower])) {
                $follower_count = $known_followers[$name_lower];
            }

            // Extract other fields if available
            $avatar_url = isset($creator['avatarUrl']) ? $conn->real_escape_string($creator['avatarUrl']) : '';
            $bio = isset($creator['bio']) ? $conn->real_escape_string($creator['bio']) : '';
            $category = isset($creator['category']) ? $conn->real_escape_string($creator['category']) : '';

            $insert_sql = "INSERT INTO creators (id, name, follower_count, avatar_url, bio, category) 
                          VALUES ('$id', '$name', $follower_count, '$avatar_url', '$bio', '$category')";

            if ($conn->query($insert_sql)) {
                $added[] = array(
                    'id' => $id,
                    'name' => $name,
                    'follower_count' => $follower_count
                );
            } else {
                // Log error but continue
                error_log("Failed to insert creator $name: " . $conn->error);
            }
        } else {
            // Creator exists - update follower count if we have better data
            $name_lower = strtolower($name);
            if (isset($known_followers[$name_lower])) {
                $follower_count = $known_followers[$name_lower];
                $update_sql = "UPDATE creators SET follower_count = $follower_count WHERE id = '$id'";
                $conn->query($update_sql);

                if ($conn->affected_rows > 0) {
                    $updated[] = array(
                        'id' => $id,
                        'name' => $name,
                        'follower_count' => $follower_count
                    );
                }
            } else {
                $skipped[] = $name;
            }
        }
    }
}

echo json_encode(array(
    'added' => $added,
    'updated' => $updated,
    'total_added' => count($added),
    'total_updated' => count($updated),
    'total_skipped' => count(array_unique($skipped))
), JSON_PRETTY_PRINT);

$conn->close();
?>