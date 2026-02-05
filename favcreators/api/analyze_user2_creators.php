<?php
// Check which creators user 2 follows and why they don't appear
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: text/plain');

echo "=== User 2 Followed Creators Analysis ===\n\n";

$user_id = 2;

// Get user's followed creators
$user_list_sql = "SELECT creators FROM user_lists WHERE user_id = $user_id";
$user_list_result = $conn->query($user_list_sql);

if ($user_list_result && $user_list_result->num_rows > 0) {
    $row = $user_list_result->fetch_assoc();
    $creators_data = json_decode($row['creators'], true);

    echo "User 2 follows " . count($creators_data) . " creators total\n\n";

    // Extract IDs
    $creator_ids = array();
    foreach ($creators_data as $creator) {
        if (isset($creator['id'])) {
            $creator_ids[] = $conn->real_escape_string($creator['id']);
        }
    }

    // Check each creator
    echo "Checking each creator:\n";
    echo str_repeat("-", 80) . "\n";

    foreach ($creator_ids as $cid) {
        // Check if exists in creators table
        $check_sql = "SELECT id, name, follower_count FROM creators WHERE id = '$cid'";
        $check_result = $conn->query($check_sql);

        if ($check_result && $check_result->num_rows > 0) {
            $creator = $check_result->fetch_assoc();

            // Check if has content
            $content_sql = "SELECT COUNT(*) as count FROM creator_mentions WHERE creator_id = '$cid'";
            $content_result = $conn->query($content_sql);
            $content_row = $content_result->fetch_assoc();

            $status = "";
            if ($creator['follower_count'] < 50000) {
                $status = "❌ Below 50K followers";
            } elseif ($content_row['count'] == 0) {
                $status = "❌ No content in creator_mentions";
            } else {
                $status = "✅ VISIBLE (" . $content_row['count'] . " items)";
            }

            echo sprintf(
                "%-20s | Followers: %10s | %s\n",
                $creator['name'],
                number_format($creator['follower_count']),
                $status
            );
        } else {
            echo sprintf("%-20s | NOT IN creators TABLE\n", $cid);
        }
    }
}

$conn->close();
?>