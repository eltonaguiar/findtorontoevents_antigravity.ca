<?php
/**
 * Schema for creator_status_updates feature.
 * Tracks the last content updates (posts, stories, streams, tweets, etc.)
 * for creators across multiple platforms (Twitch, Kick, TikTok, Instagram,
 * Twitter/X, Reddit, YouTube).
 *
 * Include this once; tables are created via $conn->query().
 */

if (!isset($conn) || !$conn) return;

$status_tables = array(
    'creator_status_updates' => "CREATE TABLE IF NOT EXISTS creator_status_updates (
        id INT AUTO_INCREMENT PRIMARY KEY,
        creator_id VARCHAR(64) NOT NULL,
        creator_name VARCHAR(255) NOT NULL,
        platform VARCHAR(32) NOT NULL COMMENT 'twitch, kick, tiktok, instagram, twitter, reddit, youtube',
        username VARCHAR(255) NOT NULL,
        account_url VARCHAR(1024) DEFAULT '',

        update_type VARCHAR(32) NOT NULL DEFAULT 'post' COMMENT 'post, story, stream, vod, tweet, comment, video, short, reel',
        content_title VARCHAR(512) DEFAULT '',
        content_url VARCHAR(1024) DEFAULT '',
        content_preview VARCHAR(2048) DEFAULT '' COMMENT 'text preview or description snippet',
        content_thumbnail VARCHAR(1024) DEFAULT '',
        content_id VARCHAR(255) DEFAULT '' COMMENT 'platform-specific content ID',

        is_live TINYINT(1) DEFAULT 0,
        viewer_count INT DEFAULT 0,
        like_count INT DEFAULT 0,
        comment_count INT DEFAULT 0,

        content_published_at DATETIME DEFAULT NULL COMMENT 'when the content was published on the platform',
        last_checked DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,

        check_count INT DEFAULT 1,
        checked_by VARCHAR(255) DEFAULT 'system',
        error_message VARCHAR(512) DEFAULT '',

        UNIQUE KEY uq_creator_platform_type (creator_id, platform, update_type),
        INDEX idx_platform (platform),
        INDEX idx_update_type (update_type),
        INDEX idx_last_checked (last_checked),
        INDEX idx_content_published (content_published_at),
        INDEX idx_creator_id (creator_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",

    'creator_status_check_log' => "CREATE TABLE IF NOT EXISTS creator_status_check_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        creator_id VARCHAR(64) NOT NULL,
        creator_name VARCHAR(255) NOT NULL,
        platform VARCHAR(32) NOT NULL,
        update_type VARCHAR(32) NOT NULL DEFAULT 'post',
        found_update TINYINT(1) DEFAULT 0,
        checked_by VARCHAR(255) DEFAULT 'system',
        checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        response_time_ms INT DEFAULT 0,
        error_message VARCHAR(512) DEFAULT '',
        INDEX idx_creator_id (creator_id),
        INDEX idx_checked_at (checked_at),
        INDEX idx_platform (platform)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
);

foreach ($status_tables as $name => $sql) {
    $result = $conn->query($sql);
    if (!$result) {
        error_log("Failed to create table $name: " . $conn->error);
    }
}
?>
