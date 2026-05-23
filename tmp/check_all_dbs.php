<?php
$db_creds = array(
    'ejaguiar1_deals'          => array('ejaguiar1_deals',          'deals123'),
    'ejaguiar1_events'         => array('ejaguiar1_events',         '0nOj4g4RA%FD9P4c7iq)'),
    'ejaguiar1_favcreators'    => array('ejaguiar1_favcreators',    '3ADDzY*stB6Qd#$!l1%IIKYuHVRCCupl'),
    'ejaguiar1_memecoin'       => array('ejaguiar1_memecoin',       getenv('MEMECOIN_DB_PASS') ?: ''),
    'ejaguiar1_news'           => array('ejaguiar1_news',           'newsnews'),
    'ejaguiar1_sportsbet'      => array('ejaguiar1_sportsbet',      'eltonsportsbets'),
    'ejaguiar1_stocks'         => array('ejaguiar1_stocks',         'stocks'),
    'ejaguiar1_tvmoviestrailers' => array('ejaguiar1_tvmoviestrailers', 'tvmoviestrailers'),
);

$result = array();
foreach ($db_creds as $dbname => $cred) {
    try {
        $pdo = new PDO("mysql:host=localhost;dbname=$dbname;charset=utf8mb4", $cred[0], $cred[1]);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $tables = $pdo->query("SHOW TABLES")->fetchAll(PDO::FETCH_COLUMN);
        $counts = array();
        foreach ($tables as $t) {
            $counts[$t] = (int)$pdo->query("SELECT COUNT(*) FROM `$t`")->fetchColumn();
        }
        $result[$dbname] = array('tables' => count($tables), 'counts' => $counts);
    } catch (Exception $e) {
        $result[$dbname] = array('error' => $e->getMessage());
    }
}
header('Content-Type: application/json');
echo json_encode($result);
