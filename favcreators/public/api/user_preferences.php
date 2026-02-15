<?php
/**
 * user_preferences.php
 * GET  — returns user preferences (requires session)
 * POST — saves user preferences (requires session)
 *
 * Preferences stored as JSON in user_preferences table: (user_id PK, preferences TEXT, updated_at)
 *
 * PHP 5.2 compatible — no ?:, ??, [], closures, __DIR__, http_response_code()
 */
error_reporting(0);
ob_start();
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: https://findtorontoevents.ca');
header('Access-Control-Allow-Credentials: true');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    ob_end_clean();
    header('HTTP/1.1 204 No Content');
    exit;
}

require_once dirname(__FILE__) . '/session_auth.php';
$session_id = get_session_user_id();
if ($session_id === null) {
    header('HTTP/1.1 401 Unauthorized');
    ob_end_clean();
    echo json_encode(array('error' => 'Unauthorized'));
    exit;
}

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    ob_end_clean();
    echo json_encode(array('error' => 'Database not available'));
    exit;
}

// Ensure table exists
_up_ensure_table($conn);

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    // Fetch preferences
    $stmt = $conn->prepare('SELECT preferences FROM user_preferences WHERE user_id = ?');
    if (!$stmt) {
        ob_end_clean();
        echo json_encode(array('error' => 'Prepare failed'));
        exit;
    }
    $stmt->bind_param('i', $session_id);
    $stmt->execute();
    $stmt->bind_result($prefJson);
    $found = $stmt->fetch();
    $stmt->close();

    if ($found && $prefJson) {
        $prefs = json_decode($prefJson, true);
        if (!is_array($prefs)) {
            $prefs = array();
        }
    } else {
        $prefs = array();
    }
    ob_end_clean();
    echo json_encode(array('ok' => true, 'preferences' => $prefs));
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);
    if (!$data || !isset($data['preferences'])) {
        ob_end_clean();
        echo json_encode(array('error' => 'Missing preferences field'));
        exit;
    }

    $prefs = $data['preferences'];
    if (!is_array($prefs)) {
        ob_end_clean();
        echo json_encode(array('error' => 'preferences must be an object'));
        exit;
    }

    // Merge with existing preferences (so partial updates work)
    $existing = array();
    $stmt = $conn->prepare('SELECT preferences FROM user_preferences WHERE user_id = ?');
    if ($stmt) {
        $stmt->bind_param('i', $session_id);
        $stmt->execute();
        $stmt->bind_result($existingJson);
        if ($stmt->fetch() && $existingJson) {
            $decoded = json_decode($existingJson, true);
            if (is_array($decoded)) {
                $existing = $decoded;
            }
        }
        $stmt->close();
    }

    // Merge: new values overwrite existing
    foreach ($prefs as $k => $v) {
        $existing[$k] = $v;
    }

    $merged = json_encode($existing);

    // Upsert
    $stmt = $conn->prepare('INSERT INTO user_preferences (user_id, preferences, updated_at) VALUES (?, ?, NOW()) ON DUPLICATE KEY UPDATE preferences = VALUES(preferences), updated_at = NOW()');
    if (!$stmt) {
        ob_end_clean();
        echo json_encode(array('error' => 'Prepare failed: ' . $conn->error));
        exit;
    }
    $stmt->bind_param('is', $session_id, $merged);
    $ok = $stmt->execute();
    $stmt->close();

    if (!$ok) {
        ob_end_clean();
        echo json_encode(array('error' => 'Save failed'));
        exit;
    }

    ob_end_clean();
    echo json_encode(array('ok' => true, 'preferences' => $existing));
    exit;
}

ob_end_clean();
echo json_encode(array('error' => 'Method not allowed'));
exit;

/**
 * Ensure the user_preferences table exists.
 */
function _up_ensure_table($conn) {
    $sql = "CREATE TABLE IF NOT EXISTS user_preferences (
        user_id INT NOT NULL PRIMARY KEY,
        preferences TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8";
    $conn->query($sql);
}
?>
