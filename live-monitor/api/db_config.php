<?php
error_reporting(0);
ini_set('display_errors', '0');

// Read a key from the adjacent .env file (gitignored, FTP-deployed).
// 50webs shared hosting cannot set custom PHP env vars via .htaccess, so
// getenv() always returns false for DB_SPORTS_PASSWORD / DB_STOCKS_PASSWORD.
// The .env file is the authoritative credential store on the live server.
// Format: KEY=value or KEY="value with spaces" — see .env.example.
function _lm_read_env_file($key) {
    $envFile = dirname(__FILE__) . '/.env';
    if (!file_exists($envFile) || !is_readable($envFile)) return '';
    $raw = file_get_contents($envFile);
    if ($raw === false) return '';
    foreach (preg_split('/\r?\n/', $raw) as $line) {
        $line = trim($line);
        if ($line === '' || $line[0] === '#' || strpos($line, '=') === false) continue;
        $eq  = strpos($line, '=');
        $k   = trim(substr($line, 0, $eq));
        if ($k !== $key) continue;
        $v   = trim(substr($line, $eq + 1));
        $len = strlen($v);
        if ($len >= 2 && (
            ($v[0] === '"'  && $v[$len-1] === '"')  ||
            ($v[0] === "'"  && $v[$len-1] === "'")
        )) { $v = substr($v, 1, $len - 2); }
        return $v;
    }
    return '';
}

// Resolve a credential: prefer getenv() (CI/staging), then .env file (prod 50webs), then $default.
function _lm_cred($key, $default) {
    $v = @getenv($key);
    if ($v !== false && $v !== '') return $v;
    if (isset($_ENV[$key]) && $_ENV[$key] !== '') return $_ENV[$key];
    $fromFile = _lm_read_env_file($key);
    if ($fromFile !== '') return $fromFile;
    return $default;
}

$host = isset($_SERVER['HTTP_HOST']) ? $_SERVER['HTTP_HOST'] : '';
if (strpos($host, 'findtorontoevents.ca') !== false || file_exists('/home/www/findtorontoevents.ca')) {
    $servername = 'mysql.50webs.com';
    $username   = 'ejaguiar1_stocks';
    $password   = _lm_cred('DB_STOCKS_PASSWORD', '');
    $dbname     = 'ejaguiar1_stocks';
} else {
    $servername = 'localhost';
    $username   = 'admin';
    $password   = _lm_cred('DB_STOCKS_PASSWORD', 'DEPLOY_WILL_REPLACE_THIS');
    $dbname     = 'ejaguiar1_stocks';
}

// API keys — always read from environment; never hardcode in source control.
$FREECRYPTO_API_KEY    = _lm_cred('FREECRYPTO_API_KEY', '');
$CURRENCYLAYER_API_KEY = _lm_cred('CURRENCY_LAYER_API_KEY', '');
$FINNHUB_API_KEY       = _lm_cred('FINNHUB_API_KEY', '');

if (strpos($host, 'findtorontoevents.ca') !== false || file_exists('/home/www/findtorontoevents.ca')) {
    // Sports DB has its own MySQL user on 50webs (ejaguiar1_sportsbet).
    // Password MUST be present in /live-monitor/api/.env on the server.
    $sports_servername = 'mysql.50webs.com';
    $sports_username   = 'ejaguiar1_sportsbet';
    $sports_password   = _lm_cred('DB_SPORTS_PASSWORD', '');
    $sports_dbname     = 'ejaguiar1_sportsbet';
} else {
    $sports_servername = 'localhost';
    $sports_username   = 'admin';
    $sports_password   = _lm_cred('DB_SPORTS_PASSWORD', 'DEPLOY_WILL_REPLACE_THIS');
    $sports_dbname     = 'ejaguiar1_sportsbet';
}

$THE_ODDS_API_KEY = getenv('THE_ODDS_API_KEY') !== false ? getenv('THE_ODDS_API_KEY') : '';
$ODDS_API_IO_KEY  = getenv('ODDS_API_IO_KEY') !== false ? getenv('ODDS_API_IO_KEY') : '';
$FMP_API_KEY      = getenv('FMP_API_KEY') !== false ? getenv('FMP_API_KEY') : '';
$MASSIVE_API_KEY  = getenv('MASSIVE_API_KEY') !== false ? getenv('MASSIVE_API_KEY') : '';

// Mercury feedback (April 2026) — Tier-1/Tier-2 paid services. Read from env
// only; never commit keys here. PR 1 ships schema + free-tier wiring; the
// callers below are added in PR 2/3 once budget is approved.
$PREDICTION_HUNT_API_KEY = getenv('PREDICTION_HUNT_API_KEY') ? getenv('PREDICTION_HUNT_API_KEY') : '';
$OPENWEATHER_API_KEY     = getenv('OPENWEATHER_API_KEY') ? getenv('OPENWEATHER_API_KEY') : '';
?>
