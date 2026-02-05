<?php
/**
 * Debug endpoint to check what user 2's data looks like. Admin only.
 */

header('Content-Type: text/plain; charset=utf-8');
header('Access-Control-Allow-Credentials: true');

require_once dirname(__FILE__) . '/session_auth.php';
require_session_admin();

require_once dirname(__FILE__) . '/db_config.php';
$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

echo "=== DEBUG: User 2 (zerounderscore@gmail.com) ===\n\n";

// Get user_lists data
$query = "SELECT creators FROM user_lists WHERE user_id = 2";
$result = $conn->query($query);

if ($result && $result->num_rows > 0) {
    $row = $result->fetch_assoc();
    $creators_json = $row['creators'];

    echo "Raw JSON length: " . strlen($creators_json) . " bytes\n\n";

    $creators = json_decode($creators_json, true);

    if ($creators === null) {
        echo "ERROR: JSON decode failed!\n";
        echo "JSON Error: " . json_last_error_msg() . "\n\n";
        echo "First 500 chars of JSON:\n";
        echo substr($creators_json, 0, 500) . "\n";
    } else {
        echo "Total creators: " . count($creators) . "\n\n";

        echo "Creator list:\n";
        foreach ($creators as $idx => $creator) {
            $id = isset($creator['id']) ? $creator['id'] : 'NO_ID';
            $name = isset($creator['name']) ? $creator['name'] : 'NO_NAME';
            $has_avatar = isset($creator['avatarUrl']) && !empty($creator['avatarUrl']) ? 'YES' : 'NO';
            $has_accounts = isset($creator['accounts']) && is_array($creator['accounts']) && count($creator['accounts']) > 0 ? count($creator['accounts']) : 0;

            echo sprintf(
                "%2d. %-30s (id: %-30s) avatar: %3s, accounts: %d\n",
                $idx + 1,
                substr($name, 0, 30),
                substr($id, 0, 30),
                $has_avatar,
                $has_accounts
            );

            // Special check for brunitarte
            if (stripos($name, 'brunitarte') !== false || stripos($id, 'brunitarte') !== false) {
                echo "    >>> FOUND BRUNITARTE! <<<\n";
                echo "    Full data: " . json_encode($creator, JSON_PRETTY_PRINT) . "\n";
            }
        }

        echo "\n\n=== API Response Test ===\n";
        echo "This is what get_my_creators.php should return:\n\n";
        echo json_encode(array('creators' => $creators), JSON_PRETTY_PRINT);
    }
} else {
    echo "ERROR: No user_lists entry found for user_id 2!\n";
}

$conn->close();
?>