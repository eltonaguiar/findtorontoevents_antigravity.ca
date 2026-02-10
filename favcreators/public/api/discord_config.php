<?php
/**
 * Discord configuration helper
 * Reads Discord OAuth settings from .env file
 */

function _discord_read_env($key, $default = '') {
    // Try getenv first
    $v = @getenv($key);
    if ($v !== false && $v !== '') return $v;
    
    // Try $_ENV
    if (isset($_ENV[$key]) && $_ENV[$key] !== '') return $_ENV[$key];
    
    // Read from .env file
    $envFile = dirname(__FILE__) . '/.env';
    if (file_exists($envFile) && is_readable($envFile)) {
        $lines = file($envFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        foreach ($lines as $line) {
            $line = trim($line);
            if ($line === '' || $line[0] === '#') continue;
            if (strpos($line, '=') === false) continue;
            $eq = strpos($line, '=');
            $k = trim(substr($line, 0, $eq));
            $val = trim(substr($line, $eq + 1));
            // Remove quotes
            if (strlen($val) >= 2 && $val[0] === '"' && $val[strlen($val)-1] === '"') {
                $val = substr($val, 1, -1);
            } else {
                // Strip inline # comments for unquoted values
                $hashPos = strpos($val, '#');
                if ($hashPos !== false) {
                    $val = rtrim(substr($val, 0, $hashPos));
                }
            }
            if ($k === $key) return $val;
        }
    }
    
    return $default;
}

function get_discord_config() {
    return array(
        'client_id' => _discord_read_env('DISCORD_CLIENT_ID', ''),
        'client_secret' => _discord_read_env('DISCORD_CLIENT_SECRET', ''),
        'public_key' => _discord_read_env('DISCORD_PUBLIC_KEY', ''),
        'bot_token' => _discord_read_env('DISCORD_BOT_TOKEN', ''),
        'redirect_uri' => _discord_read_env('DISCORD_REDIRECT_URI', 'https://findtorontoevents.ca/fc/api/discord_callback.php'),
        'webhook_url' => _discord_read_env('DISCORD_WEBHOOK_URL', '')
    );
}

function is_discord_configured() {
    $config = get_discord_config();
    return !empty($config['client_id']) && !empty($config['client_secret']);
}
