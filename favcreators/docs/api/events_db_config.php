<?php
/**
 * Events DB config - connects to ejaguiar1_events database.
 * This is separate from favcreators db config.
 */
error_reporting(0);
ini_set('display_errors', '0');

function _events_db_parse_env_value($v) {
    $v = trim($v, " \t\r\n");
    $len = strlen($v);
    if ($len >= 2 && $v[0] === '"' && $v[$len-1] === '"') {
        $v = substr($v, 1, -1);
        return str_replace(array('\\"', '\\\\'), array('"', '\\'), $v);
    }
    if ($len >= 2 && $v[0] === "'" && $v[$len-1] === "'") {
        $v = substr($v, 1, -1);
        return str_replace("\\'", "'", $v);
    }
    return $v;
}

function _events_db_read_env_file($key) {
    $envFile = dirname(__FILE__) . '/.env.events';
    if (!file_exists($envFile) || !is_readable($envFile)) return null;
    $raw = file_get_contents($envFile);
    $lines = preg_split('/\r?\n/', $raw);
    foreach ($lines as $line) {
        $line = trim($line);
        if ($line === '' || $line[0] === '#') continue;
        if (strpos($line, '=') === false) continue;
        $eq = strpos($line, '=');
        $k = trim(substr($line, 0, $eq));
        $val = substr($line, $eq + 1);
        if ($k === $key) return _events_db_parse_env_value($val);
    }
    return null;
}

/** Prefer environment variables (set on server), then .env.events file. Database: ejaguiar1_events */
function _events_db_env($key) {
    $v = getenv($key);
    if ($v !== false && $v !== '') return trim($v);
    $v = isset($_ENV[$key]) ? $_ENV[$key] : null;
    if ($v !== null && $v !== '') return is_string($v) ? trim($v) : $v;
    return _events_db_read_env_file($key);
}

// Events database credentials - database: ejaguiar1_events (password from env or .env.events)
$events_servername = _events_db_env('EVENTS_MYSQL_HOST');
if (!$events_servername) $events_servername = 'localhost';

$events_username = _events_db_env('EVENTS_MYSQL_USER');
if (!$events_username) $events_username = 'ejaguiar1_events';

$events_password = _events_db_env('EVENTS_MYSQL_PASSWORD');
if (!$events_password) $events_password = 'event123';

$events_dbname = _events_db_env('EVENTS_MYSQL_DATABASE');
if (!$events_dbname) $events_dbname = 'ejaguiar1_events';
?>
