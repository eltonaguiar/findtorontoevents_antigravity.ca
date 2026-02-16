<?php
/**
 * YouTube Trailer Description Scraper (PHP version)
 *
 * Scrapes YouTube trailer descriptions for streaming platform mentions
 * Usage: scrape-youtube-providers.php?limit=50&offset=0
 */

set_time_limit(600);
header('Content-Type: text/plain; charset=utf-8');

require_once 'db-config.php';

define('YOUTUBE_API_KEY', 'AIzaSyBjZruHqjPi2I5XEkpfoNMO5LY-8pzbvgs'); // YouTube Data API v3

$PROVIDER_PATTERNS = array(
    '8' => array(
        'name' => 'Netflix',
        'patterns' => array(
            '/(?:available|streaming|watch|now).*?(?:on|@)\s*netflix/i',
            '/netflix\s+(?:original|exclusive)/i',
            '/only on netflix/i',
            '/netflix\.com/i'
        ),
        'logo' => 'https://image.tmdb.org/t/p/original/pbpMk2JmcoNnQwx5JGpXngfoWtp.jpg'
    ),
    '9' => array(
        'name' => 'Prime Video',
        'patterns' => array(
            '/(?:available|streaming|watch|now).*?(?:on|@)\s*(?:amazon\s*)?prime\s*video/i',
            '/prime\s*video\s+(?:original|exclusive)/i',
            '/only on prime/i',
            '/primevideo\.com/i'
        ),
        'logo' => 'https://image.tmdb.org/t/p/original/emthp39XA2YScoYL1p0sdbAH2WA.jpg'
    ),
    '337' => array(
        'name' => 'Disney+',
        'patterns' => array(
            '/(?:available|streaming|watch|now).*?(?:on|@)\s*disney\s*\+/i',
            '/disney\s*\+\s+(?:original|exclusive)/i',
            '/only on disney\+/i',
            '/disneyplus\.com/i'
        ),
        'logo' => 'https://image.tmdb.org/t/p/original/7rwgEs15tFwyR9NPQ5vpzxTj19Q.jpg'
    ),
    '15' => array(
        'name' => 'Hulu',
        'patterns' => array(
            '/(?:available|streaming|watch|now).*?(?:on|@)\s*hulu/i',
            '/hulu\s+(?:original|exclusive)/i',
            '/only on hulu/i',
            '/hulu\.com/i'
        ),
        'logo' => 'https://image.tmdb.org/t/p/original/zxrVdFjIjLqkfnwyghnfywTn3Lh.jpg'
    ),
    '350' => array(
        'name' => 'Apple TV+',
        'patterns' => array(
            '/(?:available|streaming|watch|now).*?(?:on|@)\s*apple\s*tv\s*\+/i',
            '/apple\s*tv\s*\+\s+(?:original|exclusive)/i',
            '/only on apple tv\+/i',
            '/tv\.apple\.com/i'
        ),
        'logo' => 'https://image.tmdb.org/t/p/original/2E03IAZsX4ZaUqM7tXlctEPMGWS.jpg'
    ),
    '1899' => array(
        'name' => 'Max',
        'patterns' => array(
            '/(?:available|streaming|watch|now).*?(?:on|@)\s*(?:hbo\s*)?max/i',
            '/(?:hbo\s*)?max\s+(?:original|exclusive)/i',
            '/only on max/i',
            '/max\.com/i'
        ),
        'logo' => 'https://image.tmdb.org/t/p/original/Ajqyt5aNxNGjmF9uOfxArGrdf3X.jpg'
    ),
    '531' => array(
        'name' => 'Paramount+',
        'patterns' => array(
            '/(?:available|streaming|watch|now).*?(?:on|@)\s*paramount\s*\+/i',
            '/paramount\s*\+\s+(?:original|exclusive)/i',
            '/only on paramount\+/i',
            '/paramountplus\.com/i'
        ),
        'logo' => 'https://image.tmdb.org/t/p/original/xbhHHa1YgtpwhC8lb1NQ3ACVcLd.jpg'
    ),
    '230' => array(
        'name' => 'Crave',
        'patterns' => array(
            '/(?:available|streaming|watch|now).*?(?:on|@)\s*crave/i',
            '/crave\s+(?:original|exclusive)/i',
            '/only on crave/i',
            '/crave\.ca/i'
        ),
        'logo' => 'https://image.tmdb.org/t/p/original/pGhEL21HqPycD4gWV8DQ1fKD9HG.jpg'
    )
);

function getYouTubeVideoInfo($videoId, $apiKey) {
    $url = "https://www.googleapis.com/youtube/v3/videos?part=snippet&id=$videoId&key=$apiKey";

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($httpCode === 200 && $response) {
        $data = json_decode($response, true);
        if (isset($data['items'][0]['snippet'])) {
            return $data['items'][0]['snippet'];
        }
    }

    return null;
}

function extractProvidersFromDescription($description, $patterns) {
    if (empty($description)) {
        return array();
    }

    $foundProviders = array();

    foreach ($patterns as $providerId => $providerData) {
        foreach ($providerData['patterns'] as $pattern) {
            if (preg_match($pattern, $description)) {
                $foundProviders[] = array(
                    'id' => $providerId,
                    'name' => $providerData['name'],
                    'logo' => $providerData['logo']
                );
                break; // Only add each provider once
            }
        }
    }

    return $foundProviders;
}

function updateMovieProviders($pdo, $movieId, $providers) {
    foreach ($providers as $provider) {
        try {
            $priority = is_numeric($provider['id']) ? intval($provider['id']) : 99;

            $stmt = $pdo->prepare("
                INSERT INTO streaming_providers
                    (movie_id, provider_id, provider_name, provider_logo, display_priority, is_active)
                VALUES
                    (:movie_id, :provider_id, :provider_name, :provider_logo, :priority, 1)
                ON DUPLICATE KEY UPDATE
                    provider_name = VALUES(provider_name),
                    provider_logo = VALUES(provider_logo),
                    is_active = 1,
                    last_checked = NOW()
            ");

            $stmt->execute(array(
                ':movie_id' => $movieId,
                ':provider_id' => $provider['id'],
                ':provider_name' => $provider['name'],
                ':provider_logo' => $provider['logo'],
                ':priority' => $priority
            ));

        } catch (Exception $e) {
            echo "    Error: " . $e->getMessage() . "\n";
        }
    }
}

// Main execution
$limit = isset($_GET['limit']) ? intval($_GET['limit']) : 50;
$offset = isset($_GET['offset']) ? intval($_GET['offset']) : 0;

echo "YouTube Trailer Description Scraper\n";
echo "====================================\n\n";

$pdo = getDbConnection();

// Get movies with YouTube trailer IDs
$stmt = $pdo->prepare("
    SELECT m.id, m.title, t.youtube_id
    FROM movies m
    INNER JOIN trailers t ON m.id = t.movie_id
    WHERE t.youtube_id IS NOT NULL AND t.youtube_id != ''
    ORDER BY m.created_at DESC
    LIMIT :limit OFFSET :offset
");

$stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
$stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
$stmt->execute();
$movies = $stmt->fetchAll(PDO::FETCH_ASSOC);

echo "Processing " . count($movies) . " movies (offset $offset)...\n\n";

$processed = 0;
$found = 0;

foreach ($movies as $movie) {
    echo "[{$movie['id']}] {$movie['title']}\n";
    echo "  YouTube: {$movie['youtube_id']}\n";

    // Fetch video info
    $videoInfo = getYouTubeVideoInfo($movie['youtube_id'], YOUTUBE_API_KEY);

    if (!$videoInfo) {
        echo "  ⚠️  Failed to fetch video info\n\n";
        $processed++;
        usleep(100000); // Rate limiting
        continue;
    }

    $description = isset($videoInfo['description']) ? $videoInfo['description'] : '';
    $title = isset($videoInfo['title']) ? $videoInfo['title'] : '';

    // Combine title and description for better detection
    $combinedText = $title . "\n\n" . $description;

    if (empty($combinedText)) {
        echo "  ℹ️  No title/description\n\n";
        $processed++;
        usleep(100000);
        continue;
    }

    // Extract providers from combined text
    $providers = extractProvidersFromDescription($combinedText, $PROVIDER_PATTERNS);

    if (count($providers) > 0) {
        $providerNames = array();
        foreach ($providers as $p) {
            $providerNames[] = $p['name'];
        }
        echo "  ✅ Found: " . implode(', ', $providerNames) . "\n";

        // Update database
        updateMovieProviders($pdo, $movie['id'], $providers);
        $found++;
    } else {
        echo "  ℹ️  No providers mentioned\n";
    }

    echo "\n";
    $processed++;

    // Rate limiting
    usleep(500000); // 0.5 seconds
}

echo "====================================\n";
echo "SUMMARY: $found movies tagged (out of $processed processed)\n";
echo "Next batch: ?limit=$limit&offset=" . ($offset + $limit) . "\n";
