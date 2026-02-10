$crypt = [Environment]::GetEnvironmentVariable('CRYPT','User')
$cl = [Environment]::GetEnvironmentVariable('CURRENCY_LAYER_API','User')
$finnhub = [Environment]::GetEnvironmentVariable('FINNHUB','User')

$content = @"
<?php
/**
 * Database configuration for Live Trading Monitor
 * Uses same database as stocks/crypto/forex (all share ejaguiar1_stocks)
 * PHP 5.2 compatible
 */
error_reporting(0);
ini_set('display_errors', '0');

`$servername = 'mysql.50webs.com';
`$username   = 'ejaguiar1_stocks';
`$password   = 'stocks';
`$dbname     = 'ejaguiar1_stocks';

// API Keys for real-time data sources
`$FREECRYPTO_API_KEY    = '$crypt';
`$CURRENCYLAYER_API_KEY = '$cl';
`$FINNHUB_API_KEY       = '$finnhub';
?>
"@

Set-Content -Path "e:\findtorontoevents_antigravity.ca\live-monitor\api\db_config.php" -Value $content -NoNewline
Write-Host "db_config.php updated with API keys including FINNHUB (keys not shown)"
