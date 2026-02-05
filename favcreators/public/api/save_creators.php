<?php
/**
 * Save a user's creator list. Session-protected: only own list (or guest list if admin).
 */
header('Content-Type: application/json; charset=utf-8');
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Credentials: true");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

require_once dirname(__FILE__) . '/session_auth.php';
$session_id = get_session_user_id();
if ($session_id === null) {
    header('HTTP/1.1 401 Unauthorized');
    echo json_encode(array('error' => 'Unauthorized'));
    exit;
}

require_once dirname(__FILE__) . '/db_connect.php';
if (!isset($conn) || !$conn) {
    echo json_encode(array('error' => 'Database not available'));
    exit;
}
require_once dirname(__FILE__) . '/ensure_tables.php';
require_once dirname(__FILE__) . '/db_schema.php';

$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!$data || !isset($data['creators'])) {
    echo json_encode(array('error' => 'Invalid input'));
    exit;
}

$requested_id = isset($data['user_id']) ? intval($data['user_id']) : $session_id;
if ($requested_id !== $session_id && ($requested_id !== 0 || !is_session_admin())) {
    header('HTTP/1.1 403 Forbidden');
    echo json_encode(array('error' => 'Access denied'));
    exit;
}
$user_id = (int) $requested_id;
$creators = $data['creators'];
if (!is_array($creators))
    $creators = array();

// Deduplicate by id (keep first occurrence) - PHP 5.x safe
$seen = array();
$deduped = array();
foreach ($creators as $c) {
    $id = isset($c['id']) ? $c['id'] : '';
    if ($id === '' || isset($seen[$id])) continue;
    $seen[$id] = true;
    $deduped[] = $c;
}
$creators = $deduped;

// LOG: What's being saved
$log_file = '/tmp/favcreators_save_log.txt';
$log_entry = date('Y-m-d H:i:s') . " | User $user_id | Saving " . count($creators) . " creators\n";

// Get current DB state before overwriting (for logging only)
$check_query = $conn->query("SELECT creators FROM user_lists WHERE user_id = $user_id");
if ($check_query && $check_query->num_rows > 0) {
    $current_row = $check_query->fetch_assoc();
    $current_creators = json_decode($current_row['creators'], true);
    $current_count = is_array($current_creators) ? count($current_creators) : 0;
    $log_entry .= "  DB before: $current_count creators\n";
}
// Users can remove any creator from their own list; changes only affect their view.

file_put_contents($log_file, $log_entry, FILE_APPEND);

$creators_json = json_encode($creators);
$creators_escaped = $conn->real_escape_string($creators_json);

$query = "INSERT INTO user_lists (user_id, creators) VALUES ($user_id, '$creators_escaped') ON DUPLICATE KEY UPDATE creators = '$creators_escaped'";
if (!$conn->query($query)) {
    $error_msg = $conn->error;
    echo json_encode(array('error' => $error_msg));
    $conn->close();
    exit;
}

// Only when saving the GUEST list (user_id=0) do we update the global creators table. Normal users (user_id > 0) only update their own user_lists.
if ($user_id === 0) {
    $order = 0;
    foreach ($creators as $c) {
        $id = isset($c['id']) ? $c['id'] : '';
        if ($id === '')
            continue;
        $name = isset($c['name']) ? $conn->real_escape_string($c['name']) : '';
        $bio = isset($c['bio']) ? $conn->real_escape_string($c['bio']) : '';
        $avatar_url = isset($c['avatarUrl']) ? $conn->real_escape_string($c['avatarUrl']) : '';
        $category = isset($c['category']) ? $conn->real_escape_string($c['category']) : '';
        $reason = isset($c['reason']) ? $conn->real_escape_string($c['reason']) : '';
        $tags = isset($c['tags']) ? $conn->real_escape_string(is_string($c['tags']) ? $c['tags'] : json_encode($c['tags'])) : '[]';
        $accounts = isset($c['accounts']) ? $conn->real_escape_string(is_string($c['accounts']) ? $c['accounts'] : json_encode($c['accounts'])) : '[]';
        $is_fav = isset($c['isFavorite']) ? (int) (bool) $c['isFavorite'] : 0;
        $is_pinned = isset($c['isPinned']) ? (int) (bool) $c['isPinned'] : 0;
        $id_esc = $conn->real_escape_string($id);
        $sql = "INSERT INTO creators (id, name, bio, avatar_url, category, reason, tags, accounts, is_favorite, is_pinned, in_guest_list, guest_sort_order) 
                VALUES ('$id_esc','$name','$bio','$avatar_url','$category','$reason','$tags','$accounts',$is_fav,$is_pinned,1,$order) 
                ON DUPLICATE KEY UPDATE name=VALUES(name), bio=VALUES(bio), avatar_url=VALUES(avatar_url), category=VALUES(category), reason=VALUES(reason), tags=VALUES(tags), accounts=VALUES(accounts), is_favorite=VALUES(is_favorite), is_pinned=VALUES(is_pinned), in_guest_list=1, guest_sort_order=VALUES(guest_sort_order)";
        $conn->query($sql);
        $order++;
    }
}

echo json_encode(array('status' => 'success'));
$conn->close();
?>