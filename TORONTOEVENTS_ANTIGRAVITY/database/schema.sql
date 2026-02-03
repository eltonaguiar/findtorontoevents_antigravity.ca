-- MovieShows Database Schema
-- Database: ejaguiar1_tvmoviestrailers

-- Movies/TV Series Table
CREATE TABLE IF NOT EXISTS movies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    type ENUM('movie', 'tv_series') DEFAULT 'movie',
    release_year INT,
    genre VARCHAR(255),
    description TEXT,
    tmdb_id INT,
    imdb_id VARCHAR(20),
    source VARCHAR(50) COMMENT 'cineplex, tmdb, manual, etc',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_title (title),
    INDEX idx_type (type),
    INDEX idx_source (source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Trailers Table (Multiple trailers per movie)
CREATE TABLE IF NOT EXISTS trailers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    movie_id INT NOT NULL,
    youtube_id VARCHAR(20) NOT NULL,
    title VARCHAR(255),
    priority INT DEFAULT 0 COMMENT 'Higher priority = preferred trailer',
    source VARCHAR(50) COMMENT 'youtube_api, manual, scraper',
    view_count BIGINT DEFAULT 0,
    duration INT COMMENT 'Duration in seconds',
    is_active BOOLEAN DEFAULT TRUE,
    last_checked TIMESTAMP NULL,
    error_count INT DEFAULT 0 COMMENT 'Track failed load attempts',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
    INDEX idx_movie_priority (movie_id, priority DESC),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Thumbnails Table (Multiple thumbnail sources per movie)
CREATE TABLE IF NOT EXISTS thumbnails (
    id INT AUTO_INCREMENT PRIMARY KEY,
    movie_id INT NOT NULL,
    url VARCHAR(512) NOT NULL,
    source VARCHAR(50) COMMENT 'tmdb, youtube, manual, imdb',
    priority INT DEFAULT 0 COMMENT 'Higher priority = preferred thumbnail',
    width INT,
    height INT,
    is_active BOOLEAN DEFAULT TRUE,
    last_checked TIMESTAMP NULL,
    error_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
    INDEX idx_movie_priority (movie_id, priority DESC),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Content Sources Tracking
CREATE TABLE IF NOT EXISTS content_sources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    type VARCHAR(50) COMMENT 'scraper, api, manual',
    last_sync TIMESTAMP NULL,
    sync_count INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    config JSON COMMENT 'Source-specific configuration',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sync Log
CREATE TABLE IF NOT EXISTS sync_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_id INT,
    action VARCHAR(50) COMMENT 'sync, scrape, update',
    movies_added INT DEFAULT 0,
    trailers_added INT DEFAULT 0,
    thumbnails_added INT DEFAULT 0,
    errors TEXT,
    duration_ms INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES content_sources(id) ON DELETE SET NULL,
    INDEX idx_created (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert initial content sources
INSERT INTO content_sources (name, type, base_url, is_active) VALUES
('cineplex', 'scraper', 'https://www.cineplex.com', TRUE),
('tmdb', 'api', 'https://www.themoviedb.org', TRUE),
('youtube', 'api', 'https://www.youtube.com', TRUE),
('manual', 'manual', NULL, TRUE)
ON DUPLICATE KEY UPDATE name=name;

-- ============================================================================
-- USER AUTHENTICATION & QUEUE MANAGEMENT TABLES
-- ============================================================================

-- User queues table
CREATE TABLE IF NOT EXISTS user_queues (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    movie_id INT NOT NULL,
    position INT NOT NULL,
    watched BOOLEAN DEFAULT FALSE,
    watch_count INT DEFAULT 0,
    last_watched_at TIMESTAMP NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
    INDEX idx_user_queue (user_id, position),
    INDEX idx_user_movie (user_id, movie_id),
    UNIQUE KEY unique_user_movie (user_id, movie_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INT PRIMARY KEY,
    rewatch_enabled BOOLEAN DEFAULT TRUE,
    auto_play BOOLEAN DEFAULT TRUE,
    sound_on_scroll BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Shared playlists table
CREATE TABLE IF NOT EXISTS shared_playlists (
    id INT AUTO_INCREMENT PRIMARY KEY,
    share_code VARCHAR(20) UNIQUE NOT NULL,
    user_id INT NOT NULL,
    title VARCHAR(255),
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    view_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    INDEX idx_share_code (share_code),
    INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Playlist items table
CREATE TABLE IF NOT EXISTS playlist_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    playlist_id INT NOT NULL,
    movie_id INT NOT NULL,
    position INT NOT NULL,
    FOREIGN KEY (playlist_id) REFERENCES shared_playlists(id) ON DELETE CASCADE,
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
    INDEX idx_playlist (playlist_id, position)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
