<?php
/**
 * Sports Failover API Configuration
 * 
 * Defines failover chains for each sport and data type.
 * Each chain is tried in order — first successful response wins.
 * 
 * Sources (all free tier / no-auth):
 *   ESPN v2 API       — Primary for all sports (current)
 *   NHL Web API       — Official NHL API (api-web.nhle.com)
 *   MLB Stats API     — Official MLB API (statsapi.mlb.com)
 *   TheSportsDB       — Free open API for team/schedule data
 *   BallDontLie       — Free NBA/NFL/MLB stats API
 *   NBA CDN           — Official NBA scoreboard CDN
 */

// Failover chain definitions: sport → data_type → ordered list of sources
$FAILOVER_CHAINS = [

    // ─── NBA ───────────────────────────────────────────────────────
    'NBA' => [
        'standings' => [
            [
                'name'    => 'ESPN NBA Standings',
                'url'     => 'https://site.api.espn.com/apis/v2/sports/basketball/nba/standings',
                'parser'  => 'parse_espn_standings',
                'timeout' => 8,
            ],
            [
                'name'    => 'NBA CDN Scoreboard',
                'url'     => 'https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json',
                'parser'  => 'parse_nba_cdn_scoreboard',
                'timeout' => 8,
            ],
            [
                'name'    => 'BallDontLie Teams',
                'url'     => 'https://api.balldontlie.io/v1/teams',
                'parser'  => 'parse_balldontlie_teams',
                'timeout' => 10,
                'headers' => ['Authorization: 4db537a0-cca0-458d-b6a7-34f1e4b1a4f3'],
            ],
            [
                'name'    => 'TheSportsDB NBA',
                'url'     => 'https://www.thesportsdb.com/api/v1/json/3/search_all_teams.php?l=NBA',
                'parser'  => 'parse_thesportsdb_teams',
                'timeout' => 10,
            ],
        ],
        'scoreboard' => [
            [
                'name'    => 'ESPN NBA Scoreboard',
                'url'     => 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard',
                'parser'  => 'parse_espn_scoreboard',
                'timeout' => 8,
            ],
            [
                'name'    => 'NBA CDN Scoreboard',
                'url'     => 'https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json',
                'parser'  => 'parse_nba_cdn_scoreboard',
                'timeout' => 8,
            ],
            [
                'name'    => 'BallDontLie Games',
                'url'     => 'https://api.balldontlie.io/v1/games?dates[]=' . date('Y-m-d'),
                'parser'  => 'parse_balldontlie_games',
                'timeout' => 10,
                'headers' => ['Authorization: 4db537a0-cca0-458d-b6a7-34f1e4b1a4f3'],
            ],
        ],
        'injuries' => [
            [
                'name'    => 'ESPN NBA Injuries',
                'url'     => 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries',
                'parser'  => 'parse_espn_injuries',
                'timeout' => 8,
            ],
        ],
    ],

    // ─── NHL ───────────────────────────────────────────────────────
    'NHL' => [
        'standings' => [
            [
                'name'    => 'ESPN NHL Standings',
                'url'     => 'https://site.api.espn.com/apis/v2/sports/hockey/nhl/standings',
                'parser'  => 'parse_espn_standings',
                'timeout' => 8,
            ],
            [
                'name'    => 'NHL Web API Standings',
                'url'     => 'https://api-web.nhle.com/v1/standings/now',
                'parser'  => 'parse_nhl_api_standings',
                'timeout' => 8,
            ],
            [
                'name'    => 'TheSportsDB NHL',
                'url'     => 'https://www.thesportsdb.com/api/v1/json/3/search_all_teams.php?l=NHL',
                'parser'  => 'parse_thesportsdb_teams',
                'timeout' => 10,
            ],
        ],
        'scoreboard' => [
            [
                'name'    => 'ESPN NHL Scoreboard',
                'url'     => 'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard',
                'parser'  => 'parse_espn_scoreboard',
                'timeout' => 8,
            ],
            [
                'name'    => 'NHL Web API Schedule',
                'url'     => 'https://api-web.nhle.com/v1/schedule/now',
                'parser'  => 'parse_nhl_api_schedule',
                'timeout' => 8,
            ],
        ],
        'injuries' => [
            [
                'name'    => 'ESPN NHL Injuries',
                'url'     => 'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/injuries',
                'parser'  => 'parse_espn_injuries',
                'timeout' => 8,
            ],
        ],
    ],

    // ─── NFL ───────────────────────────────────────────────────────
    'NFL' => [
        'standings' => [
            [
                'name'    => 'ESPN NFL Standings',
                'url'     => 'https://site.api.espn.com/apis/v2/sports/football/nfl/standings',
                'parser'  => 'parse_espn_standings',
                'timeout' => 8,
            ],
            [
                'name'    => 'TheSportsDB NFL',
                'url'     => 'https://www.thesportsdb.com/api/v1/json/3/search_all_teams.php?l=NFL',
                'parser'  => 'parse_thesportsdb_teams',
                'timeout' => 10,
            ],
        ],
        'scoreboard' => [
            [
                'name'    => 'ESPN NFL Scoreboard',
                'url'     => 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard',
                'parser'  => 'parse_espn_scoreboard',
                'timeout' => 8,
            ],
        ],
        'injuries' => [
            [
                'name'    => 'ESPN NFL Injuries',
                'url'     => 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries',
                'parser'  => 'parse_espn_injuries',
                'timeout' => 8,
            ],
        ],
    ],

    // ─── MLB ───────────────────────────────────────────────────────
    'MLB' => [
        'standings' => [
            [
                'name'    => 'ESPN MLB Standings',
                'url'     => 'https://site.api.espn.com/apis/v2/sports/baseball/mlb/standings',
                'parser'  => 'parse_espn_standings',
                'timeout' => 8,
            ],
            [
                'name'    => 'MLB Stats API Standings',
                'url'     => 'https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=' . date('Y'),
                'parser'  => 'parse_mlb_api_standings',
                'timeout' => 8,
            ],
            [
                'name'    => 'TheSportsDB MLB',
                'url'     => 'https://www.thesportsdb.com/api/v1/json/3/search_all_teams.php?l=MLB',
                'parser'  => 'parse_thesportsdb_teams',
                'timeout' => 10,
            ],
        ],
        'scoreboard' => [
            [
                'name'    => 'ESPN MLB Scoreboard',
                'url'     => 'https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard',
                'parser'  => 'parse_espn_scoreboard',
                'timeout' => 8,
            ],
            [
                'name'    => 'MLB Stats API Schedule',
                'url'     => 'https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=' . date('Y-m-d'),
                'parser'  => 'parse_mlb_api_schedule',
                'timeout' => 8,
            ],
        ],
        'injuries' => [
            [
                'name'    => 'ESPN MLB Injuries',
                'url'     => 'https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/injuries',
                'parser'  => 'parse_espn_injuries',
                'timeout' => 8,
            ],
        ],
    ],
];

/**
 * Get failover chain for a specific sport and data type
 */
function get_failover_chain($sport, $data_type) {
    global $FAILOVER_CHAINS;
    $sport = strtoupper($sport);
    return isset($FAILOVER_CHAINS[$sport][$data_type])
        ? $FAILOVER_CHAINS[$sport][$data_type]
        : [];
}

/**
 * Get all supported sports
 */
function get_supported_sports() {
    global $FAILOVER_CHAINS;
    return array_keys($FAILOVER_CHAINS);
}

/**
 * Get all data types for a sport
 */
function get_data_types($sport) {
    global $FAILOVER_CHAINS;
    $sport = strtoupper($sport);
    return isset($FAILOVER_CHAINS[$sport])
        ? array_keys($FAILOVER_CHAINS[$sport])
        : [];
}
