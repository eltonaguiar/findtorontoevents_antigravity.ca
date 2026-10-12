<?php
header('Content-Type: text/plain');
require_once dirname(__FILE__) . '/db-config.php';

try {
    $pdo = getDbConnection();
    if ($pdo === null) {
        throw new Exception('Database connection failed');
    }
    $count = $pdo->query('SELECT COUNT(*) FROM movies')->fetchColumn();
    echo 'Connected OK! Movies table rows: ' . (int)$count;
} catch (Exception $e) {
    header('HTTP/1.1 503 Service Unavailable');
    error_log('Movies DB diagnostic failed (code ' . $e->getCode() . ')');
    echo 'FAIL: Database check failed';
}
