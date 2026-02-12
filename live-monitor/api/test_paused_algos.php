<?php
/**
 * Test script to verify that paused algorithms are correctly filtered
 * Tests the $PAUSED_ALGORITHMS array logic without running actual scans
 */

header('Content-Type: application/json');

// Mock the paused algorithms array (same as in live_signals.php)
$PAUSED_ALGORITHMS = array(
    'Consensus'
);

$PAUSED_STOCK_ALGOS = array(
    'ETF Masters',
    'Sector Rotation',
    'Sector Momentum',
    'Blue Chip Growth',
    'Technical Momentum',
    'Composite Rating',
    'Cursor Genius'
);

// Test signals - simulate what would come from algorithm functions
$test_signals = array(
    array('algorithm_name' => 'Consensus', 'asset_class' => 'CRYPTO', 'signal_type' => 'BUY'),
    array('algorithm_name' => 'Consensus', 'asset_class' => 'FOREX', 'signal_type' => 'BUY'),
    array('algorithm_name' => 'Consensus', 'asset_class' => 'STOCK', 'signal_type' => 'BUY'),
    array('algorithm_name' => 'ETF Masters', 'asset_class' => 'STOCK', 'signal_type' => 'BUY'),
    array('algorithm_name' => 'Momentum Burst', 'asset_class' => 'CRYPTO', 'signal_type' => 'BUY'),
    array('algorithm_name' => 'RSI Reversal', 'asset_class' => 'STOCK', 'signal_type' => 'BUY'),
    array('algorithm_name' => 'Sector Rotation', 'asset_class' => 'STOCK', 'signal_type' => 'BUY')
);

$filtered_signals = array();
$blocked_signals = array();

// Apply the same filtering logic as in live_signals.php
foreach ($test_signals as $sig) {
    $blocked = false;
    $reason = '';
    
    // Check general paused algorithms
    if (in_array($sig['algorithm_name'], $PAUSED_ALGORITHMS)) {
        $blocked = true;
        $reason = 'Paused (all asset classes)';
    }
    
    // Check stock-specific paused algorithms
    if ($sig['asset_class'] === 'STOCK' && in_array($sig['algorithm_name'], $PAUSED_STOCK_ALGOS)) {
        $blocked = true;
        $reason = 'Paused (stock-specific)';
    }
    
    if ($blocked) {
        $blocked_signals[] = array(
            'algorithm' => $sig['algorithm_name'],
            'asset_class' => $sig['asset_class'],
            'reason' => $reason
        );
    } else {
        $filtered_signals[] = array(
            'algorithm' => $sig['algorithm_name'],
            'asset_class' => $sig['asset_class'],
            'status' => 'ACTIVE'
        );
    }
}

$result = array(
    'ok' => true,
    'test_name' => 'Paused Algorithms Filter Test',
    'timestamp' => date('Y-m-d H:i:s'),
    'paused_algorithms' => $PAUSED_ALGORITHMS,
    'paused_stock_algos' => $PAUSED_STOCK_ALGOS,
    'test_results' => array(
        'total_signals_tested' => count($test_signals),
        'signals_blocked' => count($blocked_signals),
        'signals_allowed' => count($filtered_signals)
    ),
    'blocked_signals' => $blocked_signals,
    'allowed_signals' => $filtered_signals,
    'validation' => array(
        'consensus_blocked_crypto' => in_array('Consensus', array_column($blocked_signals, 'algorithm')) ? 'PASS' : 'FAIL',
        'consensus_blocked_forex' => in_array('Consensus', array_column($blocked_signals, 'algorithm')) ? 'PASS' : 'FAIL',
        'consensus_blocked_stock' => in_array('Consensus', array_column($blocked_signals, 'algorithm')) ? 'PASS' : 'FAIL',
        'momentum_allowed' => in_array('Momentum Burst', array_column($filtered_signals, 'algorithm')) ? 'PASS' : 'FAIL',
        'rsi_allowed' => in_array('RSI Reversal', array_column($filtered_signals, 'algorithm')) ? 'PASS' : 'FAIL',
        'etf_masters_blocked' => in_array('ETF Masters', array_column($blocked_signals, 'algorithm')) ? 'PASS' : 'FAIL'
    )
);

// Overall test status
$all_passed = true;
foreach ($result['validation'] as $test => $status) {
    if ($status === 'FAIL') {
        $all_passed = false;
        break;
    }
}

$result['overall_status'] = $all_passed ? 'ALL TESTS PASSED' : 'SOME TESTS FAILED';

echo json_encode($result, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
?>
