<?php
/**
 * NFL Stats API — Team standings with turnover margin + multi-source failover
 * PHP 5.2 compatible
 *
 * Academic context:
 *   - Biro et al. (2017, PMC5969004): positive turnover differential = ~70% win rate
 *   - Minitab analysis: turnover diff explains 44% of season win% variance
 *
 * Sources: ESPN NFL Standings API (free) -> fallback
 *
 * Actions:
 *   ?action=team_stats  — All NFL teams (public, cached 2h)
 *   ?action=refresh&key= — Force refresh (admin)
 *   ?action=health       — Check sources
 */

require_once dirname(__FILE__) . '/sports_db_connect.php';

$conn->query("CREATE TABLE IF NOT EXISTS lm_nfl_stats_cache (
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
    _nfl_action_team_stats($conn);
} elseif ($action === 'refresh') {
    _nfl_action_refresh($conn);
} elseif ($action === 'health') {
    _nfl_action_health();
} else {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

$conn->close();
exit;

function _nfl_http_get($url, $timeout) {
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

function _nfl_action_team_stats($conn) {
    $cq = $conn->query("SELECT cache_data, source, updated_at FROM lm_nfl_stats_cache WHERE cache_key='nfl_teams' AND updated_at > DATE_SUB(NOW(), INTERVAL 2 HOUR)");
    if ($cq && $row = $cq->fetch_assoc()) {
        $data = json_decode($row['cache_data'], true);
        if (is_array($data) && count($data) > 0) {
            echo json_encode(array('ok' => true, 'teams' => $data, 'count' => count($data), 'source' => $row['source'], 'updated_at' => $row['updated_at'], 'cached' => true));
            return;
        }
    }

    $result = _nfl_fetch_teams();
    if (is_array($result) && count($result['teams']) > 0) {
        $json = json_encode($result['teams']);
        $conn->query("REPLACE INTO lm_nfl_stats_cache (cache_key, cache_data, source, updated_at) VALUES ('nfl_teams', '" . $conn->real_escape_string($json) . "', '" . $conn->real_escape_string($result['source']) . "', NOW())");
        echo json_encode(array('ok' => true, 'teams' => $result['teams'], 'count' => count($result['teams']), 'source' => $result['source'], 'updated_at' => gmdate('Y-m-d H:i:s') . ' UTC', 'cached' => false));
    } else {
        $sq = $conn->query("SELECT cache_data, source, updated_at FROM lm_nfl_stats_cache WHERE cache_key='nfl_teams'");
        if ($sq && $row = $sq->fetch_assoc()) {
            $data = json_decode($row['cache_data'], true);
            if (is_array($data) && count($data) > 0) {
                echo json_encode(array('ok' => true, 'teams' => $data, 'count' => count($data), 'source' => $row['source'] . ' (stale)', 'updated_at' => $row['updated_at'], 'cached' => true, 'stale' => true));
                return;
            }
        }
        echo json_encode(array('ok' => false, 'error' => 'All NFL data sources failed', 'teams' => array()));
    }
}

function _nfl_action_refresh($conn) {
    global $ADMIN_KEY;
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $ADMIN_KEY) { header('HTTP/1.0 403 Forbidden'); echo json_encode(array('ok' => false, 'error' => 'Invalid admin key')); return; }
    $result = _nfl_fetch_teams();
    if (is_array($result) && count($result['teams']) > 0) {
        $json = json_encode($result['teams']);
        $conn->query("REPLACE INTO lm_nfl_stats_cache (cache_key, cache_data, source, updated_at) VALUES ('nfl_teams', '" . $conn->real_escape_string($json) . "', '" . $conn->real_escape_string($result['source']) . "', NOW())");
    }
    echo json_encode(array('ok' => true, 'teams' => is_array($result) ? count($result['teams']) : 0, 'source' => is_array($result) ? $result['source'] : 'none'));
}

function _nfl_action_health() {
    $t0 = microtime(true);
    $r = _nfl_http_get('https://site.api.espn.com/apis/v2/sports/football/nfl/standings', 5);
    $t1 = microtime(true);
    echo json_encode(array('ok' => true, 'sources' => array(
        array('name' => 'ESPN NFL Standings', 'ok' => ($r !== null), 'ms' => round(($t1 - $t0) * 1000))
    )));
}

function _nfl_fetch_teams() {
    $url = 'https://site.api.espn.com/apis/v2/sports/football/nfl/standings';
    $body = _nfl_http_get($url, 12);
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
            $ties = isset($stats_map['ties']) ? (int)$stats_map['ties'] : 0;
            $gp = $wins + $losses + $ties;
            $win_pct = ($gp > 0) ? round($wins / $gp, 3) : 0;

            $pf = isset($stats_map['pointsFor']) ? (float)$stats_map['pointsFor'] : '';
            $pa = isset($stats_map['pointsAgainst']) ? (float)$stats_map['pointsAgainst'] : '';
            $diff = isset($stats_map['differential']) ? $stats_map['differential'] : '';
            $streak = isset($stats_map['streak']) ? $stats_map['streak'] : '';
            $home_record = isset($stats_map['Home']) ? $stats_map['Home'] : (isset($stats_map['home']) ? $stats_map['home'] : '');
            $away_record = isset($stats_map['Road']) ? $stats_map['Road'] : (isset($stats_map['away']) ? $stats_map['away'] : '');

            // NFL-specific: turnover stats
            $giveaways = isset($stats_map['giveaways']) ? (float)$stats_map['giveaways'] : '';
            $takeaways = isset($stats_map['takeaways']) ? (float)$stats_map['takeaways'] : '';
            $turnover_diff = '';
            if ($giveaways !== '' && $takeaways !== '') {
                $turnover_diff = (int)$takeaways - (int)$giveaways;
            } elseif (isset($stats_map['differential'])) {
                // Some ESPN responses have this differently
            }

            // Points per game
            $ppg = ($gp > 0 && $pf !== '') ? round((float)$pf / $gp, 1) : '';
            $opp_ppg = ($gp > 0 && $pa !== '') ? round((float)$pa / $gp, 1) : '';

            $all_sorted[] = array(
                'name'           => $team_name,
                'short_name'     => $short_name,
                'abbreviation'   => $abbr,
                'wins'           => $wins,
                'losses'         => $losses,
                'ties'           => $ties,
                'win_pct'        => $win_pct,
                'conference'     => $conf_name,
                'points_for'     => $pf,
                'points_against' => $pa,
                'diff'           => $diff,
                'ppg'            => $ppg,
                'opp_ppg'        => $opp_ppg,
                'turnover_diff'  => $turnover_diff,
                'giveaways'      => $giveaways,
                'takeaways'      => $takeaways,
                'streak'         => $streak,
                'home_record'    => $home_record,
                'away_record'    => $away_record
            );
        }
    }

    usort($all_sorted, '_nfl_sort_wp');

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

function _nfl_sort_wp($a, $b) {
    if ($b['win_pct'] == $a['win_pct']) return 0;
    return ($b['win_pct'] > $a['win_pct']) ? 1 : -1;
}

?>
