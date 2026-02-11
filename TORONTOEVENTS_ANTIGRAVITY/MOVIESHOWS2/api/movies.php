<?php
/**
 * Movies API - supports actions needed by db-connector.js
 * Compatible with PHP 5.2+
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
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
            $limit = isset($_GET['limit']) ? min((int)$_GET['limit'], 500) : 100;
            $offset = isset($_GET['offset']) ? (int)$_GET['offset'] : 0;

            $where = '1=1';
            if (isset($_GET['type']) && in_array($_GET['type'], array('movie', 'tv'))) {
                $where .= " AND m.type = '" . $pdo->quote($_GET['type']) . "'";
                $where = str_replace("''", "'", $where);
                // Simpler approach
                $where = '1=1';
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
                (SELECT youtube_id FROM trailers WHERE movie_id = m.id AND is_active = TRUE ORDER BY priority DESC LIMIT 1) as trailer_id,
                (SELECT url FROM thumbnails WHERE movie_id = m.id ORDER BY is_primary DESC LIMIT 1) as thumbnail
            FROM movies m
            WHERE $where
            ORDER BY m.created_at DESC
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