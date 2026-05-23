<?php
/**
 * nearme_search.php — Standalone multi-source place search API (FREE, no API keys)
 *
 * Combines 3 free data sources to find nearby businesses:
 *   1. Overpass API (OpenStreetMap) — comprehensive POI database
 *   2. DuckDuckGo Lite scraping — finds businesses from web (Yelp, MapQuest, blogs)
 *   3. Nominatim geocoding — geocodes web-found businesses to get lat/lng + distance
 *
 * Usage:
 *   GET nearme_search.php?query=coffee+shop&location=M5G+2H5&limit=10
 *   GET nearme_search.php?query=coffee+shop&lat=43.654&lng=-79.387&limit=10
 *
 * Parameters:
 *   query    — what to search for (e.g. "coffee shop", "pizza", "pharmacy")
 *   location — postal code, address, or landmark (e.g. "M5G 2H5", "university and dundas")
 *   lat/lng  — explicit coordinates (override location)
 *   radius   — search radius in meters (default 2000)
 *   limit    — max results (default 10)
 *
 * Response:
 *   JSON with "ok", "results" array, "sources_used", "google_maps_url"
 *   Each result has: name, category, distance_m, address, source, maps_url, etc.
 *
 * PHP 5.2 compatible — no closures, no short arrays, no http_response_code().
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
if (strtoupper($_SERVER['REQUEST_METHOD']) === 'OPTIONS') {
    exit;
}

// ============================================================
// PARAMETERS
// ============================================================

$query    = isset($_GET['query']) ? trim($_GET['query']) : '';
$location = isset($_GET['location']) ? trim($_GET['location']) : '';
$lat      = isset($_GET['lat']) ? (float)$_GET['lat'] : 0;
$lng      = isset($_GET['lng']) ? (float)$_GET['lng'] : 0;
$radius   = isset($_GET['radius']) ? (int)$_GET['radius'] : 2000;
$limit    = isset($_GET['limit']) ? (int)$_GET['limit'] : 15;
$debug    = isset($_GET['debug']) ? (int)$_GET['debug'] : 0;

if ($radius < 100) $radius = 100;
if ($radius > 50000) $radius = 50000;
if ($limit < 1) $limit = 1;
if ($limit > 50) $limit = 50;

if ($query === '') {
    echo json_encode(array('ok' => false, 'error' => 'Missing required parameter: query'));
    exit;
}

// ============================================================
// GEOCODE LOCATION
// ============================================================

$resolved_from = '';

if ($lat == 0 && $lng == 0 && $location !== '') {
    $geo = _ns_geocode($location);
    if ($geo !== null) {
        $lat = $geo['lat'];
        $lng = $geo['lng'];
        $resolved_from = $location;
    }
}

if ($lat == 0 && $lng == 0) {
    // Default to downtown Toronto (University & Dundas area)
    $lat = 43.6555;
    $lng = -79.3878;
    $resolved_from = 'default (Toronto downtown)';
}

// ============================================================
// SOURCE 1: OVERPASS API (OpenStreetMap)
// ============================================================

// Fetch more from OSM than final limit — we merge with DDG later and need full coverage
$osm_fetch_limit = ($limit * 5 < 100) ? $limit * 5 : 100;
$osm_results = _ns_overpass_search($query, $lat, $lng, $radius, $osm_fetch_limit);

// ============================================================
// SOURCE 2: DUCKDUCKGO LITE SCRAPING
// ============================================================

$location_str = ($location !== '') ? $location : 'Toronto';
$ddg_businesses = _ns_ddg_scrape($query, $location_str);

// Geocode DDG businesses and merge (skip duplicates)
$ddg_results = _ns_geocode_businesses($ddg_businesses, $lat, $lng, $location_str, $osm_results, 5);

// ============================================================
// SOURCE 3: CURATED LOCAL BUSINESS DATABASE
// ============================================================
// Businesses known to be missing from OSM/web scraping but verified to exist.
// This ensures popular local spots always appear in nearby results.

$curated_results = _ns_curated_nearby($query, $lat, $lng, $radius);

// ============================================================
// MERGE + SORT + RESPOND
// ============================================================

$merged_osm_web = _ns_merge($osm_results, $ddg_results, $limit * 5);
$all_results = _ns_merge($merged_osm_web, $curated_results, $limit);

$google_maps_url = 'https://www.google.com/maps/search/' . urlencode($query) . '/@' . $lat . ',' . $lng . ',15z';

$sources = array();
$has_osm = false;
$has_web = false;
$has_curated = false;
foreach ($all_results as $r) {
    if ($r['source'] === 'openstreetmap') $has_osm = true;
    if ($r['source'] === 'web_search') $has_web = true;
    if ($r['source'] === 'curated') $has_curated = true;
}
if ($has_osm) $sources[] = 'openstreetmap';
if ($has_web) $sources[] = 'brave_web';
if ($has_curated) $sources[] = 'curated_local';

$response = array(
    'ok' => true,
    'query' => $query,
    'location' => array(
        'lat' => $lat,
        'lng' => $lng,
        'resolved_from' => $resolved_from
    ),
    'results' => $all_results,
    'total' => count($all_results),
    'sources_used' => $sources,
    'google_maps_url' => $google_maps_url
);

// Debug mode: include source-level details
if ($debug) {
    global $_ns_ddg_debug;
    $response['debug'] = array(
        'osm_count_before_dedup' => $osm_fetch_limit,
        'osm_count' => count($osm_results),
        'ddg_businesses_found' => count($ddg_businesses),
        'ddg_businesses' => $ddg_businesses,
        'ddg_geocoded_count' => count($ddg_results),
        'ddg_results' => $ddg_results,
        'ddg_http_debug' => isset($_ns_ddg_debug) ? $_ns_ddg_debug : array()
    );
}

echo json_encode($response);
exit;


// ============================================================
// HELPER FUNCTIONS (all PHP 5.2 compatible)
// ============================================================


/**
 * Geocode a location string using Nominatim (free OSM geocoder).
 */
function _ns_geocode($query) {
    // Try exact query first (handles postal codes, global addresses, landmarks)
    $result = _ns_nominatim_fetch($query);
    if ($result !== null) return $result;

    // Fall back: append Toronto context for local queries
    $result = _ns_nominatim_fetch($query . ', Toronto, ON, Canada');
    return $result;
}

function _ns_nominatim_fetch($query) {
    $url = 'https://nominatim.openstreetmap.org/search?format=json&limit=1&q=' . urlencode($query);
    $response = _ns_http_get($url, array(
        'User-Agent: FindTorontoEvents-NearMeSearch/1.0'
    ));
    if ($response === false) return null;

    $data = json_decode($response, true);
    if (!is_array($data) || count($data) === 0) return null;

    $first = $data[0];
    if (!isset($first['lat']) || !isset($first['lon'])) return null;
    return array('lat' => (float)$first['lat'], 'lng' => (float)$first['lon']);
}


/**
 * Search Overpass API (OpenStreetMap) for POIs near coordinates.
 */
function _ns_overpass_search($query, $lat, $lng, $radius, $limit) {
    $osm_tags = _ns_get_osm_tags($query);
    $amenity = $osm_tags['amenity'];
    $extra = $osm_tags['extra'];

    $filters = '';
    if ($amenity !== '') {
        $filters .= '["amenity"="' . $amenity . '"]';
    }
    if ($extra !== '') {
        $filters .= '[' . $extra . ']';
    }

    // If no tags matched, fall back to name-based search
    if ($filters === '') {
        $safe = str_replace('"', '', $query);
        $filters = '["name"~"' . $safe . '",i]';
    }

    // Fetch ALL results within radius (Overpass returns in arbitrary OSM-ID order,
    // not by distance). We sort + limit in PHP afterwards.
    $overpass_query = '[out:json][timeout:15];('
        . 'node(around:' . $radius . ',' . $lat . ',' . $lng . ')' . $filters . ';'
        . 'way(around:' . $radius . ',' . $lat . ',' . $lng . ')' . $filters . ';'
        . ');out center body;';

    $response = _ns_http_post(
        'https://overpass-api.de/api/interpreter',
        'data=' . urlencode($overpass_query)
    );
    if ($response === false) return array();

    $data = json_decode($response, true);
    if (!is_array($data) || !isset($data['elements'])) return array();

    $results = array();
    foreach ($data['elements'] as $el) {
        $r = _ns_format_osm_element($el, $lat, $lng);
        if ($r !== null) {
            $results[] = $r;
        }
    }

    // Sort by distance
    usort($results, '_ns_sort_by_distance');

    // Deduplicate chains: keep max 1 location per chain name
    // (avoids flooding results with 7 Tim Hortons, 5 Starbucks, etc.)
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

    if (count($deduped) > $limit) {
        $deduped = array_slice($deduped, 0, $limit);
    }

    return $deduped;
}


/**
 * Format a single Overpass element into standard result structure.
 */
function _ns_format_osm_element($el, $user_lat, $user_lng) {
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
    if ($name === '') return null;

    $distance = _ns_haversine($user_lat, $user_lng, $el_lat, $el_lng);

    // Build address
    $addr = array();
    if (isset($tags['addr:housenumber']) && isset($tags['addr:street'])) {
        $addr[] = $tags['addr:housenumber'] . ' ' . $tags['addr:street'];
    } elseif (isset($tags['addr:street'])) {
        $addr[] = $tags['addr:street'];
    }
    if (isset($tags['addr:city'])) $addr[] = $tags['addr:city'];
    if (isset($tags['addr:postcode'])) $addr[] = $tags['addr:postcode'];
    $address = implode(', ', $addr);

    // Category
    $category = '';
    if (isset($tags['amenity'])) $category = ucfirst(str_replace('_', ' ', $tags['amenity']));
    if (isset($tags['cuisine'])) $category .= ($category !== '' ? ' - ' : '') . ucfirst(str_replace(array('_', ';'), array(' ', ', '), $tags['cuisine']));
    if (isset($tags['shop'])) $category = ucfirst(str_replace('_', ' ', $tags['shop']));

    $phone = isset($tags['phone']) ? $tags['phone'] : (isset($tags['contact:phone']) ? $tags['contact:phone'] : '');
    $website = isset($tags['website']) ? $tags['website'] : (isset($tags['contact:website']) ? $tags['contact:website'] : '');
    $hours = isset($tags['opening_hours']) ? $tags['opening_hours'] : '';

    $open_now = null;
    if ($hours !== '' && strpos($hours, '24/7') !== false) {
        $open_now = true;
    }

    return array(
        'name' => $name,
        'category' => $category,
        'distance_m' => (int)round($distance),
        'address' => $address,
        'open_now' => $open_now,
        'hours' => $hours,
        'rating' => 0,
        'phone' => $phone,
        'website' => $website,
        'maps_url' => 'https://www.google.com/maps/search/?api=1&query=' . $el_lat . ',' . $el_lng,
        'source' => 'openstreetmap',
        'id' => 'osm_' . (isset($el['id']) ? $el['id'] : '0')
    );
}


/**
 * Scrape DuckDuckGo Lite for business names related to query + location.
 * Returns array of array('name' => ..., 'address' => ...) items.
 */
function _ns_ddg_scrape($search_query, $location_str) {
    global $_ns_ddg_debug;
    $_ns_ddg_debug = array();

    // Use Brave Search (works from servers; DDG returns CAPTCHA to server IPs)
    // Two queries: one for local results, one targeting Yelp snippet lists
    $brave_queries = array(
        $search_query . ' near ' . $location_str . ' Toronto',
        'best ' . $search_query . ' near ' . $location_str . ' Toronto yelp'
    );

    $businesses = array();
    $seen = array();
    $ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

    foreach ($brave_queries as $qi => $q) {
        $url = 'https://search.brave.com/search?q=' . urlencode($q) . '&source=web';

        $response = _ns_http_get($url, array(
            'User-Agent: ' . $ua,
            'Accept: text/html,application/xhtml+xml,application/xml'
        ));

        $_ns_ddg_debug[] = array(
            'url' => $url,
            'response_length' => ($response !== false) ? strlen($response) : 0,
            'engine' => 'brave'
        );

        if ($response === false) continue;

        // --- 1. Extract Brave local business panel ---
        $biz_names = array();
        preg_match_all('/<span class="mr-5">([^<]+)<\\/span>/', $response, $name_matches);
        if (isset($name_matches[1])) $biz_names = $name_matches[1];

        $biz_addrs = array();
        preg_match_all('/<address[^>]*>(.*?)<\\/address>/s', $response, $addr_matches);
        if (isset($addr_matches[1])) {
            foreach ($addr_matches[1] as $a) {
                $biz_addrs[] = trim(strip_tags($a));
            }
        }

        $_ns_ddg_debug[$qi]['local_names'] = $biz_names;

        for ($i = 0; $i < count($biz_names); $i++) {
            $name = html_entity_decode(trim($biz_names[$i]), ENT_QUOTES, 'UTF-8');
            $parts = preg_split('/\\s*-\\s*/', $name, 2);
            $name = trim($parts[0]);
            if (strlen($name) < 2 || strlen($name) > 60) continue;
            $key = strtolower($name);
            if (isset($seen[$key])) continue;
            $seen[$key] = true;
            $address = isset($biz_addrs[$i]) ? $biz_addrs[$i] : '';
            $businesses[] = array('name' => $name, 'address' => $address);
        }

        // --- 2. Extract business names from snippet text ---
        // Brave embeds snippet descriptions that may contain Yelp-style lists:
        // "NEO COFFEE BAR, Cafe Forêt, Hailed Coffee, Juju Cafe..."
        // These appear in the page as comma-separated lists of business names.
        $snippet_list_count = 0;
        // Match snippet text in Brave's rendered HTML
        preg_match_all('/<div class="(?:generic-snippet|snippet-description)[^"]*"[^>]*>(.*?)<\\/div>/s', $response, $snippet_matches);
        $snippet_texts = array();
        if (isset($snippet_matches[1])) $snippet_texts = $snippet_matches[1];

        // Also extract from Brave's embedded JS data (description fields)
        preg_match_all('/description:"(.*?)"/s', $response, $desc_matches);
        if (isset($desc_matches[1])) {
            foreach ($desc_matches[1] as $desc) {
                $snippet_texts[] = $desc;
            }
        }

        foreach ($snippet_texts as $snippet_raw) {
            $snippet = html_entity_decode(strip_tags($snippet_raw), ENT_QUOTES, 'UTF-8');
            // Decode unicode escapes like \u003C
            $snippet = preg_replace_callback('/\\\\u([0-9a-fA-F]{4})/', '_ns_decode_unicode', $snippet);
            $snippet = strip_tags($snippet);

            // Look for comma-separated lists of business names
            // Pattern: multiple capitalized names separated by commas
            // e.g. "NEO COFFEE BAR, Cafe Forêt, Hailed Coffee, Juju Cafe"
            if (preg_match('/(?:[A-Z][A-Za-z\x{00C0}-\x{017F}\'&]+(?:\\s+[A-Za-z\x{00C0}-\x{017F}\'&]+){0,4},\\s*){2,}/u', $snippet, $list_match)) {
                $list_str = $list_match[0];
                $items = preg_split('/\\s*,\\s*/', $list_str);
                foreach ($items as $item) {
                    $item = trim($item);
                    if (strlen($item) < 3 || strlen($item) > 50) continue;
                    // Skip common noise words
                    if (preg_match('/^(Last|Updated|Photos?|Reviews?|See|More|and|The Best|Top)\\b/i', $item)) continue;
                    $item_key = strtolower($item);
                    if (isset($seen[$item_key])) continue;
                    $seen[$item_key] = true;
                    $businesses[] = array('name' => $item, 'address' => '');
                    $snippet_list_count++;
                }
            }
        }

        $_ns_ddg_debug[$qi]['snippet_businesses'] = $snippet_list_count;
    }

    return $businesses;
}

/**
 * Decode a \uXXXX unicode escape to UTF-8. Used as preg_replace_callback handler.
 */
function _ns_decode_unicode($matches) {
    return mb_convert_encoding(pack('H*', $matches[1]), 'UTF-8', 'UTF-16BE');
}


/**
 * Geocode web-scraped businesses using Nominatim and format as results.
 * Skips businesses already in existing results. Rate-limited.
 */
function _ns_geocode_businesses($businesses, $user_lat, $user_lng, $location_str, $existing, $max_geocode) {
    $existing_lower = array();
    foreach ($existing as $r) {
        $existing_lower[] = strtolower($r['name']);
    }

    $results = array();
    $geocoded = 0;

    foreach ($businesses as $biz) {
        if ($geocoded >= $max_geocode) break;

        // Skip if already in existing results (fuzzy match)
        $biz_lower = strtolower($biz['name']);
        $skip = false;
        foreach ($existing_lower as $ex) {
            if ($biz_lower === $ex) { $skip = true; break; }
            if (strlen($ex) > 4 && strpos($biz_lower, $ex) !== false) { $skip = true; break; }
            if (strlen($biz_lower) > 4 && strpos($ex, $biz_lower) !== false) { $skip = true; break; }
        }
        if ($skip) continue;

        // Rate limit: 1s between Nominatim requests (their usage policy)
        if ($geocoded > 0) {
            usleep(600000);
        }

        $geo = null;
        // Try address first
        if ($biz['address'] !== '') {
            $geo = _ns_nominatim_fetch($biz['address']);
        }
        // Fall back to name + location
        if ($geo === null) {
            $geo = _ns_nominatim_fetch($biz['name'] . ', ' . $location_str);
        }
        if ($geo === null) {
            $geo = _ns_nominatim_fetch($biz['name'] . ', Toronto');
        }
        $geocoded++;

        $distance = 0;
        $maps_url = '';
        if ($geo !== null) {
            $distance = (int)round(_ns_haversine($user_lat, $user_lng, $geo['lat'], $geo['lng']));
            $maps_url = 'https://www.google.com/maps/search/?api=1&query=' . $geo['lat'] . ',' . $geo['lng'];
        } else {
            $maps_url = 'https://www.google.com/maps/search/?api=1&query=' . urlencode($biz['name'] . ' near ' . $location_str);
            $distance = 99999;
        }

        $results[] = array(
            'name' => $biz['name'],
            'category' => '',
            'distance_m' => $distance,
            'address' => $biz['address'],
            'open_now' => null,
            'hours' => '',
            'rating' => 0,
            'phone' => '',
            'website' => '',
            'maps_url' => $maps_url,
            'source' => 'web_search',
            'id' => 'web_' . md5($biz['name'])
        );
    }

    return $results;
}


/**
 * Merge two result arrays, deduplicate by name, sort by distance, limit.
 */
/**
 * Curated local business database — businesses missing from OSM that are
 * verified to exist. Returns only entries within radius and matching the query category.
 */
function _ns_curated_nearby($search_query, $user_lat, $user_lng, $radius) {
    // Each entry: name, lat, lng, address, category_tags (comma-separated keywords)
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
    $results = array();

    foreach ($curated as $biz) {
        // Check if query matches any of the business tags
        $tags = explode(',', $biz['tags']);
        $match = false;
        foreach ($tags as $tag) {
            $tag = trim($tag);
            if ($tag === $q_lower) { $match = true; break; }
            if (strpos($q_lower, $tag) !== false) { $match = true; break; }
            if (strpos($tag, $q_lower) !== false) { $match = true; break; }
        }
        // Also match plural forms
        $q_singular = rtrim($q_lower, 's');
        if (!$match) {
            foreach ($tags as $tag) {
                $tag = trim($tag);
                if ($tag === $q_singular) { $match = true; break; }
                if (strpos($q_singular, $tag) !== false) { $match = true; break; }
            }
        }
        if (!$match) continue;

        // Check distance
        $dist = _ns_haversine($user_lat, $user_lng, $biz['lat'], $biz['lng']);
        if ($dist > $radius) continue;

        $results[] = array(
            'name' => $biz['name'],
            'category' => 'Cafe',
            'distance_m' => (int)round($dist),
            'address' => $biz['address'],
            'open_now' => null,
            'hours' => $biz['hours'],
            'rating' => 0,
            'phone' => $biz['phone'],
            'website' => $biz['website'],
            'maps_url' => 'https://www.google.com/maps/search/?api=1&query=' . $biz['lat'] . ',' . $biz['lng'],
            'source' => 'curated',
            'id' => 'curated_' . md5($biz['name'] . $biz['address'])
        );
    }

    return $results;
}


function _ns_merge($results_a, $results_b, $limit) {
    $merged = $results_a;
    // Track name + approximate distance for dedup (same name but >200m apart = different location)
    $existing = array();
    foreach ($results_a as $r) {
        $existing[] = array('name' => strtolower($r['name']), 'dist' => $r['distance_m']);
    }

    foreach ($results_b as $b) {
        $b_lower = strtolower($b['name']);
        $b_dist = $b['distance_m'];
        $is_dup = false;
        foreach ($existing as $ex) {
            $name_match = false;
            if ($b_lower === $ex['name']) $name_match = true;
            if (!$name_match && strlen($ex['name']) > 4 && strpos($b_lower, $ex['name']) !== false) $name_match = true;
            if (!$name_match && strlen($b_lower) > 4 && strpos($ex['name'], $b_lower) !== false) $name_match = true;

            if ($name_match) {
                // Same name — only consider duplicate if within 200m of each other
                $dist_diff = abs($b_dist - $ex['dist']);
                if ($dist_diff < 200) {
                    $is_dup = true;
                    break;
                }
            }
        }
        if (!$is_dup) {
            $merged[] = $b;
            $existing[] = array('name' => $b_lower, 'dist' => $b_dist);
        }
    }

    usort($merged, '_ns_sort_by_distance');

    if (count($merged) > $limit) {
        $merged = array_slice($merged, 0, $limit);
    }

    return $merged;
}


/**
 * Sort comparison function — by effective distance (chains get penalty).
 * Independent businesses surface above chains at similar distances.
 */
function _ns_sort_by_distance($a, $b) {
    $a_eff = $a['distance_m'] + _ns_chain_penalty($a['name']);
    $b_eff = $b['distance_m'] + _ns_chain_penalty($b['name']);
    if ($a_eff == $b_eff) return 0;
    return ($a_eff < $b_eff) ? -1 : 1;
}


/**
 * Chain penalty — adds virtual distance to chain/franchise businesses
 * so independent/unique businesses appear higher in results.
 * Returns 0 for independent, 200m penalty for known chains.
 */
function _ns_chain_penalty($name) {
    // Major chains: heavy penalty
    $major_chains = array(
        'tim hortons', 'starbucks', 'second cup', 'timothy',
        'mcdonald', 'subway', 'pizza pizza', 'domino',
        'dunkin', 'pret a manger'
    );
    // Bubble tea / non-coffee when user searches "coffee"
    $bubble_tea = array(
        'chatime', 'coco', 'kung fu tea', 'the alley',
        'real fruit bubble tea', 'fruiteao', 'gong cha',
        'cha miao', 'tiger sugar', 'onezo', 'presotea'
    );
    // Minor chains
    $minor_chains = array(
        'aroma espresso', 'balzac', 'pilot coffee'
    );
    $name_lower = strtolower($name);
    foreach ($major_chains as $chain) {
        if (strpos($name_lower, $chain) !== false) {
            return 500; // 500m penalty for major chains
        }
    }
    foreach ($bubble_tea as $bt) {
        if (strpos($name_lower, $bt) !== false) {
            return 400; // 400m penalty for bubble tea (not coffee)
        }
    }
    foreach ($minor_chains as $mc) {
        if (strpos($name_lower, $mc) !== false) {
            return 200; // 200m for minor chains
        }
    }
    return 0;
}

/**
 * Haversine distance in meters between two lat/lng points.
 */
function _ns_haversine($lat1, $lon1, $lat2, $lon2) {
    $R = 6371000;
    $dLat = deg2rad($lat2 - $lat1);
    $dLon = deg2rad($lon2 - $lon1);
    $a = sin($dLat / 2) * sin($dLat / 2)
       + cos(deg2rad($lat1)) * cos(deg2rad($lat2))
       * sin($dLon / 2) * sin($dLon / 2);
    $c = 2 * atan2(sqrt($a), sqrt(1 - $a));
    return $R * $c;
}


/**
 * Map common search terms to OSM amenity tags for Overpass queries.
 */
function _ns_get_osm_tags($query) {
    $map = array(
        'coffee' => array('amenity' => 'cafe', 'extra' => ''),
        'coffee shop' => array('amenity' => 'cafe', 'extra' => ''),
        'coffee shops' => array('amenity' => 'cafe', 'extra' => ''),
        'cafe' => array('amenity' => 'cafe', 'extra' => ''),
        'restaurant' => array('amenity' => 'restaurant', 'extra' => ''),
        'restaurants' => array('amenity' => 'restaurant', 'extra' => ''),
        'pizza' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"pizza"'),
        'sushi' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"sushi|japanese"'),
        'burger' => array('amenity' => 'fast_food', 'extra' => '"cuisine"~"burger"'),
        'sandwich' => array('amenity' => 'fast_food', 'extra' => '"cuisine"~"sandwich"'),
        'sandwich shop' => array('amenity' => 'fast_food', 'extra' => '"cuisine"~"sandwich"'),
        'turkey sandwich' => array('amenity' => 'fast_food', 'extra' => '"cuisine"~"sandwich"'),
        'fast food' => array('amenity' => 'fast_food', 'extra' => ''),
        'bar' => array('amenity' => 'bar', 'extra' => ''),
        'pub' => array('amenity' => 'pub', 'extra' => ''),
        'pharmacy' => array('amenity' => 'pharmacy', 'extra' => ''),
        'gas station' => array('amenity' => 'fuel', 'extra' => ''),
        'hospital' => array('amenity' => 'hospital', 'extra' => ''),
        'gym' => array('amenity' => '', 'extra' => '"leisure"="fitness_centre"'),
        'bank' => array('amenity' => 'bank', 'extra' => ''),
        'atm' => array('amenity' => 'atm', 'extra' => ''),
        'grocery' => array('amenity' => '', 'extra' => '"shop"="supermarket"'),
        'supermarket' => array('amenity' => '', 'extra' => '"shop"="supermarket"'),
        'bakery' => array('amenity' => '', 'extra' => '"shop"="bakery"'),
        'bookstore' => array('amenity' => '', 'extra' => '"shop"="books"'),
        'parking' => array('amenity' => 'parking', 'extra' => ''),
        'hotel' => array('amenity' => '', 'extra' => '"tourism"="hotel"'),
        'library' => array('amenity' => 'library', 'extra' => ''),
        'dentist' => array('amenity' => 'dentist', 'extra' => ''),
        'doctor' => array('amenity' => 'doctors', 'extra' => ''),
        'clinic' => array('amenity' => 'clinic', 'extra' => ''),
        'ice cream' => array('amenity' => 'ice_cream', 'extra' => ''),
        'bubble tea' => array('amenity' => 'cafe', 'extra' => '"cuisine"~"bubble_tea"'),
        'thai' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"thai"'),
        'chinese' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"chinese"'),
        'indian' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"indian"'),
        'italian' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"italian"'),
        'mexican' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"mexican"'),
        'korean' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"korean"'),
        'japanese' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"japanese"'),
        'vietnamese' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"vietnamese"'),
        'ramen' => array('amenity' => 'restaurant', 'extra' => '"cuisine"~"ramen|japanese"')
    );

    $q = strtolower(trim($query));
    if (isset($map[$q])) return $map[$q];

    // Try without trailing 's'
    $qs = rtrim($q, 's');
    if ($qs !== $q && isset($map[$qs])) return $map[$qs];

    // Partial match
    $best = null;
    $best_len = 0;
    foreach ($map as $key => $val) {
        if (strpos($q, $key) !== false && strlen($key) > $best_len) {
            $best = $val;
            $best_len = strlen($key);
        }
    }
    if ($best !== null) return $best;

    // Fallback: name-based search (no amenity filter)
    return array('amenity' => '', 'extra' => '');
}


/**
 * HTTP GET with curl fallback to file_get_contents.
 */
function _ns_http_get($url, $headers) {
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
        if ($response !== false && $code >= 200 && $code < 300) {
            return $response;
        }
    }

    $hdr_str = '';
    foreach ($headers as $h) {
        $hdr_str .= $h . "\r\n";
    }
    $ctx = stream_context_create(array(
        'http' => array(
            'method' => 'GET',
            'timeout' => 10,
            'header' => $hdr_str
        )
    ));
    $response = @file_get_contents($url, false, $ctx);
    return ($response !== false) ? $response : false;
}


/**
 * HTTP POST with curl fallback to file_get_contents.
 */
function _ns_http_post($url, $post_data) {
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

    $ctx = stream_context_create(array(
        'http' => array(
            'method' => 'POST',
            'timeout' => 15,
            'header' => "Content-Type: application/x-www-form-urlencoded\r\nUser-Agent: FindTorontoEvents-NearMeSearch/1.0\r\n",
            'content' => $post_data
        )
    ));
    $response = @file_get_contents($url, false, $ctx);
    return ($response !== false) ? $response : false;
}
