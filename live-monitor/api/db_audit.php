<?php
header('Content-Type: application/json');
$host = 'mysql.50webs.com';
$user = 'ejaguiar1_stocks';
$pass = 'stocks';
$db   = 'ejaguiar1_stocks';

$conn = @new mysqli($host, $user, $pass, $db);
if ($conn->connect_error) {
    die(json_encode(array('ok' => false, 'error' => $conn->connect_error)));
}

$tables = array();
$res = $conn->query("SHOW TABLES");
while ($row = $res->fetch_row()) {
    $table = $row[0];
    $count_res = $conn->query("SELECT COUNT(*) FROM `$table` balance");
    $count = 0;
    if ($count_res) {
        $count_row = $count_res->fetch_row();
        $count = $count_row[0];
    }
    
    $last_res = $conn->query("SELECT created_at FROM `$table` ORDER BY created_at DESC LIMIT 1");
    // fallback for updated_at or scan_time
    if (!$last_res) $last_res = $conn->query("SELECT scan_time as created_at FROM `$table` ORDER BY scan_time DESC LIMIT 1");
    if (!$last_res) $last_res = $conn->query("SELECT pick_date as created_at FROM `$table` ORDER BY pick_date DESC LIMIT 1");

    $last_date = 'never';
    if ($last_res && $last_row = $last_res->fetch_assoc()) {
        $last_date = $last_row['created_at'];
    }

    $tables[] = array(
        'name' => $table,
        'rows' => $count,
        'latest' => $last_date
    );
}

echo json_encode(array('ok' => true, 'databases' => array('ejaguiar1_stocks' => $tables)));
$conn->close();
