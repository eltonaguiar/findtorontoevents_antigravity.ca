<?php
/**
 * resolve_link.php — Resolve aggregator URLs (AllEvents.in, etc.) to their original source
 *
 * Takes an event URL from an aggregator site and follows redirects / scrapes the page
 * to find the original event source (Eventbrite, Meetup, Ticketmaster, etc.)
 *
 * PHP 5.2 compatible — no ?:, ??, [], closures, __DIR__, http_response_code()
 *
 * Usage:
 *   GET  /api/events/resolve_link.php?url=https://allevents.in/toronto/some-event/12345
 *   POST /api/events/resolve_link.php  with JSON body { "url": "..." }
 *   POST /api/events/resolve_link.php  with JSON body { "urls": ["...", "..."] } (batch)
 *
 * Response:
 *   { "ok": true, "original_url": "...", "resolved_url": "https://eventbrite.ca/...", "source": "Eventbrite", ... }
 *   or for batch:
 *   { "ok": true, "results": [ { "original_url": "...", "resolved_url": "...", "source": "..." }, ... ] }
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

$out = array('ok' => false);

/* ── Get URL(s) from request ── */
$urls = array();

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    $u = isset($_GET['url']) ? trim($_GET['url']) : '';
    if ($u !== '') {
        $urls = array($u);
    }
} else if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);
    if ($data && isset($data['url'])) {
        $urls = array(trim($data['url']));
    } else if ($data && isset($data['urls']) && is_array($data['urls'])) {
        $urls = $data['urls'];
    }
}

if (count($urls) === 0) {
    $out['error'] = 'Missing url parameter. Use ?url=... or POST {"url":"..."} or {"urls":["..."]}';
    echo json_encode($out);
    exit;
}

/* ── Limit batch size ── */
if (count($urls) > 20) {
    $out['error'] = 'Maximum 20 URLs per batch request';
    echo json_encode($out);
    exit;
}

/* ────────────────────────────────────────────────────────────────────────
 * Core resolution functions
 * ──────────────────────────────────────────────────────────────────────── */

/**
 * Fetch a URL with cURL, following up to $maxRedirects redirects.
 * Returns array('final_url' => string, 'body' => string, 'status' => int)
 */
function rl_fetch($url, $maxRedirects) {
    if (!function_exists('curl_init')) {
        return array('final_url' => $url, 'body' => '', 'status' => 0, 'error' => 'cURL not available');
    }
    $ch = curl_init($url);
    if (!$ch) {
        return array('final_url' => $url, 'body' => '', 'status' => 0, 'error' => 'cURL init failed');
    }
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_MAXREDIRS, $maxRedirects);
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 8);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
    curl_setopt($ch, CURLOPT_HTTPHEADER, array(
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language: en-US,en;q=0.5'
    ));

    $body = curl_exec($ch);
    $status = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $finalUrl = curl_getinfo($ch, CURLINFO_EFFECTIVE_URL);
    $err = curl_error($ch);
    curl_close($ch);

    if ($body === false) {
        $body = '';
    }

    $result = array('final_url' => $finalUrl, 'body' => $body, 'status' => $status);
    if ($err) {
        $result['curl_error'] = $err;
    }
    return $result;
}

/**
 * Known event source patterns.
 * Each entry: array('pattern' => regex, 'name' => string)
 */
function rl_get_source_patterns() {
    /* Each 'domain' is used both for href extraction and for URL identification.
       Regex-safe domain fragment (dots escaped, no delimiters). */
    return array(
        array('domain' => 'eventbrite\\.\\w+', 'name' => 'Eventbrite'),
        array('domain' => 'meetup\\.com', 'name' => 'Meetup'),
        array('domain' => 'ticketmaster\\.\\w+', 'name' => 'Ticketmaster'),
        array('domain' => 'universe\\.com', 'name' => 'Universe'),
        array('domain' => 'showpass\\.com', 'name' => 'Showpass'),
        array('domain' => 'dice\\.fm', 'name' => 'Dice.fm'),
        array('domain' => 'partiful\\.com', 'name' => 'Partiful'),
        array('domain' => 'lu\\.ma', 'name' => 'Luma'),
        array('domain' => 'humanitix\\.com', 'name' => 'Humanitix'),
        array('domain' => 'zeffy\\.com', 'name' => 'Zeffy'),
        array('domain' => 'tickettailor\\.com', 'name' => 'TicketTailor'),
        array('domain' => 'fevr\\.com', 'name' => 'Fevr'),
        array('domain' => 'songkick\\.com', 'name' => 'Songkick'),
    );
}

/**
 * Extract the original event source URL from an HTML page.
 * Searches for href links matching known ticketing/event platforms.
 * Also checks JSON-LD data and meta tags for ticket/registration URLs.
 */
function rl_extract_source_url($html) {
    $patterns = rl_get_source_patterns();

    /* ── 1. Check href links matching known event platforms ── */
    for ($i = 0; $i < count($patterns); $i++) {
        $d = $patterns[$i]['domain'];
        $regex = '#href\s*=\s*["\'](https?://(?:www\.)?' . $d . '/[^"\'\\s]+)["\']#i';
        if (preg_match($regex, $html, $m)) {
            return array('url' => rl_clean_url($m[1]), 'source' => $patterns[$i]['name'], 'method' => 'href_link');
        }
    }

    /* ── 2. Check JSON-LD structured data ── */
    if (preg_match_all('#<script[^>]*type\s*=\s*["\']application/ld\\+json["\'][^>]*>(.*?)</script>#si', $html, $jsonMatches)) {
        for ($j = 0; $j < count($jsonMatches[1]); $j++) {
            $jsonStr = $jsonMatches[1][$j];
            for ($i = 0; $i < count($patterns); $i++) {
                $d = $patterns[$i]['domain'];
                if (preg_match('#https?://(?:www\.)?' . $d . '/[^"\'\\s]+#i', $jsonStr, $m2)) {
                    return array('url' => rl_clean_url($m2[0]), 'source' => $patterns[$i]['name'], 'method' => 'json_ld');
                }
            }
            /* Check for ticket_url or registration_url fields */
            if (preg_match('#"(?:ticket_url|registration_url|ticketUrl)"\s*:\s*"(https?://[^"]+)"#', $jsonStr, $m3)) {
                $ticketUrl = rl_clean_url($m3[1]);
                $src = rl_identify_source($ticketUrl);
                return array('url' => $ticketUrl, 'source' => $src, 'method' => 'json_ld_ticket_url');
            }
        }
    }

    /* ── 3. Check meta tags (og:url, canonical) for non-aggregator sources ── */
    if (preg_match('#<meta[^>]+property\s*=\s*["\']og:url["\'][^>]+content\s*=\s*["\']([^"\']+)["\']#i', $html, $m4)) {
        $ogUrl = rl_clean_url($m4[1]);
        if (strpos($ogUrl, 'allevents.in') === false) {
            $src = rl_identify_source($ogUrl);
            if ($src !== 'Unknown') {
                return array('url' => $ogUrl, 'source' => $src, 'method' => 'og_url');
            }
        }
    }
    if (preg_match('#<link[^>]+rel\s*=\s*["\']canonical["\'][^>]+href\s*=\s*["\']([^"\']+)["\']#i', $html, $m5)) {
        $canUrl = rl_clean_url($m5[1]);
        if (strpos($canUrl, 'allevents.in') === false) {
            $src = rl_identify_source($canUrl);
            if ($src !== 'Unknown') {
                return array('url' => $canUrl, 'source' => $src, 'method' => 'canonical');
            }
        }
    }

    /* ── 4. Check "Buy Tickets" / "Register" / "Get Tickets" button links ── */
    if (preg_match_all('#href\s*=\s*["\'](https?://[^"\']+)["\'][^>]*>(?:[^<]*(?:ticket|register|rsvp|book|buy)[^<]*)#i', $html, $btnMatches, PREG_SET_ORDER)) {
        for ($i = 0; $i < count($btnMatches); $i++) {
            $btnUrl = rl_clean_url($btnMatches[$i][1]);
            if (strpos($btnUrl, 'allevents.in') === false) {
                $src = rl_identify_source($btnUrl);
                if ($src !== 'Unknown') {
                    return array('url' => $btnUrl, 'source' => $src, 'method' => 'button_link');
                }
            }
        }
    }

    /* ── 5. Fallback: any external link that matches a known source ── */
    if (preg_match_all('#href\s*=\s*["\'](https?://[^"\']+)["\']#i', $html, $allLinks)) {
        for ($i = 0; $i < count($allLinks[1]); $i++) {
            $linkUrl = rl_clean_url($allLinks[1][$i]);
            if (strpos($linkUrl, 'allevents.in') !== false) continue;
            $src = rl_identify_source($linkUrl);
            if ($src !== 'Unknown') {
                return array('url' => $linkUrl, 'source' => $src, 'method' => 'page_link');
            }
        }
    }

    return null;
}

/**
 * Identify which platform a URL belongs to.
 */
function rl_identify_source($url) {
    $patterns = rl_get_source_patterns();
    for ($i = 0; $i < count($patterns); $i++) {
        $d = $patterns[$i]['domain'];
        if (preg_match('#(?:www\.)?' . $d . '#i', $url)) {
            return $patterns[$i]['name'];
        }
    }
    return 'Unknown';
}

/**
 * Clean tracking parameters from a URL.
 */
function rl_clean_url($url) {
    $url = trim($url);

    /* ── Unwrap affiliate/tracking redirect wrappers ── */
    /* Pattern: ...pxf.io/...?u=https%3A%2F%2Fwww.eventbrite.com%2F... */
    if (preg_match('#[?&]u=(https?%3A%2F%2F[^&]+)#i', $url, $wrap)) {
        $inner = urldecode($wrap[1]);
        if (strlen($inner) > 20) {
            $url = $inner;
        }
    }
    /* Pattern: ...redirect?url=https://... */
    if (preg_match('#[?&](?:url|dest|redirect|target|goto)=(https?[^&]+)#i', $url, $wrap2)) {
        $inner2 = urldecode($wrap2[1]);
        if (strlen($inner2) > 20) {
            $url = $inner2;
        }
    }

    /* Remove common tracking params */
    $url = preg_replace('#[&?](?:utm_[a-z]+|ref|aff|fbclid|gclid|mc_eid|source|medium|campaign)=[^&]*#', '', $url);
    /* Clean up leftover ? or & */
    $url = preg_replace('#\?&#', '?', $url);
    $url = preg_replace('#\?$#', '', $url);
    return $url;
}

/**
 * Resolve a single URL. Returns an associative array with results.
 */
function rl_resolve_single($url) {
    $result = array(
        'original_url' => $url,
        'resolved_url' => null,
        'source' => null,
        'method' => null,
        'final_url' => null,
        'error' => null
    );

    /* Validate URL */
    if (strpos($url, 'http') !== 0) {
        $result['error'] = 'Invalid URL (must start with http)';
        return $result;
    }

    /* ── Step 1: Follow redirects to get the final URL ── */
    $fetch = rl_fetch($url, 10);
    $result['final_url'] = $fetch['final_url'];

    /* If the redirect itself landed on a known source, that's our answer */
    if ($fetch['final_url'] !== $url) {
        $redirectSource = rl_identify_source($fetch['final_url']);
        if ($redirectSource !== 'Unknown') {
            $result['resolved_url'] = rl_clean_url($fetch['final_url']);
            $result['source'] = $redirectSource;
            $result['method'] = 'redirect';
            return $result;
        }
    }

    /* ── Step 2: Parse the page HTML for external event links ── */
    if ($fetch['body'] !== '') {
        $extracted = rl_extract_source_url($fetch['body']);
        if ($extracted) {
            $result['resolved_url'] = $extracted['url'];
            $result['source'] = $extracted['source'];
            $result['method'] = $extracted['method'];
            return $result;
        }
    }

    /* ── Step 3: Could not resolve ── */
    if ($fetch['status'] === 0 && isset($fetch['curl_error'])) {
        $result['error'] = 'Fetch failed: ' . $fetch['curl_error'];
    } else if ($fetch['status'] !== 200) {
        $result['error'] = 'HTTP ' . $fetch['status'];
    } else {
        $result['error'] = 'No external event source found on page';
    }

    return $result;
}

/* ────────────────────────────────────────────────────────────────────────
 * Main: resolve one or more URLs
 * ──────────────────────────────────────────────────────────────────────── */

if (count($urls) === 1) {
    /* Single URL mode */
    $r = rl_resolve_single($urls[0]);
    $out['ok'] = ($r['resolved_url'] !== null);
    foreach ($r as $k => $v) {
        $out[$k] = $v;
    }
} else {
    /* Batch mode */
    $results = array();
    for ($i = 0; $i < count($urls); $i++) {
        $results[] = rl_resolve_single(trim($urls[$i]));
    }
    $out['ok'] = true;
    $out['results'] = $results;
    $resolved = 0;
    for ($i = 0; $i < count($results); $i++) {
        if ($results[$i]['resolved_url'] !== null) $resolved++;
    }
    $out['resolved_count'] = $resolved;
    $out['total'] = count($results);
}

echo json_encode($out);
?>
