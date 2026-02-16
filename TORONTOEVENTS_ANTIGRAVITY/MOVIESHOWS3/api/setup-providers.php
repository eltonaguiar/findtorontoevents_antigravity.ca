<?php
/**
 * One-time setup script to create streaming_providers tables
 * Access via: https://findtorontoevents.ca/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/api/setup-providers.php
 */

header('Content-Type: text/plain');
require_once 'db-config.php';

$pdo = getDbConnection();
if (!$pdo) {
    die("ERROR: Database connection failed\n");
}

echo "Creating streaming_providers tables...\n\n";

$sql = "
CREATE TABLE IF NOT EXISTS `streaming_providers` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `movie_id` int(11) NOT NULL,
  `provider_id` varchar(10) NOT NULL COMMENT 'TMDB provider ID (e.g., 8=Netflix, 9=Prime)',
  `provider_name` varchar(100) NOT NULL,
  `provider_logo` varchar(500) DEFAULT NULL,
  `display_priority` int(11) DEFAULT 0 COMMENT 'Sort order for display',
  `first_seen` datetime DEFAULT CURRENT_TIMESTAMP,
  `last_checked` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_active` tinyint(1) DEFAULT 1 COMMENT 'FALSE when title leaves platform',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_movie_provider` (`movie_id`, `provider_id`),
  KEY `idx_movie_active` (`movie_id`, `is_active`),
  KEY `idx_provider_active` (`provider_id`, `is_active`),
  KEY `idx_provider_lookup` (`provider_id`, `is_active`, `movie_id`),
  CONSTRAINT `fk_provider_movie` FOREIGN KEY (`movie_id`) REFERENCES `movies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
";

try {
    $pdo->exec($sql);
    echo "✓ Created streaming_providers table\n";
} catch (Exception $e) {
    echo "✗ Error creating streaming_providers: " . $e->getMessage() . "\n";
}

$sql2 = "
CREATE TABLE IF NOT EXISTS `streaming_provider_history` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `movie_id` int(11) NOT NULL,
  `provider_id` varchar(10) NOT NULL,
  `provider_name` varchar(100) NOT NULL,
  `action` enum('added','removed') NOT NULL,
  `timestamp` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_movie_history` (`movie_id`, `timestamp`),
  KEY `idx_provider_history` (`provider_id`, `timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
";

try {
    $pdo->exec($sql2);
    echo "✓ Created streaming_provider_history table\n";
} catch (Exception $e) {
    echo "✗ Error creating streaming_provider_history: " . $e->getMessage() . "\n";
}

echo "\n✓ Setup complete!\n";
echo "\nNext steps:\n";
echo "1. Run initial provider load: https://findtorontoevents.ca/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/api/run-provider-update.php\n";
echo "2. Delete this file for security\n";
