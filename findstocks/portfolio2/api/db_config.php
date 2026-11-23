<?php
/**
 * Database configuration for the findstocks/portfolio2 API surface.
 * PHP 5.2 compatible.
 *
 * WHY THIS FILE EXISTS (2026-11-23)
 * ---------------------------------
 * stock_intel.php does `require_once dirname(__FILE__) . '/db_connect.php'`, and
 * kimi_goldmine_api.php pointed at the same path. But `findstocks/portfolio2/api/`
 * did not exist in the repo (only `findstocks/portfolio2/data/`) and the path
 * returned 404 on the live host, so stock_intel.php could never have run at all.
 * Creating the connector here is the fix; the caller itself was fine.
 *
 * NO HARDCODED PASSWORD
 * ---------------------
 * The rest of the repo hardcodes a stale 6-character password in five
 * db_config.php files; on the live host that returns
 *   Access denied for user 'ejaguiar1_stocks'@'<web-host-ip>' (using password: YES)
 * The live server already holds the current password in the FTP-deployed,
 * gitignored .env that live-monitor/api/db_config.php reads successfully.
 * 50webs cannot set PHP environment variables via .htaccess, so that file is the
 * only mechanism. Resolve from it rather than duplicating a stale secret.
 */

error_reporting(0);
ini_set('display_errors', '0');

$servername = 'mysql.50webs.com';
$username   = 'ejaguiar1_stocks';
$dbname     = 'ejaguiar1_stocks';

if (!function_exists('_fs_env_candidates')) {
    function _fs_env_candidates() {
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

if (!function_exists('_fs_cred')) {
    function _fs_cred($key, $default) {
        $v = @getenv($key);
        if ($v !== false && $v !== '') { return $v; }
        $paths = _fs_env_candidates();
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

$password = _fs_cred('DB_STOCKS_PASSWORD', '');
?>
