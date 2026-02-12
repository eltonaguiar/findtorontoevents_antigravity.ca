<?php
/**
 * Data Validation & Cross-Check Module
 * Validates sports data against multiple sources with confidence scoring
 * PHP 5.2 compatible
 * 
 * Philosophy: Never trust a single source. Cross-check everything.
 */

require_once dirname(dirname(__FILE__)) . '/sports_db_connect.php';

class DataValidator {
    private $conn;
    private $validation_log = array();
    private $confidence_threshold = 0.7; // 70% confidence required
    
    // Source reliability scores (0-1, based on historical accuracy)
    private $source_reliability = array(
        'espn_api' => 0.95,
        'espn_html' => 0.90,
        'pro_football_reference' => 0.92,
        'nba_com' => 0.93,
        'nhl_com' => 0.93,
        'mlb_com' => 0.94,
        'sports_reference' => 0.88,
        'yahoo_sports' => 0.85,
        'cbs_sports' => 0.83,
        'fox_sports' => 0.82,
        'bleacher_report' => 0.75,
        'twitter' => 0.60,  // Verify official accounts only
        'reddit' => 0.50    // Crowd-sourced, needs heavy validation
    );
    
    public function __construct($connection) {
        $this->conn = $connection;
        $this->_ensure_tables();
    }
    
    /**
     * Cross-validate game data from multiple sources
     */
    public function validate_game_data($game_id, $sport, $sources_data) {
        $validation = array(
            'game_id' => $game_id,
            'sport' => $sport,
            'timestamp' => gmdate('Y-m-d H:i:s'),
            'fields_validated' => array(),
            'overall_confidence' => 0,
            'warnings' => array(),
            'critical_errors' => array()
        );
        
        // Fields to validate
        $fields = $this->_get_fields_for_sport($sport);
        
        foreach ($fields as $field) {
            $field_validation = $this->_validate_field($field, $sources_data);
            $validation['fields_validated'][$field] = $field_validation;
            
            if ($field_validation['confidence'] < $this->confidence_threshold) {
                $validation['warnings'][] = "Low confidence on $field: " . $field_validation['confidence'];
            }
            
            if ($field_validation['discrepancy'] === 'critical') {
                $validation['critical_errors'][] = "Critical mismatch on $field across sources";
            }
        }
        
        // Calculate overall confidence
        $validation['overall_confidence'] = $this->_calculate_overall_confidence($validation['fields_validated']);
        
        // Determine consensus value for each field
        $validation['consensus'] = $this->_determine_consensus($validation['fields_validated']);
        
        // Store validation result
        $this->_store_validation($validation);
        
        return $validation;
    }
    
    /**
     * Fetch and validate NFL schedule from multiple sources
     */
    public function fetch_validated_nfl_schedule($year, $week) {
        $sources = array();
        
        // Source 1: ESPN API
        $espn = $this->_fetch_espn_nfl_schedule($year, $week);
        if ($espn) $sources['espn_api'] = $espn;
        
        // Source 2: ESPN HTML (backup)
        $espn_html = $this->_fetch_espn_nfl_schedule_html($year, $week);
        if ($espn_html) $sources['espn_html'] = $espn_html;
        
        // Source 3: Pro-Football-Reference (historical accuracy)
        $pfr = $this->_fetch_pfr_schedule($year, $week);
        if ($pfr) $sources['pro_football_reference'] = $pfr;
        
        // Cross-validate all games
        $validated_games = array();
        
        // Get union of all game IDs
        $all_game_ids = array();
        foreach ($sources as $source => $games) {
            foreach ($games as $game) {
                $all_game_ids[$game['game_key']] = true;
            }
        }
        
        foreach (array_keys($all_game_ids) as $game_key) {
            $game_sources = array();
            foreach ($sources as $source => $games) {
                foreach ($games as $game) {
                    if ($game['game_key'] === $game_key) {
                        $game_sources[$source] = $game;
                        break;
                    }
                }
            }
            
            if (count($game_sources) >= 2) {
                $validation = $this->validate_game_data($game_key, 'nfl', $game_sources);
                if ($validation['overall_confidence'] >= $this->confidence_threshold) {
                    $validated_games[] = array(
                        'game_key' => $game_key,
                        'consensus_data' => $validation['consensus'],
                        'confidence' => $validation['overall_confidence'],
                        'sources_used' => array_keys($game_sources)
                    );
                } else {
                    $this->validation_log[] = "Low confidence for $game_key: " . $validation['overall_confidence'];
                }
            } else {
                $this->validation_log[] = "Insufficient sources for $game_key (found " . count($game_sources) . ")";
            }
        }
        
        return array(
            'year' => $year,
            'week' => $week,
            'games_found' => count($validated_games),
            'sources_used' => array_keys($sources),
            'games' => $validated_games,
            'validation_warnings' => $this->validation_log
        );
    }
    
    /**
     * Validate player stats across sources
     */
    public function validate_player_stats($player_name, $sport, $game_date) {
        $sources = array();
        
        if ($sport === 'nfl') {
            $sources['espn'] = $this->_fetch_espn_player_stats($player_name, $game_date);
            $sources['pfr'] = $this->_fetch_pfr_player_stats($player_name, $game_date);
            $sources['yahoo'] = $this->_fetch_yahoo_player_stats($player_name, $game_date);
        }
        
        // Remove null sources
        $sources = array_filter($sources);
        
        if (count($sources) < 2) {
            return array('error' => 'Insufficient sources for validation', 'sources_found' => count($sources));
        }
        
        $validated_stats = array();
        $stat_keys = $this->_get_stat_keys_for_sport($sport);
        
        foreach ($stat_keys as $stat) {
            $values = array();
            foreach ($sources as $source => $data) {
                if (isset($data[$stat])) {
                    $values[$source] = $data[$stat];
                }
            }
            
            if (count($values) >= 2) {
                $validation = $this->_validate_stat_values($stat, $values);
                $validated_stats[$stat] = $validation;
            }
        }
        
        return array(
            'player' => $player_name,
            'sport' => $sport,
            'date' => $game_date,
            'sources_used' => array_keys($sources),
            'validated_stats' => $validated_stats,
            'overall_confidence' => $this->_calculate_stat_confidence($validated_stats)
        );
    }
    
    /**
     * Detect and flag suspicious data anomalies
     */
    public function detect_anomalies($data, $sport) {
        $anomalies = array();
        
        // Historical baselines for anomaly detection
        $baselines = $this->_get_historical_baselines($sport);
        
        foreach ($data as $game) {
            $game_anomalies = array();
            
            // Check for extreme scores
            if (isset($game['home_score']) && isset($game['away_score'])) {
                $total = $game['home_score'] + $game['away_score'];
                $spread = abs($game['home_score'] - $game['away_score']);
                
                if ($total > $baselines['max_total'] * 1.5) {
                    $game_anomalies[] = "Unusually high total score: $total";
                }
                if ($spread > $baselines['max_spread'] * 1.5) {
                    $game_anomalies[] = "Blowout alert: $spread point margin";
                }
            }
            
            // Check for impossible stats
            if (isset($game['passing_yards']) && $game['passing_yards'] > 600) {
                $game_anomalies[] = "Suspicious passing yards: {$game['passing_yards']}";
            }
            
            // Check for data entry errors (negative values where not allowed)
            if (isset($game['time_of_possession']) && $game['time_of_possession'] < 0) {
                $game_anomalies[] = "Invalid time of possession";
            }
            
            if (!empty($game_anomalies)) {
                $anomalies[$game['game_id']] = $game_anomalies;
            }
        }
        
        return $anomalies;
    }
    
    /**
     * Get validation report for a date range
     */
    public function get_validation_report($sport, $start_date, $end_date) {
        $esc_sport = $this->conn->real_escape_string($sport);
        $esc_start = $this->conn->real_escape_string($start_date);
        $esc_end = $this->conn->real_escape_string($end_date);
        
        $query = "SELECT 
                    COUNT(*) as total_validations,
                    AVG(overall_confidence) as avg_confidence,
                    SUM(CASE WHEN overall_confidence >= 0.9 THEN 1 ELSE 0 END) as high_confidence,
                    SUM(CASE WHEN overall_confidence < 0.7 THEN 1 ELSE 0 END) as low_confidence,
                    COUNT(DISTINCT CASE WHEN critical_errors != '[]' THEN game_id END) as games_with_errors
                  FROM lm_data_validation 
                  WHERE sport='$esc_sport' 
                  AND validation_date BETWEEN '$esc_start' AND '$esc_end'";
        
        $res = $this->conn->query($query);
        if ($res && $row = $res->fetch_assoc()) {
            return array(
                'sport' => $sport,
                'date_range' => "$start_date to $end_date",
                'total_validations' => (int)$row['total_validations'],
                'average_confidence' => round((float)$row['avg_confidence'], 3),
                'high_confidence_rate' => $row['total_validations'] > 0 ? round($row['high_confidence'] / $row['total_validations'], 3) : 0,
                'low_confidence_count' => (int)$row['low_confidence'],
                'games_with_critical_errors' => (int)$row['games_with_errors']
            );
        }
        
        return null;
    }
    
    // ════════════════════════════════════════════════════════════
    //  Private Validation Methods
    // ════════════════════════════════════════════════════════════
    
    private function _validate_field($field, $sources_data) {
        $values = array();
        $source_names = array();
        
        foreach ($sources_data as $source => $data) {
            if (isset($data[$field])) {
                $values[$source] = $data[$field];
                $source_names[] = $source;
            }
        }
        
        if (count($values) < 2) {
            return array(
                'field' => $field,
                'confidence' => count($values) === 1 ? 0.5 : 0,
                'discrepancy' => count($values) === 0 ? 'missing' : 'single_source',
                'values' => $values,
                'consensus' => count($values) === 1 ? reset($values) : null
            );
        }
        
        // Check for exact matches
        $unique_values = array_unique(array_map('strval', $values));
        
        if (count($unique_values) === 1) {
            // All sources agree
            return array(
                'field' => $field,
                'confidence' => 0.98,
                'discrepancy' => 'none',
                'values' => $values,
                'consensus' => reset($values)
            );
        }
        
        // Check for numeric tolerance (e.g., 21.5 vs 21.3)
        if (is_numeric(reset($values))) {
            return $this->_validate_numeric_field($field, $values);
        }
        
        // String fields - check for similarity
        return $this->_validate_string_field($field, $values);
    }
    
    private function _validate_numeric_field($field, $values) {
        $numeric_values = array_map('floatval', $values);
        $mean = array_sum($numeric_values) / count($numeric_values);
        $variance = 0;
        
        foreach ($numeric_values as $v) {
            $variance += pow($v - $mean, 2);
        }
        $std_dev = sqrt($variance / count($numeric_values));
        
        // Coefficient of variation
        $cv = $mean != 0 ? $std_dev / abs($mean) : 0;
        
        // Determine consensus (weighted by source reliability)
        $weighted_sum = 0;
        $total_weight = 0;
        
        foreach ($values as $source => $value) {
            $weight = isset($this->source_reliability[$source]) ? $this->source_reliability[$source] : 0.5;
            $weighted_sum += floatval($value) * $weight;
            $total_weight += $weight;
        }
        
        $consensus = $total_weight > 0 ? $weighted_sum / $total_weight : $mean;
        
        // Confidence based on agreement
        if ($cv < 0.01) { // < 1% variation
            $confidence = 0.95;
            $discrepancy = 'minor';
        } elseif ($cv < 0.05) { // < 5% variation
            $confidence = 0.85;
            $discrepancy = 'minor';
        } elseif ($cv < 0.15) { // < 15% variation
            $confidence = 0.70;
            $discrepancy = 'moderate';
        } else {
            $confidence = 0.50;
            $discrepancy = 'critical';
        }
        
        return array(
            'field' => $field,
            'confidence' => $confidence,
            'discrepancy' => $discrepancy,
            'values' => $values,
            'consensus' => round($consensus, 2),
            'std_deviation' => round($std_dev, 3),
            'cv' => round($cv, 3)
        );
    }
    
    private function _validate_string_field($field, $values) {
        // For strings, use most common value
        $counts = array_count_values(array_map('strtolower', $values));
        arsort($counts);
        
        $most_common = key($counts);
        $agreement_rate = reset($counts) / count($values);
        
        // Weight by source reliability
        $weighted_votes = array();
        foreach ($values as $source => $value) {
            $weight = isset($this->source_reliability[$source]) ? $this->source_reliability[$source] : 0.5;
            $key = strtolower($value);
            if (!isset($weighted_votes[$key])) {
                $weighted_votes[$key] = 0;
            }
            $weighted_votes[$key] += $weight;
        }
        
        arsort($weighted_votes);
        $consensus_key = key($weighted_votes);
        
        // Find original case for consensus
        $consensus = $most_common;
        foreach ($values as $value) {
            if (strtolower($value) === $consensus_key) {
                $consensus = $value;
                break;
            }
        }
        
        $total_weight = array_sum($weighted_votes);
        $confidence = $total_weight > 0 ? reset($weighted_votes) / $total_weight : $agreement_rate;
        
        return array(
            'field' => $field,
            'confidence' => round($confidence, 2),
            'discrepancy' => $confidence > 0.8 ? 'none' : ($confidence > 0.6 ? 'minor' : 'moderate'),
            'values' => $values,
            'consensus' => $consensus,
            'agreement_rate' => round($agreement_rate, 2)
        );
    }
    
    private function _calculate_overall_confidence($fields_validated) {
        if (empty($fields_validated)) return 0;
        
        $total_confidence = 0;
        $total_weight = 0;
        
        // Weight critical fields more heavily
        $field_weights = array(
            'home_score' => 2.0,
            'away_score' => 2.0,
            'game_date' => 3.0,
            'home_team' => 2.5,
            'away_team' => 2.5,
            'winner' => 1.5,
            'spread' => 1.0,
            'total' => 1.0
        );
        
        foreach ($fields_validated as $field => $validation) {
            $weight = isset($field_weights[$field]) ? $field_weights[$field] : 1.0;
            $total_confidence += $validation['confidence'] * $weight;
            $total_weight += $weight;
        }
        
        return $total_weight > 0 ? round($total_confidence / $total_weight, 3) : 0;
    }
    
    private function _determine_consensus($fields_validated) {
        $consensus = array();
        foreach ($fields_validated as $field => $validation) {
            if (isset($validation['consensus'])) {
                $consensus[$field] = $validation['consensus'];
            }
        }
        return $consensus;
    }
    
    private function _validate_stat_values($stat, $values) {
        // Similar to _validate_numeric_field but for player stats
        return $this->_validate_numeric_field($stat, $values);
    }
    
    private function _calculate_stat_confidence($validated_stats) {
        if (empty($validated_stats)) return 0;
        
        $sum = 0;
        foreach ($validated_stats as $stat) {
            $sum += $stat['confidence'];
        }
        
        return round($sum / count($validated_stats), 3);
    }
    
    private function _get_fields_for_sport($sport) {
        $common = array('game_date', 'home_team', 'away_team', 'home_score', 'away_score');
        
        switch ($sport) {
            case 'nfl':
                return array_merge($common, array('spread', 'total', 'winner', 'overtime'));
            case 'nba':
                return array_merge($common, array('spread', 'total', 'winner', 'quarters'));
            case 'nhl':
                return array_merge($common, array('puck_line', 'total', 'winner', 'overtime', 'shootout'));
            case 'mlb':
                return array_merge($common, array('run_line', 'total', 'winner', 'innings'));
            default:
                return $common;
        }
    }
    
    private function _get_stat_keys_for_sport($sport) {
        switch ($sport) {
            case 'nfl':
                return array('passing_yards', 'rushing_yards', 'receptions', 'touchdowns', 'interceptions');
            case 'nba':
                return array('points', 'rebounds', 'assists', 'steals', 'blocks', 'turnovers');
            case 'nhl':
                return array('goals', 'assists', 'saves', 'shots', 'plus_minus');
            case 'mlb':
                return array('at_bats', 'hits', 'home_runs', 'rbis', 'strikeouts', 'walks');
            default:
                return array();
        }
    }
    
    private function _get_historical_baselines($sport) {
        // Historical averages for anomaly detection
        $baselines = array(
            'nfl' => array('max_total' => 75, 'max_spread' => 35, 'avg_total' => 45),
            'nba' => array('max_total' => 280, 'max_spread' => 50, 'avg_total' => 220),
            'nhl' => array('max_total' => 12, 'max_spread' => 8, 'avg_total' => 6),
            'mlb' => array('max_total' => 20, 'max_spread' => 15, 'avg_total' => 9)
        );
        
        return isset($baselines[$sport]) ? $baselines[$sport] : $baselines['nfl'];
    }
    
    // ════════════════════════════════════════════════════════════
    //  Data Fetching Methods
    // ════════════════════════════════════════════════════════════
    
    private function _fetch_espn_nfl_schedule($year, $week) {
        $url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=$year&seasontype=2&week=$week";
        $body = $this->_http_get($url);
        
        if (!$body) return null;
        
        $data = json_decode($body, true);
        if (!$data || !isset($data['events'])) return null;
        
        $games = array();
        foreach ($data['events'] as $event) {
            $game = $this->_parse_espn_game($event, 'nfl');
            if ($game) $games[] = $game;
        }
        
        return $games;
    }
    
    private function _fetch_espn_nfl_schedule_html($year, $week) {
        // Backup HTML scraping
        $url = "https://www.espn.com/nfl/schedule/_/year/$year/week/$week";
        $body = $this->_http_get($url);
        
        if (!$body) return null;
        
        // Parse HTML schedule table
        $games = array();
        // Simplified parsing - would need full implementation
        
        return $games;
    }
    
    private function _fetch_pfr_schedule($year, $week) {
        // Pro-Football-Reference schedule
        $url = "https://www.pro-football-reference.com/years/$year/games.htm";
        $body = $this->_http_get($url);
        
        if (!$body) return null;
        
        // Parse PFR table
        $games = array();
        
        // Look for game rows
        preg_match_all('/<tr >.*?<td[^>]*>(.*?)<\/td>.*?<td[^>]*>(.*?)<\/td>.*?<td[^>]*>(.*?)<\/td>.*?<td[^>]*>(.*?)<\/td>.*?<\/tr>/s', $body, $matches, PREG_SET_ORDER);
        
        foreach ($matches as $match) {
            // Parse week number
            $week_num = trim(strip_tags($match[1]));
            if ($week_num == $week) {
                $games[] = array(
                    'game_key' => $year . '_' . $week . '_' . $this->_normalize_team_name(trim(strip_tags($match[3]))) . '_' . $this->_normalize_team_name(trim(strip_tags($match[4]))),
                    'week' => $week_num,
                    'day' => trim(strip_tags($match[2])),
                    'away_team' => trim(strip_tags($match[3])),
                    'home_team' => trim(strip_tags($match[4]))
                );
            }
        }
        
        return $games;
    }
    
    private function _fetch_espn_player_stats($player, $date) {
        // Would implement ESPN player stats API
        return null;
    }
    
    private function _fetch_pfr_player_stats($player, $date) {
        // Would implement PFR player stats
        return null;
    }
    
    private function _fetch_yahoo_player_stats($player, $date) {
        // Would implement Yahoo stats
        return null;
    }
    
    private function _parse_espn_game($event, $sport) {
        if (!isset($event['competitions'])) return null;
        
        $comp = $event['competitions'][0];
        $home_team = '';
        $away_team = '';
        $home_score = null;
        $away_score = null;
        
        foreach ($comp['competitors'] as $team) {
            $name = isset($team['team']['displayName']) ? $team['team']['displayName'] : '';
            if (isset($team['homeAway']) && $team['homeAway'] === 'home') {
                $home_team = $name;
                $home_score = isset($team['score']) ? $team['score'] : null;
            } else {
                $away_team = $name;
                $away_score = isset($team['score']) ? $team['score'] : null;
            }
        }
        
        return array(
            'game_key' => isset($event['id']) ? $event['id'] : md5($home_team . $away_team . $event['date']),
            'game_date' => isset($event['date']) ? $event['date'] : '',
            'home_team' => $home_team,
            'away_team' => $away_team,
            'home_score' => $home_score,
            'away_score' => $away_score,
            'status' => isset($comp['status']['type']['description']) ? $comp['status']['type']['description'] : ''
        );
    }
    
    private function _normalize_team_name($name) {
        return strtolower(preg_replace('/[^a-zA-Z0-9]/', '', $name));
    }
    
    private function _http_get($url, $timeout = 15) {
        if (function_exists('curl_init')) {
            $ch = curl_init($url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
            curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (DataValidator/1.0)');
            $body = curl_exec($ch);
            curl_close($ch);
            return $body !== false ? $body : null;
        }
        return null;
    }
    
    private function _store_validation($validation) {
        $game_id = $this->conn->real_escape_string($validation['game_id']);
        $sport = $this->conn->real_escape_string($validation['sport']);
        $confidence = $validation['overall_confidence'];
        $fields = $this->conn->real_escape_string(json_encode($validation['fields_validated']));
        $warnings = $this->conn->real_escape_string(json_encode($validation['warnings']));
        $errors = $this->conn->real_escape_string(json_encode($validation['critical_errors']));
        
        $query = "INSERT INTO lm_data_validation 
                  (game_id, sport, overall_confidence, fields_validated, warnings, critical_errors, validation_date)
                  VALUES ('$game_id', '$sport', $confidence, '$fields', '$warnings', '$errors', CURDATE())
                  ON DUPLICATE KEY UPDATE
                  overall_confidence=VALUES(overall_confidence), fields_validated=VALUES(fields_validated),
                  warnings=VALUES(warnings), critical_errors=VALUES(critical_errors), validation_date=VALUES(validation_date)";
        
        $this->conn->query($query);
    }
    
    private function _ensure_tables() {
        $this->conn->query("CREATE TABLE IF NOT EXISTS lm_data_validation (
            id INT AUTO_INCREMENT PRIMARY KEY,
            game_id VARCHAR(100),
            sport VARCHAR(20),
            overall_confidence DECIMAL(4,3),
            fields_validated TEXT,
            warnings TEXT,
            critical_errors TEXT,
            validation_date DATE,
            INDEX idx_game (game_id),
            INDEX idx_sport_date (sport, validation_date)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
    }
}

// API Endpoint
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'validate';
$validator = new DataValidator($conn);

if ($action === 'validate') {
    $game_id = isset($_GET['game_id']) ? $_GET['game_id'] : '';
    $sport = isset($_GET['sport']) ? $_GET['sport'] : '';
    $data_json = isset($_POST['data']) ? $_POST['data'] : (isset($_GET['data']) ? $_GET['data'] : '');
    $data = json_decode($data_json, true);
    
    if ($game_id && $sport && is_array($data)) {
        $result = $validator->validate_game_data($game_id, $sport, $data);
        echo json_encode(array('ok' => true, 'validation' => $result));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing parameters'));
    }
} elseif ($action === 'nfl_schedule') {
    $year = isset($_GET['year']) ? (int)$_GET['year'] : date('Y');
    $week = isset($_GET['week']) ? (int)$_GET['week'] : 1;
    $result = $validator->fetch_validated_nfl_schedule($year, $week);
    echo json_encode(array('ok' => true, 'schedule' => $result));
} elseif ($action === 'player_stats') {
    $player = isset($_GET['player']) ? $_GET['player'] : '';
    $sport = isset($_GET['sport']) ? $_GET['sport'] : '';
    $date = isset($_GET['date']) ? $_GET['date'] : date('Y-m-d');
    if ($player && $sport) {
        $result = $validator->validate_player_stats($player, $sport, $date);
        echo json_encode(array('ok' => true, 'validation' => $result));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing player or sport'));
    }
} elseif ($action === 'anomalies') {
    $data_json = isset($_POST['data']) ? $_POST['data'] : '';
    $sport = isset($_GET['sport']) ? $_GET['sport'] : 'nfl';
    $data = json_decode($data_json, true);
    if (is_array($data)) {
        $anomalies = $validator->detect_anomalies($data, $sport);
        echo json_encode(array('ok' => true, 'anomalies' => $anomalies));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Invalid data'));
    }
} elseif ($action === 'report') {
    $sport = isset($_GET['sport']) ? $_GET['sport'] : '';
    $start = isset($_GET['start']) ? $_GET['start'] : date('Y-m-d', strtotime('-7 days'));
    $end = isset($_GET['end']) ? $_GET['end'] : date('Y-m-d');
    if ($sport) {
        $report = $validator->get_validation_report($sport, $start, $end);
        echo json_encode(array('ok' => true, 'report' => $report));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing sport'));
    }
} else {
    echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

$conn->close();
?>
