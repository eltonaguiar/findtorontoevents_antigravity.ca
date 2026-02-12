<?php
/**
 * Sports Betting Database Verification Tool
 * Checks schema integrity, data consistency, and table relationships
 * PHP 5.2 compatible
 */

require_once dirname(dirname(__FILE__)) . '/sports_db_connect.php';

class DatabaseVerifier {
    private $conn;
    private $errors = array();
    private $warnings = array();
    private $info = array();
    
    // Expected tables and their required columns
    private $expected_schema = array(
        'lm_sports_odds' => array(
            'required' => array('id', 'sport', 'game_date', 'home_team', 'away_team', 'bookmaker', 'created_at'),
            'indexes' => array('sport', 'game_date')
        ),
        'sports_bets' => array(
            'required' => array('id', 'sport', 'bet_type', 'stake', 'odds', 'ev_percent', 'status', 'created_at'),
            'indexes' => array('sport', 'status', 'created_at')
        ),
        'lm_nba_odds' => array(
            'required' => array('id', 'game_date', 'home_team', 'away_team', 'spread', 'bookmaker', 'recorded_at'),
            'indexes' => array('game_date', 'home_team', 'away_team')
        ),
        'lm_nhl_odds' => array(
            'required' => array('id', 'game_date', 'home_team', 'away_team', 'puck_line', 'bookmaker', 'recorded_at'),
            'indexes' => array('game_date', 'home_team', 'away_team')
        ),
        'lm_nfl_odds' => array(
            'required' => array('id', 'game_date', 'home_team', 'away_team', 'spread', 'bookmaker', 'recorded_at'),
            'indexes' => array('game_date', 'home_team', 'away_team')
        ),
        'lm_mlb_odds' => array(
            'required' => array('id', 'game_date', 'home_team', 'away_team', 'run_line', 'bookmaker', 'recorded_at'),
            'indexes' => array('game_date', 'home_team', 'away_team')
        ),
        'lm_weather_data' => array(
            'required' => array('id', 'game_id', 'sport', 'temperature', 'wind_speed', 'impact_score', 'recorded_at'),
            'indexes' => array('game_id', 'sport')
        ),
        'lm_travel_analysis' => array(
            'required' => array('id', 'game_id', 'away_team', 'home_team', 'fatigue_score', 'analyzed_at'),
            'indexes' => array('game_id', 'away_team', 'home_team')
        ),
        'lm_mlb_analysis' => array(
            'required' => array('id', 'game_id', 'home_team', 'away_team', 'home_pitcher', 'away_pitcher', 'analyzed_at'),
            'indexes' => array('game_id', 'game_date')
        ),
        'lm_data_validation' => array(
            'required' => array('id', 'game_id', 'sport', 'overall_confidence', 'validation_date'),
            'indexes' => array('game_id', 'sport', 'validation_date')
        ),
        'lm_referee_stats' => array(
            'required' => array('id', 'sport', 'name', 'games_called', 'last_updated'),
            'indexes' => array('sport', 'name')
        ),
        'lm_live_odds' => array(
            'required' => array('id', 'game_id', 'sport', 'source', 'odds_data', 'recorded_at'),
            'indexes' => array('game_id', 'sport', 'source')
        ),
        'lm_line_movement' => array(
            'required' => array('id', 'game_id', 'sport', 'bookmaker', 'spread', 'total', 'recorded_at'),
            'indexes' => array('game_id', 'recorded_at')
        ),
        'lm_cron_log' => array(
            'required' => array('id', 'mode', 'sports', 'success_count', 'total_count', 'run_at'),
            'indexes' => array('run_at')
        ),
        'lm_scraper_log' => array(
            'required' => array('id', 'sports', 'results', 'run_at'),
            'indexes' => array('run_at')
        )
    );
    
    public function __construct($connection) {
        $this->conn = $connection;
    }
    
    /**
     * Run full database verification
     */
    public function verify_all() {
        $report = array(
            'timestamp' => gmdate('Y-m-d H:i:s'),
            'database' => $this->_get_database_name(),
            'checks' => array()
        );
        
        // 1. Check table existence
        $report['checks']['tables'] = $this->_verify_tables();
        
        // 2. Check column integrity
        $report['checks']['columns'] = $this->_verify_columns();
        
        // 3. Check index integrity
        $report['checks']['indexes'] = $this->_verify_indexes();
        
        // 4. Check data consistency
        $report['checks']['data'] = $this->_verify_data_consistency();
        
        // 5. Check for orphan records
        $report['checks']['orphans'] = $this->_check_orphan_records();
        
        // 6. Check for duplicates
        $report['checks']['duplicates'] = $this->_check_duplicates();
        
        // 7. Verify foreign key relationships
        $report['checks']['relationships'] = $this->_verify_relationships();
        
        // 8. Check for stale data
        $report['checks']['staleness'] = $this->_check_stale_data();
        
        // Summary
        $report['summary'] = $this->_generate_summary($report['checks']);
        
        return $report;
    }
    
    /**
     * Verify specific table
     */
    public function verify_table($table_name) {
        $result = array(
            'table' => $table_name,
            'exists' => false,
            'columns' => array(),
            'row_count' => 0,
            'size_mb' => 0,
            'last_update' => null
        );
        
        $esc_table = $this->conn->real_escape_string($table_name);
        
        // Check existence
        $res = $this->conn->query("SHOW TABLES LIKE '$esc_table'");
        if (!$res || $res->num_rows === 0) {
            return $result;
        }
        $result['exists'] = true;
        
        // Get columns
        $res = $this->conn->query("SHOW COLUMNS FROM $esc_table");
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $result['columns'][] = $row['Field'];
            }
        }
        
        // Get row count
        $res = $this->conn->query("SELECT COUNT(*) as count FROM $esc_table");
        if ($res && $row = $res->fetch_assoc()) {
            $result['row_count'] = (int)$row['count'];
        }
        
        // Get table size
        $res = $this->conn->query("SELECT 
            ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb 
            FROM information_schema.TABLES 
            WHERE table_schema = DATABASE() 
            AND table_name = '$esc_table'");
        if ($res && $row = $res->fetch_assoc()) {
            $result['size_mb'] = (float)$row['size_mb'];
        }
        
        // Get last update time (if timestamp column exists)
        if (in_array('created_at', $result['columns']) || in_array('recorded_at', $result['columns']) || in_array('analyzed_at', $result['columns'])) {
            $time_col = in_array('recorded_at', $result['columns']) ? 'recorded_at' : 
                        (in_array('analyzed_at', $result['columns']) ? 'analyzed_at' : 'created_at');
            $res = $this->conn->query("SELECT MAX($time_col) as last_update FROM $esc_table");
            if ($res && $row = $res->fetch_assoc()) {
                $result['last_update'] = $row['last_update'];
            }
        }
        
        return $result;
    }
    
    /**
     * Check for data anomalies
     */
    public function check_anomalies() {
        $anomalies = array();
        
        // Check for negative stakes
        $res = $this->conn->query("SELECT COUNT(*) as count FROM sports_bets WHERE stake < 0");
        if ($res && $row = $res->fetch_assoc() && $row['count'] > 0) {
            $anomalies[] = array(
                'type' => 'negative_stake',
                'table' => 'sports_bets',
                'count' => (int)$row['count'],
                'severity' => 'critical'
            );
        }
        
        // Check for impossible EV values
        $res = $this->conn->query("SELECT COUNT(*) as count FROM sports_bets WHERE ev_percent > 100 OR ev_percent < -50");
        if ($res && $row = $res->fetch_assoc() && $row['count'] > 0) {
            $anomalies[] = array(
                'type' => 'suspicious_ev',
                'table' => 'sports_bets',
                'count' => (int)$row['count'],
                'severity' => 'warning'
            );
        }
        
        // Check for future dates
        $res = $this->conn->query("SELECT COUNT(*) as count FROM lm_sports_odds WHERE game_date > DATE_ADD(NOW(), INTERVAL 7 DAY)");
        if ($res && $row = $res->fetch_assoc() && $row['count'] > 0) {
            $anomalies[] = array(
                'type' => 'future_dates',
                'table' => 'lm_sports_odds',
                'count' => (int)$row['count'],
                'severity' => 'warning'
            );
        }
        
        // Check for NULL critical fields
        $res = $this->conn->query("SELECT COUNT(*) as count FROM sports_bets WHERE sport IS NULL OR bet_type IS NULL");
        if ($res && $row = $res->fetch_assoc() && $row['count'] > 0) {
            $anomalies[] = array(
                'type' => 'null_critical_fields',
                'table' => 'sports_bets',
                'count' => (int)$row['count'],
                'severity' => 'critical'
            );
        }
        
        return $anomalies;
    }
    
    /**
     * Fix common issues
     */
    public function fix_issues($dry_run = true) {
        $fixes = array();
        
        // Fix missing indexes
        foreach ($this->expected_schema as $table => $schema) {
            if (!isset($schema['indexes'])) continue;
            
            $table_status = $this->verify_table($table);
            if (!$table_status['exists']) continue;
            
            foreach ($schema['indexes'] as $index_col) {
                $esc_table = $this->conn->real_escape_string($table);
                $esc_col = $this->conn->real_escape_string($index_col);
                
                // Check if index exists
                $res = $this->conn->query("SHOW INDEX FROM $esc_table WHERE Column_name = '$esc_col'");
                if ($res && $res->num_rows === 0) {
                    $sql = "CREATE INDEX idx_$esc_col ON $esc_table ($esc_col)";
                    $fixes[] = array(
                        'table' => $table,
                        'issue' => 'missing_index',
                        'column' => $index_col,
                        'sql' => $sql,
                        'executed' => !$dry_run
                    );
                    
                    if (!$dry_run) {
                        $this->conn->query($sql);
                    }
                }
            }
        }
        
        return $fixes;
    }
    
    // ════════════════════════════════════════════════════════════
    //  Private Methods
    // ════════════════════════════════════════════════════════════
    
    private function _get_database_name() {
        $res = $this->conn->query("SELECT DATABASE() as db");
        if ($res && $row = $res->fetch_assoc()) {
            return $row['db'];
        }
        return 'unknown';
    }
    
    private function _verify_tables() {
        $result = array(
            'expected' => count($this->expected_schema),
            'found' => 0,
            'missing' => array(),
            'unexpected' => array()
        );
        
        // Get actual tables
        $res = $this->conn->query("SHOW TABLES");
        $actual_tables = array();
        if ($res) {
            while ($row = $res->fetch_array()) {
                $actual_tables[] = $row[0];
            }
        }
        
        // Check expected tables
        foreach (array_keys($this->expected_schema) as $table) {
            if (in_array($table, $actual_tables)) {
                $result['found']++;
            } else {
                $result['missing'][] = $table;
            }
        }
        
        // Check for unexpected tables (might be from old versions)
        foreach ($actual_tables as $table) {
            if (!isset($this->expected_schema[$table]) && strpos($table, 'lm_') === 0) {
                $result['unexpected'][] = $table;
            }
        }
        
        return $result;
    }
    
    private function _verify_columns() {
        $result = array(
            'tables_checked' => 0,
            'missing_columns' => array()
        );
        
        foreach ($this->expected_schema as $table => $schema) {
            $esc_table = $this->conn->real_escape_string($table);
            $res = $this->conn->query("SHOW COLUMNS FROM $esc_table");
            
            if (!$res) continue;
            
            $existing_cols = array();
            while ($row = $res->fetch_assoc()) {
                $existing_cols[] = $row['Field'];
            }
            
            $result['tables_checked']++;
            
            foreach ($schema['required'] as $required_col) {
                if (!in_array($required_col, $existing_cols)) {
                    $result['missing_columns'][] = array(
                        'table' => $table,
                        'column' => $required_col
                    );
                }
            }
        }
        
        return $result;
    }
    
    private function _verify_indexes() {
        $result = array(
            'tables_checked' => 0,
            'missing_indexes' => array()
        );
        
        foreach ($this->expected_schema as $table => $schema) {
            if (!isset($schema['indexes'])) continue;
            
            $esc_table = $this->conn->real_escape_string($table);
            $res = $this->conn->query("SHOW INDEX FROM $esc_table");
            
            if (!$res) continue;
            
            $existing_indexes = array();
            while ($row = $res->fetch_assoc()) {
                $existing_indexes[] = $row['Column_name'];
            }
            
            $result['tables_checked']++;
            
            foreach ($schema['indexes'] as $required_idx) {
                if (!in_array($required_idx, $existing_indexes)) {
                    $result['missing_indexes'][] = array(
                        'table' => $table,
                        'column' => $required_idx
                    );
                }
            }
        }
        
        return $result;
    }
    
    private function _verify_data_consistency() {
        $result = array(
            'checks' => array()
        );
        
        // Check for bets with invalid sport
        $res = $this->conn->query("SELECT COUNT(*) as count FROM sports_bets 
            WHERE sport NOT IN ('nfl', 'nba', 'nhl', 'mlb', 'ncaaf', 'ncaab', 'cfl')");
        if ($res && $row = $res->fetch_assoc()) {
            $result['checks']['invalid_sport'] = (int)$row['count'];
        }
        
        // Check for bets without odds
        $res = $this->conn->query("SELECT COUNT(*) as count FROM sports_bets WHERE odds IS NULL OR odds = 0");
        if ($res && $row = $res->fetch_assoc()) {
            $result['checks']['missing_odds'] = (int)$row['count'];
        }
        
        // Check for duplicate bets (same game, same pick, same date)
        $res = $this->conn->query("SELECT game_id, pick, COUNT(*) as cnt 
            FROM sports_bets 
            WHERE game_id IS NOT NULL 
            GROUP BY game_id, pick 
            HAVING cnt > 1");
        $duplicates = 0;
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $duplicates += ($row['cnt'] - 1);
            }
        }
        $result['checks']['duplicate_bets'] = $duplicates;
        
        return $result;
    }
    
    private function _check_orphan_records() {
        $result = array();
        
        // Check for weather data without matching game
        $res = $this->conn->query("SELECT COUNT(*) as count FROM lm_weather_data w 
            LEFT JOIN lm_sports_odds o ON w.game_id = o.id 
            WHERE o.id IS NULL AND w.recorded_at > DATE_SUB(NOW(), INTERVAL 7 DAY)");
        if ($res && $row = $res->fetch_assoc()) {
            $result['orphan_weather'] = (int)$row['count'];
        }
        
        // Check for travel analysis without matching schedule
        foreach (array('nba', 'nhl', 'nfl', 'mlb') as $sport) {
            $table = "lm_{$sport}_schedule";
            $res = $this->conn->query("SELECT COUNT(*) as count FROM lm_travel_analysis t 
                LEFT JOIN $table s ON t.game_id = s.game_id 
                WHERE s.game_id IS NULL AND t.analyzed_at > DATE_SUB(NOW(), INTERVAL 7 DAY)");
            if ($res && $row = $res->fetch_assoc() && $row['count'] > 0) {
                $result["orphan_travel_$sport"] = (int)$row['count'];
            }
        }
        
        return $result;
    }
    
    private function _check_duplicates() {
        $result = array();
        
        // Check for duplicate odds entries
        $res = $this->conn->query("SELECT home_team, away_team, game_date, COUNT(*) as cnt 
            FROM lm_sports_odds 
            WHERE game_date >= CURDATE() 
            GROUP BY home_team, away_team, game_date 
            HAVING cnt > 1 
            LIMIT 10");
        
        $duplicate_odds = array();
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $duplicate_odds[] = $row;
            }
        }
        $result['duplicate_odds'] = $duplicate_odds;
        
        return $result;
    }
    
    private function _verify_relationships() {
        // Check referential integrity where applicable
        return array('status' => 'manual_review_required');
    }
    
    private function _check_stale_data() {
        $result = array();
        
        // Check last update times
        $tables_to_check = array(
            'lm_sports_odds' => 'created_at',
            'lm_nba_odds' => 'recorded_at',
            'lm_nhl_odds' => 'recorded_at',
            'lm_nfl_odds' => 'recorded_at',
            'lm_mlb_odds' => 'recorded_at',
            'lm_weather_data' => 'recorded_at',
            'sports_bets' => 'created_at'
        );
        
        foreach ($tables_to_check as $table => $time_col) {
            $esc_table = $this->conn->real_escape_string($table);
            $res = $this->conn->query("SELECT MAX($time_col) as last_update, 
                TIMESTAMPDIFF(HOUR, MAX($time_col), NOW()) as hours_ago 
                FROM $esc_table");
            if ($res && $row = $res->fetch_assoc()) {
                $result[$table] = array(
                    'last_update' => $row['last_update'],
                    'hours_ago' => (int)$row['hours_ago']
                );
            }
        }
        
        return $result;
    }
    
    private function _generate_summary($checks) {
        $critical = 0;
        $warnings = 0;
        $info = 0;
        
        // Count issues
        if (!empty($checks['tables']['missing'])) $critical += count($checks['tables']['missing']);
        if (!empty($checks['columns']['missing_columns'])) $critical += count($checks['columns']['missing_columns']);
        if (!empty($checks['data']['checks']['missing_odds'])) $warnings += $checks['data']['checks']['missing_odds'];
        if (!empty($checks['data']['checks']['duplicate_bets'])) $warnings += $checks['data']['checks']['duplicate_bets'];
        
        $status = 'healthy';
        if ($critical > 0) $status = 'critical';
        elseif ($warnings > 0) $status = 'warning';
        
        return array(
            'status' => $status,
            'critical_issues' => $critical,
            'warnings' => $warnings,
            'info' => $info,
            'tables_found' => $checks['tables']['found'] . '/' . $checks['tables']['expected']
        );
    }
}

// API Endpoint
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'verify';
$verifier = new DatabaseVerifier($conn);

if ($action === 'verify') {
    $report = $verifier->verify_all();
    echo json_encode(array('ok' => true, 'report' => $report));
} elseif ($action === 'table') {
    $table = isset($_GET['table']) ? $_GET['table'] : '';
    if ($table) {
        $info = $verifier->verify_table($table);
        echo json_encode(array('ok' => true, 'table_info' => $info));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing table name'));
    }
} elseif ($action === 'anomalies') {
    $anomalies = $verifier->check_anomalies();
    echo json_encode(array('ok' => true, 'anomalies' => $anomalies));
} elseif ($action === 'fix') {
    $dry_run = !isset($_GET['execute']);
    $fixes = $verifier->fix_issues($dry_run);
    echo json_encode(array(
        'ok' => true, 
        'dry_run' => $dry_run,
        'fixes' => $fixes,
        'message' => $dry_run ? 'Add ?execute=1 to apply fixes' : 'Fixes applied'
    ));
} else {
    echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

$conn->close();
?>
