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

// Sports Betting — separate database
$sports_servername = 'mysql.50webs.com';
$sports_username   = 'ejaguiar1_sportsbet';
$sports_password   = 'eltonsportsbets';
$sports_dbname     = 'ejaguiar1_sportsbet';

// Sports Betting - The Odds API (free tier: 500 credits/month)
// Sign up at https://the-odds-api.com to get your key
$THE_ODDS_API_KEY      = 'b91c3bedfe2553cf90a5fa2003417b2a';

// Multi-Dimensional Supplemental Data API Keys
// Get free API keys from:
// - FMP: https://financialmodelingprep.com/register (250 calls/day)
// - Massive: https://massive.com/signup (5 calls/min, formerly Polygon.io)
$FMP_API_KEY           = 'iF4K10WedJZINDhUWGXlGAiA57rn4sRD';
$MASSIVE_API_KEY       = 'fy4jr0InvOwOQuK43jLspga5xqhQr0Lq';
?>