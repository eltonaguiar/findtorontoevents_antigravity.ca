<?php
// Manually fix the remaining unmatched IDs
error_reporting(E_ALL);
ini_set('display_errors', 1);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: text/plain');

echo "=== Manually Fixing Unmatched IDs ===\n\n";

// ID mappings based on the pattern
// '44280078' is likely Lofe
// '491' is likely part of Zople's UUID
// '8' and '86' need investigation

$manual_fixes = array(
    // Check what these IDs actually are
);

// First, let's see what content these IDs have
$unmatched = array('8', '86', '491', '44280078');

foreach ($unmatched as $id) {
    $sql = "SELECT id, title, platform FROM creator_mentions WHERE creator_id = '$id' LIMIT 1";
    $result = $conn->query($sql);

    if ($result && $result->num_rows > 0) {
        $row = $result->fetch_assoc();
        echo "ID '$id': {$row['title']}\n";

        // Try to guess the creator from the title
        $title_lower = strtolower($row['title']);

        if (strpos($title_lower, 'lofe') !== false) {
            echo "  → Likely LOFE\n";
            // Find Lofe's correct ID
            $find = $conn->query("SELECT id FROM creators WHERE name LIKE '%lofe%'");
            if ($find && $find->num_rows > 0) {
                $creator = $find->fetch_assoc();
                $conn->query("UPDATE creator_mentions SET creator_id = '{$creator['id']}' WHERE creator_id = '$id'");
                echo "  ✅ Fixed to ID: {$creator['id']}\n";
            }
        } elseif (strpos($title_lower, 'zople') !== false) {
            echo "  → Likely ZOPLE\n";
            $find = $conn->query("SELECT id FROM creators WHERE name LIKE '%zople%'");
            if ($find && $find->num_rows > 0) {
                $creator = $find->fetch_assoc();
                $conn->query("UPDATE creator_mentions SET creator_id = '{$creator['id']}' WHERE creator_id = '$id'");
                echo "  ✅ Fixed to ID: {$creator['id']}\n";
            }
        } elseif (strpos($title_lower, 'ninja') !== false) {
            echo "  → Likely NINJA\n";
            $find = $conn->query("SELECT id FROM creators WHERE name LIKE '%ninja%'");
            if ($find && $find->num_rows > 0) {
                $creator = $find->fetch_assoc();
                $conn->query("UPDATE creator_mentions SET creator_id = '{$creator['id']}' WHERE creator_id = '$id'");
                echo "  ✅ Fixed to ID: {$creator['id']}\n";
            }
        } elseif (strpos($title_lower, 'xqc') !== false) {
            echo "  → Likely XQC\n";
            $find = $conn->query("SELECT id FROM creators WHERE name LIKE '%xqc%'");
            if ($find && $find->num_rows > 0) {
                $creator = $find->fetch_assoc();
                $conn->query("UPDATE creator_mentions SET creator_id = '{$creator['id']}' WHERE creator_id = '$id'");
                echo "  ✅ Fixed to ID: {$creator['id']}\n";
            }
        } elseif (strpos($title_lower, 'pokimane') !== false) {
            echo "  → Likely POKIMANE\n";
            $find = $conn->query("SELECT id FROM creators WHERE name LIKE '%pokimane%'");
            if ($find && $find->num_rows > 0) {
                $creator = $find->fetch_assoc();
                $conn->query("UPDATE creator_mentions SET creator_id = '{$creator['id']}' WHERE creator_id = '$id'");
                echo "  ✅ Fixed to ID: {$creator['id']}\n";
            }
        }
    }
    echo "\n";
}

echo "\n=== Checking Pokimane ===\n";
$poki_sql = "SELECT id, name, follower_count FROM creators WHERE name LIKE '%pokimane%'";
$poki_result = $conn->query($poki_sql);
if ($poki_result && $poki_result->num_rows > 0) {
    $poki = $poki_result->fetch_assoc();
    echo "Found: {$poki['name']} (ID: {$poki['id']}, Followers: {$poki['follower_count']})\n";

    // Check content
    $content_sql = "SELECT COUNT(*) as count FROM creator_mentions WHERE creator_id = '{$poki['id']}'";
    $content_result = $conn->query($content_sql);
    $content = $content_result->fetch_assoc();
    echo "Content items: {$content['count']}\n";
} else {
    echo "Pokimane NOT FOUND in creators table\n";
}

$conn->close();
?>