<?php
/**
 * Create creators and user_lists tables on the server. Seeds default guest list if empty.
 * Run once via: https://yoursite.com/fc/api/setup_tables.php
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');
header('Access-Control-Allow-Methods: GET, OPTIONS');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

require_once dirname(__FILE__) . '/session_auth.php';
require_session_admin();

$out = array('ok' => false, 'messages' => array(), 'creators_exists' => false, 'user_lists_exists' => false, 'guest_list_seeded' => false);

require_once dirname(__FILE__) . '/db_config.php';
$conn = @new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    $out['error'] = 'Database connection failed: ' . $conn->connect_error;
    echo json_encode($out);
    exit;
}

// Exact CREATE TABLE statements (match migration SQL)
$sql_creators = "CREATE TABLE IF NOT EXISTS `creators` (
  `id` varchar(64) NOT NULL,
  `name` varchar(255) NOT NULL,
  `bio` text,
  `avatar_url` varchar(1024) DEFAULT '',
  `category` varchar(128) DEFAULT '',
  `reason` varchar(255) DEFAULT '',
  `tags` text,
  `accounts` text,
  `is_favorite` tinyint(1) DEFAULT 0,
  `is_pinned` tinyint(1) DEFAULT 0,
  `in_guest_list` tinyint(1) DEFAULT 0,
  `guest_sort_order` int DEFAULT 0,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci";

$sql_user_lists = "CREATE TABLE IF NOT EXISTS `user_lists` (
  `user_id` int NOT NULL,
  `creators` longtext,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci";

if (!$conn->query($sql_creators)) {
    $out['messages'][] = 'creators create failed: ' . $conn->error;
    echo json_encode($out);
    $conn->close();
    exit;
}
$out['messages'][] = 'creators table created or already exists';
$out['creators_exists'] = true;

if (!$conn->query($sql_user_lists)) {
    $out['messages'][] = 'user_lists create failed: ' . $conn->error;
    echo json_encode($out);
    $conn->close();
    exit;
}
$out['messages'][] = 'user_lists table created or already exists';
$out['user_lists_exists'] = true;

// Seed guest list (user_id 0) if empty
$need_seed = false;
$r = $conn->query("SELECT creators FROM user_lists WHERE user_id = 0");
if (!$r || $r->num_rows === 0) {
    $need_seed = true;
} else {
    $row = $r->fetch_assoc();
    $data = json_decode($row['creators'], true);
    if (!is_array($data) || count($data) === 0) $need_seed = true;
}

if ($need_seed) {
    $json_file = dirname(__FILE__) . '/initial_creators.json';
    $seed = array();
    if (file_exists($json_file)) {
        $raw = file_get_contents($json_file);
        $seed = json_decode($raw, true);
        if (!is_array($seed)) $seed = array();
    }
    if (count($seed) > 0) {
        $order = 0;
        foreach ($seed as $c) {
            $id = isset($c['id']) ? $conn->real_escape_string($c['id']) : '';
            if ($id === '') continue;
            $name = isset($c['name']) ? $conn->real_escape_string($c['name']) : '';
            $bio = isset($c['bio']) ? $conn->real_escape_string($c['bio']) : '';
            $avatar = isset($c['avatarUrl']) ? $conn->real_escape_string($c['avatarUrl']) : '';
            $cat = isset($c['category']) ? $conn->real_escape_string($c['category']) : '';
            $reason = isset($c['reason']) ? $conn->real_escape_string($c['reason']) : '';
            $tags = isset($c['tags']) ? $conn->real_escape_string(is_string($c['tags']) ? $c['tags'] : json_encode($c['tags'])) : '[]';
            $acc = isset($c['accounts']) ? $conn->real_escape_string(is_string($c['accounts']) ? $c['accounts'] : json_encode($c['accounts'])) : '[]';
            $fav = isset($c['isFavorite']) ? (int)(bool)$c['isFavorite'] : 0;
            $pin = isset($c['isPinned']) ? (int)(bool)$c['isPinned'] : 0;
            $sql = "INSERT INTO creators (id, name, bio, avatar_url, category, reason, tags, accounts, is_favorite, is_pinned, in_guest_list, guest_sort_order)
                VALUES ('$id','$name','$bio','$avatar','$cat','$reason','$tags','$acc',$fav,$pin,1,$order)
                ON DUPLICATE KEY UPDATE name=VALUES(name), bio=VALUES(bio), avatar_url=VALUES(avatar_url), category=VALUES(category), reason=VALUES(reason), tags=VALUES(tags), accounts=VALUES(accounts), is_favorite=VALUES(is_favorite), is_pinned=VALUES(is_pinned), in_guest_list=1, guest_sort_order=VALUES(guest_sort_order)";
            $conn->query($sql);
            $order++;
        }
        $list_json = $conn->real_escape_string(json_encode($seed));
        $conn->query("INSERT INTO user_lists (user_id, creators) VALUES (0, '$list_json') ON DUPLICATE KEY UPDATE creators = '$list_json'");
        $out['guest_list_seeded'] = true;
        $out['messages'][] = 'Guest list (user_id 0) seeded with ' . count($seed) . ' creators';
    } else {
        $out['messages'][] = 'initial_creators.json missing or empty; guest list not seeded';
    }
} else {
    $out['messages'][] = 'Guest list already has data; skip seed';
}

$out['ok'] = true;
echo json_encode($out);
$conn->close();
