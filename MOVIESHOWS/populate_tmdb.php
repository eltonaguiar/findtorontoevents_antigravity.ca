<?php
/**
 * Database Population Script for TMDB Movies & TV Shows
 * Populates 100 movies + 100 TV shows per year from 2027 back to 2015
 * 
 * Usage: populate_tmdb.php?api_key=YOUR_TMDB_API_KEY&year=2027&type=movie&limit=100
 */

// Database configuration
$host = 'localhost';
$dbname = 'ejaguiar1_tvmoviestrailers';
$username = 'ejaguiar1_tvmoviestrailers';
$password = 'virus2016';

header('Content-Type: text/plain; charset=utf-8');

// Get parameters
$apiKey = isset($_GET['api_key']) ? $_GET['api_key'] : '';
$targetYear = isset($_GET['year']) ? (int) $_GET['year'] : 2027;
$targetType = isset($_GET['type']) ? $_GET['type'] : 'movie'; // 'movie' or 'tv'
$limit = isset($_GET['limit']) ? (int) $_GET['limit'] : 100;
$action = isset($_GET['action']) ? $_GET['action'] : 'inspect';

if ($action === 'populate' && empty($apiKey)) {
    die("Error: TMDB API key required. Usage: ?action=populate&api_key=YOUR_KEY&year=2027&type=movie&limit=100\n");
}

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    if ($action === 'inspect') {
        inspectDatabase($pdo);
    } elseif ($action === 'populate') {
        populateFromTMDB($pdo, $apiKey, $targetYear, $targetType, $limit);
    } elseif ($action === 'populate_all') {
        populateAllYears($pdo, $apiKey);
    } else {
        echo "Unknown action. Use: inspect, populate, or populate_all\n";
    }

} catch (PDOException $e) {
    die("Database Error: " . $e->getMessage() . "\n");
}

function fetchURL($url)
{
    // Try cURL first
    if (function_exists('curl_init')) {
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_TIMEOUT, 30);
        $response = curl_exec($ch);
        $error = curl_error($ch);
        curl_close($ch);

        if ($response === false) {
            echo "cURL Error: $error\n";
            return false;
        }
        return $response;
    }

    // Fallback to file_get_contents
    if (ini_get('allow_url_fopen')) {
        $response = @file_get_contents($url);
        if ($response === false) {
            echo "file_get_contents failed\n";
            return false;
        }
        return $response;
    }

    echo "Error: Neither cURL nor allow_url_fopen is available\n";
    return false;
}

function inspectDatabase($pdo)
{
    echo "=== DATABASE INSPECTION ===\n\n";

    // Get total count
    $stmt = $pdo->query("SELECT COUNT(*) as total FROM movies");
    $result = $stmt->fetch(PDO::FETCH_ASSOC);
    $total = $result['total'];
    echo "Total records: $total\n\n";

    // Get counts by year and type
    echo "Counts by year and type:\n";
    echo str_repeat("-", 50) . "\n";
    printf("%-6s %-10s %s\n", "Year", "Type", "Count");
    echo str_repeat("-", 50) . "\n";

    $stmt = $pdo->query("
        SELECT release_year, type, COUNT(*) as count 
        FROM movies 
        GROUP BY release_year, type 
        ORDER BY release_year DESC, type
    ");

    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        printf("%-6s %-10s %d\n", $row['release_year'], $row['type'], $row['count']);
    }

    echo "\n";

    // Sample data
    echo "Sample records (latest 5):\n";
    echo str_repeat("-", 80) . "\n";
    $stmt = $pdo->query("SELECT id, title, type, release_year FROM movies ORDER BY id DESC LIMIT 5");
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        echo "ID: {$row['id']}, {$row['title']} ({$row['type']}, {$row['release_year']})\n";
    }
}

function populateFromTMDB($pdo, $apiKey, $year, $type, $limit)
{
    echo "=== POPULATING FROM TMDB ===\n\n";
    echo "Year: $year\n";
    echo "Type: $type\n";
    echo "Target: $limit items\n\n";

    // Check existing count
    $stmt = $pdo->prepare("SELECT COUNT(*) as count FROM movies WHERE release_year = ? AND type = ?");
    $stmt->execute(array($year, $type));
    $result = $stmt->fetch(PDO::FETCH_ASSOC);
    $existing = $result['count'];
    echo "Existing: $existing items\n";

    if ($existing >= $limit) {
        echo "Already have $existing items (target: $limit). Skipping.\n";
        return;
    }

    $needed = $limit - $existing;
    echo "Need to fetch: $needed items\n\n";

    $inserted = 0;
    $page = 1;
    $maxPages = 50;

    $endpoint = $type === 'movie' ? 'discover/movie' : 'discover/tv';
    $yearParam = $type === 'movie' ? 'primary_release_year' : 'first_air_date_year';

    while ($inserted < $needed && $page <= $maxPages) {
        $url = "https://api.themoviedb.org/3/$endpoint?api_key=$apiKey&{$yearParam}=$year&page=$page&sort_by=popularity.desc";

        echo "Fetching page $page... ";
        flush();

        $response = fetchURL($url);
        if ($response === false) {
            echo "FAILED\n";
            break;
        }

        $data = json_decode($response, true);
        if (!isset($data['results']) || empty($data['results'])) {
            echo "No more results\n";
            break;
        }

        $pageInserted = 0;
        foreach ($data['results'] as $item) {
            if ($inserted >= $needed)
                break;

            $tmdbId = $item['id'];

            // Check if already exists
            $checkStmt = $pdo->prepare("SELECT id FROM movies WHERE tmdb_id = ? AND type = ?");
            $checkStmt->execute(array($tmdbId, $type));
            if ($checkStmt->fetch()) {
                continue; // Skip duplicates
            }

            $title = isset($item['title']) ? $item['title'] : $item['name'];
            $description = isset($item['overview']) ? $item['overview'] : null;
            $rating = isset($item['vote_average']) ? $item['vote_average'] : null;
            $genre = isset($item['genre_ids']) ? implode(',', $item['genre_ids']) : null;

            $insertStmt = $pdo->prepare("
                INSERT INTO movies (title, type, genre, description, release_year, imdb_rating, tmdb_id, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, NOW())
            ");

            $insertStmt->execute(array($title, $type, $genre, $description, $year, $rating, $tmdbId));
            $inserted++;
            $pageInserted++;
        }

        echo "inserted $pageInserted (total: $inserted/$needed)\n";
        $page++;

        // Rate limiting
        usleep(250000); // 250ms delay
    }

    echo "\n✓ Completed! Inserted $inserted new items\n";
}

function populateAllYears($pdo, $apiKey)
{
    echo "=== POPULATING ALL YEARS (2015-2027) ===\n\n";

    $targetPerYear = 100;
    $startYear = 2027;
    $endYear = 2015;

    for ($year = $startYear; $year >= $endYear; $year--) {
        echo "\n" . str_repeat("=", 60) . "\n";
        echo "YEAR: $year\n";
        echo str_repeat("=", 60) . "\n\n";

        // Movies
        echo "--- MOVIES ---\n";
        populateFromTMDB($pdo, $apiKey, $year, 'movie', $targetPerYear);

        echo "\n";

        // TV Shows
        echo "--- TV SHOWS ---\n";
        populateFromTMDB($pdo, $apiKey, $year, 'tv', $targetPerYear);

        echo "\n";
    }

    echo "\n" . str_repeat("=", 60) . "\n";
    echo "ALL YEARS COMPLETE!\n";
    echo str_repeat("=", 60) . "\n";
}

?>