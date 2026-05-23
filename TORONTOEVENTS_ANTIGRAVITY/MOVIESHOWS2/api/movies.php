<?php
/**
 * Movies API - supports actions needed by db-connector.js
 * Compatible with PHP 5.2+
 */
error_reporting(0);
ini_set('display_errors', '0');

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

require_once 'db-config.php';

$action = isset($_GET['action']) ? $_GET['action'] : 'list';

$pdo = getDbConnection();
if (!$pdo) {
    header('HTTP/1.0 500 Internal Server Error');
    echo json_encode(array('success' => false, 'error' => 'Database connection failed'));
    exit;
}

try {
    switch ($action) {

        case 'stats':
            $total = $pdo->query("SELECT COUNT(*) FROM movies")->fetchColumn();
            $movies = $pdo->query("SELECT COUNT(*) FROM movies WHERE type = 'movie'")->fetchColumn();
            $tv = $pdo->query("SELECT COUNT(*) FROM movies WHERE type = 'tv'")->fetchColumn();
            $trailers = $pdo->query("SELECT COUNT(*) FROM trailers WHERE is_active = TRUE")->fetchColumn();

            echo json_encode(array(
                'success' => true,
                'stats' => array(
                    'total' => (int)$total,
                    'movies' => (int)$movies,
                    'tv_shows' => (int)$tv,
                    'trailers' => (int)$trailers
                )
            ));
            break;

        case 'list':
            $limit = isset($_GET['limit']) ? min((int)$_GET['limit'], 5000) : 5000;
            $offset = isset($_GET['offset']) ? (int)$_GET['offset'] : 0;

            $where = '1=1';
            if (isset($_GET['type']) && in_array($_GET['type'], array('movie', 'tv'))) {
                if ($_GET['type'] === 'movie') {
                    $where .= " AND m.type = 'movie'";
                } else {
                    $where .= " AND m.type = 'tv'";
                }
            }
            if (isset($_GET['year']) && is_numeric($_GET['year'])) {
                $where .= " AND m.release_year = " . (int)$_GET['year'];
            }

            $sql = "SELECT
                m.id, m.title, m.type, m.genre, m.description,
                m.release_year, m.imdb_rating, m.imdb_id, m.tmdb_id, m.runtime,
                t.youtube_id as trailer_id,
                (SELECT url FROM thumbnails WHERE movie_id = m.id ORDER BY is_primary DESC LIMIT 1) as thumbnail
            FROM movies m
            INNER JOIN trailers t ON t.movie_id = m.id AND t.is_active = TRUE
            WHERE $where AND t.youtube_id IS NOT NULL AND t.youtube_id != ''
            GROUP BY m.id
            ORDER BY m.imdb_rating DESC, m.created_at DESC
            LIMIT $limit OFFSET $offset";

            $stmt = $pdo->query($sql);
            $results = $stmt->fetchAll();

            echo json_encode(array(
                'success' => true,
                'count' => count($results),
                'movies' => $results
            ));
            break;

        case 'search':
            $q = isset($_GET['q']) ? $_GET['q'] : '';
            $limit = isset($_GET['limit']) ? min((int)$_GET['limit'], 50) : 20;

            if (strlen($q) < 1) {
                echo json_encode(array('success' => true, 'count' => 0, 'movies' => array()));
                break;
            }

            $searchTerm = '%' . $q . '%';
            $stmt = $pdo->prepare("SELECT
                m.id, m.title, m.type, m.genre, m.description,
                m.release_year, m.imdb_rating, m.imdb_id, m.tmdb_id, m.runtime,
                (SELECT youtube_id FROM trailers WHERE movie_id = m.id AND is_active = TRUE ORDER BY priority DESC LIMIT 1) as trailer_id,
                (SELECT url FROM thumbnails WHERE movie_id = m.id ORDER BY is_primary DESC LIMIT 1) as thumbnail
            FROM movies m
            WHERE m.title LIKE ?
            ORDER BY m.imdb_rating DESC
            LIMIT $limit");
            $stmt->execute(array($searchTerm));
            $results = $stmt->fetchAll();

            echo json_encode(array(
                'success' => true,
                'count' => count($results),
                'movies' => $results
            ));
            break;

        case 'top_by_genre':
            $limit = isset($_GET['limit']) ? min((int)$_GET['limit'], 20) : 10;

            $genres = array('Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Drama',
                'Family', 'Fantasy', 'Horror', 'Mystery', 'Romance', 'Sci-Fi', 'Thriller',
                'War', 'History', 'Biography', 'Music', 'Sport', 'Documentary');

            $result = array();

            foreach ($genres as $genre) {
                $stmt = $pdo->prepare("SELECT
                    m.id, m.title, m.type, m.genre, m.release_year, m.imdb_rating, m.runtime,
                    t.youtube_id as trailer_id,
                    (SELECT url FROM thumbnails WHERE movie_id = m.id ORDER BY is_primary DESC LIMIT 1) as thumbnail
                FROM movies m
                INNER JOIN trailers t ON t.movie_id = m.id AND t.is_active = TRUE
                WHERE m.genre LIKE ? AND t.youtube_id IS NOT NULL AND t.youtube_id != ''
                GROUP BY m.id
                ORDER BY m.imdb_rating DESC
                LIMIT " . $limit);
                $stmt->execute(array('%' . $genre . '%'));
                $movies = $stmt->fetchAll();
                if (count($movies) >= 3) {
                    $result[] = array('genre' => $genre, 'movies' => $movies);
                }
            }

            echo json_encode(array(
                'success' => true,
                'categories' => $result
            ));
            break;

        case 'random':
            $count = isset($_GET['count']) ? min((int)$_GET['count'], 50) : 10;

            $where = '1=1';
            if (isset($_GET['type']) && in_array($_GET['type'], array('movie', 'tv'))) {
                if ($_GET['type'] === 'movie') {
                    $where .= " AND m.type = 'movie'";
                } else {
                    $where .= " AND m.type = 'tv'";
                }
            }

            $stmt = $pdo->query("SELECT
                m.id, m.title, m.type, m.genre, m.description,
                m.release_year, m.imdb_rating, m.imdb_id, m.tmdb_id, m.runtime,
                (SELECT youtube_id FROM trailers WHERE movie_id = m.id AND is_active = TRUE ORDER BY priority DESC LIMIT 1) as trailer_id,
                (SELECT url FROM thumbnails WHERE movie_id = m.id ORDER BY is_primary DESC LIMIT 1) as thumbnail
            FROM movies m
            WHERE $where
            ORDER BY RAND()
            LIMIT $count");
            $results = $stmt->fetchAll();

            echo json_encode(array(
                'success' => true,
                'count' => count($results),
                'movies' => $results
            ));
            break;

        default:
            echo json_encode(array('success' => false, 'error' => 'Unknown action: ' . $action));
            break;
    }

} catch (Exception $e) {
    header('HTTP/1.0 500 Internal Server Error');
    echo json_encode(array('success' => false, 'error' => $e->getMessage()));
}
?>
