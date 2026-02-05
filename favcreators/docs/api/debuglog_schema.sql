-- Debug log table for ejaguiar1_debuglog database
-- Run this in phpMyAdmin (or mysql client) if debug_log doesn't exist yet.
-- The API (debug_log.php) also creates it via debuglog_ensure_table.php on first use;
-- use this script when the DB user cannot CREATE TABLE or you want to align schema manually.

USE `ejaguiar1_debuglog`;

-- Table used by debug_log.php (event_type, payload, user_id, etc.)
CREATE TABLE IF NOT EXISTS `debug_log` (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Optional: drop legacy placeholder tables if you don't use them
-- DROP TABLE IF EXISTS `eventslogs`;
-- DROP TABLE IF EXISTS `favcreatorslogs`;
