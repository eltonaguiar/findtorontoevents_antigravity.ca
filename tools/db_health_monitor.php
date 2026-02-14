<?php
/**
 * Database Health Monitor
 * 
 * Checks all 3 databases for stale data, empty tables, and broken pipelines.
 * Designed to be called by GitHub Actions daily.
 *
 * PHP 5.2 compatible.
 *
 * ?action=check     — Full health check across all 3 DBs
 * ?action=summary   — Quick summary (row counts, freshness)
 */

error_reporting(0);
ini_set('display_errors', '0');
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$dbs = array(
    array('name' => 'ejaguiar1_stocks', 'host' => 'mysql.50webs.com', 'user' => 'ejaguiar1_stocks', 'pass' => 'stocks'),
    array('name' => 'ejaguiar1_memecoin', 'host' => 'mysql.50webs.com', 'user' => 'ejaguiar1_memecoin', 'pass' => 'testing123'),
    array('name' => 'ejaguiar1_sportsbet', 'host' => 'mysql.50webs.com', 'user' => 'ejaguiar1_sportsbet', 'pass' => 'wannabet')
);

$action = isset($_GET['action']) ? $_GET['action'] : 'check';

if ($action === 'summary') {
    $summary = array();
    foreach ($dbs as $db_info) {
        $conn = new mysqli($db_info['host'], $db_info['user'], $db_info['pass'], $db_info['name']);
        if ($conn->connect_error) {
            $summary[] = array('database' => $db_info['name'], 'status' => 'DOWN', 'error' => $conn->connect_error);
            continue;
        }
        $conn->set_charset('utf8');
        $total_tables = 0; $populated = 0; $empty = 0; $total_rows = 0;
        $r = $conn->query("SHOW TABLES");
        if ($r) {
            while ($row = $r->fetch_row()) {
                $total_tables++;
                $r2 = $conn->query("SELECT COUNT(*) as cnt FROM `" . $row[0] . "`");
                if ($r2) {
                    $cnt_row = $r2->fetch_assoc();
                    $cnt = (int)$cnt_row['cnt'];
                    $total_rows += $cnt;
                    if ($cnt > 0) $populated++;
                    else $empty++;
                }
            }
        }
        $summary[] = array(
            'database' => $db_info['name'],
            'status' => 'UP',
            'total_tables' => $total_tables,
            'populated' => $populated,
            'empty' => $empty,
            'total_rows' => $total_rows
        );
        $conn->close();
    }
    echo json_encode(array('ok' => true, 'databases' => $summary));
    exit;
}

// Full health check
$health = array();
$warnings = array();
$critical = array();

foreach ($dbs as $db_info) {
    $conn = new mysqli($db_info['host'], $db_info['user'], $db_info['pass'], $db_info['name']);
    if ($conn->connect_error) {
        $critical[] = $db_info['name'] . ': Connection FAILED';
        continue;
    }
    $conn->set_charset('utf8');

    $db_health = array('database' => $db_info['name'], 'status' => 'UP', 'tables' => array());
    $r = $conn->query("SHOW TABLES");
    if ($r) {
        while ($row = $r->fetch_row()) {
            $tbl = $row[0];
            $r2 = $conn->query("SELECT COUNT(*) as cnt FROM `" . $tbl . "`");
            $cnt = 0;
            if ($r2) {
                $cr = $r2->fetch_assoc();
                $cnt = (int)$cr['cnt'];
            }

            // Check freshness for key tables
            $freshness = '';
            $date_cols = array('created_at', 'signal_time', 'computed_at', 'updated_at', 'collected_at');
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
                                $warnings[] = $db_info['name'] . '.' . $tbl . ': Last update ' . round($age_hours) . 'h ago (' . $cnt . ' rows)';
                            }
                        }
                        break;
                    }
                }
            }

            $db_health['tables'][] = array('name' => $tbl, 'rows' => $cnt, 'last_update' => $freshness);
        }
    }
    $health[] = $db_health;
    $conn->close();
}

// Key tables that MUST have data
$must_have = array(
    array('db' => 'ejaguiar1_stocks', 'table' => 'lm_signals', 'min_rows' => 10),
    array('db' => 'ejaguiar1_stocks', 'table' => 'ua_predictions', 'min_rows' => 1),
    array('db' => 'ejaguiar1_stocks', 'table' => 'ps_scores', 'min_rows' => 30),
    array('db' => 'ejaguiar1_stocks', 'table' => 'ml_feature_store', 'min_rows' => 1),
    array('db' => 'ejaguiar1_memecoin', 'table' => 'he_signals', 'min_rows' => 1),
    array('db' => 'ejaguiar1_memecoin', 'table' => 'tv_signals', 'min_rows' => 1),
    array('db' => 'ejaguiar1_sportsbet', 'table' => 'lm_sports_odds', 'min_rows' => 10)
);

foreach ($must_have as $check) {
    $found = false;
    foreach ($health as $db) {
        if ($db['database'] !== $check['db']) continue;
        foreach ($db['tables'] as $t) {
            if ($t['name'] !== $check['table']) continue;
            $found = true;
            if ($t['rows'] < $check['min_rows']) {
                $warnings[] = $check['db'] . '.' . $check['table'] . ': Only ' . $t['rows'] . ' rows (min: ' . $check['min_rows'] . ')';
            }
        }
    }
    if (!$found) {
        $critical[] = $check['db'] . '.' . $check['table'] . ': TABLE NOT FOUND';
    }
}

$overall = 'HEALTHY';
if (count($warnings) > 0) $overall = 'WARNING';
if (count($critical) > 0) $overall = 'CRITICAL';

echo json_encode(array(
    'ok' => (count($critical) === 0),
    'overall_status' => $overall,
    'critical' => $critical,
    'warnings' => $warnings,
    'databases' => $health
));
