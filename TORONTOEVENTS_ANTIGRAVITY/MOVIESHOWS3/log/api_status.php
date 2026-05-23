<?php
/**
 * API Status — returns DB stats for the MOVIESHOWS3 admin dashboard.
 * Uses shared api/db-config.php with credential fallback chain.
 *
 * PHP 5.2 compatible — no short array syntax, no ?? operator
 */
error_reporting(0);
ini_set('display_errors', '0');

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

// ---- DB connection (use shared config with credential fallback) ----
$dbConfigPath = dirname(__FILE__) . '/../api/db-config.php';
if (!file_exists($dbConfigPath)) {
    echo json_encode(array(
        'success' => false,
        'error' => 'Missing api/db-config.php',
        'timestamp' => date('Y-m-d H:i:s')
    ));
    exit;
}

require_once $dbConfigPath;

if (!function_exists('getDbConnection')) {
    echo json_encode(array(
        'success' => false,
        'error' => 'getDbConnection() not defined',
        'timestamp' => date('Y-m-d H:i:s')
    ));
    exit;
}

$pdo = getDbConnection();
if ($pdo === null) {
    echo json_encode(array(
        'success' => false,
        'error' => 'DB connection failed',
        'timestamp' => date('Y-m-d H:i:s')
    ));
    exit;
}

// ---- Gather stats ----
try {
    $totalStmt = $pdo->query("SELECT COUNT(*) AS total FROM movies");
    $totalRow = $totalStmt->fetch(PDO::FETCH_ASSOC);
    $totalRecords = (int)$totalRow['total'];

    $movieStmt = $pdo->query("SELECT COUNT(*) AS cnt FROM movies WHERE type = 'movie'");
    $movieRow = $movieStmt->fetch(PDO::FETCH_ASSOC);
    $totalMovies = (int)$movieRow['cnt'];

    $tvStmt = $pdo->query("SELECT COUNT(*) AS cnt FROM movies WHERE type = 'tv'");
    $tvRow = $tvStmt->fetch(PDO::FETCH_ASSOC);
    $totalTV = (int)$tvRow['cnt'];

    $trailerStmt = $pdo->query("SELECT COUNT(*) AS cnt FROM trailers WHERE is_active = TRUE AND youtube_id IS NOT NULL AND youtube_id != ''");
    $trailerRow = $trailerStmt->fetch(PDO::FETCH_ASSOC);
    $totalTrailers = (int)$trailerRow['cnt'];

    $latestStmt = $pdo->query("SELECT MAX(created_at) AS latest FROM movies");
    $latestRow = $latestStmt->fetch(PDO::FETCH_ASSOC);
    $lastUpdate = $latestRow['latest'];

    echo json_encode(array(
        'success' => true,
        'total_records' => $totalRecords,
        'total_movies' => $totalMovies,
        'total_tv' => $totalTV,
        'total_trailers' => $totalTrailers,
        'last_update' => $lastUpdate,
        'db' => 'ejaguiar1_tvmoviestrailers',
        'timestamp' => date('Y-m-d H:i:s')
    ));

} catch (Exception $e) {
    echo json_encode(array(
        'success' => false,
        'error' => $e->getMessage(),
        'timestamp' => date('Y-m-d H:i:s')
    ));
}
?>
