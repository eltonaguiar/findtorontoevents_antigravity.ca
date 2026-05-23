<?php
header("Content-Type: text/plain; charset=utf-8");
header("Access-Control-Allow-Origin: *");
error_reporting(E_ALL);
ini_set('display_errors', '1');

echo "=== get_cached_updates.php diagnosis ===\n\n";

echo "1. Loading session_auth...\n";
try {
    require_once dirname(__FILE__) . '/session_auth.php';
    echo "   OK\n";
} catch (Exception $e) {
    echo "   ERROR: " . $e->getMessage() . "\n";
}

echo "2. Loading db_connect...\n";
try {
    require_once dirname(__FILE__) . '/db_connect.php';
    echo "   OK\n";
} catch (Exception $e) {
    echo "   ERROR: " . $e->getMessage() . "\n";
}

echo "3. Checking conn...\n";
if (!isset($conn) || !$conn) {
    echo "   FAIL: conn not set\n";
    exit;
}
if ($conn->connect_error) {
    echo "   FAIL: " . $conn->connect_error . "\n";
    exit;
}
echo "   Connected to: " . $conn->server_info . "\n";

echo "4. Loading schema...\n";
try {
    require_once dirname(__FILE__) . '/creator_status_updates_schema.php';
    echo "   OK\n";
} catch (Exception $e) {
    echo "   ERROR: " . $e->getMessage() . "\n";
}

echo "\n5. Checking tables...\n";
$tables = array('user_lists', 'creator_status_updates', 'creator_mentions', 'creators');
foreach ($tables as $t) {
    $r = $conn->query("SHOW TABLES LIKE '$t'");
    if ($r && $r->num_rows > 0) {
        $cnt = $conn->query("SELECT COUNT(*) as c FROM `$t`");
        $row = $cnt ? $cnt->fetch_assoc() : null;
        $count = $row ? $row['c'] : '?';
        echo "   $t: EXISTS ($count rows)\n";
    } else {
        echo "   $t: MISSING\n";
    }
}

echo "\n6. Testing user_lists query for user_id=0...\n";
$r = $conn->query("SELECT creators FROM user_lists WHERE user_id = 0");
if (!$r) {
    echo "   QUERY ERROR: " . $conn->error . "\n";
} else {
    echo "   Rows: " . $r->num_rows . "\n";
    if ($r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $creators_raw = $row['creators'];
        echo "   creators column length: " . strlen($creators_raw) . "\n";
        $decoded = json_decode($creators_raw, true);
        if (is_array($decoded)) {
            echo "   Decoded creators count: " . count($decoded) . "\n";
        } else {
            echo "   json_decode failed: " . json_last_error_msg() . "\n";
            echo "   First 200 chars: " . substr($creators_raw, 0, 200) . "\n";
        }
    }
}

echo "\n7. Running full get_cached_updates logic...\n";
$user_id = 0;
$creators_query = $conn->query("SELECT creators FROM user_lists WHERE user_id = $user_id");
$creators = array();
if ($creators_query && $creators_query->num_rows > 0) {
    $row = $creators_query->fetch_assoc();
    $decoded = json_decode($row['creators'], true);
    if (is_array($decoded)) $creators = $decoded;
}
echo "   Creators loaded: " . count($creators) . "\n";

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
echo "   Account keys: " . count($account_keys) . "\n";

if (!empty($account_keys)) {
    $conditions = array();
    foreach ($account_keys as $ak) {
        $esc_platform = $conn->real_escape_string($ak['platform']);
        $esc_username = $conn->real_escape_string($ak['username']);
        $conditions[] = "(platform = '$esc_platform' AND username = '$esc_username')";
    }
    $where_clause = implode(' OR ', $conditions);
    $sql = "SELECT COUNT(*) as c FROM creator_status_updates WHERE ($where_clause)";
    $r = $conn->query($sql);
    if (!$r) {
        echo "   Status updates query ERROR: " . $conn->error . "\n";
    } else {
        $row = $r->fetch_assoc();
        echo "   Matching status updates: " . $row['c'] . "\n";
    }
}

echo "\n8. Testing json_encode output...\n";
$test_output = array(
    'ok' => true,
    'user_id' => 0,
    'creators_count' => count($creators),
    'accounts_count' => count($account_keys),
    'updates' => array(),
    'cache_stats' => array('total_cached' => 0),
    'from_cache' => true
);
$json = json_encode($test_output);
if ($json === false) {
    echo "   json_encode FAILED: " . json_last_error_msg() . "\n";
} else {
    echo "   json_encode OK (" . strlen($json) . " bytes)\n";
}

echo "\nDiagnosis complete.\n";
$conn->close();
?>