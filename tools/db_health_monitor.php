<?php
/**
 * Database Health Monitor - ENHANCED
 * 
 * Checks all 8 databases for stale data, empty tables, and broken pipelines.
 * Designed to be called by GitHub Actions daily.
 *
 * PHP 5.2 compatible.
 *
 * ?action=check     — Full health check across all 8 DBs
 * ?action=summary   — Quick summary (row counts, freshness)
 * ?action=setup_all — Trigger schema setup for all databases
 */

error_reporting(0);
ini_set('display_errors', '0');
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// All 8 databases with credentials
die(json_encode(array('ok' => false, 'error' => 'Missing DB_PASSWORD environment variable')));

$dbs = array(
    array('name' => 'ejaguiar1_stocks', 'host' => 'mysql.50webs.com', 'user' => 'ejaguiar1_stocks', 'pass' => getenv('DB_STOCKS_PASS') ?: 'stocks'),
    array('name' => 'ejaguiar1_memecoin', 'host' => 'mysql.50webs.com', 'user' => 'ejaguiar1_memecoin', 'pass' => getenv('DB_MEMECOIN_PASS') ?: 'testing123'),
    array('name' => 'ejaguiar1_sportsbet', 'host' => 'mysql.50webs.com', 'user' => 'ejaguiar1_sportsbet', 'pass' => getenv('DB_SPORTSBET_PASS') ?: 'wannabet'),
    array('name' => 'ejaguiar1_favcreators', 'host' => 'mysql.50webs.com', 'user' => 'ejaguiar1', 'pass' => getenv('DB_FAVCREATORS_PASS') ?: ''),
    array('name' => 'ejaguiar1_events', 'host' => 'mysql.50webs.com', 'user' => 'ejaguiar1', 'pass' => getenv('DB_EVENTS_PASS') ?: ''),
    array('name' => 'ejaguiar1_tvmoviestrailers', 'host' => 'mysql.50webs.com', 'user' => 'ejaguiar1', 'pass' => getenv('DB_MOVIES_PASS') ?: ''),
    array('name' => 'ejaguiar1_deals', 'host' => 'mysql.50webs.com', 'user' => 'ejaguiar1', 'pass' => getenv('DB_DEALS_PASS') ?: ''),
    array('name' => 'ejaguiar1_news', 'host' => 'mysql.50webs.com', 'user' => 'ejaguiar1', 'pass' => getenv('DB_NEWS_PASS') ?: '')
);

$action = isset($_GET['action']) ? $_GET['action'] : 'check';

// Summary action - Quick overview
if ($action === 'summary') {
    $summary = array();
    $total_empty = 0;
    $total_critical = 0;
    
    foreach ($dbs as $db_info) {
        $conn = new mysqli($db_info['host'], $db_info['user'], $db_info['pass'], $db_info['name']);
        if ($conn->connect_error) {
            $summary[] = array(
                'database' => $db_info['name'], 
                'status' => 'DOWN', 
                'error' => $conn->connect_error,
                'total_tables' => 0,
                'populated' => 0,
                'empty' => 0,
                'total_rows' => 0
            );
            $total_critical++;
            continue;
        }
        $conn->set_charset('utf8');
        
        $total_tables = 0; 
        $populated = 0; 
        $empty = 0; 
        $total_rows = 0;
        
        $r = $conn->query("SHOW TABLES");
        if ($r) {
            while ($row = $r->fetch_row()) {
                $total_tables++;
                $r2 = $conn->query("SELECT COUNT(*) as cnt FROM `" . $row[0] . "`");
                if ($r2) {
                    $cnt_row = $r2->fetch_assoc();
                    $cnt = (int)$cnt_row['cnt'];
                    $total_rows += $cnt;
                    if ($cnt > 0) {
                        $populated++;
                    } else {
                        $empty++;
                        $total_empty++;
                    }
                }
            }
        }
        
        // Determine status based on tables
        $status = 'UP';
        if ($total_tables === 0) {
            $status = 'NO_TABLES';
        } elseif ($empty === $total_tables && $total_tables > 0) {
            $status = 'ALL_EMPTY';
        } elseif ($empty > 0) {
            $status = 'PARTIAL';
        }
        
        $summary[] = array(
            'database' => $db_info['name'],
            'status' => $status,
            'total_tables' => $total_tables,
            'populated' => $populated,
            'empty' => $empty,
            'total_rows' => $total_rows,
            'health_percent' => ($total_tables > 0) ? round(($populated / $total_tables) * 100) : 0
        );
        
        $conn->close();
    }
    
    echo json_encode(array(
        'ok' => true, 
        'total_databases' => count($dbs),
        'total_empty_tables' => $total_empty,
        'critical_databases' => $total_critical,
        'timestamp' => date('Y-m-d H:i:s'),
        'databases' => $summary
    ));
    exit;
}

// Check action - Full detailed health check
$health = array();
$warnings = array();
$critical = array();
$db_stats = array();

foreach ($dbs as $db_info) {
    $conn = new mysqli($db_info['host'], $db_info['user'], $db_info['pass'], $db_info['name']);
    
    if ($conn->connect_error) {
        $critical[] = $db_info['name'] . ': Connection FAILED - ' . $conn->connect_error;
        $db_stats[$db_info['name']] = array('status' => 'DOWN', 'tables' => array());
        continue;
    }
    
    $conn->set_charset('utf8');
    
    $db_health = array(
        'database' => $db_info['name'], 
        'status' => 'UP', 
        'tables' => array(),
        'empty_tables' => array(),
        'stale_tables' => array()
    );
    
    $r = $conn->query("SHOW TABLES");
    if ($r) {
        while ($row = $r->fetch_row()) {
            $tbl = $row[0];
            
            // Get row count
            $r2 = $conn->query("SELECT COUNT(*) as cnt FROM `" . $tbl . "`");
            $cnt = 0;
            if ($r2) {
                $cr = $r2->fetch_assoc();
                $cnt = (int)$cr['cnt'];
            }
            
            // Track empty tables
            if ($cnt === 0) {
                $db_health['empty_tables'][] = $tbl;
            }
            
            // Check freshness for key tables
            $freshness = '';
            $is_stale = false;
            $date_cols = array('created_at', 'signal_time', 'computed_at', 'updated_at', 'collected_at', 'synced_at', 'last_update');
            
            foreach ($date_cols as $dc) {
                $r3 = $conn->query("SELECT `" . $dc . "` FROM `" . $tbl . "` ORDER BY `" . $dc . "` DESC LIMIT 1");
                if ($r3 && $r3->num_rows > 0) {
                    $d = $r3->fetch_row();
                    if ($d[0] !== null && $d[0] !== '' && $d[0] !== '0000-00-00 00:00:00') {
                        $freshness = $d[0];
                        // Check if stale (>48h old for active tables)
                        $ts = strtotime($d[0]);
                        if ($ts !== false && $cnt > 0) {
                            $age_hours = (time() - $ts) / 3600;
                            if ($age_hours > 48 && $cnt > 10) {
                                $is_stale = true;
                                $db_health['stale_tables'][] = array(
                                    'table' => $tbl,
                                    'last_update' => $freshness,
                                    'age_hours' => round($age_hours),
                                    'rows' => $cnt
                                );
                                $warnings[] = $db_info['name'] . '.' . $tbl . ': Last update ' . round($age_hours) . 'h ago (' . $cnt . ' rows)';
                            }
                        }
                        break;
                    }
                }
            }
            
            $db_health['tables'][] = array(
                'name' => $tbl, 
                'rows' => $cnt, 
                'last_update' => $freshness,
                'is_stale' => $is_stale
            );
        }
    }
    
    $health[] = $db_health;
    $db_stats[$db_info['name']] = $db_health;
    $conn->close();
}

// Extended critical tables check for all databases
$must_have = array(
    // Stocks DB
    array('db' => 'ejaguiar1_stocks', 'table' => 'lm_signals', 'min_rows' => 10),
    array('db' => 'ejaguiar1_stocks', 'table' => 'ua_predictions', 'min_rows' => 1),
    array('db' => 'ejaguiar1_stocks', 'table' => 'ps_scores', 'min_rows' => 30),
    array('db' => 'ejaguiar1_stocks', 'table' => 'ml_feature_store', 'min_rows' => 1),
    array('db' => 'ejaguiar1_stocks', 'table' => 'goldmine_tracker', 'min_rows' => 1),
    array('db' => 'ejaguiar1_stocks', 'table' => 'performance_probe', 'min_rows' => 1),
    
    // Memecoin DB
    array('db' => 'ejaguiar1_memecoin', 'table' => 'he_signals', 'min_rows' => 1),
    array('db' => 'ejaguiar1_memecoin', 'table' => 'tv_signals', 'min_rows' => 1),
    array('db' => 'ejaguiar1_memecoin', 'table' => 'ke_signals', 'min_rows' => 1),
    array('db' => 'ejaguiar1_memecoin', 'table' => 'ec_signals', 'min_rows' => 1),
    array('db' => 'ejaguiar1_memecoin', 'table' => 'meme_signals', 'min_rows' => 1),
    array('db' => 'ejaguiar1_memecoin', 'table' => 'meme_ml_models', 'min_rows' => 1),
    array('db' => 'ejaguiar1_memecoin', 'table' => 'ml_feature_store', 'min_rows' => 1),
    array('db' => 'ejaguiar1_memecoin', 'table' => 'algo_predictions', 'min_rows' => 1),
    
    // Sportsbet DB
    array('db' => 'ejaguiar1_sportsbet', 'table' => 'lm_sports_odds', 'min_rows' => 10),
    array('db' => 'ejaguiar1_sportsbet', 'table' => 'sports_data_bridge', 'min_rows' => 1),
    
    // Events DB
    array('db' => 'ejaguiar1_events', 'table' => 'events', 'min_rows' => 10),
    array('db' => 'ejaguiar1_events', 'table' => 'event_sources', 'min_rows' => 1),
    array('db' => 'ejaguiar1_events', 'table' => 'sync_log', 'min_rows' => 1),
    
    // Movies DB
    array('db' => 'ejaguiar1_tvmoviestrailers', 'table' => 'movies', 'min_rows' => 10),
    array('db' => 'ejaguiar1_tvmoviestrailers', 'table' => 'trailers', 'min_rows' => 1),
    array('db' => 'ejaguiar1_tvmoviestrailers', 'table' => 'thumbnails', 'min_rows' => 1),
    array('db' => 'ejaguiar1_tvmoviestrailers', 'table' => 'content_sources', 'min_rows' => 1),
    
    // Favcreators DB
    array('db' => 'ejaguiar1_favcreators', 'table' => 'streamer_last_seen', 'min_rows' => 1),
    array('db' => 'ejaguiar1_favcreators', 'table' => 'streamer_check_log', 'min_rows' => 1),
    array('db' => 'ejaguiar1_favcreators', 'table' => 'favcreatorslogs', 'min_rows' => 1),
    array('db' => 'ejaguiar1_favcreators', 'table' => 'creators', 'min_rows' => 1)
);

$missing_tables = array();
$low_row_tables = array();

foreach ($must_have as $check) {
    $found = false;
    $db_found = isset($db_stats[$check['db']]) && $db_stats[$check['db']]['status'] === 'UP';
    
    if ($db_found) {
        foreach ($db_stats[$check['db']]['tables'] as $t) {
            if ($t['name'] !== $check['table']) continue;
            $found = true;
            if ($t['rows'] < $check['min_rows']) {
                $low_row_tables[] = array(
                    'db' => $check['db'],
                    'table' => $check['table'],
                    'rows' => $t['rows'],
                    'min_required' => $check['min_rows']
                );
                $warnings[] = $check['db'] . '.' . $check['table'] . ': Only ' . $t['rows'] . ' rows (min: ' . $check['min_rows'] . ')';
            }
        }
    }
    
    if (!$found && $db_found) {
        $missing_tables[] = $check['db'] . '.' . $check['table'];
        $critical[] = $check['db'] . '.' . $check['table'] . ': TABLE NOT FOUND';
    }
}

// Calculate overall statistics
$total_empty_tables = 0;
$total_populated_tables = 0;
$total_tables = 0;

foreach ($health as $db) {
    foreach ($db['tables'] as $t) {
        $total_tables++;
        if ($t['rows'] === 0) {
            $total_empty_tables++;
        } else {
            $total_populated_tables++;
        }
    }
}

$overall = 'HEALTHY';
if (count($warnings) > 0) $overall = 'WARNING';
if (count($critical) > 0) $overall = 'CRITICAL';
if (count($missing_tables) > 5) $overall = 'CRITICAL_SETUP_REQUIRED';

echo json_encode(array(
    'ok' => (count($critical) === 0),
    'overall_status' => $overall,
    'timestamp' => date('Y-m-d H:i:s'),
    'statistics' => array(
        'total_databases' => count($dbs),
        'total_tables' => $total_tables,
        'total_populated_tables' => $total_populated_tables,
        'total_empty_tables' => $total_empty_tables,
        'health_percentage' => ($total_tables > 0) ? round(($total_populated_tables / $total_tables) * 100) : 0,
        'critical_issues' => count($critical),
        'warnings' => count($warnings),
        'missing_critical_tables' => count($missing_tables),
        'low_row_tables' => count($low_row_tables)
    ),
    'critical' => $critical,
    'warnings' => $warnings,
    'missing_tables' => $missing_tables,
    'low_row_tables' => $low_row_tables,
    'databases' => $health
));
