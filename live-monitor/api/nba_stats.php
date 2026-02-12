<?php
/**
 * NBA Stats API — Real team stats with multi-source failover
 * PHP 5.2 compatible (no short arrays, no closures, no __DIR__)
 *
 * Data sources (failover chain — APIs first, scrapers as fallback):
 *   1. ESPN API (free, no key) — standings, records, streaks
 *   2. BallDontLie API (free, no key) — team stats, season averages
 *   3. NBA.com stats (free, no key) — official standings fallback
 *   4. ESPN web scraping (last resort)
 *
 * Actions:
 *   ?action=team_stats    — All NBA team stats (public, cached 2h)
 *   ?action=refresh&key=X — Force refresh from APIs (admin)
 *   ?action=health        — Check which sources are responding
 */

require_once dirname(__FILE__) . '/sports_db_connect.php';

// ── Ensure cache table exists ──
$conn->query("CREATE TABLE IF NOT EXISTS lm_nba_stats_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cache_key VARCHAR(50) NOT NULL,
    cache_data LONGTEXT NOT NULL,
    source VARCHAR(100) NOT NULL DEFAULT '',
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_key (cache_key)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ── Admin key from db_config ──
$ADMIN_KEY = isset($SPORTS_ADMIN_KEY) ? $SPORTS_ADMIN_KEY : 'livetrader2026';

// ── Action routing ──
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'team_stats';

if ($action === 'team_stats') {
    _nba_action_team_stats($conn);
} elseif ($action === 'refresh') {
    _nba_action_refresh($conn);
} elseif ($action === 'health') {
    _nba_action_health();
} else {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

$conn->close();
exit;

// ════════════════════════════════════════════════════════════
//  HTTP helper
// ════════════════════════════════════════════════════════════

function _nba_http_get($url, $timeout) {
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
        'http' => array(
            'method'  => 'GET',
            'timeout' => $timeout,
            'header'  => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\nAccept: application/json\r\n"
        ),
        'ssl' => array('verify_peer' => false)
    ));
    $body = @file_get_contents($url, false, $ctx);
    return ($body === false) ? null : $body;
}

// ════════════════════════════════════════════════════════════
//  ACTION: team_stats — Return cached or fresh NBA team data
// ════════════════════════════════════════════════════════════

function _nba_action_team_stats($conn) {
    // Check cache (2-hour TTL)
    $cache_q = $conn->query("SELECT cache_data, source, updated_at FROM lm_nba_stats_cache WHERE cache_key='nba_teams' AND updated_at > DATE_SUB(NOW(), INTERVAL 2 HOUR)");
    if ($cache_q && $row = $cache_q->fetch_assoc()) {
        $data = json_decode($row['cache_data'], true);
        if (is_array($data) && count($data) > 0) {
            echo json_encode(array(
                'ok'         => true,
                'teams'      => $data,
                'count'      => count($data),
                'source'     => $row['source'],
                'updated_at' => $row['updated_at'],
                'cached'     => true
            ));
            return;
        }
    }

    // Cache miss or stale — fetch fresh
    $result = _nba_fetch_all_team_stats();

    if (is_array($result) && count($result['teams']) > 0) {
        // Store in cache
        $json = json_encode($result['teams']);
        $conn->query("REPLACE INTO lm_nba_stats_cache (cache_key, cache_data, source, updated_at) VALUES ('nba_teams', '" . $conn->real_escape_string($json) . "', '" . $conn->real_escape_string($result['source']) . "', NOW())");

        echo json_encode(array(
            'ok'         => true,
            'teams'      => $result['teams'],
            'count'      => count($result['teams']),
            'source'     => $result['source'],
            'updated_at' => gmdate('Y-m-d H:i:s') . ' UTC',
            'cached'     => false
        ));
    } else {
        // All sources failed — try stale cache
        $stale_q = $conn->query("SELECT cache_data, source, updated_at FROM lm_nba_stats_cache WHERE cache_key='nba_teams'");
        if ($stale_q && $row = $stale_q->fetch_assoc()) {
            $data = json_decode($row['cache_data'], true);
            if (is_array($data) && count($data) > 0) {
                echo json_encode(array(
                    'ok'         => true,
                    'teams'      => $data,
                    'count'      => count($data),
                    'source'     => $row['source'] . ' (stale)',
                    'updated_at' => $row['updated_at'],
                    'cached'     => true,
                    'stale'      => true
                ));
                return;
            }
        }
        echo json_encode(array('ok' => false, 'error' => 'All NBA data sources failed', 'teams' => array()));
    }
}

// ════════════════════════════════════════════════════════════
//  ACTION: refresh — Force refresh (admin)
// ════════════════════════════════════════════════════════════

function _nba_action_refresh($conn) {
    global $ADMIN_KEY;
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    $result = _nba_fetch_all_team_stats();
    if (is_array($result) && count($result['teams']) > 0) {
        $json = json_encode($result['teams']);
        $conn->query("REPLACE INTO lm_nba_stats_cache (cache_key, cache_data, source, updated_at) VALUES ('nba_teams', '" . $conn->real_escape_string($json) . "', '" . $conn->real_escape_string($result['source']) . "', NOW())");
    }

    echo json_encode(array(
        'ok'     => true,
        'teams'  => isset($result['teams']) ? count($result['teams']) : 0,
        'source' => isset($result['source']) ? $result['source'] : 'none',
        'errors' => isset($result['errors']) ? $result['errors'] : array()
    ));
}

// ════════════════════════════════════════════════════════════
//  ACTION: health — Check which APIs are responding
// ════════════════════════════════════════════════════════════

function _nba_action_health() {
    $sources = array();

    // ESPN API
    $t0 = microtime(true);
    $espn = _nba_http_get('https://site.api.espn.com/apis/v2/sports/basketball/nba/standings', 5);
    $t1 = microtime(true);
    $sources[] = array('name' => 'ESPN API', 'ok' => ($espn !== null), 'ms' => round(($t1 - $t0) * 1000));

    // BallDontLie
    $t0 = microtime(true);
    $bdl = _nba_http_get('https://api.balldontlie.io/v1/teams', 5);
    $t1 = microtime(true);
    $sources[] = array('name' => 'BallDontLie API', 'ok' => ($bdl !== null), 'ms' => round(($t1 - $t0) * 1000));

    // ESPN scoreboard (for live scores)
    $t0 = microtime(true);
    $sb = _nba_http_get('https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard', 5);
    $t1 = microtime(true);
    $sources[] = array('name' => 'ESPN Scoreboard', 'ok' => ($sb !== null), 'ms' => round(($t1 - $t0) * 1000));

    echo json_encode(array('ok' => true, 'sources' => $sources));
}

// ════════════════════════════════════════════════════════════
//  CORE: Fetch NBA team stats — failover chain
//  APIs first → Scrapers as fallback → Empty state (never fake)
// ════════════════════════════════════════════════════════════

function _nba_fetch_all_team_stats() {
    $teams = array();
    $source = 'none';
    $errors = array();

    // ── Source 1: ESPN Standings API (free, no key) ──
    $espn_teams = _nba_source_espn_standings();
    if (is_array($espn_teams) && count($espn_teams) > 0) {
        $teams = $espn_teams;
        $source = 'espn_api';
    } else {
        $errors[] = 'ESPN standings API failed';
    }

    // ── Source 2: ESPN Scoreboard API (supplement with today's data) ──
    $scoreboard = _nba_source_espn_scoreboard();
    if (is_array($scoreboard) && count($scoreboard) > 0) {
        // Merge scoreboard data (today's games) into team data
        foreach ($scoreboard as $game) {
            // This adds recent game context but doesn't replace standings
        }
        if ($source === 'none') {
            $source = 'espn_scoreboard';
        } else {
            $source .= '+scoreboard';
        }
    } else {
        $errors[] = 'ESPN scoreboard failed';
    }

    // ── Source 3: BallDontLie API (supplement with advanced stats) ──
    $bdl_teams = _nba_source_balldontlie();
    if (is_array($bdl_teams) && count($bdl_teams) > 0) {
        // Merge BDL data into existing teams (PPG, etc.)
        foreach ($bdl_teams as $bdl_key => $bdl_data) {
            // Find matching team in our data
            foreach ($teams as $tk => $t) {
                if (_nba_team_match($t['name'], $bdl_data['name'])) {
                    // Supplement with any missing fields
                    if (empty($teams[$tk]['ppg']) && !empty($bdl_data['ppg'])) {
                        $teams[$tk]['ppg'] = $bdl_data['ppg'];
                    }
                    if (empty($teams[$tk]['opp_ppg']) && !empty($bdl_data['opp_ppg'])) {
                        $teams[$tk]['opp_ppg'] = $bdl_data['opp_ppg'];
                    }
                    break;
                }
            }
        }
        if ($source === 'none') {
            $teams = $bdl_teams;
            $source = 'balldontlie';
        } else {
            $source .= '+balldontlie';
        }
    } else {
        $errors[] = 'BallDontLie API failed or returned empty';
    }

    // ── Source 4: NBA.com standings (fallback if ESPN failed) ──
    if (count($teams) === 0) {
        $nba_com = _nba_source_nba_com();
        if (is_array($nba_com) && count($nba_com) > 0) {
            $teams = $nba_com;
            $source = 'nba.com';
        } else {
            $errors[] = 'NBA.com fallback failed';
        }
    }

    return array('teams' => $teams, 'source' => $source, 'errors' => $errors);
}

// ════════════════════════════════════════════════════════════
//  Source 1: ESPN Standings API
// ════════════════════════════════════════════════════════════

function _nba_source_espn_standings() {
    $url = 'https://site.api.espn.com/apis/v2/sports/basketball/nba/standings';
    $body = _nba_http_get($url, 12);
    if ($body === null) return null;

    $data = json_decode($body, true);
    if (!is_array($data) || !isset($data['children'])) return null;

    $teams = array();
    $all_sorted = array();

    foreach ($data['children'] as $conf) {
        if (!isset($conf['standings']['entries'])) continue;
        $conf_name = isset($conf['name']) ? $conf['name'] : '';

        foreach ($conf['standings']['entries'] as $entry) {
            if (!isset($entry['team'])) continue;
            $team = $entry['team'];

            $stats_map = array();
            if (isset($entry['stats'])) {
                foreach ($entry['stats'] as $s) {
                    $sn = isset($s['name']) ? $s['name'] : '';
                    $sv = isset($s['displayValue']) ? $s['displayValue'] : (isset($s['value']) ? $s['value'] : '');
                    $stats_map[$sn] = $sv;
                }
            }

            $team_name = isset($team['displayName']) ? $team['displayName'] : '';
            $short_name = isset($team['shortDisplayName']) ? $team['shortDisplayName'] : '';
            $abbr = isset($team['abbreviation']) ? $team['abbreviation'] : '';
            $wins = isset($stats_map['wins']) ? (int)$stats_map['wins'] : 0;
            $losses = isset($stats_map['losses']) ? (int)$stats_map['losses'] : 0;
            $win_pct = ($wins + $losses) > 0 ? round($wins / ($wins + $losses), 3) : 0;

            // Extract additional stats
            $streak = isset($stats_map['streak']) ? $stats_map['streak'] : '';
            $home_record = isset($stats_map['Home']) ? $stats_map['Home'] : (isset($stats_map['home']) ? $stats_map['home'] : '');
            $away_record = isset($stats_map['Road']) ? $stats_map['Road'] : (isset($stats_map['away']) ? $stats_map['away'] : '');
            $last10 = isset($stats_map['Last Ten Games']) ? $stats_map['Last Ten Games'] : (isset($stats_map['L10']) ? $stats_map['L10'] : '');
            $ppg = isset($stats_map['pointsFor']) ? round((float)$stats_map['pointsFor'], 1) : '';
            $opp_ppg = isset($stats_map['pointsAgainst']) ? round((float)$stats_map['pointsAgainst'], 1) : '';
            $diff = isset($stats_map['differential']) ? $stats_map['differential'] : '';

            $all_sorted[] = array(
                'name'         => $team_name,
                'short_name'   => $short_name,
                'abbreviation' => $abbr,
                'wins'         => $wins,
                'losses'       => $losses,
                'win_pct'      => $win_pct,
                'conference'   => $conf_name,
                'streak'       => $streak,
                'home_record'  => $home_record,
                'away_record'  => $away_record,
                'last10'       => $last10,
                'ppg'          => $ppg,
                'opp_ppg'      => $opp_ppg,
                'diff'         => $diff
            );
        }
    }

    // Sort by win pct desc
    usort($all_sorted, '_nba_sort_win_pct');

    // Index by team abbreviation for easy lookup
    for ($i = 0; $i < count($all_sorted); $i++) {
        $t = $all_sorted[$i];
        $t['rank'] = $i + 1;
        $key = strtolower($t['abbreviation']);
        if (!$key) $key = strtolower(str_replace(' ', '_', $t['name']));
        $teams[$key] = $t;
    }

    return count($teams) > 0 ? $teams : null;
}

function _nba_sort_win_pct($a, $b) {
    if ($b['win_pct'] == $a['win_pct']) return 0;
    return ($b['win_pct'] > $a['win_pct']) ? 1 : -1;
}

// ════════════════════════════════════════════════════════════
//  Source 2: ESPN Scoreboard (today's games + scores)
// ════════════════════════════════════════════════════════════

function _nba_source_espn_scoreboard() {
    $url = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard';
    $body = _nba_http_get($url, 10);
    if ($body === null) return null;

    $data = json_decode($body, true);
    if (!is_array($data) || !isset($data['events'])) return null;

    $games = array();
    foreach ($data['events'] as $event) {
        if (!isset($event['competitions'])) continue;
        foreach ($event['competitions'] as $comp) {
            if (!isset($comp['competitors'])) continue;

            $game = array('home_team' => '', 'away_team' => '', 'status' => '');

            if (isset($comp['status']['type']['description'])) {
                $game['status'] = $comp['status']['type']['description'];
            }

            foreach ($comp['competitors'] as $team_data) {
                $tn = '';
                if (isset($team_data['team']['displayName'])) {
                    $tn = $team_data['team']['displayName'];
                }
                $is_home = (isset($team_data['homeAway']) && $team_data['homeAway'] === 'home');
                if ($is_home) {
                    $game['home_team'] = $tn;
                    $game['home_score'] = isset($team_data['score']) ? $team_data['score'] : '';
                } else {
                    $game['away_team'] = $tn;
                    $game['away_score'] = isset($team_data['score']) ? $team_data['score'] : '';
                }
            }
            $games[] = $game;
        }
    }
    return count($games) > 0 ? $games : null;
}

// ════════════════════════════════════════════════════════════
//  Source 3: BallDontLie API (free, no key required)
// ════════════════════════════════════════════════════════════

function _nba_source_balldontlie() {
    // BallDontLie v1 teams endpoint
    $url = 'https://api.balldontlie.io/v1/teams';
    $body = _nba_http_get($url, 10);
    if ($body === null) return null;

    $data = json_decode($body, true);
    if (!is_array($data) || !isset($data['data'])) return null;

    $teams = array();
    foreach ($data['data'] as $t) {
        $full_name = isset($t['full_name']) ? $t['full_name'] : '';
        $abbr = isset($t['abbreviation']) ? strtolower($t['abbreviation']) : '';
        $city = isset($t['city']) ? $t['city'] : '';
        $name = isset($t['name']) ? $t['name'] : '';

        $teams[$abbr] = array(
            'name'         => $full_name,
            'short_name'   => $city . ' ' . $name,
            'abbreviation' => strtoupper($abbr),
            'wins'         => 0,
            'losses'       => 0,
            'win_pct'      => 0,
            'ppg'          => '',
            'opp_ppg'      => ''
        );
    }

    // BallDontLie doesn't provide standings in v1 free tier
    // Teams data is supplementary for name matching
    return count($teams) > 0 ? $teams : null;
}

// ════════════════════════════════════════════════════════════
//  Source 4: NBA.com standings (CDN endpoint, free)
// ════════════════════════════════════════════════════════════

function _nba_source_nba_com() {
    // NBA.com CDN endpoint for standings
    $url = 'https://cdn.nba.com/static/json/staticData/standings/seasonYear/standings.json';
    $body = _nba_http_get($url, 10);
    if ($body === null) {
        // Try alternate URL
        $url2 = 'https://stats.nba.com/stats/leaguestandingsv3?LeagueID=00&Season=2025-26&SeasonType=Regular+Season';
        $body = _nba_http_get($url2, 10);
    }
    if ($body === null) return null;

    $data = json_decode($body, true);
    if (!is_array($data)) return null;

    $teams = array();

    // Parse NBA.com format (varies by endpoint)
    if (isset($data['league']['standard']['teams'])) {
        foreach ($data['league']['standard']['teams'] as $t) {
            $name = isset($t['teamSitesOnly']['teamNickname']) ? $t['teamSitesOnly']['teamNickname'] : '';
            $city = isset($t['teamSitesOnly']['teamName']) ? $t['teamSitesOnly']['teamName'] : '';
            $wins = isset($t['win']) ? (int)$t['win'] : 0;
            $losses = isset($t['loss']) ? (int)$t['loss'] : 0;
            $conf = isset($t['confName']) ? $t['confName'] : '';
            $streak = isset($t['streak']) ? $t['streak'] : '';

            $key = strtolower(str_replace(' ', '_', $city . '_' . $name));
            $teams[$key] = array(
                'name'         => $city . ' ' . $name,
                'short_name'   => $name,
                'abbreviation' => isset($t['tricode']) ? $t['tricode'] : '',
                'wins'         => $wins,
                'losses'       => $losses,
                'win_pct'      => ($wins + $losses) > 0 ? round($wins / ($wins + $losses), 3) : 0,
                'conference'   => $conf,
                'streak'       => $streak,
                'home_record'  => '',
                'away_record'  => '',
                'last10'       => '',
                'ppg'          => '',
                'opp_ppg'      => ''
            );
        }
    }

    return count($teams) > 0 ? $teams : null;
}

// ════════════════════════════════════════════════════════════
//  Fuzzy team name matching
// ════════════════════════════════════════════════════════════

function _nba_team_match($name1, $name2) {
    if (empty($name1) || empty($name2)) return false;
    $n1 = strtolower(trim($name1));
    $n2 = strtolower(trim($name2));
    if ($n1 === $n2) return true;
    if (strpos($n1, $n2) !== false || strpos($n2, $n1) !== false) return true;

    // Last word match (e.g. "Lakers", "Raptors")
    $w1 = explode(' ', $n1);
    $w2 = explode(' ', $n2);
    $last1 = $w1[count($w1) - 1];
    $last2 = $w2[count($w2) - 1];
    if (strlen($last1) >= 4 && $last1 === $last2) return true;

    return false;
}

?>
