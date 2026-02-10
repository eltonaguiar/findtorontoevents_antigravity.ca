<?php
/**
 * Database configuration for Live Trading Monitor
 * Uses same database as stocks/crypto/forex (all share ejaguiar1_stocks)
 * PHP 5.2 compatible
 */
error_reporting(0);
ini_set('display_errors', '0');

$servername = 'mysql.50webs.com';
$username   = 'ejaguiar1_stocks';
$password   = 'stocks';
$dbname     = 'ejaguiar1_stocks';

// API Keys for real-time data sources
$FREECRYPTO_API_KEY    = 'qb8ddikglknpseumlz4w';
$CURRENCYLAYER_API_KEY = 'd7ea1ac2fe1deb49ed6f8e07c882b341';
$FINNHUB_API_KEY       = 'cvstlkhr01qhup0t0j7gcvstlkhr01qhup0t0j80';
?>