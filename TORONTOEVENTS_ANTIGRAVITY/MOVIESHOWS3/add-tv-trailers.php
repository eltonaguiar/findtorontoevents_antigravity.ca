<?php
/**
 * Add trailers to existing TV shows in database
 */
header('Content-Type: text/plain; charset=utf-8');
set_time_limit(300);

require_once 'api/db-config.php';

$pdo = getDbConnection();
if (!$pdo) {
    die("Database connection failed!\n");
}

echo "Adding Trailers to TV Shows\n";
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

// Get all TV shows without trailers
$stmt = $pdo->query("
    SELECT m.id, m.title, m.tmdb_id
    FROM movies m
    LEFT JOIN trailers t ON m.id = t.movie_id AND t.is_active = TRUE
    WHERE m.type = 'tv' AND t.id IS NULL
");

$tvShows = $stmt->fetchAll(PDO::FETCH_ASSOC);
echo "Found " . count($tvShows) . " TV shows without trailers\n\n";

$added = 0;

foreach ($tvShows as $show) {
    try {
        echo "Processing: {$show['title']}...";

        // Fetch TV show details with videos from TMDB
        $detailUrl = "https://api.themoviedb.org/3/tv/{$show['tmdb_id']}?api_key={$tmdbApiKey}&append_to_response=videos";
        $detailResponse = fetchUrl($detailUrl);

        if (!$detailResponse) {
            echo " FAILED (no response)\n";
            continue;
        }

        $details = json_decode($detailResponse, true);

        // Find a trailer
        $trailerAdded = false;
        if (isset($details['videos']['results'])) {
            foreach ($details['videos']['results'] as $video) {
                if ($video['site'] === 'YouTube' && ($video['type'] === 'Trailer' || $video['type'] === 'Teaser')) {
                    $videoKey = $video['key'];
                    $videoName = $video['name'];

                    $stmt = $pdo->prepare("
                        INSERT INTO trailers (movie_id, youtube_id, title, priority, is_active)
                        VALUES (?, ?, ?, 1, TRUE)
                    ");
                    $stmt->execute(array($show['id'], $videoKey, $videoName));

                    echo " ✅ Added trailer: {$videoKey}\n";
                    $trailerAdded = true;
                    $added++;
                    break;
                }
            }
        }

        if (!$trailerAdded) {
            echo " ⚠️ No trailer found\n";
        }

        usleep(250000); // Rate limiting

    } catch (Exception $e) {
        echo " ERROR: " . $e->getMessage() . "\n";
    }
}

echo "\n✅ Done!\n";
echo "Trailers added: $added\n\n";

// Verify
$stmt = $pdo->query("
    SELECT COUNT(DISTINCT m.id) 
    FROM movies m
    INNER JOIN trailers t ON m.id = t.movie_id
    WHERE m.type = 'tv' AND t.is_active = TRUE
");
$tvWithTrailers = $stmt->fetchColumn();

echo "TV shows WITH trailers now: $tvWithTrailers\n";
?>