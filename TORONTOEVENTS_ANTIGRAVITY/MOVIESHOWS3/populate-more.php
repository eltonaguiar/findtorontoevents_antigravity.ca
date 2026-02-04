<?php
/**
 * Populate MORE movies - 10 pages instead of 2
 */
header('Content-Type: text/plain; charset=utf-8');
set_time_limit(600);

require_once 'api/db-config.php';

$pdo = getDbConnection();
if (!$pdo) {
    die("Database connection failed!\n");
}

echo "Populating MORE Movies (10 pages)\n";
echo "==================================\n\n";

$tmdbApiKey = '15d2ea6d0dc1d476efbca3eba2b9bbfb';
$totalAdded = 0;

function fetchUrl($url)
{
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);
    $response = curl_exec($ch);
    curl_close($ch);
    return $response;
}

// Fetch 10 pages of popular movies
for ($page = 1; $page <= 10; $page++) {
    echo "Page $page...\n";

    $url = "https://api.themoviedb.org/3/movie/popular?api_key={$tmdbApiKey}&page={$page}";
    $response = fetchUrl($url);

    if (!$response) {
        echo "  Failed\n";
        continue;
    }

    $data = json_decode($response, true);
    if (!isset($data['results'])) {
        echo "  Invalid response\n";
        continue;
    }

    foreach ($data['results'] as $movie) {
        try {
            $movieTmdbId = $movie['id'];

            // Check if exists
            $stmt = $pdo->prepare("SELECT id FROM movies WHERE tmdb_id = ?");
            $stmt->execute(array($movieTmdbId));
            if ($stmt->fetch()) {
                continue;
            }

            // Get details with videos
            $detailUrl = "https://api.themoviedb.org/3/movie/{$movieTmdbId}?api_key={$tmdbApiKey}&append_to_response=videos";
            $detailResponse = fetchUrl($detailUrl);

            if (!$detailResponse) {
                continue;
            }

            $details = json_decode($detailResponse, true);

            // Extract genres
            $genres = array();
            if (isset($details['genres'])) {
                foreach ($details['genres'] as $genre) {
                    $genres[] = $genre['name'];
                }
            }
            $genreStr = implode(', ', $genres);

            // Insert movie
            $stmt = $pdo->prepare("
                INSERT INTO movies (title, type, genre, description, release_year, imdb_rating, imdb_id, tmdb_id, runtime)
                VALUES (?, 'movie', ?, ?, ?, ?, ?, ?, ?)
            ");

            $movieTitle = isset($details['title']) ? $details['title'] : $movie['title'];
            $movieDesc = isset($details['overview']) ? $details['overview'] : '';
            $releaseYear = isset($details['release_date']) ? (int) substr($details['release_date'], 0, 4) : null;
            $rating = isset($details['vote_average']) ? round($details['vote_average'], 1) : null;
            $imdbId = isset($details['imdb_id']) ? $details['imdb_id'] : null;
            $runtime = isset($details['runtime']) ? $details['runtime'] : null;

            $stmt->execute(array(
                $movieTitle,
                $genreStr,
                $movieDesc,
                $releaseYear,
                $rating,
                $imdbId,
                $movieTmdbId,
                $runtime
            ));

            $movieId = $pdo->lastInsertId();

            // Insert trailer
            $trailerAdded = false;
            if (isset($details['videos']['results'])) {
                foreach ($details['videos']['results'] as $video) {
                    if ($video['site'] === 'YouTube' && $video['type'] === 'Trailer') {
                        $videoKey = $video['key'];
                        $videoName = $video['name'];
                        $stmt = $pdo->prepare("
                            INSERT INTO trailers (movie_id, youtube_id, title, priority, is_active)
                            VALUES (?, ?, ?, 1, TRUE)
                        ");
                        $stmt->execute(array($movieId, $videoKey, $videoName));
                        $trailerAdded = true;
                        break;
                    }
                }
            }

            // Insert thumbnail
            if (isset($movie['poster_path'])) {
                $stmt = $pdo->prepare("
                    INSERT INTO thumbnails (movie_id, url, is_primary)
                    VALUES (?, ?, TRUE)
                ");
                $thumbnailUrl = "https://image.tmdb.org/t/p/w500" . $movie['poster_path'];
                $stmt->execute(array($movieId, $thumbnailUrl));
            }

            if ($trailerAdded) {
                $totalAdded++;
                echo "  ✅ {$movieTitle}\n";
            }

            usleep(250000); // Rate limiting

        } catch (Exception $e) {
            // Skip errors
        }
    }
}

echo "\n✅ Done!\n";
echo "New movies with trailers: $totalAdded\n\n";

// Verify
$stmt = $pdo->query("SELECT COUNT(*) FROM movies");
$movieCount = $stmt->fetchColumn();

$stmt = $pdo->query("SELECT COUNT(DISTINCT movie_id) FROM trailers WHERE is_active = TRUE");
$trailerCount = $stmt->fetchColumn();

echo "Total movies: $movieCount\n";
echo "Movies with trailers: $trailerCount\n";
?>