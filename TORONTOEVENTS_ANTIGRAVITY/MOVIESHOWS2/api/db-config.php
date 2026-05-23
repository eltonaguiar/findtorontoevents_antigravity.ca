<?php
/**
 * Database configuration for MovieShows2
 * Auto-detects host: 50webs (findtorontoevents.ca) vs GoDaddy (torontoevent.net)
 */

function getDbConnection()
{
    $host = 'localhost';
    $serverHost = isset($_SERVER['HTTP_HOST']) ? $_SERVER['HTTP_HOST'] : '';

    if (strpos($serverHost, 'torontoevent.net') !== false) {
        // GoDaddy
        $dbname   = 'ejaguiar1_tvmoviestrailers';
        $username = 'admin';
        $password = '3ADDzY*stB6Qd#$!l1%IIKYuHVRCCupl';
    } else {
        // 50webs (findtorontoevents.ca, tdotevent.ca)
        $dbname   = 'ejaguiar1_tvmoviestrailers';
        $username = 'ejaguiar1_tvmoviestrailers';
        $password = 'tvmoviestrailers';
    }

    try {
        $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $username, $password);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
        return $pdo;
    } catch (PDOException $e) {
        error_log("Database connection failed: " . $e->getMessage());
        return null;
    }
}
?>
