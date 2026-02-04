<?php
/**
 * Populate popular TV shows with trailers from TMDB
 */
header('Content-Type: text/plain; charset=utf-8');
set_time_limit(300);

require_once 'api/db-config.php';

$pdo = getDbConnection();
if (!$pdo) {
    die("Database connection failed!\n");
}

echo "Populating Popular TV Shows\n";
echo "============================\n\n";

$tmdbApiKey = '15d2ea6d0dc1d476efbca3eba2b9bbfb';

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

$added = 0;
$skipped = 0;

// Fetch popular TV shows from TMDB (5 pages = 100 shows)
for ($page = 1; $page <= 5; $page++) {
    echo "Fetching page $page...\n";

    $url = "https://api.themoviedb.org/3/tv/popular?api_key={$tmdbApiKey}&page={$page}";
    $response = fetchUrl($url);

    if (!$response) {
        echo "Failed to fetch page $page\n";
        continue;
    }

    $data = json_decode($response, true);

    if (!isset($data['results'])) {
        echo "No results in page $page\n";
        continue;
    }

    foreach ($data['results'] as $show) {
        try {
            $showTmdbId = $show['id'];

            // Check if already exists
            $stmt = $pdo->prepare("SELECT id FROM movies WHERE tmdb_id = ?");
            $stmt->execute(array($showTmdbId));
            if ($stmt->fetch()) {
                $skipped++;
                continue;
            }

            // Fetch full details with videos
            $detailUrl = "https://api.themoviedb.org/3/tv/{$showTmdbId}?api_key={$tmdbApiKey}&append_to_response=videos";
            $detailResponse = fetchUrl($detailUrl);

            if (!$detailResponse) {
                continue;
            }

            $details = json_decode($detailResponse, true);

            // Find a trailer
            $trailerKey = null;
            $trailerName = null;

            if (isset($details['videos']['results'])) {
                foreach ($details['videos']['results'] as $video) {
                    if ($video['site'] === 'YouTube' && ($video['type'] === 'Trailer' || $video['type'] === 'Teaser')) {
                        $trailerKey = $video['key'];
                        $trailerName = $video['name'];
                        break;
                    }
                }
            }

            // Only add if we have a trailer
            if (!$trailerKey) {
                continue;
            }

            // Prepare data
            $title = $show['name'];
            $description = isset($show['overview']) ? $show['overview'] : '';
            $releaseYear = isset($show['first_air_date']) ? substr($show['first_air_date'], 0, 4) : null;
            $rating = isset($show['vote_average']) ? round($show['vote_average'], 1) : null;

            $genres = array();
            if (isset($details['genres'])) {
                foreach ($details['genres'] as $genre) {
                    $genres[] = $genre['name'];
                }
            }
            $genreStr = implode(', ', $genres);

            // Insert TV show
            $stmt = $pdo->prepare("
                INSERT INTO movies (title, type, genre, description, release_year, imdb_rating, tmdb_id)
                VALUES (?, 'tv', ?, ?, ?, ?, ?)
            ");

            $stmt->execute(array(
                $title,
                $genreStr,
                $description,
                $releaseYear,
                $rating,
                $showTmdbId
            ));

            $movieId = $pdo->lastInsertId();

            // Add trailer
            $stmt = $pdo->prepare("
                INSERT INTO trailers (movie_id, youtube_id, title, priority, is_active)
                VALUES (?, ?, ?, 1, TRUE)
            ");
            $stmt->execute(array($movieId, $trailerKey, $trailerName));

            // Add thumbnail
            if (isset($show['poster_path'])) {
                $thumbnailUrl = "https://image.tmdb.org/t/p/w500" . $show['poster_path'];
                $stmt = $pdo->prepare("
                    INSERT INTO thumbnails (movie_id, url, is_primary)
                    VALUES (?, ?, TRUE)
                ");
                $stmt->execute(array($movieId, $thumbnailUrl));
            }

            echo "✅ Added: {$title} ({$releaseYear}) - Trailer: {$trailerKey}\n";
            $added++;

            usleep(250000); // Rate limiting

        } catch (Exception $e) {
            echo "ERROR: " . $e->getMessage() . "\n";
        }
    }
}

echo "\n✅ Done!\n";
echo "TV shows added: $added\n";
echo "Skipped (already exist): $skipped\n\n";

// Verify
$stmt = $pdo->query("
    SELECT COUNT(DISTINCT m.id) 
    FROM movies m
    INNER JOIN trailers t ON m.id = t.movie_id
    WHERE m.type = 'tv' AND t.is_active = TRUE
");
$tvWithTrailers = $stmt->fetchColumn();

echo "Total TV shows WITH trailers: $tvWithTrailers\n";
?>