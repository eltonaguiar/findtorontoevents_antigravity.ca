<?php
/**
 * Business Verification API
 * Cross-references Foursquare v3 and OpenStreetMap to determine if a business is open or closed.
 *
 * PHP 5.2 compatible — no closures, no short array syntax, no ?: or ??
 *
 * Parameters:
 *   name    (string, required) - Business name (e.g. "241 Pizza")
 *   address (string, optional) - Street address (e.g. "327 Queen St W")
 *   lat     (float, optional)  - Latitude (skip geocoding if provided)
 *   lng     (float, optional)  - Longitude
 *   city    (string, optional) - Default: "Toronto"
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.1 200 OK');
    exit;
}

// Load config (for Foursquare API key)
require_once dirname(__FILE__) . '/config.php';

// ============================================================
// READ PARAMETERS
// ============================================================

$name = isset($_GET['name']) ? trim($_GET['name']) : '';
if ($name === '') {
    echo json_encode(array('ok' => false, 'error' => 'Missing required parameter: name'));
    exit;
}

$address = isset($_GET['address']) ? trim($_GET['address']) : '';
$lat = isset($_GET['lat']) ? (float)$_GET['lat'] : 0;
$lng = isset($_GET['lng']) ? (float)$_GET['lng'] : 0;
$city = isset($_GET['city']) ? trim($_GET['city']) : 'Toronto';

// ============================================================
// CACHING — 24-hour file cache
// ============================================================

$cache_key = md5(strtolower($name) . '|' . strtolower($address) . '|' . strtolower($city));
$cache_file = sys_get_temp_dir() . '/verify_biz_' . $cache_key . '.json';
$cache_ttl = 86400; // 24 hours

if (file_exists($cache_file) && (time() - filemtime($cache_file)) < $cache_ttl) {
    $cached = @file_get_contents($cache_file);
    if ($cached !== false) {
        echo $cached;
        exit;
    }
}

// ============================================================
// GEOCODING — Get coordinates if not provided
// ============================================================

if ($lat == 0 && $lng == 0 && $address !== '') {
    $geo = _vb_geocode($address, $city);
    if ($geo !== null) {
        $lat = $geo['lat'];
        $lng = $geo['lng'];
    }
}

// If still no coords, try geocoding just the city
if ($lat == 0 && $lng == 0) {
    $geo = _vb_geocode($city, '');
    if ($geo !== null) {
        $lat = $geo['lat'];
        $lng = $geo['lng'];
    }
}

// ============================================================
// SOURCE 1: FOURSQUARE v2 (venue search/confirmation)
// ============================================================

$fsq_source = _vb_check_foursquare($name, $address, $city, $lat, $lng);

// ============================================================
// SOURCE 2: OVERPASS / OpenStreetMap
// ============================================================

$osm_source = null;
if ($lat != 0 && $lng != 0) {
    $osm_source = _vb_check_overpass($name, $lat, $lng);
}

// ============================================================
// SOURCE 3: GOOGLE PLACES (if API key configured)
// ============================================================

$google_source = null;
$google_api_key = defined('GOOGLE_PLACES_API_KEY') ? GOOGLE_PLACES_API_KEY : '';
if ($google_api_key !== '' && $lat != 0 && $lng != 0) {
    $google_source = _vb_check_google_places($name, $address, $city, $lat, $lng, $google_api_key);
}

// ============================================================
// CROSS-REFERENCE & VERDICT
// ============================================================

$sources = array();
if ($fsq_source !== null) $sources[] = $fsq_source;
if ($osm_source !== null) $sources[] = $osm_source;
if ($google_source !== null) $sources[] = $google_source;

$verdict_info = _vb_compute_verdict($fsq_source, $osm_source, $google_source);

$result = array(
    'ok' => true,
    'business_name' => $name,
    'query_address' => $address,
    'query_city' => $city,
    'coordinates' => array('lat' => $lat, 'lng' => $lng),
    'verdict' => $verdict_info['verdict'],
    'confidence' => $verdict_info['confidence'],
    'sources' => $sources,
    'summary' => $verdict_info['summary']
);

$json_output = json_encode($result);

// Cache the result
@file_put_contents($cache_file, $json_output);

echo $json_output;
exit;


// ============================================================
// HELPER FUNCTIONS
// ============================================================

function _vb_geocode($query, $city) {
    if ($query === '') return null;

    $search = $query;
    if ($city !== '' && stripos($query, $city) === false) {
        $search = $query . ', ' . $city;
    }

    // Try exact query first
    $result = _vb_nominatim_fetch($search);

    // Check if result is in GTA area
    $is_local = false;
    if ($result !== null) {
        if ($result['lat'] >= 43.4 && $result['lat'] <= 44.0 && $result['lng'] >= -80.0 && $result['lng'] <= -79.0) {
            $is_local = true;
        }
    }

    // If not local, try with Toronto suffix
    if ($result === null || !$is_local) {
        $toronto_result = _vb_nominatim_fetch($query . ', Toronto, ON, Canada');
        if ($toronto_result !== null) return $toronto_result;
    }

    return $result;
}

function _vb_nominatim_fetch($query) {
    $url = 'https://nominatim.openstreetmap.org/search?format=json&limit=1&q=' . urlencode($query);

    $context = stream_context_create(array(
        'http' => array(
            'method' => 'GET',
            'timeout' => 5,
            'header' => "User-Agent: FindTorontoEvents-VerifyBiz/1.0\r\n"
        )
    ));

    $response = @file_get_contents($url, false, $context);
    if ($response === false) return null;

    $data = json_decode($response, true);
    if (!is_array($data) || count($data) === 0) return null;

    $first = $data[0];
    if (!isset($first['lat']) || !isset($first['lon'])) return null;

    return array('lat' => (float)$first['lat'], 'lng' => (float)$first['lon']);
}

// ============================================================
// FOURSQUARE v2 CHECK (venue search + confirmation)
// ============================================================

function _vb_get_fsq_credentials() {
    $envFile = dirname(__FILE__) . '/.env';
    $cid = '';
    $csec = '';
    if (file_exists($envFile) && is_readable($envFile)) {
        $raw = file_get_contents($envFile);
        $lines = preg_split('/\r?\n/', $raw);
        foreach ($lines as $line) {
            $line = trim($line);
            if ($line === '' || $line[0] === '#') continue;
            if (strpos($line, '=') === false) continue;
            $eq = strpos($line, '=');
            $k = trim(substr($line, 0, $eq));
            $val = trim(substr($line, $eq + 1));
            $len = strlen($val);
            if ($len >= 2 && $val[0] === '"' && $val[$len - 1] === '"') {
                $val = substr($val, 1, -1);
            } elseif ($len >= 2 && $val[0] === "'" && $val[$len - 1] === "'") {
                $val = substr($val, 1, -1);
            }
            if ($k === 'FOURSQUARE_CLIENT_ID') $cid = $val;
            if ($k === 'FOURSQUARE_CLIENT_SECRET') $csec = $val;
        }
    }
    if ($cid !== '' && $csec !== '') {
        return array('client_id' => $cid, 'client_secret' => $csec);
    }
    return null;
}

function _vb_check_foursquare($name, $address, $city, $lat, $lng) {
    $creds = _vb_get_fsq_credentials();
    if ($creds === null) {
        return array(
            'provider' => 'foursquare',
            'status' => 'unavailable',
            'note' => 'No Foursquare credentials configured'
        );
    }

    // Need coordinates for v2 search
    if ($lat == 0 && $lng == 0) {
        return array(
            'provider' => 'foursquare',
            'status' => 'error',
            'note' => 'No coordinates available for search'
        );
    }

    $params = array(
        'client_id' => $creds['client_id'],
        'client_secret' => $creds['client_secret'],
        'v' => '20250101',
        'query' => $name,
        'll' => $lat . ',' . $lng,
        'radius' => '500',
        'limit' => '5',
        'intent' => 'browse'
    );

    $qs = '';
    foreach ($params as $k => $v) {
        if ($qs !== '') $qs .= '&';
        $qs .= urlencode($k) . '=' . urlencode($v);
    }

    $url = 'https://api.foursquare.com/v2/venues/search?' . $qs;
    $response = _vb_http_get($url, array());

    if ($response === false) {
        return array(
            'provider' => 'foursquare',
            'status' => 'error',
            'note' => 'API request failed'
        );
    }

    $data = json_decode($response, true);
    if (!is_array($data) || !isset($data['response']) || !isset($data['response']['venues'])) {
        return array(
            'provider' => 'foursquare',
            'status' => 'error',
            'note' => 'Unexpected response format'
        );
    }

    if (count($data['response']['venues']) === 0) {
        return array(
            'provider' => 'foursquare',
            'status' => 'not_found',
            'note' => 'No matching business found'
        );
    }

    // Find best match by name similarity
    $best_match = null;
    $best_score = 0;
    $name_norm = _vb_normalize_name($name);

    foreach ($data['response']['venues'] as $venue) {
        $venue_name = isset($venue['name']) ? $venue['name'] : '';
        $score = _vb_name_match_score($name_norm, _vb_normalize_name($venue_name));
        if ($score > $best_score) {
            $best_score = $score;
            $best_match = $venue;
        }
    }

    if ($best_match === null || $best_score < 0.4) {
        return array(
            'provider' => 'foursquare',
            'status' => 'not_found',
            'note' => 'No close name match found (best score: ' . round($best_score, 2) . ')'
        );
    }

    $match_name = isset($best_match['name']) ? $best_match['name'] : '';
    $match_id = isset($best_match['id']) ? $best_match['id'] : '';
    $category = '';
    if (isset($best_match['categories']) && is_array($best_match['categories']) && count($best_match['categories']) > 0) {
        $category = isset($best_match['categories'][0]['name']) ? $best_match['categories'][0]['name'] : '';
    }

    // Build address
    $match_address = '';
    if (isset($best_match['location'])) {
        $loc = $best_match['location'];
        if (isset($loc['formattedAddress']) && is_array($loc['formattedAddress'])) {
            $match_address = implode(', ', $loc['formattedAddress']);
        } elseif (isset($loc['address'])) {
            $parts = array();
            $parts[] = $loc['address'];
            if (isset($loc['city'])) $parts[] = $loc['city'];
            if (isset($loc['state'])) $parts[] = $loc['state'];
            $match_address = implode(', ', $parts);
        }
    }

    // v2 search finds the venue but doesn't tell us if it's closed.
    // Status is 'found' — the venue exists in Foursquare's database.
    return array(
        'provider' => 'foursquare',
        'name' => $match_name,
        'address' => $match_address,
        'category' => $category,
        'status' => 'found',
        'match_score' => round($best_score, 2),
        'note' => 'Venue found in Foursquare database (closure status not available via free API)'
    );
}

// ============================================================
// OVERPASS / OSM CHECK
// ============================================================

function _vb_check_overpass($name, $lat, $lng) {
    $safe_name = str_replace('"', '', $name);

    // Search for active amenities, shops, AND disused/abandoned entries with matching name
    $overpass_query = '[out:json][timeout:10];('
        . 'node(around:300,' . $lat . ',' . $lng . ')["name"~"' . $safe_name . '",i];'
        . 'way(around:300,' . $lat . ',' . $lng . ')["name"~"' . $safe_name . '",i];'
        . 'node(around:300,' . $lat . ',' . $lng . ')["disused:amenity"]["name"~"' . $safe_name . '",i];'
        . 'way(around:300,' . $lat . ',' . $lng . ')["disused:amenity"]["name"~"' . $safe_name . '",i];'
        . 'node(around:300,' . $lat . ',' . $lng . ')["abandoned:amenity"]["name"~"' . $safe_name . '",i];'
        . 'way(around:300,' . $lat . ',' . $lng . ')["abandoned:amenity"]["name"~"' . $safe_name . '",i];'
        . 'node(around:300,' . $lat . ',' . $lng . ')["disused:shop"]["name"~"' . $safe_name . '",i];'
        . 'way(around:300,' . $lat . ',' . $lng . ')["disused:shop"]["name"~"' . $safe_name . '",i];'
        . ');out body;';

    $url = 'https://overpass-api.de/api/interpreter';
    $post_data = 'data=' . urlencode($overpass_query);

    $response = _vb_http_post($url, $post_data);
    if ($response === false) {
        return array(
            'provider' => 'osm',
            'status' => 'error',
            'note' => 'Overpass API request failed'
        );
    }

    $data = json_decode($response, true);
    if (!is_array($data) || !isset($data['elements'])) {
        return array(
            'provider' => 'osm',
            'status' => 'error',
            'note' => 'Invalid Overpass response'
        );
    }

    if (count($data['elements']) === 0) {
        return array(
            'provider' => 'osm',
            'status' => 'not_found',
            'note' => 'No active or disused entry found nearby'
        );
    }

    // Categorize findings
    $active = array();
    $disused = array();

    foreach ($data['elements'] as $el) {
        $tags = isset($el['tags']) ? $el['tags'] : array();
        $el_name = isset($tags['name']) ? $tags['name'] : '';

        $is_disused = isset($tags['disused:amenity']) || isset($tags['abandoned:amenity'])
                   || isset($tags['disused:shop']) || isset($tags['abandoned:shop']);

        $entry = array(
            'name' => $el_name,
            'tags' => $tags
        );

        // Build address
        $addr_parts = array();
        if (isset($tags['addr:housenumber']) && isset($tags['addr:street'])) {
            $addr_parts[] = $tags['addr:housenumber'] . ' ' . $tags['addr:street'];
        } elseif (isset($tags['addr:street'])) {
            $addr_parts[] = $tags['addr:street'];
        }
        if (isset($tags['addr:city'])) $addr_parts[] = $tags['addr:city'];
        $entry['address'] = implode(', ', $addr_parts);

        if ($is_disused) {
            $disused[] = $entry;
        } else {
            $active[] = $entry;
        }
    }

    if (count($disused) > 0) {
        $first = $disused[0];
        return array(
            'provider' => 'osm',
            'name' => $first['name'],
            'address' => $first['address'],
            'status' => 'disused',
            'note' => 'Listed as disused/abandoned in OpenStreetMap'
        );
    }

    if (count($active) > 0) {
        $first = $active[0];
        return array(
            'provider' => 'osm',
            'name' => $first['name'],
            'address' => $first['address'],
            'status' => 'active',
            'note' => 'Active listing found in OpenStreetMap'
        );
    }

    return array(
        'provider' => 'osm',
        'status' => 'not_found',
        'note' => 'No matching entry found nearby'
    );
}

// ============================================================
// VERDICT COMPUTATION
// ============================================================

// ============================================================
// GOOGLE PLACES CHECK (when API key is available)
// ============================================================

function _vb_check_google_places($name, $address, $city, $lat, $lng, $api_key) {
    // Use Text Search to find the business
    $search_text = $name;
    if ($address !== '') $search_text .= ' ' . $address;
    if ($city !== '') $search_text .= ' ' . $city;

    $params = array(
        'query' => $search_text,
        'location' => $lat . ',' . $lng,
        'radius' => '500',
        'key' => $api_key
    );

    $qs = '';
    foreach ($params as $k => $v) {
        if ($qs !== '') $qs .= '&';
        $qs .= urlencode($k) . '=' . urlencode($v);
    }

    $url = 'https://maps.googleapis.com/maps/api/place/textsearch/json?' . $qs;
    $response = _vb_http_get($url, array());

    if ($response === false) {
        return array(
            'provider' => 'google_places',
            'status' => 'error',
            'note' => 'API request failed'
        );
    }

    $data = json_decode($response, true);
    if (!is_array($data) || !isset($data['results'])) {
        return array(
            'provider' => 'google_places',
            'status' => 'error',
            'note' => 'Unexpected response format'
        );
    }

    if (count($data['results']) === 0) {
        return array(
            'provider' => 'google_places',
            'status' => 'not_found',
            'note' => 'No matching business found'
        );
    }

    // Find best match by name
    $best_match = null;
    $best_score = 0;
    $name_norm = _vb_normalize_name($name);

    foreach ($data['results'] as $place) {
        $place_name = isset($place['name']) ? $place['name'] : '';
        $score = _vb_name_match_score($name_norm, _vb_normalize_name($place_name));
        if ($score > $best_score) {
            $best_score = $score;
            $best_match = $place;
        }
    }

    if ($best_match === null || $best_score < 0.4) {
        return array(
            'provider' => 'google_places',
            'status' => 'not_found',
            'note' => 'No close name match found'
        );
    }

    $match_name = isset($best_match['name']) ? $best_match['name'] : '';
    $match_address = isset($best_match['formatted_address']) ? $best_match['formatted_address'] : '';
    $business_status = isset($best_match['business_status']) ? $best_match['business_status'] : '';

    // Map Google's business_status to our status
    $status = 'unknown';
    if ($business_status === 'OPERATIONAL') {
        $status = 'open';
    } elseif ($business_status === 'CLOSED_PERMANENTLY') {
        $status = 'closed';
    } elseif ($business_status === 'CLOSED_TEMPORARILY') {
        $status = 'temporarily_closed';
    }

    $result = array(
        'provider' => 'google_places',
        'name' => $match_name,
        'address' => $match_address,
        'status' => $status,
        'match_score' => round($best_score, 2)
    );
    if ($business_status !== '') {
        $result['business_status'] = $business_status;
    }

    return $result;
}

// ============================================================
// VERDICT COMPUTATION
// ============================================================

function _vb_compute_verdict($fsq, $osm, $google) {
    $fsq_status = ($fsq !== null && isset($fsq['status'])) ? $fsq['status'] : 'not_found';
    $osm_status = ($osm !== null && isset($osm['status'])) ? $osm['status'] : 'not_found';
    $google_status = ($google !== null && isset($google['status'])) ? $google['status'] : 'not_found';

    $verdict = 'unknown';
    $confidence = 'low';
    $summary = '';

    // Google Places has the most authoritative closure data
    if ($google_status === 'closed') {
        $verdict = 'likely_closed';
        $confidence = 'high';
        $summary = 'Google Places reports this business as permanently closed.';
        if ($osm_status === 'disused') $summary .= ' OpenStreetMap also lists it as disused.';
        if ($fsq_status === 'found') $summary .= ' Foursquare has a historical listing.';
    }
    elseif ($google_status === 'temporarily_closed') {
        $verdict = 'temporarily_closed';
        $confidence = 'high';
        $summary = 'Google Places reports this business as temporarily closed.';
    }
    elseif ($google_status === 'open') {
        if ($osm_status === 'active') {
            $verdict = 'likely_open';
            $confidence = 'high';
            $summary = 'Google Places and OpenStreetMap both confirm this business is operational.';
        } else {
            $verdict = 'likely_open';
            $confidence = 'high';
            $summary = 'Google Places confirms this business is operational.';
        }
    }
    // No Google data — rely on OSM + Foursquare
    elseif ($osm_status === 'disused') {
        $verdict = 'possibly_closed';
        $confidence = 'medium';
        $summary = 'OpenStreetMap lists this business as disused/abandoned.';
        if ($fsq_status === 'found') $summary .= ' Foursquare has a historical listing.';
    }
    elseif ($osm_status === 'active') {
        $verdict = 'likely_open';
        $confidence = ($fsq_status === 'found') ? 'medium' : 'low';
        $summary = 'OpenStreetMap has an active listing for this business.';
        if ($fsq_status === 'found') $summary .= ' Also found in Foursquare.';
    }
    elseif ($fsq_status === 'found') {
        // Found on Foursquare but not on OSM — venue exists but status unclear
        $verdict = 'unverified';
        $confidence = 'low';
        $summary = 'Business found in Foursquare database but status could not be verified. It may be open or may have closed — consider checking in person or calling ahead.';
    }
    else {
        // Not found anywhere
        $verdict = 'unknown';
        $confidence = 'low';
        if ($fsq_status === 'not_found' && $osm_status === 'not_found') {
            $summary = 'Business not found in any of our data sources. It may not exist at this location, or it may be too new/small to be listed.';
        } else {
            $summary = 'No definitive data found from available sources.';
        }
    }

    return array(
        'verdict' => $verdict,
        'confidence' => $confidence,
        'summary' => $summary
    );
}

// ============================================================
// NAME MATCHING
// ============================================================

function _vb_normalize_name($name) {
    $name = strtolower($name);
    $name = preg_replace('/[^a-z0-9 ]/', '', $name);
    $name = preg_replace('/\s+/', ' ', $name);
    return trim($name);
}

function _vb_name_match_score($query, $candidate) {
    if ($query === '' || $candidate === '') return 0;

    // Exact match
    if ($query === $candidate) return 1.0;

    // One contains the other
    if (strpos($candidate, $query) !== false) {
        return (float)strlen($query) / (float)strlen($candidate);
    }
    if (strpos($query, $candidate) !== false) {
        return (float)strlen($candidate) / (float)strlen($query);
    }

    // Word-level overlap
    $q_words = explode(' ', $query);
    $c_words = explode(' ', $candidate);
    $matches = 0;
    foreach ($q_words as $qw) {
        foreach ($c_words as $cw) {
            if ($qw === $cw) {
                $matches++;
                break;
            }
        }
    }

    $max_words = max(count($q_words), count($c_words));
    if ($max_words === 0) return 0;
    return (float)$matches / (float)$max_words;
}

// ============================================================
// HTTP HELPERS (same pattern as nearme.php)
// ============================================================

function _vb_http_get($url, $headers) {
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        if (count($headers) > 0) {
            curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        }
        $response = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        // Return response even for non-2xx so caller can inspect error
        if ($response !== false && $code >= 200 && $code < 500) {
            return $response;
        }
    }

    $hdr_str = "User-Agent: FindTorontoEvents-VerifyBiz/1.0\r\n";
    foreach ($headers as $h) {
        $hdr_str .= $h . "\r\n";
    }
    $context = stream_context_create(array(
        'http' => array(
            'method' => 'GET',
            'timeout' => 10,
            'header' => $hdr_str
        )
    ));

    $response = @file_get_contents($url, false, $context);
    return ($response !== false) ? $response : false;
}

function _vb_http_post($url, $post_data) {
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $post_data);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: application/x-www-form-urlencoded'));
        $response = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($response !== false && $code >= 200 && $code < 300) {
            return $response;
        }
    }

    $context = stream_context_create(array(
        'http' => array(
            'method' => 'POST',
            'timeout' => 15,
            'header' => "Content-Type: application/x-www-form-urlencoded\r\nUser-Agent: FindTorontoEvents-VerifyBiz/1.0\r\n",
            'content' => $post_data
        )
    ));

    $response = @file_get_contents($url, false, $context);
    return ($response !== false) ? $response : false;
}
