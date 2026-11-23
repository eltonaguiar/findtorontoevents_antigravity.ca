<?php
/**
 * Database configuration for Mutual Funds Portfolio Analysis
 * Uses same database as stocks but with mf_ prefixed tables
 * PHP 5.2 compatible
 */
error_reporting(0);
ini_set('display_errors', '0');

$servername = 'mysql.50webs.com';
// Using v1 stocks database (same DB, different table prefix: mf_)
$username   = 'ejaguiar1_stocks';
$password   = 'stocks';
$dbname     = 'ejaguiar1_stocks';
// --- Credential override (2026-11-23) ---------------------------------------
// The hardcoded $password above is STALE: on the live PHP 5.2 host it yields
//   Access denied for user 'ejaguiar1_stocks'@'<web-host-ip>' (using password: YES)
// taking this system's endpoints down. The live server already holds the current
// password in the FTP-deployed, gitignored .env that live-monitor/api/db_config.php
// reads successfully. Reuse it so a rotation is applied in one place only.
if (!function_exists('_fx_env_candidates')) {
    function _fx_env_candidates() {
        $dir = dirname(__FILE__);
        $dirs = array();
        for ($i = 0; $i < 6; $i++) {
            $dirs[] = $dir;
            $parent = dirname($dir);
            if ($parent === $dir) { break; }
            $dir = $parent;
        }
        $paths = array();
        foreach ($dirs as $d) {
            $paths[] = $d . '/.env';
            $paths[] = $d . '/live-monitor/api/.env';
        }
        return $paths;
    }
}

if (!function_exists('_fx_cred')) {
    function _fx_cred($key, $default) {
        $v = @getenv($key);
        if ($v !== false && $v !== '') { return $v; }
        $paths = _fx_env_candidates();
        foreach ($paths as $p) {
            if (!file_exists($p) || !is_readable($p)) { continue; }
            $raw = @file_get_contents($p);
            if ($raw === false) { continue; }
            $lines = preg_split('/\r?\n/', $raw);
            foreach ($lines as $line) {
                $line = trim($line);
                if ($line === '' || $line[0] === '#' || strpos($line, '=') === false) { continue; }
                $eq = strpos($line, '=');
                $k = trim(substr($line, 0, $eq));
                if ($k !== $key) { continue; }
                $val = trim(substr($line, $eq + 1));
                $len = strlen($val);
                if ($len >= 2 && (($val[0] === '"' && $val[$len - 1] === '"') || ($val[0] === "'" && $val[$len - 1] === "'"))) {
                    $val = substr($val, 1, $len - 2);
                }
                return $val;
            }
        }
        return $default;
    }
}

$password = _fx_cred('DB_STOCKS_PASSWORD', $password);
?>
