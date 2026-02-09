<?php
/**
 * Near Me API Endpoint
 * Shared backend for website AI bot and Discord bot.
 * Proxies requests to Foursquare Places API v3.
 *
 * PHP 5.2 compatible — no closures, no short array syntax, no ?: or ??
 *
 * Parameters:
 *   query    (string, required) - What to search for
 *   lat      (float)            - Latitude
 *   lng      (float)            - Longitude
 *   location (string)           - Landmark, intersection, postal code (geocoded server-side)
 *   radius   (int)              - Search radius in meters (default 2000, max 50000)
 *   open_now (bool)             - Filter to currently open places
 *   open_at  (string)           - Time string like "midnight", "3am", "23:00"
 *   dietary  (string)           - halal, vegan, kosher, gluten-free
 *   limit    (int)              - Max results (default 10, max 50)
 *   sort     (string)           - DISTANCE, RELEVANCE, RATING, POPULARITY
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('HTTP/1.1 200 OK');
    exit;
}

// Load config (for API key)
require_once dirname(__FILE__) . '/config.php';
require_once dirname(__FILE__) . '/nearme_categories.php';

// ============================================================
// READ PARAMETERS
// ============================================================

$query = isset($_GET['query']) ? trim($_GET['query']) : '';
if ($query === '') {
    echo json_encode(array('ok' => false, 'error' => 'Missing required parameter: query'));
    exit;
}

$lat = isset($_GET['lat']) ? (float)$_GET['lat'] : 0;
$lng = isset($_GET['lng']) ? (float)$_GET['lng'] : 0;
$location = isset($_GET['location']) ? trim($_GET['location']) : '';
$radius = isset($_GET['radius']) ? (int)$_GET['radius'] : 2000;
$open_now_param = isset($_GET['open_now']) ? $_GET['open_now'] : '';
$open_at = isset($_GET['open_at']) ? trim($_GET['open_at']) : '';
$dietary = isset($_GET['dietary']) ? trim(strtolower($_GET['dietary'])) : '';
$limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 10;
$sort_param = isset($_GET['sort']) ? strtoupper(trim($_GET['sort'])) : 'DISTANCE';
$provider = isset($_GET['provider']) ? strtolower(trim($_GET['provider'])) : 'google';
$valid_providers = array('foursquare', 'google');
$prov_ok = false;
foreach ($valid_providers as $vp) { if ($provider === $vp) { $prov_ok = true; break; } }
if (!$prov_ok) $provider = 'google';

// Clamp values
if ($radius < 100) $radius = 100;
if ($radius > 50000) $radius = 50000;
if ($limit < 1) $limit = 1;
if ($limit > 50) $limit = 50;

$valid_sorts = array('DISTANCE', 'RELEVANCE', 'RATING', 'POPULARITY');
$found_sort = false;
foreach ($valid_sorts as $vs) {
    if ($sort_param === $vs) {
        $found_sort = true;
        break;
    }
}
if (!$found_sort) $sort_param = 'DISTANCE';

$open_now = ($open_now_param === '1' || $open_now_param === 'true' || $open_now_param === 'yes');


// ============================================================
// STEP 1: CRISIS DETECTION
// ============================================================

if (nearme_is_crisis_query($query)) {
    $crisis_resources = nearme_get_crisis_resources();

    // Also try to find nearby places via Foursquare (shelters, etc.)
    $also_results = array();
    $fsq_creds = _nearme_get_fsq_credentials();
    if ($fsq_creds['type'] !== 'none') {
        // Resolve location if needed
        $coords = _nearme_resolve_location($lat, $lng, $location);
        $lat = $coords['lat'];
        $lng = $coords['lng'];

        if ($lat != 0 && $lng != 0) {
            $cat = nearme_lookup_category($query);
            $also_results = _nearme_call_foursquare($fsq_creds, $cat['query'], $lat, $lng, $radius, $open_now, $limit, $sort_param, $dietary, $cat);
        }
    }

    echo json_encode(array(
        'ok' => true,
        'query' => $query,
        'is_crisis' => true,
        'crisis_resources' => $crisis_resources,
        'also_searching_nearby' => (count($also_results) > 0),
        'results' => $also_results,
        'total' => count($also_results)
    ));
    exit;
}


// ============================================================
// STEP 2: RESOLVE LOCATION
// ============================================================

$coords = _nearme_resolve_location($lat, $lng, $location);
$lat = $coords['lat'];
$lng = $coords['lng'];
$resolved_from = $coords['resolved_from'];

if ($lat == 0 && $lng == 0) {
    // Default to downtown Toronto
    $lat = 43.6532;
    $lng = -79.3832;
    $resolved_from = 'default (downtown Toronto)';
}


// ============================================================
// STEP 3: CATEGORY LOOKUP
// ============================================================

$cat = nearme_lookup_category($query);
$fsq_query = $cat['query'];
$fsq_categories = $cat['categories'];
$group = $cat['group'];


// ============================================================
// STEP 4: DIETARY ENRICHMENT
// ============================================================

$dietary_note = '';
if ($dietary !== '') {
    $dietary_map = nearme_get_dietary_keywords();
    if (isset($dietary_map[$dietary])) {
        $d = $dietary_map[$dietary];
        if ($d['modifier'] !== '') {
            // Append dietary to query if not already present
            if (strpos(strtolower($fsq_query), strtolower($d['modifier'])) === false) {
                $fsq_query = $d['modifier'] . ' ' . $fsq_query;
            }
        }
        $dietary_note = $d['note'];
    } else {
        // Unknown dietary, just prepend
        $fsq_query = $dietary . ' ' . $fsq_query;
        $dietary_note = ucfirst($dietary) . ' -- call ahead to confirm';
    }
}


// ============================================================
// STEP 5: SEARCH API CALL (routed by provider)
// ============================================================

$results = array();

if ($provider === 'google') {
    // "google" provider: comprehensive free search from multiple sources
    // Try Google Places API first if key is configured
    $gp_results = _nearme_call_google_places($fsq_query, $lat, $lng, $radius, $limit, $cat, $dietary, $open_now);
    if ($gp_results !== null) {
        $results = $gp_results;
    } else {
        // No Google API key — merge multiple free sources for best coverage
        // Integrates: Overpass (OSM) + Foursquare + Photon + Curated local DB
        // Features: chain penalty, name dedup, business name priority matching

        // 1. Overpass (OpenStreetMap) — free, no key needed
        // Fetch more results than requested so we have a rich pool for merging
        $osm_limit = ($limit < 20) ? $limit * 4 : $limit * 2;
        if ($osm_limit > 200) $osm_limit = 200;
        $osm_results = _nearme_call_overpass($fsq_query, $lat, $lng, $radius, $osm_limit, $cat, $dietary);

        // Deduplicate chains in Overpass results (max 1 per chain name)
        $osm_results = _nearme_dedup_chains($osm_results);

        // 2. Foursquare — complements OSM with different business coverage
        $fsq_results = array();
        $fsq_creds = _nearme_get_fsq_credentials();
        if ($fsq_creds['type'] !== 'none') {
            $fsq_results = _nearme_call_foursquare($fsq_creds, $fsq_query, $lat, $lng, $radius, $open_now, $limit, $sort_param, $dietary, $cat);
        }

        // 3. Curated local businesses — verified businesses missing from OSM
        $curated_results = _nearme_curated_nearby($fsq_query, $lat, $lng, $radius, $dietary);

        // 4. Photon POI name search — finds specific businesses by name from OSM data
        //    Uses ORIGINAL query (not category-mapped) so "hailed coffee" finds "Hailed Coffee"
        $merged_for_dedup = _nearme_merge_results($osm_results, $fsq_results, $osm_limit + $limit);
        $photon_results = _nearme_search_photon($query, $lat, $lng, $radius, $dietary, $merged_for_dedup, 5);

        // Merge all sources with chain penalty sorting
        $all_results = _nearme_merge_results($osm_results, $fsq_results, $osm_limit + $limit);
        $all_results = _nearme_merge_results($all_results, $curated_results, $osm_limit + $limit + 10);
        $all_results = _nearme_merge_results($all_results, $photon_results, $osm_limit + $limit + 15);

        // Filter out closed businesses
        $all_results = _nearme_filter_closed($all_results);

        // Apply chain penalty: chains get virtual distance added so indie businesses rank higher
        $results = _nearme_sort_with_chain_penalty($all_results, $limit);
    }
} else {
    // Default: Foursquare
    $fsq_creds = _nearme_get_fsq_credentials();
    if ($fsq_creds['type'] === 'none') {
        echo json_encode(array(
            'ok' => false,
            'error' => 'Foursquare API credentials not configured. Add FOURSQUARE_CLIENT_ID and FOURSQUARE_CLIENT_SECRET (or FOURSQUARE_API_KEY) to .env file.',
            'setup_url' => 'https://foursquare.com/developers/signup'
        ));
        exit;
    }
    $results = _nearme_call_foursquare($fsq_creds, $fsq_query, $lat, $lng, $radius, $open_now, $limit, $sort_param, $dietary, $cat);
}


// ============================================================
// STEP 6: BUILD RESPONSE
// ============================================================

$delivery_tip = nearme_get_delivery_tip($group);
$pro_tip = _nearme_generate_pro_tip($query, $dietary, $open_at, count($results));

// Always include Google Maps search link for cross-reference
$google_maps_url = 'https://www.google.com/maps/search/' . urlencode($fsq_query) . '/@' . $lat . ',' . $lng . ',15z';

// Auto-suggest nearby intersection when user searched by postal code
$nearby_intersection = '';
if (_nearme_is_postal_code($resolved_from)) {
    $nearby_intersection = _nearme_reverse_geocode_intersection($lat, $lng);
}

$response = array(
    'ok' => true,
    'query' => $query,
    'category' => $cat['query'],
    'location' => array('lat' => $lat, 'lng' => $lng, 'resolved_from' => $resolved_from),
    'dietary' => $dietary,
    'dietary_note' => $dietary_note,
    'provider' => $provider,
    'results' => $results,
    'total' => count($results),
    'delivery_tip' => $delivery_tip,
    'pro_tip' => $pro_tip,
    'google_maps_url' => $google_maps_url,
    'is_crisis' => false,
    'nearby_intersection' => $nearby_intersection
);

echo json_encode($response);
exit;


// ============================================================
// INTERNAL FUNCTIONS
// ============================================================

function _nearme_get_fsq_credentials() {
    // Prefer v2 client_id + client_secret (more reliable on this hosting)
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
        return array('type' => 'v2', 'client_id' => $cid, 'client_secret' => $csec);
    }
    // Fall back to v3 API key if v2 credentials not available
    if (defined('FOURSQUARE_API_KEY') && FOURSQUARE_API_KEY !== '') {
        return array('type' => 'v3', 'key' => FOURSQUARE_API_KEY);
    }
    return array('type' => 'none');
}

function _nearme_resolve_location($lat, $lng, $location) {
    $resolved_from = '';

    // If location string is provided, always resolve it (overrides lat/lng)
    // This ensures "coffee shops near M5G 2H5" uses the postal code, not browser GPS
    if ($location !== '') {
        $loc_lower = strtolower(trim($location));

        // 1. Check landmarks table (includes common postal codes)
        $landmarks = nearme_get_landmarks();
        if (isset($landmarks[$loc_lower])) {
            $lm = $landmarks[$loc_lower];
            return array('lat' => $lm['lat'], 'lng' => $lm['lng'], 'resolved_from' => $location);
        }

        // 2. Check intersections
        $intersection = nearme_resolve_intersection($location);
        if ($intersection !== null) {
            return array('lat' => $intersection['lat'], 'lng' => $intersection['lng'], 'resolved_from' => $location);
        }

        // 3. Nominatim geocoding for postal codes and addresses
        $geo = _nearme_geocode_nominatim($location);
        if ($geo !== null) {
            return array('lat' => $geo['lat'], 'lng' => $geo['lng'], 'resolved_from' => $location);
        }

        // Location string couldn't be resolved - fall through to lat/lng
    }

    // If lat/lng provided (e.g. browser GPS for "near me"), use them
    if ($lat != 0 && $lng != 0) {
        return array('lat' => $lat, 'lng' => $lng, 'resolved_from' => 'coordinates');
    }

    return array('lat' => 0, 'lng' => 0, 'resolved_from' => '');
}

/**
 * Check if a string looks like a Canadian or US postal/zip code.
 */
function _nearme_is_postal_code($str) {
    $str = strtoupper(trim($str));
    // Canadian postal code: A1A 1A1 or A1A1A1
    if (preg_match('/^[A-Z]\d[A-Z]\s?\d[A-Z]\d$/', $str)) return true;
    // US zip: 12345 or 12345-6789
    if (preg_match('/^\d{5}(-\d{4})?$/', $str)) return true;
    return false;
}

/**
 * Reverse-geocode coordinates to find the nearest intersection/street name.
 * Uses Nominatim reverse geocoding. Returns string like "University Ave & Dundas St W"
 * or empty string on failure.
 */
function _nearme_reverse_geocode_intersection($lat, $lng) {
    // Nominatim reverse at zoom 17 (street level)
    $url = 'https://nominatim.openstreetmap.org/reverse?lat=' . $lat . '&lon=' . $lng
         . '&format=json&zoom=17&addressdetails=1';
    $headers = array('User-Agent: FindTorontoEvents/1.0');
    $response = _nearme_http_get($url, $headers);
    if ($response === false) return '';

    $data = json_decode($response, true);
    if (!is_array($data)) return '';

    $addr = isset($data['address']) ? $data['address'] : array();
    $road = isset($addr['road']) ? $addr['road'] : '';
    if ($road === '') return '';

    // Try to build an intersection name from the display_name
    // Nominatim sometimes includes nearby cross streets
    $display = isset($data['display_name']) ? $data['display_name'] : '';

    // Also do a second lookup slightly offset to find a cross street
    // Offset ~50m north to increase chance of hitting a different street
    $offset_lat = $lat + 0.00045;
    $url2 = 'https://nominatim.openstreetmap.org/reverse?lat=' . $offset_lat . '&lon=' . $lng
          . '&format=json&zoom=17&addressdetails=1';
    $response2 = _nearme_http_get($url2, $headers);
    $road2 = '';
    if ($response2 !== false) {
        $data2 = json_decode($response2, true);
        if (is_array($data2) && isset($data2['address'])) {
            $road2 = isset($data2['address']['road']) ? $data2['address']['road'] : '';
        }
    }

    // If we found two different streets, that's an intersection
    if ($road2 !== '' && strtolower($road2) !== strtolower($road)) {
        return $road . ' & ' . $road2;
    }

    // Fallback: just return the street name
    return $road;
}


function _nearme_geocode_nominatim($query) {
    // 1. Try exact query first (handles global locations, full addresses, postal codes)
    $result = _nearme_nominatim_fetch($query);

    // 2. If result is NOT in the GTA area (lat ~43.4-44.0, lon ~-80.0 to -79.0),
    //    also try with Toronto suffix and prefer that result
    $is_local = false;
    if ($result !== null) {
        $lat = $result['lat'];
        $lng = $result['lng'];
        if ($lat >= 43.4 && $lat <= 44.0 && $lng >= -80.0 && $lng <= -79.0) {
            $is_local = true;
        }
    }

    if ($result === null || !$is_local) {
        $toronto_result = _nearme_nominatim_fetch($query . ', Toronto, ON, Canada');
        if ($toronto_result !== null) return $toronto_result;
    }

    // Return whatever we got (may be non-local if Toronto fallback also failed)
    return $result;
}

function _nearme_nominatim_fetch($query) {
    $url = 'https://nominatim.openstreetmap.org/search?format=json&limit=1&q=' . urlencode($query);

    $context = stream_context_create(array(
        'http' => array(
            'method' => 'GET',
            'timeout' => 5,
            'header' => "User-Agent: FindTorontoEvents-NearMe/1.0\r\n"
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

function _nearme_call_foursquare($creds, $fsq_query, $lat, $lng, $radius, $open_now, $limit, $sort, $dietary, $cat) {
    if ($creds['type'] === 'v2') {
        $results = _nearme_call_foursquare_v2($creds, $fsq_query, $lat, $lng, $radius, $open_now, $limit, $sort, $dietary, $cat);
    } else {
        $results = _nearme_call_foursquare_v3($creds['key'], $fsq_query, $lat, $lng, $radius, $open_now, $limit, $sort, $dietary, $cat);
    }
    // Always sort by distance server-side (Foursquare sortByDistance is unreliable)
    if ($sort === 'DISTANCE' && count($results) > 1) {
        usort($results, '_nearme_sort_by_distance');
    }
    return $results;
}

function _nearme_call_foursquare_v2($creds, $fsq_query, $lat, $lng, $radius, $open_now, $limit, $sort, $dietary, $cat) {
    $params = array(
        'client_id' => $creds['client_id'],
        'client_secret' => $creds['client_secret'],
        'v' => '20250101',
        'query' => $fsq_query,
        'll' => $lat . ',' . $lng,
        'radius' => $radius,
        'limit' => $limit,
        'intent' => 'browse'
    );

    if ($open_now) {
        $params['openNow'] = '1';
    }

    // Note: v3 category IDs are not compatible with v2 API, so we skip categoryId
    // and rely on the query text alone for filtering.

    if ($sort === 'DISTANCE') {
        $params['sortByDistance'] = '1';
    }

    $qs = '';
    foreach ($params as $k => $v) {
        if ($qs !== '') $qs .= '&';
        $qs .= urlencode($k) . '=' . urlencode($v);
    }

    $url = 'https://api.foursquare.com/v2/venues/search?' . $qs;
    $response = _nearme_http_get($url, array());

    if ($response === false) {
        return array();
    }

    $data = json_decode($response, true);
    if (!is_array($data) || !isset($data['response']) || !isset($data['response']['venues'])) {
        return array();
    }

    $results = array();
    foreach ($data['response']['venues'] as $venue) {
        $result = _nearme_format_place_v2($venue, $lat, $lng, $dietary);
        $results[] = $result;
    }

    return $results;
}

function _nearme_format_place_v2($venue, $user_lat, $user_lng, $dietary) {
    $name = isset($venue['name']) ? $venue['name'] : 'Unknown';
    $vid = isset($venue['id']) ? $venue['id'] : '';
    $distance = 0;
    $address = '';
    $place_lat = 0;
    $place_lng = 0;
    $city = '';

    if (isset($venue['location'])) {
        $loc = $venue['location'];
        if (isset($loc['distance'])) $distance = (int)$loc['distance'];
        if (isset($loc['lat'])) $place_lat = (float)$loc['lat'];
        if (isset($loc['lng'])) $place_lng = (float)$loc['lng'];
        if (isset($loc['city'])) $city = $loc['city'];
        // Build address
        $parts = array();
        if (isset($loc['address']) && $loc['address'] !== '') $parts[] = $loc['address'];
        if ($city !== '') $parts[] = $city;
        if (isset($loc['state']) && $loc['state'] !== '') $parts[] = $loc['state'];
        if (isset($loc['postalCode']) && $loc['postalCode'] !== '') $parts[] = $loc['postalCode'];
        if (isset($loc['country']) && $loc['country'] !== '') $parts[] = $loc['country'];
        $address = implode(', ', $parts);
    }

    $category_name = '';
    if (isset($venue['categories']) && is_array($venue['categories']) && count($venue['categories']) > 0) {
        $first_cat = $venue['categories'][0];
        $category_name = isset($first_cat['name']) ? $first_cat['name'] : '';
    }

    $maps_url = '';
    if ($place_lat != 0 && $place_lng != 0) {
        $maps_url = 'https://www.google.com/maps/search/?api=1&query=' . $place_lat . ',' . $place_lng;
    } elseif ($address !== '') {
        $maps_url = 'https://www.google.com/maps/search/?api=1&query=' . urlencode($address);
    }

    $dietary_notes = '';
    if ($dietary !== '') {
        $dietary_map = nearme_get_dietary_keywords();
        if (isset($dietary_map[$dietary])) {
            $dietary_notes = $dietary_map[$dietary]['note'];
        } else {
            $dietary_notes = ucfirst($dietary) . ' -- call ahead to confirm';
        }
    }

    return array(
        'name' => $name,
        'category' => $category_name,
        'distance_m' => $distance,
        'address' => $address,
        'open_now' => null,
        'hours' => '',
        'hours_detail' => '',
        'rating' => 0,
        'price' => '',
        'phone' => '',
        'website' => '',
        'dietary_notes' => $dietary_notes,
        'maps_url' => $maps_url,
        'fsq_id' => $vid
    );
}

function _nearme_http_get($url, $headers) {
    // Try curl first
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        if (count($headers) > 0) {
            curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        }
        $response = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($response !== false && $code >= 200 && $code < 300) {
            return $response;
        }
    }

    // Fallback to file_get_contents
    $hdr_str = "User-Agent: FindTorontoEvents-NearMe/1.0\r\n";
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

function _nearme_call_foursquare_v3($api_key, $fsq_query, $lat, $lng, $radius, $open_now, $limit, $sort, $dietary, $cat) {
    $params = array(
        'query' => $fsq_query,
        'll' => $lat . ',' . $lng,
        'radius' => $radius,
        'limit' => $limit,
        'sort' => $sort,
        'fields' => 'fsq_id,name,categories,location,distance,tel,website,hours,hours_popular,rating,price'
    );

    if ($open_now) {
        $params['open_now'] = 'true';
    }

    $categories = isset($cat['categories']) ? $cat['categories'] : '';
    if ($categories !== '') {
        $params['categories'] = $categories;
    }

    $qs = '';
    foreach ($params as $k => $v) {
        if ($qs !== '') $qs .= '&';
        $qs .= urlencode($k) . '=' . urlencode($v);
    }

    $url = 'https://api.foursquare.com/v3/places/search?' . $qs;
    $response = _nearme_http_get($url, array(
        'Authorization: ' . $api_key,
        'Accept: application/json'
    ));

    if ($response === false) {
        return array();
    }

    $data = json_decode($response, true);
    if (!is_array($data) || !isset($data['results'])) {
        return array();
    }

    $results = array();
    foreach ($data['results'] as $place) {
        $result = _nearme_format_place($place, $lat, $lng, $dietary);
        $results[] = $result;
    }

    return $results;
}

function _nearme_format_place($place, $user_lat, $user_lng, $dietary) {
    $name = isset($place['name']) ? $place['name'] : 'Unknown';
    $fsq_id = isset($place['fsq_id']) ? $place['fsq_id'] : '';
    $distance = isset($place['distance']) ? (int)$place['distance'] : 0;
    $rating_val = isset($place['rating']) ? $place['rating'] : 0;
    $phone = isset($place['tel']) ? $place['tel'] : '';
    $website = isset($place['website']) ? $place['website'] : '';

    // Category
    $category_name = '';
    if (isset($place['categories']) && is_array($place['categories']) && count($place['categories']) > 0) {
        $first_cat = $place['categories'][0];
        $category_name = isset($first_cat['name']) ? $first_cat['name'] : '';
    }

    // Address
    $address = '';
    if (isset($place['location'])) {
        $loc = $place['location'];
        $address = isset($loc['formatted_address']) ? $loc['formatted_address'] : '';
        if ($address === '' && isset($loc['address'])) {
            $address = $loc['address'];
            if (isset($loc['locality'])) {
                $address .= ', ' . $loc['locality'];
            }
            if (isset($loc['region'])) {
                $address .= ', ' . $loc['region'];
            }
        }
    }

    // Coordinates for maps URL
    $place_lat = 0;
    $place_lng = 0;
    if (isset($place['location'])) {
        $loc = $place['location'];
        if (isset($loc['lat'])) $place_lat = (float)$loc['lat'];
        if (isset($loc['lng'])) $place_lng = (float)$loc['lng'];
    }

    $maps_url = '';
    if ($place_lat != 0 && $place_lng != 0) {
        $maps_url = 'https://www.google.com/maps/search/?api=1&query=' . $place_lat . ',' . $place_lng;
    } else if ($address !== '') {
        $maps_url = 'https://www.google.com/maps/search/?api=1&query=' . urlencode($address);
    }

    // Hours
    $hours_str = '';
    $open_now_flag = null;
    $hours_detail = '';
    if (isset($place['hours'])) {
        $h = $place['hours'];
        if (isset($h['display'])) {
            $hours_str = $h['display'];
        }
        if (isset($h['open_now'])) {
            $open_now_flag = (bool)$h['open_now'];
        }
        // Build hours detail from regular hours
        if (isset($h['regular']) && is_array($h['regular'])) {
            $today_day = (int)date('w'); // 0=Sun, 1=Mon, ...
            // Foursquare uses 1=Mon, 2=Tue, ... 7=Sun
            $fsq_day = ($today_day === 0) ? 7 : $today_day;
            foreach ($h['regular'] as $reg) {
                if (isset($reg['day']) && (int)$reg['day'] === $fsq_day) {
                    $open_t = isset($reg['open']) ? $reg['open'] : '';
                    $close_t = isset($reg['close']) ? $reg['close'] : '';
                    if ($close_t !== '') {
                        $hours_detail = 'Closes at ' . _nearme_format_time($close_t);
                    }
                    break;
                }
            }
        }
    }

    // Dietary note
    $dietary_notes = '';
    if ($dietary !== '') {
        $dietary_map = nearme_get_dietary_keywords();
        if (isset($dietary_map[$dietary])) {
            $dietary_notes = $dietary_map[$dietary]['note'];
        } else {
            $dietary_notes = ucfirst($dietary) . ' -- call ahead to confirm';
        }
    }

    // Price tier
    $price = '';
    if (isset($place['price']) && (int)$place['price'] > 0) {
        $p = (int)$place['price'];
        $price = str_repeat('$', $p);
    }

    return array(
        'name' => $name,
        'category' => $category_name,
        'distance_m' => $distance,
        'address' => $address,
        'open_now' => $open_now_flag,
        'hours' => $hours_str,
        'hours_detail' => $hours_detail,
        'rating' => $rating_val,
        'price' => $price,
        'phone' => $phone,
        'website' => $website,
        'dietary_notes' => $dietary_notes,
        'maps_url' => $maps_url,
        'fsq_id' => $fsq_id
    );
}

function _nearme_format_time($time_str) {
    // Foursquare times are "HH:MM" in 24h format or "+HH:MM" for next day
    $time_str = ltrim($time_str, '+');
    $parts = explode(':', $time_str);
    if (count($parts) < 2) return $time_str;

    $h = (int)$parts[0];
    $m = (int)$parts[1];

    if ($h === 0 && $m === 0) return '12:00 AM (midnight)';
    if ($h === 12 && $m === 0) return '12:00 PM (noon)';

    $suffix = ($h >= 12) ? 'PM' : 'AM';
    $display_h = $h % 12;
    if ($display_h === 0) $display_h = 12;

    if ($m === 0) {
        return $display_h . ' ' . $suffix;
    }
    return $display_h . ':' . str_pad((string)$m, 2, '0', STR_PAD_LEFT) . ' ' . $suffix;
}

function _nearme_generate_pro_tip($query, $dietary, $open_at, $result_count) {
    $tips = array();

    if ($result_count === 0) {
        $tips[] = 'No results found. Try expanding your search radius or adjusting your query.';
        $tips[] = 'Search Google Maps for "' . $query . '" near your location for more options.';
        return implode(' ', $tips);
    }

    if ($dietary !== '') {
        $tips[] = 'Call ahead to confirm ' . $dietary . ' certification and availability.';
    }

    if ($open_at !== '') {
        $tips[] = 'Late-night hours may vary. Call ahead to confirm.';
    }

    if ($result_count <= 3) {
        $tips[] = 'Limited results in this area. Consider expanding your search radius.';
    }

    if (count($tips) === 0) {
        $tips[] = 'Call ahead to confirm hours and availability.';
    }

    return implode(' ', $tips);
}


// ============================================================
// OVERPASS API (OpenStreetMap) PROVIDER
// ============================================================

function _nearme_call_overpass($search_query, $lat, $lng, $radius, $limit, $cat, $dietary) {
    // Map search query to OSM tags
    $osm = nearme_get_osm_tags_for_query($search_query, $cat);
    $amenity = $osm['amenity'];
    $extra_tags = $osm['extra'];

    // Build Overpass QL query
    $filters = '';
    if ($amenity !== '') {
        $filters .= '["amenity"="' . $amenity . '"]';
    }
    if ($extra_tags !== '') {
        $filters .= '[' . $extra_tags . ']';
    }

    // If no specific tags, do a name-based search
    $name_filter = '';
    if ($filters === '') {
        // Fallback: search by name containing the query
        $safe_query = str_replace('"', '', $search_query);
        $name_filter = '["name"~"' . $safe_query . '",i]';
        $overpass_query = '[out:json][timeout:15];('
            . 'node(around:' . $radius . ',' . $lat . ',' . $lng . ')' . $name_filter . ';'
            . 'way(around:' . $radius . ',' . $lat . ',' . $lng . ')' . $name_filter . ';'
            . ');out center body;';
    } else {
        // Specific amenity-based search.
        // Overpass returns results in arbitrary order (by OSM ID), not by distance.
        // Fetch ALL matching elements (no count limit), then sort/limit in PHP.
        // Downtown Toronto can have 200+ cafes within 2km — must get them all.
        $overpass_query = '[out:json][timeout:15];('
            . 'node(around:' . $radius . ',' . $lat . ',' . $lng . ')' . $filters . ';'
            . 'way(around:' . $radius . ',' . $lat . ',' . $lng . ')' . $filters . ';'
            . ');out center body;';
    }

    $url = 'https://overpass-api.de/api/interpreter';
    $post_data = 'data=' . urlencode($overpass_query);

    $response = _nearme_http_post($url, $post_data);
    if ($response === false) return array();

    $data = json_decode($response, true);
    if (!is_array($data) || !isset($data['elements'])) return array();

    $results = array();
    foreach ($data['elements'] as $el) {
        $result = _nearme_format_overpass_element($el, $lat, $lng, $dietary);
        if ($result !== null) {
            $results[] = $result;
        }
    }

    // Sort by distance
    usort($results, '_nearme_sort_by_distance');

    // Limit results
    if (count($results) > $limit) {
        $results = array_slice($results, 0, $limit);
    }

    return $results;
}

function _nearme_sort_by_distance($a, $b) {
    if ($a['distance_m'] == $b['distance_m']) return 0;
    return ($a['distance_m'] < $b['distance_m']) ? -1 : 1;
}

function _nearme_format_overpass_element($el, $user_lat, $user_lng, $dietary) {
    // Get coordinates
    $el_lat = 0;
    $el_lng = 0;
    if (isset($el['lat']) && isset($el['lon'])) {
        $el_lat = (float)$el['lat'];
        $el_lng = (float)$el['lon'];
    } elseif (isset($el['center'])) {
        $el_lat = isset($el['center']['lat']) ? (float)$el['center']['lat'] : 0;
        $el_lng = isset($el['center']['lon']) ? (float)$el['center']['lon'] : 0;
    }

    if ($el_lat == 0 && $el_lng == 0) return null;

    $tags = isset($el['tags']) ? $el['tags'] : array();
    $name = isset($tags['name']) ? $tags['name'] : '';
    if ($name === '') return null; // Skip unnamed elements

    // Calculate distance using Haversine
    $distance = _nearme_haversine($user_lat, $user_lng, $el_lat, $el_lng);

    // Build address
    $addr_parts = array();
    if (isset($tags['addr:housenumber']) && isset($tags['addr:street'])) {
        $addr_parts[] = $tags['addr:housenumber'] . ' ' . $tags['addr:street'];
    } elseif (isset($tags['addr:street'])) {
        $addr_parts[] = $tags['addr:street'];
    }
    if (isset($tags['addr:city'])) $addr_parts[] = $tags['addr:city'];
    if (isset($tags['addr:province'])) $addr_parts[] = $tags['addr:province'];
    elseif (isset($tags['addr:state'])) $addr_parts[] = $tags['addr:state'];
    if (isset($tags['addr:postcode'])) $addr_parts[] = $tags['addr:postcode'];
    $address = implode(', ', $addr_parts);

    // Category from OSM tags
    $category = '';
    if (isset($tags['amenity'])) $category = ucfirst(str_replace('_', ' ', $tags['amenity']));
    if (isset($tags['cuisine'])) $category .= ($category !== '' ? ' - ' : '') . ucfirst(str_replace(array('_', ';'), array(' ', ', '), $tags['cuisine']));
    if (isset($tags['shop'])) $category = ucfirst(str_replace('_', ' ', $tags['shop']));

    // Phone / website
    $phone = isset($tags['phone']) ? $tags['phone'] : (isset($tags['contact:phone']) ? $tags['contact:phone'] : '');
    $website = isset($tags['website']) ? $tags['website'] : (isset($tags['contact:website']) ? $tags['contact:website'] : '');

    // Opening hours
    $hours_str = isset($tags['opening_hours']) ? $tags['opening_hours'] : '';
    $open_now_flag = null;
    if ($hours_str !== '') {
        // Simple check: if hours contain "24/7" it's always open
        if (strpos($hours_str, '24/7') !== false) {
            $open_now_flag = true;
        }
    }

    // Maps URL
    $maps_url = 'https://www.google.com/maps/search/?api=1&query=' . $el_lat . ',' . $el_lng;

    // Dietary note
    $dietary_notes = '';
    if ($dietary !== '') {
        $dietary_map = nearme_get_dietary_keywords();
        if (isset($dietary_map[$dietary])) {
            $dietary_notes = $dietary_map[$dietary]['note'];
        } else {
            $dietary_notes = ucfirst($dietary) . ' -- call ahead to confirm';
        }
        // Check OSM tags for dietary info
        if (isset($tags['diet:vegan']) && $tags['diet:vegan'] === 'yes') $dietary_notes = 'Vegan options available';
        if (isset($tags['diet:vegetarian']) && $tags['diet:vegetarian'] === 'yes') $dietary_notes = 'Vegetarian options available';
        if (isset($tags['diet:halal']) && $tags['diet:halal'] === 'yes') $dietary_notes = 'Halal certified';
        if (isset($tags['diet:kosher']) && $tags['diet:kosher'] === 'yes') $dietary_notes = 'Kosher certified';
    }

    return array(
        'name' => $name,
        'category' => $category,
        'distance_m' => (int)round($distance),
        'address' => $address,
        'open_now' => $open_now_flag,
        'hours' => $hours_str,
        'hours_detail' => '',
        'rating' => 0,
        'price' => '',
        'phone' => $phone,
        'website' => $website,
        'dietary_notes' => $dietary_notes,
        'maps_url' => $maps_url,
        'fsq_id' => 'osm_' . (isset($el['id']) ? $el['id'] : '0'),
        'source' => 'openstreetmap'
    );
}

function _nearme_haversine($lat1, $lon1, $lat2, $lon2) {
    $R = 6371000; // Earth radius in meters
    $dLat = deg2rad($lat2 - $lat1);
    $dLon = deg2rad($lon2 - $lon1);
    $a = sin($dLat / 2) * sin($dLat / 2)
       + cos(deg2rad($lat1)) * cos(deg2rad($lat2))
       * sin($dLon / 2) * sin($dLon / 2);
    $c = 2 * atan2(sqrt($a), sqrt(1 - $a));
    return $R * $c;
}

function _nearme_http_post($url, $post_data) {
    // Try curl first
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

    // Fallback to file_get_contents with POST
    $context = stream_context_create(array(
        'http' => array(
            'method' => 'POST',
            'timeout' => 15,
            'header' => "Content-Type: application/x-www-form-urlencoded\r\nUser-Agent: FindTorontoEvents-NearMe/1.0\r\n",
            'content' => $post_data
        )
    ));

    $response = @file_get_contents($url, false, $context);
    return ($response !== false) ? $response : false;
}

// ============================================================
// GOOGLE PLACES API PROVIDER
// ============================================================

/**
 * Call Google Places Text Search API.
 * Returns array of results on success, or null if API key not configured / API error (triggers Overpass fallback).
 */
function _nearme_call_google_places($search_query, $lat, $lng, $radius, $limit, $cat, $dietary, $open_now) {
    $api_key = defined('GOOGLE_PLACES_API_KEY') ? GOOGLE_PLACES_API_KEY : '';
    if ($api_key === '') return null; // No key — fall back to Overpass

    // Build Text Search URL
    $params = array(
        'query' => $search_query,
        'location' => $lat . ',' . $lng,
        'radius' => $radius,
        'key' => $api_key
    );

    $qs = '';
    foreach ($params as $k => $v) {
        if ($qs !== '') $qs .= '&';
        $qs .= urlencode($k) . '=' . urlencode($v);
    }

    $url = 'https://maps.googleapis.com/maps/api/place/textsearch/json?' . $qs;
    if ($open_now) {
        $url .= '&opennow';
    }

    $response = _nearme_http_get($url, array());
    if ($response === false) return null;

    $data = json_decode($response, true);
    if (!is_array($data) || !isset($data['results'])) return null;
    if (!isset($data['status'])) return null;
    if ($data['status'] !== 'OK' && $data['status'] !== 'ZERO_RESULTS') return null;

    $results = array();
    foreach ($data['results'] as $place) {
        $result = _nearme_format_google_place($place, $lat, $lng, $dietary);
        if ($result !== null) {
            $results[] = $result;
        }
        if (count($results) >= $limit) break;
    }

    // Sort by distance
    if (count($results) > 1) {
        usort($results, '_nearme_sort_by_distance');
    }

    return $results;
}

function _nearme_format_google_place($place, $user_lat, $user_lng, $dietary) {
    $name = isset($place['name']) ? $place['name'] : '';
    if ($name === '') return null;

    // Coordinates
    $place_lat = 0;
    $place_lng = 0;
    if (isset($place['geometry']) && isset($place['geometry']['location'])) {
        $loc = $place['geometry']['location'];
        if (isset($loc['lat'])) $place_lat = (float)$loc['lat'];
        if (isset($loc['lng'])) $place_lng = (float)$loc['lng'];
    }

    // Distance
    $distance = 0;
    if ($place_lat != 0 && $place_lng != 0) {
        $distance = (int)round(_nearme_haversine($user_lat, $user_lng, $place_lat, $place_lng));
    }

    $address = isset($place['formatted_address']) ? $place['formatted_address'] : '';

    // Rating (Google uses 1.0-5.0 scale)
    $rating = isset($place['rating']) ? (float)$place['rating'] : 0;

    // Price level (0-4 in Google, convert to $ signs)
    $price = '';
    if (isset($place['price_level']) && (int)$place['price_level'] > 0) {
        $price = str_repeat('$', (int)$place['price_level']);
    }

    // Open now
    $open_now_flag = null;
    if (isset($place['opening_hours']) && isset($place['opening_hours']['open_now'])) {
        $open_now_flag = (bool)$place['opening_hours']['open_now'];
    }

    // Category from types
    $category = '';
    if (isset($place['types']) && is_array($place['types'])) {
        $type_map = array(
            'cafe' => 'Cafe',
            'restaurant' => 'Restaurant',
            'bar' => 'Bar',
            'bakery' => 'Bakery',
            'pharmacy' => 'Pharmacy',
            'hospital' => 'Hospital',
            'gas_station' => 'Gas Station',
            'grocery_or_supermarket' => 'Grocery Store',
            'supermarket' => 'Grocery Store',
            'shopping_mall' => 'Shopping Mall',
            'gym' => 'Gym',
            'park' => 'Park',
            'bank' => 'Bank',
            'library' => 'Library',
            'school' => 'School',
            'church' => 'Church',
            'movie_theater' => 'Movie Theater',
            'clothing_store' => 'Clothing Store',
            'book_store' => 'Book Store',
            'hair_care' => 'Hair Salon',
            'beauty_salon' => 'Beauty Salon',
            'dentist' => 'Dentist',
            'doctor' => 'Doctor',
            'veterinary_care' => 'Veterinary',
            'car_repair' => 'Auto Repair',
            'car_wash' => 'Car Wash',
            'laundry' => 'Laundry',
            'lodging' => 'Hotel',
            'night_club' => 'Night Club',
            'convenience_store' => 'Convenience Store'
        );
        foreach ($place['types'] as $t) {
            if (isset($type_map[$t])) {
                $category = $type_map[$t];
                break;
            }
        }
        // Skip generic types like "point_of_interest", "establishment", "food"
        if ($category === '') {
            $skip_types = array('point_of_interest', 'establishment', 'food', 'store', 'health', 'finance', 'general_contractor', 'political', 'locality', 'route');
            foreach ($place['types'] as $t) {
                $is_skip = false;
                foreach ($skip_types as $st) {
                    if ($t === $st) { $is_skip = true; break; }
                }
                if (!$is_skip) {
                    $category = ucfirst(str_replace('_', ' ', $t));
                    break;
                }
            }
        }
    }

    // Maps URL — use place_id for precise link
    $place_id = isset($place['place_id']) ? $place['place_id'] : '';
    $maps_url = '';
    if ($place_id !== '') {
        $maps_url = 'https://www.google.com/maps/place/?q=place_id:' . $place_id;
    } elseif ($place_lat != 0 && $place_lng != 0) {
        $maps_url = 'https://www.google.com/maps/search/?api=1&query=' . $place_lat . ',' . $place_lng;
    } elseif ($address !== '') {
        $maps_url = 'https://www.google.com/maps/search/?api=1&query=' . urlencode($address);
    }

    // Dietary note
    $dietary_notes = '';
    if ($dietary !== '') {
        $dietary_map = nearme_get_dietary_keywords();
        if (isset($dietary_map[$dietary])) {
            $dietary_notes = $dietary_map[$dietary]['note'];
        } else {
            $dietary_notes = ucfirst($dietary) . ' -- call ahead to confirm';
        }
    }

    return array(
        'name' => $name,
        'category' => $category,
        'distance_m' => $distance,
        'address' => $address,
        'open_now' => $open_now_flag,
        'hours' => '',
        'hours_detail' => '',
        'rating' => $rating,
        'price' => $price,
        'phone' => '',
        'website' => '',
        'dietary_notes' => $dietary_notes,
        'maps_url' => $maps_url,
        'fsq_id' => 'gp_' . $place_id,
        'source' => 'google_places'
    );
}

// ============================================================
// PHOTON POI NAME SEARCH (free, based on OpenStreetMap data)
// ============================================================

/**
 * Search Photon geocoder for POIs matching the query near the user's location.
 * Photon (photon.komoot.io) is a free geocoding API based on OSM data that
 * can find businesses by name. No API key needed.
 * Returns formatted results array, skipping duplicates already in existing results.
 */
function _nearme_search_photon($search_query, $user_lat, $user_lng, $radius, $dietary, $existing_results, $max_results) {
    // Build Photon query with location bias
    $url = 'https://photon.komoot.io/api/?q=' . urlencode($search_query)
         . '&lat=' . $user_lat . '&lon=' . $user_lng
         . '&limit=' . ($max_results * 3);

    $response = _nearme_http_get($url, array());
    if ($response === false) return array();

    $data = json_decode($response, true);
    if (!is_array($data) || !isset($data['features'])) return array();

    // Build existing names for dedup
    $existing_lower = array();
    foreach ($existing_results as $r) {
        $existing_lower[] = strtolower($r['name']);
    }

    $results = array();
    foreach ($data['features'] as $feat) {
        if (count($results) >= $max_results) break;

        $props = isset($feat['properties']) ? $feat['properties'] : array();
        $coords = isset($feat['geometry']) && isset($feat['geometry']['coordinates']) ? $feat['geometry']['coordinates'] : array(0, 0);

        $name = isset($props['name']) ? $props['name'] : '';
        if ($name === '') continue;

        // Only include POI-type results (amenity, shop, tourism, etc.), not addresses/cities
        $osm_key = isset($props['osm_key']) ? $props['osm_key'] : '';
        $poi_keys = array('amenity', 'shop', 'tourism', 'leisure', 'office', 'craft');
        $is_poi = false;
        foreach ($poi_keys as $pk) {
            if ($osm_key === $pk) { $is_poi = true; break; }
        }
        if (!$is_poi) continue;

        $feat_lat = (float)$coords[1];
        $feat_lng = (float)$coords[0];
        $distance = (int)round(_nearme_haversine($user_lat, $user_lng, $feat_lat, $feat_lng));

        // Skip if outside search radius
        if ($distance > $radius) continue;

        // Skip if already in existing results (fuzzy match)
        $name_lower = strtolower($name);
        $skip = false;
        foreach ($existing_lower as $ex) {
            if ($name_lower === $ex) { $skip = true; break; }
            if (strlen($ex) > 4 && strpos($name_lower, $ex) !== false) { $skip = true; break; }
            if (strlen($name_lower) > 4 && strpos($ex, $name_lower) !== false) { $skip = true; break; }
        }
        if ($skip) continue;

        // Build address
        $addr_parts = array();
        if (isset($props['housenumber']) && isset($props['street'])) {
            $addr_parts[] = $props['housenumber'] . ' ' . $props['street'];
        } elseif (isset($props['street'])) {
            $addr_parts[] = $props['street'];
        }
        if (isset($props['city'])) $addr_parts[] = $props['city'];
        if (isset($props['state'])) $addr_parts[] = $props['state'];
        if (isset($props['postcode'])) $addr_parts[] = $props['postcode'];
        $address = implode(', ', $addr_parts);

        // Category from OSM tags
        $osm_value = isset($props['osm_value']) ? $props['osm_value'] : '';
        $category = ucfirst(str_replace('_', ' ', $osm_value));

        // Maps URL
        $maps_url = 'https://www.google.com/maps/search/?api=1&query=' . $feat_lat . ',' . $feat_lng;

        // Dietary note
        $dietary_notes = '';
        if ($dietary !== '') {
            $dietary_map = nearme_get_dietary_keywords();
            if (isset($dietary_map[$dietary])) {
                $dietary_notes = $dietary_map[$dietary]['note'];
            } else {
                $dietary_notes = ucfirst($dietary) . ' -- call ahead to confirm';
            }
        }

        $results[] = array(
            'name' => $name,
            'category' => $category,
            'distance_m' => $distance,
            'address' => $address,
            'open_now' => null,
            'hours' => '',
            'hours_detail' => '',
            'rating' => 0,
            'price' => '',
            'phone' => '',
            'website' => '',
            'dietary_notes' => $dietary_notes,
            'maps_url' => $maps_url,
            'fsq_id' => 'photon_' . (isset($props['osm_id']) ? $props['osm_id'] : '0'),
            'source' => 'photon'
        );
    }

    return $results;
}


// ============================================================
// CURATED LOCAL BUSINESS DATABASE
// ============================================================

/**
 * Curated businesses verified to exist but missing from OSM/Foursquare.
 * Returns entries within radius matching the query category.
 */
function _nearme_curated_nearby($search_query, $user_lat, $user_lng, $radius, $dietary) {
    $curated = array(
        array('name' => 'Cafe Foret', 'lat' => 43.6549, 'lng' => -79.3877,
              'address' => '153 Dundas St W, Toronto, ON M5G 1C6',
              'tags' => 'cafe,coffee,coffee shop,korean cafe',
              'phone' => '', 'website' => 'https://instagram.com/cafeforet_to',
              'hours' => 'Mon-Sun 10am-10pm'),
        array('name' => 'Hailed Coffee', 'lat' => 43.6566, 'lng' => -79.3852,
              'address' => '112 Elizabeth St, Toronto, ON M5G 1P5',
              'tags' => 'cafe,coffee,coffee shop',
              'phone' => '', 'website' => 'https://hailedcoffee.com',
              'hours' => ''),
        array('name' => 'Hailed Coffee', 'lat' => 43.6589, 'lng' => -79.3838,
              'address' => '44 Gerrard St W, Toronto, ON M5G 2K2',
              'tags' => 'cafe,coffee,coffee shop',
              'phone' => '', 'website' => 'https://hailedcoffee.com',
              'hours' => ''),
        array('name' => 'Hailed Coffee', 'lat' => 43.6679, 'lng' => -79.3528,
              'address' => '801 Gerrard St E, Toronto, ON M4M 1Y5',
              'tags' => 'cafe,coffee,coffee shop',
              'phone' => '', 'website' => 'https://hailedcoffee.com',
              'hours' => '')
    );

    $q_lower = strtolower(trim($search_query));
    $q_singular = rtrim($q_lower, 's');
    $results = array();

    foreach ($curated as $biz) {
        $tags = explode(',', $biz['tags']);
        $match = false;
        foreach ($tags as $tag) {
            $tag = trim($tag);
            if ($tag === $q_lower || $tag === $q_singular) { $match = true; break; }
            if (strpos($q_lower, $tag) !== false) { $match = true; break; }
            if (strpos($tag, $q_lower) !== false) { $match = true; break; }
        }
        // Also match if query looks like this business name
        $name_lower = strtolower($biz['name']);
        if (strpos($name_lower, $q_lower) !== false || strpos($q_lower, $name_lower) !== false) {
            $match = true;
        }
        if (!$match) continue;

        $dist = _nearme_haversine($user_lat, $user_lng, $biz['lat'], $biz['lng']);
        if ($dist > $radius) continue;

        $dietary_notes = '';
        if ($dietary !== '') {
            $dietary_map = nearme_get_dietary_keywords();
            if (isset($dietary_map[$dietary])) {
                $dietary_notes = $dietary_map[$dietary]['note'];
            } else {
                $dietary_notes = ucfirst($dietary) . ' -- call ahead to confirm';
            }
        }

        $results[] = array(
            'name' => $biz['name'],
            'category' => 'Cafe',
            'distance_m' => (int)round($dist),
            'address' => $biz['address'],
            'open_now' => null,
            'hours' => $biz['hours'],
            'hours_detail' => '',
            'rating' => 0,
            'price' => '',
            'phone' => $biz['phone'],
            'website' => $biz['website'],
            'dietary_notes' => $dietary_notes,
            'maps_url' => 'https://www.google.com/maps/search/?api=1&query=' . $biz['lat'] . ',' . $biz['lng'],
            'fsq_id' => 'curated_' . md5($biz['name'] . $biz['address']),
            'source' => 'curated'
        );
    }

    return $results;
}


// ============================================================
// CHAIN PENALTY + DEDUP
// ============================================================

/**
 * Deduplicate chain businesses: keep max 1 location per chain name.
 * Prevents results from being flooded with 7 Tim Hortons, 5 Starbucks, etc.
 */
function _nearme_dedup_chains($results) {
    $deduped = array();
    $name_counts = array();
    foreach ($results as $r) {
        $name_key = strtolower($r['name']);
        $count = isset($name_counts[$name_key]) ? $name_counts[$name_key] : 0;
        if ($count < 1) {
            $deduped[] = $r;
            $name_counts[$name_key] = $count + 1;
        }
    }
    return $deduped;
}


/**
 * Filter out businesses that appear to be permanently closed.
 * Matches names containing "(closed)", "[closed]", "closed permanently", etc.
 */
function _nearme_filter_closed($results) {
    // Known-closed businesses: array of [name_substring, address_substring] pairs
    // Both must match (case-insensitive) for the entry to be removed.
    // Use '' for address to match by name alone across all locations.
    $known_closed = array(
        array('241 pizza', '327 queen'),
    );

    $filtered = array();
    foreach ($results as $r) {
        $name_lower = strtolower($r['name']);
        $addr_lower = strtolower(isset($r['address']) ? $r['address'] : '');

        // Filter names containing "closed"
        if (strpos($name_lower, 'closed') !== false) continue;

        // Check known-closed blocklist
        $is_closed = false;
        foreach ($known_closed as $entry) {
            $match_name = strpos($name_lower, $entry[0]) !== false;
            $match_addr = ($entry[1] === '') || (strpos($addr_lower, $entry[1]) !== false);
            if ($match_name && $match_addr) {
                $is_closed = true;
                break;
            }
        }
        if ($is_closed) continue;

        $filtered[] = $r;
    }
    return $filtered;
}


/**
 * Sort results with chain penalty: chains get virtual distance added so
 * independent/unique businesses surface above chains at similar distances.
 */
function _nearme_sort_with_chain_penalty($results, $limit) {
    // Add effective distance for sorting
    $with_penalty = array();
    foreach ($results as $r) {
        $penalty = _nearme_chain_penalty($r['name']);
        $r['_effective_dist'] = $r['distance_m'] + $penalty;
        $with_penalty[] = $r;
    }

    usort($with_penalty, '_nearme_sort_by_effective_distance');

    if (count($with_penalty) > $limit) {
        $with_penalty = array_slice($with_penalty, 0, $limit);
    }

    // Remove internal sort key
    $out = array();
    foreach ($with_penalty as $r) {
        unset($r['_effective_dist']);
        $out[] = $r;
    }
    return $out;
}

function _nearme_sort_by_effective_distance($a, $b) {
    if ($a['_effective_dist'] == $b['_effective_dist']) return 0;
    return ($a['_effective_dist'] < $b['_effective_dist']) ? -1 : 1;
}

/**
 * Chain penalty in meters: major chains get pushed down in results.
 */
function _nearme_chain_penalty($name) {
    $major_chains = array(
        'tim hortons', 'starbucks', 'second cup', 'timothy',
        'mcdonald', 'subway', 'pizza pizza', 'domino',
        'dunkin', 'pret a manger'
    );
    $bubble_tea = array(
        'chatime', 'coco', 'kung fu tea', 'the alley',
        'real fruit bubble tea', 'fruiteao', 'gong cha',
        'cha miao', 'tiger sugar', 'onezo', 'presotea'
    );
    $minor_chains = array(
        'aroma espresso', 'balzac', 'pilot coffee'
    );
    $name_lower = strtolower($name);
    foreach ($major_chains as $chain) {
        if (strpos($name_lower, $chain) !== false) return 500;
    }
    foreach ($bubble_tea as $bt) {
        if (strpos($name_lower, $bt) !== false) return 400;
    }
    foreach ($minor_chains as $mc) {
        if (strpos($name_lower, $mc) !== false) return 200;
    }
    return 0;
}


// ============================================================
// MULTI-SOURCE RESULT MERGING
// ============================================================

/**
 * Merge two result arrays, deduplicating by name similarity + proximity.
 */
function _nearme_merge_results($results_a, $results_b, $limit) {
    $merged = $results_a;

    foreach ($results_b as $b) {
        $is_dup = false;
        $b_lower = strtolower($b['name']);

        foreach ($merged as $a) {
            $a_lower = strtolower($a['name']);

            // Name match: exact or one contains the other
            $name_match = false;
            if ($a_lower === $b_lower) {
                $name_match = true;
            } else {
                $a_long = (strlen($a_lower) > 4);
                $b_long = (strlen($b_lower) > 4);
                if (($a_long && strpos($b_lower, $a_lower) !== false) ||
                    ($b_long && strpos($a_lower, $b_lower) !== false)) {
                    $name_match = true;
                }
            }
            if ($name_match) {
                // Only dedup if same physical location (within 150m from user)
                if ($a['distance_m'] > 0 && $a['distance_m'] < 99999 &&
                    $b['distance_m'] > 0 && $b['distance_m'] < 99999) {
                    $diff = $a['distance_m'] - $b['distance_m'];
                    if ($diff < 0) $diff = -$diff;
                    if ($diff < 150) { $is_dup = true; break; }
                } else {
                    $is_dup = true; break;
                }
            }
        }

        if (!$is_dup) {
            $merged[] = $b;
        }
    }

    usort($merged, '_nearme_sort_by_distance');

    if (count($merged) > $limit) {
        $merged = array_slice($merged, 0, $limit);
    }

    return $merged;
}


/**
 * Deduplicate an array of results (preserving order), limit to $limit.
 * Used when priority results are prepended before distance-sorted results.
 */
function _nearme_deduplicate($results, $limit) {
    $seen = array();
    $out = array();
    foreach ($results as $r) {
        if (count($out) >= $limit) break;
        $name_lower = strtolower($r['name']);
        // Check for duplicates
        $is_dup = false;
        foreach ($seen as $s) {
            if ($name_lower === $s) { $is_dup = true; break; }
            if (strlen($s) > 4 && strpos($name_lower, $s) !== false) { $is_dup = true; break; }
            if (strlen($name_lower) > 4 && strpos($s, $name_lower) !== false) { $is_dup = true; break; }
        }
        if (!$is_dup) {
            $out[] = $r;
            $seen[] = $name_lower;
        }
    }
    return $out;
}


/**
 * Map a search query to OSM tags for Overpass API
 */
function nearme_get_osm_tags_for_query($search_query, $cat) {
    $osm_map = nearme_get_osm_tags();
    $q = strtolower(trim($search_query));

    // Direct match
    if (isset($osm_map[$q])) return $osm_map[$q];

    // Try without trailing 's'
    $qs = rtrim($q, 's');
    if ($qs !== $q && isset($osm_map[$qs])) return $osm_map[$qs];

    // Partial match: check if any key is in the query
    $best = null;
    $best_len = 0;
    foreach ($osm_map as $key => $val) {
        if (strpos($q, $key) !== false && strlen($key) > $best_len) {
            $best = $val;
            $best_len = strlen($key);
        }
    }
    if ($best !== null) return $best;

    // Fallback based on Foursquare category group
    $group = isset($cat['group']) ? $cat['group'] : '';
    if ($group === 'food') return array('amenity' => 'restaurant', 'extra' => '');
    if ($group === 'retail') return array('amenity' => '', 'extra' => '"shop"');
    if ($group === 'healthcare') return array('amenity' => 'hospital', 'extra' => '');

    // No mapping found: search by name
    return array('amenity' => '', 'extra' => '');
}
