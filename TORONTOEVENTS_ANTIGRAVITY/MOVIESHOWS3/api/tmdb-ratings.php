<?php
/* The legacy imdb_rating column contains TMDB scores, not IMDb scores. */
function validateTmdbRating($data, $tmdbId) {
    if (!is_array($data) || !isset($data['id']) || (int)$data['id'] !== (int)$tmdbId
        || !isset($data['vote_average']) || !is_numeric($data['vote_average'])
        || is_string($data['vote_average']) || $data['vote_average'] < 0 || $data['vote_average'] > 10
        || !isset($data['vote_count']) || !is_int($data['vote_count']) || $data['vote_count'] < 0) {
        throw new Exception('Invalid TMDB rating data or mismatched title identity');
    }
    return array(
        'rating' => $data['vote_average'],
        'vote_count' => $data['vote_count'],
        'provisional' => $data['vote_count'] < 50
    );
}

function attachTmdbRatingDetails($pdo, $movies) {
    $metadata = $pdo->query("SELECT movie_id, vote_count, checked_at FROM movie_rating_details")->fetchAll();
    $byId = array();
    foreach ($metadata as $row) {
        $byId[$row['movie_id']] = $row;
    }
    foreach ($movies as $index => $movie) {
        $movies[$index]['rating_source'] = 'TMDB';
        $movies[$index]['rating_vote_count'] = null;
        $movies[$index]['rating_provisional'] = null;
        $movies[$index]['rating_checked_at'] = null;
        if (isset($byId[$movie['id']])) {
            $details = $byId[$movie['id']];
            $movies[$index]['rating_vote_count'] = (int)$details['vote_count'];
            $movies[$index]['rating_provisional'] = (int)$details['vote_count'] < 50;
            $movies[$index]['rating_checked_at'] = $details['checked_at'];
        }
    }
    return $movies;
}

function refreshTmdbRatings($pdo, $apiKey) {
    if (!$apiKey) {
        throw new Exception('TMDB credentials unavailable for rating refresh');
    }
    $pdo->exec("CREATE TABLE IF NOT EXISTS movie_rating_details (
        movie_id INT NOT NULL PRIMARY KEY,
        vote_count INT NOT NULL,
        checked_at DATETIME NOT NULL
    ) ENGINE=InnoDB");
    // Keep refreshing the corrected cohort after its scores fall below 10.
    $movies = $pdo->query("SELECT m.id, m.title, m.type, m.tmdb_id, m.imdb_rating
        FROM movies m LEFT JOIN movie_rating_details r ON r.movie_id = m.id
        WHERE (m.imdb_rating >= 10 AND EXISTS (
            SELECT 1 FROM trailers t WHERE t.movie_id = m.id AND t.is_active = TRUE
            AND t.youtube_id IS NOT NULL AND t.youtube_id != ''
        )) OR r.movie_id IS NOT NULL")->fetchAll();
    $results = array();
    $failures = array();
    $errors = 0;
    foreach ($movies as $movie) {
        $transactionActive = false;
        $failureReason = 'invalid_tmdb_identity';
        try {
            if (!in_array($movie['type'], array('movie', 'tv')) || (int)$movie['tmdb_id'] <= 0) {
                throw new Exception('Title has no valid TMDB identity');
            }
            $url = 'https://api.themoviedb.org/3/' . $movie['type'] . '/' . (int)$movie['tmdb_id']
                . '?api_key=' . urlencode($apiKey);
            $failureReason = 'tmdb_request_failed';
            $ch = curl_init($url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, 30);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);
            $body = curl_exec($ch);
            $http = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);
            if ($body === false || $http !== 200) {
                throw new Exception('TMDB rating request failed');
            }
            $failureReason = 'invalid_tmdb_rating';
            $rating = validateTmdbRating(json_decode($body, true), $movie['tmdb_id']);
            $rating['rating'] = round($rating['rating'], 1);
            $checked = date('Y-m-d H:i:s');
            $failureReason = 'database_write_failed';
            $pdo->beginTransaction();
            $transactionActive = true;
            $stmt = $pdo->prepare("UPDATE movies SET imdb_rating = ? WHERE id = ? AND tmdb_id = ?");
            $stmt->execute(array($rating['rating'], $movie['id'], $movie['tmdb_id']));
            $stmt = $pdo->prepare("INSERT INTO movie_rating_details (movie_id, vote_count, checked_at)
                VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE vote_count = VALUES(vote_count), checked_at = VALUES(checked_at)");
            $stmt->execute(array($movie['id'], $rating['vote_count'], $checked));
            $pdo->commit();
            $transactionActive = false;
            $results[] = array(
                'id' => (int)$movie['id'],
                'title' => $movie['title'],
                'old_rating' => $movie['imdb_rating'],
                'rating' => $rating['rating'],
                'vote_count' => $rating['vote_count'],
                'provisional' => $rating['provisional'],
                'checked_at' => $checked
            );
        } catch (Exception $error) {
            if ($transactionActive) {
                $pdo->rollBack();
            }
            error_log('TMDB rating refresh failed for movie ID ' . (int)$movie['id'] . ': ' . $error->getMessage());
            $failures[] = array('id' => (int)$movie['id'], 'title' => $movie['title'], 'reason' => $failureReason);
            $errors++;
        }
    }
    return array('success' => $errors === 0, 'errors' => $errors, 'failures' => $failures,
        'refreshed' => count($results), 'ratings' => $results);
}
?>
