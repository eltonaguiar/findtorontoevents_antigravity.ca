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
?>
