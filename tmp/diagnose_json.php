<?php
header("Content-Type: text/plain; charset=utf-8");
error_reporting(E_ALL);
ini_set('display_errors', '1');

require_once dirname(__FILE__) . '/session_auth.php';
require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/creator_status_updates_schema.php';

if (!isset($conn) || !$conn) {
    echo "No DB connection\n";
    exit;
}

echo "DB connected OK\n\n";

$user_id = 0;
$creators_query = $conn->query("SELECT creators FROM user_lists WHERE user_id = $user_id");
$creators = array();
if ($creators_query && $creators_query->num_rows > 0) {
    $row = $creators_query->fetch_assoc();
    $decoded = json_decode($row['creators'], true);
    if (is_array($decoded)) $creators = $decoded;
}
echo "Creators: " . count($creators) . "\n";

// Test json_encode on creators data
$test = json_encode($creators);
if ($test === false) {
    echo "ERROR: json_encode(creators) failed: " . json_last_error_msg() . "\n";
    // Find which creator has the issue
    foreach ($creators as $i => $c) {
        $t = json_encode($c);
        if ($t === false) {
            echo "  Bad creator index $i: " . json_last_error_msg() . "\n";
            echo "  Name: " . (isset($c['name']) ? $c['name'] : '?') . "\n";
            // Check each field
            foreach ($c as $k => $v) {
                if (is_string($v) && json_encode($v) === false) {
                    echo "    Bad field '$k': len=" . strlen($v) . " err=" . json_last_error_msg() . "\n";
                    echo "    hex: " . bin2hex(substr($v, 0, 50)) . "\n";
                }
            }
        }
    }
} else {
    echo "creators json_encode OK (" . strlen($test) . " bytes)\n";
}

// Now test the full update query
$account_keys = array();
foreach ($creators as $creator) {
    if (isset($creator['accounts']) && is_array($creator['accounts'])) {
        foreach ($creator['accounts'] as $account) {
            $platform = isset($account['platform']) ? strtolower($account['platform']) : '';
            $username = isset($account['username']) ? $account['username'] : '';
            if ($platform !== '' && $username !== '' && $platform !== 'other') {
                $account_keys[] = array('platform' => $platform, 'username' => $username);
            }
        }
    }
}

echo "Account keys: " . count($account_keys) . "\n\n";

$updates = array();
if (!empty($account_keys)) {
    $conditions = array();
    foreach ($account_keys as $ak) {
        $conditions[] = "(platform = '" . $conn->real_escape_string($ak['platform']) . "' AND username = '" . $conn->real_escape_string($ak['username']) . "')";
    }
    $where_clause = implode(' OR ', $conditions);
    $sql = "SELECT * FROM creator_status_updates WHERE ($where_clause) ORDER BY is_live DESC, content_published_at DESC, last_checked DESC LIMIT 500";
    $result = $conn->query($sql);
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $updates[] = $row;
            $t = json_encode($row);
            if ($t === false) {
                echo "BAD ROW id=" . $row['id'] . " platform=" . $row['platform'] . " username=" . $row['username'] . "\n";
                echo "  json error: " . json_last_error_msg() . "\n";
                foreach ($row as $k => $v) {
                    if (is_string($v) && json_encode($v) === false) {
                        echo "  bad field '$k': len=" . strlen($v) . " err=" . json_last_error_msg() . "\n";
                        echo "  hex dump: " . bin2hex(substr($v, 0, 100)) . "\n";
                    }
                }
            }
        }
        echo "Status updates: " . count($updates) . " rows fetched\n";
    } else {
        echo "Query error: " . $conn->error . "\n";
    }
}

// Test mentions
$creator_ids = array();
foreach ($creators as $c) {
    if (isset($c['id']) && $c['id'] !== '') {
        $creator_ids[] = $conn->real_escape_string($c['id']);
    }
}

echo "\nTesting creator_mentions...\n";
if (!empty($creator_ids)) {
    $all_ids = array();
    foreach ($creator_ids as $cid) {
        $all_ids[] = $cid;
        if (preg_match('/^(\d+)-/', $cid, $matches)) {
            $all_ids[] = $matches[1];
        }
    }
    $ids_in = "'" . implode("','", array_unique($all_ids)) . "'";
    $mentions_sql = "SELECT cm.*, c.name as creator_name, c.avatar_url as creator_avatar FROM creator_mentions cm LEFT JOIN creators c ON cm.creator_id = c.id WHERE cm.creator_id IN ($ids_in) ORDER BY cm.posted_at DESC LIMIT 100";
    $mentions_result = $conn->query($mentions_sql);
    if ($mentions_result) {
        $mention_count = 0;
        while ($row = $mentions_result->fetch_assoc()) {
            $mention_count++;
            $t = json_encode($row);
            if ($t === false) {
                echo "BAD MENTION id=" . $row['id'] . " platform=" . $row['platform'] . "\n";
                echo "  json error: " . json_last_error_msg() . "\n";
                foreach ($row as $k => $v) {
                    if (is_string($v) && json_encode($v) === false) {
                        echo "  bad field '$k': len=" . strlen($v) . " err=" . json_last_error_msg() . "\n";
                        echo "  hex dump: " . bin2hex(substr($v, 0, 100)) . "\n";
                    }
                }
            }
        }
        echo "Mentions: $mention_count rows fetched\n";
    } else {
        echo "Mentions query error: " . $conn->error . "\n";
    }
}

// Test the FULL json_encode like the real script would
echo "\nBuilding full response...\n";
$full_response = array(
    'ok' => true,
    'user_id' => $user_id,
    'is_guest' => true,
    'creators_count' => count($creators),
    'accounts_count' => count($account_keys),
    'updates' => $updates,
    'cache_stats' => array('total_cached' => count($updates)),
    'from_cache' => true
);

$json = json_encode($full_response);
if ($json === false) {
    echo "FULL json_encode FAILED: " . json_last_error_msg() . "\n";
    echo "json_last_error code: " . json_last_error() . "\n";
    
    // Try with JSON_INVALID_UTF8_SUBSTITUTE
    $json2 = json_encode($full_response, JSON_INVALID_UTF8_SUBSTITUTE);
    if ($json2 !== false) {
        echo "With JSON_INVALID_UTF8_SUBSTITUTE: OK (" . strlen($json2) . " bytes)\n";
    } else {
        echo "Even with substitute: FAILED\n";
    }
} else {
    echo "Full json_encode OK (" . strlen($json) . " bytes)\n";
}

$conn->close();
echo "\nDone.\n";
?>