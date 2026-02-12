<?php
/**
 * performance_probe.php — Probe for algorithm performance across assets.
 * Dumps summaries from key tables. PHP 5.2 compatible.
 */

// Load DB connection
require_once __DIR__ . '/../../favcreators/public/api/config.php';

$asset_classes = array('STOCK', 'CRYPTO', 'FOREX', 'SPORTS');
$output = array();

// Helper to query performance
function query_perf($conn, $table, $asset=null) {
    $query = "SELECT * FROM $table";
    if ($asset) $query .= " WHERE asset_class = '" . $conn->real_escape_string($asset) . "'";
    $query .= " ORDER BY win_rate DESC, avg_return_pct DESC LIMIT 50";
    
    $r = $conn->query($query);
    $rows = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $rows[] = $row;
        }
    }
    return $rows;
}

// Stocks (algo_performance, lm_algo_performance)
$output['stocks'] = query_perf($conn, 'algo_performance', 'STOCK');
$output['stocks_lm'] = query_perf($conn, 'lm_algo_performance', 'STOCK');

// Crypto
$output['crypto'] = query_perf($conn, 'cr_algo_performance', 'CRYPTO');

// Forex
$output['forex'] = query_perf($conn, 'fx_algo_performance', 'FOREX');

// Sports (from betting DB if separate, else adapt)
$sports_conn = @new mysqli('mysql.50webs.com', 'ejaguiar1_sportsbet', 'eltonsportsbets', 'ejaguiar1_sportsbet');
if (!$sports_conn->connect_error) {
    $output['sports'] = query_perf($sports_conn, 'lm_sports_algo_performance');
    $sports_conn->close();
} else {
    $output['sports'] = array();  // Or query from main if integrated
}

// Penny stocks, mutual funds, meme (adapt queries if tables exist)
$output['penny'] = query_perf($conn, 'penny_performance');  // Assuming table
$output['mutual'] = query_perf($conn, 'mf_algo_performance');
$output['meme'] = query_perf($conn, 'mc_performance');  // Assuming

header('Content-Type: application/json');
echo json_encode($output);

$conn->close();
?>