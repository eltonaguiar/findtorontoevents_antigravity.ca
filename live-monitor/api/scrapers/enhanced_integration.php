<?php
/**
 * Enhanced Sports Scraper Integration
 * Combines all gap-bridging modules into unified analysis
 * PHP 5.2 compatible
 */

require_once dirname(dirname(__FILE__)) . '/sports_db_connect.php';

class EnhancedIntegration {
    private $conn;
    private $modules = array();
    
    public function __construct($connection) {
        $this->conn = $connection;
        $this->_load_modules();
    }
    
    /**
     * Get comprehensive game analysis with all factors
     */
    public function get_comprehensive_analysis($sport, $home_team, $away_team, $game_id = null, $game_time = null) {
        if (!$game_id) $game_id = md5($home_team . $away_team . date('Y-m-d'));
        if (!$game_time) $game_time = date('Y-m-d H:i:s');
        
        $analysis = array(
            'game_id' => $game_id,
            'sport' => $sport,
            'home_team' => $home_team,
            'away_team' => $away_team,
            'game_time' => $game_time,
            'timestamp' => gmdate('Y-m-d H:i:s'),
            'factors' => array()
        );
        
        // 1. Weather Impact (NFL/MLB only)
        if ($sport === 'nfl' || $sport === 'mlb') {
            $weather = $this->_get_weather_impact($home_team, $sport, $game_time);
            $analysis['factors']['weather'] = $weather;
        }
        
        // 2. Travel/Altitude Effects (NBA/NHL primarily)
        $travel = $this->_get_travel_fatigue($away_team, $home_team, $game_time);
        $analysis['factors']['travel'] = $travel;
        
        // 3. Altitude Effect (all sports with Denver/SLC/etc)
        $altitude = $this->_get_altitude_effect($home_team, $sport);
        $analysis['factors']['altitude'] = $altitude;
        
        // 4. Referee/Officials Impact
        $refs = $this->_get_referee_impact($sport, $home_team, $away_team, $game_time);
        $analysis['factors']['officials'] = $refs;
        
        // 5. Sport-Specific Deep Analysis
        if ($sport === 'mlb') {
            $mlb = $this->_get_mlb_deep_analysis($home_team, $away_team, date('Y-m-d', strtotime($game_time)));
            $analysis['factors']['mlb_specific'] = $mlb;
        }
        
        // 6. Live Odds Comparison
        $live_odds = $this->_get_live_odds($game_id, $sport);
        $analysis['factors']['live_odds'] = $live_odds;
        
        // Calculate composite score
        $analysis['composite_score'] = $this->_calculate_composite($analysis['factors'], $sport);
        
        // Generate final recommendations
        $analysis['recommendations'] = $this->_generate_recommendations($analysis);
        
        // Store analysis
        $this->_store_comprehensive_analysis($analysis);
        
        return $analysis;
    }
    
    /**
     * Batch analyze multiple games
     */
    public function batch_analyze($games) {
        $results = array();
        
        foreach ($games as $game) {
            $sport = isset($game['sport']) ? $game['sport'] : '';
            $home = isset($game['home']) ? $game['home'] : '';
            $away = isset($game['away']) ? $game['away'] : '';
            $time = isset($game['time']) ? $game['time'] : null;
            
            if ($sport && $home && $away) {
                $results[] = $this->get_comprehensive_analysis($sport, $home, $away, null, $time);
            }
        }
        
        return $results;
    }
    
    /**
     * Get situational advantages summary
     */
    public function get_situational_edges($sport, $date = null) {
        if (!$date) $date = date('Y-m-d');
        
        // Fetch all games for date
        $games = $this->_get_days_games($sport, $date);
        
        $edges = array();
        
        foreach ($games as $game) {
            $analysis = $this->get_comprehensive_analysis(
                $sport,
                $game['home_team'],
                $game['away_team'],
                $game['game_id'],
                $game['game_time']
            );
            
            // Extract key edges
            $edge_score = 0;
            $edge_factors = array();
            
            // Weather edge
            if (isset($analysis['factors']['weather'])) {
                $w = $analysis['factors']['weather'];
                if (isset($w['impact']) && abs($w['impact']) > 1) {
                    $edge_score += abs($w['impact']);
                    $edge_factors[] = 'weather';
                }
            }
            
            // Travel edge
            if (isset($analysis['factors']['travel'])) {
                $t = $analysis['factors']['travel'];
                if (isset($t['fatigue_score']) && $t['fatigue_score'] > 4) {
                    $edge_score += $t['fatigue_score'] / 2;
                    $edge_factors[] = 'travel_fatigue';
                }
            }
            
            // Referee edge
            if (isset($analysis['factors']['officials'])) {
                $r = $analysis['factors']['officials'];
                if (isset($r['combined_impact']['total_bias_score']) && abs($r['combined_impact']['total_bias_score']) > 1) {
                    $edge_score += abs($r['combined_impact']['total_bias_score']);
                    $edge_factors[] = 'officials';
                }
            }
            
            if ($edge_score > 2) {
                $edges[] = array(
                    'game_id' => $game['game_id'],
                    'home' => $game['home_team'],
                    'away' => $game['away_team'],
                    'edge_score' => round($edge_score, 1),
                    'edge_level' => $edge_score > 6 ? 'strong' : ($edge_score > 4 ? 'moderate' : 'mild'),
                    'factors' => $edge_factors,
                    'recommendation' => $analysis['recommendations']['primary']
                );
            }
        }
        
        // Sort by edge score
        usort($edges, array($this, '_sort_by_edge_score'));
        
        return $edges;
    }
    
    // ════════════════════════════════════════════════════════════
    //  Private Module Access Methods
    // ════════════════════════════════════════════════════════════
    
    private function _get_weather_impact($home_team, $sport, $game_time) {
        $module_file = dirname(__FILE__) . '/weather_module.php';
        if (!file_exists($module_file)) return null;
        
        // Call weather module via HTTP
        $url = $this->_build_module_url('weather_module.php', array(
            'action' => 'impact',
            'home' => urlencode($home_team),
            'sport' => $sport,
            'time' => urlencode($game_time)
        ));
        
        $response = $this->_http_get($url);
        if ($response) {
            $data = json_decode($response, true);
            return isset($data['data']) ? $data['data'] : null;
        }
        return null;
    }
    
    private function _get_travel_fatigue($away_team, $home_team, $game_time) {
        $module_file = dirname(__FILE__) . '/travel_altitude_module.php';
        if (!file_exists($module_file)) return null;
        
        $url = $this->_build_module_url('travel_altitude_module.php', array(
            'action' => 'fatigue',
            'away' => urlencode($away_team),
            'home' => urlencode($home_team),
            'time' => urlencode($game_time)
        ));
        
        $response = $this->_http_get($url);
        if ($response) {
            $data = json_decode($response, true);
            return isset($data['analysis']) ? $data['analysis'] : null;
        }
        return null;
    }
    
    private function _get_altitude_effect($team, $sport) {
        $module_file = dirname(__FILE__) . '/travel_altitude_module.php';
        if (!file_exists($module_file)) return null;
        
        $url = $this->_build_module_url('travel_altitude_module.php', array(
            'action' => 'altitude',
            'team' => urlencode($team),
            'sport' => $sport
        ));
        
        $response = $this->_http_get($url);
        if ($response) {
            $data = json_decode($response, true);
            return isset($data['altitude']) ? $data['altitude'] : null;
        }
        return null;
    }
    
    private function _get_referee_impact($sport, $home_team, $away_team, $game_time) {
        $module_file = dirname(__FILE__) . '/referee_tracker.php';
        if (!file_exists($module_file)) return null;
        
        $url = $this->_build_module_url('referee_tracker.php', array(
            'action' => 'analyze',
            'sport' => $sport,
            'home' => urlencode($home_team),
            'away' => urlencode($away_team),
            'date' => urlencode(date('Y-m-d', strtotime($game_time)))
        ));
        
        $response = $this->_http_get($url);
        if ($response) {
            $data = json_decode($response, true);
            return isset($data['analysis']) ? $data['analysis'] : null;
        }
        return null;
    }
    
    private function _get_mlb_deep_analysis($home_team, $away_team, $date) {
        $module_file = dirname(__FILE__) . '/mlb_deep_analysis.php';
        if (!file_exists($module_file)) return null;
        
        $url = $this->_build_module_url('mlb_deep_analysis.php', array(
            'action' => 'analyze',
            'home' => urlencode($home_team),
            'away' => urlencode($away_team),
            'date' => $date
        ));
        
        $response = $this->_http_get($url);
        if ($response) {
            $data = json_decode($response, true);
            return isset($data['analysis']) ? $data['analysis'] : null;
        }
        return null;
    }
    
    private function _get_live_odds($game_id, $sport) {
        $module_file = dirname(__FILE__) . '/live_odds_feed.php';
        if (!file_exists($module_file)) return null;
        
        $url = $this->_build_module_url('live_odds_feed.php', array(
            'action' => 'game',
            'game_id' => urlencode($game_id),
            'sport' => $sport
        ));
        
        $response = $this->_http_get($url);
        if ($response) {
            $data = json_decode($response, true);
            return isset($data['odds']) ? $data['odds'] : null;
        }
        return null;
    }
    
    private function _build_module_url($file, $params) {
        $protocol = isset($_SERVER['HTTPS']) ? 'https' : 'http';
        $host = isset($_SERVER['HTTP_HOST']) ? $_SERVER['HTTP_HOST'] : 'localhost';
        $path = dirname($_SERVER['PHP_SELF']) . '/' . $file;
        
        $url = $protocol . '://' . $host . $path;
        if (!empty($params)) {
            $url .= '?' . http_build_query($params);
        }
        return $url;
    }
    
    private function _get_days_games($sport, $date) {
        $table = 'lm_' . $sport . '_schedule';
        $games = array();
        
        $res = $this->conn->query("SELECT * FROM $table WHERE DATE(game_date) = '$date'");
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $games[] = array(
                    'game_id' => $row['game_id'],
                    'home_team' => $row['home_team'],
                    'away_team' => $row['away_team'],
                    'game_time' => $row['game_date']
                );
            }
        }
        return $games;
    }
    
    // ════════════════════════════════════════════════════════════
    //  Analysis & Scoring
    // ════════════════════════════════════════════════════════════
    
    private function _calculate_composite($factors, $sport) {
        $score = 0;
        $weights = array();
        $explanations = array();
        
        // Weather impact (NFL/MLB)
        if (isset($factors['weather']) && !isset($factors['weather']['error'])) {
            $w = $factors['weather'];
            if (isset($w['impact'])) {
                $weather_weight = $sport === 'nfl' ? 2.0 : 1.5;
                $score += $w['impact'] * $weather_weight;
                $weights['weather'] = $w['impact'] * $weather_weight;
                $explanations[] = 'Weather: ' . $w['reason'];
            }
        }
        
        // Travel fatigue
        if (isset($factors['travel']) && !isset($factors['travel']['error'])) {
            $t = $factors['travel'];
            if (isset($t['fatigue_score'])) {
                $travel_impact = $t['fatigue_score'] * 0.5; // Penalizes away team
                $score -= $travel_impact; // Negative impact on away team
                $weights['travel'] = -$travel_impact;
                $explanations[] = 'Travel: ' . $t['fatigue_level'] . ' fatigue for ' . $t['away_team'];
            }
        }
        
        // Altitude
        if (isset($factors['altitude']) && !isset($factors['altitude']['error'])) {
            $a = $factors['altitude'];
            if (isset($a['effect']) && $a['effect'] !== 'minimal') {
                $alt_boost = isset($a['scoring_boost']) ? $a['scoring_boost'] * 10 : 0;
                $score += $alt_boost;
                $weights['altitude'] = $alt_boost;
                $explanations[] = 'Altitude: ' . $a['notes'];
            }
        }
        
        // Officials
        if (isset($factors['officials']) && !isset($factors['officials']['error'])) {
            $o = $factors['officials'];
            if (isset($o['combined_impact']['total_bias_score'])) {
                $bias = $o['combined_impact']['total_bias_score'];
                $score += $bias * 0.5;
                $weights['officials'] = $bias * 0.5;
                $explanations[] = 'Officials: ' . implode(', ', $o['combined_impact']['betting_notes']);
            }
        }
        
        return array(
            'total_score' => round($score, 2),
            'weights' => $weights,
            'explanations' => $explanations,
            'interpretation' => $this->_interpret_composite($score)
        );
    }
    
    private function _interpret_composite($score) {
        if ($score > 5) return 'Strong situational advantage for home team';
        if ($score > 2) return 'Moderate situational advantage for home team';
        if ($score < -5) return 'Strong situational advantage for away team';
        if ($score < -2) return 'Moderate situational advantage for away team';
        return 'Situational factors are balanced';
    }
    
    private function _generate_recommendations($analysis) {
        $recs = array();
        
        $composite = isset($analysis['composite_score']['total_score']) ? $analysis['composite_score']['total_score'] : 0;
        
        // Primary recommendation based on composite
        if ($composite > 3) {
            $recs['primary'] = 'Strong situational edge: Consider HOME team';
        } elseif ($composite < -3) {
            $recs['primary'] = 'Strong situational edge: Consider AWAY team';
        } else {
            $recs['primary'] = 'Situational factors neutral - rely on other analysis';
        }
        
        // Secondary recommendations
        $secondary = array();
        
        if (isset($analysis['factors']['weather'])) {
            $w = $analysis['factors']['weather'];
            if (isset($w['betting_recommendation'])) {
                $secondary[] = $w['betting_recommendation'];
            }
        }
        
        if (isset($analysis['factors']['officials'])) {
            $o = $analysis['factors']['officials'];
            if (isset($o['combined_impact']['betting_notes'])) {
                $secondary = array_merge($secondary, $o['combined_impact']['betting_notes']);
            }
        }
        
        $recs['secondary'] = $secondary;
        
        return $recs;
    }
    
    private function _store_comprehensive_analysis($analysis) {
        $game_id = $this->conn->real_escape_string($analysis['game_id']);
        $sport = $this->conn->real_escape_string($analysis['sport']);
        $home = $this->conn->real_escape_string($analysis['home_team']);
        $away = $this->conn->real_escape_string($analysis['away_team']);
        $composite = $analysis['composite_score']['total_score'];
        $recs = $this->conn->real_escape_string(json_encode($analysis['recommendations']));
        $factors = $this->conn->real_escape_string(json_encode($analysis['factors']));
        
        $query = "INSERT INTO lm_comprehensive_analysis 
                  (game_id, sport, home_team, away_team, composite_score, recommendations, factors, analyzed_at)
                  VALUES ('$game_id', '$sport', '$home', '$away', $composite, '$recs', '$factors', NOW())
                  ON DUPLICATE KEY UPDATE
                  composite_score=VALUES(composite_score), recommendations=VALUES(recommendations),
                  factors=VALUES(factors), analyzed_at=NOW()";
        
        $this->conn->query($query);
    }
    
    private function _load_modules() {
        // Module files are loaded dynamically when needed
    }
    
    private function _http_get($url, $timeout = 15) {
        if (function_exists('curl_init')) {
            $ch = curl_init($url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
            $body = curl_exec($ch);
            curl_close($ch);
            return $body !== false ? $body : null;
        }
        return null;
    }
    
    private function _sort_by_edge_score($a, $b) {
        if ($a['edge_score'] == $b['edge_score']) return 0;
        return ($a['edge_score'] > $b['edge_score']) ? -1 : 1;
    }
    
    private function _ensure_tables() {
        $this->conn->query("CREATE TABLE IF NOT EXISTS lm_comprehensive_analysis (
            id INT AUTO_INCREMENT PRIMARY KEY,
            game_id VARCHAR(50),
            sport VARCHAR(20),
            home_team VARCHAR(100),
            away_team VARCHAR(100),
            composite_score DECIMAL(5,2),
            recommendations TEXT,
            factors TEXT,
            analyzed_at DATETIME DEFAULT NOW(),
            UNIQUE KEY idx_game (game_id),
            INDEX idx_sport_date (sport, analyzed_at)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
    }
}

// API Endpoint
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'analyze';
$integration = new EnhancedIntegration($conn);

if ($action === 'analyze') {
    $sport = isset($_GET['sport']) ? strtolower($_GET['sport']) : '';
    $home = isset($_GET['home']) ? $_GET['home'] : '';
    $away = isset($_GET['away']) ? $_GET['away'] : '';
    $game_id = isset($_GET['game_id']) ? $_GET['game_id'] : null;
    $time = isset($_GET['time']) ? $_GET['time'] : null;
    
    if ($sport && $home && $away) {
        $result = $integration->get_comprehensive_analysis($sport, $home, $away, $game_id, $time);
        echo json_encode(array('ok' => true, 'analysis' => $result));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing required parameters'));
    }
} elseif ($action === 'batch') {
    $games_json = isset($_POST['games']) ? $_POST['games'] : (isset($_GET['games']) ? $_GET['games'] : '');
    $games = json_decode($games_json, true);
    
    if (is_array($games)) {
        $results = $integration->batch_analyze($games);
        echo json_encode(array('ok' => true, 'results' => $results));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Invalid games JSON'));
    }
} elseif ($action === 'edges') {
    $sport = isset($_GET['sport']) ? $_GET['sport'] : '';
    $date = isset($_GET['date']) ? $_GET['date'] : date('Y-m-d');
    
    if ($sport) {
        $edges = $integration->get_situational_edges($sport, $date);
        echo json_encode(array('ok' => true, 'edges' => $edges));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing sport'));
    }
} else {
    echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

$conn->close();
?>
