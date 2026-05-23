<?php
/**
 * Sports Failover Proxy
 * 
 * Unified endpoint that cascades through multiple free APIs per sport.
 * Returns the first successful response, logging which source succeeded.
 * 
 * Usage:
 *   ?sport=NBA&type=standings     → NBA standings (ESPN → NBA CDN → BallDontLie → TheSportsDB)
 *   ?sport=NHL&type=standings     → NHL standings (ESPN → NHL Web API → TheSportsDB)
 *   ?sport=MLB&type=scoreboard    → MLB scores   (ESPN → MLB Stats API)
 *   ?action=health                → Health check of all failover sources
 *   ?action=sources               → List all configured sources
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: public, max-age=300'); // 5 min cache

require_once __DIR__ . '/sports_failover_config.php';

$action = $_GET['action'] ?? '';
$sport  = strtoupper($_GET['sport'] ?? '');
$type   = $_GET['type'] ?? 'standings';

// ─── Action: list sources ─────────────────────────────────────
if ($action === 'sources') {
    $result = [];
    foreach (get_supported_sports() as $sp) {
        $result[$sp] = [];
        foreach (get_data_types($sp) as $dt) {
            $chain = get_failover_chain($sp, $dt);
            $result[$sp][$dt] = array_map(function($src) {
                return [
                    'name'    => $src['name'],
                    'url'     => preg_replace('/[a-f0-9-]{20,}/', '***', $src['url']), // mask keys
                    'timeout' => $src['timeout'],
                ];
            }, $chain);
        }
    }
    echo json_encode(['ok' => true, 'sources' => $result, 'timestamp' => gmdate('c')]);
    exit;
}

// ─── Action: health check ─────────────────────────────────────
if ($action === 'health') {
    $results = [];
    foreach (get_supported_sports() as $sp) {
        foreach (get_data_types($sp) as $dt) {
            $chain = get_failover_chain($sp, $dt);
            foreach ($chain as $src) {
                $start = microtime(true);
                $ok = false;
                $error = null;
                try {
                    $ctx = stream_context_create([
                        'http' => [
                            'timeout' => min($src['timeout'], 5),
                            'method'  => 'HEAD',
                            'header'  => isset($src['headers']) ? implode("\r\n", $src['headers']) : '',
                        ],
                        'ssl' => ['verify_peer' => false, 'verify_peer_name' => false],
                    ]);
                    $headers = @get_headers($src['url'], true, $ctx);
                    $ok = $headers && (strpos($headers[0], '200') !== false || strpos($headers[0], '301') !== false);
                } catch (Exception $e) {
                    $error = $e->getMessage();
                }
                $elapsed = round((microtime(true) - $start) * 1000);
                $results[] = [
                    'sport'      => $sp,
                    'data_type'  => $dt,
                    'source'     => $src['name'],
                    'ok'         => $ok,
                    'latency_ms' => $elapsed,
                    'error'      => $error,
                ];
            }
        }
    }
    $healthy = count(array_filter($results, function($r) { return $r['ok']; }));
    echo json_encode([
        'ok'        => true,
        'healthy'   => $healthy,
        'total'     => count($results),
        'results'   => $results,
        'timestamp' => gmdate('c'),
    ]);
    exit;
}

// ─── Main: fetch with failover ────────────────────────────────
if (!$sport) {
    echo json_encode(['ok' => false, 'error' => 'Missing sport parameter. Use ?sport=NBA|NHL|NFL|MLB']);
    exit;
}

$chain = get_failover_chain($sport, $type);
if (empty($chain)) {
    echo json_encode(['ok' => false, 'error' => "No failover chain for $sport/$type"]);
    exit;
}

$attempts = [];
$result_data = null;

foreach ($chain as $idx => $source) {
    $start = microtime(true);
    $attempt = [
        'source'  => $source['name'],
        'url'     => preg_replace('/[a-f0-9-]{20,}/', '***', $source['url']),
        'attempt' => $idx + 1,
    ];

    try {
        $headers_arr = ['User-Agent: FindTorontoEvents-SportsBetting/1.0'];
        if (isset($source['headers'])) {
            $headers_arr = array_merge($headers_arr, $source['headers']);
        }

        $ctx = stream_context_create([
            'http' => [
                'timeout' => $source['timeout'],
                'header'  => implode("\r\n", $headers_arr),
            ],
            'ssl' => ['verify_peer' => false, 'verify_peer_name' => false],
        ]);

        $raw = @file_get_contents($source['url'], false, $ctx);
        $elapsed = round((microtime(true) - $start) * 1000);

        if ($raw === false) {
            $attempt['ok'] = false;
            $attempt['error'] = 'HTTP fetch failed';
            $attempt['latency_ms'] = $elapsed;
            $attempts[] = $attempt;
            continue;
        }

        $data = json_decode($raw, true);
        if ($data === null) {
            $attempt['ok'] = false;
            $attempt['error'] = 'JSON decode failed';
            $attempt['latency_ms'] = $elapsed;
            $attempts[] = $attempt;
            continue;
        }

        // Parse through the appropriate parser
        $parser = $source['parser'];
        if (function_exists($parser)) {
            $parsed = $parser($data, $sport);
        } else {
            $parsed = ['raw' => $data];
        }

        if (!empty($parsed)) {
            $attempt['ok'] = true;
            $attempt['latency_ms'] = $elapsed;
            $attempt['record_count'] = is_array($parsed) && isset($parsed['teams']) ? count($parsed['teams']) : 0;
            $attempts[] = $attempt;
            $result_data = $parsed;
            break; // Success — stop cascading
        } else {
            $attempt['ok'] = false;
            $attempt['error'] = 'Parser returned empty result';
            $attempt['latency_ms'] = $elapsed;
            $attempts[] = $attempt;
        }
    } catch (Exception $e) {
        $elapsed = round((microtime(true) - $start) * 1000);
        $attempt['ok'] = false;
        $attempt['error'] = $e->getMessage();
        $attempt['latency_ms'] = $elapsed;
        $attempts[] = $attempt;
    }
}

$success_source = null;
foreach ($attempts as $a) {
    if (!empty($a['ok'])) {
        $success_source = $a['source'];
        break;
    }
}

if ($result_data) {
    echo json_encode([
        'ok'             => true,
        'sport'          => $sport,
        'data_type'      => $type,
        'source'         => $success_source,
        'failover_chain' => $attempts,
        'data'           => $result_data,
        'timestamp'      => gmdate('c'),
    ]);
} else {
    echo json_encode([
        'ok'             => false,
        'sport'          => $sport,
        'data_type'      => $type,
        'error'          => 'All failover sources failed',
        'failover_chain' => $attempts,
        'timestamp'      => gmdate('c'),
    ]);
}

// ════════════════════════════════════════════════════════════════
//  P A R S E R S  — Normalize each API response into a common shape
// ════════════════════════════════════════════════════════════════

/**
 * Parse ESPN v2 Standings API (works for NBA, NHL, NFL, MLB)
 */
function parse_espn_standings($data, $sport) {
    $teams = [];
    $children = $data['children'] ?? [];
    foreach ($children as $conference) {
        $conf_name = $conference['name'] ?? '';
        $standings = $conference['standings']['entries'] ?? [];
        foreach ($standings as $entry) {
            $team = $entry['team'] ?? [];
            $stats = [];
            foreach ($entry['stats'] ?? [] as $stat) {
                $stats[$stat['name'] ?? ''] = $stat['value'] ?? $stat['displayValue'] ?? '';
            }
            $teams[] = [
                'name'         => $team['displayName'] ?? '',
                'short_name'   => $team['shortDisplayName'] ?? '',
                'abbreviation' => $team['abbreviation'] ?? '',
                'conference'   => $conf_name,
                'wins'         => intval($stats['wins'] ?? 0),
                'losses'       => intval($stats['losses'] ?? 0),
                'win_pct'      => floatval($stats['winPercent'] ?? $stats['winPct'] ?? 0),
                'streak'       => $stats['streak'] ?? '',
                'home_record'  => $stats['Home'] ?? $stats['home'] ?? '',
                'away_record'  => $stats['Road'] ?? $stats['road'] ?? $stats['Away'] ?? '',
                'points'       => intval($stats['points'] ?? 0),
                'source'       => 'espn_standings',
            ];
        }
    }
    return ['teams' => $teams, 'count' => count($teams)];
}

/**
 * Parse ESPN Scoreboard API
 */
function parse_espn_scoreboard($data, $sport) {
    $games = [];
    foreach ($data['events'] ?? [] as $event) {
        $comp = $event['competitions'][0] ?? [];
        $competitors = $comp['competitors'] ?? [];
        $home = null; $away = null;
        foreach ($competitors as $c) {
            if ($c['homeAway'] === 'home') $home = $c;
            else $away = $c;
        }
        $games[] = [
            'id'           => $event['id'] ?? '',
            'date'         => $event['date'] ?? '',
            'status'       => $event['status']['type']['description'] ?? '',
            'home_team'    => $home['team']['displayName'] ?? '',
            'home_abbrev'  => $home['team']['abbreviation'] ?? '',
            'home_score'   => intval($home['score'] ?? 0),
            'away_team'    => $away['team']['displayName'] ?? '',
            'away_abbrev'  => $away['team']['abbreviation'] ?? '',
            'away_score'   => intval($away['score'] ?? 0),
            'venue'        => $comp['venue']['fullName'] ?? '',
            'source'       => 'espn_scoreboard',
        ];
    }
    return ['games' => $games, 'count' => count($games)];
}

/**
 * Parse ESPN Injuries API
 */
function parse_espn_injuries($data, $sport) {
    $teams = [];
    foreach ($data['injuries'] ?? $data as $group) {
        $team_name = $group['team']['displayName'] ?? '';
        $team_abbr = $group['team']['abbreviation'] ?? '';
        $injuries = [];
        foreach ($group['injuries'] ?? [] as $inj) {
            $injuries[] = [
                'player'     => $inj['athlete']['displayName'] ?? '',
                'position'   => $inj['athlete']['position']['abbreviation'] ?? '',
                'status'     => $inj['status'] ?? '',
                'type'       => $inj['type'] ?? '',
                'detail'     => $inj['details']['detail'] ?? $inj['longComment'] ?? '',
            ];
        }
        if ($team_name) {
            $teams[] = [
                'name'         => $team_name,
                'abbreviation' => $team_abbr,
                'injuries'     => $injuries,
                'out'          => count(array_filter($injuries, function($i) {
                    return stripos($i['status'], 'Out') !== false;
                })),
                'questionable' => count(array_filter($injuries, function($i) {
                    return stripos($i['status'], 'Questionable') !== false
                        || stripos($i['status'], 'Day-To-Day') !== false;
                })),
                'source'       => 'espn_injuries',
            ];
        }
    }
    return ['teams' => $teams, 'count' => count($teams)];
}

/**
 * Parse NHL Web API Standings (api-web.nhle.com)
 */
function parse_nhl_api_standings($data, $sport) {
    $teams = [];
    foreach ($data['standings'] ?? [] as $entry) {
        $teams[] = [
            'name'         => $entry['teamName']['default'] ?? '',
            'short_name'   => $entry['teamCommonName']['default'] ?? '',
            'abbreviation' => $entry['teamAbbrev']['default'] ?? '',
            'conference'   => $entry['conferenceName'] ?? '',
            'division'     => $entry['divisionName'] ?? '',
            'wins'         => intval($entry['wins'] ?? 0),
            'losses'       => intval($entry['losses'] ?? 0),
            'otl'          => intval($entry['otLosses'] ?? 0),
            'points'       => intval($entry['points'] ?? 0),
            'win_pct'      => floatval($entry['pointPctg'] ?? 0),
            'goals_for'    => intval($entry['goalFor'] ?? 0),
            'goals_against'=> intval($entry['goalAgainst'] ?? 0),
            'goal_diff'    => intval($entry['goalDifferential'] ?? 0),
            'streak'       => ($entry['streakCode'] ?? '') . ($entry['streakCount'] ?? ''),
            'home_record'  => ($entry['homeWins'] ?? 0) . '-' . ($entry['homeLosses'] ?? 0) . '-' . ($entry['homeOtLosses'] ?? 0),
            'away_record'  => ($entry['roadWins'] ?? 0) . '-' . ($entry['roadLosses'] ?? 0) . '-' . ($entry['roadOtLosses'] ?? 0),
            'games_played' => intval($entry['gamesPlayed'] ?? 0),
            'source'       => 'nhl_web_api',
        ];
    }
    return ['teams' => $teams, 'count' => count($teams)];
}

/**
 * Parse NHL Web API Schedule
 */
function parse_nhl_api_schedule($data, $sport) {
    $games = [];
    foreach ($data['gameWeek'] ?? [] as $day) {
        foreach ($day['games'] ?? [] as $game) {
            $games[] = [
                'id'           => $game['id'] ?? '',
                'date'         => $day['date'] ?? '',
                'status'       => $game['gameState'] ?? '',
                'home_team'    => $game['homeTeam']['placeName']['default'] ?? '',
                'home_abbrev'  => $game['homeTeam']['abbrev'] ?? '',
                'home_score'   => intval($game['homeTeam']['score'] ?? 0),
                'away_team'    => $game['awayTeam']['placeName']['default'] ?? '',
                'away_abbrev'  => $game['awayTeam']['abbrev'] ?? '',
                'away_score'   => intval($game['awayTeam']['score'] ?? 0),
                'venue'        => $game['venue']['default'] ?? '',
                'source'       => 'nhl_web_api',
            ];
        }
    }
    return ['games' => $games, 'count' => count($games)];
}

/**
 * Parse MLB Stats API Standings
 */
function parse_mlb_api_standings($data, $sport) {
    $teams = [];
    foreach ($data['records'] ?? [] as $division) {
        $div_name = $division['division']['name'] ?? '';
        foreach ($division['teamRecords'] ?? [] as $record) {
            $team = $record['team'] ?? [];
            $homeRec = $record['records']['splitRecords'] ?? [];
            $home_w = 0; $home_l = 0; $away_w = 0; $away_l = 0;
            foreach ($homeRec as $split) {
                if (($split['type'] ?? '') === 'home') {
                    $home_w = intval($split['wins'] ?? 0);
                    $home_l = intval($split['losses'] ?? 0);
                }
                if (($split['type'] ?? '') === 'away') {
                    $away_w = intval($split['wins'] ?? 0);
                    $away_l = intval($split['losses'] ?? 0);
                }
            }
            $streak = $record['streak']['streakCode'] ?? '';
            $teams[] = [
                'name'         => $team['name'] ?? '',
                'short_name'   => $team['teamName'] ?? '',
                'abbreviation' => $team['abbreviation'] ?? '',
                'division'     => $div_name,
                'wins'         => intval($record['wins'] ?? 0),
                'losses'       => intval($record['losses'] ?? 0),
                'win_pct'      => floatval($record['winningPercentage'] ?? 0),
                'streak'       => $streak,
                'home_record'  => $home_w . '-' . $home_l,
                'away_record'  => $away_w . '-' . $away_l,
                'runs_scored'  => intval($record['runsScored'] ?? 0),
                'runs_allowed' => intval($record['runsAllowed'] ?? 0),
                'run_diff'     => intval($record['runDifferential'] ?? 0),
                'games_back'   => $record['gamesBack'] ?? '',
                'source'       => 'mlb_stats_api',
            ];
        }
    }
    return ['teams' => $teams, 'count' => count($teams)];
}

/**
 * Parse MLB Stats API Schedule
 */
function parse_mlb_api_schedule($data, $sport) {
    $games = [];
    foreach ($data['dates'] ?? [] as $day) {
        foreach ($day['games'] ?? [] as $game) {
            $home = $game['teams']['home'] ?? [];
            $away = $game['teams']['away'] ?? [];
            $games[] = [
                'id'           => $game['gamePk'] ?? '',
                'date'         => $day['date'] ?? '',
                'status'       => $game['status']['detailedState'] ?? '',
                'home_team'    => $home['team']['name'] ?? '',
                'home_abbrev'  => $home['team']['abbreviation'] ?? '',
                'home_score'   => intval($home['score'] ?? 0),
                'away_team'    => $away['team']['name'] ?? '',
                'away_abbrev'  => $away['team']['abbreviation'] ?? '',
                'away_score'   => intval($away['score'] ?? 0),
                'venue'        => $game['venue']['name'] ?? '',
                'source'       => 'mlb_stats_api',
            ];
        }
    }
    return ['games' => $games, 'count' => count($games)];
}

/**
 * Parse NBA CDN Scoreboard
 */
function parse_nba_cdn_scoreboard($data, $sport) {
    $sb = $data['scoreboard'] ?? $data;
    $games = [];
    foreach ($sb['games'] ?? [] as $game) {
        $games[] = [
            'id'           => $game['gameId'] ?? '',
            'date'         => $game['gameTimeUTC'] ?? '',
            'status'       => $game['gameStatusText'] ?? '',
            'home_team'    => $game['homeTeam']['teamName'] ?? '',
            'home_abbrev'  => $game['homeTeam']['teamTricode'] ?? '',
            'home_score'   => intval($game['homeTeam']['score'] ?? 0),
            'away_team'    => $game['awayTeam']['teamName'] ?? '',
            'away_abbrev'  => $game['awayTeam']['teamTricode'] ?? '',
            'away_score'   => intval($game['awayTeam']['score'] ?? 0),
            'source'       => 'nba_cdn',
        ];
    }
    // Also works as pseudo-standings from team records
    $teams = [];
    foreach ($sb['games'] ?? [] as $game) {
        foreach (['homeTeam', 'awayTeam'] as $side) {
            $t = $game[$side] ?? [];
            $wins = intval($t['wins'] ?? 0);
            $losses = intval($t['losses'] ?? 0);
            if ($wins + $losses > 0) {
                $abbr = $t['teamTricode'] ?? '';
                if ($abbr && !isset($teams[$abbr])) {
                    $teams[$abbr] = [
                        'name'         => ($t['teamCity'] ?? '') . ' ' . ($t['teamName'] ?? ''),
                        'short_name'   => $t['teamName'] ?? '',
                        'abbreviation' => $abbr,
                        'wins'         => $wins,
                        'losses'       => $losses,
                        'win_pct'      => $wins / max(1, $wins + $losses),
                        'source'       => 'nba_cdn',
                    ];
                }
            }
        }
    }
    return [
        'games' => $games,
        'teams' => array_values($teams),
        'count' => max(count($games), count($teams)),
    ];
}

/**
 * Parse BallDontLie Teams API
 */
function parse_balldontlie_teams($data, $sport) {
    $teams = [];
    foreach ($data['data'] ?? [] as $team) {
        $teams[] = [
            'name'         => $team['full_name'] ?? '',
            'short_name'   => $team['name'] ?? '',
            'abbreviation' => $team['abbreviation'] ?? '',
            'conference'   => $team['conference'] ?? '',
            'division'     => $team['division'] ?? '',
            'city'         => $team['city'] ?? '',
            'source'       => 'balldontlie',
        ];
    }
    return ['teams' => $teams, 'count' => count($teams)];
}

/**
 * Parse BallDontLie Games API
 */
function parse_balldontlie_games($data, $sport) {
    $games = [];
    foreach ($data['data'] ?? [] as $game) {
        $games[] = [
            'id'           => $game['id'] ?? '',
            'date'         => $game['date'] ?? '',
            'status'       => $game['status'] ?? '',
            'home_team'    => $game['home_team']['full_name'] ?? '',
            'home_abbrev'  => $game['home_team']['abbreviation'] ?? '',
            'home_score'   => intval($game['home_team_score'] ?? 0),
            'away_team'    => $game['visitor_team']['full_name'] ?? '',
            'away_abbrev'  => $game['visitor_team']['abbreviation'] ?? '',
            'away_score'   => intval($game['visitor_team_score'] ?? 0),
            'source'       => 'balldontlie',
        ];
    }
    return ['games' => $games, 'count' => count($games)];
}

/**
 * Parse TheSportsDB Teams API (works for any league)
 */
function parse_thesportsdb_teams($data, $sport) {
    $teams = [];
    foreach ($data['teams'] ?? [] as $team) {
        $teams[] = [
            'name'         => $team['strTeam'] ?? '',
            'short_name'   => $team['strTeamShort'] ?? $team['strTeam'] ?? '',
            'abbreviation' => $team['strTeamShort'] ?? '',
            'league'       => $team['strLeague'] ?? '',
            'stadium'      => $team['strStadium'] ?? '',
            'location'     => $team['strStadiumLocation'] ?? '',
            'badge_url'    => $team['strBadge'] ?? '',
            'description'  => substr($team['strDescriptionEN'] ?? '', 0, 200),
            'source'       => 'thesportsdb',
        ];
    }
    return ['teams' => $teams, 'count' => count($teams)];
}
