<?php
/**
 * Validate that creators and user_lists tables exist and have expected structure.
 * Run via: https://yoursite.com/fc/api/validate_tables.php
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');
header('Access-Control-Allow-Methods: GET, OPTIONS');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

require_once dirname(__FILE__) . '/session_auth.php';
require_session_admin();

$out = array(
    'ok' => false,
    'db_connected' => false,
    'creators' => array('exists' => false, 'columns' => array(), 'row_count' => 0, 'valid' => false),
    'user_lists' => array('exists' => false, 'columns' => array(), 'row_count' => 0, 'valid' => false),
);

require_once dirname(__FILE__) . '/db_config.php';
$conn = @new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    $out['error'] = 'Database connection failed: ' . $conn->connect_error;
    echo json_encode($out);
    exit;
}
$out['db_connected'] = true;

$required_creators_columns = array('id', 'name', 'bio', 'avatar_url', 'category', 'reason', 'tags', 'accounts', 'is_favorite', 'is_pinned', 'in_guest_list', 'guest_sort_order', 'created_at', 'updated_at');
$required_user_lists_columns = array('user_id', 'creators', 'updated_at');

function describe_table($conn, $table) {
    $cols = array();
    $r = $conn->query("DESCRIBE `" . $conn->real_escape_string($table) . "`");
    if ($r) {
        while ($row = $r->fetch_assoc()) $cols[] = $row['Field'];
    }
    return $cols;
}

function table_exists($conn, $table) {
    $t = $conn->real_escape_string($table);
    $r = $conn->query("SHOW TABLES LIKE '$t'");
    return $r && $r->num_rows > 0;
}

function row_count($conn, $table) {
    $t = $conn->real_escape_string($table);
    $r = $conn->query("SELECT COUNT(*) AS c FROM `$t`");
    if ($r && $row = $r->fetch_assoc()) return (int)$row['c'];
    return 0;
}

// creators
if (table_exists($conn, 'creators')) {
    $out['creators']['exists'] = true;
    $out['creators']['columns'] = describe_table($conn, 'creators');
    $out['creators']['row_count'] = row_count($conn, 'creators');
    $missing_c = array_diff($required_creators_columns, $out['creators']['columns']);
    $out['creators']['valid'] = (count($missing_c) === 0);
    if (count($missing_c) > 0) $out['creators']['missing_columns'] = array_values($missing_c);
} else {
    $out['creators']['error'] = 'Table creators does not exist';
}

// user_lists
if (table_exists($conn, 'user_lists')) {
    $out['user_lists']['exists'] = true;
    $out['user_lists']['columns'] = describe_table($conn, 'user_lists');
    $out['user_lists']['row_count'] = row_count($conn, 'user_lists');
    $missing_u = array_diff($required_user_lists_columns, $out['user_lists']['columns']);
    $out['user_lists']['valid'] = (count($missing_u) === 0);
    if (count($missing_u) > 0) $out['user_lists']['missing_columns'] = array_values($missing_u);
    // Check guest list row
    $r = $conn->query("SELECT creators FROM user_lists WHERE user_id = 0");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $data = json_decode($row['creators'], true);
        $out['user_lists']['guest_list_count'] = is_array($data) ? count($data) : 0;
    } else {
        $out['user_lists']['guest_list_count'] = 0;
    }
} else {
    $out['user_lists']['error'] = 'Table user_lists does not exist';
}

$out['ok'] = $out['creators']['valid'] && $out['user_lists']['valid'];
echo json_encode($out);
$conn->close();
