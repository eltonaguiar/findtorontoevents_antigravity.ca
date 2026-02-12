<?php
/**
 * Live Betting Odds Feed Scraper
 * Real-time odds scanning for in-game betting
 * PHP 5.2 compatible
 */

require_once dirname(dirname(__FILE__)) . '/sports_db_connect.php';

class LiveOddsFeed {
    private $conn;
    private $errors = array();
    private $sources = array();
    
    public function __construct($connection) {
        $this->conn = $connection;
        $this->_ensure_tables();
        $this->_init_sources();
    }
    
    /**
     * Scan all sources for live odds
     */
    public function scan_live_odds($sport = null) {
        $results = array();
        
        $sports = $sport ? array($sport) : array('nba', 'nhl', 'nfl', 'mlb');
        
        foreach ($sports as $s) {
            $sport_odds = array();
            
            // Try each source
            foreach ($this->sources as $source_name => $source_config) {
                if ($source_config['type'] === 'websocket') continue; // Skip WS for now
                
                $odds = $this->_fetch_from_source($source_name, $s);
                if ($odds) {
                    $sport_odds[$source_name] = $odds;
                }
            }
            
            $results[$s] = $sport_odds;
            
            // Store in database
            $this->_store_live_odds($s, $sport_odds);
        }
        
        return array(
            'timestamp' => gmdate('Y-m-d H:i:s'),
            'sports' => $results
        );
    }
    
    /**
     * Get live odds for a specific game
     */
    public function get_game_live_odds($game_id, $sport) {
        $esc_game = $this->conn->real_escape_string($game_id);
        $esc_sport = $this->conn->real_escape_string($sport);
        
        $query = "SELECT * FROM lm_live_odds WHERE game_id='$esc_game' AND sport='$esc_sport' 
                  AND recorded_at > DATE_SUB(NOW(), INTERVAL 5 MINUTE)
                  ORDER BY recorded_at DESC LIMIT 1";
        
        $res = $this->conn->query($query);
        if ($res && $row = $res->fetch_assoc()) {
            return array(
                'game_id' => $row['game_id'],
                'sport' => $row['sport'],
                'odds' => json_decode($row['odds_data'], true),
                'recorded_at' => $row['recorded_at']
            );
        }
        
        return null;
    }
    
    /**
     * Get line movements for a game
     */
    public function get_line_movement($game_id, $hours = 24) {
        $esc_game = $this->conn->real_escape_string($game_id);
        $hours = (int)$hours;
        
        $query = "SELECT * FROM lm_line_movement 
                  WHERE game_id='$esc_game' 
                  AND recorded_at > DATE_SUB(NOW(), INTERVAL $hours HOUR)
                  ORDER BY recorded_at ASC";
        
        $res = $this->conn->query($query);
        $movements = array();
        
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $movements[] = array(
                    'spread' => $row['spread'],
                    'total' => $row['total'],
                    'home_ml' => $row['home_ml'],
                    'away_ml' => $row['away_ml'],
                    'recorded_at' => $row['recorded_at']
                );
            }
        }
        
        return $movements;
    }
    
    /**
     * Detect sharp line movements
     */
    public function detect_sharp_moves($sport = null, $minutes = 30) {
        $movements = array();
        $esc_sport = $sport ? "AND sport='" . $this->conn->real_escape_string($sport) . "'" : '';
        $minutes = (int)$minutes;
        
        // Find games with significant line movement
        $query = "SELECT game_id, sport, bookmaker,
                  MIN(CAST(spread AS DECIMAL(5,1))) as min_spread,
                  MAX(CAST(spread AS DECIMAL(5,1))) as max_spread,
                  COUNT(*) as updates
                  FROM lm_line_movement 
                  WHERE recorded_at > DATE_SUB(NOW(), INTERVAL $minutes MINUTE)
                  $esc_sport
                  GROUP BY game_id, bookmaker
                  HAVING ABS(max_spread - min_spread) > 1.0";
        
        $res = $this->conn->query($query);
        
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $spread_move = abs($row['max_spread'] - $row['min_spread']);
                if ($spread_move >= 1.0) {
                    $movements[] = array(
                        'game_id' => $row['game_id'],
                        'sport' => $row['sport'],
                        'bookmaker' => $row['bookmaker'],
                        'spread_movement' => $spread_move,
                        'direction' => $row['max_spread'] > $row['min_spread'] ? 'toward_home' : 'toward_away',
                        'sharp_indicator' => $spread_move >= 2.0 ? 'high' : 'moderate'
                    );
                }
            }
        }
        
        return $movements;
    }
    
    /**
     * Compare odds across bookmakers (arbitrage detection)
     */
    public function find_arbitrage_opportunities($sport = null) {
        $opportunities = array();
        $esc_sport = $sport ? "WHERE sport='" . $this->conn->real_escape_string($sport) . "'" : '';
        
        // Find best lines across books
        $query = "SELECT game_id, sport,
                  MIN(CAST(home_ml AS DECIMAL(5,0))) as best_home_ml,
                  MIN(CAST(away_ml AS DECIMAL(5,0))) as best_away_ml,
                  MAX(CAST(home_ml AS DECIMAL(5,0))) as worst_home_ml,
                  MAX(CAST(away_ml AS DECIMAL(5,0))) as worst_away_ml
                  FROM lm_live_odds 
                  $esc_sport
                  AND recorded_at > DATE_SUB(NOW(), INTERVAL 5 MINUTE)
                  GROUP BY game_id, sport";
        
        $res = $this->conn->query($query);
        
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $home_ml = $row['best_home_ml'];
                $away_ml = $row['best_away_ml'];
                
                // Calculate no-vig implied probability
                if ($home_ml > 0) {
                    $home_prob = 100 / ($home_ml + 100);
                } else {
                    $home_prob = abs($home_ml) / (abs($home_ml) + 100);
                }
                
                if ($away_ml > 0) {
                    $away_prob = 100 / ($away_ml + 100);
                } else {
                    $away_prob = abs($away_ml) / (abs($away_ml) + 100);
                }
                
                $total_prob = $home_prob + $away_prob;
                
                // If total < 1, there's potential arbitrage
                if ($total_prob < 0.98) {
                    $opportunities[] = array(
                        'game_id' => $row['game_id'],
                        'sport' => $row['sport'],
                        'home_ml' => $home_ml,
                        'away_ml' => $away_ml,
                        'total_implied_prob' => round($total_prob * 100, 2) . '%',
                        'arb_profit' => round((1 - $total_prob) * 100, 2) . '%',
                        'type' => 'moneyline_arb'
                    );
                }
            }
        }
        
        return $opportunities;
    }
    
    // ════════════════════════════════════════════════════════════
    //  Private Methods
    // ════════════════════════════════════════════════════════════
    
    private function _init_sources() {
        $this->sources = array(
            'pinnacle' => array(
                'type' => 'api',
                'url' => 'https://api.pinnacle.com/v1/odds',
                'weight' => 1.0 // Sharpest book
            ),
            'betonline' => array(
                'type' => 'scrape',
                'url' => 'https://www.betonline.ag/sportsbook',
                'weight' => 0.9
            ),
            'bookmaker' => array(
                'type' => 'api',
                'weight' => 0.95
            ),
            'circa' => array(
                'type' => 'scrape',
                'weight' => 0.95
            ),
            'cris' => array(
                'type' => 'api',
                'weight' => 0.9
            )
        );
    }
    
    private function _fetch_from_source($source, $sport) {
        // Simulated for now - would implement actual scraping
        return null;
    }
    
    private function _store_live_odds($sport, $odds_data) {
        if (empty($odds_data)) return;
        
        foreach ($odds_data as $source => $games) {
            if (!is_array($games)) continue;
            
            foreach ($games as $game) {
                if (!isset($game['game_id'])) continue;
                
                $game_id = $this->conn->real_escape_string($game['game_id']);
                $sport_esc = $this->conn->real_escape_string($sport);
                $source_esc = $this->conn->real_escape_string($source);
                $odds_json = $this->conn->real_escape_string(json_encode($game));
                
                // Store in live odds
                $query = "INSERT INTO lm_live_odds (game_id, sport, source, odds_data, recorded_at)
                          VALUES ('$game_id', '$sport_esc', '$source_esc', '$odds_json', NOW())
                          ON DUPLICATE KEY UPDATE odds_data=VALUES(odds_data), recorded_at=NOW()";
                $this->conn->query($query);
                
                // Also track line movement
                $this->_track_line_movement($game, $sport, $source);
            }
        }
    }
    
    private function _track_line_movement($game, $sport, $source) {
        if (!isset($game['game_id'])) return;
        
        $game_id = $this->conn->real_escape_string($game['game_id']);
        $sport_esc = $this->conn->real_escape_string($sport);
        $source_esc = $this->conn->real_escape_string($source);
        
        $spread = isset($game['spread']) ? $this->conn->real_escape_string($game['spread']) : '';
        $total = isset($game['total']) ? $this->conn->real_escape_string($game['total']) : '';
        $home_ml = isset($game['home_ml']) ? $this->conn->real_escape_string($game['home_ml']) : '';
        $away_ml = isset($game['away_ml']) ? $this->conn->real_escape_string($game['away_ml']) : '';
        
        // Check if line has changed from last record
        $check = $this->conn->query("SELECT * FROM lm_line_movement 
                                     WHERE game_id='$game_id' AND bookmaker='$source_esc' 
                                     ORDER BY recorded_at DESC LIMIT 1");
        
        $should_insert = true;
        if ($check && $row = $check->fetch_assoc()) {
            if ($row['spread'] === $spread && $row['total'] === $total) {
                $should_insert = false; // No change
            }
        }
        
        if ($should_insert) {
            $query = "INSERT INTO lm_line_movement (game_id, sport, bookmaker, spread, total, home_ml, away_ml, recorded_at)
                      VALUES ('$game_id', '$sport_esc', '$source_esc', '$spread', '$total', '$home_ml', '$away_ml', NOW())";
            $this->conn->query($query);
        }
    }
    
    private function _ensure_tables() {
        $this->conn->query("CREATE TABLE IF NOT EXISTS lm_live_odds (
            id INT AUTO_INCREMENT PRIMARY KEY,
            game_id VARCHAR(50),
            sport VARCHAR(20),
            source VARCHAR(50),
            odds_data TEXT,
            recorded_at DATETIME DEFAULT NOW(),
            INDEX idx_game (game_id),
            INDEX idx_sport (sport),
            INDEX idx_time (recorded_at)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
        
        $this->conn->query("CREATE TABLE IF NOT EXISTS lm_line_movement (
            id INT AUTO_INCREMENT PRIMARY KEY,
            game_id VARCHAR(50),
            sport VARCHAR(20),
            bookmaker VARCHAR(50),
            spread VARCHAR(20),
            total VARCHAR(20),
            home_ml VARCHAR(10),
            away_ml VARCHAR(10),
            recorded_at DATETIME DEFAULT NOW(),
            INDEX idx_game (game_id),
            INDEX idx_time (recorded_at)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
    }
}

// API Endpoint
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'scan';
$feed = new LiveOddsFeed($conn);

if ($action === 'scan') {
    $sport = isset($_GET['sport']) ? strtolower($_GET['sport']) : null;
    $results = $feed->scan_live_odds($sport);
    echo json_encode(array('ok' => true, 'results' => $results));
} elseif ($action === 'game') {
    $game_id = isset($_GET['game_id']) ? $_GET['game_id'] : '';
    $sport = isset($_GET['sport']) ? $_GET['sport'] : '';
    if ($game_id && $sport) {
        $odds = $feed->get_game_live_odds($game_id, $sport);
        echo json_encode(array('ok' => true, 'odds' => $odds));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing game_id or sport'));
    }
} elseif ($action === 'movement') {
    $game_id = isset($_GET['game_id']) ? $_GET['game_id'] : '';
    $hours = isset($_GET['hours']) ? (int)$_GET['hours'] : 24;
    if ($game_id) {
        $movements = $feed->get_line_movement($game_id, $hours);
        echo json_encode(array('ok' => true, 'movements' => $movements));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing game_id'));
    }
} elseif ($action === 'sharp') {
    $sport = isset($_GET['sport']) ? $_GET['sport'] : null;
    $minutes = isset($_GET['minutes']) ? (int)$_GET['minutes'] : 30;
    $moves = $feed->detect_sharp_moves($sport, $minutes);
    echo json_encode(array('ok' => true, 'sharp_moves' => $moves));
} elseif ($action === 'arb') {
    $sport = isset($_GET['sport']) ? $_GET['sport'] : null;
    $arbs = $feed->find_arbitrage_opportunities($sport);
    echo json_encode(array('ok' => true, 'arbitrage' => $arbs));
} else {
    echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

$conn->close();
?>
