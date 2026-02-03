<?php
// Create tables directly with inline SQL
$host = 'localhost';
$dbname = 'ejaguiar1_tvmoviestrailers';
$username = 'ejaguiar1_tvmoviestrailers';
$password = 'virus2016';

header('Content-Type: text/plain; charset=utf-8');

echo "MovieShows Database Initialization\n";
echo "===================================\n\n";

try {
    echo "Connecting...\n";
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    echo "Connected!\n\n";

    echo "Creating tables...\n";

    // Create movies table
    $pdo->exec("CREATE TABLE IF NOT EXISTS movies (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        type ENUM('movie', 'tv') DEFAULT 'movie',
        genre VARCHAR(255),
        description TEXT,
        release_year INT,
        imdb_rating DECIMAL(3,1),
        imdb_id VARCHAR(20),
        tmdb_id INT,
        runtime INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_type (type),
        INDEX idx_release_year (release_year),
        INDEX idx_imdb_id (imdb_id),
        INDEX idx_tmdb_id (tmdb_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
    echo "  movies\n";

    // Create trailers table
    $pdo->exec("CREATE TABLE IF NOT EXISTS trailers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        movie_id INT NOT NULL,
        youtube_id VARCHAR(20) NOT NULL,
        title VARCHAR(255),
        priority INT DEFAULT 0,
        source VARCHAR(50),
        view_count BIGINT DEFAULT 0,
        duration INT,
        is_active BOOLEAN DEFAULT TRUE,
        last_checked TIMESTAMP NULL,
        error_count INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
        INDEX idx_movie_priority (movie_id, priority DESC),
        INDEX idx_active (is_active)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
    echo "  trailers\n";

    // Create thumbnails table
    $pdo->exec("CREATE TABLE IF NOT EXISTS thumbnails (
        id INT AUTO_INCREMENT PRIMARY KEY,
        movie_id INT NOT NULL,
        url VARCHAR(500) NOT NULL,
        is_primary BOOLEAN DEFAULT FALSE,
        width INT,
        height INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
        INDEX idx_movie_primary (movie_id, is_primary DESC)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
    echo "  thumbnails\n";

    // Create content_sources table
    $pdo->exec("CREATE TABLE IF NOT EXISTS content_sources (
        id INT AUTO_INCREMENT PRIMARY KEY,
        movie_id INT NOT NULL,
        source VARCHAR(50) NOT NULL,
        source_data JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
        INDEX idx_movie_source (movie_id, source)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
    echo "  content_sources\n";

    // Create sync_log table
    $pdo->exec("CREATE TABLE IF NOT EXISTS sync_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        sync_type VARCHAR(50) NOT NULL,
        status ENUM('success', 'failed', 'partial') DEFAULT 'success',
        items_processed INT DEFAULT 0,
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_sync_type (sync_type),
        INDEX idx_created_at (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
    echo "  sync_log\n";

    // Create user_queues table
    $pdo->exec("CREATE TABLE IF NOT EXISTS user_queues (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        movie_id INT NOT NULL,
        position INT NOT NULL,
        watched BOOLEAN DEFAULT FALSE,
        watch_count INT DEFAULT 0,
        last_watched_at TIMESTAMP NULL,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
        UNIQUE KEY unique_user_movie (user_id, movie_id),
        INDEX idx_user_position (user_id, position)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
    echo "  user_queues\n";

    // Create user_preferences table
    $pdo->exec("CREATE TABLE IF NOT EXISTS user_preferences (
        user_id INT PRIMARY KEY,
        rewatch_enabled BOOLEAN DEFAULT FALSE,
        autoplay BOOLEAN DEFAULT TRUE,
        sound_on_scroll BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
    echo "  user_preferences\n";

    // Create shared_playlists table
    $pdo->exec("CREATE TABLE IF NOT EXISTS shared_playlists (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        share_code VARCHAR(20) UNIQUE NOT NULL,
        title VARCHAR(255),
        view_count INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_share_code (share_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
    echo "  shared_playlists\n";

    // Create playlist_items table
    $pdo->exec("CREATE TABLE IF NOT EXISTS playlist_items (
        id INT AUTO_INCREMENT PRIMARY KEY,
        playlist_id INT NOT NULL,
        movie_id INT NOT NULL,
        position INT NOT NULL,
        FOREIGN KEY (playlist_id) REFERENCES shared_playlists(id) ON DELETE CASCADE,
        FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
        INDEX idx_playlist_position (playlist_id, position)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");
    echo "  playlist_items\n";

    echo "\nVerifying...\n";
    $stmt = $pdo->query("SHOW TABLES");
    $tables = $stmt->fetchAll(PDO::FETCH_COLUMN);

    echo "SUCCESS! Created " . count($tables) . " tables:\n";
    foreach ($tables as $table) {
        $countStmt = $pdo->query("SELECT COUNT(*) FROM `" . $table . "`");
        $count = $countStmt->fetchColumn();
        echo "  " . $table . ": " . $count . " rows\n";
    }

    echo "\nDatabase ready!\n";

} catch (PDOException $e) {
    echo "Error: " . $e->getMessage() . "\n";
}
?>