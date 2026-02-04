<?php
/**
 * Populate database using cURL (since file_get_contents is disabled)
 * Fetches movies from TMDB API
 */
header('Content-Type: text/plain; charset=utf-8');
set_time_limit(600);

require_once 'api/db-config.php';

$pdo = getDbConnection();
if (!$pdo) {
    die("Database connection failed!\n");
}

echo "Populating MovieShows Database with cURL\n";
echo "=========================================\n\n";

$tmdbApiKey = '15d2ea6d0dc1d476efbca3eba2b9bbfb';
$totalAdded = 0;
$errors = 0;

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

// Fetch popular movies (just 2 pages for now to test)
for ($page = 1; $page <= 2; $page++) {
    echo "Fetching page $page...\n";

    $url = "https://api.themoviedb.org/3/movie/popular?api_key={$tmdbApiKey}&page={$page}";
    $response = fetchUrl($url);

    if (!$response) {
        echo "  Failed to fetch page $page\n";
        continue;
    }

    $data = json_decode($response, true);
    if (!isset($data['results'])) {
        echo "  Invalid response for page $page\n";
        continue;
    }

    foreach ($data['results'] as $movie) {
        try {
            $movieTmdbId = $movie['id'];

            // Check if exists
            $stmt = $pdo->prepare("SELECT id FROM movies WHERE tmdb_id = ?");
            $stmt->execute(array($movieTmdbId));
            if ($stmt->fetch()) {
                echo "  Skipping {$movie['title']} (already exists)\n";
                continue;
            }

            // Get movie details with videos
            $detailUrl = "https://api.themoviedb.org/3/movie/{$movieTmdbId}?api_key={$tmdbApiKey}&append_to_response=videos";
            $detailResponse = fetchUrl($detailUrl);

            if (!$detailResponse) {
                echo "  Failed to fetch details for {$movie['title']}\n";
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

            $totalAdded++;
            $trailerStatus = $trailerAdded ? '✅' : '⚠️ NO TRAILER';
            echo "  ✅ Added: {$movieTitle} {$trailerStatus}\n";

            usleep(250000); // Rate limiting

        } catch (PDOException $e) {
            $errors++;
            echo "  ❌ Error: " . $e->getMessage() . "\n";
        }
    }
}

echo "\n✅ Population complete!\n";
echo "Movies added: $totalAdded\n";
echo "Errors: $errors\n\n";

// Verify
$stmt = $pdo->query("SELECT COUNT(*) FROM movies");
$movieCount = $stmt->fetchColumn();

$stmt = $pdo->query("SELECT COUNT(DISTINCT movie_id) FROM trailers WHERE is_active = TRUE");
$trailerCount = $stmt->fetchColumn();

echo "Total movies in database: $movieCount\n";
echo "Movies with trailers: $trailerCount\n";
?>