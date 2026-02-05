<?php
/**
 * Ensure creators and user_lists tables exist and guest list is seeded if empty.
 * Included by get_my_creators.php, save_creators.php, sync_creators_table.php.
 * No output — runs automatically so no user action is required.
 */
if (!isset($conn) || !$conn) return;

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
$conn->query($sql_creators);

$sql_user_lists = "CREATE TABLE IF NOT EXISTS `user_lists` (
  `user_id` int NOT NULL,
  `creators` longtext,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci";
$conn->query($sql_user_lists);

$sql_users = "CREATE TABLE IF NOT EXISTS `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `password` varchar(255) DEFAULT NULL,
  `role` varchar(64) DEFAULT 'user',
  `display_name` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci";
$conn->query($sql_users);

$sql_user_saved_events = "CREATE TABLE IF NOT EXISTS `user_saved_events` (
  `user_id` int NOT NULL,
  `event_id` varchar(255) NOT NULL,
  `event_data` longtext,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`,`event_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci";
$conn->query($sql_user_saved_events);

// Test user for Playwright: username bob, password bob
$bob_check = $conn->query("SELECT id FROM users WHERE email = 'bob'");
if (!$bob_check || $bob_check->num_rows === 0) {
    $conn->query("INSERT INTO users (email, password, role, display_name) VALUES ('bob', 'bob', 'user', 'Bob')");
}

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
    }
}
