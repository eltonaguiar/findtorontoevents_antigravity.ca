<?php
/**
 * Database Table Audit — one-time diagnostic endpoint
 * Lists ALL tables in the sports DB with row counts and last update time
 * PHP 5.2 compatible
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/sports_db_connect.php';

$out = array('ok' => true, 'database' => '', 'tables' => array(), 'blank_tables' => array(), 'populated_tables' => array());

// Which database are we connected to?
$db_q = $conn->query("SELECT DATABASE() AS db_name");
if ($db_q && $row = $db_q->fetch_assoc()) {
    $out['database'] = $row['db_name'];
}

// Get all tables
$tbl_q = $conn->query("SHOW TABLES");
if (!$tbl_q) {
    $out['ok'] = false;
    $out['error'] = 'Cannot list tables: ' . $conn->error;
    echo json_encode($out);
    exit;
}

while ($row = $tbl_q->fetch_row()) {
    $tbl = $row[0];
    $info = array('name' => $tbl, 'rows' => 0, 'last_update' => null, 'columns' => array());

    // Row count
    $cnt = $conn->query("SELECT COUNT(*) AS c FROM `" . $tbl . "`");
    if ($cnt && $r = $cnt->fetch_assoc()) {
        $info['rows'] = (int)$r['c'];
    }

    // Try to get last update from common date columns
    $date_cols = array('updated_at', 'recorded_at', 'placed_at', 'run_at', 'reported_at', 'snapshot_date', 'settled_at', 'predicted_at', 'created_at', 'commence_time');
    foreach ($date_cols as $dc) {
        $dq = @$conn->query("SELECT MAX(`" . $dc . "`) AS latest FROM `" . $tbl . "`");
        if ($dq && $dr = $dq->fetch_assoc()) {
            if ($dr['latest'] !== null) {
                $info['last_update'] = $dr['latest'];
                break;
            }
        }
    }

    // Get column names
    $col_q = @$conn->query("SHOW COLUMNS FROM `" . $tbl . "`");
    if ($col_q) {
        while ($cr = $col_q->fetch_assoc()) {
            $info['columns'][] = $cr['Field'];
        }
    }

    $out['tables'][] = $info;

    if ($info['rows'] === 0) {
        $out['blank_tables'][] = $tbl;
    } else {
        $out['populated_tables'][] = $tbl . ' (' . $info['rows'] . ' rows)';
    }
}

$out['total_tables'] = count($out['tables']);
$out['total_blank'] = count($out['blank_tables']);
$out['total_populated'] = count($out['populated_tables']);

echo json_encode($out);
?>
