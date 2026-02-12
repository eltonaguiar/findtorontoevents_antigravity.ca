<?php
/**
 * Schedule Intelligence — Back-to-back, rest days, road trips for all sports
 * PHP 5.2 compatible (no short arrays, no closures, no __DIR__)
 *
 * Uses ESPN Scoreboard API (free, no key) to build schedule context.
 * Calculates fatigue factors backed by academic research:
 *   - Dean Oliver (2004): rest disparity is a measurable NBA edge
 *   - Entine & Small (2008): rest contributes to home-court advantage
 *   - PMC8636381: travel distance compounds B2B fatigue
 *   - Hockey Graphs (2014): goalie Sv% drops .008 on B2Bs
 *   - ESPN/ABC7: road favorites beat tired home underdogs 72.2%
 *
 * Actions:
 *   ?action=schedule&sport=basketball_nba  — Schedule intel for sport (public, cached 4h)
 *   ?action=game&sport=X&home=Y&away=Z    — Intel for specific matchup (public)
 *   ?action=refresh&sport=X&key=K          — Force refresh (admin)
 *   ?action=health                         — Check ESPN endpoints
 */

require_once dirname(__FILE__) . '/sports_db_connect.php';

// ── Ensure cache table ──
$conn->query("CREATE TABLE IF NOT EXISTS lm_schedule_intel_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cache_key VARCHAR(100) NOT NULL,
    cache_data LONGTEXT NOT NULL,
    source VARCHAR(100) NOT NULL DEFAULT '',
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_key (cache_key)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$ADMIN_KEY = isset($SPORTS_ADMIN_KEY) ? $SPORTS_ADMIN_KEY : 'livetrader2026';

// ── Sport -> ESPN path mapping ──
$SPORT_ESPN = array(
    'icehockey_nhl'          => 'hockey/nhl',
    'basketball_nba'         => 'basketball/nba',
    'americanfootball_nfl'   => 'football/nfl',
    'baseball_mlb'           => 'baseball/mlb',
    'americanfootball_cfl'   => 'football/cfl',
    'soccer_usa_mls'         => 'soccer/usa.1',
    'americanfootball_ncaaf' => 'football/college-football',
    'basketball_ncaab'       => 'basketball/mens-college-basketball'
);

// ── Action routing ──
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'schedule';

if ($action === 'schedule') {
    _si_action_schedule($conn);
} elseif ($action === 'game') {
    _si_action_game($conn);
} elseif ($action === 'refresh') {
    _si_action_refresh($conn);
} elseif ($action === 'health') {
    _si_action_health();
} else {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

$conn->close();
exit;

// ════════════════════════════════════════════════════════════
//  HTTP helper
// ════════════════════════════════════════════════════════════

function _si_http_get($url, $timeout) {
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
//  ACTION: schedule — Return cached or fresh schedule intel
// ════════════════════════════════════════════════════════════

function _si_action_schedule($conn) {
    $sport = isset($_GET['sport']) ? trim($_GET['sport']) : '';
    if (!$sport) {
        echo json_encode(array('ok' => false, 'error' => 'Missing sport parameter'));
        return;
    }

    $cache_key = 'sched_' . $sport;

    // Check cache (4-hour TTL)
    $cq = $conn->query("SELECT cache_data, source, updated_at FROM lm_schedule_intel_cache WHERE cache_key='" . $conn->real_escape_string($cache_key) . "' AND updated_at > DATE_SUB(NOW(), INTERVAL 4 HOUR)");
    if ($cq && $row = $cq->fetch_assoc()) {
        $data = json_decode($row['cache_data'], true);
        if (is_array($data)) {
            echo json_encode(array('ok' => true, 'teams' => $data, 'source' => $row['source'], 'updated_at' => $row['updated_at'], 'cached' => true, 'sport' => $sport));
            return;
        }
    }

    // Fetch fresh
    $result = _si_build_intel($sport);

    if (is_array($result) && count($result['teams']) > 0) {
        $json = json_encode($result['teams']);
        $conn->query("REPLACE INTO lm_schedule_intel_cache (cache_key, cache_data, source, updated_at) VALUES ('" . $conn->real_escape_string($cache_key) . "', '" . $conn->real_escape_string($json) . "', '" . $conn->real_escape_string($result['source']) . "', NOW())");

        echo json_encode(array('ok' => true, 'teams' => $result['teams'], 'count' => count($result['teams']), 'source' => $result['source'], 'updated_at' => gmdate('Y-m-d H:i:s') . ' UTC', 'cached' => false, 'sport' => $sport));
    } else {
        // Try stale cache
        $sq = $conn->query("SELECT cache_data, source, updated_at FROM lm_schedule_intel_cache WHERE cache_key='" . $conn->real_escape_string($cache_key) . "'");
        if ($sq && $row = $sq->fetch_assoc()) {
            $data = json_decode($row['cache_data'], true);
            if (is_array($data)) {
                echo json_encode(array('ok' => true, 'teams' => $data, 'source' => $row['source'] . ' (stale)', 'updated_at' => $row['updated_at'], 'cached' => true, 'stale' => true, 'sport' => $sport));
                return;
            }
        }
        echo json_encode(array('ok' => false, 'error' => 'Could not fetch schedule for ' . $sport, 'teams' => array()));
    }
}

// ════════════════════════════════════════════════════════════
//  ACTION: game — Intel for a specific matchup
// ════════════════════════════════════════════════════════════

function _si_action_game($conn) {
    $sport = isset($_GET['sport']) ? trim($_GET['sport']) : '';
    $home  = isset($_GET['home']) ? trim($_GET['home']) : '';
    $away  = isset($_GET['away']) ? trim($_GET['away']) : '';

    if (!$sport || !$home || !$away) {
        echo json_encode(array('ok' => false, 'error' => 'Required: sport, home, away'));
        return;
    }

    // Get full schedule intel (from cache or fresh)
    $cache_key = 'sched_' . $sport;
    $cq = $conn->query("SELECT cache_data FROM lm_schedule_intel_cache WHERE cache_key='" . $conn->real_escape_string($cache_key) . "'");
    $teams = array();
    if ($cq && $row = $cq->fetch_assoc()) {
        $teams = json_decode($row['cache_data'], true);
        if (!is_array($teams)) $teams = array();
    }

    if (count($teams) === 0) {
        $result = _si_build_intel($sport);
        if (is_array($result)) $teams = $result['teams'];
    }

    $home_intel = _si_find_team($teams, $home);
    $away_intel = _si_find_team($teams, $away);

    // Calculate advantage
    $rest_adv = 0;
    if ($home_intel && $away_intel) {
        $rest_adv = (int)$home_intel['rest_days'] - (int)$away_intel['rest_days'];
    }

    echo json_encode(array(
        'ok'           => true,
        'sport'        => $sport,
        'home_team'    => $home,
        'away_team'    => $away,
        'home_intel'   => $home_intel ? $home_intel : array(),
        'away_intel'   => $away_intel ? $away_intel : array(),
        'rest_advantage_home' => $rest_adv,
        'fatigue_edge' => _si_describe_fatigue($home_intel, $away_intel, $sport)
    ));
}

// ════════════════════════════════════════════════════════════
//  ACTION: refresh — Force rebuild (admin)
// ════════════════════════════════════════════════════════════

function _si_action_refresh($conn) {
    global $ADMIN_KEY;
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    $sport = isset($_GET['sport']) ? trim($_GET['sport']) : '';
    if (!$sport) {
        echo json_encode(array('ok' => false, 'error' => 'Missing sport parameter'));
        return;
    }

    $result = _si_build_intel($sport);
    if (is_array($result) && count($result['teams']) > 0) {
        $cache_key = 'sched_' . $sport;
        $json = json_encode($result['teams']);
        $conn->query("REPLACE INTO lm_schedule_intel_cache (cache_key, cache_data, source, updated_at) VALUES ('" . $conn->real_escape_string($cache_key) . "', '" . $conn->real_escape_string($json) . "', '" . $conn->real_escape_string($result['source']) . "', NOW())");
    }

    echo json_encode(array(
        'ok'     => true,
        'teams'  => is_array($result) ? count($result['teams']) : 0,
        'source' => is_array($result) ? $result['source'] : 'none'
    ));
}

// ════════════════════════════════════════════════════════════
//  ACTION: health — Check ESPN schedule endpoints
// ════════════════════════════════════════════════════════════

function _si_action_health() {
    $sources = array();
    $sports_check = array(
        'basketball/nba' => 'NBA',
        'hockey/nhl' => 'NHL',
        'football/nfl' => 'NFL',
        'baseball/mlb' => 'MLB'
    );

    foreach ($sports_check as $path => $label) {
        $t0 = microtime(true);
        $r = _si_http_get('https://site.api.espn.com/apis/site/v2/sports/' . $path . '/scoreboard', 5);
        $t1 = microtime(true);
        $sources[] = array('name' => $label . ' Scoreboard', 'ok' => ($r !== null), 'ms' => round(($t1 - $t0) * 1000));
    }

    echo json_encode(array('ok' => true, 'sources' => $sources));
}

// ════════════════════════════════════════════════════════════
//  CORE: Build schedule intelligence for a sport
// ════════════════════════════════════════════════════════════

function _si_build_intel($sport) {
    global $SPORT_ESPN;

    $espn_path = isset($SPORT_ESPN[$sport]) ? $SPORT_ESPN[$sport] : '';
    if (!$espn_path) {
        return array('teams' => array(), 'source' => 'unsupported_sport');
    }

    $base = 'https://site.api.espn.com/apis/site/v2/sports/' . $espn_path . '/scoreboard';

    // Fetch today + past 3 days of schedule to compute rest days
    $all_games = array();
    $source = 'none';

    for ($d = -3; $d <= 1; $d++) {
        $date = date('Ymd', strtotime($d . ' days'));
        $url = $base . '?dates=' . $date;
        $body = _si_http_get($url, 10);
        if ($body === null) continue;

        $data = json_decode($body, true);
        if (!is_array($data) || !isset($data['events'])) continue;

        $source = 'espn_scoreboard';

        foreach ($data['events'] as $event) {
            if (!isset($event['competitions'])) continue;
            foreach ($event['competitions'] as $comp) {
                if (!isset($comp['competitors'])) continue;

                $game = array(
                    'date'    => $date,
                    'status'  => '',
                    'home'    => '',
                    'away'    => '',
                    'home_abbr' => '',
                    'away_abbr' => ''
                );

                if (isset($comp['status']['type']['description'])) {
                    $game['status'] = $comp['status']['type']['description'];
                }

                foreach ($comp['competitors'] as $td) {
                    $tn = isset($td['team']['displayName']) ? $td['team']['displayName'] : '';
                    $ta = isset($td['team']['abbreviation']) ? $td['team']['abbreviation'] : '';
                    $is_home = (isset($td['homeAway']) && $td['homeAway'] === 'home');
                    if ($is_home) {
                        $game['home'] = $tn;
                        $game['home_abbr'] = $ta;
                    } else {
                        $game['away'] = $tn;
                        $game['away_abbr'] = $ta;
                    }
                }

                if ($game['home'] && $game['away']) {
                    $all_games[] = $game;
                }
            }
        }
    }

    if (count($all_games) === 0) {
        return array('teams' => array(), 'source' => $source);
    }

    // Build per-team schedule history
    $team_games = array(); // team_name => array of game dates + home/away
    $today = date('Ymd');
    $yesterday = date('Ymd', strtotime('-1 day'));

    foreach ($all_games as $g) {
        $gdate = $g['date'];

        // Home team
        $hn = $g['home'];
        if (!isset($team_games[$hn])) $team_games[$hn] = array('games' => array(), 'abbr' => $g['home_abbr']);
        $team_games[$hn]['games'][] = array('date' => $gdate, 'role' => 'home', 'status' => $g['status']);

        // Away team
        $an = $g['away'];
        if (!isset($team_games[$an])) $team_games[$an] = array('games' => array(), 'abbr' => $g['away_abbr']);
        $team_games[$an]['games'][] = array('date' => $gdate, 'role' => 'away', 'status' => $g['status']);
    }

    // Compute intel per team
    $teams = array();
    foreach ($team_games as $name => $info) {
        $games = $info['games'];
        $abbr = $info['abbr'];

        // Sort by date
        usort($games, '_si_sort_by_date');

        // Find last completed game (before today or today if already Final)
        $last_game_date = '';
        $last_game_role = '';
        $consec_away = 0;
        $games_last_7 = 0;
        $seven_days_ago = date('Ymd', strtotime('-7 days'));

        foreach ($games as $g) {
            if ($g['date'] < $today || ($g['date'] === $today && stripos($g['status'], 'Final') !== false)) {
                $last_game_date = $g['date'];
                $last_game_role = $g['role'];
            }
            if ($g['date'] >= $seven_days_ago && $g['date'] <= $today) {
                $games_last_7++;
            }
        }

        // Rest days
        $rest_days = 99; // unknown = lots of rest
        if ($last_game_date) {
            $diff = (strtotime($today) - strtotime($last_game_date)) / 86400;
            $rest_days = (int)$diff;
        }

        // Back-to-back detection
        $is_b2b = ($last_game_date === $yesterday);
        $played_today = false;
        foreach ($games as $g) {
            if ($g['date'] === $today) $played_today = true;
        }

        // Road trip detection: 3+ consecutive away games including today
        $recent_roles = array();
        foreach ($games as $g) {
            if ($g['date'] >= date('Ymd', strtotime('-5 days')) && $g['date'] <= $today) {
                $recent_roles[] = $g['role'];
            }
        }
        $consec_away = 0;
        $max_consec_away = 0;
        for ($i = count($recent_roles) - 1; $i >= 0; $i--) {
            if ($recent_roles[$i] === 'away') {
                $consec_away++;
                if ($consec_away > $max_consec_away) $max_consec_away = $consec_away;
            } else {
                break;
            }
        }
        $is_road_trip = ($max_consec_away >= 3);

        $key = strtolower($abbr);
        if (!$key) $key = strtolower(str_replace(' ', '_', $name));

        $teams[$key] = array(
            'name'          => $name,
            'abbreviation'  => $abbr,
            'is_back_to_back' => $is_b2b,
            'rest_days'       => $rest_days,
            'is_road_trip'    => $is_road_trip,
            'games_last_7'    => $games_last_7,
            'last_game_date'  => $last_game_date,
            'last_game_role'  => $last_game_role,
            'consec_away'     => $max_consec_away,
            'has_game_today'  => $played_today
        );
    }

    return array('teams' => $teams, 'source' => $source);
}

function _si_sort_by_date($a, $b) {
    return strcmp($a['date'], $b['date']);
}

// ════════════════════════════════════════════════════════════
//  Fuzzy team name matching
// ════════════════════════════════════════════════════════════

function _si_find_team($teams, $name) {
    if (!is_array($teams) || !$name) return null;
    $name = strtolower(trim($name));

    foreach ($teams as $k => $t) {
        $tn = strtolower($t['name']);
        $ta = strtolower($t['abbreviation']);
        if ($tn === $name || $ta === $name) return $t;
        if (strpos($tn, $name) !== false || strpos($name, $tn) !== false) return $t;
        if ($ta && (strpos($ta, $name) !== false || strpos($name, $ta) !== false)) return $t;
        // Last word match
        $parts = explode(' ', $name);
        $last = $parts[count($parts) - 1];
        if (strlen($last) >= 4 && strpos($tn, $last) !== false) return $t;
    }
    return null;
}

// ════════════════════════════════════════════════════════════
//  Describe fatigue edge for a matchup
// ════════════════════════════════════════════════════════════

function _si_describe_fatigue($home_intel, $away_intel, $sport) {
    $edges = array();

    if (!$home_intel || !$away_intel) {
        return array('description' => 'Schedule data unavailable', 'points' => 0, 'edges' => array());
    }

    $pts = 0;

    // B2B detection
    if ($away_intel['is_back_to_back'] && !$home_intel['is_back_to_back']) {
        if ($sport === 'basketball_nba' || $sport === 'basketball_ncaab') {
            $edges[] = 'Away team on back-to-back (historically ~2.5 pts worse, Dean Oliver 2004)';
            $pts += 10;
        } elseif ($sport === 'icehockey_nhl') {
            $edges[] = 'Away team on back-to-back (goalie Sv% drops .008, Hockey Graphs 2014)';
            $pts += 10;
        } else {
            $edges[] = 'Away team on back-to-back';
            $pts += 6;
        }
    } elseif ($home_intel['is_back_to_back'] && !$away_intel['is_back_to_back']) {
        if ($sport === 'icehockey_nhl') {
            $edges[] = 'Home team on B2B -- road favorites win 72.2% vs tired home underdogs (ESPN study)';
            $pts += 8;
        } else {
            $edges[] = 'Home team on back-to-back (fatigue disadvantage)';
            $pts += 7;
        }
    }

    // Rest advantage
    $rest_diff = (int)$home_intel['rest_days'] - (int)$away_intel['rest_days'];
    if (abs($rest_diff) >= 2) {
        $rested = ($rest_diff > 0) ? 'Home' : 'Away';
        $edges[] = $rested . ' team has ' . abs($rest_diff) . '-day rest advantage (Entine & Small 2008)';
        $pts += min(abs($rest_diff) * 2, 5);
    }

    // Road trip fatigue
    if ($away_intel['is_road_trip']) {
        $edges[] = 'Away team on extended road trip (' . $away_intel['consec_away'] . ' consecutive away games, PMC8636381)';
        $pts += 3;
    }

    // Schedule density
    if ($away_intel['games_last_7'] >= 5 && $home_intel['games_last_7'] <= 3) {
        $edges[] = 'Away team has dense schedule (' . $away_intel['games_last_7'] . ' games in 7 days vs ' . $home_intel['games_last_7'] . ')';
        $pts += 2;
    } elseif ($home_intel['games_last_7'] >= 5 && $away_intel['games_last_7'] <= 3) {
        $edges[] = 'Home team has dense schedule (' . $home_intel['games_last_7'] . ' games in 7 days vs ' . $away_intel['games_last_7'] . ')';
        $pts += 2;
    }

    $desc = count($edges) > 0 ? implode('. ', $edges) . '.' : 'No significant schedule-based edge detected.';

    return array('description' => $desc, 'points' => $pts, 'edges' => $edges);
}

?>
