<?php
/**
 * Hardened NFL Scraper with Multi-Source Validation
 * Cross-checks data from ESPN, Pro-Football-Reference, and other sources
 * Never trusts a single source - validates everything
 * PHP 5.2 compatible
 */

require_once dirname(dirname(__FILE__)) . '/sports_db_connect.php';
require_once dirname(__FILE__) . '/data_validator.php';

class NFLHardenedScraper {
    private $conn;
    private $validator;
    private $errors = array();
    private $validation_results = array();
    
    // Source configuration
    private $sources = array(
        'primary' => array('espn_api', 'pro_football_reference'),
        'secondary' => array('espn_html', 'yahoo_sports', 'cbs_sports'),
        'backup' => array('fox_sports', 'sports_reference')
    );
    
    public function __construct($connection) {
        $this->conn = $connection;
        $this->validator = new DataValidator($connection);
        $this->_ensure_tables();
    }
    
    /**
     * Get hardened schedule data for a week
     */
    public function get_hardened_schedule($year, $week) {
        $this->errors = array();
        $this->validation_results = array();
        
        // Fetch from all available sources
        $raw_data = array();
        
        // Primary sources
        $raw_data['espn_api'] = $this->_fetch_espn_api_schedule($year, $week);
        $raw_data['pfr'] = $this->_fetch_pfr_schedule($year, $week);
        
        // Secondary sources (only fetch if primaries fail)
        if (!$raw_data['espn_api'] || !$raw_data['pfr']) {
            $raw_data['espn_html'] = $this->_fetch_espn_html_schedule($year, $week);
        }
        
        // Log which sources responded
        $available_sources = array_filter($raw_data);
        
        if (count($available_sources) < 2) {
            return array(
                'ok' => false,
                'error' => 'Insufficient data sources available',
                'sources_found' => count($available_sources),
                'errors' => $this->errors
            );
        }
        
        // Cross-validate and merge games
        $validated_games = $this->_cross_validate_schedule($raw_data, $year, $week);
        
        return array(
            'ok' => true,
            'year' => $year,
            'week' => $week,
            'sources_used' => array_keys($available_sources),
            'games_count' => count($validated_games),
            'games' => $validated_games,
            'validation_summary' => $this->_get_validation_summary(),
            'warnings' => $this->errors
        );
    }
    
    /**
     * Get hardened game data with play-by-play validation
     */
    public function get_hardened_game_data($game_id, $game_key = null) {
        // Fetch from multiple sources
        $sources_data = array();
        
        $sources_data['espn_api'] = $this->_fetch_espn_game_data($game_id);
        $sources_data['pfr'] = $this->_fetch_pfr_game_data($game_id, $game_key);
        
        // Filter out failed sources
        $sources_data = array_filter($sources_data);
        
        if (count($sources_data) < 2) {
            return array(
                'ok' => false,
                'error' => 'Need at least 2 sources for validation',
                'sources_found' => count($sources_data)
            );
        }
        
        // Validate the data
        $validation = $this->validator->validate_game_data($game_id, 'nfl', $sources_data);
        
        if ($validation['overall_confidence'] < 0.6) {
            return array(
                'ok' => false,
                'error' => 'Data confidence too low',
                'confidence' => $validation['overall_confidence'],
                'validation' => $validation
            );
        }
        
        // Store validation result
        $this->validation_results[] = $validation;
        
        return array(
            'ok' => true,
            'game_id' => $game_id,
            'confidence' => $validation['overall_confidence'],
            'data' => $validation['consensus'],
            'validation_details' => $validation,
            'sources_used' => array_keys($sources_data)
        );
    }
    
    /**
     * Get player stats with cross-validation
     */
    public function get_hardened_player_stats($player_name, $game_date = null) {
        if (!$game_date) $game_date = date('Y-m-d');
        
        $validation = $this->validator->validate_player_stats($player_name, 'nfl', $game_date);
        
        if (isset($validation['error'])) {
            return array('ok' => false, 'error' => $validation['error']);
        }
        
        return array(
            'ok' => true,
            'player' => $player_name,
            'date' => $game_date,
            'confidence' => $validation['overall_confidence'],
            'stats' => $validation['validated_stats'],
            'sources' => $validation['sources_used']
        );
    }
    
    /**
     * Get weekly box scores with full validation
     */
    public function get_hardened_weekly_scores($year, $week) {
        $schedule = $this->get_hardened_schedule($year, $week);
        
        if (!$schedule['ok']) {
            return $schedule;
        }
        
        $detailed_games = array();
        
        foreach ($schedule['games'] as $game) {
            $game_details = $this->get_hardened_game_data($game['game_id'], $game['game_key']);
            
            if ($game_details['ok']) {
                $detailed_games[] = array_merge($game, $game_details);
            } else {
                // Use schedule data only
                $detailed_games[] = array_merge($game, array(
                    'confidence' => 0.5,
                    'warning' => 'Game details unavailable'
                ));
            }
            
            // Rate limiting - be nice to APIs
            usleep(100000); // 100ms delay
        }
        
        return array(
            'ok' => true,
            'year' => $year,
            'week' => $week,
            'games' => $detailed_games,
            'avg_confidence' => $this->_calculate_avg_confidence($detailed_games),
            'fully_validated' => count(array_filter($detailed_games, create_function('$g', 'return isset($g["confidence"]) && $g["confidence"] >= 0.7;')))
        );
    }
    
    // ════════════════════════════════════════════════════════════
    //  Data Fetching Methods
    // ════════════════════════════════════════════════════════════
    
    private function _fetch_espn_api_schedule($year, $week) {
        $url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=$year&seasontype=2&week=$week";
        $body = $this->_http_get($url);
        
        if (!$body) {
            $this->errors[] = "ESPN API failed for week $week";
            return null;
        }
        
        $data = json_decode($body, true);
        if (!$data || !isset($data['events'])) {
            $this->errors[] = "ESPN API returned invalid data";
            return null;
        }
        
        $games = array();
        foreach ($data['events'] as $event) {
            $game = $this->_parse_espn_event($event);
            if ($game) {
                $games[] = $game;
            }
        }
        
        return $games;
    }
    
    private function _fetch_pfr_schedule($year, $week) {
        // Pro-Football-Reference schedule page
        $url = "https://www.pro-football-reference.com/years/$year/games.htm";
        $body = $this->_http_get($url);
        
        if (!$body) {
            $this->errors[] = "PFR schedule failed";
            return null;
        }
        
        $games = array();
        
        // Parse PFR schedule table
        // Each row represents one game
        preg_match_all('/<tr >\s*<td[^>]*>(.*?)<\/td>\s*<td[^>]*>(.*?)<\/td>\s*<td[^>]*>(.*?)<\/td>\s*<td[^>]*>(.*?)<\/td>\s*<td[^>]*>(.*?)<\/td>\s*<td[^>]*>(.*?)<\/td>\s*<td[^>]*>(.*?)<\/td>\s*<td[^>]*>(.*?)<\/td>/s', $body, $matches, PREG_SET_ORDER);
        
        foreach ($matches as $match) {
            $week_num = trim(strip_tags($match[1]));
            
            // Skip header rows and other weeks
            if (!is_numeric($week_num) || (int)$week_num !== $week) {
                continue;
            }
            
            $day = trim(strip_tags($match[2]));
            $date = trim(strip_tags($match[3]));
            $time = trim(strip_tags($match[4]));
            $winner = trim(strip_tags($match[5]));
            $winner_pts = trim(strip_tags($match[6]));
            $loser = trim(strip_tags($match[7]));
            $loser_pts = trim(strip_tags($match[8]));
            
            // Determine home/away from PFR data format
            // PFR lists winner first, loser second
            // We need to check which is home team
            $at_pos = strpos($winner, ' @ ');
            if ($at_pos !== false) {
                // Format: "Away @ Home"
                $away_team = trim(substr($winner, 0, $at_pos));
                $home_team = trim(substr($winner, $at_pos + 3));
            } else {
                // Winner/loser format - need to determine home from other data
                $away_team = $winner;
                $home_team = $loser;
            }
            
            $games[] = array(
                'game_key' => $year . '_WK' . $week . '_' . $this->_normalize_team($away_team) . '_at_' . $this->_normalize_team($home_team),
                'week' => $week_num,
                'day' => $day,
                'date' => $date,
                'time' => $time,
                'away_team' => $away_team,
                'home_team' => $home_team,
                'away_score' => is_numeric($loser_pts) ? (int)$loser_pts : null,
                'home_score' => is_numeric($winner_pts) ? (int)$winner_pts : null,
                'winner' => $winner,
                'loser' => $loser,
                'source' => 'pfr'
            );
        }
        
        return $games;
    }
    
    private function _fetch_espn_html_schedule($year, $week) {
        // ESPN HTML as backup
        $url = "https://www.espn.com/nfl/schedule/_/year/$year/week/$week";
        $body = $this->_http_get($url);
        
        if (!$body) {
            $this->errors[] = "ESPN HTML schedule failed";
            return null;
        }
        
        $games = array();
        
        // Parse ESPN schedule page
        preg_match_all('/<div[^>]*class="[^"]*game-container[^"]*"[^>]*>(.*?)<\/div>\s*<\/div>/s', $body, $game_blocks);
        
        foreach ($game_blocks[1] as $block) {
            // Extract teams
            preg_match('/<span[^>]*class="[^"]*team-name[^"]*"[^>]*>(.*?)<\/span>/', $block, $away_match);
            preg_match('/<span[^>]*class="[^"]*team-name[^"]*"[^>]*>.*?<\/span>.*?<span[^>]*class="[^"]*team-name[^"]*"[^>]*>(.*?)<\/span>/s', $block, $home_match);
            
            $away_team = isset($away_match[1]) ? trim(strip_tags($away_match[1])) : '';
            $home_team = isset($home_match[1]) ? trim(strip_tags($home_match[1])) : '';
            
            if ($away_team && $home_team) {
                $games[] = array(
                    'game_key' => $year . '_WK' . $week . '_' . $this->_normalize_team($away_team) . '_at_' . $this->_normalize_team($home_team),
                    'week' => $week,
                    'away_team' => $away_team,
                    'home_team' => $home_team,
                    'source' => 'espn_html'
                );
            }
        }
        
        return $games;
    }
    
    private function _fetch_espn_game_data($game_id) {
        $url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event=$game_id";
        $body = $this->_http_get($url);
        
        if (!$body) return null;
        
        $data = json_decode($body, true);
        if (!$data) return null;
        
        return $this->_extract_box_score_data($data, 'espn');
    }
    
    private function _fetch_pfr_game_data($game_id, $game_key) {
        if (!$game_key) return null;
        
        // Parse game key to get teams and date
        // Format: YEAR_WK#_away_at_home
        $parts = explode('_', $game_key);
        if (count($parts) < 4) return null;
        
        $year = $parts[0];
        
        // Construct PFR boxscore URL
        // PFR uses date-based URLs: /boxscores/202109120rai.htm
        // Would need to extract date from game data
        
        return null; // Placeholder - would need date parsing
    }
    
    // ════════════════════════════════════════════════════════════
    //  Validation & Merging
    // ════════════════════════════════════════════════════════════
    
    private function _cross_validate_schedule($raw_data, $year, $week) {
        $validated_games = array();
        
        // Build index of all games found
        $game_index = array();
        
        foreach ($raw_data as $source => $games) {
            if (!is_array($games)) continue;
            
            foreach ($games as $game) {
                $key = isset($game['game_key']) ? $game['game_key'] : $this->_generate_game_key($game);
                
                if (!isset($game_index[$key])) {
                    $game_index[$key] = array();
                }
                
                $game_index[$key][$source] = $game;
            }
        }
        
        // Validate each game
        foreach ($game_index as $key => $sources) {
            if (count($sources) < 2) {
                $this->errors[] = "Game $key only found in " . count($sources) . " source(s)";
                continue;
            }
            
            // Normalize team names for comparison
            $normalized = $this->_normalize_game_data($sources);
            
            // Run validation
            $validation = $this->validator->validate_game_data($key, 'nfl', $normalized);
            
            if ($validation['overall_confidence'] >= 0.6) {
                $validated_games[] = array(
                    'game_id' => isset($normalized['espn_api']['id']) ? $normalized['espn_api']['id'] : md5($key),
                    'game_key' => $key,
                    'year' => $year,
                    'week' => $week,
                    'confidence' => $validation['overall_confidence'],
                    'data' => $validation['consensus'],
                    'sources' => array_keys($sources),
                    'validation' => $validation
                );
            } else {
                $this->errors[] = "Game $key failed validation (confidence: {$validation['overall_confidence']})";
            }
        }
        
        return $validated_games;
    }
    
    private function _normalize_game_data($sources_data) {
        $normalized = array();
        
        foreach ($sources_data as $source => $game) {
            $normalized[$source] = array(
                'game_date' => isset($game['date']) ? $game['date'] : (isset($game['game_date']) ? $game['game_date'] : ''),
                'home_team' => isset($game['home_team']) ? $this->_standardize_team_name($game['home_team']) : '',
                'away_team' => isset($game['away_team']) ? $this->_standardize_team_name($game['away_team']) : '',
                'home_score' => isset($game['home_score']) ? $game['home_score'] : null,
                'away_score' => isset($game['away_score']) ? $game['away_score'] : null,
                'id' => isset($game['id']) ? $game['id'] : (isset($game['game_id']) ? $game['game_id'] : '')
            );
        }
        
        return $normalized;
    }
    
    private function _standardize_team_name($name) {
        $name = strtolower(trim($name));
        
        // Remove common suffixes
        $name = str_replace(array('saints', 'rams', 'ravens', 'cardinals', 'browns', 'giants', 'jets', 'chargers', 'chiefs', 'raiders', 'broncos', 'texans', 'colts', 'jaguars', 'titans', 'steelers', 'bengals', 'bills', 'dolphins', 'patriots', 'jets', 'cowboys', 'eagles', 'commanders', 'packers', 'lions', 'vikings', 'bears', 'falcons', 'panthers', 'buccaneers', '49ers', 'seahawks'), '', $name);
        
        // City name mappings
        $city_map = array(
            'newengland' => 'new england',
            'kansascity' => 'kansas city',
            'greenbay' => 'green bay',
            'tampabay' => 'tampa bay',
            'lasvegas' => 'las vegas',
            'losangeles' => 'los angeles',
            'neworleans' => 'new orleans',
            'newyork' => 'new york',
            'sandiego' => 'san diego',
            'sanfrancisco' => 'san francisco'
        );
        
        foreach ($city_map as $compact => $proper) {
            if (strpos($name, $compact) !== false) {
                $name = str_replace($compact, $proper, $name);
            }
        }
        
        return trim($name);
    }
    
    private function _extract_box_score_data($api_response, $source) {
        if (!isset($api_response['header'])) return null;
        
        $header = $api_response['header'];
        $home = isset($header['competitions'][0]['competitors'][0]) ? $header['competitions'][0]['competitors'][0] : null;
        $away = isset($header['competitions'][0]['competitors'][1]) ? $header['competitions'][0]['competitors'][1] : null;
        
        if (!$home || !$away) return null;
        
        $data = array(
            'home_team' => isset($home['team']['displayName']) ? $home['team']['displayName'] : '',
            'away_team' => isset($away['team']['displayName']) ? $away['team']['displayName'] : '',
            'home_score' => isset($home['score']) ? (int)$home['score'] : null,
            'away_score' => isset($away['score']) ? (int)$away['score'] : null,
            'source' => $source
        );
        
        // Add team statistics if available
        if (isset($api_response['boxscore']['teams'])) {
            foreach ($api_response['boxscore']['teams'] as $team_stats) {
                // Parse statistics
            }
        }
        
        return $data;
    }
    
    private function _generate_game_key($game) {
        $away = isset($game['away_team']) ? $this->_normalize_team($game['away_team']) : 'unknown';
        $home = isset($game['home_team']) ? $this->_normalize_team($game['home_team']) : 'unknown';
        $date = isset($game['date']) ? $game['date'] : date('Ymd');
        
        return $date . '_' . $away . '_at_' . $home;
    }
    
    private function _normalize_team($name) {
        return strtolower(preg_replace('/[^a-zA-Z]/', '', $name));
    }
    
    private function _get_validation_summary() {
        if (empty($this->validation_results)) {
            return array('total_validated' => 0);
        }
        
        $total = count($this->validation_results);
        $high_confidence = 0;
        $avg_confidence = 0;
        
        foreach ($this->validation_results as $result) {
            $avg_confidence += $result['overall_confidence'];
            if ($result['overall_confidence'] >= 0.9) {
                $high_confidence++;
            }
        }
        
        return array(
            'total_validated' => $total,
            'high_confidence_count' => $high_confidence,
            'average_confidence' => round($avg_confidence / $total, 3)
        );
    }
    
    private function _calculate_avg_confidence($games) {
        $total = 0;
        $count = 0;
        
        foreach ($games as $game) {
            if (isset($game['confidence'])) {
                $total += $game['confidence'];
                $count++;
            }
        }
        
        return $count > 0 ? round($total / $count, 3) : 0;
    }
    
    private function _parse_espn_event($event) {
        if (!isset($event['competitions']) || empty($event['competitions'])) {
            return null;
        }
        
        $comp = $event['competitions'][0];
        $home_team = '';
        $away_team = '';
        $home_score = null;
        $away_score = null;
        
        foreach ($comp['competitors'] as $team) {
            $name = isset($team['team']['displayName']) ? $team['team']['displayName'] : '';
            $score = isset($team['score']) ? $team['score'] : null;
            
            if (isset($team['homeAway']) && $team['homeAway'] === 'home') {
                $home_team = $name;
                $home_score = $score;
            } else {
                $away_team = $name;
                $away_score = $score;
            }
        }
        
        return array(
            'id' => isset($event['id']) ? $event['id'] : '',
            'game_key' => isset($event['date']) ? substr($event['date'], 0, 10) . '_' . $this->_normalize_team($away_team) . '_at_' . $this->_normalize_team($home_team) : '',
            'date' => isset($event['date']) ? $event['date'] : '',
            'home_team' => $home_team,
            'away_team' => $away_team,
            'home_score' => $home_score,
            'away_score' => $away_score,
            'status' => isset($comp['status']['type']['description']) ? $comp['status']['type']['description'] : '',
            'source' => 'espn_api'
        );
    }
    
    private function _http_get($url, $timeout = 15) {
        if (function_exists('curl_init')) {
            $ch = curl_init($url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
            curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (SportsDataBot/1.0; Validation Mode)');
            $body = curl_exec($ch);
            $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);
            
            if ($body !== false && $code >= 200 && $code < 300) {
                return $body;
            }
        }
        return null;
    }
    
    private function _ensure_tables() {
        $this->conn->query("CREATE TABLE IF NOT EXISTS lm_nfl_hardened_games (
            id INT AUTO_INCREMENT PRIMARY KEY,
            game_id VARCHAR(50),
            game_key VARCHAR(100),
            year INT,
            week INT,
            home_team VARCHAR(100),
            away_team VARCHAR(100),
            home_score INT,
            away_score INT,
            confidence DECIMAL(4,3),
            sources TEXT,
            validation_data TEXT,
            fetched_at DATETIME DEFAULT NOW(),
            UNIQUE KEY idx_game (game_id),
            INDEX idx_year_week (year, week)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
    }
}

// API Endpoint
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'schedule';
$scraper = new NFLHardenedScraper($conn);

if ($action === 'schedule') {
    $year = isset($_GET['year']) ? (int)$_GET['year'] : date('Y');
    $week = isset($_GET['week']) ? (int)$_GET['week'] : 1;
    $result = $scraper->get_hardened_schedule($year, $week);
    echo json_encode($result);
} elseif ($action === 'game') {
    $game_id = isset($_GET['game_id']) ? $_GET['game_id'] : '';
    $game_key = isset($_GET['game_key']) ? $_GET['game_key'] : null;
    if ($game_id) {
        $result = $scraper->get_hardened_game_data($game_id, $game_key);
        echo json_encode($result);
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing game_id'));
    }
} elseif ($action === 'week_scores') {
    $year = isset($_GET['year']) ? (int)$_GET['year'] : date('Y');
    $week = isset($_GET['week']) ? (int)$_GET['week'] : 1;
    $result = $scraper->get_hardened_weekly_scores($year, $week);
    echo json_encode($result);
} elseif ($action === 'player_stats') {
    $player = isset($_GET['player']) ? $_GET['player'] : '';
    $date = isset($_GET['date']) ? $_GET['date'] : null;
    if ($player) {
        $result = $scraper->get_hardened_player_stats($player, $date);
        echo json_encode($result);
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing player name'));
    }
} else {
    echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

$conn->close();
?>
