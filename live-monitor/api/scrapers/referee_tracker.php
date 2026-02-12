<?php
/**
 * Referee/Official Bias Tracking Module
 * Tracks tendencies and biases for NFL, NBA, and NHL officials
 * PHP 5.2 compatible
 */

require_once dirname(dirname(__FILE__)) . '/sports_db_connect.php';

class RefereeTracker {
    private $conn;
    private $errors = array();
    
    // Referee tendency profiles (would be updated from database)
    private $ref_profiles = array();
    
    public function __construct($connection) {
        $this->conn = $connection;
        $this->_ensure_tables();
        $this->_load_referee_data();
    }
    
    /**
     * Get referee analysis for a game
     */
    public function get_referee_impact($sport, $home_team, $away_team, $game_date = null) {
        if (!$game_date) $game_date = date('Y-m-d');
        
        // Fetch assigned officials
        $officials = $this->_fetch_officials($sport, $home_team, $game_date);
        
        if (!$officials) {
            return array('error' => 'Official assignments not available');
        }
        
        $analysis = array(
            'sport' => $sport,
            'home_team' => $home_team,
            'away_team' => $away_team,
            'game_date' => $game_date,
            'officials' => array(),
            'combined_impact' => array()
        );
        
        foreach ($officials as $official) {
            $profile = $this->_get_official_profile($sport, $official['name'], $official['position']);
            $analysis['officials'][] = array(
                'name' => $official['name'],
                'position' => $official['position'],
                'profile' => $profile,
                'impact' => $this->_calculate_official_impact($sport, $profile)
            );
        }
        
        $analysis['combined_impact'] = $this->_combine_impacts($analysis['officials'], $sport);
        
        return $analysis;
    }
    
    /**
     * Store referee analysis
     */
    public function store_analysis($game_id, $sport, $home, $away, $date) {
        $analysis = $this->get_referee_impact($sport, $home, $away, $date);
        
        if (isset($analysis['error'])) return false;
        
        $game_id_esc = $this->conn->real_escape_string($game_id);
        $sport_esc = $this->conn->real_escape_string($sport);
        $home_esc = $this->conn->real_escape_string($home);
        $away_esc = $this->conn->real_escape_string($away);
        
        // Store main official (referee in NFL, crew chief in NBA)
        $main_official = isset($analysis['officials'][0]) ? $analysis['officials'][0] : null;
        $ref_name = $main_official ? $this->conn->real_escape_string($main_official['name']) : '';
        $ref_pos = $main_official ? $this->conn->real_escape_string($main_official['position']) : '';
        
        $foul_diff = isset($analysis['combined_impact']['foul_differential']) ? $analysis['combined_impact']['foul_differential'] : 0;
        $total_bias = isset($analysis['combined_impact']['total_bias_score']) ? $analysis['combined_impact']['total_bias_score'] : 0;
        $notes = isset($analysis['combined_impact']['betting_notes']) ? $this->conn->real_escape_string(json_encode($analysis['combined_impact']['betting_notes'])) : '';
        
        $query = "INSERT INTO lm_referee_analysis 
                  (game_id, sport, home_team, away_team, game_date, main_official, official_position,
                   foul_differential_expectation, total_bias_score, betting_notes, analyzed_at)
                  VALUES ('$game_id_esc', '$sport_esc', '$home_esc', '$away_esc', '$date', '$ref_name', '$ref_pos',
                          $foul_diff, $total_bias, '$notes', NOW())
                  ON DUPLICATE KEY UPDATE
                  main_official=VALUES(main_official), official_position=VALUES(official_position),
                  foul_differential_expectation=VALUES(foul_differential_expectation),
                  total_bias_score=VALUES(total_bias_score), betting_notes=VALUES(betting_notes), analyzed_at=NOW()";
        
        return $this->conn->query($query);
    }
    
    /**
     * Update referee stats from recent games
     */
    public function update_referee_stats($sport, $referee_name, $game_data) {
        $esc_name = $this->conn->real_escape_string($referee_name);
        $esc_sport = $this->conn->real_escape_string($sport);
        
        // Extract stats based on sport
        if ($sport === 'nfl') {
            $penalties = isset($game_data['total_penalties']) ? (int)$game_data['total_penalties'] : 0;
            $pen_yards = isset($game_data['penalty_yards']) ? (int)$game_data['penalty_yards'] : 0;
            
            $query = "INSERT INTO lm_referee_stats (sport, name, games_called, avg_penalties_per_game, 
                      avg_penalty_yards, last_updated)
                      VALUES ('$esc_sport', '$esc_name', 1, $penalties, $pen_yards, NOW())
                      ON DUPLICATE KEY UPDATE
                      games_called = games_called + 1,
                      avg_penalties_per_game = ((avg_penalties_per_game * (games_called - 1)) + $penalties) / games_called,
                      avg_penalty_yards = ((avg_penalty_yards * (games_called - 1)) + $pen_yards) / games_called,
                      last_updated = NOW()";
            
        } elseif ($sport === 'nba') {
            $fouls = isset($game_data['total_fouls']) ? (int)$game_data['total_fouls'] : 0;
            $fta = isset($game_data['free_throw_attempts']) ? (int)$game_data['free_throw_attempts'] : 0;
            
            $query = "INSERT INTO lm_referee_stats (sport, name, games_called, avg_fouls_per_game,
                      avg_fta_per_game, last_updated)
                      VALUES ('$esc_sport', '$esc_name', 1, $fouls, $fta, NOW())
                      ON DUPLICATE KEY UPDATE
                      games_called = games_called + 1,
                      avg_fouls_per_game = ((avg_fouls_per_game * (games_called - 1)) + $fouls) / games_called,
                      avg_fta_per_game = ((avg_fta_per_game * (games_called - 1)) + $fta) / games_called,
                      last_updated = NOW()";
            
        } elseif ($sport === 'nhl') {
            $penalties = isset($game_data['total_penalties']) ? (int)$game_data['total_penalties'] : 0;
            $pim = isset($game_data['penalty_minutes']) ? (int)$game_data['penalty_minutes'] : 0;
            
            $query = "INSERT INTO lm_referee_stats (sport, name, games_called, avg_penalties_per_game,
                      avg_pim_per_game, last_updated)
                      VALUES ('$esc_sport', '$esc_name', 1, $penalties, $pim, NOW())
                      ON DUPLICATE KEY UPDATE
                      games_called = games_called + 1,
                      avg_penalties_per_game = ((avg_penalties_per_game * (games_called - 1)) + $penalties) / games_called,
                      avg_pim_per_game = ((avg_pim_per_game * (games_called - 1)) + $pim) / games_called,
                      last_updated = NOW()";
        }
        
        return $this->conn->query($query);
    }
    
    // ════════════════════════════════════════════════════════════
    //  Private Methods
    // ════════════════════════════════════════════════════════════
    
    private function _fetch_officials($sport, $home_team, $game_date) {
        // Scrape from various sources
        if ($sport === 'nfl') {
            return $this->_fetch_nfl_officials($home_team, $game_date);
        } elseif ($sport === 'nba') {
            return $this->_fetch_nba_officials($home_team, $game_date);
        } elseif ($sport === 'nhl') {
            return $this->_fetch_nhl_officials($home_team, $game_date);
        }
        return null;
    }
    
    private function _fetch_nfl_officials($home_team, $game_date) {
        // Scrape from NFLPenalties.com or Pro-Football-Reference
        $url = 'https://www.nflpenalties.com/officials.php';
        $body = $this->_http_get($url);
        
        if (!$body) return null;
        
        $officials = array();
        
        // Parse officials table (simplified)
        // In production, would match specific game date and teams
        
        return $officials;
    }
    
    private function _fetch_nba_officials($home_team, $game_date) {
        // Scrape from official NBA assignments
        $url = 'https://official.nba.com/referee-assignments/';
        $body = $this->_http_get($url);
        
        if (!$body) return null;
        
        $officials = array();
        
        // Parse the assignment table
        preg_match_all('/<tr[^>]*>.*?<td[^>]*>(.*?)<\/td>.*?<td[^>]*>(.*?)<\/td>.*?<td[^>]*>(.*?)<\/td>.*?<\/tr>/s', $body, $matches, PREG_SET_ORDER);
        
        foreach ($matches as $match) {
            $date = trim(strip_tags($match[1]));
            $teams = trim(strip_tags($match[2]));
            $crew = trim(strip_tags($match[3]));
            
            // Check if this row matches our game
            if (stripos($teams, $home_team) !== false && stripos($date, $game_date) !== false) {
                // Parse crew into individual officials
                $crew_members = explode(',', $crew);
                foreach ($crew_members as $member) {
                    $member = trim($member);
                    if (!empty($member)) {
                        $officials[] = array(
                            'name' => $member,
                            'position' => 'Crew Member'
                        );
                    }
                }
                break;
            }
        }
        
        return $officials;
    }
    
    private function _fetch_nhl_officials($home_team, $game_date) {
        // NHL officials are harder to predict in advance
        // Often announced day-of-game
        return array();
    }
    
    private function _get_official_profile($sport, $name, $position) {
        $esc_name = $this->conn->real_escape_string($name);
        $esc_sport = $this->conn->real_escape_string($sport);
        
        $res = $this->conn->query("SELECT * FROM lm_referee_stats WHERE sport='$esc_sport' AND name='$esc_name' LIMIT 1");
        
        if ($res && $row = $res->fetch_assoc()) {
            return array(
                'name' => $name,
                'games' => (int)$row['games_called'],
                'sport_specific' => $this->_get_sport_specific_stats($sport, $row)
            );
        }
        
        return array('name' => $name, 'games' => 0, 'sport_specific' => array());
    }
    
    private function _get_sport_specific_stats($sport, $row) {
        if ($sport === 'nfl') {
            return array(
                'avg_penalties' => isset($row['avg_penalties_per_game']) ? (float)$row['avg_penalties_per_game'] : 13.5,
                'avg_penalty_yards' => isset($row['avg_penalty_yards']) ? (float)$row['avg_penalty_yards'] : 110,
                'style' => $this->_classify_nfl_style($row)
            );
        } elseif ($sport === 'nba') {
            return array(
                'avg_fouls' => isset($row['avg_fouls_per_game']) ? (float)$row['avg_fouls_per_game'] : 42,
                'avg_fta' => isset($row['avg_fta_per_game']) ? (float)$row['avg_fta_per_game'] : 48,
                'style' => $this->_classify_nba_style($row)
            );
        } elseif ($sport === 'nhl') {
            return array(
                'avg_penalties' => isset($row['avg_penalties_per_game']) ? (float)$row['avg_penalties_per_game'] : 8,
                'avg_pim' => isset($row['avg_pim_per_game']) ? (float)$row['avg_pim_per_game'] : 12,
                'style' => $this->_classify_nhl_style($row)
            );
        }
        return array();
    }
    
    private function _classify_nfl_style($row) {
        $penalties = isset($row['avg_penalties_per_game']) ? (float)$row['avg_penalties_per_game'] : 13.5;
        if ($penalties > 16) return 'flag-happy';
        if ($penalties < 11) return 'lets-them-play';
        return 'average';
    }
    
    private function _classify_nba_style($row) {
        $fouls = isset($row['avg_fouls_per_game']) ? (float)$row['avg_fouls_per_game'] : 42;
        if ($fouls > 48) return 'tight-calling';
        if ($fouls < 38) return 'physical-allowed';
        return 'average';
    }
    
    private function _classify_nhl_style($row) {
        $pim = isset($row['avg_pim_per_game']) ? (float)$row['avg_pim_per_game'] : 12;
        if ($pim > 16) return 'strict';
        if ($pim < 8) return 'letting-go';
        return 'average';
    }
    
    private function _calculate_official_impact($sport, $profile) {
        $impact = array(
            'total_score' => 0,
            'fouls_expectation' => 'average',
            'home_team_bias' => 0, // -3 to +3, negative = favors away
            'betting_notes' => array()
        );
        
        if (!isset($profile['sport_specific'])) return $impact;
        
        $stats = $profile['sport_specific'];
        
        if ($sport === 'nfl') {
            $avg_pens = isset($stats['avg_penalties']) ? $stats['avg_penalties'] : 13.5;
            
            if ($stats['style'] === 'flag-happy') {
                $impact['total_score'] += 2;
                $impact['fouls_expectation'] = 'high';
                $impact['betting_notes'][] = 'More penalties expected - favors UNDER if high total';
            } elseif ($stats['style'] === 'lets-them-play') {
                $impact['total_score'] -= 1;
                $impact['fouls_expectation'] = 'low';
                $impact['betting_notes'][] = 'Fewer penalties - game flow better for offenses';
            }
            
        } elseif ($sport === 'nba') {
            $avg_fouls = isset($stats['avg_fouls']) ? $stats['avg_fouls'] : 42;
            
            if ($stats['style'] === 'tight-calling') {
                $impact['total_score'] += 2;
                $impact['fouls_expectation'] = 'high';
                $impact['betting_notes'][] = 'More fouls = more FTs - consider OVER';
                $impact['betting_notes'][] = 'Star players may sit with foul trouble';
            } elseif ($stats['style'] === 'physical-allowed') {
                $impact['total_score'] -= 1;
                $impact['fouls_expectation'] = 'low';
                $impact['betting_notes'][] = 'Physical play allowed - benefits defensive teams';
            }
            
        } elseif ($sport === 'nhl') {
            if ($stats['style'] === 'strict') {
                $impact['total_score'] += 2;
                $impact['fouls_expectation'] = 'high';
                $impact['betting_notes'][] = 'More power plays - increases scoring variance';
            } elseif ($stats['style'] === 'letting-go') {
                $impact['total_score'] -= 1;
                $impact['betting_notes'][] = 'Fewer penalties - even strength play';
            }
        }
        
        return $impact;
    }
    
    private function _combine_impacts($officials, $sport) {
        $total_score = 0;
        $foul_expectations = array();
        $all_notes = array();
        
        foreach ($officials as $official) {
            if (isset($official['impact'])) {
                $total_score += $official['impact']['total_score'];
                $foul_expectations[] = $official['impact']['fouls_expectation'];
                $all_notes = array_merge($all_notes, $official['impact']['betting_notes']);
            }
        }
        
        // Calculate average foul expectation
        $avg_fouls = 'average';
        $high_count = 0;
        $low_count = 0;
        foreach ($foul_expectations as $exp) {
            if ($exp === 'high') $high_count++;
            if ($exp === 'low') $low_count++;
        }
        if ($high_count > count($foul_expectations) / 2) $avg_fouls = 'high';
        if ($low_count > count($foul_expectations) / 2) $avg_fouls = 'low';
        
        return array(
            'total_bias_score' => $total_score,
            'foul_differential' => $avg_fouls,
            'betting_notes' => array_unique($all_notes)
        );
    }
    
    private function _load_referee_data() {
        // Load cached profiles from database
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
        $this->conn->query("CREATE TABLE IF NOT EXISTS lm_referee_stats (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sport VARCHAR(20),
            name VARCHAR(100),
            games_called INT DEFAULT 0,
            avg_penalties_per_game DECIMAL(5,2),
            avg_penalty_yards DECIMAL(6,2),
            avg_fouls_per_game DECIMAL(5,2),
            avg_fta_per_game DECIMAL(5,2),
            avg_pim_per_game DECIMAL(5,2),
            home_win_rate DECIMAL(4,3),
            consistency_score DECIMAL(4,2),
            last_updated DATETIME DEFAULT NOW(),
            INDEX idx_sport_name (sport, name)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
        
        $this->conn->query("CREATE TABLE IF NOT EXISTS lm_referee_analysis (
            id INT AUTO_INCREMENT PRIMARY KEY,
            game_id VARCHAR(50),
            sport VARCHAR(20),
            home_team VARCHAR(100),
            away_team VARCHAR(100),
            game_date DATE,
            main_official VARCHAR(100),
            official_position VARCHAR(50),
            foul_differential_expectation VARCHAR(20),
            total_bias_score DECIMAL(4,2),
            betting_notes TEXT,
            analyzed_at DATETIME DEFAULT NOW(),
            UNIQUE KEY idx_game (game_id),
            INDEX idx_date (game_date)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
    }
}

// API Endpoint
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'analyze';
$tracker = new RefereeTracker($conn);

if ($action === 'analyze') {
    $sport = isset($_GET['sport']) ? strtolower($_GET['sport']) : '';
    $home = isset($_GET['home']) ? $_GET['home'] : '';
    $away = isset($_GET['away']) ? $_GET['away'] : '';
    $date = isset($_GET['date']) ? $_GET['date'] : date('Y-m-d');
    
    if ($sport && $home && $away) {
        $result = $tracker->get_referee_impact($sport, $home, $away, $date);
        echo json_encode(array('ok' => true, 'analysis' => $result));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing parameters'));
    }
} elseif ($action === 'store') {
    $game_id = isset($_GET['game_id']) ? $_GET['game_id'] : '';
    $sport = isset($_GET['sport']) ? $_GET['sport'] : '';
    $home = isset($_GET['home']) ? $_GET['home'] : '';
    $away = isset($_GET['away']) ? $_GET['away'] : '';
    $date = isset($_GET['date']) ? $_GET['date'] : date('Y-m-d');
    
    if ($game_id && $sport && $home && $away) {
        $tracker->store_analysis($game_id, $sport, $home, $away, $date);
        echo json_encode(array('ok' => true, 'message' => 'Stored'));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing parameters'));
    }
} else {
    echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

$conn->close();
?>
