<?php
/**
 * Update providers for a single movie by database ID
 * Usage: update-single-movie.php?id=580
 */
header('Content-Type: text/plain');
require_once 'db-config.php';
require_once 'run-provider-update.php'; // This will define constants and load before the update runs

// Override $_GET for the main script
$movieId = isset($_GET['id']) ? intval($_GET['id']) : 0;

if ($movieId === 0) {
    die("Usage: update-single-movie.php?id=MOVIE_ID\n");
}

// Fetch the specific movie
$pdo = getDbConnection();
$stmt = $pdo->prepare("SELECT id, title, type, tmdb_id FROM movies WHERE id = ?");
$stmt->execute(array($movieId));
$movie = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$movie) {
    die("Movie ID $movieId not found\n");
}

echo "Updating: {$movie['title']} (ID: {$movie['id']}, TMDB: {$movie['tmdb_id']})\n\n";

// Trigger run-provider-update with this single movie
$_GET['limit'] = 1;
$_GET['offset'] = 0;

// Temporarily override the SELECT query to target this specific ID
$GLOBALS['override_movie_id'] = $movieId;
