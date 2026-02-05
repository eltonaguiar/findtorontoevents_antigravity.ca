<?php
// Fix creator_mentions to use correct creator IDs
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: text/plain');

echo "=== Fixing Creator IDs in creator_mentions ===\n\n";

// Get all unique creator_ids from creator_mentions
$sql = "SELECT DISTINCT creator_id FROM creator_mentions";
$result = $conn->query($sql);

$fixed = 0;
$not_found = array();

while ($row = $result->fetch_assoc()) {
    $wrong_id = $row['creator_id'];

    // Try to find the correct creator by name match
    // The wrong_id might be a name, numeric ID, or partial match
    $search_sql = "SELECT id, name FROM creators WHERE 
                   name LIKE '%" . $conn->real_escape_string($wrong_id) . "%' OR
                   id = '" . $conn->real_escape_string($wrong_id) . "'
                   LIMIT 1";

    $search_result = $conn->query($search_sql);

    if ($search_result && $search_result->num_rows > 0) {
        $creator = $search_result->fetch_assoc();
        $correct_id = $creator['id'];

        if ($wrong_id != $correct_id) {
            // Update creator_mentions
            $update_sql = "UPDATE creator_mentions 
                          SET creator_id = '" . $conn->real_escape_string($correct_id) . "' 
                          WHERE creator_id = '" . $conn->real_escape_string($wrong_id) . "'";

            if ($conn->query($update_sql)) {
                echo "✅ Fixed: '$wrong_id' → '{$creator['name']}' (ID: $correct_id) - {$conn->affected_rows} rows\n";
                $fixed += $conn->affected_rows;
            } else {
                echo "❌ Error updating: " . $conn->error . "\n";
            }
        } else {
            echo "✓ Already correct: {$creator['name']} (ID: $correct_id)\n";
        }
    } else {
        $not_found[] = $wrong_id;
        echo "⚠️  No match found for: '$wrong_id'\n";
    }
}

echo "\n=== Summary ===\n";
echo "Fixed: $fixed rows\n";
echo "Not found: " . count($not_found) . " IDs\n";

if (count($not_found) > 0) {
    echo "\nUnmatched IDs:\n";
    foreach ($not_found as $id) {
        echo "  - $id\n";
    }
}

$conn->close();
?>