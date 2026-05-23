<?php
// config.php - Configuration (reads from .env file, then getenv(), then defaults)
// PHP 5.2 compatible — no ?: operator, no closures, no short array syntax.

// --- .env reader (shared with db_config.php pattern) ---
function _config_read_env($key) {
    $envFile = dirname(__FILE__) . '/.env';
    if (!file_exists($envFile) || !is_readable($envFile)) return null;
    $raw = file_get_contents($envFile);
    $lines = preg_split('/\r?\n/', $raw);
    foreach ($lines as $line) {
        $line = trim($line);
        if ($line === '' || $line[0] === '#') continue;
        if (strpos($line, '=') === false) continue;
        $eq = strpos($line, '=');
        $k = trim(substr($line, 0, $eq));
        if ($k !== $key) continue;
        $val = trim(substr($line, $eq + 1));
        $len = strlen($val);
        // Strip surrounding quotes
        if ($len >= 2 && $val[0] === '"' && $val[$len-1] === '"') {
            return substr($val, 1, -1);
        }
        if ($len >= 2 && $val[0] === "'" && $val[$len-1] === "'") {
            return substr($val, 1, -1);
        }
        // Strip inline comments (unquoted # or // at end)
        $hash = strpos($val, '#');
        if ($hash !== false) {
            $val = rtrim(substr($val, 0, $hash));
        }
        return $val;
    }
    return null;
}

function _config_get($key, $default) {
    // 1. .env file (most reliable on shared hosting)
    $v = _config_read_env($key);
    if ($v !== null && $v !== '') return $v;
    // 2. getenv (works if server sets SetEnv / php_value)
    $v = @getenv($key);
    if ($v !== false && $v !== '') return $v;
    // 3. $_ENV superglobal
    if (isset($_ENV[$key]) && (string)$_ENV[$key] !== '') return (string)$_ENV[$key];
    return $default;
}

// Google OAuth Credentials
// From: https://console.cloud.google.com/apis/credentials
define('GOOGLE_CLIENT_ID', _config_get('GOOGLE_CLIENT_ID', ''));
define('GOOGLE_CLIENT_SECRET', _config_get('GOOGLE_CLIENT_SECRET', ''));

// Database credentials (if needed)
define('DB_HOST', _config_get('MYSQL_HOST', 'localhost'));
define('DB_USER', _config_get('MYSQL_USER', 'ejaguiar1_favcreators'));
define('DB_PASS', _config_get('MYSQL_PASSWORD', ''));
define('DB_NAME', _config_get('MYSQL_DATABASE', 'ejaguiar1_favcreators'));

// Foursquare Places API v3 (for Near Me feature)
// Get a free API key at: https://foursquare.com/developers/signup
define('FOURSQUARE_API_KEY', _config_get('FOURSQUARE_API_KEY', ''));

// Google Places API (for comprehensive business results when "using google")
// Get a key at: https://console.cloud.google.com/apis/credentials
// Enable "Places API" in Google Cloud Console. $200/month free credit (~6,250 text searches).
define('GOOGLE_PLACES_API_KEY', _config_get('GOOGLE_PLACES_API_KEY', ''));
// No closing PHP tag — intentional best practice for PHP-only files
