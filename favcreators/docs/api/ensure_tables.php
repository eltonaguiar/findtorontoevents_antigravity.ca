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

// FriendTracker tables
$sql_friendt_friends = "CREATE TABLE IF NOT EXISTS `friendt_friends` (
  `id` varchar(32) NOT NULL,
  `user_id` int NOT NULL,
  `name` varchar(255) NOT NULL,
  `nickname` varchar(255) DEFAULT NULL,
  `birthday` date DEFAULT NULL,
  `how_met` varchar(255) DEFAULT NULL,
  `notes` text,
  `phone` varchar(50) DEFAULT NULL,
  `email` varchar(255) DEFAULT NULL,
  `instagram` varchar(100) DEFAULT NULL,
  `tiktok` varchar(100) DEFAULT NULL,
  `twitter` varchar(100) DEFAULT NULL,
  `snapchat` varchar(100) DEFAULT NULL,
  `linkedin` varchar(255) DEFAULT NULL,
  `other_social` varchar(255) DEFAULT NULL,
  `tags` text,
  `cadence_days` int DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci";
$conn->query($sql_friendt_friends);

$sql_friendt_hangouts = "CREATE TABLE IF NOT EXISTS `friendt_hangouts` (
  `id` varchar(32) NOT NULL,
  `friend_id` varchar(32) NOT NULL,
  `user_id` int NOT NULL,
  `date` date NOT NULL,
  `activity` varchar(255) DEFAULT NULL,
  `notes` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `friend_id` (`friend_id`),
  KEY `user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci";
$conn->query($sql_friendt_hangouts);

$sql_friendt_events = "CREATE TABLE IF NOT EXISTS `friendt_events` (
  `id` varchar(32) NOT NULL,
  `user_id` int NOT NULL,
  `name` varchar(255) NOT NULL,
  `type` varchar(50) DEFAULT 'hangout',
  `date` date NOT NULL,
  `time` time DEFAULT NULL,
  `location` varchar(255) DEFAULT NULL,
  `description` text,
  `invite_by_tags` text,
  `invited_friends` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci";
$conn->query($sql_friendt_events);

// Test user for Playwright: username bob, password bob
$bob_check = $conn->query("SELECT id FROM users WHERE email = 'bob'");
if (!$bob_check || $bob_check->num_rows === 0) {
    $conn->query("INSERT INTO users (email, password, role, display_name) VALUES ('bob', 'bob', 'user', 'Bob')");
}

// Test user for FriendTracker: John Doe, password password123
$john_check = $conn->query("SELECT id FROM users WHERE email = 'johndoe'");
if (!$john_check || $john_check->num_rows === 0) {
    $conn->query("INSERT INTO users (email, password, role, display_name) VALUES ('johndoe', 'password123', 'user', 'John Doe')");
    $john_id = $conn->insert_id;
} else {
    $john_row = $john_check->fetch_assoc();
    $john_id = $john_row['id'];
}

// If John Doe user exists, create test friend Jane Doe
if (isset($john_id) && $john_id) {
    // Check if Jane Doe friend already exists
    $jane_check = $conn->query("SELECT id FROM friendt_friends WHERE id = 'jd_20260302' AND user_id = $john_id");
    if (!$jane_check || $jane_check->num_rows === 0) {
        $tags_json = $conn->real_escape_string(json_encode(["best friend", "college", "coffee buddy"]));
        $sql_jane = "INSERT INTO friendt_friends (
            id, user_id, name, nickname, birthday, how_met, notes,
            phone, email, instagram, tags, cadence_days
        ) VALUES (
            'jd_20260302',
            $john_id,
            'Jane Doe',
            'Jane',
            '1990-05-15',
            'College friends',
            'Best friend from college. Loves coffee and hiking.',
            '+1 (555) 123-4567',
            'jane.doe@example.com',
            '@janedoe',
            '$tags_json',
            7
        )";
        $conn->query($sql_jane);
        
        // Add hangout from yesterday (coffee)
        $hangout_check = $conn->query("SELECT id FROM friendt_hangouts WHERE id = 'hangout_20260301' AND friend_id = 'jd_20260302'");
        if (!$hangout_check || $hangout_check->num_rows === 0) {
            $sql_hangout = "INSERT INTO friendt_hangouts (
                id, friend_id, user_id, date, activity, notes
            ) VALUES (
                'hangout_20260301',
                'jd_20260302',
                $john_id,
                '2026-03-01',
                'Coffee catch-up',
                'Met at local café. Discussed work and weekend plans.'
            )";
            $conn->query($sql_hangout);
        }
    }
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
