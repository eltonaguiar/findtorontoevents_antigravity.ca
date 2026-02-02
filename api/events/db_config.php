<?php
/**
 * Events DB config: env vars (getenv or $_ENV), then optional .env file, then defaults.
 * Database: ejaguiar1_events
 * Complex passwords: use .env with quoted value MYSQL_PASSWORD="p@ss#word" so # $ " ' etc. are preserved.
 */
error_reporting(0);
ini_set('display_errors', '0');

function _events_db_unquote_env($v) {
    if (!is_string($v) || $v === '') return $v;
    $len = strlen($v);
    if ($len >= 2 && $v[0] === '"' && $v[$len-1] === '"') return substr($v, 1, -1);
    if ($len >= 2 && $v[0] === "'" && $v[$len-1] === "'") return substr($v, 1, -1);
    return $v;
}

function _events_db_clean_password($v) {
    if (!is_string($v)) return $v;
    $v = str_replace("\0", '', $v);
    return rtrim($v, "\r\n");
}

function _events_db_read_env_file($key) {
    $envFile = dirname(__FILE__) . '/.env';
    if (!file_exists($envFile) || !is_readable($envFile)) return null;
    $raw = file_get_contents($envFile);
    $lines = preg_split('/\r?\n/', $raw);
    $passwordKeys = array('MYSQL_PASSWORD', 'DB_PASS_SERVER_EVENTS', 'DB_PASSWORD', 'DATABASE_PASSWORD');
    foreach ($lines as $line) {
        $line = trim($line);
        if ($line === '' || $line[0] === '#') continue;
        if (strpos($line, '=') === false) continue;
        $eq = strpos($line, '=');
        $k = trim(substr($line, 0, $eq));
        $val = substr($line, $eq + 1);
        if ($k === $key) return _events_db_parse_env_value($val);
        if ($key === 'MYSQL_PASSWORD' && in_array($k, $passwordKeys)) return _events_db_parse_env_value($val);
    }
    return null;
}

function _events_db_env_raw($key, $default) {
    // Prefer .env for password so deployed file wins over server env (which may be wrong/truncated).
    if ($key === 'MYSQL_PASSWORD') {
        $fromFile = _events_db_read_env_file($key);
        if ($fromFile !== null && $fromFile !== '') return $fromFile;
    }
    $v = @getenv($key);
    if ($v !== false && $v !== '') return _events_db_unquote_env($v);
    if (isset($_ENV[$key]) && (string)$_ENV[$key] !== '') return _events_db_unquote_env((string)$_ENV[$key]);
    $alts = array('MYSQL_PASSWORD' => array('DB_PASS_SERVER_EVENTS', 'DB_PASSWORD', 'DATABASE_PASSWORD'), 'MYSQL_USER' => array('DB_USER'), 'MYSQL_HOST' => array('DB_HOST'), 'MYSQL_DATABASE' => array('DB_NAME'));
    if (isset($alts[$key])) {
        foreach ($alts[$key] as $alt) {
            $v = @getenv($alt);
            if ($v !== false && $v !== '') return _events_db_unquote_env($v);
            if (isset($_ENV[$alt]) && (string)$_ENV[$alt] !== '') return _events_db_unquote_env((string)$_ENV[$alt]);
        }
    }
    $fromFile = _events_db_read_env_file($key);
    if ($fromFile !== null) return $fromFile;
    return $default;
}

// Parse .env value: quoted strings preserve # $ " ' and spaces; no #-as-comment in value.
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

$servername = _events_db_env_raw('MYSQL_HOST', 'localhost');
$username   = _events_db_env_raw('MYSQL_USER', 'ejaguiar1_events');
$password   = _events_db_env_raw('MYSQL_PASSWORD', 'event123');
$password   = _events_db_clean_password($password);
$dbname     = _events_db_env_raw('MYSQL_DATABASE', 'ejaguiar1_events');
?>
