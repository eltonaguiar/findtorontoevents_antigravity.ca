<?php
/**
 * MLB Deep Analysis Module
 * Starting pitcher analysis, umpire tracking, bullpen status
 * PHP 5.2 compatible
 */

require_once dirname(dirname(__FILE__)) . '/sports_db_connect.php';

class MLBDeepAnalysis {
    private $conn;
    private $errors = array();
    
    // Umpire tendencies database (updated periodically)
    private $umpire_data = array();
    
    public function __construct($connection) {
        $this->conn = $connection;
        $this->_ensure_tables();
        $this->_load_umpire_data();
    }
    
    /**
     * Analyze a specific matchup
     */
    public function analyze_matchup($home_team, $away_team, $game_date = null) {
        if (!$game_date) $game_date = date('Y-m-d');
        
        $analysis = array(
            'home_team' => $home_team,
            'away_team' => $away_team,
            'game_date' => $game_date,
            'pitchers' => $this->get_pitcher_matchup($home_team, $away_team, $game_date),
            'umpire' => $this->get_umpire_impact($home_team, $game_date),
            'bullpens' => $this->get_bullpen_status($home_team, $away_team),
            'park_factors' => $this->get_park_factors($home_team),
            'betting_recommendations' => array()
        );
        
        // Generate recommendations
        $analysis['betting_recommendations'] = $this->_generate_recommendations($analysis);
        
        return $analysis;
    }
    
    /**
     * Get starting pitcher matchup details
     */
    public function get_pitcher_matchup($home_team, $away_team, $game_date) {
        $home_pitcher = $this->_fetch_probable_pitcher($home_team, $game_date);
        $away_pitcher = $this->_fetch_probable_pitcher($away_team, $game_date);
        
        return array(
            'home' => $this->_analyze_pitcher($home_pitcher, $home_team),
            'away' => $this->_analyze_pitcher($away_pitcher, $away_team),
            'advantage' => $this->_calculate_pitcher_advantage($home_pitcher, $away_pitcher)
        );
    }
    
    /**
     * Get umpire impact on game
     */
    public function get_umpire_impact($home_team, $game_date) {
        // Fetch scheduled umpires
        $umpire = $this->_fetch_umpire_assignment($home_team, $game_date);
        
        if (!$umpire) {
            return array('error' => 'Umpire assignment not available');
        }
        
        $stats = $this->_get_umpire_stats($umpire['name']);
        
        return array(
            'name' => $umpire['name'],
            'position' => $umpire['position'], // HP = home plate
            'stats' => $stats,
            'impact_score' => $this->_calculate_umpire_impact($stats),
            'betting_notes' => $this->_get_umpire_betting_notes($stats)
        );
    }
    
    /**
     * Get bullpen status for both teams
     */
    public function get_bullpen_status($home_team, $away_team) {
        return array(
            'home' => $this->_fetch_bullpen_data($home_team),
            'away' => $this->_fetch_bullpen_data($away_team)
        );
    }
    
    /**
     * Get park factors for home stadium
     */
    public function get_park_factors($team) {
        $park_data = $this->_fetch_park_factors($team);
        
        return array(
            'runs_factor' => isset($park_data['runs']) ? $park_data['runs'] : 1.0,
            'hr_factor' => isset($park_data['hr']) ? $park_data['hr'] : 1.0,
            'hits_factor' => isset($park_data['hits']) ? $park_data['hits'] : 1.0,
            'doubles_factor' => isset($park_data['doubles']) ? $park_data['doubles'] : 1.0,
            'triples_factor' => isset($park_data['triples']) ? $park_data['triples'] : 1.0,
            'walks_factor' => isset($park_data['walks']) ? $park_data['walks'] : 1.0,
            'interpretation' => $this->_interpret_park_factors($park_data)
        );
    }
    
    /**
     * Store analysis for a game
     */
    public function store_analysis($game_id, $home, $away, $date) {
        $analysis = $this->analyze_matchup($home, $away, $date);
        
        $home_pitcher = isset($analysis['pitchers']['home']['name']) ? $analysis['pitchers']['home']['name'] : '';
        $away_pitcher = isset($analysis['pitchers']['away']['name']) ? $analysis['pitchers']['away']['name'] : '';
        $pitcher_adv = isset($analysis['pitchers']['advantage']) ? $analysis['pitchers']['advantage'] : 'even';
        
        $umpire = isset($analysis['umpire']['name']) ? $analysis['umpire']['name'] : '';
        $umpire_impact = isset($analysis['umpire']['impact_score']) ? $analysis['umpire']['impact_score'] : 0;
        
        $park_runs = isset($analysis['park_factors']['runs_factor']) ? $analysis['park_factors']['runs_factor'] : 1.0;
        
        $recs = isset($analysis['betting_recommendations']) ? json_encode($analysis['betting_recommendations']) : '[]';
        
        $game_id_esc = $this->conn->real_escape_string($game_id);
        $home_esc = $this->conn->real_escape_string($home);
        $away_esc = $this->conn->real_escape_string($away);
        $home_p_esc = $this->conn->real_escape_string($home_pitcher);
        $away_p_esc = $this->conn->real_escape_string($away_pitcher);
        $umpire_esc = $this->conn->real_escape_string($umpire);
        $recs_esc = $this->conn->real_escape_string($recs);
        
        $query = "INSERT INTO lm_mlb_analysis 
                  (game_id, game_date, home_team, away_team, home_pitcher, away_pitcher, pitcher_advantage,
                   umpire, umpire_impact, park_factor_runs, recommendations, analyzed_at)
                  VALUES ('$game_id_esc', '$date', '$home_esc', '$away_esc', '$home_p_esc', '$away_p_esc', '$pitcher_adv',
                          '$umpire_esc', $umpire_impact, $park_runs, '$recs_esc', NOW())
                  ON DUPLICATE KEY UPDATE
                  home_pitcher=VALUES(home_pitcher), away_pitcher=VALUES(away_pitcher), pitcher_advantage=VALUES(pitcher_advantage),
                  umpire=VALUES(umpire), umpire_impact=VALUES(umpire_impact), park_factor_runs=VALUES(park_factor_runs),
                  recommendations=VALUES(recommendations), analyzed_at=NOW()";
        
        return $this->conn->query($query);
    }
    
    // ════════════════════════════════════════════════════════════
    //  Private Methods
    // ════════════════════════════════════════════════════════════
    
    private function _fetch_probable_pitcher($team, $date) {
        // Try to fetch from MLB.com API or ESPN
        $url = 'https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard';
        $body = $this->_http_get($url);
        
        if (!$body) return null;
        
        $data = json_decode($body, true);
        if (!$data || !isset($data['events'])) return null;
        
        foreach ($data['events'] as $event) {
            if (!isset($event['competitions'])) continue;
            
            foreach ($event['competitions'] as $comp) {
                // Find matching team
                $match = false;
                if (isset($comp['competitors'])) {
                    foreach ($comp['competitors'] as $team_data) {
                        $team_name = isset($team_data['team']['displayName']) ? strtolower($team_data['team']['displayName']) : '';
                        if (strpos($team_name, strtolower($team)) !== false) {
                            $match = true;
                            break;
                        }
                    }
                }
                
                if ($match && isset($comp['probables'])) {
                    foreach ($comp['probables'] as $pitcher) {
                        $p_team = isset($pitcher['team']['displayName']) ? strtolower($pitcher['team']['displayName']) : '';
                        if (strpos($p_team, strtolower($team)) !== false) {
                            return array(
                                'name' => isset($pitcher['athlete']['displayName']) ? $pitcher['athlete']['displayName'] : '',
                                'era' => isset($pitcher['athlete']['statistics'][0]['displayValue']) ? $pitcher['athlete']['statistics'][0]['displayValue'] : '',
                                'record' => isset($pitcher['athlete']['statistics'][1]['displayValue']) ? $pitcher['athlete']['statistics'][1]['displayValue'] : ''
                            );
                        }
                    }
                }
            }
        }
        
        return null;
    }
    
    private function _analyze_pitcher($pitcher, $team) {
        if (!$pitcher) {
            return array('error' => 'No pitcher data available');
        }
        
        // Get additional stats from our database or APIs
        $stats = $this->_fetch_pitcher_stats($pitcher['name']);
        
        return array(
            'name' => $pitcher['name'],
            'team' => $team,
            'era' => isset($pitcher['era']) ? $pitcher['era'] : (isset($stats['era']) ? $stats['era'] : 'N/A'),
            'record' => isset($pitcher['record']) ? $pitcher['record'] : '',
            'whip' => isset($stats['whip']) ? $stats['whip'] : 'N/A',
            'k_per_9' => isset($stats['k_per_9']) ? $stats['k_per_9'] : 'N/A',
            'bb_per_9' => isset($stats['bb_per_9']) ? $stats['bb_per_9'] : 'N/A',
            'innings' => isset($stats['innings']) ? $stats['innings'] : 'N/A',
            'recent_form' => isset($stats['last_3_starts']) ? $stats['last_3_starts'] : array(),
            'vs_opponent' => isset($stats['vs_current_opponent']) ? $stats['vs_current_opponent'] : array()
        );
    }
    
    private function _calculate_pitcher_advantage($home_pitcher, $away_pitcher) {
        if (!$home_pitcher || !$away_pitcher) return 'unknown';
        
        // Simple ERA comparison
        $home_era = $this->_parse_era($home_pitcher['era'] ?? '5.00');
        $away_era = $this->_parse_era($away_pitcher['era'] ?? '5.00');
        
        $diff = $home_era - $away_era;
        
        if ($diff < -1.0) return 'home_strong';
        if ($diff < -0.5) return 'home_moderate';
        if ($diff > 1.0) return 'away_strong';
        if ($diff > 0.5) return 'away_moderate';
        return 'even';
    }
    
    private function _parse_era($era_str) {
        $era_str = str_replace(' ERA', '', $era_str);
        return is_numeric($era_str) ? (float)$era_str : 5.00;
    }
    
    private function _fetch_umpire_assignment($home_team, $date) {
        // Scrape from Rotowire or similar source
        // This requires HTML scraping as no free API exists
        $url = 'https://www.rotowire.com/baseball/umpire.htm';
        $body = $this->_http_get($url);
        
        if (!$body) return null;
        
        // Parse umpire assignments
        // Looking for table with: Date, Away, Home, Umpire
        preg_match_all('/<tr[^>]*>.*?<td[^>]*>(.*?)<\/td>.*?<td[^>]*>(.*?)<\/td>.*?<td[^>]*>(.*?)<\/td>.*?<td[^>]*>(.*?)<\/td>.*?<\/tr>/s', $body, $matches, PREG_SET_ORDER);
        
        foreach ($matches as $match) {
            $row_date = trim(strip_tags($match[1]));
            $row_away = trim(strip_tags($match[2]));
            $row_home = trim(strip_tags($match[3]));
            $row_umpire = trim(strip_tags($match[4]));
            
            if (stripos($row_home, $home_team) !== false) {
                return array(
                    'name' => $row_umpire,
                    'position' => 'HP',
                    'date' => $row_date
                );
            }
        }
        
        return null;
    }
    
    private function _get_umpire_stats($umpire_name) {
        // Return cached stats or defaults
        $defaults = array(
            'games' => 0,
            'avg_runs' => 9.0,
            'strike_zone_size' => 'average', // small, average, large
            'fav_pitchers' => false, // Does he favor pitchers?
            'fav_hitters' => false,
            'consistency' => 'average'
        );
        
        $esc_name = $this->conn->real_escape_string($umpire_name);
        $res = $this->conn->query("SELECT * FROM lm_umpire_stats WHERE name='$esc_name' LIMIT 1");
        
        if ($res && $row = $res->fetch_assoc()) {
            return array(
                'games' => (int)$row['games'],
                'avg_runs' => (float)$row['avg_runs_per_game'],
                'strike_zone_size' => $row['strike_zone'],
                'fav_pitchers' => (float)$row['avg_runs_per_game'] < 8.5,
                'fav_hitters' => (float)$row['avg_runs_per_game'] > 10.0,
                'consistency' => $row['consistency']
            );
        }
        
        return $defaults;
    }
    
    private function _calculate_umpire_impact($stats) {
        $score = 0;
        
        if ($stats['avg_runs'] < 8.0) $score -= 2; // Pitcher friendly
        elseif ($stats['avg_runs'] > 10.0) $score += 2; // Hitter friendly
        
        if ($stats['strike_zone_size'] === 'large') $score -= 1;
        elseif ($stats['strike_zone_size'] === 'small') $score += 1;
        
        return $score;
    }
    
    private function _get_umpire_betting_notes($stats) {
        $notes = array();
        
        if ($stats['fav_pitchers']) {
            $notes[] = 'Pitcher-friendly umpire - consider UNDER';
        }
        if ($stats['fav_hitters']) {
            $notes[] = 'Hitter-friendly umpire - consider OVER';
        }
        if ($stats['games'] < 10) {
            $notes[] = 'Limited sample size on this umpire';
        }
        
        return $notes;
    }
    
    private function _fetch_bullpen_data($team) {
        // Calculate bullpen fatigue
        $query = "SELECT COUNT(*) as games_last_3, AVG(innings) as avg_innings 
                  FROM lm_mlb_schedule 
                  WHERE (home_team LIKE '%$team%' OR away_team LIKE '%$team%') 
                  AND game_date >= DATE_SUB(NOW(), INTERVAL 3 DAY)";
        
        $res = $this->conn->query($query);
        $fatigue = array('games_last_3' => 0, 'fatigue_score' => 0);
        
        if ($res && $row = $res->fetch_assoc()) {
            $games = (int)$row['games_last_3'];
            $fatigue['games_last_3'] = $games;
            $fatigue['fatigue_score'] = min(10, $games * 2); // 0-10 scale
        }
        
        return array(
            'fatigue' => $fatigue,
            'key_relievers' => $this->_get_key_relievers($team),
            'closer_status' => $this->_get_closer_status($team)
        );
    }
    
    private function _get_key_relievers($team) {
        // Would fetch from stats API
        return array(); // Placeholder
    }
    
    private function _get_closer_status($team) {
        // Would fetch injury/closer status
        return array('name' => '', 'available' => true);
    }
    
    private function _fetch_park_factors($team) {
        $team_key = strtolower($team);
        
        // 2023-2024 park factors (ESPN data)
        $factors = array(
            'colorado rockies' => array('runs' => 1.30, 'hr' => 1.25, 'hits' => 1.15), // Coors Field
            'boston red sox' => array('runs' => 1.10, 'hr' => 1.05, 'hits' => 1.08), // Fenway
            'new york yankees' => array('runs' => 1.05, 'hr' => 1.15, 'hits' => 0.98),
            'chicago cubs' => array('runs' => 1.08, 'hr' => 1.02, 'hits' => 1.05), // Wrigley
            'cincinnati reds' => array('runs' => 1.12, 'hr' => 1.20, 'hits' => 1.02),
            'philadelphia phillies' => array('runs' => 1.05, 'hr' => 1.10, 'hits' => 1.00),
            'texas rangers' => array('runs' => 1.08, 'hr' => 1.05, 'hits' => 1.02),
            'arizona diamondbacks' => array('runs' => 1.05, 'hr' => 0.95, 'hits' => 1.02),
            'houston astros' => array('runs' => 0.98, 'hr' => 1.02, 'hits' => 0.98),
            'tampa bay rays' => array('runs' => 0.92, 'hr' => 0.88, 'hits' => 0.95), // Trop
            'san francisco giants' => array('runs' => 0.88, 'hr' => 0.82, 'hits' => 0.92), // Oracle Park
            'los angeles dodgers' => array('runs' => 0.95, 'hr' => 1.08, 'hits' => 0.95),
            'san diego padres' => array('runs' => 0.92, 'hr' => 0.90, 'hits' => 0.94),
            'oakland athletics' => array('runs' => 0.90, 'hr' => 0.85, 'hits' => 0.92),
            'miami marlins' => array('runs' => 0.88, 'hr' => 0.80, 'hits' => 0.95),
            'seattle mariners' => array('runs' => 0.92, 'hr' => 0.90, 'hits' => 0.92),
            'pittsburgh pirates' => array('runs' => 0.90, 'hr' => 0.88, 'hits' => 0.95),
            'new york mets' => array('runs' => 0.95, 'hr' => 0.95, 'hits' => 0.98),
            'st. louis cardinals' => array('runs' => 0.92, 'hr' => 0.90, 'hits' => 0.98),
            'detroit tigers' => array('runs' => 0.95, 'hr' => 0.88, 'hits' => 0.98),
        );
        
        foreach ($factors as $key => $data) {
            if (strpos($team_key, $key) !== false || strpos($key, $team_key) !== false) {
                return $data;
            }
        }
        
        return array('runs' => 1.0, 'hr' => 1.0, 'hits' => 1.0);
    }
    
    private function _interpret_park_factors($factors) {
        $runs = isset($factors['runs']) ? $factors['runs'] : 1.0;
        $hr = isset($factors['hr']) ? $factors['hr'] : 1.0;
        
        if ($runs > 1.15) return 'Extreme hitters park';
        if ($runs > 1.05) return 'Slight hitters park';
        if ($runs < 0.90) return 'Extreme pitchers park';
        if ($runs < 0.95) return 'Slight pitchers park';
        return 'Neutral park';
    }
    
    private function _generate_recommendations($analysis) {
        $recs = array();
        
        // Pitcher-based recommendations
        $pitcher_adv = isset($analysis['pitchers']['advantage']) ? $analysis['pitchers']['advantage'] : 'even';
        if ($pitcher_adv === 'home_strong') {
            $recs[] = 'Strong home pitching advantage - lean home team / UNDER';
        } elseif ($pitcher_adv === 'away_strong') {
            $recs[] = 'Strong away pitching advantage - lean away team / UNDER';
        }
        
        // Umpire-based
        $umpire_impact = isset($analysis['umpire']['impact_score']) ? $analysis['umpire']['impact_score'] : 0;
        if ($umpire_impact < -1) {
            $recs[] = 'Pitcher-friendly umpire - consider UNDER';
        } elseif ($umpire_impact > 1) {
            $recs[] = 'Hitter-friendly umpire - consider OVER';
        }
        
        // Park-based
        $park_runs = isset($analysis['park_factors']['runs_factor']) ? $analysis['park_factors']['runs_factor'] : 1.0;
        if ($park_runs > 1.15) {
            $recs[] = 'Extreme hitters park (Coors/etc) - strongly consider OVER';
        } elseif ($park_runs < 0.90) {
            $recs[] = 'Extreme pitchers park - consider UNDER';
        }
        
        return $recs;
    }
    
    private function _fetch_pitcher_stats($name) {
        // Would integrate with stats API
        return array();
    }
    
    private function _load_umpire_data() {
        // Load from database or defaults
    }
    
    private function _http_get($url, $timeout = 10) {
        if (function_exists('curl_init')) {
            $ch = curl_init($url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
            curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0');
            $body = curl_exec($ch);
            curl_close($ch);
            return $body !== false ? $body : null;
        }
        return null;
    }
    
    private function _ensure_tables() {
        $this->conn->query("CREATE TABLE IF NOT EXISTS lm_mlb_analysis (
            id INT AUTO_INCREMENT PRIMARY KEY,
            game_id VARCHAR(50),
            game_date DATE,
            home_team VARCHAR(100),
            away_team VARCHAR(100),
            home_pitcher VARCHAR(100),
            away_pitcher VARCHAR(100),
            pitcher_advantage VARCHAR(20),
            umpire VARCHAR(100),
            umpire_impact DECIMAL(3,1),
            park_factor_runs DECIMAL(4,2),
            recommendations TEXT,
            analyzed_at DATETIME DEFAULT NOW(),
            UNIQUE KEY idx_game (game_id),
            INDEX idx_date (game_date)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
        
        $this->conn->query("CREATE TABLE IF NOT EXISTS lm_umpire_stats (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            games INT DEFAULT 0,
            avg_runs_per_game DECIMAL(4,2),
            strike_zone VARCHAR(20),
            consistency VARCHAR(20),
            updated_at DATETIME DEFAULT NOW(),
            UNIQUE KEY idx_name (name)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
    }
}

// API Endpoint
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'analyze';
$analysis = new MLBDeepAnalysis($conn);

if ($action === 'analyze') {
    $home = isset($_GET['home']) ? $_GET['home'] : '';
    $away = isset($_GET['away']) ? $_GET['away'] : '';
    $date = isset($_GET['date']) ? $_GET['date'] : date('Y-m-d');
    
    if ($home && $away) {
        $result = $analysis->analyze_matchup($home, $away, $date);
        echo json_encode(array('ok' => true, 'analysis' => $result));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing home or away team'));
    }
} elseif ($action === 'store') {
    $game_id = isset($_GET['game_id']) ? $_GET['game_id'] : '';
    $home = isset($_GET['home']) ? $_GET['home'] : '';
    $away = isset($_GET['away']) ? $_GET['away'] : '';
    $date = isset($_GET['date']) ? $_GET['date'] : date('Y-m-d');
    
    if ($game_id && $home && $away) {
        $analysis->store_analysis($game_id, $home, $away, $date);
        echo json_encode(array('ok' => true, 'message' => 'Analysis stored'));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing parameters'));
    }
} else {
    echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

$conn->close();
?>
