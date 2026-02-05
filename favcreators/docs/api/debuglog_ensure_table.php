<?php
/**
 * Ensure debug_log table exists in ejaguiar1_debuglog.
 * No output - just runs when included. Expects $debuglog_conn from caller.
 */
if (!isset($debuglog_conn) || !$debuglog_conn) return;

$sql = "CREATE TABLE IF NOT EXISTS `debug_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `event_type` varchar(64) NOT NULL,
  `user_id` int DEFAULT NULL,
  `session_id` varchar(255) DEFAULT NULL,
  `payload` text,
  `ip` varchar(64) DEFAULT NULL,
  `user_agent` varchar(512) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `event_type` (`event_type`),
  KEY `created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";
$debuglog_conn->query($sql);
