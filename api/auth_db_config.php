<?php
// Auth DB config: same DB as FavCreators (users table).
// Use this when FavCreators db_config is not available (e.g. api deployed separately).
// Reads FC_MYSQL_* or MYSQL_* from env or api/.env. See api/.env.example (auth section).
error_reporting(0);
ini_set('display_errors', '0');

$envFile = dirname(__FILE__) . '/.env';
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
}

function _auth_db_get($keys, $default) {
    foreach ((array) $keys as $k) {
        $v = getenv($k);
        if ($v !== false && $v !== '') return $v;
        if (isset($_ENV[$k]) && (string) $_ENV[$k] !== '') return (string) $_ENV[$k];
    }
    return $default;
}

// Reads env / api/.env first; defaults below used when PHP doesn't see server env (e.g. cPanel).
// FavCreators DB: ejaguiar1_favcreators / Solid-Kitten-92-Brave-Vessel
$servername = _auth_db_get(array('FC_MYSQL_HOST', 'MYSQL_HOST'), 'localhost');
$username   = _auth_db_get(array('FC_MYSQL_USER', 'MYSQL_USER'), 'ejaguiar1_favcreators');
$password   = _auth_db_get(array('DB_PASS_SERVER_FAVCREATORS', 'FC_MYSQL_PASSWORD', 'MYSQL_PASSWORD'), 'Solid-Kitten-92-Brave-Vessel');
$dbname     = _auth_db_get(array('DB_NAME_SERVER_FAVCREATORS', 'FC_MYSQL_DATABASE', 'MYSQL_DATABASE'), 'ejaguiar1_favcreators');
