<?php
/**
 * One-time setup: create debug_log table in ejaguiar1_debuglog.
 * Safe to call repeatedly (CREATE TABLE IF NOT EXISTS).
 * GET or POST; returns JSON. Call after deploy to apply schema remotely.
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/debuglog_db_config.php';
$conn = new mysqli($debuglog_host, $debuglog_user, $debuglog_password, $debuglog_database);
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'DB connection failed: ' . $conn->connect_error));
    exit;
}

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci";
if ($conn->query($sql)) {
    echo json_encode(array('ok' => true, 'message' => 'debug_log table ready'));
} else {
    echo json_encode(array('ok' => false, 'error' => $conn->error));
}
$conn->close();
