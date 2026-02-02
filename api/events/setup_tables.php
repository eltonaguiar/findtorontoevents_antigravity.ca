<?php
/**
 * Create events_log and event_pulls tables on the server.
 * Run once via: https://findtorontoevents.ca/api/events/setup_tables.php
 * 
 * Tables:
 * - event_pulls: logs each time events are pulled/synced (timestamp, count, source)
 * - events_log: individual events with all details
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

$out = array(
    'ok' => false, 
    'messages' => array(), 
    'event_pulls_exists' => false, 
    'events_log_exists' => false
);

require_once dirname(__FILE__) . '/db_config.php';
$conn = @new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    $out['error'] = 'Database connection failed: ' . $conn->connect_error;
    echo json_encode($out);
    exit;
}

// Table 1: event_pulls - tracks each pull/sync operation
$sql_event_pulls = "CREATE TABLE IF NOT EXISTS `event_pulls` (
  `id` int NOT NULL AUTO_INCREMENT,
  `pull_timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `events_count` int NOT NULL DEFAULT 0,
  `source` varchar(255) DEFAULT 'manual',
  `status` varchar(50) DEFAULT 'success',
  `notes` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_pull_timestamp` (`pull_timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";

// Table 2: events_log - individual events with all details
$sql_events_log = "CREATE TABLE IF NOT EXISTS `events_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `event_id` varchar(64) NOT NULL,
  `pull_id` int DEFAULT NULL,
  `title` varchar(500) NOT NULL,
  `event_date` datetime DEFAULT NULL,
  `location` varchar(500) DEFAULT NULL,
  `source` varchar(255) DEFAULT NULL,
  `host` varchar(255) DEFAULT NULL,
  `url` varchar(1024) DEFAULT NULL,
  `price` varchar(100) DEFAULT NULL,
  `price_amount` decimal(10,2) DEFAULT NULL,
  `is_free` tinyint(1) DEFAULT 0,
  `description` text,
  `categories` text,
  `status` varchar(50) DEFAULT 'UPCOMING',
  `tags` text,
  `last_updated` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_event_id` (`event_id`),
  INDEX `idx_event_date` (`event_date`),
  INDEX `idx_source` (`source`),
  INDEX `idx_status` (`status`),
  INDEX `idx_pull_id` (`pull_id`),
  FOREIGN KEY (`pull_id`) REFERENCES `event_pulls`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";

// Table 3: stats_summary - pre-computed stats for fast retrieval
$sql_stats_summary = "CREATE TABLE IF NOT EXISTS `stats_summary` (
  `id` int NOT NULL AUTO_INCREMENT,
  `stat_name` varchar(100) NOT NULL,
  `stat_value` int DEFAULT 0,
  `stat_text` varchar(500) DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_stat_name` (`stat_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";

// Create event_pulls table
if (!$conn->query($sql_event_pulls)) {
    $out['messages'][] = 'event_pulls create failed: ' . $conn->error;
    echo json_encode($out);
    $conn->close();
    exit;
}
$out['messages'][] = 'event_pulls table created or already exists';
$out['event_pulls_exists'] = true;

// Create events_log table
if (!$conn->query($sql_events_log)) {
    $out['messages'][] = 'events_log create failed: ' . $conn->error;
    echo json_encode($out);
    $conn->close();
    exit;
}
$out['messages'][] = 'events_log table created or already exists';
$out['events_log_exists'] = true;

// Create stats_summary table
if (!$conn->query($sql_stats_summary)) {
    $out['messages'][] = 'stats_summary create failed: ' . $conn->error;
    echo json_encode($out);
    $conn->close();
    exit;
}
$out['messages'][] = 'stats_summary table created or already exists';
$out['stats_summary_exists'] = true;

// Initialize default stats if empty
$init_stats = array(
    array('total_events', 0, 'Total events in database'),
    array('total_pulls', 0, 'Total sync operations'),
    array('last_pull_count', 0, 'Events from last pull'),
    array('upcoming_events', 0, 'Upcoming events'),
    array('free_events', 0, 'Free events')
);

foreach ($init_stats as $stat) {
    $name = $conn->real_escape_string($stat[0]);
    $val = (int)$stat[1];
    $text = $conn->real_escape_string($stat[2]);
    $conn->query("INSERT IGNORE INTO stats_summary (stat_name, stat_value, stat_text) VALUES ('$name', $val, '$text')");
}
$out['messages'][] = 'Default stats initialized';

$out['ok'] = true;
echo json_encode($out, JSON_PRETTY_PRINT);
$conn->close();
?>
