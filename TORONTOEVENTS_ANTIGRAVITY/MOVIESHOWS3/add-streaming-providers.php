<?php
/**
 * Migration: Add streaming_providers table
 * Tracks which streaming platforms each movie/show is available on
 */

$host = 'localhost';
$dbname = 'ejaguiar1_tvmoviestrailers';
$username = 'ejaguiar1_tvmoviestrailers';
$password = 'D41$4Jci6T9W2PsJdagLEr*KMo96nrCD';

header('Content-Type: text/plain; charset=utf-8');

echo "Adding Streaming Providers Table\n";
echo "================================\n\n";

try {
    echo "Connecting...\n";
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    echo "Connected!\n\n";

    echo "Creating streaming_providers table...\n";

    // Create streaming_providers table
    $pdo->exec("CREATE TABLE IF NOT EXISTS streaming_providers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        movie_id INT NOT NULL,
        provider_id INT NOT NULL COMMENT 'TMDB provider ID (8=Netflix, 9=Prime, etc)',
        provider_name VARCHAR(100) NOT NULL,
        provider_logo_url VARCHAR(500),
        region VARCHAR(5) DEFAULT 'US' COMMENT 'Country code',
        monetization_type VARCHAR(20) COMMENT 'flatrate, free, ads, rent, buy',
        link VARCHAR(500) COMMENT 'Direct link to content on platform',
        first_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When we first saw it on this platform',
        last_verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last time we confirmed it',
        removed_at TIMESTAMP NULL COMMENT 'When it left this platform',
        is_active BOOLEAN DEFAULT TRUE COMMENT 'Currently available on this platform',
        FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
        UNIQUE KEY unique_movie_provider (movie_id, provider_id, region),
        INDEX idx_provider (provider_id),
        INDEX idx_active (is_active),
        INDEX idx_movie_active (movie_id, is_active)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");

    echo "✓ streaming_providers table created\n\n";

    echo "Creating provider_update_log table...\n";

    // Track provider update jobs
    $pdo->exec("CREATE TABLE IF NOT EXISTS provider_update_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP NULL,
        movies_checked INT DEFAULT 0,
        providers_added INT DEFAULT 0,
        providers_removed INT DEFAULT 0,
        errors INT DEFAULT 0,
        status ENUM('running', 'completed', 'failed') DEFAULT 'running',
        error_message TEXT,
        INDEX idx_started_at (started_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci");

    echo "✓ provider_update_log table created\n\n";

    // Verify tables
    echo "Verifying tables...\n";
    $stmt = $pdo->query("SHOW TABLES LIKE '%provider%'");
    $tables = $stmt->fetchAll(PDO::FETCH_COLUMN);

    foreach ($tables as $table) {
        $countStmt = $pdo->query("SELECT COUNT(*) FROM `$table`");
        $count = $countStmt->fetchColumn();
        echo "  ✓ $table: $count rows\n";
    }

    echo "\n✅ SUCCESS! Streaming providers tables are ready.\n";
    echo "\nNext steps:\n";
    echo "1. Run update-providers.php to fetch provider data from TMDB\n";
    echo "2. Set up a cron job to run it daily\n";

} catch (PDOException $e) {
    echo "❌ Error: " . $e->getMessage() . "\n";
    echo "\nStack trace:\n" . $e->getTraceAsString() . "\n";
}
?>
