<?php
/**
 * Injury Intelligence — Player injury reports from ESPN free endpoints
 * PHP 5.2 compatible
 *
 * Fetches injury data from ESPN's undocumented free API endpoints.
 * Provides per-team injury counts (OUT, questionable) for use in pick grading.
 *
 * Sources: ESPN injuries/news endpoints (free, no key)
 *
 * Actions:
 *   ?action=injuries&sport=basketball_nba  — Injury report for sport (public, cached 2h)
 *   ?action=team&sport=X&team=Y            — Injuries for a specific team
 *   ?action=refresh&sport=X&key=K          — Force refresh (admin)
 *   ?action=health                         — Check ESPN injury endpoints
 */

require_once dirname(__FILE__) . '/sports_db_connect.php';

$conn->query("CREATE TABLE IF NOT EXISTS lm_injury_intel_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cache_key VARCHAR(100) NOT NULL,
    cache_data LONGTEXT NOT NULL,
    source VARCHAR(100) NOT NULL DEFAULT '',
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_key (cache_key)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$ADMIN_KEY = isset($SPORTS_ADMIN_KEY) ? $SPORTS_ADMIN_KEY : 'livetrader2026';

$SPORT_ESPN_INJ = array(
    'icehockey_nhl'          => 'hockey/nhl',
    'basketball_nba'         => 'basketball/nba',
    'americanfootball_nfl'   => 'football/nfl',
    'baseball_mlb'           => 'baseball/mlb',
    'basketball_ncaab'       => 'basketball/mens-college-basketball'
);

$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'injuries';

if ($action === 'injuries') {
    _inj_action_injuries($conn);
} elseif ($action === 'team') {
    _inj_action_team($conn);
} elseif ($action === 'refresh') {
    _inj_action_refresh($conn);
} elseif ($action === 'health') {
    _inj_action_health();
} else {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

$conn->close();
exit;

function _inj_http_get($url, $timeout) {
    if (!$timeout) $timeout = 12;
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array(
            'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept: application/json'
        ));
        $body = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($body !== false && $code >= 200 && $code < 300) return $body;
        return null;
    }
    $ctx = stream_context_create(array(
        'http' => array('method' => 'GET', 'timeout' => $timeout,
            'header' => "User-Agent: Mozilla/5.0\r\nAccept: application/json\r\n"),
        'ssl' => array('verify_peer' => false)
    ));
    $body = @file_get_contents($url, false, $ctx);
    return ($body === false) ? null : $body;
}

// ════════════════════════════════════════════════════════════
//  ACTION: injuries — All team injury summaries for a sport
// ════════════════════════════════════════════════════════════

function _inj_action_injuries($conn) {
    $sport = isset($_GET['sport']) ? trim($_GET['sport']) : '';
    if (!$sport) {
        echo json_encode(array('ok' => false, 'error' => 'Missing sport parameter'));
        return;
    }

    $cache_key = 'inj_' . $sport;
    $cq = $conn->query("SELECT cache_data, source, updated_at FROM lm_injury_intel_cache WHERE cache_key='" . $conn->real_escape_string($cache_key) . "' AND updated_at > DATE_SUB(NOW(), INTERVAL 2 HOUR)");
    if ($cq && $row = $cq->fetch_assoc()) {
        $data = json_decode($row['cache_data'], true);
        if (is_array($data)) {
            echo json_encode(array('ok' => true, 'teams' => $data, 'count' => count($data), 'source' => $row['source'], 'updated_at' => $row['updated_at'], 'cached' => true, 'sport' => $sport));
            return;
        }
    }

    $result = _inj_fetch_all($sport);
    if (is_array($result) && count($result['teams']) > 0) {
        $json = json_encode($result['teams']);
        $conn->query("REPLACE INTO lm_injury_intel_cache (cache_key, cache_data, source, updated_at) VALUES ('" . $conn->real_escape_string($cache_key) . "', '" . $conn->real_escape_string($json) . "', '" . $conn->real_escape_string($result['source']) . "', NOW())");
        echo json_encode(array('ok' => true, 'teams' => $result['teams'], 'count' => count($result['teams']), 'source' => $result['source'], 'updated_at' => gmdate('Y-m-d H:i:s') . ' UTC', 'cached' => false, 'sport' => $sport));
    } else {
        // Stale cache
        $sq = $conn->query("SELECT cache_data, source, updated_at FROM lm_injury_intel_cache WHERE cache_key='" . $conn->real_escape_string($cache_key) . "'");
        if ($sq && $row = $sq->fetch_assoc()) {
            $data = json_decode($row['cache_data'], true);
            if (is_array($data)) {
                echo json_encode(array('ok' => true, 'teams' => $data, 'source' => $row['source'] . ' (stale)', 'updated_at' => $row['updated_at'], 'cached' => true, 'stale' => true, 'sport' => $sport));
                return;
            }
        }
        echo json_encode(array('ok' => false, 'error' => 'No injury data for ' . $sport, 'teams' => array()));
    }
}

// ════════════════════════════════════════════════════════════
//  ACTION: team — Injuries for a specific team
// ════════════════════════════════════════════════════════════

function _inj_action_team($conn) {
    $sport = isset($_GET['sport']) ? trim($_GET['sport']) : '';
    $team  = isset($_GET['team']) ? trim($_GET['team']) : '';
    if (!$sport || !$team) {
        echo json_encode(array('ok' => false, 'error' => 'Required: sport, team'));
        return;
    }

    $cache_key = 'inj_' . $sport;
    $cq = $conn->query("SELECT cache_data FROM lm_injury_intel_cache WHERE cache_key='" . $conn->real_escape_string($cache_key) . "'");
    $teams = array();
    if ($cq && $row = $cq->fetch_assoc()) {
        $teams = json_decode($row['cache_data'], true);
        if (!is_array($teams)) $teams = array();
    }

    if (count($teams) === 0) {
        $result = _inj_fetch_all($sport);
        if (is_array($result)) $teams = $result['teams'];
    }

    $team_data = _inj_find_team($teams, $team);
    echo json_encode(array('ok' => true, 'team' => $team, 'injuries' => $team_data ? $team_data : array('out' => 0, 'questionable' => 0, 'players_out' => array())));
}

// ════════════════════════════════════════════════════════════
//  ACTION: refresh — Force refresh
// ════════════════════════════════════════════════════════════

function _inj_action_refresh($conn) {
    global $ADMIN_KEY;
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $ADMIN_KEY) { header('HTTP/1.0 403 Forbidden'); echo json_encode(array('ok' => false, 'error' => 'Invalid admin key')); return; }

    $sport = isset($_GET['sport']) ? trim($_GET['sport']) : '';
    if (!$sport) { echo json_encode(array('ok' => false, 'error' => 'Missing sport')); return; }

    $result = _inj_fetch_all($sport);
    if (is_array($result) && count($result['teams']) > 0) {
        $cache_key = 'inj_' . $sport;
        $json = json_encode($result['teams']);
        $conn->query("REPLACE INTO lm_injury_intel_cache (cache_key, cache_data, source, updated_at) VALUES ('" . $conn->real_escape_string($cache_key) . "', '" . $conn->real_escape_string($json) . "', '" . $conn->real_escape_string($result['source']) . "', NOW())");
    }
    echo json_encode(array('ok' => true, 'teams' => is_array($result) ? count($result['teams']) : 0, 'source' => is_array($result) ? $result['source'] : 'none'));
}

// ════════════════════════════════════════════════════════════
//  ACTION: health — Check ESPN injury endpoints
// ════════════════════════════════════════════════════════════

function _inj_action_health() {
    $checks = array(
        'basketball/nba' => 'NBA',
        'hockey/nhl' => 'NHL',
        'football/nfl' => 'NFL'
    );
    $sources = array();
    foreach ($checks as $path => $label) {
        $t0 = microtime(true);
        $r = _inj_http_get('https://site.api.espn.com/apis/site/v2/sports/' . $path . '/teams', 5);
        $t1 = microtime(true);
        $sources[] = array('name' => $label . ' Teams', 'ok' => ($r !== null), 'ms' => round(($t1 - $t0) * 1000));
    }
    echo json_encode(array('ok' => true, 'sources' => $sources));
}

// ════════════════════════════════════════════════════════════
//  CORE: Fetch injury data from ESPN
// ════════════════════════════════════════════════════════════

function _inj_fetch_all($sport) {
    global $SPORT_ESPN_INJ;

    $espn_path = isset($SPORT_ESPN_INJ[$sport]) ? $SPORT_ESPN_INJ[$sport] : '';
    if (!$espn_path) {
        return array('teams' => array(), 'source' => 'unsupported_sport');
    }

    // Strategy: Fetch teams list first, then get injuries from team rosters/news
    // ESPN does not have a clean /injuries endpoint for all sports, but the
    // scoreboard/summary endpoint includes injury data per game.
    // Alternate: fetch from the teams endpoint and check each team.

    // Method 1: Try the scoreboard which sometimes includes injury info
    $teams = array();
    $source = 'none';

    // Method: Fetch team list and then each team's injuries via roster endpoint
    $teams_url = 'https://site.api.espn.com/apis/site/v2/sports/' . $espn_path . '/teams?limit=50';
    $body = _inj_http_get($teams_url, 12);

    if ($body !== null) {
        $data = json_decode($body, true);
        if (is_array($data) && isset($data['sports'])) {
            $source = 'espn_teams';
            foreach ($data['sports'] as $sp) {
                if (!isset($sp['leagues'])) continue;
                foreach ($sp['leagues'] as $league) {
                    if (!isset($league['teams'])) continue;
                    foreach ($league['teams'] as $tm) {
                        if (!isset($tm['team'])) continue;
                        $t = $tm['team'];
                        $team_name = isset($t['displayName']) ? $t['displayName'] : '';
                        $abbr = isset($t['abbreviation']) ? $t['abbreviation'] : '';
                        $tid = isset($t['id']) ? $t['id'] : '';

                        if (!$team_name || !$tid) continue;

                        // Fetch team injuries from roster endpoint
                        $inj_url = 'https://site.api.espn.com/apis/site/v2/sports/' . $espn_path . '/teams/' . $tid . '/injuries';
                        $inj_body = _inj_http_get($inj_url, 8);

                        $out_count = 0;
                        $quest_count = 0;
                        $players_out = array();

                        if ($inj_body !== null) {
                            $inj_data = json_decode($inj_body, true);
                            if (is_array($inj_data) && isset($inj_data['items'])) {
                                foreach ($inj_data['items'] as $item) {
                                    $status = '';
                                    if (isset($item['status'])) {
                                        $status = strtolower($item['status']);
                                    } elseif (isset($item['type']['description'])) {
                                        $status = strtolower($item['type']['description']);
                                    }
                                    $pname = '';
                                    if (isset($item['athlete']['displayName'])) {
                                        $pname = $item['athlete']['displayName'];
                                    } elseif (isset($item['athlete']['fullName'])) {
                                        $pname = $item['athlete']['fullName'];
                                    }
                                    $pos = isset($item['athlete']['position']['abbreviation']) ? $item['athlete']['position']['abbreviation'] : '';

                                    if (strpos($status, 'out') !== false || strpos($status, 'injured reserve') !== false || strpos($status, 'suspension') !== false) {
                                        $out_count++;
                                        if ($pname) {
                                            $players_out[] = array('name' => $pname, 'position' => $pos, 'status' => $status);
                                        }
                                    } elseif (strpos($status, 'day-to-day') !== false || strpos($status, 'questionable') !== false || strpos($status, 'doubtful') !== false || strpos($status, 'probable') !== false) {
                                        $quest_count++;
                                    }
                                }
                            }
                        }

                        $key = strtolower($abbr);
                        if (!$key) $key = strtolower(str_replace(' ', '_', $team_name));

                        $teams[$key] = array(
                            'name'          => $team_name,
                            'abbreviation'  => $abbr,
                            'out'           => $out_count,
                            'questionable'  => $quest_count,
                            'total_injured' => $out_count + $quest_count,
                            'players_out'   => array_slice($players_out, 0, 5) // top 5 to save space
                        );
                    }
                }
            }
        }
    }

    // If per-team fetching is too slow or returns nothing, try scoreboard approach
    if (count($teams) === 0) {
        $sb_url = 'https://site.api.espn.com/apis/site/v2/sports/' . $espn_path . '/scoreboard';
        $sb_body = _inj_http_get($sb_url, 10);
        if ($sb_body !== null) {
            $sb_data = json_decode($sb_body, true);
            if (is_array($sb_data) && isset($sb_data['events'])) {
                $source = 'espn_scoreboard_fallback';
                // Extract team names at minimum (injury data may be limited)
                foreach ($sb_data['events'] as $event) {
                    if (!isset($event['competitions'])) continue;
                    foreach ($event['competitions'] as $comp) {
                        if (!isset($comp['competitors'])) continue;
                        foreach ($comp['competitors'] as $c) {
                            $tn = isset($c['team']['displayName']) ? $c['team']['displayName'] : '';
                            $ta = isset($c['team']['abbreviation']) ? strtolower($c['team']['abbreviation']) : '';
                            if ($tn && $ta && !isset($teams[$ta])) {
                                $teams[$ta] = array(
                                    'name' => $tn,
                                    'abbreviation' => strtoupper($ta),
                                    'out' => 0,
                                    'questionable' => 0,
                                    'total_injured' => 0,
                                    'players_out' => array()
                                );
                            }
                        }
                    }
                }
            }
        }
    }

    return array('teams' => $teams, 'source' => $source);
}

function _inj_find_team($teams, $name) {
    if (!is_array($teams) || !$name) return null;
    $name = strtolower(trim($name));
    foreach ($teams as $k => $t) {
        $tn = strtolower($t['name']);
        $ta = strtolower($t['abbreviation']);
        if ($tn === $name || $ta === $name) return $t;
        if (strpos($tn, $name) !== false || strpos($name, $tn) !== false) return $t;
        $parts = explode(' ', $name);
        $last = $parts[count($parts) - 1];
        if (strlen($last) >= 4 && strpos($tn, $last) !== false) return $t;
    }
    return null;
}

?>
