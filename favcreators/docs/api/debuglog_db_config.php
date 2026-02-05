<?php
/**
 * Config for ejaguiar1_debuglog database (debug logging).
 * Env: DEBUGLOG_MYSQL_HOST, DEBUGLOG_MYSQL_USER, DEBUGLOG_MYSQL_PASSWORD, DEBUGLOG_MYSQL_DATABASE
 * Default password: "debuglog" for database ejaguiar1_debuglog.
 */
if (!function_exists('_debuglog_env')) {
    function _debuglog_env($key, $default) {
        $v = @getenv($key);
        if ($v !== false && $v !== '') return $v;
        if (isset($_ENV[$key]) && (string)$_ENV[$key] !== '') return (string)$_ENV[$key];
        $envFile = dirname(__FILE__) . '/.env';
        if (file_exists($envFile) && is_readable($envFile)) {
            $raw = file_get_contents($envFile);
            foreach (preg_split('/\r?\n/', $raw) as $line) {
                $line = trim($line);
                if ($line === '' || $line[0] === '#') continue;
                if (strpos($line, '=') === false) continue;
                $eq = strpos($line, '=');
                $k = trim(substr($line, 0, $eq));
                if ($k === $key) return trim(substr($line, $eq + 1), " \t\"'");
            }
        }
        return $default;
    }
}
$debuglog_host     = _debuglog_env('DEBUGLOG_MYSQL_HOST', 'localhost');
$debuglog_user     = _debuglog_env('DEBUGLOG_MYSQL_USER', 'ejaguiar1_debuglog');
$debuglog_password = _debuglog_env('DEBUGLOG_MYSQL_PASSWORD', 'debuglog');
$debuglog_database = _debuglog_env('DEBUGLOG_MYSQL_DATABASE', 'ejaguiar1_debuglog');
