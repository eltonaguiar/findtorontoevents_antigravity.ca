<?php
/**
 * Travel and Altitude Effects Calculator
 * Models fatigue from travel distance, time zones, and altitude effects
 * PHP 5.2 compatible
 */

require_once dirname(dirname(__FILE__)) . '/sports_db_connect.php';

class TravelAltitudeModule {
    private $conn;
    private $team_locations = array();
    
    // NBA/NHL arena coordinates
    private $arena_coords = array(
        // NBA
        'atlanta hawks' => array('lat' => 33.7573, 'lon' => -84.3963, 'tz' => 'America/New_York', 'altitude' => 1050),
        'boston celtics' => array('lat' => 42.3662, 'lon' => -71.0621, 'tz' => 'America/New_York', 'altitude' => 20),
        'brooklyn nets' => array('lat' => 40.6826, 'lon' => -73.9754, 'tz' => 'America/New_York', 'altitude' => 20),
        'charlotte hornets' => array('lat' => 35.2251, 'lon' => -80.8392, 'tz' => 'America/New_York', 'altitude' => 750),
        'chicago bulls' => array('lat' => 41.8807, 'lon' => -87.6742, 'tz' => 'America/Chicago', 'altitude' => 600),
        'cleveland cavaliers' => array('lat' => 41.4965, 'lon' => -81.6882, 'tz' => 'America/New_York', 'altitude' => 650),
        'dallas mavericks' => array('lat' => 32.7905, 'lon' => -96.8103, 'tz' => 'America/Chicago', 'altitude' => 420),
        'denver nuggets' => array('lat' => 39.7487, 'lon' => -105.0077, 'tz' => 'America/Denver', 'altitude' => 5280),
        'detroit pistons' => array('lat' => 42.3411, 'lon' => -83.0554, 'tz' => 'America/New_York', 'altitude' => 600),
        'golden state warriors' => array('lat' => 37.7680, 'lon' => -122.3876, 'tz' => 'America/Los_Angeles', 'altitude' => 20),
        'houston rockets' => array('lat' => 29.7508, 'lon' => -95.3621, 'tz' => 'America/Chicago', 'altitude' => 45),
        'indiana pacers' => array('lat' => 39.7640, 'lon' => -86.1555, 'tz' => 'America/New_York', 'altitude' => 715),
        'los angeles clippers' => array('lat' => 34.0430, 'lon' => -118.2673, 'tz' => 'America/Los_Angeles', 'altitude' => 150),
        'los angeles lakers' => array('lat' => 34.0430, 'lon' => -118.2673, 'tz' => 'America/Los_Angeles', 'altitude' => 150),
        'memphis grizzlies' => array('lat' => 35.1382, 'lon' => -90.0506, 'tz' => 'America/Chicago', 'altitude' => 270),
        'miami heat' => array('lat' => 25.7814, 'lon' => -80.1870, 'tz' => 'America/New_York', 'altitude' => 10),
        'milwaukee bucks' => array('lat' => 43.0451, 'lon' => -87.9172, 'tz' => 'America/Chicago', 'altitude' => 600),
        'minnesota timberwolves' => array('lat' => 44.9795, 'lon' => -93.2763, 'tz' => 'America/Chicago', 'altitude' => 850),
        'new orleans pelicans' => array('lat' => 29.9490, 'lon' => -90.0821, 'tz' => 'America/Chicago', 'altitude' => 5),
        'new york knicks' => array('lat' => 40.7505, 'lon' => -73.9934, 'tz' => 'America/New_York', 'altitude' => 30),
        'oklahoma city thunder' => array('lat' => 35.4634, 'lon' => -97.5151, 'tz' => 'America/Chicago', 'altitude' => 1200),
        'orlando magic' => array('lat' => 28.5392, 'lon' => -81.3839, 'tz' => 'America/New_York', 'altitude' => 100),
        'philadelphia 76ers' => array('lat' => 39.9012, 'lon' => -75.1720, 'tz' => 'America/New_York', 'altitude' => 40),
        'phoenix suns' => array('lat' => 33.4457, 'lon' => -112.0712, 'tz' => 'America/Phoenix', 'altitude' => 1100),
        'portland trail blazers' => array('lat' => 45.5316, 'lon' => -122.6668, 'tz' => 'America/Los_Angeles', 'altitude' => 30),
        'sacramento kings' => array('lat' => 38.5802, 'lon' => -121.4997, 'tz' => 'America/Los_Angeles', 'altitude' => 30),
        'san antonio spurs' => array('lat' => 29.4270, 'lon' => -98.4375, 'tz' => 'America/Chicago', 'altitude' => 650),
        'toronto raptors' => array('lat' => 43.6435, 'lon' => -79.3791, 'tz' => 'America/Toronto', 'altitude' => 270),
        'utah jazz' => array('lat' => 40.7683, 'lon' => -111.9011, 'tz' => 'America/Denver', 'altitude' => 4200),
        'washington wizards' => array('lat' => 38.8982, 'lon' => -77.0209, 'tz' => 'America/New_York', 'altitude' => 20),
        
        // NHL
        'anaheim ducks' => array('lat' => 33.8078, 'lon' => -117.8765, 'tz' => 'America/Los_Angeles', 'altitude' => 150),
        'arizona coyotes' => array('lat' => 33.5324, 'lon' => -112.2614, 'tz' => 'America/Phoenix', 'altitude' => 1100),
        'boston bruins' => array('lat' => 42.3662, 'lon' => -71.0621, 'tz' => 'America/New_York', 'altitude' => 20),
        'buffalo sabres' => array('lat' => 42.8751, 'lon' => -78.8765, 'tz' => 'America/New_York', 'altitude' => 600),
        'calgary flames' => array('lat' => 51.0375, 'lon' => -114.0519, 'tz' => 'America/Edmonton', 'altitude' => 3400),
        'carolina hurricanes' => array('lat' => 35.8033, 'lon' => -78.7218, 'tz' => 'America/New_York', 'altitude' => 350),
        'chicago blackhawks' => array('lat' => 41.8807, 'lon' => -87.6742, 'tz' => 'America/Chicago', 'altitude' => 600),
        'colorado avalanche' => array('lat' => 39.7487, 'lon' => -105.0077, 'tz' => 'America/Denver', 'altitude' => 5280),
        'columbus blue jackets' => array('lat' => 39.9692, 'lon' => -83.0060, 'tz' => 'America/New_York', 'altitude' => 750),
        'dallas stars' => array('lat' => 32.7905, 'lon' => -96.8103, 'tz' => 'America/Chicago', 'altitude' => 420),
        'detroit red wings' => array('lat' => 42.3411, 'lon' => -83.0554, 'tz' => 'America/New_York', 'altitude' => 600),
        'edmonton oilers' => array('lat' => 53.5461, 'lon' => -113.4978, 'tz' => 'America/Edmonton', 'altitude' => 2200),
        'florida panthers' => array('lat' => 26.1583, 'lon' => -80.3255, 'tz' => 'America/New_York', 'altitude' => 10),
        'los angeles kings' => array('lat' => 34.0430, 'lon' => -118.2673, 'tz' => 'America/Los_Angeles', 'altitude' => 150),
        'minnesota wild' => array('lat' => 44.9448, 'lon' => -93.1011, 'tz' => 'America/Chicago', 'altitude' => 850),
        'montreal canadiens' => array('lat' => 45.4961, 'lon' => -73.5693, 'tz' => 'America/New_York', 'altitude' => 100),
        'nashville predators' => array('lat' => 36.1592, 'lon' => -86.7785, 'tz' => 'America/Chicago', 'altitude' => 550),
        'new jersey devils' => array('lat' => 40.7336, 'lon' => -74.1711, 'tz' => 'America/New_York', 'altitude' => 30),
        'new york islanders' => array('lat' => 40.7118, 'lon' => -73.7260, 'tz' => 'America/New_York', 'altitude' => 30),
        'new york rangers' => array('lat' => 40.7505, 'lon' => -73.9934, 'tz' => 'America/New_York', 'altitude' => 30),
        'ottawa senators' => array('lat' => 45.2969, 'lon' => -75.9272, 'tz' => 'America/New_York', 'altitude' => 230),
        'philadelphia flyers' => array('lat' => 39.9012, 'lon' => -75.1720, 'tz' => 'America/New_York', 'altitude' => 40),
        'pittsburgh penguins' => array('lat' => 40.4395, 'lon' => -79.9893, 'tz' => 'America/New_York', 'altitude' => 750),
        'san jose sharks' => array('lat' => 37.3328, 'lon' => -121.9012, 'tz' => 'America/Los_Angeles', 'altitude' => 100),
        'seattle kraken' => array('lat' => 47.6221, 'lon' => -122.3541, 'tz' => 'America/Los_Angeles', 'altitude' => 60),
        'st. louis blues' => array('lat' => 38.6268, 'lon' => -90.2027, 'tz' => 'America/Chicago', 'altitude' => 465),
        'tampa bay lightning' => array('lat' => 27.9427, 'lon' => -82.4518, 'tz' => 'America/New_York', 'altitude' => 45),
        'toronto maple leafs' => array('lat' => 43.6435, 'lon' => -79.3791, 'tz' => 'America/Toronto', 'altitude' => 270),
        'vancouver canucks' => array('lat' => 49.2778, 'lon' => -123.1088, 'tz' => 'America/Vancouver', 'altitude' => 170),
        'vegas golden knights' => array('lat' => 36.1029, 'lon' => -115.1784, 'tz' => 'America/Los_Angeles', 'altitude' => 2000),
        'washington capitals' => array('lat' => 38.8982, 'lon' => -77.0209, 'tz' => 'America/New_York', 'altitude' => 20),
        'winnipeg jets' => array('lat' => 49.8926, 'lon' => -97.1439, 'tz' => 'America/Winnipeg', 'altitude' => 780)
    );
    
    public function __construct($connection) {
        $this->conn = $connection;
        $this->_ensure_tables();
    }
    
    /**
     * Calculate travel fatigue for a game
     */
    public function calculate_travel_fatigue($away_team, $home_team, $game_time) {
        $away_key = $this->_normalize_team_name($away_team);
        $home_key = $this->_normalize_team_name($home_team);
        
        if (!isset($this->arena_coords[$away_key]) || !isset($this->arena_coords[$home_key])) {
            return array('error' => 'Team coordinates not found');
        }
        
        $away_data = $this->arena_coords[$away_key];
        $home_data = $this->arena_coords[$home_key];
        
        // Calculate distance
        $distance = $this->_haversine_distance(
            $away_data['lat'], $away_data['lon'],
            $home_data['lat'], $home_data['lon']
        );
        
        // Calculate time zone change
        $tz_diff = $this->_timezone_difference($away_data['tz'], $home_data['tz']);
        
        // Check for altitude change
        $altitude_change = $home_data['altitude'] - $away_data['altitude'];
        $altitude_impact = $this->_calculate_altitude_fatigue($altitude_change);
        
        // Check for back-to-back
        $b2b_penalty = $this->_check_back_to_back($away_team, $game_time);
        
        // Calculate total fatigue score
        $fatigue_score = $this->_calculate_fatigue_score($distance, $tz_diff, $b2b_penalty, $altitude_impact);
        
        return array(
            'away_team' => $away_team,
            'home_team' => $home_team,
            'distance_miles' => round($distance, 1),
            'timezone_change' => $tz_diff,
            'altitude_change' => $altitude_change,
            'altitude_impact' => $altitude_impact,
            'back_to_back' => $b2b_penalty > 0,
            'fatigue_score' => $fatigue_score,
            'fatigue_level' => $this->_fatigue_level($fatigue_score),
            'betting_impact' => $this->_betting_recommendation($fatigue_score)
        );
    }
    
    /**
     * Get altitude effect on performance
     */
    public function get_altitude_effect($team, $sport) {
        $key = $this->_normalize_team_name($team);
        
        if (!isset($this->arena_coords[$key])) {
            return array('error' => 'Team not found');
        }
        
        $altitude = $this->arena_coords[$key]['altitude'];
        
        // Altitude effects
        if ($altitude < 2000) {
            return array(
                'altitude' => $altitude,
                'effect' => 'minimal',
                'notes' => 'Sea level to low elevation - no significant impact'
            );
        } elseif ($altitude < 4000) {
            return array(
                'altitude' => $altitude,
                'effect' => 'mild',
                'notes' => 'Mild altitude - slight endurance advantage for home team',
                'scoring_boost' => 0.02 // 2% boost
            );
        } elseif ($altitude < 5000) {
            return array(
                'altitude' => $altitude,
                'effect' => 'moderate',
                'notes' => 'Moderate altitude (Utah) - significant endurance advantage',
                'scoring_boost' => 0.05, // 5% boost for home team
                'fatigue_factor' => 'Visitors tire 10-15% faster'
            );
        } else {
            // Denver (5280 ft) - extreme
            return array(
                'altitude' => $altitude,
                'effect' => 'extreme',
                'notes' => 'Extreme altitude (Denver) - major home advantage',
                'scoring_boost' => 0.08, // 8% boost
                'fatigue_factor' => 'Visitors tire 20-25% faster',
                'oxygen_impact' => 'Reduced oxygen affects recovery',
                'betting_note' => 'Favor Denver in 2nd half, back-to-backs'
            );
        }
    }
    
    /**
     * Analyze road trip severity
     */
    public function analyze_road_trip($team, $games) {
        if (count($games) < 2) {
            return array('error' => 'Need at least 2 games for road trip analysis');
        }
        
        $total_distance = 0;
        $timezone_crossings = 0;
        $current_tz = null;
        $game_count = count($games);
        
        for ($i = 0; $i < $game_count - 1; $i++) {
            $from_key = $this->_normalize_team_name($games[$i]['home']);
            $to_key = $this->_normalize_team_name($games[$i + 1]['home']);
            
            if (!isset($this->arena_coords[$from_key]) || !isset($this->arena_coords[$to_key])) {
                continue;
            }
            
            $from = $this->arena_coords[$from_key];
            $to = $this->arena_coords[$to_key];
            
            $leg_distance = $this->_haversine_distance($from['lat'], $from['lon'], $to['lat'], $to['lon']);
            $total_distance += $leg_distance;
            
            if ($current_tz === null) {
                $current_tz = $from['tz'];
            }
            if ($to['tz'] !== $current_tz) {
                $timezone_crossings++;
                $current_tz = $to['tz'];
            }
        }
        
        // Calculate severity
        $avg_distance = $total_distance / ($game_count - 1);
        $trip_length = $game_count;
        
        $severity_score = 0;
        if ($avg_distance > 1500) $severity_score += 3; // Long flights
        elseif ($avg_distance > 800) $severity_score += 2;
        elseif ($avg_distance > 400) $severity_score += 1;
        
        $severity_score += $timezone_crossings * 2;
        $severity_score += max(0, $trip_length - 3); // Penalty for trips > 3 games
        
        return array(
            'total_distance' => round($total_distance, 1),
            'avg_leg_distance' => round($avg_distance, 1),
            'games' => $game_count,
            'timezone_crossings' => $timezone_crossings,
            'severity_score' => $severity_score,
            'severity' => $severity_score > 6 ? 'extreme' : ($severity_score > 3 ? 'high' : ($severity_score > 1 ? 'moderate' : 'low')),
            'betting_note' => $severity_score > 5 ? 'Avoid betting on this team during this trip' : 'Monitor for fatigue'
        );
    }
    
    /**
     * Store travel analysis
     */
    public function store_travel_analysis($game_id, $away, $home, $game_time) {
        $analysis = $this->calculate_travel_fatigue($away, $home, $game_time);
        
        if (isset($analysis['error'])) return false;
        
        $game_id_esc = $this->conn->real_escape_string($game_id);
        $away_esc = $this->conn->real_escape_string($away);
        $home_esc = $this->conn->real_escape_string($home);
        $dist = $analysis['distance_miles'];
        $tz = $analysis['timezone_change'];
        $alt = $analysis['altitude_change'];
        $fatigue = $analysis['fatigue_score'];
        $level = $this->conn->real_escape_string($analysis['fatigue_level']);
        
        $query = "INSERT INTO lm_travel_analysis 
                  (game_id, away_team, home_team, distance_miles, timezone_change, altitude_change, 
                   fatigue_score, fatigue_level, analyzed_at)
                  VALUES ('$game_id_esc', '$away_esc', '$home_esc', $dist, $tz, $alt, $fatigue, '$level', NOW())
                  ON DUPLICATE KEY UPDATE
                  distance_miles=VALUES(distance_miles), timezone_change=VALUES(timezone_change),
                  altitude_change=VALUES(altitude_change), fatigue_score=VALUES(fatigue_score),
                  fatigue_level=VALUES(fatigue_level), analyzed_at=NOW()";
        
        return $this->conn->query($query);
    }
    
    // ════════════════════════════════════════════════════════════
    //  Private Helper Methods
    // ════════════════════════════════════════════════════════════
    
    private function _haversine_distance($lat1, $lon1, $lat2, $lon2) {
        $earth_radius = 3959; // miles
        
        $d_lat = deg2rad($lat2 - $lat1);
        $d_lon = deg2rad($lon2 - $lon1);
        
        $a = sin($d_lat / 2) * sin($d_lat / 2) +
             cos(deg2rad($lat1)) * cos(deg2rad($lat2)) *
             sin($d_lon / 2) * sin($d_lon / 2);
        
        $c = 2 * atan2(sqrt($a), sqrt(1 - $a));
        
        return $earth_radius * $c;
    }
    
    private function _timezone_difference($tz1, $tz2) {
        // Simplified timezone offsets (hours)
        $offsets = array(
            'America/New_York' => -5,
            'America/Toronto' => -5,
            'America/Chicago' => -6,
            'America/Denver' => -7,
            'America/Phoenix' => -7,
            'America/Edmonton' => -7,
            'America/Los_Angeles' => -8,
            'America/Vancouver' => -8,
            'America/Winnipeg' => -6
        );
        
        $o1 = isset($offsets[$tz1]) ? $offsets[$tz1] : 0;
        $o2 = isset($offsets[$tz2]) ? $offsets[$tz2] : 0;
        
        return abs($o1 - $o2);
    }
    
    private function _calculate_altitude_fatigue($altitude_change) {
        if ($altitude_change < 2000) return 0;
        if ($altitude_change < 4000) return 1; // Mild fatigue
        return 2; // Significant fatigue
    }
    
    private function _check_back_to_back($team, $game_time) {
        // Check if team played yesterday
        $team_esc = $this->conn->real_escape_string($team);
        $yesterday = date('Y-m-d', strtotime($game_time . ' -1 day'));
        
        $query = "SELECT COUNT(*) as count FROM lm_nba_schedule 
                  WHERE (away_team LIKE '%$team_esc%' OR home_team LIKE '%$team_esc%')
                  AND DATE(game_date) = '$yesterday'";
        
        $res = $this->conn->query($query);
        if ($res && $row = $res->fetch_assoc()) {
            return $row['count'] > 0 ? 2 : 0; // 2 point penalty for B2B
        }
        
        return 0;
    }
    
    private function _calculate_fatigue_score($distance, $tz_diff, $b2b_penalty, $altitude_impact) {
        $score = 0;
        
        // Distance factor
        if ($distance > 2000) $score += 3; // Cross-country
        elseif ($distance > 1500) $score += 2;
        elseif ($distance > 1000) $score += 1;
        
        // Time zone factor (each hour = 0.5 points)
        $score += $tz_diff * 0.5;
        
        // B2B penalty
        $score += $b2b_penalty;
        
        // Altitude impact
        $score += $altitude_impact;
        
        // Bonus for combination (e.g., B2B + cross-country)
        if ($b2b_penalty > 0 && $distance > 1500) $score += 1;
        
        return min(10, round($score, 1)); // Cap at 10
    }
    
    private function _fatigue_level($score) {
        if ($score >= 7) return 'extreme';
        if ($score >= 5) return 'high';
        if ($score >= 3) return 'moderate';
        if ($score >= 1) return 'mild';
        return 'none';
    }
    
    private function _betting_recommendation($score) {
        if ($score >= 7) {
            return 'Strong fade opportunity - extreme travel fatigue';
        } elseif ($score >= 5) {
            return 'Moderate fade - significant travel disadvantage';
        } elseif ($score >= 3) {
            return 'Slight travel disadvantage noted';
        }
        return 'No significant travel impact';
    }
    
    private function _normalize_team_name($name) {
        $name = strtolower(trim($name));
        
        // Common normalizations
        $map = array(
            'la clippers' => 'los angeles clippers',
            'la lakers' => 'los angeles lakers',
            'la kings' => 'los angeles kings',
            'vegas' => 'vegas golden knights',
            'st louis' => 'st. louis',
            'saint louis' => 'st. louis',
            'nj devils' => 'new jersey devils',
            'sj sharks' => 'san jose sharks'
        );
        
        foreach ($map as $from => $to) {
            if (strpos($name, $from) !== false) {
                $name = str_replace($from, $to, $name);
            }
        }
        
        return $name;
    }
    
    private function _ensure_tables() {
        $this->conn->query("CREATE TABLE IF NOT EXISTS lm_travel_analysis (
            id INT AUTO_INCREMENT PRIMARY KEY,
            game_id VARCHAR(50),
            away_team VARCHAR(100),
            home_team VARCHAR(100),
            distance_miles DECIMAL(8,1),
            timezone_change INT,
            altitude_change INT,
            fatigue_score DECIMAL(3,1),
            fatigue_level VARCHAR(20),
            analyzed_at DATETIME DEFAULT NOW(),
            UNIQUE KEY idx_game (game_id),
            INDEX idx_teams (away_team, home_team)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
    }
}

// API Endpoint
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'fatigue';
$module = new TravelAltitudeModule($conn);

if ($action === 'fatigue') {
    $away = isset($_GET['away']) ? $_GET['away'] : '';
    $home = isset($_GET['home']) ? $_GET['home'] : '';
    $time = isset($_GET['time']) ? $_GET['time'] : date('Y-m-d H:i:s');
    
    if ($away && $home) {
        $result = $module->calculate_travel_fatigue($away, $home, $time);
        echo json_encode(array('ok' => true, 'analysis' => $result));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing away or home team'));
    }
} elseif ($action === 'altitude') {
    $team = isset($_GET['team']) ? $_GET['team'] : '';
    $sport = isset($_GET['sport']) ? $_GET['sport'] : '';
    
    if ($team) {
        $result = $module->get_altitude_effect($team, $sport);
        echo json_encode(array('ok' => true, 'altitude' => $result));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing team'));
    }
} elseif ($action === 'roadtrip') {
    $team = isset($_GET['team']) ? $_GET['team'] : '';
    $games_json = isset($_GET['games']) ? $_GET['games'] : '';
    $games = json_decode($games_json, true);
    
    if ($team && is_array($games)) {
        $result = $module->analyze_road_trip($team, $games);
        echo json_encode(array('ok' => true, 'road_trip' => $result));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing team or games'));
    }
} elseif ($action === 'store') {
    $game_id = isset($_GET['game_id']) ? $_GET['game_id'] : '';
    $away = isset($_GET['away']) ? $_GET['away'] : '';
    $home = isset($_GET['home']) ? $_GET['home'] : '';
    $time = isset($_GET['time']) ? $_GET['time'] : date('Y-m-d H:i:s');
    
    if ($game_id && $away && $home) {
        $module->store_travel_analysis($game_id, $away, $home, $time);
        echo json_encode(array('ok' => true, 'message' => 'Stored'));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing parameters'));
    }
} else {
    echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

$conn->close();
?>
