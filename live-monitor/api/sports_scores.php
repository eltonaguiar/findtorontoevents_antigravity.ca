<?php
/**
 * Multi-source Sports Score Fetcher
 * Provides unified score data from multiple free APIs
 * PHP 5.2 compatible (no short arrays, no http_response_code, no spread operator)
 *
 * Usage as include:
 *   require_once 'sports_scores.php';
 *   $result = _scores_fetch_all('icehockey_nhl', 3);
 *   // $result = array('scores' => $score_map, 'source' => 'odds_api', 'count' => N)
 *
 * Usage standalone:
 *   ?action=test&sport=icehockey_nhl
 *   ?action=test&sport=basketball_nba&days=3
 */

require_once dirname(__FILE__) . '/db_config.php';

// ────────────────────────────────────────────────────────────
//  ESPN sport key mapping
// ────────────────────────────────────────────────────────────

$_SCORES_ESPN_MAP = array(
    'icehockey_nhl'          => 'hockey/nhl',
    'basketball_nba'         => 'basketball/nba',
    'americanfootball_nfl'   => 'football/nfl',
    'baseball_mlb'           => 'baseball/mlb',
    'basketball_ncaab'       => 'basketball/mens-college-basketball',
    'americanfootball_ncaaf' => 'football/college-football',
    'soccer_usa_mls'         => 'soccer/usa.1'
);

// ────────────────────────────────────────────────────────────
//  HTTP helper
// ────────────────────────────────────────────────────────────

function _scores_http_get($url) {
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
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
            'timeout' => 15,
            'header'  => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\nAccept: application/json\r\n"
        ),
        'ssl' => array('verify_peer' => false)
    ));
    $body = @file_get_contents($url, false, $ctx);
    return ($body === false) ? null : $body;
}

// ────────────────────────────────────────────────────────────
//  Team name matching — fuzzy, case-insensitive
// ────────────────────────────────────────────────────────────

/**
 * Check if two team names refer to the same team.
 * Handles variations like:
 *   "Toronto Maple Leafs" vs "Maple Leafs"
 *   "LA Lakers" vs "Los Angeles Lakers"
 *   "NY Rangers" vs "New York Rangers"
 */
function _scores_team_match($name1, $name2) {
    if (empty($name1) || empty($name2)) return false;

    $n1 = strtolower(trim($name1));
    $n2 = strtolower(trim($name2));

    // Exact match
    if ($n1 === $n2) return true;

    // One contains the other
    if (strpos($n1, $n2) !== false || strpos($n2, $n1) !== false) return true;

    // Normalize common abbreviations
    $n1_norm = _scores_normalize_team($n1);
    $n2_norm = _scores_normalize_team($n2);
    if ($n1_norm === $n2_norm) return true;
    if (strpos($n1_norm, $n2_norm) !== false || strpos($n2_norm, $n1_norm) !== false) return true;

    // Last-word match (e.g. "Maple Leafs" from "Toronto Maple Leafs")
    // Use last 2 words for multi-word nicknames
    $words1 = explode(' ', $n1_norm);
    $words2 = explode(' ', $n2_norm);
    if (count($words1) >= 2 && count($words2) >= 2) {
        $tail1 = implode(' ', array_slice($words1, -2));
        $tail2 = implode(' ', array_slice($words2, -2));
        if ($tail1 === $tail2) return true;
    }

    // Single last word match (e.g. "Lakers", "Raptors")
    $last1 = end($words1);
    $last2 = end($words2);
    if (strlen($last1) >= 4 && $last1 === $last2) return true;

    return false;
}

/**
 * Normalize team name: expand abbreviations, strip common prefixes
 */
function _scores_normalize_team($name) {
    $name = strtolower(trim($name));

    // City abbreviation expansions
    $abbrevs = array(
        'la '   => 'los angeles ',
        'l.a. ' => 'los angeles ',
        'ny '   => 'new york ',
        'n.y. ' => 'new york ',
        'nj '   => 'new jersey ',
        'tb '   => 'tampa bay ',
        'sf '   => 'san francisco ',
        'kc '   => 'kansas city ',
        'gb '   => 'green bay ',
        'okc '  => 'oklahoma city ',
        'stl '  => 'st. louis ',
        'st '   => 'st. louis '
    );

    foreach ($abbrevs as $short => $full) {
        if (strpos($name, $short) === 0) {
            $name = $full . substr($name, strlen($short));
            break;
        }
    }

    // Remove common noise: "the", periods, extra spaces
    $name = str_replace('.', '', $name);
    $name = str_replace('  ', ' ', $name);
    if (strpos($name, 'the ') === 0) {
        $name = substr($name, 4);
    }

    return trim($name);
}

// ────────────────────────────────────────────────────────────
//  Source 1: The Odds API scores (0 credits)
// ────────────────────────────────────────────────────────────

function _scores_from_odds_api($sport, $days_from) {
    global $THE_ODDS_API_KEY;

    if (empty($THE_ODDS_API_KEY)) return null;

    $url = 'https://api.the-odds-api.com/v4/sports/' . urlencode($sport)
         . '/scores/?apiKey=' . urlencode($THE_ODDS_API_KEY)
         . '&daysFrom=' . (int)$days_from
         . '&dateFormat=iso';

    $body = _scores_http_get($url);
    if ($body === null) return null;

    $data = json_decode($body, true);
    if (!is_array($data)) return null;

    $scores = array();
    foreach ($data as $game) {
        $gid = isset($game['id']) ? $game['id'] : '';
        $completed = isset($game['completed']) && $game['completed'];
        if (!$gid || !$completed) continue;

        $home_team = isset($game['home_team']) ? $game['home_team'] : '';
        $away_team = isset($game['away_team']) ? $game['away_team'] : '';
        $home_score = null;
        $away_score = null;

        if (isset($game['scores']) && is_array($game['scores'])) {
            foreach ($game['scores'] as $sc) {
                $sname = isset($sc['name']) ? $sc['name'] : '';
                $sval  = isset($sc['score']) ? (int)$sc['score'] : 0;
                if ($sname === $home_team) $home_score = $sval;
                if ($sname === $away_team) $away_score = $sval;
            }
        }

        if ($home_score !== null && $away_score !== null) {
            $scores[$gid] = array(
                'home_score' => $home_score,
                'away_score' => $away_score,
                'home_team'  => $home_team,
                'away_team'  => $away_team,
                'completed'  => true
            );
        }
    }

    if (count($scores) === 0) return null;
    return $scores;
}

// ────────────────────────────────────────────────────────────
//  Source 2: ESPN API (free, no key)
// ────────────────────────────────────────────────────────────

function _scores_from_espn_api($sport) {
    global $_SCORES_ESPN_MAP;

    if (!isset($_SCORES_ESPN_MAP[$sport])) return null;

    $espn_path = $_SCORES_ESPN_MAP[$sport];
    $url = 'https://site.api.espn.com/apis/site/v2/sports/' . $espn_path . '/scoreboard';

    $body = _scores_http_get($url);
    if ($body === null) return null;

    $data = json_decode($body, true);
    if (!is_array($data) || !isset($data['events'])) return null;

    $scores = array();
    foreach ($data['events'] as $event) {
        if (!isset($event['competitions']) || !is_array($event['competitions'])) continue;

        foreach ($event['competitions'] as $comp) {
            // Check if game is completed
            $completed = false;
            if (isset($comp['status']['type']['completed'])) {
                $completed = (bool)$comp['status']['type']['completed'];
            }
            if (!$completed) continue;

            if (!isset($comp['competitors']) || !is_array($comp['competitors'])) continue;

            $home_team = '';
            $away_team = '';
            $home_score = null;
            $away_score = null;
            $game_date = '';

            if (isset($comp['date'])) {
                $game_date = substr($comp['date'], 0, 10); // YYYY-MM-DD
            }

            foreach ($comp['competitors'] as $team) {
                $team_name = '';
                if (isset($team['team']['displayName'])) {
                    $team_name = $team['team']['displayName'];
                } elseif (isset($team['team']['name'])) {
                    $team_name = $team['team']['name'];
                }

                $team_score = isset($team['score']) ? (int)$team['score'] : 0;
                $is_home = (isset($team['homeAway']) && $team['homeAway'] === 'home');

                if ($is_home) {
                    $home_team = $team_name;
                    $home_score = $team_score;
                } else {
                    $away_team = $team_name;
                    $away_score = $team_score;
                }
            }

            if ($home_score !== null && $away_score !== null && $home_team && $away_team) {
                // Create composite key from team names + date for matching
                $composite_key = 'espn_' . _scores_make_key($home_team, $away_team, $game_date);
                $scores[$composite_key] = array(
                    'home_score' => $home_score,
                    'away_score' => $away_score,
                    'home_team'  => $home_team,
                    'away_team'  => $away_team,
                    'completed'  => true,
                    'game_date'  => $game_date
                );
            }
        }
    }

    if (count($scores) === 0) return null;
    return $scores;
}

// ────────────────────────────────────────────────────────────
//  Source 3: ESPN web scraping (last resort fallback)
// ────────────────────────────────────────────────────────────

function _scores_from_espn_scrape($sport) {
    global $_SCORES_ESPN_MAP;

    if (!isset($_SCORES_ESPN_MAP[$sport])) return null;

    $espn_path = $_SCORES_ESPN_MAP[$sport];
    // ESPN scoreboard page
    $url = 'https://www.espn.com/' . str_replace('/', '/', $espn_path) . '/scoreboard';

    $body = _scores_http_get($url);
    if ($body === null) return null;

    // Try to extract embedded JSON data
    // ESPN embeds scoreboard data in various JS variables
    $json_data = null;

    // Pattern 1: window['__espnfitt__']
    if (preg_match("/window\['__espnfitt__'\]\s*=\s*(\{.+?\});\s*</s", $body, $matches)) {
        $json_data = json_decode($matches[1], true);
    }

    // Pattern 2: window.espn.scoreboardData
    if ($json_data === null && preg_match('/window\.espn\.scoreboardData\s*=\s*(\{.+?\});\s*/s', $body, $matches)) {
        $json_data = json_decode($matches[1], true);
    }

    // Pattern 3: __NEXT_DATA__ (newer ESPN pages)
    if ($json_data === null && preg_match('/<script id="__NEXT_DATA__"[^>]*>(\{.+?\})<\/script>/s', $body, $matches)) {
        $next_data = json_decode($matches[1], true);
        if (is_array($next_data) && isset($next_data['props']['pageProps']['scoreboard'])) {
            $json_data = $next_data['props']['pageProps']['scoreboard'];
        } elseif (is_array($next_data) && isset($next_data['props']['pageProps'])) {
            $json_data = $next_data['props']['pageProps'];
        }
    }

    if (!is_array($json_data)) return null;

    // Find the events array — it could be nested
    $events = null;
    if (isset($json_data['events'])) {
        $events = $json_data['events'];
    } elseif (isset($json_data['page']['content']['scoreboard']['evts'])) {
        $events = $json_data['page']['content']['scoreboard']['evts'];
    } elseif (isset($json_data['scoreboard']['events'])) {
        $events = $json_data['scoreboard']['events'];
    }

    if (!is_array($events)) return null;

    $scores = array();
    foreach ($events as $event) {
        $competitions = null;
        if (isset($event['competitions'])) {
            $competitions = $event['competitions'];
        } elseif (isset($event['cmpts'])) {
            $competitions = $event['cmpts'];
        }
        if (!is_array($competitions)) continue;

        foreach ($competitions as $comp) {
            // Check completion
            $completed = false;
            if (isset($comp['status']['type']['completed'])) {
                $completed = (bool)$comp['status']['type']['completed'];
            } elseif (isset($comp['sts']['typ']['completed'])) {
                $completed = (bool)$comp['sts']['typ']['completed'];
            }
            if (!$completed) continue;

            $competitors = null;
            if (isset($comp['competitors'])) {
                $competitors = $comp['competitors'];
            } elseif (isset($comp['cmptrs'])) {
                $competitors = $comp['cmptrs'];
            }
            if (!is_array($competitors)) continue;

            $home_team = '';
            $away_team = '';
            $home_score = null;
            $away_score = null;
            $game_date = '';

            if (isset($comp['date'])) {
                $game_date = substr($comp['date'], 0, 10);
            } elseif (isset($comp['dt'])) {
                $game_date = substr($comp['dt'], 0, 10);
            }

            foreach ($competitors as $team) {
                $team_name = '';
                if (isset($team['team']['displayName'])) {
                    $team_name = $team['team']['displayName'];
                } elseif (isset($team['team']['dspNm'])) {
                    $team_name = $team['team']['dspNm'];
                } elseif (isset($team['team']['name'])) {
                    $team_name = $team['team']['name'];
                } elseif (isset($team['tm']['dspNm'])) {
                    $team_name = $team['tm']['dspNm'];
                }

                $team_score = 0;
                if (isset($team['score'])) {
                    $team_score = (int)$team['score'];
                } elseif (isset($team['scr'])) {
                    $team_score = (int)$team['scr'];
                }

                $is_home = false;
                if (isset($team['homeAway'])) {
                    $is_home = ($team['homeAway'] === 'home');
                } elseif (isset($team['hmAwy'])) {
                    $is_home = ($team['hmAwy'] === 'home');
                }

                if ($is_home) {
                    $home_team = $team_name;
                    $home_score = $team_score;
                } else {
                    $away_team = $team_name;
                    $away_score = $team_score;
                }
            }

            if ($home_score !== null && $away_score !== null && $home_team && $away_team) {
                $composite_key = 'scrape_' . _scores_make_key($home_team, $away_team, $game_date);
                $scores[$composite_key] = array(
                    'home_score' => $home_score,
                    'away_score' => $away_score,
                    'home_team'  => $home_team,
                    'away_team'  => $away_team,
                    'completed'  => true,
                    'game_date'  => $game_date
                );
            }
        }
    }

    if (count($scores) === 0) return null;
    return $scores;
}

// ────────────────────────────────────────────────────────────
//  Helper: create a stable composite key from teams + date
// ────────────────────────────────────────────────────────────

function _scores_make_key($home, $away, $date) {
    $h = strtolower(preg_replace('/[^a-z0-9]/', '', strtolower($home)));
    $a = strtolower(preg_replace('/[^a-z0-9]/', '', strtolower($away)));
    // Sort alphabetically so order doesn't matter
    $parts = array($h, $a);
    sort($parts);
    return $parts[0] . '_' . $parts[1] . '_' . $date;
}

// ────────────────────────────────────────────────────────────
//  Main: fetch all scores, merge sources
// ────────────────────────────────────────────────────────────

/**
 * Fetch completed game scores from multiple sources.
 *
 * @param string $sport    Odds API sport key (e.g. 'icehockey_nhl')
 * @param int    $days_from Number of days back to fetch (1-3)
 * @return array array('scores' => $map, 'source' => string, 'count' => int)
 */
function _scores_fetch_all($sport, $days_from) {
    $days_from = max(1, min((int)$days_from, 3));
    $all_scores = array();
    $source = 'none';

    // Source 1: The Odds API (preferred — has event_ids matching our bets)
    $odds_scores = _scores_from_odds_api($sport, $days_from);
    if (is_array($odds_scores) && count($odds_scores) > 0) {
        foreach ($odds_scores as $key => $val) {
            $all_scores[$key] = $val;
        }
        $source = 'odds_api';
    }

    // Source 2: ESPN API (supplement with additional scores)
    $espn_scores = _scores_from_espn_api($sport);
    if (is_array($espn_scores) && count($espn_scores) > 0) {
        // Only add ESPN scores that we don't already have from Odds API
        // Check by team name matching
        foreach ($espn_scores as $key => $espn_game) {
            $already_have = false;
            foreach ($all_scores as $existing) {
                if (_scores_team_match($existing['home_team'], $espn_game['home_team'])
                    && _scores_team_match($existing['away_team'], $espn_game['away_team'])) {
                    $already_have = true;
                    break;
                }
            }
            if (!$already_have) {
                $all_scores[$key] = $espn_game;
                if ($source === 'none') $source = 'espn_api';
                elseif ($source === 'odds_api') $source = 'odds_api+espn_api';
            }
        }
    }

    // Source 3: ESPN scraping (fallback only if we have nothing yet)
    if (count($all_scores) === 0) {
        $scrape_scores = _scores_from_espn_scrape($sport);
        if (is_array($scrape_scores) && count($scrape_scores) > 0) {
            foreach ($scrape_scores as $key => $val) {
                $all_scores[$key] = $val;
            }
            $source = 'espn_scrape';
        }
    }

    return array(
        'scores' => $all_scores,
        'source' => $source,
        'count'  => count($all_scores)
    );
}

/**
 * Look up a score from a merged score map by event_id (exact) or team names (fuzzy).
 * Use this from sports_bets.php settle action.
 *
 * @param array  $score_map  From _scores_fetch_all()['scores']
 * @param string $event_id   The Odds API event ID
 * @param string $home_team  Home team name from the bet
 * @param string $away_team  Away team name from the bet
 * @return array|null  Score entry or null
 */
function _scores_lookup($score_map, $event_id, $home_team, $away_team) {
    // First: exact event_id match (Odds API scores)
    if (!empty($event_id) && isset($score_map[$event_id])) {
        return $score_map[$event_id];
    }

    // Second: fuzzy team name match (ESPN scores)
    foreach ($score_map as $entry) {
        if (_scores_team_match($entry['home_team'], $home_team)
            && _scores_team_match($entry['away_team'], $away_team)) {
            return $entry;
        }
        // Also check swapped home/away (sometimes sources disagree)
        if (_scores_team_match($entry['home_team'], $away_team)
            && _scores_team_match($entry['away_team'], $home_team)) {
            // Swap scores to match our bet's perspective
            return array(
                'home_score' => $entry['away_score'],
                'away_score' => $entry['home_score'],
                'home_team'  => $entry['away_team'],
                'away_team'  => $entry['home_team'],
                'completed'  => true
            );
        }
    }

    return null;
}

// ────────────────────────────────────────────────────────────
//  Standings / Rankings — ESPN API (free, no key)
// ────────────────────────────────────────────────────────────

function _standings_cmp_winpct($a, $b) {
    if ($b['win_pct'] == $a['win_pct']) return 0;
    return ($b['win_pct'] > $a['win_pct']) ? 1 : -1;
}

/**
 * Fetch current standings for a sport from ESPN.
 * Returns associative array keyed by various forms of team name (lowercase).
 * Each value: array(name, abbr, wins, losses, win_pct, rank, record, conf)
 */
function _scores_fetch_standings($sport) {
    global $_SCORES_ESPN_MAP;

    if (!isset($_SCORES_ESPN_MAP[$sport])) return array();

    $espn_path = $_SCORES_ESPN_MAP[$sport];
    $url = 'https://site.api.espn.com/apis/v2/sports/' . $espn_path . '/standings';

    $body = _scores_http_get($url);
    if (!$body) return array();

    $data = json_decode($body, true);
    if (!$data || !isset($data['children'])) return array();

    $all_teams = array();

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
                    $stats_map[$sn] = isset($s['value']) ? $s['value'] : 0;
                }
            }

            $team_name = isset($team['displayName']) ? $team['displayName'] : '';
            $wins   = isset($stats_map['wins']) ? (int)$stats_map['wins'] : 0;
            $losses = isset($stats_map['losses']) ? (int)$stats_map['losses'] : 0;
            $win_pct = isset($stats_map['winPercent']) ? (float)$stats_map['winPercent'] : 0;

            $all_teams[] = array(
                'name'    => $team_name,
                'abbr'    => isset($team['abbreviation']) ? $team['abbreviation'] : '',
                'wins'    => $wins,
                'losses'  => $losses,
                'win_pct' => $win_pct,
                'conf'    => $conf_name
            );
        }
    }

    usort($all_teams, '_standings_cmp_winpct');

    $standings = array();
    for ($i = 0; $i < count($all_teams); $i++) {
        $t = $all_teams[$i];
        $t['rank'] = $i + 1;
        $t['record'] = $t['wins'] . '-' . $t['losses'];

        $key = strtolower($t['name']);
        $standings[$key] = $t;

        if ($t['abbr']) {
            $standings[strtolower($t['abbr'])] = $t;
        }

        // Key by last word(s) for fuzzy lookup
        $parts = explode(' ', $key);
        if (count($parts) > 1) {
            $last = $parts[count($parts) - 1];
            if (!isset($standings[$last])) {
                $standings[$last] = $t;
            }
            // Two-word nicknames: "maple leafs", "blue jays"
            if (count($parts) >= 3) {
                $last2 = $parts[count($parts) - 2] . ' ' . $last;
                if (!isset($standings[$last2])) {
                    $standings[$last2] = $t;
                }
            }
        }
    }

    return $standings;
}

/**
 * Find a team's standing from the lookup map.
 * Uses fuzzy matching to handle variations.
 */
function _scores_find_team_standing($team_name, $standings) {
    if (empty($team_name) || empty($standings)) return null;

    $search = strtolower(trim($team_name));

    // Direct match
    if (isset($standings[$search])) return $standings[$search];

    // Last word
    $parts = explode(' ', $search);
    $last = $parts[count($parts) - 1];
    if (strlen($last) >= 4 && isset($standings[$last])) return $standings[$last];

    // Last 2 words (for "Maple Leafs", "Blue Jays")
    if (count($parts) >= 2) {
        $last2 = $parts[count($parts) - 2] . ' ' . $parts[count($parts) - 1];
        if (isset($standings[$last2])) return $standings[$last2];
    }

    // Fuzzy match via _scores_team_match
    foreach ($standings as $key => $val) {
        if (_scores_team_match($team_name, $val['name'])) return $val;
    }

    return null;
}

// ────────────────────────────────────────────────────────────
//  Standalone action handler: ?action=test
// ────────────────────────────────────────────────────────────

if (isset($_GET['action']) && strtolower(trim($_GET['action'])) === 'test') {
    header('Content-Type: application/json');
    header('Access-Control-Allow-Origin: *');

    $sport = isset($_GET['sport']) ? trim($_GET['sport']) : 'icehockey_nhl';
    $days  = isset($_GET['days']) ? (int)$_GET['days'] : 3;

    $result = _scores_fetch_all($sport, $days);

    // Format scores for display
    $formatted = array();
    foreach ($result['scores'] as $key => $game) {
        $formatted[] = array(
            'key'        => $key,
            'home_team'  => $game['home_team'],
            'away_team'  => $game['away_team'],
            'home_score' => $game['home_score'],
            'away_score' => $game['away_score'],
            'display'    => $game['away_team'] . ' ' . $game['away_score']
                          . ' @ ' . $game['home_team'] . ' ' . $game['home_score'],
            'game_date'  => isset($game['game_date']) ? $game['game_date'] : ''
        );
    }

    echo json_encode(array(
        'ok'     => true,
        'sport'  => $sport,
        'days'   => $days,
        'source' => $result['source'],
        'count'  => $result['count'],
        'scores' => $formatted
    ));
    exit;
}
?>
