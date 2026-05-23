<?php
/**
 * foursquare_proxy.php — Server-side Foursquare Places API proxy.
 * PHP 5.2 compatible. No closures, no ?:, no ??, no short arrays.
 *
 * Endpoints:
 *   GET ?action=search&ll=43.65,-79.38&query=vegan+restaurant&limit=10
 *   GET ?action=search&near=Yonge+and+Dundas,Toronto&query=late+night+food
 *   GET ?action=details&venue_id=XXXXX
 *   GET ?action=search&ll=43.65,-79.38&query=pizza&openNow=1
 *   GET ?action=search&near=M5B+2H1&query=halal
 *
 * Returns JSON from Foursquare API v2.
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Credentials: true');
header('Cache-Control: public, max-age=300');

// ── Read Foursquare credentials from .env ──
function _fs_read_env($key) {
    $envFile = dirname(__FILE__) . '/.env';
    if (!file_exists($envFile) || !is_readable($envFile)) return '';
    $raw = file_get_contents($envFile);
    $lines = preg_split('/\r?\n/', $raw);
    foreach ($lines as $line) {
        $line = trim($line);
        if ($line === '' || $line[0] === '#') continue;
        if (strpos($line, '=') === false) continue;
        $eq = strpos($line, '=');
        $k = trim(substr($line, 0, $eq));
        if ($k !== $key) continue;
        $val = trim(substr($line, $eq + 1));
        $len = strlen($val);
        if ($len >= 2 && $val[0] === '"' && $val[$len - 1] === '"') {
            return substr($val, 1, -1);
        }
        if ($len >= 2 && $val[0] === "'" && $val[$len - 1] === "'") {
            return substr($val, 1, -1);
        }
        return $val;
    }
    return '';
}

$client_id     = _fs_read_env('FOURSQUARE_CLIENT_ID');
$client_secret = _fs_read_env('FOURSQUARE_CLIENT_SECRET');

if ($client_id === '' || $client_secret === '') {
    header('HTTP/1.1 500 Internal Server Error');
    echo json_encode(array('ok' => false, 'error' => 'Foursquare credentials not configured'));
    exit;
}

$action = isset($_GET['action']) ? trim($_GET['action']) : '';

if ($action === '') {
    header('HTTP/1.1 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Missing action parameter (search or details)'));
    exit;
}

$v = '20231010'; // Foursquare API version date

// ── SEARCH ──
if ($action === 'search') {
    $query = isset($_GET['query']) ? trim($_GET['query']) : '';
    $ll    = isset($_GET['ll'])    ? trim($_GET['ll'])    : '';
    $near  = isset($_GET['near'])  ? trim($_GET['near'])  : '';
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 10;
    $openNow   = isset($_GET['openNow']) ? trim($_GET['openNow']) : '';
    $radius    = isset($_GET['radius'])  ? intval($_GET['radius']) : 0;
    $categoryId = isset($_GET['categoryId']) ? trim($_GET['categoryId']) : '';
    $sortByDistance = isset($_GET['sortByDistance']) ? trim($_GET['sortByDistance']) : '';

    if ($ll === '' && $near === '') {
        // Default to downtown Toronto
        $ll = '43.6532,-79.3832';
    }
    if ($limit < 1) $limit = 10;
    if ($limit > 50) $limit = 50;

    $params = array(
        'client_id'     => $client_id,
        'client_secret' => $client_secret,
        'v'             => $v,
        'limit'         => $limit,
    );
    if ($query !== '') $params['query'] = $query;
    if ($ll !== '')    $params['ll'] = $ll;
    if ($near !== '')  $params['near'] = $near;
    if ($openNow === '1' || $openNow === 'true') $params['openNow'] = '1';
    if ($radius > 0)  $params['radius'] = $radius;
    if ($categoryId !== '') $params['categoryId'] = $categoryId;
    if ($sortByDistance === '1' || $sortByDistance === 'true') $params['sortByDistance'] = '1';

    $url = 'https://api.foursquare.com/v2/venues/search?' . http_build_query($params);
    $result = _fs_fetch($url);

    if ($result === false) {
        header('HTTP/1.1 502 Bad Gateway');
        echo json_encode(array('ok' => false, 'error' => 'Failed to reach Foursquare API'));
        exit;
    }

    $data = json_decode($result, true);
    if (!$data || !isset($data['response'])) {
        header('HTTP/1.1 502 Bad Gateway');
        echo json_encode(array('ok' => false, 'error' => 'Invalid Foursquare response'));
        exit;
    }

    // Simplify the response for the frontend
    $venues = array();
    if (isset($data['response']['venues'])) {
        $raw_venues = $data['response']['venues'];
        for ($i = 0; $i < count($raw_venues); $i++) {
            $rv = $raw_venues[$i];
            $loc = isset($rv['location']) ? $rv['location'] : array();
            $cats = isset($rv['categories']) ? $rv['categories'] : array();
            $catNames = array();
            for ($j = 0; $j < count($cats); $j++) {
                $catNames[] = $cats[$j]['name'];
            }
            $venue = array(
                'id'        => $rv['id'],
                'name'      => $rv['name'],
                'address'   => isset($loc['formattedAddress']) ? implode(', ', $loc['formattedAddress']) : '',
                'lat'       => isset($loc['lat']) ? $loc['lat'] : null,
                'lng'       => isset($loc['lng']) ? $loc['lng'] : null,
                'distance'  => isset($loc['distance']) ? $loc['distance'] : null,
                'city'      => isset($loc['city']) ? $loc['city'] : '',
                'categories' => $catNames,
            );
            $venues[] = $venue;
        }
    }

    echo json_encode(array('ok' => true, 'venues' => $venues, 'count' => count($venues)));
    exit;
}

// ── DETAILS ──
if ($action === 'details') {
    $venue_id = isset($_GET['venue_id']) ? trim($_GET['venue_id']) : '';
    if ($venue_id === '') {
        header('HTTP/1.1 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'Missing venue_id'));
        exit;
    }

    $params = array(
        'client_id'     => $client_id,
        'client_secret' => $client_secret,
        'v'             => $v,
    );
    $url = 'https://api.foursquare.com/v2/venues/' . urlencode($venue_id) . '?' . http_build_query($params);
    $result = _fs_fetch($url);

    if ($result === false) {
        header('HTTP/1.1 502 Bad Gateway');
        echo json_encode(array('ok' => false, 'error' => 'Failed to reach Foursquare API'));
        exit;
    }

    $data = json_decode($result, true);
    if (!$data || !isset($data['response']['venue'])) {
        header('HTTP/1.1 502 Bad Gateway');
        echo json_encode(array('ok' => false, 'error' => 'Invalid Foursquare venue response'));
        exit;
    }

    $rv = $data['response']['venue'];
    $loc = isset($rv['location']) ? $rv['location'] : array();
    $cats = isset($rv['categories']) ? $rv['categories'] : array();
    $catNames = array();
    for ($j = 0; $j < count($cats); $j++) {
        $catNames[] = $cats[$j]['name'];
    }

    $hours_status = '';
    $is_open = null;
    if (isset($rv['hours'])) {
        if (isset($rv['hours']['status'])) $hours_status = $rv['hours']['status'];
        if (isset($rv['hours']['isOpen'])) $is_open = $rv['hours']['isOpen'];
    }
    if (isset($rv['popular']) && isset($rv['popular']['status'])) {
        $hours_status = $rv['popular']['status'];
    }

    $rating = isset($rv['rating']) ? $rv['rating'] : null;
    $price_tier = null;
    if (isset($rv['price']) && isset($rv['price']['tier'])) {
        $price_tier = $rv['price']['tier'];
    }
    $price_msg = '';
    if (isset($rv['price']) && isset($rv['price']['message'])) {
        $price_msg = $rv['price']['message'];
    }

    $url_venue = isset($rv['url']) ? $rv['url'] : '';
    $phone = '';
    if (isset($rv['contact']) && isset($rv['contact']['formattedPhone'])) {
        $phone = $rv['contact']['formattedPhone'];
    }

    $venue = array(
        'id'          => $rv['id'],
        'name'        => $rv['name'],
        'address'     => isset($loc['formattedAddress']) ? implode(', ', $loc['formattedAddress']) : '',
        'lat'         => isset($loc['lat']) ? $loc['lat'] : null,
        'lng'         => isset($loc['lng']) ? $loc['lng'] : null,
        'city'        => isset($loc['city']) ? $loc['city'] : '',
        'categories'  => $catNames,
        'rating'      => $rating,
        'price_tier'  => $price_tier,
        'price_msg'   => $price_msg,
        'hours_status' => $hours_status,
        'is_open'     => $is_open,
        'url'         => $url_venue,
        'phone'       => $phone,
    );

    echo json_encode(array('ok' => true, 'venue' => $venue));
    exit;
}

// ── EXPLORE (trending/recommended) ──
if ($action === 'explore') {
    $query = isset($_GET['query']) ? trim($_GET['query']) : '';
    $ll    = isset($_GET['ll'])    ? trim($_GET['ll'])    : '';
    $near  = isset($_GET['near'])  ? trim($_GET['near'])  : '';
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 10;
    $openNow   = isset($_GET['openNow']) ? trim($_GET['openNow']) : '';
    $section   = isset($_GET['section']) ? trim($_GET['section']) : ''; // food, drinks, coffee, shops, arts, outdoors, sights, trending, topPicks

    if ($ll === '' && $near === '') {
        $ll = '43.6532,-79.3832';
    }
    if ($limit < 1) $limit = 10;
    if ($limit > 50) $limit = 50;

    $params = array(
        'client_id'     => $client_id,
        'client_secret' => $client_secret,
        'v'             => $v,
        'limit'         => $limit,
    );
    if ($query !== '') $params['query'] = $query;
    if ($ll !== '')    $params['ll'] = $ll;
    if ($near !== '')  $params['near'] = $near;
    if ($openNow === '1' || $openNow === 'true') $params['openNow'] = '1';
    if ($section !== '') $params['section'] = $section;

    $url = 'https://api.foursquare.com/v2/venues/explore?' . http_build_query($params);
    $result = _fs_fetch($url);

    if ($result === false) {
        header('HTTP/1.1 502 Bad Gateway');
        echo json_encode(array('ok' => false, 'error' => 'Failed to reach Foursquare API'));
        exit;
    }

    $data = json_decode($result, true);
    if (!$data || !isset($data['response'])) {
        header('HTTP/1.1 502 Bad Gateway');
        echo json_encode(array('ok' => false, 'error' => 'Invalid Foursquare response'));
        exit;
    }

    $venues = array();
    if (isset($data['response']['groups'])) {
        $groups = $data['response']['groups'];
        for ($g = 0; $g < count($groups); $g++) {
            $items = isset($groups[$g]['items']) ? $groups[$g]['items'] : array();
            for ($i = 0; $i < count($items); $i++) {
                $rv = $items[$i]['venue'];
                $loc = isset($rv['location']) ? $rv['location'] : array();
                $cats = isset($rv['categories']) ? $rv['categories'] : array();
                $catNames = array();
                for ($j = 0; $j < count($cats); $j++) {
                    $catNames[] = $cats[$j]['name'];
                }
                $rating = isset($rv['rating']) ? $rv['rating'] : null;
                $price_tier = null;
                if (isset($rv['price']) && isset($rv['price']['tier'])) {
                    $price_tier = $rv['price']['tier'];
                }
                $venue = array(
                    'id'         => $rv['id'],
                    'name'       => $rv['name'],
                    'address'    => isset($loc['formattedAddress']) ? implode(', ', $loc['formattedAddress']) : '',
                    'lat'        => isset($loc['lat']) ? $loc['lat'] : null,
                    'lng'        => isset($loc['lng']) ? $loc['lng'] : null,
                    'distance'   => isset($loc['distance']) ? $loc['distance'] : null,
                    'city'       => isset($loc['city']) ? $loc['city'] : '',
                    'categories' => $catNames,
                    'rating'     => $rating,
                    'price_tier' => $price_tier,
                );
                $venues[] = $venue;
            }
        }
    }

    echo json_encode(array('ok' => true, 'venues' => $venues, 'count' => count($venues)));
    exit;
}

header('HTTP/1.1 400 Bad Request');
echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action . '. Use search, details, or explore.'));
exit;

// ── HTTP fetch helper (cURL with file_get_contents fallback) ──
function _fs_fetch($url) {
    $body = false;
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        if ($ch) {
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, 15);
            curl_setopt($ch, CURLOPT_USERAGENT, 'FindTorontoEvents/1.0');
            $body = curl_exec($ch);
            curl_close($ch);
        }
    }
    if ($body === false && ini_get('allow_url_fopen')) {
        $opts = array(
            'http' => array(
                'method'  => 'GET',
                'header'  => "User-Agent: FindTorontoEvents/1.0\r\n",
                'timeout' => 15,
            )
        );
        $ctx = stream_context_create($opts);
        $body = @file_get_contents($url, false, $ctx);
    }
    return $body;
}
