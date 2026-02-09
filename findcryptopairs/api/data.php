<?php
/**
 * Returns basic data and statistics
 * PHP 5.2 compatible
 * Parameters: type (stats|strategies|signals)
 */
require_once dirname(__FILE__) . '/db_connect.php';

function _get_param($key, $default) {
    if (isset($_POST[$key]) && $_POST[$key] !== '') return $_POST[$key];
    if (isset($_GET[$key]) && $_GET[$key] !== '') return $_GET[$key];
    return $default;
}

$type = _get_param('type', 'stats');

if ($type === 'stats') {
    // Get counts
    $pair_count = 0;
    $pair_res = $conn->query("SELECT COUNT(DISTINCT pair) as cnt FROM cp_pairs");
    if ($pair_res && $row = $pair_res->fetch_assoc()) {
        $pair_count = (int)$row['cnt'];
    }
    
    $signal_count = 0;
    $signal_res = $conn->query("SELECT COUNT(*) as cnt FROM cp_signals");
    if ($signal_res && $row = $signal_res->fetch_assoc()) {
        $signal_count = (int)$row['cnt'];
    }
    
    $price_count = 0;
    $price_res = $conn->query("SELECT COUNT(*) as cnt FROM cp_prices");
    if ($price_res && $row = $price_res->fetch_assoc()) {
        $price_count = (int)$row['cnt'];
    }
    
    echo json_encode(array(
        'ok' => true,
        'type' => 'stats',
        'stats' => array(
            'pair_count' => $pair_count,
            'signal_count' => $signal_count,
            'price_count' => $price_count
        )
    ));
    
} elseif ($type === 'strategies') {
    // Get list of strategies
    $strategies = array();
    $strat_res = $conn->query("SELECT name, description, strategy_type, ideal_timeframe 
                                FROM cp_strategies 
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
    
    echo json_encode(array(
        'ok' => true,
        'type' => 'strategies',
        'strategies' => $strategies
    ));
    
} elseif ($type === 'signals') {
    // Get recent signals
    $limit = (int)_get_param('limit', 50);
    if ($limit > 500) $limit = 500;
    if ($limit < 1) $limit = 50;
    
    $signals = array();
    $signals_res = $conn->query("SELECT pair, strategy_name, signal_date, signal_time, direction, entry_price 
                                  FROM cp_signals 
                                  ORDER BY signal_date DESC, signal_time DESC 
                                  LIMIT $limit");
    if ($signals_res) {
        while ($row = $signals_res->fetch_assoc()) {
            $signals[] = array(
                'pair' => $row['pair'],
                'strategy_name' => $row['strategy_name'],
                'signal_date' => $row['signal_date'],
                'signal_time' => $row['signal_time'],
                'direction' => $row['direction'],
                'entry_price' => round((float)$row['entry_price'], 8)
            );
        }
    }
    
    echo json_encode(array(
        'ok' => true,
        'type' => 'signals',
        'signals' => $signals,
        'limit' => $limit
    ));
    
} else {
    echo json_encode(array(
        'ok' => false,
        'error' => 'Invalid type. Use: stats, strategies, or signals'
    ));
}

$conn->close();
?>
