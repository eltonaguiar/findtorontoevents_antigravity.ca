<?php
/**
 * Sports Odds Fetcher + Cache — The Odds API integration
 * PHP 5.2 compatible (no short arrays, no http_response_code, no spread operator)
 *
 * Data source: The Odds API (free tier: 500 credits/month)
 * Regions: us, us2 (covers bet365, FanDuel, DraftKings, BetMGM, PointsBet, Caesars)
 *
 * Actions:
 *   ?action=sports                        — List active in-season sports (free, 0 credits)
 *   ?action=fetch&key=livetrader2026      — Fetch odds from The Odds API, cache in DB
 *   ?action=get[&sport=X][&hours=48]      — Return cached odds grouped by event
 *   ?action=credit_usage                  — Monthly API credit usage stats
 */

require_once dirname(__FILE__) . '/sports_db_connect.php';
require_once dirname(__FILE__) . '/sports_schema.php';
require_once dirname(__FILE__) . '/odds_scraper.php';

// ────────────────────────────────────────────────────────────
//  Auto-create tables (centralized in sports_schema.php)
// ────────────────────────────────────────────────────────────
_sb_ensure_schema($conn);

// ────────────────────────────────────────────────────────────
//  Constants
// ────────────────────────────────────────────────────────────

$ADMIN_KEY = isset($SPORTS_ADMIN_KEY) ? $SPORTS_ADMIN_KEY : 'livetrader2026';
$API_BASE  = 'https://api.the-odds-api.com/v4';

$TARGET_SPORTS = array(
    'icehockey_nhl'          => 'NHL',
    'basketball_nba'         => 'NBA',
    'americanfootball_nfl'   => 'NFL',
    'baseball_mlb'           => 'MLB',
    'americanfootball_cfl'   => 'CFL',
    'soccer_usa_mls'         => 'MLS',
    'americanfootball_ncaaf' => 'NCAAF',
    'basketball_ncaab'       => 'NCAAB'
);

$BOOK_DISPLAY = array(
    'fanduel'        => 'FanDuel',
    'draftkings'     => 'DraftKings',
    'betmgm'         => 'BetMGM',
    'bet365'         => 'bet365',
    'pointsbetus'    => 'PointsBet',
    'williamhill_us' => 'Caesars',
    'bovada'         => 'Bovada',
    'betonlineag'    => 'BetOnline',
    'betrivers'      => 'BetRivers',
    'unibet_us'      => 'Unibet',
    'mybookieag'     => 'MyBookie',
    'superbook'      => 'SuperBook',
    'lowvig'         => 'LowVig',
    'betus'          => 'BetUS',
    'pinnacle'       => 'Pinnacle',
    'barstool'       => 'ESPN BET',
    'espnbet'        => 'ESPN BET',
    'fliff'          => 'Fliff',
    'hardrockbet'    => 'Hard Rock',
    'fanatics'       => 'Fanatics'
);

$CANADIAN_BOOKS = array('bet365', 'fanduel', 'draftkings', 'betmgm', 'pointsbetus', 'williamhill_us', 'betrivers', 'espnbet', 'fanatics');

// ────────────────────────────────────────────────────────────
//  HTTP helper (with response headers capture for credit tracking)
// ────────────────────────────────────────────────────────────

// Global var for header capture (PHP 5.2 — no closures)
$_so_captured_headers = array();

function _so_curl_header_callback($ch, $header) {
    global $_so_captured_headers;
    $parts = explode(':', $header, 2);
    if (count($parts) === 2) {
        $_so_captured_headers[strtolower(trim($parts[0]))] = trim($parts[1]);
    }
    return strlen($header);
}

function _so_http_get($url, &$resp_headers) {
    global $_so_captured_headers;
    $resp_headers = array();
    $_so_captured_headers = array();

    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 30);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array(
            'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept: application/json'
        ));
        curl_setopt($ch, CURLOPT_HEADERFUNCTION, '_so_curl_header_callback');
        $body = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        $resp_headers = $_so_captured_headers;
        if ($body !== false && $code >= 200 && $code < 300) {
            return $body;
        }
        if ($body !== false && $code == 429) {
            return json_encode(array('error' => 'Rate limited by The Odds API'));
        }
        return null;
    }

    // Fallback
    $ctx = stream_context_create(array(
        'http' => array(
            'method'  => 'GET',
            'timeout' => 30,
            'header'  => "User-Agent: Mozilla/5.0\r\nAccept: application/json\r\n"
        ),
        'ssl' => array('verify_peer' => false)
    ));
    $body = @file_get_contents($url, false, $ctx);
    if ($body === false) return null;
    // Parse $http_response_header if available
    if (isset($http_response_header) && is_array($http_response_header)) {
        foreach ($http_response_header as $h) {
            $parts = explode(':', $h, 2);
            if (count($parts) === 2) {
                $resp_headers[strtolower(trim($parts[0]))] = trim($parts[1]);
            }
        }
    }
    return $body;
}

function _so_http_get_simple($url) {
    $h = array();
    return _so_http_get($url, $h);
}

// ────────────────────────────────────────────────────────────
//  Helper: UTC ISO 8601 → MySQL DATETIME
// ────────────────────────────────────────────────────────────

function _so_iso_to_mysql($iso) {
    // "2026-02-10T20:00:00Z" → "2026-02-10 20:00:00"
    $t = strtotime($iso);
    if ($t === false) return '2026-01-01 00:00:00';
    return gmdate('Y-m-d H:i:s', $t);
}

// ────────────────────────────────────────────────────────────
//  Helper: get bookmaker display name
// ────────────────────────────────────────────────────────────

function _so_book_name($key) {
    global $BOOK_DISPLAY;
    if (isset($BOOK_DISPLAY[$key])) return $BOOK_DISPLAY[$key];
    return ucfirst($key);
}

function _so_is_canadian_book($key) {
    global $CANADIAN_BOOKS;
    return in_array($key, $CANADIAN_BOOKS);
}

// ────────────────────────────────────────────────────────────
//  Action routing
// ────────────────────────────────────────────────────────────

$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'get';

if ($action === 'sports') {
    _so_action_sports($conn);
} elseif ($action === 'fetch') {
    _so_action_fetch($conn);
} elseif ($action === 'get') {
    _so_action_get($conn);
} elseif ($action === 'credit_usage') {
    _so_action_credit_usage($conn);
} elseif ($action === 'clv') {
    _so_action_clv($conn);
} else {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

$conn->close();
exit;

// ════════════════════════════════════════════════════════════
//  ACTION: sports — List active in-season sports (free, 0 credits)
// ════════════════════════════════════════════════════════════

function _so_action_sports($conn) {
    global $API_BASE, $THE_ODDS_API_KEY, $TARGET_SPORTS;

    // If no API key configured, return target sports list as fallback
    if (empty($THE_ODDS_API_KEY) || $THE_ODDS_API_KEY === 'YOUR_KEY_HERE') {
        $fallback = array();
        $titles = array(
            'icehockey_nhl'          => 'NHL',
            'basketball_nba'         => 'NBA',
            'americanfootball_nfl'   => 'NFL',
            'baseball_mlb'           => 'MLB',
            'americanfootball_cfl'   => 'CFL',
            'soccer_usa_mls'         => 'MLS',
            'americanfootball_ncaaf' => 'NCAA Football',
            'basketball_ncaab'       => 'NCAA Basketball'
        );
        foreach ($TARGET_SPORTS as $key => $short) {
            $fallback[] = array(
                'key'         => $key,
                'title'       => isset($titles[$key]) ? $titles[$key] : $key,
                'short_name'  => $short,
                'description' => '',
                'active'      => false
            );
        }
        echo json_encode(array(
            'ok'            => true,
            'active_sports' => $fallback,
            'count'         => 0,
            'all_target'    => count($TARGET_SPORTS),
            'note'          => 'API key not configured. Sign up at https://the-odds-api.com'
        ));
        return;
    }

    $url = $API_BASE . '/sports/?apiKey=' . $THE_ODDS_API_KEY;
    $body = _so_http_get_simple($url);

    if ($body === null) {
        header('HTTP/1.0 502 Bad Gateway');
        echo json_encode(array('ok' => false, 'error' => 'Failed to fetch sports list from The Odds API'));
        return;
    }

    $all_sports = json_decode($body, true);
    if (!is_array($all_sports)) {
        header('HTTP/1.0 502 Bad Gateway');
        echo json_encode(array('ok' => false, 'error' => 'Invalid response from The Odds API'));
        return;
    }

    $active = array();
    foreach ($all_sports as $s) {
        $key = isset($s['key']) ? $s['key'] : '';
        if (isset($TARGET_SPORTS[$key]) && isset($s['active']) && $s['active']) {
            $active[] = array(
                'key'         => $key,
                'title'       => isset($s['title']) ? $s['title'] : $key,
                'short_name'  => $TARGET_SPORTS[$key],
                'description' => isset($s['description']) ? $s['description'] : '',
                'active'      => true
            );
        }
    }

    echo json_encode(array(
        'ok'            => true,
        'active_sports' => $active,
        'count'         => count($active),
        'all_target'    => count($TARGET_SPORTS)
    ));
}

// ════════════════════════════════════════════════════════════
//  ACTION: fetch — Pull odds from The Odds API and cache in DB
// ════════════════════════════════════════════════════════════

function _so_action_fetch($conn) {
    global $API_BASE, $THE_ODDS_API_KEY, $TARGET_SPORTS, $ADMIN_KEY;

    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    $budget_safe = isset($_GET['budget_safe']) ? (int)$_GET['budget_safe'] : 0;

    // Check monthly credit usage before fetching
    $monthly_used = _so_monthly_credits($conn);
    $monthly_limit = 500;
    $credits_remaining = $monthly_limit - $monthly_used;

    // ── Monthly budget tracker: calculate daily credit allowance ──
    $day_of_month = (int)date('j');
    $days_in_month = (int)date('t');
    $days_remaining = $days_in_month - $day_of_month + 1;
    // Reserve 10% buffer for end-of-month
    $safe_remaining = $credits_remaining - 20;
    // With 5 fetches/day, calculate max credits per fetch
    $fetches_per_day = 5;
    $credits_per_fetch = ($days_remaining > 0 && $safe_remaining > 0)
        ? floor($safe_remaining / ($days_remaining * $fetches_per_day))
        : 0;

    if ($credits_remaining < 20) {
        echo json_encode(array(
            'ok' => false,
            'error' => 'Monthly credit budget nearly exhausted',
            'credits_used_this_month' => $monthly_used,
            'credits_remaining' => $credits_remaining,
            'daily_budget' => $credits_per_fetch * $fetches_per_day
        ));
        return;
    }

    // Get active sports
    $url = $API_BASE . '/sports/?apiKey=' . $THE_ODDS_API_KEY;
    $body = _so_http_get_simple($url);
    if ($body === null) {
        header('HTTP/1.0 502 Bad Gateway');
        echo json_encode(array('ok' => false, 'error' => 'Failed to fetch sports list'));
        return;
    }

    $all_sports = json_decode($body, true);
    if (!is_array($all_sports)) {
        header('HTTP/1.0 502 Bad Gateway');
        echo json_encode(array('ok' => false, 'error' => 'Invalid sports response'));
        return;
    }

    $active_keys = array();
    foreach ($all_sports as $s) {
        $sk = isset($s['key']) ? $s['key'] : '';
        if (isset($TARGET_SPORTS[$sk]) && isset($s['active']) && $s['active']) {
            $active_keys[] = $sk;
        }
    }

    if (count($active_keys) === 0) {
        echo json_encode(array('ok' => true, 'sports_fetched' => 0, 'message' => 'No target sports currently in season'));
        return;
    }

    // ── Smart budget-safe mode ──
    $skipped_sports = array();
    if ($budget_safe) {
        $filtered_keys = array();
        foreach ($active_keys as $sport_key) {
            // Skip 1: Check if odds for this sport were updated less than 2 hours ago
            $recent_q = $conn->query("SELECT MAX(last_updated) as lu FROM lm_sports_odds WHERE sport='"
                . $conn->real_escape_string($sport_key) . "'");
            if ($recent_q && $rrow = $recent_q->fetch_assoc()) {
                if ($rrow['lu'] !== null) {
                    $last_ts = strtotime($rrow['lu']);
                    if ($last_ts !== false && (time() - $last_ts) < 7200) {
                        $skipped_sports[] = array('sport' => $sport_key, 'reason' => 'Updated ' . round((time() - $last_ts) / 60) . ' min ago (< 2hr)');
                        continue;
                    }
                }
            }

            // Skip 2: Only fetch sports that have games in the next 24 hours
            $upcoming_q = $conn->query("SELECT COUNT(*) as cnt FROM lm_sports_odds WHERE sport='"
                . $conn->real_escape_string($sport_key)
                . "' AND commence_time > NOW() AND commence_time < DATE_ADD(NOW(), INTERVAL 24 HOUR)");
            $has_upcoming = false;
            if ($upcoming_q && $urow = $upcoming_q->fetch_assoc()) {
                $has_upcoming = ((int)$urow['cnt'] > 0);
            }
            // If we have NO cached data for this sport, always fetch (first time)
            $any_q = $conn->query("SELECT COUNT(*) as cnt FROM lm_sports_odds WHERE sport='"
                . $conn->real_escape_string($sport_key) . "'");
            $has_any = false;
            if ($any_q && $arow = $any_q->fetch_assoc()) {
                $has_any = ((int)$arow['cnt'] > 0);
            }

            if ($has_any && !$has_upcoming) {
                $skipped_sports[] = array('sport' => $sport_key, 'reason' => 'No games in next 24h');
                continue;
            }

            $filtered_keys[] = $sport_key;
        }
        $active_keys = $filtered_keys;

        // Additional throttle: if budget is tight, cap sports per fetch
        if ($credits_remaining < 100 && count($active_keys) > 2) {
            $active_keys = array_slice($active_keys, 0, 2);
        } elseif ($credits_per_fetch < 8 && count($active_keys) > 1) {
            // Very tight budget: only 1 sport per fetch
            $active_keys = array_slice($active_keys, 0, 1);
        }
    }

    if (count($active_keys) === 0) {
        echo json_encode(array(
            'ok' => true,
            'sports_fetched' => 0,
            'message' => 'All sports skipped by smart budget mode',
            'skipped_sports' => $skipped_sports,
            'credits_remaining' => $credits_remaining,
            'credits_per_fetch_budget' => $credits_per_fetch
        ));
        return;
    }

    $total_events = 0;
    $total_odds = 0;
    $total_credits = 0;
    $sports_fetched = 0;
    $sport_details = array();

    foreach ($active_keys as $sport_key) {
        // Fetch odds: regions=us,us2 markets=h2h,spreads,totals
        $odds_url = $API_BASE . '/sports/' . $sport_key . '/odds/'
            . '?apiKey=' . $THE_ODDS_API_KEY
            . '&regions=us,us2'
            . '&markets=h2h,spreads,totals'
            . '&oddsFormat=decimal'
            . '&dateFormat=iso';

        $resp_headers = array();
        $odds_body = _so_http_get($odds_url, $resp_headers);

        // Track credits from response headers
        $credits_used_now = 0;
        $api_remaining = null;
        if (isset($resp_headers['x-requests-used'])) {
            $credits_used_now = (int)$resp_headers['x-requests-used'];
        }
        if (isset($resp_headers['x-requests-remaining'])) {
            $api_remaining = (int)$resp_headers['x-requests-remaining'];
        }
        if (isset($resp_headers['x-requests-last'])) {
            $total_credits += (int)$resp_headers['x-requests-last'];
        }

        if ($odds_body === null) {
            // Fall to scraper
            $scraper_data = scrape_odds_failover($sport_key);
            if (is_array($scraper_data) &amp;&amp; count($scraper_data) > 0) {
                $odds_body = json_encode($scraper_data);
                $sport_details[] = array('sport' => $sport_key, 'source' => 'scraper');
            } else {
                $sport_details[] = array('sport' => $sport_key, 'error' => 'fetch failed (API and scraper)');
                continue;
            }
        }

        $events = json_decode($odds_body, true);
        if (!is_array($events)) {
            $sport_details[] = array('sport' => $sport_key, 'error' => 'invalid JSON');
            continue;
        }

        $event_count = 0;
        $odds_count = 0;

        foreach ($events as $event) {
            $event_id = isset($event['id']) ? $event['id'] : '';
            $home = isset($event['home_team']) ? $event['home_team'] : '';
            $away = isset($event['away_team']) ? $event['away_team'] : '';
            $commence = isset($event['commence_time']) ? _so_iso_to_mysql($event['commence_time']) : '2026-01-01 00:00:00';

            if (!$event_id || !$home) continue;
            $event_count++;

            $bookmakers = isset($event['bookmakers']) ? $event['bookmakers'] : array();
            foreach ($bookmakers as $bm) {
                $bm_key = isset($bm['key']) ? $bm['key'] : '';
                $bm_name = _so_book_name($bm_key);

                $markets = isset($bm['markets']) ? $bm['markets'] : array();
                foreach ($markets as $mkt) {
                    $mkt_key = isset($mkt['key']) ? $mkt['key'] : '';
                    $outcomes = isset($mkt['outcomes']) ? $mkt['outcomes'] : array();

                    foreach ($outcomes as $oc) {
                        $oc_name = isset($oc['name']) ? $oc['name'] : '';
                        $oc_price = isset($oc['price']) ? (float)$oc['price'] : 0;
                        $oc_point = isset($oc['point']) ? $oc['point'] : 'NULL';

                        // REPLACE INTO for upsert on unique key
                        $sql = "REPLACE INTO lm_sports_odds "
                            . "(sport, event_id, home_team, away_team, commence_time, "
                            . "bookmaker, bookmaker_key, market, outcome_name, outcome_price, outcome_point, last_updated) "
                            . "VALUES ("
                            . "'" . $conn->real_escape_string($sport_key) . "', "
                            . "'" . $conn->real_escape_string($event_id) . "', "
                            . "'" . $conn->real_escape_string($home) . "', "
                            . "'" . $conn->real_escape_string($away) . "', "
                            . "'" . $conn->real_escape_string($commence) . "', "
                            . "'" . $conn->real_escape_string($bm_name) . "', "
                            . "'" . $conn->real_escape_string($bm_key) . "', "
                            . "'" . $conn->real_escape_string($mkt_key) . "', "
                            . "'" . $conn->real_escape_string($oc_name) . "', "
                            . "" . (float)$oc_price . ", "
                            . ($oc_point === 'NULL' ? "NULL" : (float)$oc_point) . ", "
                            . "NOW()"
                            . ")";
                        $conn->query($sql);
                        $odds_count++;

                        // Kimi: CLV tracking — snapshot opening odds, update closing odds
                        $clv_implied = ($oc_price > 1) ? round(1.0 / $oc_price, 6) : 0;
                        $clv_sql = "INSERT INTO lm_sports_clv "
                            . "(event_id, sport, home_team, away_team, commence_time, bookmaker_key, market, outcome_name, "
                            . "opening_price, opening_implied_prob, closing_price, closing_implied_prob, first_seen, last_updated) "
                            . "VALUES ("
                            . "'" . $conn->real_escape_string($event_id) . "', "
                            . "'" . $conn->real_escape_string($sport_key) . "', "
                            . "'" . $conn->real_escape_string($home) . "', "
                            . "'" . $conn->real_escape_string($away) . "', "
                            . "'" . $conn->real_escape_string($commence) . "', "
                            . "'" . $conn->real_escape_string($bm_key) . "', "
                            . "'" . $conn->real_escape_string($mkt_key) . "', "
                            . "'" . $conn->real_escape_string($oc_name) . "', "
                            . (float)$oc_price . ", " . $clv_implied . ", "
                            . (float)$oc_price . ", " . $clv_implied . ", "
                            . "NOW(), NOW()"
                            . ") ON DUPLICATE KEY UPDATE "
                            . "closing_price = " . (float)$oc_price . ", "
                            . "closing_implied_prob = " . $clv_implied . ", "
                            . "clv_pct = ROUND((opening_implied_prob - " . $clv_implied . ") / opening_implied_prob * 100, 4), "
                            . "last_updated = NOW()";
                        $conn->query($clv_sql);
                    }
                }
            }
        }

        $total_events += $event_count;
        $total_odds += $odds_count;
        $sports_fetched++;

        $sport_details[] = array(
            'sport' => $sport_key,
            'short_name' => isset($TARGET_SPORTS[$sport_key]) ? $TARGET_SPORTS[$sport_key] : $sport_key,
            'events' => $event_count,
            'odds_rows' => $odds_count
        );

        // Log credit usage
        $conn->query("INSERT INTO lm_sports_credit_usage (request_time, sport, credits_used, credits_remaining) VALUES (NOW(), '"
            . $conn->real_escape_string($sport_key) . "', "
            . (int)(isset($resp_headers['x-requests-last']) ? $resp_headers['x-requests-last'] : 6) . ", "
            . ($api_remaining !== null ? (int)$api_remaining : 'NULL') . ")");
    }

    // Purge old odds (games that started more than 6 hours ago)
    $conn->query("DELETE FROM lm_sports_odds WHERE commence_time < DATE_SUB(NOW(), INTERVAL 6 HOUR)");

    // Expire old value bets
    $conn->query("UPDATE lm_sports_value_bets SET status='expired' WHERE commence_time < NOW() AND status='active'");

    $result = array(
        'ok'              => true,
        'sports_fetched'  => $sports_fetched,
        'events_cached'   => $total_events,
        'odds_rows'       => $total_odds,
        'credits_used'    => $total_credits,
        'credits_remaining' => $api_remaining,
        'monthly_used'    => _so_monthly_credits($conn),
        'monthly_limit'   => $monthly_limit,
        'daily_budget'    => $credits_per_fetch * $fetches_per_day,
        'days_remaining_in_month' => $days_remaining,
        'sport_details'   => $sport_details
    );
    if (count($skipped_sports) > 0) {
        $result['skipped_sports'] = $skipped_sports;
    }
    echo json_encode($result);
}

// ════════════════════════════════════════════════════════════
//  ACTION: get — Return cached odds grouped by event
// ════════════════════════════════════════════════════════════

function _so_action_get($conn) {
    global $TARGET_SPORTS;

    $sport_filter = isset($_GET['sport']) ? $conn->real_escape_string(trim($_GET['sport'])) : '';
    $hours = isset($_GET['hours']) ? (int)$_GET['hours'] : 48;
    if ($hours < 1) $hours = 1;
    if ($hours > 168) $hours = 168;

    $where = "commence_time > NOW() AND commence_time < DATE_ADD(NOW(), INTERVAL " . $hours . " HOUR)";
    if ($sport_filter) {
        $where .= " AND sport='" . $sport_filter . "'";
    }

    $result = $conn->query("SELECT * FROM lm_sports_odds WHERE " . $where . " ORDER BY commence_time ASC, event_id ASC, bookmaker ASC");

    if (!$result) {
        header('HTTP/1.0 500 Internal Server Error');
        echo json_encode(array('ok' => false, 'error' => 'Query failed'));
        return;
    }

    // Group by event → bookmaker → market → outcomes
    $events = array();
    $event_meta = array();

    while ($row = $result->fetch_assoc()) {
        $eid = $row['event_id'];
        if (!isset($event_meta[$eid])) {
            $short = isset($TARGET_SPORTS[$row['sport']]) ? $TARGET_SPORTS[$row['sport']] : $row['sport'];
            $event_meta[$eid] = array(
                'event_id'       => $eid,
                'sport'          => $row['sport'],
                'sport_short'    => $short,
                'home_team'      => $row['home_team'],
                'away_team'      => $row['away_team'],
                'commence_time'  => $row['commence_time'],
                'bookmakers'     => array()
            );
        }

        $bm_key = $row['bookmaker_key'];
        if (!isset($event_meta[$eid]['bookmakers'][$bm_key])) {
            $event_meta[$eid]['bookmakers'][$bm_key] = array(
                'key'          => $bm_key,
                'name'         => $row['bookmaker'],
                'is_canadian'  => _so_is_canadian_book($bm_key),
                'markets'      => array()
            );
        }

        $mkt = $row['market'];
        if (!isset($event_meta[$eid]['bookmakers'][$bm_key]['markets'][$mkt])) {
            $event_meta[$eid]['bookmakers'][$bm_key]['markets'][$mkt] = array();
        }

        $event_meta[$eid]['bookmakers'][$bm_key]['markets'][$mkt][] = array(
            'name'  => $row['outcome_name'],
            'price' => (float)$row['outcome_price'],
            'point' => $row['outcome_point'] !== null ? (float)$row['outcome_point'] : null
        );
    }

    // Convert to indexed arrays for JSON
    $events_out = array();
    foreach ($event_meta as $eid => $ev) {
        $bm_arr = array();
        foreach ($ev['bookmakers'] as $bk => $bm) {
            $mkt_arr = array();
            foreach ($bm['markets'] as $mk => $outcomes) {
                $mkt_arr[] = array('key' => $mk, 'outcomes' => $outcomes);
            }
            $bm['markets'] = $mkt_arr;
            $bm_arr[] = $bm;
        }
        $ev['bookmakers'] = $bm_arr;
        $events_out[] = $ev;
    }

    // Get last update time
    $lu = $conn->query("SELECT MAX(last_updated) as lu FROM lm_sports_odds WHERE " . $where);
    $last_updated = '';
    if ($lu && $r = $lu->fetch_assoc()) {
        $last_updated = $r['lu'] ? $r['lu'] : '';
    }

    echo json_encode(array(
        'ok'           => true,
        'events'       => $events_out,
        'event_count'  => count($events_out),
        'last_updated' => $last_updated,
        'filters'      => array('sport' => $sport_filter, 'hours_ahead' => $hours)
    ));
}

// ════════════════════════════════════════════════════════════
//  ACTION: credit_usage — Monthly API credit stats
// ════════════════════════════════════════════════════════════

function _so_action_credit_usage($conn) {
    $monthly = _so_monthly_credits($conn);
    $limit = 500;

    // Daily breakdown
    $daily = $conn->query("SELECT DATE(request_time) as day, SUM(credits_used) as used FROM lm_sports_credit_usage WHERE request_time >= DATE_SUB(NOW(), INTERVAL 30 DAY) GROUP BY DATE(request_time) ORDER BY day DESC LIMIT 30");
    $daily_arr = array();
    if ($daily) {
        while ($row = $daily->fetch_assoc()) {
            $daily_arr[] = array('date' => $row['day'], 'credits' => (int)$row['used']);
        }
    }

    echo json_encode(array(
        'ok'                => true,
        'monthly_used'      => $monthly,
        'monthly_limit'     => $limit,
        'monthly_remaining' => $limit - $monthly,
        'pct_used'          => round(($monthly / $limit) * 100, 1),
        'daily_breakdown'   => $daily_arr
    ));
}

// ════════════════════════════════════════════════════════════
//  Helper: get total credits used this month
// ════════════════════════════════════════════════════════════

function _so_monthly_credits($conn) {
    $r = $conn->query("SELECT COALESCE(SUM(credits_used), 0) as total FROM lm_sports_credit_usage WHERE request_time >= DATE_FORMAT(NOW(), '%Y-%m-01 00:00:00')");
    if ($r && $row = $r->fetch_assoc()) {
        return (int)$row['total'];
    }
    return 0;
}

// ════════════════════════════════════════════════════════════
//  ACTION: clv — Closing Line Value report (Kimi)
// ════════════════════════════════════════════════════════════

function _so_action_clv($conn) {
    global $TARGET_SPORTS;

    $sport = isset($_GET['sport']) ? $conn->real_escape_string(trim($_GET['sport'])) : '';
    $hours = isset($_GET['hours']) ? (int)$_GET['hours'] : 72;
    if ($hours < 1) $hours = 72;
    if ($hours > 720) $hours = 720;

    $where = "commence_time > DATE_SUB(NOW(), INTERVAL $hours HOUR)";
    if ($sport !== '') {
        $where .= " AND sport = '$sport'";
    }

    // CLV summary: avg CLV by bookmaker
    $bm_sql = "SELECT bookmaker_key,
               COUNT(*) as total_lines,
               ROUND(AVG(clv_pct), 4) as avg_clv,
               SUM(CASE WHEN clv_pct > 0 THEN 1 ELSE 0 END) as positive_clv,
               SUM(CASE WHEN clv_pct < 0 THEN 1 ELSE 0 END) as negative_clv
               FROM lm_sports_clv
               WHERE $where AND clv_pct IS NOT NULL
               GROUP BY bookmaker_key
               ORDER BY avg_clv DESC";
    $bm_res = $conn->query($bm_sql);
    $by_bookmaker = array();
    if ($bm_res) {
        while ($row = $bm_res->fetch_assoc()) {
            $row['avg_clv'] = (float)$row['avg_clv'];
            $row['total_lines'] = (int)$row['total_lines'];
            $row['positive_clv'] = (int)$row['positive_clv'];
            $row['negative_clv'] = (int)$row['negative_clv'];
            $by_bookmaker[] = $row;
        }
    }

    // Top CLV movers (biggest line movements)
    $top_sql = "SELECT event_id, sport, home_team, away_team, bookmaker_key, market, outcome_name,
               opening_price, closing_price, opening_implied_prob, closing_implied_prob, clv_pct, commence_time
               FROM lm_sports_clv
               WHERE $where AND clv_pct IS NOT NULL
               ORDER BY ABS(clv_pct) DESC
               LIMIT 20";
    $top_res = $conn->query($top_sql);
    $top_movers = array();
    if ($top_res) {
        while ($row = $top_res->fetch_assoc()) {
            $row['opening_price'] = (float)$row['opening_price'];
            $row['closing_price'] = (float)$row['closing_price'];
            $row['clv_pct'] = (float)$row['clv_pct'];
            $top_movers[] = $row;
        }
    }

    // Overall stats
    $stats_sql = "SELECT COUNT(*) as total_tracked,
                 SUM(CASE WHEN clv_pct IS NOT NULL THEN 1 ELSE 0 END) as with_movement,
                 ROUND(AVG(clv_pct), 4) as overall_avg_clv,
                 ROUND(MAX(clv_pct), 4) as max_clv,
                 ROUND(MIN(clv_pct), 4) as min_clv
                 FROM lm_sports_clv WHERE $where";
    $stats_res = $conn->query($stats_sql);
    $stats = array();
    if ($stats_res) {
        $stats = $stats_res->fetch_assoc();
        $stats['total_tracked'] = (int)$stats['total_tracked'];
        $stats['with_movement'] = (int)$stats['with_movement'];
    }

    echo json_encode(array(
        'ok' => true,
        'action' => 'clv',
        'hours' => $hours,
        'sport_filter' => $sport,
        'stats' => $stats,
        'by_bookmaker' => $by_bookmaker,
        'top_movers' => $top_movers
    ));
}

?>
