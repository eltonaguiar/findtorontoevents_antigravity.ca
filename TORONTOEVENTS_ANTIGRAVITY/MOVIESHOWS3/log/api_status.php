<?php
/**
 * Movie/TV Series Sync Status API
 * Returns JSON with database stats and recent sync logs
 * Used by GitHub Actions to verify successful data pulls
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

$host = 'localhost';
$dbname = 'ejaguiar1_tvmoviestrailers';
$username = 'ejaguiar1_tvmoviestrailers';
$password = 'D41$4Jci6T9W2PsJdagLEr*KMo96nrCD';

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);

    // Overall counts
    $stmt = $pdo->query("SELECT
        COUNT(*) as total,
        SUM(CASE WHEN type = 'movie' THEN 1 ELSE 0 END) as movies,
        SUM(CASE WHEN type = 'tv' THEN 1 ELSE 0 END) as tv_shows
    FROM movies");
    $counts = $stmt->fetch();

    // Trailer count
    $stmt = $pdo->query("SELECT COUNT(*) as count FROM trailers WHERE is_active = 1");
    $trailers = $stmt->fetch();

    // Last 10 sync logs
    $stmt = $pdo->query("SELECT * FROM sync_log ORDER BY created_at DESC LIMIT 10");
    $recent_logs = $stmt->fetchAll();

    // Movies per year
    $stmt = $pdo->query("SELECT release_year, type, COUNT(*) as count
        FROM movies GROUP BY release_year, type ORDER BY release_year DESC");
    $yearly = $stmt->fetchAll();

    echo json_encode(array(
        'success' => true,
        'timestamp' => date('Y-m-d H:i:s T'),
        'stats' => array(
            'total_titles' => (int)$counts['total'],
            'movies' => (int)$counts['movies'],
            'tv_shows' => (int)$counts['tv_shows'],
            'active_trailers' => (int)$trailers['count']
        ),
        'recent_syncs' => $recent_logs,
        'by_year' => $yearly
    ));

} catch (PDOException $e) {
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array(
        'success' => false,
        'error' => $e->getMessage(),
        'timestamp' => date('Y-m-d H:i:s T')
    ));
}
?>
