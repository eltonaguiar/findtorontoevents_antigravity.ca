-- Migration: Create streaming_providers table
-- Purpose: Store streaming platform availability for movies/TV shows
-- Date: 2026-02-15

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
  CONSTRAINT `fk_provider_movie` FOREIGN KEY (`movie_id`) REFERENCES `movies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Index for efficient provider filtering
CREATE INDEX idx_provider_lookup ON streaming_providers(provider_id, is_active, movie_id);

-- Track provider changes history
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
