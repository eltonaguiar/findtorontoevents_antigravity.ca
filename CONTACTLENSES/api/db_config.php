<?php
/**
 * Contact Lens Checker - DB Configuration
 * Uses the same FavCreators database (ejaguiar1_favcreators).
 * Reads credentials from environment variables or falls back to server defaults.
 */
error_reporting(0);
ini_set('display_errors', '0');

// Try to load .env from project api/ dir
$envPaths = array(
    dirname(__FILE__) . '/.env',
    dirname(__FILE__) . '/../../api/.env'
);
foreach ($envPaths as $envFile) {
    if (file_exists($envFile) && is_readable($envFile)) {
        $raw = file_get_contents($envFile);
        foreach (preg_split('/\r?\n/', $raw) as $line) {
            $line = trim($line);
            if ($line === '' || $line[0] === '#' || strpos($line, '=') === false) continue;
            $eq = strpos($line, '=');
            $k = trim(substr($line, 0, $eq));
            $val = trim(substr($line, $eq + 1), " \t\"'");
            if (!array_key_exists($k, $_ENV)) $_ENV[$k] = $val;
            if (getenv($k) === false) putenv("$k=$val");
        }
        break;
    }
}

function _cl_env($keys, $default) {
    foreach ((array) $keys as $k) {
        $v = getenv($k);
        if ($v !== false && $v !== '') return $v;
        if (isset($_ENV[$k]) && (string) $_ENV[$k] !== '') return (string) $_ENV[$k];
    }
    return $default;
}

$cl_db_host = _cl_env(array('FC_MYSQL_HOST', 'MYSQL_HOST'), 'localhost');
$cl_db_user = _cl_env(array('FC_MYSQL_USER', 'MYSQL_USER'), 'ejaguiar1_favcreators');
$cl_db_pass = _cl_env(array('DB_PASS_SERVER_FAVCREATORS', 'FC_MYSQL_PASSWORD', 'MYSQL_PASSWORD'), '3ADDzY*stB6Qd#$!l1%IIKYuHVRCCupl');
$cl_db_name = _cl_env(array('DB_NAME_SERVER_FAVCREATORS', 'FC_MYSQL_DATABASE', 'MYSQL_DATABASE'), 'ejaguiar1_favcreators');

function cl_get_pdo() {
    global $cl_db_host, $cl_db_user, $cl_db_pass, $cl_db_name;
    $dsn = "mysql:host=$cl_db_host;dbname=$cl_db_name;charset=utf8mb4";
    $pdo = new PDO($dsn, $cl_db_user, $cl_db_pass, array(
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
    ));
    return $pdo;
}
