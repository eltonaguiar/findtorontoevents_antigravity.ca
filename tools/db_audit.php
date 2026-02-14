<?php
/**
 * Database Audit Tool — Inventories all 3 databases
 * Lists every table, row count, and most recent timestamp
 * PHP 5.2 compatible
 */
error_reporting(0);
ini_set('display_errors', '0');
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$databases = array(
    array(
        'name' => 'ejaguiar1_stocks',
        'host' => 'mysql.50webs.com',
        'user' => 'ejaguiar1_stocks',
        'pass' => 'stocks'
    ),
    array(
        'name' => 'ejaguiar1_memecoin',
        'host' => 'mysql.50webs.com',
        'user' => 'ejaguiar1_memecoin',
        'pass' => 'testing123'
    ),
    array(
        'name' => 'ejaguiar1_sportsbet',
        'host' => 'mysql.50webs.com',
        'user' => 'ejaguiar1_sportsbet',
        'pass' => 'wannabet'
    )
);

$all_results = array();

foreach ($databases as $db_info) {
    $conn = new mysqli($db_info['host'], $db_info['user'], $db_info['pass'], $db_info['name']);
    if ($conn->connect_error) {
        $all_results[] = array(
            'database' => $db_info['name'],
            'error' => 'Connection failed: ' . $conn->connect_error,
            'tables' => array()
        );
        continue;
    }
    $conn->set_charset('utf8');

    $tables = array();
    $r = $conn->query("SHOW TABLES");
    if ($r) {
        while ($row = $r->fetch_row()) {
            $tbl_name = $row[0];
            $info = array('name' => $tbl_name, 'rows' => 0, 'columns' => array(), 'last_date' => '');

            // Row count
            $r2 = $conn->query("SELECT COUNT(*) as cnt FROM `" . $tbl_name . "`");
            if ($r2) {
                $cnt_row = $r2->fetch_assoc();
                $info['rows'] = (int)$cnt_row['cnt'];
            }

            // Column names
            $r3 = $conn->query("SHOW COLUMNS FROM `" . $tbl_name . "`");
            if ($r3) {
                $cols = array();
                while ($col = $r3->fetch_assoc()) {
                    $cols[] = $col['Field'] . ' (' . $col['Type'] . ')';
                }
                $info['columns'] = $cols;
            }

            // Try to find latest timestamp
            $date_cols = array('created_at', 'signal_time', 'computed_at', 'collected_at', 'updated_at', 'trade_date', 'pick_date', 'snapshot_time', 'recorded_at', 'metric_date', 'data_date', 'scan_time', 'timestamp', 'resolved_at');
            $found_date = false;
            foreach ($date_cols as $dc) {
                $r4 = $conn->query("SELECT `" . $dc . "` FROM `" . $tbl_name . "` ORDER BY `" . $dc . "` DESC LIMIT 1");
                if ($r4 && $r4->num_rows > 0) {
                    $d_row = $r4->fetch_row();
                    if ($d_row[0] !== null && $d_row[0] !== '' && $d_row[0] !== '0000-00-00 00:00:00') {
                        $info['last_date'] = $d_row[0];
                        $info['date_column'] = $dc;
                        $found_date = true;
                        break;
                    }
                }
            }

            $tables[] = $info;
        }
    }

    // Sort: tables with data first, then empty
    usort($tables, '_db_sort_tables');

    $total_rows = 0;
    $empty_tables = 0;
    $populated_tables = 0;
    foreach ($tables as $t) {
        $total_rows += $t['rows'];
        if ($t['rows'] > 0) $populated_tables++;
        else $empty_tables++;
    }

    $all_results[] = array(
        'database' => $db_info['name'],
        'total_tables' => count($tables),
        'populated_tables' => $populated_tables,
        'empty_tables' => $empty_tables,
        'total_rows' => $total_rows,
        'tables' => $tables
    );

    $conn->close();
}

echo json_encode(array('ok' => true, 'databases' => $all_results));

function _db_sort_tables($a, $b) {
    if ($a['rows'] == $b['rows']) return strcmp($a['name'], $b['name']);
    return ($a['rows'] > $b['rows']) ? -1 : 1;
}
