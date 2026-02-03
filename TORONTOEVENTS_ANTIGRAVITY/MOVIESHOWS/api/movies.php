<?php
/**
 * Movies API Endpoint
 * GET /api/movies.php - Get all movies with trailers and thumbnails
 * POST /api/movies.php - Create new movie
 * PUT /api/movies.php?id=X - Update movie
 * DELETE /api/movies.php?id=X - Delete movie
 */

require_once 'db-config.php';

$pdo = getDbConnection();
if (!$pdo) {
    sendError('Database connection failed', 500);
}

$method = $_SERVER['REQUEST_METHOD'];
$movieId = isset($_GET['id']) ? intval($_GET['id']) : null;

try {
    switch ($method) {
        case 'GET':
            if ($movieId) {
                getMovie($pdo, $movieId);
            } else {
                getAllMovies($pdo);
            }
            break;

        case 'POST':
            createMovie($pdo);
            break;

        case 'PUT':
            if (!$movieId) {
                sendError('Movie ID required', 400);
            }
            updateMovie($pdo, $movieId);
            break;

        case 'DELETE':
            if (!$movieId) {
                sendError('Movie ID required', 400);
            }
            deleteMovie($pdo, $movieId);
            break;

        default:
            sendError('Method not allowed', 405);
    }
} catch (Exception $e) {
    error_log("Movies API Error: " . $e->getMessage());
    sendError('Internal server error', 500, $e->getMessage());
}

/**
 * Get all movies with their trailers and thumbnails
 */
function getAllMovies($pdo)
{
    $sql = "SELECT * FROM movies ORDER BY created_at DESC";
    $stmt = $pdo->query($sql);
    $movies = $stmt->fetchAll();

    // Fetch trailers and thumbnails for each movie
    foreach ($movies as &$movie) {
        $movie['trailers'] = getMovieTrailers($pdo, $movie['id']);
        $movie['thumbnails'] = getMovieThumbnails($pdo, $movie['id']);
    }

    sendJson(array('movies' => $movies, 'count' => count($movies)));
}

/**
 * Get single movie with trailers and thumbnails
 */
function getMovie($pdo, $movieId)
{
    $sql = "SELECT * FROM movies WHERE id = ?";
    $stmt = $pdo->prepare($sql);
    $stmt->execute(array($movieId));
    $movie = $stmt->fetch();

    if (!$movie) {
        sendError('Movie not found', 404);
    }

    $movie['trailers'] = getMovieTrailers($pdo, $movieId);
    $movie['thumbnails'] = getMovieThumbnails($pdo, $movieId);

    sendJson($movie);
}

/**
 * Get trailers for a movie
 */
function getMovieTrailers($pdo, $movieId)
{
    $sql = "SELECT * FROM trailers WHERE movie_id = ? AND is_active = 1 ORDER BY priority DESC, view_count DESC";
    $stmt = $pdo->prepare($sql);
    $stmt->execute(array($movieId));
    return $stmt->fetchAll();
}

/**
 * Get thumbnails for a movie
 */
function getMovieThumbnails($pdo, $movieId)
{
    $sql = "SELECT * FROM thumbnails WHERE movie_id = ? AND is_active = 1 ORDER BY priority DESC";
    $stmt = $pdo->prepare($sql);
    $stmt->execute(array($movieId));
    return $stmt->fetchAll();
}

/**
 * Create new movie
 */
function createMovie($pdo)
{
    $data = getRequestBody();

    if (!isset($data['title'])) {
        sendError('Title is required', 400);
    }

    $sql = "INSERT INTO movies (title, type, release_year, genre, description, tmdb_id, imdb_id, source) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)";

    $stmt = $pdo->prepare($sql);
    $stmt->execute([
        $data['title'],
        $data['type'] ?? 'movie',
        $data['release_year'] ?? null,
        $data['genre'] ?? null,
        $data['description'] ?? null,
        $data['tmdb_id'] ?? null,
        $data['imdb_id'] ?? null,
        $data['source'] ?? 'manual'
    ]);

    $movieId = $pdo->lastInsertId();

    // Add trailers if provided
    if (isset($data['trailers']) && is_array($data['trailers'])) {
        foreach ($data['trailers'] as $trailer) {
            addTrailer($pdo, $movieId, $trailer);
        }
    }

    // Add thumbnails if provided
    if (isset($data['thumbnails']) && is_array($data['thumbnails'])) {
        foreach ($data['thumbnails'] as $thumbnail) {
            addThumbnail($pdo, $movieId, $thumbnail);
        }
    }

    sendJson(array('id' => $movieId, 'message' => 'Movie created successfully'), 201);
}

/**
 * Add trailer to movie
 */
function addTrailer($pdo, $movieId, $trailerData)
{
    $sql = "INSERT INTO trailers (movie_id, youtube_id, title, priority, source, view_count, duration) 
            VALUES (?, ?, ?, ?, ?, ?, ?)";

    $stmt = $pdo->prepare($sql);
    $stmt->execute([
        $movieId,
        $trailerData['youtube_id'],
        $trailerData['title'] ?? null,
        $trailerData['priority'] ?? 0,
        $trailerData['source'] ?? 'manual',
        $trailerData['view_count'] ?? 0,
        $trailerData['duration'] ?? null
    ]);
}

/**
 * Add thumbnail to movie
 */
function addThumbnail($pdo, $movieId, $thumbnailData)
{
    $sql = "INSERT INTO thumbnails (movie_id, url, source, priority, width, height) 
            VALUES (?, ?, ?, ?, ?, ?)";

    $stmt = $pdo->prepare($sql);
    $stmt->execute([
        $movieId,
        $thumbnailData['url'],
        $thumbnailData['source'] ?? 'manual',
        $thumbnailData['priority'] ?? 0,
        $thumbnailData['width'] ?? null,
        $thumbnailData['height'] ?? null
    ]);
}

/**
 * Update movie
 */
function updateMovie($pdo, $movieId)
{
    $data = getRequestBody();

    $fields = [];
    $values = array();

    $allowedFields = ['title', 'type', 'release_year', 'genre', 'description', 'tmdb_id', 'imdb_id', 'source'];

    foreach ($allowedFields as $field) {
        if (isset($data[$field])) {
            $fields[] = "$field = ?";
            $values[] = $data[$field];
        }
    }

    if (empty($fields)) {
        sendError('No fields to update', 400);
    }

    $values[] = $movieId;
    $sql = "UPDATE movies SET " . implode(', ', $fields) . " WHERE id = ?";

    $stmt = $pdo->prepare($sql);
    $stmt->execute($values);

    sendJson(array('message' => 'Movie updated successfully'));
}

/**
 * Delete movie (cascades to trailers and thumbnails)
 */
function deleteMovie($pdo, $movieId)
{
    $sql = "DELETE FROM movies WHERE id = ?";
    $stmt = $pdo->prepare($sql);
    $stmt->execute(array($movieId));

    if ($stmt->rowCount() === 0) {
        sendError('Movie not found', 404);
    }

    sendJson(array('message' => 'Movie deleted successfully'));
}
