<?php
/**
 * Create event_sources table for tracking multiple sources per event.
 * Run once via: https://findtorontoevents.ca/fc/api/events_sources_setup.php
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

$out = array('ok' => false, 'messages' => array());

require_once dirname(__FILE__) . '/events_db_config.php';
$conn = @new mysqli($events_servername, $events_username, $events_password, $events_dbname);
if ($conn->connect_error) {
    $out['error'] = 'Database connection failed: ' . $conn->connect_error;
    echo json_encode($out);
    exit;
}

// Table: event_sources - stores alternate source URLs for events
// Events are grouped by canonical_event_id which is the "primary" event
$sql_event_sources = "CREATE TABLE IF NOT EXISTS `event_sources` (
  `id` int NOT NULL AUTO_INCREMENT,
  `canonical_event_id` varchar(64) NOT NULL COMMENT 'The primary event ID this source belongs to',
  `source_event_id` varchar(64) NOT NULL COMMENT 'The event_id from events_log that is an alternate source',
  `source_name` varchar(255) NOT NULL COMMENT 'Source name (e.g., AllEvents.in, Eventbrite)',
  `source_url` varchar(1024) NOT NULL COMMENT 'Direct URL to the event on this source',
  `price` varchar(100) DEFAULT NULL,
  `match_confidence` decimal(5,2) DEFAULT 100.00 COMMENT 'How confident we are this is the same event (0-100)',
  `is_primary` tinyint(1) DEFAULT 0 COMMENT 'Is this the primary/canonical source',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_canonical_event_id` (`canonical_event_id`),
  INDEX `idx_source_event_id` (`source_event_id`),
  UNIQUE KEY `uk_canonical_source` (`canonical_event_id`, `source_event_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";

// Table: event_title_index - normalized titles for matching
$sql_title_index = "CREATE TABLE IF NOT EXISTS `event_title_index` (
  `id` int NOT NULL AUTO_INCREMENT,
  `event_id` varchar(64) NOT NULL,
  `normalized_title` varchar(500) NOT NULL COMMENT 'Lowercase, stripped of punctuation',
  `event_date` date DEFAULT NULL,
  `source` varchar(255) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_normalized_title` (`normalized_title`(255)),
  INDEX `idx_event_date` (`event_date`),
  UNIQUE KEY `uk_event_id` (`event_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";

// Create tables
if (!$conn->query($sql_event_sources)) {
    $out['messages'][] = 'event_sources create failed: ' . $conn->error;
    echo json_encode($out);
    $conn->close();
    exit;
}
$out['messages'][] = 'event_sources table created or already exists';

if (!$conn->query($sql_title_index)) {
    $out['messages'][] = 'event_title_index create failed: ' . $conn->error;
    echo json_encode($out);
    $conn->close();
    exit;
}
$out['messages'][] = 'event_title_index table created or already exists';

$out['ok'] = true;
echo json_encode($out);
$conn->close();
?>
