<?php
/**
 * Batch Add Movies to MOVIESHOWS database
 * Inserts movies + trailers + thumbnails with duplicate detection
 *
 * Usage: ?key=ms2_sync_2024_findto
 * Method: GET (movies are hardcoded in this batch script)
 *
 * PHP 5.2 compatible (no short array syntax, no ?? operator)
 */
error_reporting(0);
ini_set('display_errors', '0');

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

// ---- Auth check ----
$key = isset($_GET['key']) ? $_GET['key'] : '';
if ($key !== 'ms2_sync_2024_findto') {
    http_response_code(403);
    echo json_encode(array(
        'success' => false,
        'error' => 'Unauthorized. Provide ?key=...'
    ));
    exit;
}

// ---- DB connection ----
$dbConfigPath = dirname(__FILE__) . '/db-config.php';
if (!file_exists($dbConfigPath)) {
    echo json_encode(array(
        'success' => false,
        'error' => 'Missing db-config.php'
    ));
    exit;
}

require_once $dbConfigPath;

if (!function_exists('getDbConnection')) {
    echo json_encode(array(
        'success' => false,
        'error' => 'getDbConnection() not defined'
    ));
    exit;
}

$pdo = getDbConnection();
if ($pdo === null) {
    echo json_encode(array(
        'success' => false,
        'error' => 'Database connection failed'
    ));
    exit;
}

// ---- Movies to add ----
$movies_to_add = array(
    array(
        'title'        => 'Hellfire',
        'type'         => 'movie',
        'genre'        => 'Action, Thriller',
        'description'  => 'A haunted ex-Green Beret drifter wanders into a Southern town controlled by a criminal syndicate. He wages a one-man war against the corrupt powers for justice and redemption.',
        'release_year' => 2026,
        'imdb_rating'  => 6.1,
        'imdb_id'      => 'tt14507394',
        'tmdb_id'      => 1088434,
        'runtime'      => 95,
        'youtube_id'   => 'XVMVJX0H2Ss',
        'thumbnail'    => 'https://image.tmdb.org/t/p/w500/v7bwDmkw40TqcYGLCFGzNJ6EFBK.jpg'
    ),
    array(
        'title'        => 'Crime 101',
        'type'         => 'movie',
        'genre'        => 'Crime, Drama, Thriller',
        'description'  => 'An elusive jewel thief\'s heists along the 101 freeway mystify police. When he eyes the score of a lifetime, his path crosses a disillusioned insurance broker facing her own crossroads.',
        'release_year' => 2026,
        'imdb_rating'  => 7.2,
        'imdb_id'      => 'tt32430579',
        'tmdb_id'      => 1171145,
        'runtime'      => 139,
        'youtube_id'   => 'f5y-cziwmMw',
        'thumbnail'    => 'https://image.tmdb.org/t/p/w500/ixquhfJshfLSPQIkYUfCBmJOOvP.jpg'
    )
);

// ---- Process each movie ----
$results = array();

foreach ($movies_to_add as $movie) {
    $entry = array(
        'title'   => $movie['title'],
        'tmdb_id' => $movie['tmdb_id'],
        'status'  => 'pending'
    );

    try {
        // Check for duplicate by tmdb_id
        $checkStmt = $pdo->prepare("SELECT id, title FROM movies WHERE tmdb_id = ?");
        $checkStmt->execute(array($movie['tmdb_id']));
        $existing = $checkStmt->fetch(PDO::FETCH_ASSOC);

        if ($existing) {
            $entry['status'] = 'skipped';
            $entry['reason'] = 'Already exists with id=' . $existing['id'] . ' title="' . $existing['title'] . '"';
            $entry['movie_id'] = $existing['id'];
            $results[] = $entry;
            continue;
        }

        // Also check by imdb_id as secondary duplicate detection
        $checkImdb = $pdo->prepare("SELECT id, title FROM movies WHERE imdb_id = ?");
        $checkImdb->execute(array($movie['imdb_id']));
        $existingImdb = $checkImdb->fetch(PDO::FETCH_ASSOC);

        if ($existingImdb) {
            $entry['status'] = 'skipped';
            $entry['reason'] = 'Already exists by imdb_id with id=' . $existingImdb['id'] . ' title="' . $existingImdb['title'] . '"';
            $entry['movie_id'] = $existingImdb['id'];
            $results[] = $entry;
            continue;
        }

        // Begin transaction
        $pdo->beginTransaction();

        // 1. Insert movie
        $insertMovie = $pdo->prepare(
            "INSERT INTO movies (title, type, genre, description, release_year, imdb_rating, imdb_id, tmdb_id, runtime, created_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW())"
        );
        $insertMovie->execute(array(
            $movie['title'],
            $movie['type'],
            $movie['genre'],
            $movie['description'],
            $movie['release_year'],
            $movie['imdb_rating'],
            $movie['imdb_id'],
            $movie['tmdb_id'],
            $movie['runtime']
        ));
        $movieId = $pdo->lastInsertId();

        // 2. Insert trailer
        $insertTrailer = $pdo->prepare(
            "INSERT INTO trailers (movie_id, youtube_id, is_active, priority, source, created_at)
             VALUES (?, ?, TRUE, 1, 'manual', NOW())"
        );
        $insertTrailer->execute(array(
            $movieId,
            $movie['youtube_id']
        ));

        // 3. Insert thumbnail
        $insertThumb = $pdo->prepare(
            "INSERT INTO thumbnails (movie_id, url, is_primary, created_at)
             VALUES (?, ?, TRUE, NOW())"
        );
        $insertThumb->execute(array(
            $movieId,
            $movie['thumbnail']
        ));

        // Commit transaction
        $pdo->commit();

        $entry['status'] = 'added';
        $entry['movie_id'] = $movieId;
        $entry['trailer_youtube_id'] = $movie['youtube_id'];
        $entry['thumbnail_url'] = $movie['thumbnail'];

    } catch (Exception $e) {
        // Rollback on error
        if ($pdo->inTransaction()) {
            $pdo->rollBack();
        }
        $entry['status'] = 'error';
        $entry['error'] = $e->getMessage();
    }

    $results[] = $entry;
}

// ---- Summary ----
$added = 0;
$skipped = 0;
$errors = 0;
foreach ($results as $r) {
    if ($r['status'] === 'added') {
        $added++;
    } elseif ($r['status'] === 'skipped') {
        $skipped++;
    } elseif ($r['status'] === 'error') {
        $errors++;
    }
}

echo json_encode(array(
    'success' => ($errors === 0),
    'summary' => array(
        'total'   => count($movies_to_add),
        'added'   => $added,
        'skipped' => $skipped,
        'errors'  => $errors
    ),
    'results' => $results,
    'timestamp' => date('Y-m-d H:i:s')
));
?>
