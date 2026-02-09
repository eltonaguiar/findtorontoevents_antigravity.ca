<?php
/**
 * Returns basic data for the Forex system
 * PHP 5.2 compatible
 *
 * Parameters:
 *   type - stats|strategies|signals (default: stats)
 */
require_once dirname(__FILE__) . '/db_connect.php';

$type = isset($_GET['type']) ? $_GET['type'] : (isset($_POST['type']) ? $_POST['type'] : 'stats');

if ($type === 'stats') {
    // Get counts
    $pair_count = 0;
    $pair_res = $conn->query("SELECT COUNT(DISTINCT pair) as cnt FROM fx_pairs");
    if ($pair_res && $row = $pair_res->fetch_assoc()) {
        $pair_count = (int)$row['cnt'];
    }
    
    $signal_count = 0;
    $signal_res = $conn->query("SELECT COUNT(*) as cnt FROM fx_signals");
    if ($signal_res && $row = $signal_res->fetch_assoc()) {
        $signal_count = (int)$row['cnt'];
    }
    
    $price_count = 0;
    $price_res = $conn->query("SELECT COUNT(*) as cnt FROM fx_prices");
    if ($price_res && $row = $price_res->fetch_assoc()) {
        $price_count = (int)$row['cnt'];
    }
    
    $result = array(
        'ok' => true,
        'type' => 'stats',
        'pair_count' => $pair_count,
        'signal_count' => $signal_count,
        'price_count' => $price_count
    );
    
} elseif ($type === 'strategies') {
    // Get list of strategies
    $strategies = array();
    $strat_res = $conn->query("SELECT name, description, strategy_type, ideal_timeframe 
                               FROM fx_strategies 
                               ORDER BY name ASC");
    if ($strat_res) {
        while ($row = $strat_res->fetch_assoc()) {
            $strategies[] = array(
                'name' => $row['name'],
                'description' => $row['description'],
                'strategy_type' => $row['strategy_type'],
                'ideal_timeframe' => $row['ideal_timeframe']
            );
        }
    }
    
    $result = array(
        'ok' => true,
        'type' => 'strategies',
        'strategies' => $strategies,
        'count' => count($strategies)
    );
    
} elseif ($type === 'signals') {
    // Get recent signals
    $limit = isset($_GET['limit']) ? (int)$_GET['limit'] : (isset($_POST['limit']) ? (int)$_POST['limit'] : 50);
    if ($limit > 500) $limit = 500;
    if ($limit < 1) $limit = 50;
    
    $signals = array();
    $signal_res = $conn->query("SELECT pair, strategy_name, signal_date, direction, entry_price 
                                FROM fx_signals 
                                ORDER BY signal_date DESC, pair ASC 
                                LIMIT $limit");
    if ($signal_res) {
        while ($row = $signal_res->fetch_assoc()) {
            $signals[] = array(
                'pair' => $row['pair'],
                'strategy_name' => $row['strategy_name'],
                'signal_date' => $row['signal_date'],
                'direction' => $row['direction'],
                'entry_price' => round((float)$row['entry_price'], 6)
            );
        }
    }
    
    $result = array(
        'ok' => true,
        'type' => 'signals',
        'signals' => $signals,
        'count' => count($signals),
        'limit' => $limit
    );
    
} else {
    $result = array(
        'ok' => false,
        'error' => 'Invalid type. Use: stats, strategies, or signals'
    );
}

// Audit log
$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : 'unknown';
$ip_esc = $conn->real_escape_string($ip);
$details_esc = $conn->real_escape_string("data.php?type=$type");
$now = date('Y-m-d H:i:s');
$conn->query("INSERT INTO fx_audit_log (action_type, details, ip_address, created_at) 
              VALUES ('data_query', '$details_esc', '$ip_esc', '$now')");

echo json_encode($result);
$conn->close();
?>
