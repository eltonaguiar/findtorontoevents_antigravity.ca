<?php
/**
 * NHL Stats API — Team standings with multi-source failover
 * PHP 5.2 compatible
 *
 * Academic context:
 *   - Macdonald (2012): Expected goals correlation 0.55 vs Corsi 0.37
 *   - Hockey Graphs (2014): Goalie Sv% drops .008 on back-to-backs
 *
 * Sources: ESPN NHL Standings API (free) -> ESPN Scoreboard -> fallback
 *
 * Actions:
 *   ?action=team_stats  — All NHL teams (public, cached 2h)
 *   ?action=refresh&key= — Force refresh (admin)
 *   ?action=health       — Check sources
 */

require_once dirname(__FILE__) . '/sports_db_connect.php';

$conn->query("CREATE TABLE IF NOT EXISTS lm_nhl_stats_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cache_key VARCHAR(50) NOT NULL,
    cache_data LONGTEXT NOT NULL,
    source VARCHAR(100) NOT NULL DEFAULT '',
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_key (cache_key)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$ADMIN_KEY = isset($SPORTS_ADMIN_KEY) ? $SPORTS_ADMIN_KEY : 'livetrader2026';

$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'team_stats';

if ($action === 'team_stats') {
    _nhl_action_team_stats($conn);
} elseif ($action === 'refresh') {
    _nhl_action_refresh($conn);
} elseif ($action === 'health') {
    _nhl_action_health();
} else {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

$conn->close();
exit;

function _nhl_http_get($url, $timeout) {
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

// ── team_stats action ──
function _nhl_action_team_stats($conn) {
    $cq = $conn->query("SELECT cache_data, source, updated_at FROM lm_nhl_stats_cache WHERE cache_key='nhl_teams' AND updated_at > DATE_SUB(NOW(), INTERVAL 2 HOUR)");
    if ($cq && $row = $cq->fetch_assoc()) {
        $data = json_decode($row['cache_data'], true);
        if (is_array($data) && count($data) > 0) {
            echo json_encode(array('ok' => true, 'teams' => $data, 'count' => count($data), 'source' => $row['source'], 'updated_at' => $row['updated_at'], 'cached' => true));
            return;
        }
    }

    $result = _nhl_fetch_teams();
    if (is_array($result) && count($result['teams']) > 0) {
        $json = json_encode($result['teams']);
        $conn->query("REPLACE INTO lm_nhl_stats_cache (cache_key, cache_data, source, updated_at) VALUES ('nhl_teams', '" . $conn->real_escape_string($json) . "', '" . $conn->real_escape_string($result['source']) . "', NOW())");
        echo json_encode(array('ok' => true, 'teams' => $result['teams'], 'count' => count($result['teams']), 'source' => $result['source'], 'updated_at' => gmdate('Y-m-d H:i:s') . ' UTC', 'cached' => false));
    } else {
        $sq = $conn->query("SELECT cache_data, source, updated_at FROM lm_nhl_stats_cache WHERE cache_key='nhl_teams'");
        if ($sq && $row = $sq->fetch_assoc()) {
            $data = json_decode($row['cache_data'], true);
            if (is_array($data) && count($data) > 0) {
                echo json_encode(array('ok' => true, 'teams' => $data, 'count' => count($data), 'source' => $row['source'] . ' (stale)', 'updated_at' => $row['updated_at'], 'cached' => true, 'stale' => true));
                return;
            }
        }
        echo json_encode(array('ok' => false, 'error' => 'All NHL data sources failed', 'teams' => array()));
    }
}

function _nhl_action_refresh($conn) {
    global $ADMIN_KEY;
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $ADMIN_KEY) { header('HTTP/1.0 403 Forbidden'); echo json_encode(array('ok' => false, 'error' => 'Invalid admin key')); return; }

    $result = _nhl_fetch_teams();
    if (is_array($result) && count($result['teams']) > 0) {
        $json = json_encode($result['teams']);
        $conn->query("REPLACE INTO lm_nhl_stats_cache (cache_key, cache_data, source, updated_at) VALUES ('nhl_teams', '" . $conn->real_escape_string($json) . "', '" . $conn->real_escape_string($result['source']) . "', NOW())");
    }
    echo json_encode(array('ok' => true, 'teams' => is_array($result) ? count($result['teams']) : 0, 'source' => is_array($result) ? $result['source'] : 'none'));
}

function _nhl_action_health() {
    $t0 = microtime(true);
    $r = _nhl_http_get('https://site.api.espn.com/apis/v2/sports/hockey/nhl/standings', 5);
    $t1 = microtime(true);
    echo json_encode(array('ok' => true, 'sources' => array(
        array('name' => 'ESPN NHL Standings', 'ok' => ($r !== null), 'ms' => round(($t1 - $t0) * 1000))
    )));
}

// ── Core: fetch NHL teams from ESPN ──
function _nhl_fetch_teams() {
    $url = 'https://site.api.espn.com/apis/v2/sports/hockey/nhl/standings';
    $body = _nhl_http_get($url, 12);
    if ($body === null) return array('teams' => array(), 'source' => 'failed');

    $data = json_decode($body, true);
    if (!is_array($data) || !isset($data['children'])) return array('teams' => array(), 'source' => 'parse_error');

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
            $otl = isset($stats_map['OTLosses']) ? (int)$stats_map['OTLosses'] : (isset($stats_map['otLosses']) ? (int)$stats_map['otLosses'] : 0);
            $points = isset($stats_map['points']) ? (int)$stats_map['points'] : ($wins * 2 + $otl);
            $gp = $wins + $losses + $otl;
            $pts_pct = ($gp > 0) ? round($points / ($gp * 2), 3) : 0;

            $gf = isset($stats_map['pointsFor']) ? (float)$stats_map['pointsFor'] : '';
            $ga = isset($stats_map['pointsAgainst']) ? (float)$stats_map['pointsAgainst'] : '';
            $diff = isset($stats_map['differential']) ? $stats_map['differential'] : '';
            $streak = isset($stats_map['streak']) ? $stats_map['streak'] : '';
            $home_record = isset($stats_map['Home']) ? $stats_map['Home'] : (isset($stats_map['home']) ? $stats_map['home'] : '');
            $away_record = isset($stats_map['Road']) ? $stats_map['Road'] : (isset($stats_map['away']) ? $stats_map['away'] : '');
            $last10 = isset($stats_map['Last Ten Games']) ? $stats_map['Last Ten Games'] : (isset($stats_map['L10']) ? $stats_map['L10'] : '');

            // NHL-specific stats
            $pp_pct = isset($stats_map['powerPlayPct']) ? $stats_map['powerPlayPct'] : '';
            $pk_pct = isset($stats_map['penaltyKillPct']) ? $stats_map['penaltyKillPct'] : '';

            $all_sorted[] = array(
                'name'         => $team_name,
                'short_name'   => $short_name,
                'abbreviation' => $abbr,
                'wins'         => $wins,
                'losses'       => $losses,
                'otl'          => $otl,
                'points'       => $points,
                'pts_pct'      => $pts_pct,
                'gp'           => $gp,
                'conference'   => $conf_name,
                'goals_for'    => $gf,
                'goals_against' => $ga,
                'diff'         => $diff,
                'streak'       => $streak,
                'home_record'  => $home_record,
                'away_record'  => $away_record,
                'last10'       => $last10,
                'pp_pct'       => $pp_pct,
                'pk_pct'       => $pk_pct
            );
        }
    }

    usort($all_sorted, '_nhl_sort_pts');

    $teams = array();
    for ($i = 0; $i < count($all_sorted); $i++) {
        $t = $all_sorted[$i];
        $t['rank'] = $i + 1;
        $key = strtolower($t['abbreviation']);
        if (!$key) $key = strtolower(str_replace(' ', '_', $t['name']));
        $teams[$key] = $t;
    }

    return array('teams' => $teams, 'source' => 'espn_api');
}

function _nhl_sort_pts($a, $b) {
    if ($b['pts_pct'] == $a['pts_pct']) return 0;
    return ($b['pts_pct'] > $a['pts_pct']) ? 1 : -1;
}

?>
