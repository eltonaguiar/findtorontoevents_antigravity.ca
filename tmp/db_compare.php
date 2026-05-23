<?php
$conn = new PDO('mysql:host=localhost;dbname=ejaguiar1_favcreators;charset=utf8mb4',
    'ejaguiar1_favcreators', '3ADDzY*stB6Qd#$!l1%IIKYuHVRCCupl');
$conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

$tables = $conn->query("SHOW TABLES")->fetchAll(PDO::FETCH_COLUMN);
$counts = array();
foreach ($tables as $t) {
    $n = $conn->query("SELECT COUNT(*) FROM `$t`")->fetchColumn();
    $counts[$t] = (int)$n;
}
header('Content-Type: application/json');
echo json_encode(array('table_count' => count($tables), 'tables' => $counts));
