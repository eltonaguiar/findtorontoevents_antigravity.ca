<?php
/**
 * Database configuration for MovieShows
 */

function getDbConnection()
{
    $host = 'localhost';
    $dbname = 'ejaguiar1_tvmoviestrailers';
    $username = 'ejaguiar1_tvmoviestrailers';
    $password = 'D41$4Jci6T9W2PsJdagLEr*KMo96nrCD';

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