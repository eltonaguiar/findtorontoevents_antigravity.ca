<?php
/**
 * Admin Search API - Search TMDB and check against local database
 * Returns TMDB results annotated with whether they already exist locally
 *
 * Query params:
 *   ?q=search+term   (required)
 *   &type=movie|tv|multi  (default: multi)
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

$TMDB_API_KEY = 'b84ff7bfe35ffad8779b77bcbbda317f';
$TMDB_READ_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJiODRmZjdiZmUzNWZmYWQ4Nzc5Yjc3YmNiYmRhMzE3ZiIsIm5iZiI6MTU4NTg2ODk2NC41Mzc5OTk5LCJzdWIiOiI1ZTg2NzBhNGE1NzQzZDAwMTEwZmU3MWUiLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.zKkPzhHNhnlghJQeJJz2GddR8NEI_TzXAUgU96Ky_Q4';

$query = isset($_GET['q']) ? trim($_GET['q']) : '';
$type = isset($_GET['type']) ? $_GET['type'] : 'multi';

if ($query === '') {
    echo json_encode(array('success' => false, 'error' => 'Missing search query (?q=...)'));
    exit;
}

// DB connection
$host = 'localhost';
$dbname = 'ejaguiar1_tvmoviestrailers';
$dbuser = 'ejaguiar1_tvmoviestrailers';
$dbpass = 'D41$4Jci6T9W2PsJdagLEr*KMo96nrCD';

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $dbuser, $dbpass);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    echo json_encode(array('success' => false, 'error' => 'DB connection failed'));
    exit;
}

// Load existing tmdb_ids
$existingTmdb = array();
$stmt = $pdo->query("SELECT tmdb_id, type FROM movies WHERE tmdb_id IS NOT NULL");
while ($row = $stmt->fetch()) {
    $existingTmdb[(int)$row['tmdb_id']] = $row['type'];
}

// Search TMDB
$searchType = ($type === 'multi') ? 'multi' : $type;
$url = "https://api.themoviedb.org/3/search/{$searchType}?api_key={$TMDB_API_KEY}&query=" . urlencode($query) . "&page=1";

$ch = curl_init();
curl_setopt_array($ch, array(
    CURLOPT_URL => $url,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT => 15,
    CURLOPT_HTTPHEADER => array(
        'Authorization: Bearer ' . $TMDB_READ_TOKEN,
        'Accept: application/json'
    ),
    CURLOPT_SSL_VERIFYPEER => false
));
$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpCode !== 200 || !$response) {
    echo json_encode(array('success' => false, 'error' => 'TMDB API request failed'));
    exit;
}

$data = json_decode($response, true);

if (!isset($data['results'])) {
    echo json_encode(array('success' => false, 'error' => 'Invalid TMDB response'));
    exit;
}

$results = array();
foreach ($data['results'] as $item) {
    $mediaType = isset($item['media_type']) ? $item['media_type'] : $type;
    if ($mediaType === 'person') continue; // Skip people in multi search

    $tmdbId = (int)$item['id'];
    $title = isset($item['title']) ? $item['title'] : (isset($item['name']) ? $item['name'] : 'Unknown');
    $releaseDate = isset($item['release_date']) ? $item['release_date'] : (isset($item['first_air_date']) ? $item['first_air_date'] : '');
    $year = $releaseDate ? (int)substr($releaseDate, 0, 4) : null;

    $results[] = array(
        'tmdb_id' => $tmdbId,
        'title' => $title,
        'type' => $mediaType,
        'year' => $year,
        'overview' => isset($item['overview']) ? substr($item['overview'], 0, 200) : '',
        'poster' => isset($item['poster_path']) ? 'https://image.tmdb.org/t/p/w200' . $item['poster_path'] : null,
        'rating' => isset($item['vote_average']) ? round($item['vote_average'], 1) : null,
        'in_database' => isset($existingTmdb[$tmdbId]),
        'db_type' => isset($existingTmdb[$tmdbId]) ? $existingTmdb[$tmdbId] : null
    );
}

echo json_encode(array(
    'success' => true,
    'query' => $query,
    'total_results' => isset($data['total_results']) ? $data['total_results'] : count($results),
    'results' => $results
));
?>
