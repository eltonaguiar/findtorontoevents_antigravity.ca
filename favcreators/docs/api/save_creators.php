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

// Get current DB state before overwriting
$check_query = $conn->query("SELECT creators FROM user_lists WHERE user_id = $user_id");
$current_count = 0;
$current_json = '';
if ($check_query && $check_query->num_rows > 0) {
    $current_row = $check_query->fetch_assoc();
    $current_json = $current_row['creators'];
    $current_creators = json_decode($current_json, true);
    $current_count = is_array($current_creators) ? count($current_creators) : 0;
    $log_entry .= "  DB before: $current_count creators\n";
}

$new_count = count($creators);
$log_entry .= "  New count: $new_count creators\n";

// Safety check: if the new list is drastically smaller (lost >40% of creators and dropped more than 5),
// save a backup of the current list before overwriting. This protects against stale localStorage overwrites.
if ($current_count > 10 && $new_count > 0 && ($current_count - $new_count) > 5 && $new_count < $current_count * 0.6) {
    $log_entry .= "  WARNING: Large drop detected ($current_count -> $new_count). Saving backup.\n";
    // Save backup to user_lists_backup table (create if not exists)
    $conn->query("CREATE TABLE IF NOT EXISTS user_lists_backup (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        creators LONGTEXT,
        backed_up_at DATETIME,
        reason VARCHAR(255)
    )");
    $backup_esc = $conn->real_escape_string($current_json);
    $reason = $conn->real_escape_string("Auto-backup: list shrank from $current_count to $new_count");
    $conn->query("INSERT INTO user_lists_backup (user_id, creators, backed_up_at, reason) VALUES ($user_id, '$backup_esc', NOW(), '$reason')");
    // Keep only last 5 backups per user (MySQL-safe: can't subquery same table in DELETE)
    $keep_q = $conn->query("SELECT id FROM user_lists_backup WHERE user_id = $user_id ORDER BY backed_up_at DESC LIMIT 5");
    $keep_ids = array();
    if ($keep_q) { while ($kr = $keep_q->fetch_assoc()) { $keep_ids[] = (int)$kr['id']; } }
    if (count($keep_ids) > 0) {
        $keep_str = implode(',', $keep_ids);
        $conn->query("DELETE FROM user_lists_backup WHERE user_id = $user_id AND id NOT IN ($keep_str)");
    }
    $log_entry .= "  Backup saved. Proceeding with save.\n";
}

// Block completely empty saves for users who had a real list (likely a bug)
if ($new_count === 0 && $current_count > 5) {
    $log_entry .= "  BLOCKED: Refusing to save empty list (DB has $current_count). Likely a frontend bug.\n";
    file_put_contents($log_file, $log_entry, FILE_APPEND);
    echo json_encode(array('error' => 'Refusing to save empty list', 'current_count' => $current_count));
    $conn->close();
    exit;
}

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
    // Ensure selected_avatar_source column exists (migration for existing tables)
    $col_check = $conn->query("SHOW COLUMNS FROM creators LIKE 'selected_avatar_source'");
    if ($col_check && $col_check->num_rows === 0) {
        $conn->query("ALTER TABLE creators ADD COLUMN selected_avatar_source VARCHAR(255) DEFAULT '' AFTER avatar_url");
    }
    $order = 0;
    foreach ($creators as $c) {
        $id = isset($c['id']) ? $c['id'] : '';
        if ($id === '')
            continue;
        $name = isset($c['name']) ? $conn->real_escape_string($c['name']) : '';
        $bio = isset($c['bio']) ? $conn->real_escape_string($c['bio']) : '';
        $avatar_url = isset($c['avatarUrl']) ? $conn->real_escape_string($c['avatarUrl']) : '';
        $sel_avatar_src = isset($c['selectedAvatarSource']) ? $conn->real_escape_string($c['selectedAvatarSource']) : '';
        $category = isset($c['category']) ? $conn->real_escape_string($c['category']) : '';
        $reason = isset($c['reason']) ? $conn->real_escape_string($c['reason']) : '';
        $tags = isset($c['tags']) ? $conn->real_escape_string(is_string($c['tags']) ? $c['tags'] : json_encode($c['tags'])) : '[]';
        $accounts = isset($c['accounts']) ? $conn->real_escape_string(is_string($c['accounts']) ? $c['accounts'] : json_encode($c['accounts'])) : '[]';
        $is_fav = isset($c['isFavorite']) ? (int) (bool) $c['isFavorite'] : 0;
        $is_pinned = isset($c['isPinned']) ? (int) (bool) $c['isPinned'] : 0;
        $id_esc = $conn->real_escape_string($id);
        $sql = "INSERT INTO creators (id, name, bio, avatar_url, selected_avatar_source, category, reason, tags, accounts, is_favorite, is_pinned, in_guest_list, guest_sort_order) 
                VALUES ('$id_esc','$name','$bio','$avatar_url','$sel_avatar_src','$category','$reason','$tags','$accounts',$is_fav,$is_pinned,1,$order) 
                ON DUPLICATE KEY UPDATE name=VALUES(name), bio=VALUES(bio), avatar_url=VALUES(avatar_url), selected_avatar_source=VALUES(selected_avatar_source), category=VALUES(category), reason=VALUES(reason), tags=VALUES(tags), accounts=VALUES(accounts), is_favorite=VALUES(is_favorite), is_pinned=VALUES(is_pinned), in_guest_list=1, guest_sort_order=VALUES(guest_sort_order)";
        $conn->query($sql);
        $order++;
    }
}

echo json_encode(array('status' => 'success'));
$conn->close();
?>