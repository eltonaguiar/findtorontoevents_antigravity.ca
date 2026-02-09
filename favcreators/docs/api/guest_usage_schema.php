<?php
/**
 * Schema for guest_usage table.
 * Tracks site visits (by distinct calendar days) and AI bot message usage
 * by IP address for guest (non-logged-in) users.
 *
 * - AI bot: guests get 1 free message, then must sign in.
 * - Events / FavCreators: guests can browse for 2 calendar days, then must sign in.
 *
 * Include this once after db_connect.php; tables auto-create via $conn->query().
 * PHP 5.2 compatible.
 */

if (!isset($conn) || !$conn) return;

$guest_usage_tables = array(
    'guest_usage' => "CREATE TABLE IF NOT EXISTS guest_usage (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ip_address VARCHAR(45) NOT NULL COMMENT 'IPv4 or IPv6',
        ai_message_count INT NOT NULL DEFAULT 0 COMMENT 'AI bot messages sent by this IP',
        first_seen_at DATETIME NOT NULL COMMENT 'First visit timestamp',
        last_seen_at DATETIME NOT NULL COMMENT 'Most recent visit timestamp',
        distinct_days INT NOT NULL DEFAULT 1 COMMENT 'Number of distinct calendar days visited',
        last_day_counted DATE NOT NULL COMMENT 'Last calendar day we incremented distinct_days',
        user_agent VARCHAR(512) DEFAULT '',
        UNIQUE KEY uq_ip (ip_address),
        INDEX idx_last_seen (last_seen_at),
        INDEX idx_distinct_days (distinct_days)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",

    'user_visit_days' => "CREATE TABLE IF NOT EXISTS user_visit_days (
        user_id INT NOT NULL PRIMARY KEY COMMENT 'FK to users.id',
        distinct_days INT NOT NULL DEFAULT 1 COMMENT 'Number of distinct calendar days this user visited',
        last_day_counted DATE NOT NULL COMMENT 'Last calendar day we incremented distinct_days',
        first_visit_at DATETIME NOT NULL COMMENT 'First visit as logged-in user',
        last_visit_at DATETIME NOT NULL COMMENT 'Most recent visit',
        INDEX idx_distinct_days (distinct_days),
        INDEX idx_last_visit (last_visit_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",

    'click_log' => "CREATE TABLE IF NOT EXISTS click_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ip_address VARCHAR(45) NOT NULL COMMENT 'IPv4 or IPv6',
        user_id INT DEFAULT NULL COMMENT 'FK to users.id if logged in, NULL for guests',
        click_type VARCHAR(32) NOT NULL COMMENT 'event_click, link_click, heart_click, nav_click',
        page VARCHAR(64) NOT NULL DEFAULT 'events' COMMENT 'events, fc, stocks, movies, etc.',
        target_url VARCHAR(1024) DEFAULT '' COMMENT 'URL or href clicked',
        target_title VARCHAR(512) DEFAULT '' COMMENT 'Event title, link text, etc.',
        target_id VARCHAR(255) DEFAULT '' COMMENT 'Event ID, creator ID, etc.',
        clicked_at DATETIME NOT NULL,
        INDEX idx_ip (ip_address),
        INDEX idx_user (user_id),
        INDEX idx_type (click_type),
        INDEX idx_clicked_at (clicked_at),
        INDEX idx_page (page)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",

    'page_view_log' => "CREATE TABLE IF NOT EXISTS page_view_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ip_address VARCHAR(45) NOT NULL COMMENT 'IPv4 or IPv6',
        user_id INT DEFAULT NULL COMMENT 'FK to users.id if logged in, NULL for guests',
        page VARCHAR(64) NOT NULL COMMENT 'events, fc, stocks, movies, movies_v2, movies_v3, wellness, windowsfixer, stats, vr, weather',
        page_url VARCHAR(1024) DEFAULT '' COMMENT 'Full path visited',
        visit_count INT NOT NULL DEFAULT 1 COMMENT 'Number of visits to this page by this IP/user',
        first_visit_at DATETIME NOT NULL,
        last_visit_at DATETIME NOT NULL,
        UNIQUE KEY uq_ip_page (ip_address, page),
        INDEX idx_user (user_id),
        INDEX idx_page (page),
        INDEX idx_last_visit (last_visit_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
);

foreach ($guest_usage_tables as $name => $sql) {
    $result = $conn->query($sql);
    if (!$result) {
        error_log("Failed to create table $name: " . $conn->error);
    }
}

// Migration: add registered_user_id and registered_at columns if missing
$col_check = $conn->query("SHOW COLUMNS FROM guest_usage LIKE 'registered_user_id'");
if ($col_check && $col_check->num_rows === 0) {
    $conn->query("ALTER TABLE guest_usage ADD COLUMN registered_user_id INT DEFAULT NULL COMMENT 'User ID if this IP registered an account'");
    $conn->query("ALTER TABLE guest_usage ADD COLUMN registered_at DATETIME DEFAULT NULL COMMENT 'When the account was registered/linked'");
    $conn->query("ALTER TABLE guest_usage ADD INDEX idx_registered (registered_user_id)");
}
?>
