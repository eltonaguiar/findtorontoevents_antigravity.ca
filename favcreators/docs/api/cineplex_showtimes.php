<?php
/**
 * Cineplex Showtimes API Proxy
 * Fetches real showtime data from Cineplex's theatrical API.
 * Returns simplified, time-sorted showtimes for a given theater.
 *
 * PHP 5.2 compatible — no closures, no short array syntax.
 *
 * Parameters:
 *   theatreId (int)            - Cineplex theater ID (e.g., 7130)
 *   theatre   (string)         - Theater name to fuzzy-match (alternative to theatreId)
 *   date      (string, optional) - YYYY-MM-DD (default: today)
 *   action    (string, optional) - "theatres" to list known theaters
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.1 200 OK');
    exit;
}

// ============================================================
// CONFIGURATION
// ============================================================

$CINEPLEX_API = 'https://apis.cineplex.com/prod/cpx/theatrical/api';
$CINEPLEX_KEY = 'dcdac5601d864addbc2675a2e96cb1f8';

// Cache TTL: 5 minutes (prioritize accuracy for showtimes)
$CACHE_TTL = 300;

// Known Toronto-area Cineplex theater IDs
// These are used to validate the theatreId parameter
$KNOWN_THEATERS = array(
    7130 => 'Cineplex Cinemas Yonge-Dundas and VIP',
    7131 => 'Scotiabank Theatre Toronto',
    7101 => 'Cineplex Cinemas Varsity and VIP',
    7129 => 'Cineplex Cinemas Empress Walk',
    7156 => 'Cineplex Odeon Eglinton Town Centre',
    7140 => 'Cineplex Cinemas Queensway and VIP',
    7170 => 'Cineplex Odeon Morningside Cinemas',
    7136 => 'SilverCity Fairview Mall Cinemas',
    7151 => 'SilverCity Yorkdale Cinemas',
    7120 => 'Carlton Cinemas'
);

// ============================================================
// READ PARAMETERS
// ============================================================

$action = isset($_GET['action']) ? trim($_GET['action']) : '';

// Action: list known theaters
if ($action === 'theatres') {
    $list = array();
    foreach ($KNOWN_THEATERS as $id => $name) {
        $list[] = array('theatreId' => $id, 'name' => $name);
    }
    echo json_encode(array('ok' => true, 'theatres' => $list));
    exit;
}

$theatreId = isset($_GET['theatreId']) ? (int)$_GET['theatreId'] : 0;
$theatreName = isset($_GET['theatre']) ? trim($_GET['theatre']) : '';
$date = isset($_GET['date']) ? trim($_GET['date']) : date('Y-m-d');

// If theatre name given but no ID, try to match
if ($theatreId <= 0 && $theatreName !== '') {
    $theatreId = _cineplex_match_theatre($theatreName, $KNOWN_THEATERS);
}

// Validate theatreId
if ($theatreId <= 0) {
    echo json_encode(array(
        'ok' => false,
        'error' => 'theatreId or theatre name is required.',
        'known_theatres' => array_values($KNOWN_THEATERS)
    ));
    exit;
}

// Validate date format
if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $date)) {
    $date = date('Y-m-d');
}

// ============================================================
// CHECK CACHE
// ============================================================

$cache_file = sys_get_temp_dir() . '/fte_cineplex_' . $theatreId . '_' . $date . '.json';
$cache_age_minutes = 0;

if (file_exists($cache_file)) {
    $cache_time = filemtime($cache_file);
    $age = time() - $cache_time;
    $cache_age_minutes = (int)round($age / 60);

    if ($age < $CACHE_TTL) {
        $cached = @file_get_contents($cache_file);
        if ($cached !== false) {
            $cached_data = json_decode($cached, true);
            if (is_array($cached_data) && isset($cached_data['ok']) && $cached_data['ok']) {
                // Recalculate is_past/just_started with current time
                $cached_data = _cineplex_refresh_past_flags($cached_data);
                $cached_data['cached'] = true;
                $cached_data['cache_age_minutes'] = $cache_age_minutes;
                echo json_encode($cached_data);
                exit;
            }
        }
    }
}

// ============================================================
// FETCH FROM CINEPLEX API
// ============================================================

$url = $CINEPLEX_API . '/v1/showtimes?LocationId=' . $theatreId
    . '&Date=' . urlencode($date) . '&language=en';

$response = _cineplex_http_get($url, $CINEPLEX_KEY);

if ($response === false) {
    echo json_encode(array(
        'ok' => false,
        'error' => 'Could not fetch showtimes from Cineplex.'
    ));
    exit;
}

$data = json_decode($response, true);
if (!is_array($data) || count($data) === 0) {
    echo json_encode(array(
        'ok' => false,
        'error' => 'No showtime data returned.',
        'theatreId' => $theatreId
    ));
    exit;
}

// ============================================================
// FORMAT RESULTS
// ============================================================

$theatreName = '';
$showtimes = array();

// The API returns an array of theatre objects
$theatre = $data[0];
$theatreName = isset($theatre['theatre']) ? $theatre['theatre'] : '';
$theatreIdReturned = isset($theatre['theatreId']) ? (int)$theatre['theatreId'] : $theatreId;
// Build Cineplex URL from theatre name
// Cineplex slugs: lowercase, spaces→hyphens, strip existing hyphens from names first
// e.g. "Cineplex Cinemas Yonge-Dundas and VIP" → "cineplex-cinemas-yongedundas-and-vip"
$cineplexUrl = 'https://www.cineplex.com/Showtimes';
if ($theatreName !== '') {
    $slug = strtolower($theatreName);
    $slug = str_replace('-', '', $slug);
    $slug = preg_replace('/[^a-z0-9\s]/', '', $slug);
    $slug = preg_replace('/\s+/', '-', trim($slug));
    $slug = preg_replace('/-+/', '-', $slug);
    $cineplexUrl = 'https://www.cineplex.com/theatre/' . $slug;
}

$dates = isset($theatre['dates']) ? $theatre['dates'] : array();
foreach ($dates as $dateBlock) {
    $movies = isset($dateBlock['movies']) ? $dateBlock['movies'] : array();
    foreach ($movies as $movie) {
        $movieName = isset($movie['name']) ? $movie['name'] : '';
        if ($movieName === '') continue;

        $movieId = isset($movie['id']) ? (int)$movie['id'] : 0;
        $runtime = isset($movie['runtimeInMinutes']) ? (int)$movie['runtimeInMinutes'] : 0;
        $posterUrl = isset($movie['smallPosterImageUrl']) ? $movie['smallPosterImageUrl'] : '';
        $filmUrl = isset($movie['filmUrl']) ? $movie['filmUrl'] : '';
        $isEvent = isset($movie['isEvent']) ? $movie['isEvent'] : false;

        $sessions = array();
        $experiences = isset($movie['experiences']) ? $movie['experiences'] : array();
        foreach ($experiences as $exp) {
            $expTypes = isset($exp['experienceTypes']) ? $exp['experienceTypes'] : array('Regular');
            $expLabel = implode(', ', $expTypes);
            $expSessions = isset($exp['sessions']) ? $exp['sessions'] : array();
            foreach ($expSessions as $sess) {
                $startTime = isset($sess['showStartDateTime']) ? $sess['showStartDateTime'] : '';
                if ($startTime === '') continue;

                $seatsLeft = isset($sess['seatsRemaining']) ? (int)$sess['seatsRemaining'] : 0;
                $isSoldOut = isset($sess['isSoldOut']) ? $sess['isSoldOut'] : false;
                $ticketUrl = isset($sess['ticketingUrl']) ? $sess['ticketingUrl'] : '';
                $auditorium = isset($sess['auditorium']) ? $sess['auditorium'] : '';

                // Format time for display (e.g., "9:45 PM")
                $ts = strtotime($startTime);
                $timeDisplay = date('g:i A', $ts);
                $timeSort = date('H:i', $ts);

                // 20-minute grace: show recently-started sessions as "just started"
                $nowTs = time();
                $minutesAgo = ($nowTs - $ts) / 60;
                $isPast = ($ts < $nowTs && $minutesAgo > 20);
                $justStarted = ($ts < $nowTs && $minutesAgo <= 20 && $minutesAgo > 0);

                $sessions[] = array(
                    'time' => $timeDisplay,
                    'time_sort' => $timeSort,
                    'time_raw' => $startTime,
                    'experience' => $expLabel,
                    'seats_remaining' => $seatsLeft,
                    'is_sold_out' => $isSoldOut,
                    'is_past' => $isPast,
                    'just_started' => $justStarted,
                    'minutes_ago' => ($minutesAgo > 0 && $minutesAgo <= 20) ? (int)round($minutesAgo) : 0,
                    'ticket_url' => $ticketUrl,
                    'auditorium' => $auditorium
                );
            }
        }

        // Sort sessions by time
        usort($sessions, '_cineplex_sort_by_time');

        if (count($sessions) > 0) {
            $showtimes[] = array(
                'movie' => $movieName,
                'movie_id' => $movieId,
                'runtime' => $runtime,
                'poster_url' => $posterUrl,
                'film_url' => $filmUrl,
                'is_event' => $isEvent,
                'sessions' => $sessions
            );
        }
    }
}

// Sort movies by earliest showtime
usort($showtimes, '_cineplex_sort_by_earliest');

$result = array(
    'ok' => true,
    'theatre' => $theatreName,
    'theatreId' => $theatreIdReturned,
    'cineplex_url' => $cineplexUrl,
    'date' => $date,
    'showtimes' => $showtimes,
    'total_movies' => count($showtimes),
    'cached' => false,
    'cache_age_minutes' => 0
);

// Write cache
@file_put_contents($cache_file, json_encode($result));

echo json_encode($result);
exit;


// ============================================================
// INTERNAL FUNCTIONS
// ============================================================

function _cineplex_refresh_past_flags($data) {
    if (!isset($data['showtimes'])) return $data;
    // Regenerate cineplex_url if missing (old cache)
    if (!isset($data['cineplex_url']) || $data['cineplex_url'] === '' || $data['cineplex_url'] === 'https://www.cineplex.com/Showtimes') {
        $tn = isset($data['theatre']) ? $data['theatre'] : '';
        if ($tn !== '') {
            $s = strtolower($tn);
            $s = str_replace('-', '', $s);
            $s = preg_replace('/[^a-z0-9\s]/', '', $s);
            $s = preg_replace('/\s+/', '-', trim($s));
            $s = preg_replace('/-+/', '-', $s);
            $data['cineplex_url'] = 'https://www.cineplex.com/theatre/' . $s;
        }
    }
    $nowTs = time();
    for ($i = 0; $i < count($data['showtimes']); $i++) {
        if (!isset($data['showtimes'][$i]['sessions'])) continue;
        for ($j = 0; $j < count($data['showtimes'][$i]['sessions']); $j++) {
            $raw = $data['showtimes'][$i]['sessions'][$j]['time_raw'];
            $ts = strtotime($raw);
            $minutesAgo = ($nowTs - $ts) / 60;
            $data['showtimes'][$i]['sessions'][$j]['is_past'] = ($ts < $nowTs && $minutesAgo > 20);
            $data['showtimes'][$i]['sessions'][$j]['just_started'] = ($ts < $nowTs && $minutesAgo <= 20 && $minutesAgo > 0);
            $data['showtimes'][$i]['sessions'][$j]['minutes_ago'] = ($minutesAgo > 0 && $minutesAgo <= 20) ? (int)round($minutesAgo) : 0;
        }
    }
    return $data;
}

function _cineplex_sort_by_time($a, $b) {
    return strcmp($a['time_sort'], $b['time_sort']);
}

function _cineplex_sort_by_earliest($a, $b) {
    $aTime = isset($a['sessions'][0]) ? $a['sessions'][0]['time_sort'] : '99:99';
    $bTime = isset($b['sessions'][0]) ? $b['sessions'][0]['time_sort'] : '99:99';
    return strcmp($aTime, $bTime);
}

function _cineplex_match_theatre($query, $knownTheaters) {
    $query = strtolower(trim($query));
    // Remove common prefixes
    $query = preg_replace('/^cineplex\s*(cinemas?\s*)?/i', '', $query);
    $query = preg_replace('/^scotiabank\s*(theatre\s*)?/i', 'scotiabank ', $query);
    $query = trim($query);

    $bestId = 0;
    $bestScore = 0;

    foreach ($knownTheaters as $id => $name) {
        $nameLower = strtolower($name);
        // Exact match
        if ($nameLower === strtolower(trim($_GET['theatre']))) {
            return $id;
        }
        // Contains match
        if (strpos($nameLower, $query) !== false) {
            $score = strlen($query);
            if ($score > $bestScore) {
                $bestScore = $score;
                $bestId = $id;
            }
        }
        // Reverse: query contains key words from name
        $words = explode(' ', $query);
        $matchCount = 0;
        foreach ($words as $w) {
            if (strlen($w) > 2 && strpos($nameLower, $w) !== false) {
                $matchCount++;
            }
        }
        if ($matchCount > $bestScore) {
            $bestScore = $matchCount;
            $bestId = $id;
        }
    }
    return $bestId;
}

function _cineplex_http_get($url, $apiKey) {
    // Try curl first
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array(
            'Ocp-Apim-Subscription-Key: ' . $apiKey,
            'User-Agent: FindTorontoEvents/1.0'
        ));
        $response = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($response !== false && $code >= 200 && $code < 300) {
            return $response;
        }
    }

    // Fallback to file_get_contents
    $context = stream_context_create(array(
        'http' => array(
            'method' => 'GET',
            'timeout' => 10,
            'header' => "Ocp-Apim-Subscription-Key: " . $apiKey . "\r\n"
                . "User-Agent: FindTorontoEvents/1.0\r\n"
        )
    ));

    $response = @file_get_contents($url, false, $context);
    return ($response !== false) ? $response : false;
}
