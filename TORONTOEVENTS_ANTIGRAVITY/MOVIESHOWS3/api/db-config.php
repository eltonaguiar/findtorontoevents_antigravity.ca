<?php
/**
 * Database configuration for MovieShows3
 * Supports both legacy 50webs credentials and GoDaddy admin credentials.
 */

function getDbConnection()
{
    $host = 'localhost';
    $dbname = 'ejaguiar1_tvmoviestrailers';
    $serverHost = isset($_SERVER['HTTP_HOST']) ? $_SERVER['HTTP_HOST'] : '';

    // Allow secure override from environment first.
    $envUser = getenv('EJAGUIAR1_TVMOVIESTRAILERS_USER');
    $envPass = getenv('EJAGUIAR1_TVMOVIESTRAILERS');
    $credCandidates = array();

    if (!empty($envUser) && !empty($envPass)) {
        $credCandidates[] = array($envUser, $envPass);
    }

    // Prefer host-specific defaults, then include fallback chain.
    if (strpos($serverHost, 'torontoevent.net') !== false) {
        $credCandidates[] = array('admin', '3ADDzY*stB6Qd#$!l1%IIKYuHVRCCupl');
        $credCandidates[] = array('ejaguiar1_tvmoviestrailers', 'tvmoviestrailers');
    } else {
        $credCandidates[] = array('ejaguiar1_tvmoviestrailers', 'tvmoviestrailers');
        $credCandidates[] = array('admin', '3ADDzY*stB6Qd#$!l1%IIKYuHVRCCupl');
    }

    $lastError = null;

    foreach ($credCandidates as $creds) {
        $username = $creds[0];
        $password = $creds[1];

        try {
            $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $username, $password);
            $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
            return $pdo;
        } catch (PDOException $e) {
            $lastError = $e->getMessage();
            error_log("MovieShows3 DB connect failed for user '" . $username . "': " . $lastError);
        }
    }

    error_log("MovieShows3 DB connection failed after all credential fallbacks");
    return null;
}
?>

